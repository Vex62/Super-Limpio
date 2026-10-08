"""Acciones del sistema: comandos oficiales de Windows, siempre con confirmación.

Cada acción declara exactamente qué ejecutará. La interfaz muestra el comando
literal al usuario antes de lanzarlo. Las que requieren administrador se lanzan
con el verbo «runas», de modo que Windows muestra además su propio aviso UAC.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import winapi
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


TOOLS: list[SysTool] = [
    SysTool("storage", "Abrir Almacenamiento de Windows",
            "Vista oficial de Configuración > Sistema > Almacenamiento.",
            "ms-settings:storagesense", risk=Risk.BAJO,
            effect="Solo abre Configuración."),
    SysTool("apps", "Abrir Aplicaciones instaladas",
            "Incluye apps de Microsoft Store, que no siempre aparecen en el registro clásico.",
            "ms-settings:appsfeatures", risk=Risk.BAJO, effect="Solo abre Configuración."),
    SysTool("taskmgr_startup", "Administrar programas de inicio",
            "Abre el Administrador de tareas en la pestaña Inicio para desactivar entradas de forma reversible.",
            "taskmgr.exe", "/0 /startup", risk=Risk.BAJO, effect="Solo abre el Administrador de tareas."),
    SysTool("cleanmgr", "Liberador de espacio de Windows",
            "Herramienta clásica de Microsoft (incluye «Limpiar archivos del sistema»).",
            "cleanmgr.exe", risk=Risk.BAJO, effect="Abre la herramienta; no borra nada hasta que la uses."),
    SysTool("restore", "Crear punto de restauración",
            "Abre Protección del sistema. Recomendado antes de desinstalar en masa.",
            "SystemPropertiesProtection.exe", risk=Risk.BAJO, effect="Solo abre la ventana."),
    SysTool("analyze_sxs", "Analizar almacén de componentes (WinSxS)",
            "Informa cuánto se puede recuperar de WinSxS. No modifica nada.",
            "cmd.exe", "/k Dism.exe /Online /Cleanup-Image /AnalyzeComponentStore",
            admin=True, risk=Risk.MEDIO, keep_console=True,
            effect="Ejecuta DISM en modo análisis (solo lectura) en una consola visible."),
    SysTool("clean_sxs", "Limpiar componentes de Windows (WinSxS)",
            "Elimina versiones antiguas de componentes reemplazados por actualizaciones. "
            "Tras esto no podrás desinstalar esas actualizaciones antiguas.",
            "cmd.exe", "/k Dism.exe /Online /Cleanup-Image /StartComponentCleanup",
            admin=True, risk=Risk.CRITICO, keep_console=True,
            effect="DISM borra componentes antiguos. Puede tardar varios minutos. Irreversible."),
    SysTool("hiber_off", "Desactivar hibernación (borra hiberfil.sys)",
            "Libera tantos GB como ~40 % de tu RAM. Desactiva también el «Inicio rápido».",
            "cmd.exe", "/k powercfg.exe /hibernate off",
            admin=True, risk=Risk.CRITICO, keep_console=True,
            effect="Desactiva la hibernación. Reversible con «powercfg /hibernate on»."),
    SysTool("hiber_on", "Reactivar hibernación",
            "Vuelve a crear hiberfil.sys y habilita el Inicio rápido.",
            "cmd.exe", "/k powercfg.exe /hibernate on",
            admin=True, risk=Risk.ALTO, keep_console=True, effect="Reactiva la hibernación."),
]


def run_tool(tool: SysTool) -> tuple[bool, str]:
    verb = "runas" if tool.admin else "open"
    ok, msg = winapi.shell_execute(tool.exe, tool.params or None, verb=verb)
    log_action("herramienta_sistema", tool.command_line, msg, ok=ok, admin=tool.admin)
    return ok, msg
