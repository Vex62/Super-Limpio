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

from . import winapi
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


def default_categories() -> list[Category]:
    L = r"%LOCALAPPDATA%"
    A = r"%APPDATA%"
    U = r"%USERPROFILE%"
    W = r"%WINDIR%"
    P = r"%PROGRAMDATA%"
    cats = [
        # ----------------------------------------------------------- Windows
        Category("temp_user", "Windows", "Temporales del usuario",
                 "Carpeta %TEMP%. Solo archivos con más de 24 h para no romper instalaciones en curso.",
                 dirs=[r"%TEMP%"], min_age_hours=24, risk=Risk.BAJO),
        Category("temp_win", "Windows", "Temporales de Windows",
                 r"C:\Windows\Temp. Requiere administrador para la mayoría de archivos.",
                 dirs=[rf"{W}\Temp"], min_age_hours=24, risk=Risk.MEDIO, admin=True),
        Category("thumbs", "Windows", "Caché de miniaturas e iconos",
                 "Se regenera sola. Explorer bloquea parte de ella mientras está abierto.",
                 files=[rf"{L}\Microsoft\Windows\Explorer\thumbcache_*.db",
                        rf"{L}\Microsoft\Windows\Explorer\iconcache_*.db"], risk=Risk.BAJO),
        Category("wer", "Windows", "Informes de errores de Windows",
                 "Informes ya enviados o pendientes de Windows Error Reporting.",
                 dirs=[rf"{L}\Microsoft\Windows\WER", rf"{P}\Microsoft\Windows\WER\ReportArchive",
                       rf"{P}\Microsoft\Windows\WER\ReportQueue", rf"{P}\Microsoft\Windows\WER\Temp"],
                 risk=Risk.BAJO),
        Category("dumps", "Windows", "Volcados de memoria de programas",
                 "Archivos .dmp generados cuando una aplicación se cuelga.",
                 dirs=[rf"{L}\CrashDumps"], files=[rf"{W}\Minidump\*.dmp", rf"{W}\MEMORY.DMP"],
                 risk=Risk.BAJO),
        Category("wu", "Windows", "Descargas de Windows Update",
                 "Paquetes ya instalados. Windows los vuelve a descargar si los necesita. Requiere admin.",
                 dirs=[rf"{W}\SoftwareDistribution\Download"], risk=Risk.MEDIO, admin=True,
                 default_on=False),
        Category("do", "Windows", "Caché de Optimización de distribución",
                 "Actualizaciones compartidas entre equipos. Requiere admin.",
                 dirs=[rf"{W}\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache"],
                 risk=Risk.MEDIO, admin=True, default_on=False),
        Category("recycle", "Windows", "Papelera de reciclaje",
                 "Vacía la Papelera de todas las unidades. NO se puede deshacer.",
                 special="recycle_bin", risk=Risk.ALTO, default_on=False),
        # ------------------------------------------------------- Navegadores
        Category("edge", "Navegadores", "Microsoft Edge: caché",
                 "Caché web y de shaders. No borra contraseñas, historial ni cookies.",
                 dirs=_browser_profiles(rf"{L}\Microsoft\Edge\User Data"), close_apps="msedge.exe"),
        Category("chrome", "Navegadores", "Google Chrome: caché",
                 "Caché web y de shaders. No borra contraseñas, historial ni cookies.",
                 dirs=_browser_profiles(rf"{L}\Google\Chrome\User Data"), close_apps="chrome.exe"),
        Category("brave", "Navegadores", "Brave: caché", "Caché web y de shaders.",
                 dirs=_browser_profiles(rf"{L}\BraveSoftware\Brave-Browser\User Data"),
                 close_apps="brave.exe"),
        Category("firefox", "Navegadores", "Firefox: caché",
                 "Caché web (cache2). No borra marcadores ni sesiones.",
                 dirs=[rf"{L}\Mozilla\Firefox\Profiles\*\cache2"], close_apps="firefox.exe"),
        # ------------------------------------------------------- Desarrollo
        Category("pip", "Desarrollo", "Caché de pip", "Paquetes Python descargados. Regenerable.",
                 dirs=[rf"{L}\pip\Cache"], default_on=False),
        Category("npm", "Desarrollo", "Caché de npm / Yarn / pnpm",
                 "Paquetes Node descargados. Regenerable (se vuelve a descargar).",
                 dirs=[rf"{L}\npm-cache", rf"{A}\npm-cache", rf"{L}\Yarn\Cache", rf"{L}\pnpm-cache"],
                 default_on=False),
        Category("nuget", "Desarrollo", "Caché HTTP de NuGet",
                 "Solo la caché HTTP (no la carpeta de paquetes).",
                 dirs=[rf"{L}\NuGet\v3-cache", rf"{L}\NuGet\plugins-cache"], default_on=False),
        Category("gradle", "Desarrollo", "Caché de Gradle",
                 "Dependencias y builds de Gradle. Regenerable, la próxima compilación será más lenta.",
                 dirs=[rf"{U}\.gradle\caches"], default_on=False),
        Category("cargo", "Desarrollo", "Caché de Cargo (Rust)", "Crates descargados (registry/cache).",
                 dirs=[rf"{U}\.cargo\registry\cache"], default_on=False),
        Category("vscode", "Desarrollo", "Cachés de VS Code",
                 "Caché web, de código y de extensiones antiguas de VS Code instalado.",
                 dirs=[rf"{A}\Code\Cache", rf"{A}\Code\CachedData", rf"{A}\Code\CachedExtensionVSIXs",
                       rf"{A}\Code\Code Cache", rf"{A}\Code\GPUCache"], close_apps="Code.exe"),
        # --------------------------------------------------------- Programas
        Category("discord", "Aplicaciones", "Discord / Teams / Slack: caché",
                 "Cachés de apps Electron de mensajería.",
                 dirs=[rf"{A}\discord\Cache", rf"{A}\discord\Code Cache", rf"{A}\discord\GPUCache",
                       rf"{A}\Slack\Cache", rf"{A}\Slack\Code Cache",
                       rf"{L}\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView\Default\Cache"],
                 default_on=False),
        Category("dx", "Aplicaciones", "Caché de shaders DirectX / GPU",
                 "Shaders compilados por juegos y drivers. Se regeneran.",
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
        est.locations = ["Papelera de reciclaje (todas las unidades)"]
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
        est.note = "Sin admin solo se borrará una parte."
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
        res.note = f"{res.failed} archivos en uso o sin permiso se han omitido."
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
