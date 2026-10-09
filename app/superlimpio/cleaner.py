"""Limpieza al estilo CCleaner: categorías de archivos temporales y cachés.

Cada categoría es una LISTA BLANCA cerrada de ubicaciones conocidas. La app
nunca borra fuera de ellas. Primero se analiza (sin tocar nada) y solo tras
la confirmación del usuario se borra. Los archivos en uso se omiten.
"""

from __future__ import annotations

import glob
import os
import stat as _stat
import threading
import time
from dataclasses import dataclass, field

from . import i18n, winapi
from .safety import Risk, log_action
from .scanner import _is_link_or_junction
from .util import IS_WINDOWS, expand
from .winapi import CLOUD_ONLY_MASK


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


def _browser_profiles(base: str) -> list[str]:
    """Rutas de caché de navegadores Chromium para todos los perfiles."""
    out = []
    for sub in (r"Cache\Cache_Data", "Code Cache", "GPUCache", r"Service Worker\CacheStorage"):
        out.append(os.path.join(base, "*", sub))
    out.append(os.path.join(base, "ShaderCache"))
    out.append(os.path.join(base, "GrShaderCache"))
    return out


def _cat(cat_id: str, group: str, **kw) -> Category:
    """Crea una categoría cuyo nombre y descripción se leen del catálogo i18n."""
    return Category(cat_id, group, i18n.t(f"clean.{cat_id}.name"), i18n.t(f"clean.{cat_id}.desc"), **kw)


def default_categories() -> list[Category]:
    L = r"%LOCALAPPDATA%"
    A = r"%APPDATA%"
    U = r"%USERPROFILE%"
    W = r"%WINDIR%"
    P = r"%PROGRAMDATA%"
    cats = [
        # ----------------------------------------------------------- Windows
        _cat("temp_user", "Windows", dirs=[r"%TEMP%"], min_age_hours=24, risk=Risk.BAJO),
        _cat("temp_win", "Windows", dirs=[rf"{W}\Temp"], min_age_hours=24, risk=Risk.MEDIO, admin=True),
        _cat("thumbs", "Windows",
             files=[rf"{L}\Microsoft\Windows\Explorer\thumbcache_*.db",
                    rf"{L}\Microsoft\Windows\Explorer\iconcache_*.db"], risk=Risk.BAJO),
        _cat("wer", "Windows",
             dirs=[rf"{L}\Microsoft\Windows\WER", rf"{P}\Microsoft\Windows\WER\ReportArchive",
                   rf"{P}\Microsoft\Windows\WER\ReportQueue", rf"{P}\Microsoft\Windows\WER\Temp"],
             risk=Risk.BAJO),
        _cat("dumps", "Windows",
             dirs=[rf"{L}\CrashDumps"], files=[rf"{W}\Minidump\*.dmp", rf"{W}\MEMORY.DMP"],
             risk=Risk.BAJO),
        _cat("wu", "Windows",
             dirs=[rf"{W}\SoftwareDistribution\Download"], risk=Risk.MEDIO, admin=True, default_on=False),
        _cat("do", "Windows",
             dirs=[rf"{W}\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache"],
             risk=Risk.MEDIO, admin=True, default_on=False),
        _cat("recycle", "Windows", special="recycle_bin", risk=Risk.ALTO, default_on=False),
        # ------------------------------------------------------- Navegadores
        _cat("edge", "Navegadores", dirs=_browser_profiles(rf"{L}\Microsoft\Edge\User Data"),
             close_apps="msedge.exe"),
        _cat("chrome", "Navegadores", dirs=_browser_profiles(rf"{L}\Google\Chrome\User Data"),
             close_apps="chrome.exe"),
        _cat("brave", "Navegadores",
             dirs=_browser_profiles(rf"{L}\BraveSoftware\Brave-Browser\User Data"), close_apps="brave.exe"),
        _cat("firefox", "Navegadores",
             dirs=[rf"{L}\Mozilla\Firefox\Profiles\*\cache2"], close_apps="firefox.exe"),
        # ------------------------------------------------------- Desarrollo
        _cat("pip", "Desarrollo", dirs=[rf"{L}\pip\Cache"], default_on=False),
        _cat("npm", "Desarrollo",
             dirs=[rf"{L}\npm-cache", rf"{A}\npm-cache", rf"{L}\Yarn\Cache", rf"{L}\pnpm-cache"],
             default_on=False),
        _cat("nuget", "Desarrollo",
             dirs=[rf"{L}\NuGet\v3-cache", rf"{L}\NuGet\plugins-cache"], default_on=False),
        _cat("gradle", "Desarrollo", dirs=[rf"{U}\.gradle\caches"], default_on=False),
        _cat("cargo", "Desarrollo", dirs=[rf"{U}\.cargo\registry\cache"], default_on=False),
        _cat("vscode", "Desarrollo",
             dirs=[rf"{A}\Code\Cache", rf"{A}\Code\CachedData", rf"{A}\Code\CachedExtensionVSIXs",
                   rf"{A}\Code\Code Cache", rf"{A}\Code\GPUCache"], close_apps="Code.exe"),
        # --------------------------------------------------------- Programas
        _cat("discord", "Aplicaciones",
             dirs=[rf"{A}\discord\Cache", rf"{A}\discord\Code Cache", rf"{A}\discord\GPUCache",
                   rf"{A}\Slack\Cache", rf"{A}\Slack\Code Cache",
                   rf"{L}\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView\Default\Cache"],
             default_on=False),
        _cat("dx", "Aplicaciones",
             dirs=[rf"{L}\D3DSCache", rf"{L}\NVIDIA\DXCache", rf"{L}\NVIDIA\GLCache", rf"{L}\AMD\DxCache"],
             default_on=False),
    ]
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
        est.size, est.count = winapi.recycle_bin_info()
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
    if cat.admin and not winapi.is_admin():
        est.note = i18n.t("clean.partial_admin")
    return est


def clean(cat: Category, cancel: threading.Event | None = None) -> CleanResult:
    res = CleanResult(cat)
    if cat.special == "recycle_bin":
        size, count = winapi.recycle_bin_info()
        ok, msg = winapi.empty_recycle_bin()
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
    return {p.name.lower() for p in winapi.list_processes()}


__all__ = ["Category", "default_categories", "analyze", "clean", "Estimate", "CleanResult",
           "running_process_names", "IS_WINDOWS"]
