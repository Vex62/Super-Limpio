"""Acciones del sistema: comandos oficiales del sistema operativo, siempre con confirmación.

Cada acción declara exactamente qué ejecutará. La interfaz muestra el comando literal
al usuario antes de lanzarlo. Las que requieren administrador piden la elevación por
la vía del propio sistema (el aviso UAC en Windows, la contraseña de sudo en Linux).

Qué herramientas hay y cómo se lanzan lo sabe cada plataforma (`plat`).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import i18n, plat
from .safety import Risk, log_action


@dataclass
class SysTool:
    id: str
    title: str
    description: str
    exe: str
    params: str = ""
    admin: bool = False
    risk: Risk = Risk.BAJO
    keep_console: bool = False   # muestra la salida en una consola que no se cierra
    effect: str = ""             # qué pasará, en lenguaje llano

    @property
    def command_line(self) -> str:
        return f"{self.exe} {self.params}".strip()


def tools() -> list[SysTool]:
    """Lista de herramientas con los textos en el idioma activo."""
    out = []
    for spec in plat.system_tools():
        spec = dict(spec)
        tool_id = spec.pop("id")
        spec["risk"] = Risk(spec.get("risk", int(Risk.BAJO)))
        out.append(SysTool(tool_id, i18n.t(f"systool.{tool_id}.title"), i18n.t(f"systool.{tool_id}.desc"),
                           effect=i18n.t(f"systool.{tool_id}.effect"), **spec))
    return out


def run_tool(tool: SysTool) -> tuple[bool, str]:
    ok, msg = plat.run_system_tool(tool.exe, tool.params, tool.admin, tool.keep_console)
    log_action("herramienta_sistema", tool.command_line, msg, ok=ok, admin=tool.admin)
    return ok, msg
