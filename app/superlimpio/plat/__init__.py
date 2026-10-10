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
from typing import Any

from .common import (API, CLOUD_ONLY_MASK, FILE_ATTRIBUTE_OFFLINE, FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS,
                     FILE_ATTRIBUTE_RECALL_ON_OPEN, FILE_ATTRIBUTE_REPARSE_POINT, PRIORITY_ABOVE_NORMAL,
                     PRIORITY_BELOW_NORMAL, PRIORITY_HIGH, PRIORITY_IDLE, PRIORITY_NORMAL, PRIORITY_REALTIME,
                     MemoryStatus, PerfInfo, RawProcess, WindowInfo)

# Cada sistema tiene su rama, y lo que no es ni Windows ni Linux falla aquí, con un mensaje
# claro, en vez de caer en la rama de otro sistema y comportarse a medias (macOS, BSD…).
# Se pregunta por sys.platform porque es lo único que entienden mypy y pyright.
if sys.platform == "win32":
    NAME = "windows"
    from . import windows as _backend
    from .windows import (
        acquire_instance_lock, capabilities, cleaner_categories, close_window, config_dir, empty_recycle_bin,
        helper_command, installed_programs, is_admin, list_drives, list_processes, list_windows,
        memory_status, open_apps_settings, open_in_explorer, open_startup_manager, performance_info,
        prepare_process, process_alive, recycle_bin_info, reopen_program, restore_efficiency, run_elevated,
        run_system_tool, send_to_recycle_bin, set_efficiency, set_priority, shell_execute, startup_entries,
        state_dir, system_tools, terminate_process, trim_working_set, uninstall_command)
elif sys.platform.startswith("linux"):
    NAME = "linux"
    from . import linux as _backend
    from .linux import (
        acquire_instance_lock, capabilities, cleaner_categories, close_window, config_dir, empty_recycle_bin,
        helper_command, installed_programs, is_admin, list_drives, list_processes, list_windows,
        memory_status, open_apps_settings, open_in_explorer, open_startup_manager, performance_info,
        prepare_process, process_alive, recycle_bin_info, reopen_program, restore_efficiency, run_elevated,
        run_system_tool, send_to_recycle_bin, set_efficiency, set_priority, shell_execute, startup_entries,
        state_dir, system_tools, terminate_process, trim_working_set, uninstall_command)
else:
    raise ImportError(f"Super Limpio no admite esta plataforma: {sys.platform}")

IS_WINDOWS = NAME == "windows"
IS_LINUX = NAME == "linux"

_missing = [name for name in API if not hasattr(_backend, name)]
if _missing:  # pragma: no cover - fallo de programación, no de uso
    raise ImportError(f"plat.{NAME} no implementa: {', '.join(_missing)}")


class _Knowledge:
    """Acceso al módulo de conocimiento activo (`know.PROTECTED_PROCESSES`, `know.classify_path`...)."""

    def __init__(self) -> None:
        self.name = ""
        self._module: Any = None

    def use(self, name: str) -> None:
        self._module = importlib.import_module(f".{name}_know", __name__)
        self.name = name

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._module, attr)


know = _Knowledge()
know.use(NAME)
# El del sistema real: lo usan las protecciones de borrado, que nunca deben seguir a un test.
native_know = importlib.import_module(f".{NAME}_know", __name__)


def set_knowledge(name: str) -> None:
    """Cambia las reglas de procesos y rutas que usa la lógica («windows» o «linux»)."""
    know.use(name)


__all__ = [
    "API", "CLOUD_ONLY_MASK", "FILE_ATTRIBUTE_OFFLINE", "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS",
    "FILE_ATTRIBUTE_RECALL_ON_OPEN", "FILE_ATTRIBUTE_REPARSE_POINT", "IS_LINUX", "IS_WINDOWS", "NAME",
    "PRIORITY_ABOVE_NORMAL", "PRIORITY_BELOW_NORMAL", "PRIORITY_HIGH", "PRIORITY_IDLE", "PRIORITY_NORMAL",
    "PRIORITY_REALTIME", "MemoryStatus", "PerfInfo", "RawProcess", "WindowInfo",
    "acquire_instance_lock", "capabilities", "cleaner_categories", "close_window", "config_dir",
    "empty_recycle_bin", "helper_command", "installed_programs", "is_admin", "know", "list_drives",
    "list_processes", "list_windows", "memory_status", "native_know", "open_apps_settings", "open_in_explorer",
    "open_startup_manager", "performance_info", "prepare_process", "process_alive", "recycle_bin_info",
    "reopen_program", "restore_efficiency", "run_elevated", "run_system_tool", "send_to_recycle_bin",
    "set_efficiency", "set_knowledge", "set_priority", "shell_execute", "startup_entries", "state_dir",
    "system_tools", "terminate_process", "trim_working_set", "uninstall_command",
]
