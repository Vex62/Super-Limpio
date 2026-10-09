"""Reglas de seguridad: rutas protegidas, niveles de riesgo y registro de acciones.

Principios:
  * Nada se borra ni se ejecuta sin una confirmación explícita en pantalla.
  * Por defecto se usa la Papelera (recuperable). El borrado definitivo exige
    escribir una palabra de confirmación.
  * Hay rutas del sistema que la app se niega a borrar aunque el usuario lo pida.
  * Todas las acciones quedan registradas en logs/acciones.log (portable).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from dataclasses import dataclass
from enum import IntEnum

from . import i18n
from .util import APP_ROOT, IS_WINDOWS, LOG_DIR, expand, norm_key


class Risk(IntEnum):
    BAJO = 1      # recuperable o sin efectos (abrir una ventana, Papelera)
    MEDIO = 2     # borra datos regenerables (cachés, temporales)
    ALTO = 3      # desinstala software / necesita administrador
    CRITICO = 4   # irreversible o afecta al sistema (borrado definitivo, comandos de sistema)

    @property
    def label(self) -> str:
        return i18n.t(f"risk.{int(self)}")


def confirm_word() -> str:
    """Palabra que el usuario debe escribir para acciones críticas (según el idioma)."""
    return i18n.t("confirm.word")

# Procesos que nunca se deben finalizar (el sistema se cuelga o reinicia)
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe", "fontdrvhost.exe",
    "dwm.exe", "memory compression", "secure system", "msmpeng.exe", "nissrv.exe",
    "securityhealthservice.exe", "sgrmbroker.exe", "audiodg.exe", "spoolsv.exe",
}

# Procesos que se pueden cerrar pero con aviso reforzado
SENSITIVE_PROCESSES = {"explorer.exe", "sihost.exe", "ctfmon.exe", "searchhost.exe",
                       "startmenuexperiencehost.exe", "taskhostw.exe", "runtimebroker.exe"}


def _protected_roots() -> tuple[set[str], set[str]]:
    """Devuelve (rutas_exactas, rutas_con_todo_su_contenido) protegidas."""
    exact: set[str] = set()
    tree: set[str] = set()
    if IS_WINDOWS:
        sysdrive = os.environ.get("SystemDrive", "C:")   # Windows no siempre está en C:
        windir = os.environ.get("WINDIR", rf"{sysdrive}\Windows")
        programdata = os.environ.get("ProgramData", rf"{sysdrive}\ProgramData")
        tree.update({
            windir,
            os.environ.get("ProgramFiles", rf"{sysdrive}\Program Files"),
            os.environ.get("ProgramFiles(x86)", rf"{sysdrive}\Program Files (x86)"),
            os.environ.get("ProgramW6432", rf"{sysdrive}\Program Files"),
            rf"{sysdrive}\Recovery",
            rf"{sysdrive}\Boot",
            rf"{sysdrive}\$WinREAgent",
            expand(r"%LOCALAPPDATA%\Microsoft\WindowsApps"),
            expand(r"%LOCALAPPDATA%\Packages"),
            rf"{programdata}\Microsoft",
        })
        exact.update({
            programdata,
            os.environ.get("USERPROFILE", ""),
            os.environ.get("APPDATA", ""),
            os.environ.get("LOCALAPPDATA", ""),
            expand(r"%USERPROFILE%\AppData"),
            expand(r"%USERPROFILE%\AppData\LocalLow"),
            rf"{sysdrive}\Users",
            rf"{sysdrive}\Users\Public",
            rf"{sysdrive}\Users\Default",
        })
        for name in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
                     "OneDrive", "Favorites", "Contacts", "Saved Games", "Links", "Searches"):
            exact.add(expand(rf"%USERPROFILE%\{name}"))
        for f in ("DumpStack.log.tmp", "bootmgr"):
            exact.add(rf"{sysdrive}\{f}")
    else:
        tree.update({"/bin", "/boot", "/etc", "/lib", "/lib64", "/proc", "/sbin", "/sys", "/usr", "/dev"})
        exact.update({"/home", os.path.expanduser("~")})
    tree.add(str(APP_ROOT))  # la propia aplicación
    return ({norm_key(p) for p in exact if p}, {norm_key(p) for p in tree if p})


_EXACT, _TREE = _protected_roots()

_PER_DRIVE_SYSTEM_DIRS = {"system volume information", "$recycle.bin"}

_SYSTEM_FILE_HINTS = {
    "pagefile.sys": "safety.file.pagefile",
    "hiberfil.sys": "safety.file.hiberfil",
    "swapfile.sys": "safety.file.swapfile",
}


@dataclass
class DeleteCheck:
    allowed: bool
    reason: str = ""


def check_deletable(path: str) -> DeleteCheck:
    """Comprueba si una ruta se puede borrar. Las rutas del sistema se bloquean siempre."""
    if not path:
        return DeleteCheck(False, i18n.t("safety.empty_path"))
    key = norm_key(path)
    # Raíz de unidad
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    if rest.strip("\\/") == "":
        return DeleteCheck(False, i18n.t("safety.drive_root"))
    # Carpetas del sistema que existen en la raíz de TODAS las unidades
    if rest.strip("\\/").split(os.sep)[0].lower() in _PER_DRIVE_SYSTEM_DIRS:
        return DeleteCheck(False, i18n.t("safety.per_drive_system"))
    base = os.path.basename(key)
    if base in _SYSTEM_FILE_HINTS:
        return DeleteCheck(False, i18n.t(_SYSTEM_FILE_HINTS[base]))
    if key in _EXACT:
        return DeleteCheck(False, i18n.t("safety.essential"))
    for root in _TREE:
        if key == root or key.startswith(root + os.sep):
            if "program files" in root:
                return DeleteCheck(False, i18n.t("safety.program_files"))
            if root == norm_key(str(APP_ROOT)):
                return DeleteCheck(False, i18n.t("safety.own_app"))
            return DeleteCheck(False, i18n.t("safety.protected_zone"))
    # Ninguna carpeta que contenga una zona protegida
    for root in _TREE | _EXACT:
        if root.startswith(key + os.sep):
            return DeleteCheck(False, i18n.t("safety.contains_protected"))
    return DeleteCheck(True)


def check_process_kill(name: str, pid: int) -> tuple[bool, Risk, str]:
    n = name.lower()
    if pid in (0, 4) or n in PROTECTED_PROCESSES:
        return False, Risk.CRITICO, i18n.t("safety.proc.essential")
    if pid == os.getpid():
        return False, Risk.ALTO, i18n.t("safety.proc.self")
    if n in SENSITIVE_PROCESSES:
        return True, Risk.ALTO, i18n.t("safety.proc.sensitive")
    return True, Risk.MEDIO, i18n.t("safety.proc.normal")


# =========================================================================
# Registro de acciones (JSON por línea, dentro de la carpeta portable)
# =========================================================================

_log_lock = threading.Lock()


def log_action(action: str, target: str = "", result: str = "", ok: bool = True, **extra) -> None:
    rec = {
        "fecha": _dt.datetime.now().isoformat(timespec="seconds"),
        "accion": action,
        "objetivo": target,
        "ok": ok,
        "resultado": result,
    }
    rec.update(extra)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _log_lock, open(LOG_DIR / "acciones.log", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_log(limit: int = 500) -> list[dict]:
    path = LOG_DIR / "acciones.log"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
