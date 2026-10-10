"""Limpieza al estilo CCleaner: categorías de archivos temporales y cachés.

Cada categoría es una LISTA BLANCA cerrada de ubicaciones conocidas (las de cada
sistema operativo están en la capa de plataforma). La app nunca borra fuera de ellas.
Primero se analiza (sin tocar nada) y solo tras la confirmación del usuario se borra. Los
archivos en uso se omiten.

Las ubicaciones salen de carpetas del sistema y de variables del entorno, así que antes
de vaciar una se comprueba dónde está de verdad (`safety.check_clean_root`): si es un
enlace, o resulta ser la carpeta de usuario, un disco entero o una zona con carpetas
protegidas dentro, se deja sin tocar y se avisa.
"""

from __future__ import annotations

import glob
import os
import stat as _stat
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import i18n, plat
from .safety import Risk, check_clean_root, log_action
from .plat import CLOUD_ONLY_MASK
from .util import IS_WINDOWS, expand, is_link, long_path


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
    refused: list[tuple[str, str]] = field(default_factory=list)   # (carpeta, por qué no se toca)


@dataclass
class CleanResult:
    category: Category
    freed: int = 0
    deleted: int = 0
    failed: int = 0
    note: str = ""
    refused: list[tuple[str, str]] = field(default_factory=list)
    cancelled: bool = False


def _matches(pattern: str) -> list[str]:
    path = expand(pattern)
    # Una variable sin definir deja la ruta relativa («%TEMP%»): no se busca en la carpeta actual.
    return glob.glob(path) if os.path.isabs(path) else []


