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
import logging
import logging.handlers
import os
import threading
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from . import i18n, plat
from .plat import know
from .util import APP_ROOT, LOG_DIR, is_link, norm_key


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


def __getattr__(name: str) -> Any:
    if name in _KNOWLEDGE_NAMES:
        return getattr(know, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _real(path: str, follow_last: bool = False) -> str | None:
    """La ruta real: con los enlaces, junctions y nombres cortos (PROGRA~1) de las carpetas
    que la contienen ya resueltos. El último elemento solo se sigue si no es él mismo un
    enlace (borrar un enlace quita el enlace, no su destino). None si no se puede resolver."""
    full = os.path.abspath(path)
    parent, name = os.path.split(full)
    try:
        if not name:
            return os.path.realpath(full)
        if not follow_last:
            try:
                if is_link(os.lstat(full)):
                    return os.path.join(os.path.realpath(parent), name)
            except OSError:
                pass   # ya no existe: se resuelve hasta donde llegue
        return os.path.realpath(full)
    except (OSError, ValueError):
        return None


def _keys(path: str) -> set[str] | None:
    """Las formas de una misma ruta que hay que comparar: tal como se escribió y la real.
    None si alguna no se sabe interpretar (se bloquea: ante la duda, no se borra)."""
    know = plat.native_know
    written = know.canonical(os.path.abspath(path))
    real = _real(written) if written else None
    real = know.canonical(real) if real else None
    if not written or not real:
        return None
    return {norm_key(written), norm_key(real)}


def _protected_roots() -> tuple[set[str], set[str], set[str]]:
    """(rutas exactas, rutas con todo su contenido, carpetas de programas) protegidas, cada
    una tal como se escribe y también resuelta (en Linux /bin es un enlace a /usr/bin)."""
    exact, tree, programs = plat.native_know.protected_roots()
    tree = set(tree) | {str(APP_ROOT)}   # la propia aplicación

    def both(paths: Any) -> set[str]:
        out = set()
        for p in paths:
            if p:
                out.add(norm_key(p))
                real = _real(p, follow_last=True)
                if real:
                    out.add(norm_key(real))
        return out

    return both(exact), both(tree), both(programs)


_EXACT, _TREE, _PROGRAMS = _protected_roots()
_OWN = {norm_key(str(APP_ROOT)), norm_key(os.path.realpath(str(APP_ROOT)))}
_ENV: dict[str, Any] = {}


def _inside(key: str, root: str) -> bool:
    """True si «key» es «root» o está dentro. Se compara por componentes, no por texto:
    «C:\\datos2» empieza por «C:\\datos» y no está dentro."""
    if key == root:
        return True
    try:
        return os.path.commonpath([key, root]) == root
    except ValueError:   # unidades distintas, o una relativa y otra absoluta
        return False


@dataclass
class DeleteCheck:
    allowed: bool
    reason: str = ""


def _blocked(key: str) -> str:
    """Motivo por el que esa ruta (ya normalizada) no se puede borrar; '' si se puede."""
    know = plat.native_know
    _drive, rest = os.path.splitdrive(key)
    parts = [p for p in rest.replace("\\", "/").split("/") if p]
    if not parts:
        return i18n.t("safety.drive_root")
    # Carpetas del sistema que existen en la raíz de TODAS las unidades
    if parts[0].lower() in know.PER_DRIVE_SYSTEM_DIRS:
        return i18n.t("safety.per_drive_system")
    hints = know.SYSTEM_FILE_HINTS
    if parts[-1].lower() in hints:
        return i18n.t(hints[parts[-1].lower()])
    if key in _EXACT:
        return i18n.t("safety.essential")
    for root in _TREE:
        if _inside(key, root):
            if root in _PROGRAMS:
                return i18n.t("safety.program_files")
            if root in _OWN:
                return i18n.t("safety.own_app")
            return i18n.t("safety.protected_zone")
    # Ninguna carpeta que contenga una zona protegida
    for root in _TREE | _EXACT:
        if root != key and _inside(root, key):
            return i18n.t("safety.contains_protected")
    if not _ENV:
        _ENV.update(know.path_env(str(APP_ROOT)))
    if know.foreign_profile(know.norm(key), _ENV):
        return i18n.t("safety.other_profile")
    return ""


def check_deletable(path: str) -> DeleteCheck:
    """Comprueba si una ruta se puede borrar. Las rutas del sistema se bloquean siempre, se
    escriban como se escriban: se compara la ruta real, no solo el texto."""
    if not path:
        return DeleteCheck(False, i18n.t("safety.empty_path"))
    if plat.native_know.name_problem(os.path.abspath(path)):
        return DeleteCheck(False, i18n.t("safety.bad_name"))
    keys = _keys(path)
    if keys is None:
        return DeleteCheck(False, i18n.t("safety.unresolved"))
    for key in sorted(keys):
        why = _blocked(key)
        if why:
            return DeleteCheck(False, why)
    try:   # la raíz de otro disco montado (un USB en /media, una carpeta de montaje)
        if os.path.ismount(os.path.abspath(path)) and not is_link(os.lstat(os.path.abspath(path))):
            return DeleteCheck(False, i18n.t("safety.drive_root"))
    except (OSError, ValueError):
        pass
    return DeleteCheck(True)


def check_clean_root(path: str) -> tuple[DeleteCheck, str]:
    """¿Se puede VACIAR esta carpeta en una limpieza? Devuelve (resultado, ruta real).

    Las carpetas de limpieza son una lista cerrada, pero salen de variables del entorno:
    si una apunta donde no debe (la carpeta de usuario, un disco entero, una zona que
    contiene otras protegidas) o es un enlace, no se toca. A diferencia del borrado, sí
    puede estar DENTRO de una zona protegida (Windows\\Temp lo está)."""
    know = plat.native_know
    full = os.path.abspath(path)
    try:
        st = os.lstat(full)
    except OSError:
        return DeleteCheck(False, i18n.t("safety.unresolved")), ""
    if is_link(st):
        return DeleteCheck(False, i18n.t("safety.is_link")), ""
    written = know.canonical(full)
    real = _real(written, follow_last=True) if written else None
    real = know.canonical(real) if real else None
    if not real or know.name_problem(real):
        return DeleteCheck(False, i18n.t("safety.unresolved")), ""
    key = norm_key(real)
    _drive, rest = os.path.splitdrive(key)
    if not rest.strip("\\/") or os.path.ismount(real):
        return DeleteCheck(False, i18n.t("safety.drive_root")), real
    if key in _EXACT or key in _TREE:
        return DeleteCheck(False, i18n.t("safety.essential")), real
    if any(_inside(root, key) for root in _TREE | _EXACT):
        return DeleteCheck(False, i18n.t("safety.contains_protected")), real
    if any(_inside(key, root) for root in _OWN):
        return DeleteCheck(False, i18n.t("safety.own_app")), real
    if not _ENV:
        _ENV.update(know.path_env(str(APP_ROOT)))
    if know.foreign_profile(know.norm(key), _ENV):
        return DeleteCheck(False, i18n.t("safety.other_profile")), real
    return DeleteCheck(True), real


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
LOG_NAME = "acciones.log"
LOG_MAX_BYTES = 1024 * 1024    # al llegar aquí el archivo rota: acciones.log.1, .2, .3
LOG_BACKUPS = 3
_READ_TAIL = 2 * 1024 * 1024   # lo más que se lee para enseñar el registro
_handler: logging.Handler | None = None
_handler_dir = None
log_failures = 0               # acciones que no se pudieron anotar (disco lleno, sin permiso)


class _RotatingLog(logging.handlers.RotatingFileHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        raise   # que log_action sepa que no se pudo escribir, en vez de callarlo


def _log_handler() -> logging.Handler:
    """El archivo de registro, con rotación. Se abre al primer uso y se vuelve a abrir si
    cambia la carpeta (los tests la cambian)."""
    global _handler, _handler_dir
    if _handler is None or _handler_dir != LOG_DIR:
        if _handler is not None:
            _handler.close()
        os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)   # solo del usuario
        _handler = _RotatingLog(
            os.path.join(LOG_DIR, LOG_NAME), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS,
            encoding="utf-8", errors="backslashreplace", delay=True)
        _handler.setFormatter(logging.Formatter("%(message)s"))
        _handler_dir = LOG_DIR
    return _handler


def close_log() -> None:
    """Suelta el archivo de registro (al salir, y en los tests antes de borrar su carpeta)."""
    global _handler
    with _log_lock:
        if _handler is not None:
            _handler.close()
            _handler = None


def log_action(action: str, target: str = "", result: str = "", ok: bool = True, **extra: Any) -> None:
    global log_failures
    rec = {
        # Hora local con su desfase («+02:00»): sin él, dos fechas de zonas distintas no se comparan.
        "fecha": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "accion": action,
        "objetivo": target,
        "ok": ok,
        "resultado": result,
    }
    rec.update(extra)
    try:
        # json.dumps escapa los saltos de línea: nada de lo que se anote puede fingir otra línea.
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with _log_lock:
            handler = _log_handler()
            handler.emit(logging.LogRecord("superlimpio", logging.INFO if ok else logging.WARNING,
                                           "", 0, line, None, None))
    except (OSError, ValueError):
        log_failures += 1   # no se puede anotar: la interfaz lo dice en «Registro de acciones»


def read_log(limit: int = 500) -> list[dict[str, Any]]:
    path = os.path.join(LOG_DIR, LOG_NAME)
    try:
        with open(path, "rb") as fh:
            size = fh.seek(0, os.SEEK_END)
            fh.seek(max(0, size - _READ_TAIL))
            lines = fh.read(_READ_TAIL).decode("utf-8", "replace").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue   # la primera línea de la cola puede venir cortada
        if isinstance(rec, dict):
            out.append(rec)
    return out
