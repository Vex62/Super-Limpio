"""Programas instalados y su desinstalación.

La desinstalación SIEMPRE usa la vía oficial del sistema: en Windows, el desinstalador
del propio programa (el mismo que lanza Configuración > Aplicaciones); en Linux, el
gestor de paquetes. La app no borra carpetas de programas por su cuenta.

De dónde sale la lista y qué comando desinstala lo sabe cada plataforma (`plat`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import i18n, plat
from .plat.windows import split_command  # noqa: F401 - forma parte de la interfaz de este módulo
from .util import expand


@dataclass
class Program:
    name: str
    publisher: str = ""
    version: str = ""
    estimated_size: int = 0        # bytes (dato declarado por el instalador)
    real_size: int | None = None   # bytes medidos en disco (bajo demanda)
    install_date: str = ""         # aaaa-mm-dd (ISO, ordenable en cualquier idioma)
    install_location: str = ""
    uninstall_string: str = ""
    quiet_uninstall_string: str = ""
    modify_path: str = ""
    msi_code: str = ""             # {GUID} si es Windows Installer
    scope: str = ""                # token interno: "machine64", "user", "deb", "flatpak"...
    reg_key: str = ""              # clave del registro (Windows) o identificador del paquete
    display_icon: str = ""

    @property
    def best_size(self) -> int:
        return self.real_size if self.real_size is not None else self.estimated_size

    @property
    def scope_label(self) -> str:
        return i18n.t(f"programs.scope.{self.scope}") if self.scope else ""

    @property
    def location_guess(self) -> str:
        """Carpeta de instalación declarada o deducida del icono/desinstalador."""
        if self.install_location and os.path.isdir(expand(self.install_location.strip('"'))):
            return expand(self.install_location.strip('"'))
        for src in (self.display_icon, self.uninstall_string):
            exe, _ = split_command(src) if src else ("", "")
            exe = exe.split(",")[0]
            if exe and os.path.isabs(exe):
                d = os.path.dirname(exe)
                low = d.lower()
                # Evita devolver carpetas genéricas compartidas
                if os.path.isdir(d) and not low.endswith(("\\system32", "\\syswow64", "\\windows",
                                                          "\\installer", "\\package cache")) \
                        and "\\package cache\\" not in low and "\\installer\\" not in low:
                    return d
        return ""


def list_installed() -> list[Program]:
    return [Program(**fields) for fields in plat.installed_programs()]


@dataclass
class UninstallPlan:
    exe: str
    params: str
    display: str        # texto exacto que se mostrará al usuario
    warnings: list[str]
    critical: bool = False   # True si el desinstalador usa un intérprete de comandos


def build_uninstall_plan(p: Program, command=None) -> UninstallPlan:
    """Qué se va a ejecutar para desinstalar. «command» permite fijar la plataforma (tests)."""
    exe, params, warnings, critical, *shown = (command or plat.uninstall_command)(p)
    display = shown[0] if shown else (f'"{exe}" {params}'.strip() if exe else "")
    return UninstallPlan(exe, params, display, warnings, critical)