def _resolve_dirs(patterns: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Carpetas a vaciar, ya con su ruta real, y las que se rechazan con su motivo."""
    found: list[str] = []
    refused: list[tuple[str, str]] = []
    for pat in patterns:
        for path in _matches(pat):
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if not _stat.S_ISDIR(st.st_mode) and not is_link(st):
                continue
            chk, real = check_clean_root(path)
            if chk.allowed:
                found.append(real)
            else:
                refused.append((path, chk.reason))
    # sin duplicados ni anidados
    final: list[str] = []
    for p in sorted(set(found), key=len):
        key = os.path.normcase(p)
        if not any(key == os.path.normcase(q) or key.startswith(os.path.normcase(q) + os.sep) for q in final):
            final.append(p)
    return final, refused


def _resolve_files(patterns: list[str]) -> list[str]:
    """Archivos sueltos: solo archivos corrientes, nunca un enlace."""
    out = []
    for pat in patterns:
        for path in _matches(pat):
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if _stat.S_ISREG(st.st_mode) and not is_link(st):
                out.append(path)
    return sorted(set(out))


def _resolve(patterns: list[str], want_dir: bool) -> list[str]:
    return _resolve_dirs(patterns)[0] if want_dir else _resolve_files(patterns)


def _iter_tree(root: str, cancel: threading.Event | None) -> Any:
    """Recorre sin seguir enlaces/junctions ni salir a otro disco montado. Devuelve
    (archivos, carpetas_postorden)."""
    files: list[tuple[str, int, float]] = []
    dirs: list[str] = []
    stack = [root]
    try:
        root_dev = os.lstat(long_path(root)).st_dev
    except OSError:
        return files, dirs
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        dirs.append(cur)
        try:
            with os.scandir(long_path(cur)) as it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                        if is_link(st):
                            continue
                        full = os.path.join(cur, e.name)
                        if _stat.S_ISDIR(st.st_mode):
                            if IS_WINDOWS or st.st_dev == root_dev:
                                stack.append(full)
                        elif _stat.S_ISREG(st.st_mode):
                            if getattr(st, "st_file_attributes", 0) & CLOUD_ONLY_MASK:
                                continue
                            files.append((full, st.st_size, st.st_mtime))
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
    roots, est.refused = _resolve_dirs(cat.dirs)
    for d in roots:
        est.locations.append(d)
        files, _ = _iter_tree(d, cancel)
        for _p, size, mtime in files:
            if cutoff and mtime > cutoff:
                est.skipped_young += 1
                continue
            est.size += size
            est.count += 1
    for f in _resolve_files(cat.files):
        try:
            st = os.lstat(f)
        except OSError:
            continue
        est.locations.append(f)
        est.size += st.st_size
        est.count += 1
    notes = []
    if est.refused:
        notes.append(i18n.t("clean.refused_note", n=len(est.refused), why=est.refused[0][1]))
    if cat.admin and not plat.is_admin():
        notes.append(i18n.t("clean.partial_admin"))
    est.note = " ".join(notes)
    return est


# Donde el sistema lo permite (Linux), se borra a través del descriptor de cada carpeta:
# aunque alguien cambie una carpeta por un enlace a mitad de la limpieza, no se sale de ella.
_FD_SAFE = (not IS_WINDOWS and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
            and os.unlink in os.supports_dir_fd and os.rmdir in os.supports_dir_fd
            and os.open in os.supports_dir_fd and os.scandir in os.supports_fd)


def _stopped(cancel: threading.Event | None) -> bool:
    return cancel is not None and cancel.is_set()


def _clean_dir_fd(root: str, cutoff: float | None, cancel: threading.Event | None, res: CleanResult) -> None:
    """Vacía una carpeta trabajando siempre con descriptores (openat/unlinkat)."""
    # getattr: estas constantes no existen en Windows, donde esta función no se usa (ver _FD_SAFE)
    flags = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_CLOEXEC", 0))

    def empty_files(fd: int, dev: int) -> list[str]:
        """Borra los archivos de esa carpeta y devuelve sus subcarpetas (del mismo disco)."""
        subdirs = []
        with os.scandir(fd) as it:
            entries = list(it)
        for e in entries:
            if _stopped(cancel):
                break
            try:
                st = e.stat(follow_symlinks=False)
                if _stat.S_ISLNK(st.st_mode):
                    continue
                if _stat.S_ISDIR(st.st_mode):
                    if st.st_dev == dev:
                        subdirs.append(e.name)
                elif _stat.S_ISREG(st.st_mode):
                    if cutoff and st.st_mtime > cutoff:
                        continue
                    try:
                        os.unlink(e.name, dir_fd=fd)
                        res.freed += st.st_size
                        res.deleted += 1
                    except OSError:
                        res.failed += 1
            except OSError:
                res.failed += 1
        return subdirs

    try:
        root_fd = os.open(root, flags)
    except OSError:
        res.failed += 1
        return
    dev = -1
    # (descriptor, nombre en su carpeta padre, subcarpetas pendientes)
    frames: list[tuple[int, str, list[str]]] = [(root_fd, "", [])]
    try:
        dev = os.fstat(root_fd).st_dev
        try:
            frames[-1] = (root_fd, "", empty_files(root_fd, dev))
        except OSError:
            res.failed += 1
        while frames:
            fd, name, pending = frames[-1]
            if pending and not _stopped(cancel):
                child = pending.pop()
                try:
                    child_fd = os.open(child, flags, dir_fd=fd)   # falla si ahora es un enlace
                except OSError:
                    res.failed += 1
                    continue
                try:
                    frames.append((child_fd, child, empty_files(child_fd, dev)))
                except OSError:
                    os.close(child_fd)
                    res.failed += 1
                continue
            frames.pop()
            os.close(fd)
            if frames:   # nunca la carpeta raíz de la categoría
                try:
                    os.rmdir(name, dir_fd=frames[-1][0])
                except OSError:
                    pass   # no quedó vacía (archivos recientes o en uso): se conserva
    finally:
        for fd, _name, _pending in frames:
            try:
                os.close(fd)
            except OSError:
                pass   # ya estaba cerrado: no hay nada más que soltar


def _still_real_dir(path: str) -> bool:
    """La carpeta sigue siendo una carpeta de verdad y sigue estando donde estaba."""
    try:
        if is_link(os.lstat(long_path(path))):
            return False
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(path)
    except OSError:
        return False


def _clean_dir_paths(root: str, cutoff: float | None, cancel: threading.Event | None, res: CleanResult) -> None:
    """Vacía una carpeta por rutas (Windows). Antes de borrar en cada subcarpeta se comprueba
    que no se ha cambiado por un enlace, y cada archivo se vuelve a mirar antes de quitarlo."""
    files, dirs = _iter_tree(root, cancel)
    trusted: dict[str, bool] = {}
    for path, size, mtime in files:
        if _stopped(cancel):
            break
        if cutoff and mtime > cutoff:
            continue
        parent = os.path.dirname(path)
        if parent not in trusted:
            trusted[parent] = _still_real_dir(parent)
        if trusted[parent] and _remove_file(path):
            res.freed += size
            res.deleted += 1
        else:
            res.failed += 1
    if _stopped(cancel):
        return
    # Subcarpetas vacías (de más profunda a menos); nunca la carpeta raíz de la categoría
    for sub in sorted(dirs[1:], key=len, reverse=True):
        try:
            if not is_link(os.lstat(long_path(sub))):
                os.rmdir(long_path(sub))
        except OSError:
            pass   # no quedó vacía (archivos recientes o en uso): se conserva


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
    roots, res.refused = _resolve_dirs(cat.dirs)
    for d in roots:
        if _stopped(cancel):
            break
        if _FD_SAFE:
            _clean_dir_fd(d, cutoff, cancel, res)
        else:
            _clean_dir_paths(d, cutoff, cancel, res)
    for f in _resolve_files(cat.files):
        if _stopped(cancel):   # detenido: no se borra nada más, tampoco los archivos sueltos
            break
        try:
            size = os.lstat(f).st_size
        except OSError:
            continue
        if _remove_file(f):
            res.freed += size
            res.deleted += 1
        else:
            res.failed += 1
    res.cancelled = _stopped(cancel)
    notes = []
    if res.cancelled:
        notes.append(i18n.t("clean.cancelled_note"))
    if res.failed:
        notes.append(i18n.t("clean.skipped_note", n=res.failed))
    if res.refused:
        notes.append(i18n.t("clean.refused_note", n=len(res.refused), why=res.refused[0][1]))
    res.note = " ".join(notes)
    log_action("limpieza", cat.name, res.note or "ok", ok=not res.cancelled, liberado=res.freed,
               archivos=res.deleted, omitidos=res.failed,
               rechazadas=[p for p, _why in res.refused])
    return res


def _remove_file(path: str) -> bool:
    target = long_path(path)
    try:
        st = os.lstat(target)
        if is_link(st) or not _stat.S_ISREG(st.st_mode):
            return False   # ya no es el archivo que se analizó
        try:
            os.remove(target)
        except PermissionError:
            if st.st_mode & _stat.S_IWRITE:
                return False   # en uso o sin permiso
            os.chmod(target, _stat.S_IWRITE | _stat.S_IREAD)   # solo lectura: se quita y se reintenta una vez
            os.remove(target)
        return True
    except OSError:
        return False


def running_process_names() -> set[str]:
    return {p.name.lower() for p in plat.list_processes()}


__all__ = ["Category", "default_categories", "analyze", "clean", "Estimate", "CleanResult",
           "running_process_names", "IS_WINDOWS"]
