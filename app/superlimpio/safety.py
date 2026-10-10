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

from . import i18n, plat
from .plat import know
from .util import APP_ROOT, LOG_DIR, norm_key


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

# Qué procesos y rutas se protegen depende del sistema: las listas viven en la capa de
# plataforma. Los procesos siguen a `plat.know` (que los tests pueden cambiar); las rutas
# usan siempre las del sistema real.
_KNOWLEDGE_NAMES = ("PROTECTED_PROCESSES", "SENSITIVE_PROCESSES")


def __getattr__(name: str):
    if name in _KNOWLEDGE_NAMES:
        return getattr(know, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _protected_roots() -> tuple[set[str], set[str], set[str]]:
    """(rutas exactas, rutas con todo su contenido, carpetas de programas) protegidas."""
    exact, tree, programs = plat.native_know.protected_roots()
    tree = set(tree) | {str(APP_ROOT)}   # la propia aplicación
    return ({norm_key(p) for p in exact if p}, {norm_key(p) for p in tree if p},
            {norm_key(p) for p in programs if p})


_EXACT, _TREE, _PROGRAMS = _protected_roots()


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
    if rest.strip("\\/").split(os.sep)[0].lower() in plat.native_know.PER_DRIVE_SYSTEM_DIRS:
        return DeleteCheck(False, i18n.t("safety.per_drive_system"))
    base = os.path.basename(key)
    hints = plat.native_know.SYSTEM_FILE_HINTS
    if base.lower() in hints:
        return DeleteCheck(False, i18n.t(hints[base.lower()]))
    if key in _EXACT:
        return DeleteCheck(False, i18n.t("safety.essential"))
    for root in _TREE:
        if key == root or key.startswith(root + os.sep):
            if root in _PROGRAMS:
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
    if pid in know.VITAL_PIDS or n in know.PROTECTED_PROCESSES:
        return False, Risk.CRITICO, i18n.t("safety.proc.essential")
    if pid == os.getpid():
        return False, Risk.ALTO, i18n.t("safety.proc.self")
    if n in know.SENSITIVE_PROCESSES:
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
        with _log_lock, open(LOG_DIR / "acciones.log", "a", encoding="utf-8", errors="backslashreplace") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_log(limit: int = 500) -> list[dict]:
    path = LOG_DIR / "acciones.log"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
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
