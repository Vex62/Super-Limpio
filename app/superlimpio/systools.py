"""Acciones del sistema: comandos oficiales de Windows, siempre con confirmación.

Cada acción declara exactamente qué ejecutará. La interfaz muestra el comando
literal al usuario antes de lanzarlo. Las que requieren administrador se lanzan
con el verbo «runas», de modo que Windows muestra además su propio aviso UAC.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import i18n, winapi
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


def _tool(tool_id: str, exe: str, params: str = "", **kw) -> SysTool:
    return SysTool(tool_id, i18n.t(f"systool.{tool_id}.title"), i18n.t(f"systool.{tool_id}.desc"),
                   exe, params, effect=i18n.t(f"systool.{tool_id}.effect"), **kw)


def tools() -> list[SysTool]:
    """Lista de herramientas con los textos en el idioma activo."""
    return [
        _tool("storage", "ms-settings:storagesense", risk=Risk.BAJO),
        _tool("apps", "ms-settings:appsfeatures", risk=Risk.BAJO),
        _tool("taskmgr_startup", "taskmgr.exe", "/0 /startup", risk=Risk.BAJO),
        _tool("cleanmgr", "cleanmgr.exe", risk=Risk.BAJO),
        _tool("restore", "SystemPropertiesProtection.exe", risk=Risk.BAJO),
        _tool("analyze_sxs", "cmd.exe", "/k Dism.exe /Online /Cleanup-Image /AnalyzeComponentStore",
              admin=True, risk=Risk.MEDIO, keep_console=True),
        _tool("clean_sxs", "cmd.exe", "/k Dism.exe /Online /Cleanup-Image /StartComponentCleanup",
              admin=True, risk=Risk.CRITICO, keep_console=True),
        _tool("hiber_off", "cmd.exe", "/k powercfg.exe /hibernate off",
              admin=True, risk=Risk.CRITICO, keep_console=True),
        _tool("hiber_on", "cmd.exe", "/k powercfg.exe /hibernate on",
              admin=True, risk=Risk.ALTO, keep_console=True),
    ]


def run_tool(tool: SysTool) -> tuple[bool, str]:
    verb = "runas" if tool.admin else "open"
    ok, msg = winapi.shell_execute(tool.exe, tool.params or None, verb=verb)
    log_action("herramienta_sistema", tool.command_line, msg, ok=ok, admin=tool.admin)
    return ok, msg
