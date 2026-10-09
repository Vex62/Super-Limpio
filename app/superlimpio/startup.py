"""Programas que arrancan con Windows (solo lectura).

Super Limpio no modifica el arranque: para desactivar una entrada abre el
Administrador de tareas (pestaña Inicio), que es la vía oficial y reversible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import i18n
from .programs import split_command
from .util import IS_WINDOWS, expand

if IS_WINDOWS:
    import winreg


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


_APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


def _approved_map(hive, sub: str, view: int) -> dict[str, bool]:
    out: dict[str, bool] = {}
    try:
        with winreg.OpenKey(hive, f"{_APPROVED}\\{sub}", 0, winreg.KEY_READ | view) as k:
            i = 0
            while True:
                try:
                    name, data, _t = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if isinstance(data, bytes) and data:
                    out[name.lower()] = data[0] in (0x02, 0x06)  # pares = activado
    except OSError:
        pass
    return out


def list_startup() -> list[StartupItem]:
    if not IS_WINDOWS:
        return []
    items: list[StartupItem] = []
    reg_sources = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
         i18n.t("startup.src.hkcu_run"), "Run"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", 0,
         i18n.t("startup.src.hkcu_runonce"), None),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",
         winreg.KEY_WOW64_64KEY, i18n.t("startup.src.hklm_run"), "Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",
         winreg.KEY_WOW64_32KEY, i18n.t("startup.src.hklm_run32"), "Run32"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
         winreg.KEY_WOW64_64KEY, i18n.t("startup.src.hklm_runonce"), None),
    ]
    for hive, path, view, label, approved_sub in reg_sources:
        approved = _approved_map(hive, approved_sub, view) if approved_sub else {}
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as k:
                i = 0
                while True:
                    try:
                        name, data, _t = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    cmd = str(data)
                    exe, _ = split_command(expand(cmd) if "%" in cmd else cmd)
                    items.append(StartupItem(name or i18n.t("startup.default_name"), cmd, label,
                                             approved.get(name.lower(), True) if approved_sub else None, exe))
        except OSError:
            continue

    folders = [
        (expand(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"),
         i18n.t("startup.src.folder_user"), winreg.HKEY_CURRENT_USER),
        (expand(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\StartUp"),
         i18n.t("startup.src.folder_all"), winreg.HKEY_LOCAL_MACHINE),
    ]
    for folder, label, hive in folders:
        approved = _approved_map(hive, "StartupFolder", 0)
        try:
            for entry in os.scandir(folder):
                if entry.name.lower() == "desktop.ini":
                    continue
                items.append(StartupItem(entry.name, entry.path, label,
                                         approved.get(entry.name.lower(), True), entry.path))
        except OSError:
            continue
    return items
