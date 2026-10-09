"""Modo de recuperación: detecta arranques fallidos y repara el estado de la app.

Cómo funciona:
  * Justo antes de construir la ventana se escribe una «marca de arranque». Cuando la
    interfaz lleva unos segundos en pie, la marca se borra. Si en el siguiente arranque
    la marca sigue ahí, el inicio anterior terminó mal (crash o cierre forzado durante
    el arranque): se repara automáticamente antes de volver a intentarlo.
  * Reparar = volver la configuración a valores por defecto (apartando la dañada) y
    limpiar cachés de bytecode regenerables. No se toca ningún dato del usuario ni los
    registros de acciones.
  * El borrado de archivos y los registros ya son robustos de por sí: la escritura de
    la configuración es atómica (ver config.py) y el log se escribe línea a línea, así
    que un corte a mitad nunca corrompe lo anterior.
"""

from __future__ import annotations

import os
import shutil

from . import config
from .util import APP_ROOT

_FLAG_NAME = "superlimpio.starting"


def _flag_path() -> str:
    return os.path.join(config.state_dir(), _FLAG_NAME)


def pending_recovery() -> bool:
    """True si el arranque anterior no llegó a completarse (marca sin borrar)."""
    return os.path.exists(_flag_path())


def mark_starting() -> None:
    try:
        with open(_flag_path(), "w", encoding="ascii") as fh:
            fh.write("1")
    except OSError:
        pass


def mark_started() -> None:
    try:
        os.remove(_flag_path())
    except OSError:
        pass


def _clear_bytecode_caches() -> int:
    """Borra cachés de bytecode regenerables (__pycache__ y runtime/_pycache).

    NUNCA borra .pyc sueltos: en la distribución sin fuente esos .pyc SON el programa y
    no viven en __pycache__, así que quedan intactos."""
    removed = 0
    pycache_prefix = os.path.join(str(APP_ROOT), "runtime", "_pycache")
    if os.path.isdir(pycache_prefix):
        shutil.rmtree(pycache_prefix, ignore_errors=True)
        removed += 1
    app_dir = os.path.join(str(APP_ROOT), "app")
    for folder, dirs, _names in os.walk(app_dir):
        if os.path.basename(folder) == "__pycache__":
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
            dirs[:] = []
    return removed


def repair(reason: str) -> list[str]:
    """Repara el estado tras un error. Devuelve la lista de acciones realizadas."""
    actions: list[str] = []
    config.reset_to_defaults(quarantine=True)
    actions.append("configuración restablecida")
    caches = _clear_bytecode_caches()
    if caches:
        actions.append(f"{caches} cachés de bytecode limpiadas")
    mark_started()  # retira la marca de arranque pendiente
    actions.append(f"motivo: {reason}")
    return actions
