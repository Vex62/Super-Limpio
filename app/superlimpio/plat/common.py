"""Tipos y constantes que comparten todas las plataformas.

Cada sistema operativo tiene su propio módulo (`windows.py`, `linux.py`) con las mismas
funciones; aquí está lo que devuelven, para que el resto de la aplicación no sepa en
qué sistema corre.
"""

from __future__ import annotations

from dataclasses import dataclass

# Clases de prioridad. Son los valores de Windows; en otros sistemas cada módulo los
# traduce a lo suyo (en Linux, al valor «nice»).
PRIORITY_IDLE = 0x40
PRIORITY_BELOW_NORMAL = 0x4000
PRIORITY_NORMAL = 0x20
PRIORITY_ABOVE_NORMAL = 0x8000
PRIORITY_HIGH = 0x80
PRIORITY_REALTIME = 0x100

# Atributos de archivo de Windows (en otros sistemas `st_file_attributes` no existe y
# las comprobaciones dan siempre falso).
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
CLOUD_ONLY_MASK = FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS


@dataclass
class MemoryStatus:
    total: int
    available: int
    load_pct: int
    commit_total: int
    commit_available: int

    @property
    def used(self) -> int:
        return self.total - self.available


@dataclass
class RawProcess:
    pid: int
    ppid: int
    name: str
    threads: int
    path: str = ""
    working_set: int = 0
    private: int = 0
    cpu_time: float = 0.0  # segundos de CPU acumulados (kernel + usuario)
    accessible: bool = False
    create_time: float = 0.0  # instante de creación: con el PID identifica al proceso sin ambigüedad
    handles: int = 0
    priority: int = 0


@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    title: str


@dataclass
class PerfInfo:
    commit_total: int
    commit_limit: int
    commit_peak: int
    system_cache: int
    kernel_paged: int
    kernel_nonpaged: int
    handles: int
    processes: int
    threads: int


# Funciones que todo módulo de plataforma tiene que ofrecer. `plat/__init__.py` comprueba
# la lista al arrancar: si a una plataforma le falta alguna, se sabe en el acto.
API = (
    # información general
    "is_admin", "list_drives", "memory_status", "performance_info",
    # procesos
    "list_processes", "terminate_process", "process_alive", "set_efficiency", "restore_efficiency",
    "set_priority", "trim_working_set", "list_windows", "close_window",
    # abrir, ejecutar y papelera
    "shell_execute", "open_in_explorer", "recycle_bin_info", "empty_recycle_bin", "send_to_recycle_bin",
    "admin_command", "relaunch_as_admin",
    # datos propios de cada sistema
    "cleaner_categories", "startup_entries", "open_startup_manager", "installed_programs",
    "uninstall_command", "open_apps_settings", "system_tools", "run_system_tool",
    # qué sabe hacer esta plataforma
    "capabilities",
)
