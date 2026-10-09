"""Programas que arrancan con el sistema (solo lectura).

Super Limpio no modifica el arranque: para desactivar una entrada abre la herramienta
del propio sistema (en Windows, el Administrador de tareas), que es la vía oficial y
reversible. De dónde se lee la lista lo sabe cada plataforma (`plat`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import plat


@dataclass
class StartupItem:
    name: str
    command: str
    location: str
    enabled: bool | None   # None = desconocido
    exe: str = ""

    @property
    def exists(self) -> bool:
        return bool(self.exe) and os.path.exists(self.exe)


def list_startup() -> list[StartupItem]:
    return [StartupItem(**fields) for fields in plat.startup_entries()]


def open_manager() -> tuple[bool, str]:
    """Abre la herramienta del sistema desde la que se activa o desactiva el arranque."""
    return plat.open_startup_manager()
