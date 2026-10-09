"""Capa de plataforma: todo lo que depende del sistema operativo pasa por aquí.

El resto de la aplicación hace `from . import plat` y llama a `plat.list_processes()`,
`plat.send_to_recycle_bin()`... sin saber en qué sistema corre. Hay dos piezas por
sistema:

  * `windows.py` / `linux.py`       — las llamadas al sistema y sus listas de datos
                                       (categorías de limpieza, arranque, programas...).
  * `windows_know.py` / `linux_know.py` — lo que hay que SABER del sistema: qué procesos y
                                       carpetas son vitales, cuáles se protegen, cómo se
                                       agrupan los programas. Es lógica pura, sin llamadas
                                       al sistema, así que se prueba en cualquier equipo.

`know` apunta al conocimiento del sistema en uso. Los tests pueden cambiarlo con
`set_knowledge("windows")` para probar las reglas de un sistema desde otro.
"""

from __future__ import annotations

import importlib
import sys

from .common import *  # noqa: F401,F403 - tipos y constantes comunes
from .common import API

if sys.platform == "win32":
    NAME = "windows"
elif sys.platform.startswith("linux"):
    NAME = "linux"
else:
    NAME = "linux"   # otros Unix: se intenta con lo de Linux; lo que no exista da valores neutros

IS_WINDOWS = NAME == "windows"
IS_LINUX = NAME == "linux"

_backend = importlib.import_module(f".{NAME}", __name__)
_missing = [name for name in API if not hasattr(_backend, name)]
if _missing:  # pragma: no cover - fallo de programación, no de uso
    raise ImportError(f"plat.{NAME} no implementa: {', '.join(_missing)}")
globals().update({name: getattr(_backend, name) for name in API})


class _Knowledge:
    """Acceso al módulo de conocimiento activo (`know.PROTECTED_PROCESSES`, `know.classify_path`...)."""

    def __init__(self) -> None:
        self.name = ""
        self._module = None

    def use(self, name: str) -> None:
        self._module = importlib.import_module(f".{name}_know", __name__)
        self.name = name

    def __getattr__(self, attr: str):
        return getattr(self._module, attr)


know = _Knowledge()
know.use(NAME)
# El del sistema real: lo usan las protecciones de borrado, que nunca deben seguir a un test.
native_know = importlib.import_module(f".{NAME}_know", __name__)


def set_knowledge(name: str) -> None:
    """Cambia las reglas de procesos y rutas que usa la lógica («windows» o «linux»)."""
    know.use(name)
