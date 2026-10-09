"""Programas instalados (lectura del registro, solo lectura) y desinstalación.

La desinstalación SIEMPRE usa el desinstalador oficial del propio programa
(el mismo que lanza Configuración > Aplicaciones). La app no borra carpetas
de programas ni claves del registro por su cuenta.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass

from . import i18n
from .util import IS_WINDOWS, expand

if IS_WINDOWS:
    import winreg

UNINSTALL_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


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
    scope: str = ""                # token interno: "machine64", "machine32", "user"
    reg_key: str = ""
    display_icon: str = ""

    @property
    def best_size(self) -> int:
        return self.real_size if self.real_size is not None else self.estimated_size

    @property
    def scope_label(self) -> str:
        return i18n.t({"machine64": "programs.scope.machine64", "machine32": "programs.scope.machine32",
                       "user": "programs.scope.user"}.get(self.scope, self.scope))

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


def _read_value(key, name: str):
    try:
        val, _typ = winreg.QueryValueEx(key, name)
        return val
    except OSError:
        return None


def _fmt_install_date(raw) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if re.fullmatch(r"\d{8}", s):
        try:
            return _dt.datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return s
    return s


def list_installed() -> list[Program]:
    if not IS_WINDOWS:
        return []
    sources = [
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY, "machine64", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY, "machine32", "HKLM"),
        (winreg.HKEY_CURRENT_USER, 0, "user", "HKCU"),
    ]
    seen: set[tuple[str, str]] = set()
    programs: list[Program] = []
    for hive, view, scope, hive_name in sources:
        try:
            root = winreg.OpenKey(hive, UNINSTALL_SUBKEY, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub, 0, winreg.KEY_READ | view) as k:
                        name = _read_value(k, "DisplayName")
                        if not name:
                            continue
                        if _read_value(k, "SystemComponent") == 1:
                            continue
                        if _read_value(k, "ParentKeyName") or _read_value(k, "ReleaseType") in (
                                "Update", "Hotfix", "Security Update"):
                            continue
                        uninstall = _read_value(k, "UninstallString") or ""
                        is_msi = _read_value(k, "WindowsInstaller") == 1
                        if not uninstall and not is_msi:
                            continue
                        version = str(_read_value(k, "DisplayVersion") or "")
                        dedup = (name.strip().lower(), version)
                        if dedup in seen:
                            continue
                        seen.add(dedup)
                        size_kb = _read_value(k, "EstimatedSize")
                        msi_code = sub if (is_msi and re.fullmatch(r"\{[0-9A-Fa-f\-]{36}\}", sub)) else ""
                        programs.append(Program(
                            name=name.strip(),
                            publisher=str(_read_value(k, "Publisher") or "").strip(),
                            version=version,
                            estimated_size=int(size_kb) * 1024 if isinstance(size_kb, int) else 0,
                            install_date=_fmt_install_date(_read_value(k, "InstallDate")),
                            install_location=str(_read_value(k, "InstallLocation") or ""),
                            uninstall_string=uninstall,
                            quiet_uninstall_string=str(_read_value(k, "QuietUninstallString") or ""),
                            modify_path=str(_read_value(k, "ModifyPath") or ""),
                            msi_code=msi_code,
                            scope=scope,
                            reg_key=f"{hive_name}\\{UNINSTALL_SUBKEY}\\{sub}",
                            display_icon=str(_read_value(k, "DisplayIcon") or ""),
                        ))
                except OSError:
                    continue
    programs.sort(key=lambda p: p.name.lower())
    return programs


# -------------------------------------------------------------------------
# Interpretación segura de la línea de desinstalación
# -------------------------------------------------------------------------

def split_command(cmd: str) -> tuple[str, str]:
    """Separa «ejecutable» y «parámetros» de una UninstallString sin usar un shell.

    Admite: "C:\\ruta con espacios\\unins000.exe" /SILENT
            C:\\ruta con espacios\\uninstall.exe --flag   (sin comillas)
            MsiExec.exe /I{GUID}
    """
    cmd = (cmd or "").strip()
    if not cmd:
        return "", ""
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end == -1:
            return cmd.strip('"'), ""
        return expand(cmd[1:end]) if "%" in cmd[1:end] else cmd[1:end], cmd[end + 1:].strip()
    # Sin comillas: buscar el final del ejecutable (.exe/.cmd/.bat/.com)
    m = re.match(r"^(.+?\.(?:exe|com|bat|cmd))(?=\s|$)(.*)$", cmd, re.IGNORECASE)
    if m:
        exe = m.group(1)
        if "%" in exe:
            exe = expand(exe)
        return exe, m.group(2).strip()
    parts = cmd.split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


@dataclass
class UninstallPlan:
    exe: str
    params: str
    display: str        # texto exacto que se mostrará al usuario
    warnings: list[str]
    critical: bool = False   # True si el desinstalador usa un intérprete de comandos


def build_uninstall_plan(p: Program) -> UninstallPlan:
    warnings: list[str] = []
    critical = False
    if p.msi_code:
        # Windows Installer: /X = desinstalar (nunca /I, que reinstala/modifica)
        exe, params = "msiexec.exe", f"/x {p.msi_code}"
    else:
        exe, params = split_command(p.uninstall_string)
        if os.path.basename(exe).lower() == "msiexec.exe":
            params = re.sub(r"(?i)/I(\s*\{)", r"/X\1", params)
    base = os.path.basename(exe).lower()
    if os.path.isabs(exe) and not os.path.exists(exe):
        warnings.append(i18n.t("programs.warn.missing"))
    if base in ("cmd.exe", "powershell.exe", "pwsh.exe", "wscript.exe", "cscript.exe", "rundll32.exe"):
        warnings.append(i18n.t("programs.warn.interpreter", base=base))
        critical = True
    if p.scope.startswith("machine"):
        warnings.append(i18n.t("programs.warn.machine"))
    display = f'"{exe}" {params}'.strip()
    return UninstallPlan(exe, params, display, warnings, critical)
