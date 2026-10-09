"""Limpieza al estilo CCleaner: categorías de archivos temporales y cachés.

Cada categoría es una LISTA BLANCA cerrada de ubicaciones conocidas (las de cada
sistema operativo están en la capa de plataforma). La app nunca borra fuera de ellas. Primero se analiza (sin tocar nada) y solo tras
la confirmación del usuario se borra. Los archivos en uso se omiten.
"""

from __future__ import annotations

import glob
import os
import stat as _stat
import threading
import time
from dataclasses import dataclass, field

from . import i18n, plat
from .safety import Risk, log_action
from .scanner import _is_link_or_junction
from .plat import CLOUD_ONLY_MASK
from .util import IS_WINDOWS, expand


@dataclass
class Category:
    id: str
    group: str
    name: str
    description: str
    dirs: list[str] = field(default_factory=list)     # se vacía su CONTENIDO
    files: list[str] = field(default_factory=list)    # archivos sueltos (glob)
    min_age_hours: float = 0
    risk: Risk = Risk.MEDIO
    admin: bool = False
    default_on: bool = True
    special: str = ""                                 # "recycle_bin"
    close_apps: str = ""                              # app que conviene cerrar antes


def default_categories() -> list[Category]:
    """Categorías del sistema en uso, con nombre y descripción en el idioma activo."""
    cats = []
    for spec in plat.cleaner_categories():
        spec = dict(spec)
        cat_id, group = spec.pop("id"), spec.pop("group")
        spec["risk"] = Risk(spec.get("risk", int(Risk.MEDIO)))
        cats.append(Category(cat_id, group, i18n.t(f"clean.{cat_id}.name"), i18n.t(f"clean.{cat_id}.desc"),
                             **spec))
    return cats


@dataclass
class Estimate:
    category: Category
    size: int = 0
    count: int = 0
    locations: list[str] = field(default_factory=list)
    skipped_young: int = 0
    note: str = ""


@dataclass
class CleanResult:
    category: Category
    freed: int = 0
    deleted: int = 0
    failed: int = 0
    note: str = ""


def _resolve(patterns: list[str], want_dir: bool) -> list[str]:
    out = []
    for pat in patterns:
        for path in glob.glob(expand(pat)):
            if want_dir and os.path.isdir(path) and not os.path.islink(path):
                out.append(path)
            elif not want_dir and os.path.isfile(path):
                out.append(path)
    # sin duplicados ni anidados
    out = sorted(set(out), key=len)
    final: list[str] = []
    for p in out:
        if not any(p.lower().startswith(q.lower() + os.sep) for q in final):
            final.append(p)
    return final


def _iter_tree(root: str, cancel: threading.Event | None):
    """Recorre sin seguir enlaces/junctions. Devuelve (archivos, carpetas_postorden)."""
    files: list[tuple[str, int, float]] = []
    dirs: list[str] = []
    stack = [root]
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        dirs.append(cur)
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if _is_link_or_junction(e):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            st = e.stat(follow_symlinks=False)
                            if getattr(st, "st_file_attributes", 0) & CLOUD_ONLY_MASK:
                                continue
                            files.append((e.path, st.st_size, st.st_mtime))
                    except OSError:
                        continue
        except OSError:
            continue
    return files, dirs


def analyze(cat: Category, cancel: threading.Event | None = None) -> Estimate:
    est = Estimate(cat)
    if cat.special == "recycle_bin":
        est.size, est.count = plat.recycle_bin_info()
        est.locations = [i18n.t("clean.recycle_location")]
        return est
    cutoff = time.time() - cat.min_age_hours * 3600 if cat.min_age_hours else None
    for d in _resolve(cat.dirs, True):
        est.locations.append(d)
        files, _ = _iter_tree(d, cancel)
        for _p, size, mtime in files:
            if cutoff and mtime > cutoff:
                est.skipped_young += 1
                continue
            est.size += size
            est.count += 1
    for f in _resolve(cat.files, False):
        try:
            st = os.stat(f)
        except OSError:
            continue
        est.locations.append(f)
        est.size += st.st_size
        est.count += 1
    if cat.admin and not plat.is_admin():
        est.note = i18n.t("clean.partial_admin")
    return est


def clean(cat: Category, cancel: threading.Event | None = None) -> CleanResult:
    res = CleanResult(cat)
    if cat.special == "recycle_bin":
        size, count = plat.recycle_bin_info()
        ok, msg = plat.empty_recycle_bin()
        if ok:
            res.freed, res.deleted = size, count
        else:
            res.failed = 1
        res.note = msg
        log_action("limpieza", cat.name, msg, ok=ok, liberado=res.freed)
        return res
    cutoff = time.time() - cat.min_age_hours * 3600 if cat.min_age_hours else None
    for d in _resolve(cat.dirs, True):
        files, dirs = _iter_tree(d, cancel)
        for path, size, mtime in files:
            if cancel is not None and cancel.is_set():
                break
            if cutoff and mtime > cutoff:
                continue
            if _remove_file(path):
                res.freed += size
                res.deleted += 1
            else:
                res.failed += 1
        # Subcarpetas vacías (de más profunda a menos); nunca la carpeta raíz de la categoría
        for sub in sorted(dirs[1:], key=len, reverse=True):
            try:
                os.rmdir(sub)
            except OSError:
                pass
    for f in _resolve(cat.files, False):
        try:
            size = os.path.getsize(f)
        except OSError:
            continue
        if _remove_file(f):
            res.freed += size
            res.deleted += 1
        else:
            res.failed += 1
    if res.failed:
        res.note = i18n.t("clean.skipped_note", n=res.failed)
    log_action("limpieza", cat.name, res.note or "ok", ok=True, liberado=res.freed,
               archivos=res.deleted, omitidos=res.failed)
    return res


def _remove_file(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except PermissionError:
        try:
            st = os.stat(path)
            if not st.st_mode & _stat.S_IWRITE:
                os.chmod(path, _stat.S_IWRITE)
                os.remove(path)
                return True
        except OSError:
            pass
        return False
    except FileNotFoundError:
        return False
    except OSError:
        return False


def running_process_names() -> set[str]:
    return {p.name.lower() for p in plat.list_processes()}


__all__ = ["Category", "default_categories", "analyze", "clean", "Estimate", "CleanResult",
           "running_process_names", "IS_WINDOWS"]
