"""Importancia de un proceso o de un archivo para el sistema: qué es y qué pasa si se toca.

`safety` decide si algo se PUEDE borrar o finalizar; este módulo lo explica. A cada
proceso y a cada ruta le pone un nivel (normal, precaución, importante o vital), una
frase que dice qué es y otra con el riesgo de cerrarlo o borrarlo. Se usa para avisar
en «Memoria y procesos», en el análisis de «Optimizar» y en el «Analizador de disco».

Solo contiene lógica (sin interfaz ni llamadas al sistema), para poder probarla con tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum

from . import i18n
from .safety import PROTECTED_PROCESSES, SENSITIVE_PROCESSES, check_deletable
from .util import APP_ROOT


class Level(IntEnum):
    NORMAL = 0       # programa o archivo corriente: no afecta al sistema
    CAUTION = 1      # se puede cerrar o borrar, pero algo deja de funcionar o se pierde
    IMPORTANT = 2    # componente de Windows, de seguridad o de un programa instalado
    VITAL = 3        # sin él Windows se detiene o no arranca

    @property
    def label(self) -> str:
        return i18n.t(f"crit.level.{int(self)}")


@dataclass(frozen=True)
class Assessment:
    level: Level
    what: str        # qué es
    risk: str        # qué pasa si se cierra o se borra
    kind: str = ""   # «self» = la propia aplicación
    system: bool = False   # es del propio sistema y borrarlo daña a Windows (solo rutas)

    @property
    def label(self) -> str:
        return self.level.label

    @property
    def text(self) -> str:
        return f"{self.what} {self.risk}".strip()


# =========================================================================
# Procesos
# =========================================================================

# Seguridad y anti-trampas: cerrarlos desprotege el equipo o provoca expulsiones en
# juegos en línea. «Optimizar» nunca los propone.
SECURITY_PROCESSES = {
    "securityhealthsystray.exe", "smartscreen.exe", "mbam.exe", "mbamservice.exe", "mbamtray.exe",
    "avp.exe", "avpui.exe", "avgsvc.exe", "avgui.exe", "avastsvc.exe", "avastui.exe", "ekrn.exe",
    "egui.exe", "bdagent.exe", "bdservicehost.exe", "vsserv.exe", "mcshield.exe", "mcuicnt.exe",
    "nortonsecurity.exe", "sophosui.exe", "savservice.exe", "wrsa.exe", "psanhost.exe",
    "easyanticheat.exe", "easyanticheat_eos.exe", "beservice.exe", "beservice_x64.exe", "vgc.exe",
    "vgtray.exe", "faceit.exe", "faceitclient.exe",
}
SECURITY_PATHS = ("\\windows defender", "\\microsoft defender")

_V, _I, _C = Level.VITAL, Level.IMPORTANT, Level.CAUTION

# nombre -> (nivel, clave de «qué es», clave del riesgo)
_PROCESSES: dict[str, tuple[Level, str, str]] = {
    "system": (_V, "crit.proc.system", "crit.risk.vital"),
    "system idle process": (_V, "crit.proc.idle", "crit.risk.vital"),
    "registry": (_V, "crit.proc.registry", "crit.risk.vital"),
    "memory compression": (_V, "crit.proc.memcompression", "crit.risk.vital"),
    "secure system": (_V, "crit.proc.secure", "crit.risk.vital"),
    "smss.exe": (_V, "crit.proc.smss", "crit.risk.vital"),
    "csrss.exe": (_V, "crit.proc.csrss", "crit.risk.vital"),
    "wininit.exe": (_V, "crit.proc.wininit", "crit.risk.vital"),
    "services.exe": (_V, "crit.proc.services", "crit.risk.vital"),
    "lsass.exe": (_V, "crit.proc.lsass", "crit.risk.vital"),
    "lsaiso.exe": (_V, "crit.proc.lsaiso", "crit.risk.vital"),
    "winlogon.exe": (_V, "crit.proc.winlogon", "crit.risk.session"),
    "svchost.exe": (_V, "crit.proc.svchost", "crit.risk.svchost"),
    "dwm.exe": (_V, "crit.proc.dwm", "crit.risk.session"),
    "fontdrvhost.exe": (_V, "crit.proc.fontdrvhost", "crit.risk.session"),
    "msmpeng.exe": (_I, "crit.proc.defender", "crit.risk.security"),
    "nissrv.exe": (_I, "crit.proc.defender_net", "crit.risk.security"),
    "securityhealthservice.exe": (_I, "crit.proc.security_center", "crit.risk.security"),
    "sgrmbroker.exe": (_I, "crit.proc.sgrm", "crit.risk.security"),
    "audiodg.exe": (_I, "crit.proc.audiodg", "crit.risk.audio"),
    "spoolsv.exe": (_I, "crit.proc.spooler", "crit.risk.print"),
    "wudfhost.exe": (_I, "crit.proc.wudfhost", "crit.risk.driver"),
    "trustedinstaller.exe": (_I, "crit.proc.update", "crit.risk.update"),
    "tiworker.exe": (_I, "crit.proc.update", "crit.risk.update"),
    "mousocoreworker.exe": (_I, "crit.proc.update", "crit.risk.update"),
    "wuauclt.exe": (_I, "crit.proc.update", "crit.risk.update"),
    "msiexec.exe": (_I, "crit.proc.msiexec", "crit.risk.update"),
    "explorer.exe": (_C, "crit.proc.explorer", "crit.risk.shell"),
    "sihost.exe": (_C, "crit.proc.sihost", "crit.risk.shell"),
    "ctfmon.exe": (_C, "crit.proc.ctfmon", "crit.risk.input"),
    "textinputhost.exe": (_C, "crit.proc.ctfmon", "crit.risk.input"),
    "searchhost.exe": (_C, "crit.proc.search", "crit.risk.relaunch"),
    "searchindexer.exe": (_C, "crit.proc.indexer", "crit.risk.relaunch"),
    "startmenuexperiencehost.exe": (_C, "crit.proc.startmenu", "crit.risk.relaunch"),
    "shellexperiencehost.exe": (_C, "crit.proc.shellexp", "crit.risk.relaunch"),
    "taskhostw.exe": (_C, "crit.proc.taskhost", "crit.risk.relaunch"),
    "runtimebroker.exe": (_C, "crit.proc.runtimebroker", "crit.risk.relaunch"),
    "applicationframehost.exe": (_C, "crit.proc.appframe", "crit.risk.store_apps"),
    "dllhost.exe": (_C, "crit.proc.dllhost", "crit.risk.relaunch"),
    "conhost.exe": (_C, "crit.proc.conhost", "crit.risk.console"),
    "wmiprvse.exe": (_C, "crit.proc.wmi", "crit.risk.relaunch"),
    "dashost.exe": (_C, "crit.proc.dashost", "crit.risk.driver"),
    "wlanext.exe": (_C, "crit.proc.wlan", "crit.risk.network"),
    "vmmem": (_C, "crit.proc.vmmem", "crit.risk.vm"),
    "vmmemwsl": (_C, "crit.proc.vmmem", "crit.risk.vm"),
    "vmwp.exe": (_C, "crit.proc.vmmem", "crit.risk.vm"),
    "vmcompute.exe": (_C, "crit.proc.vmmem", "crit.risk.vm"),
}

# Programas de Windows que abre el propio usuario: viven en la carpeta de Windows, pero
# cerrarlos es tan inocuo como cerrar cualquier otro programa.
_WINDOWS_TOOLS = {
    "notepad.exe", "cmd.exe", "powershell.exe", "powershell_ise.exe", "taskmgr.exe", "mspaint.exe",
    "regedit.exe", "mmc.exe", "control.exe", "snippingtool.exe", "calc.exe", "wordpad.exe", "write.exe",
    "charmap.exe", "osk.exe", "magnify.exe", "perfmon.exe", "resmon.exe", "cleanmgr.exe", "dfrgui.exe",
    "msinfo32.exe", "winver.exe", "openconsole.exe", "mstsc.exe", "eventvwr.exe", "msconfig.exe",
    "systemsettings.exe", "wscript.exe", "cscript.exe", "rundll32.exe",
}


def _nk(path: str) -> str:
    """Clave de comparación de rutas de Windows, sin tocar el disco."""
    return path.replace("/", "\\").rstrip("\\").lower()


def _under(key: str, folder: str) -> bool:
    return bool(folder) and (key == folder or key.startswith(folder + "\\"))


def _a(level: Level, what: str, risk: str, kind: str = "", **kw) -> Assessment:
    return Assessment(level, i18n.t(what, **kw), i18n.t(risk), kind)


def assess_process(name: str, path: str = "", pid: int = -1, accessible: bool = True,
                   service: bool = False, windir: str | None = None,
                   self_pid: int | None = None) -> Assessment:
    """Qué es un proceso y qué pasa si se finaliza."""
    n = name.lower()
    if pid >= 0 and pid == (os.getpid() if self_pid is None else self_pid):
        return _a(Level.NORMAL, "crit.proc.self", "crit.risk.self", kind="self")
    if pid in (0, 4):
        return _a(Level.VITAL, "crit.proc.system", "crit.risk.vital")
    known = _PROCESSES.get(n)
    if known:
        return _a(*known)
    if n in PROTECTED_PROCESSES:
        return _a(Level.VITAL, "crit.proc.essential", "crit.risk.vital")
    if n in SENSITIVE_PROCESSES:
        return _a(Level.CAUTION, "crit.proc.shell", "crit.risk.shell")
    key = _nk(path)
    if n in SECURITY_PROCESSES or any(h in key for h in SECURITY_PATHS):
        return _a(Level.IMPORTANT, "crit.proc.security", "crit.risk.security")
    windir_key = _nk(windir if windir is not None else os.environ.get("WINDIR", r"C:\Windows"))
    in_windows = bool(key) and _under(key, windir_key)
    if in_windows and n in _WINDOWS_TOOLS and not service:
        return _a(Level.NORMAL, "crit.proc.windows_tool", "crit.risk.normal")
    if service:
        if in_windows or not key:
            return _a(Level.IMPORTANT, "crit.proc.windows_service", "crit.risk.service")
        return _a(Level.CAUTION, "crit.proc.app_service", "crit.risk.service")
    if in_windows:
        return _a(Level.IMPORTANT, "crit.proc.windows_component", "crit.risk.component")
    if not key and not accessible:   # no se sabe qué es: se avisa, sin darlo por parte de Windows
        return _a(Level.CAUTION, "crit.proc.no_access", "crit.risk.unknown")
    return _a(Level.NORMAL, "crit.proc.normal", "crit.risk.normal")


# =========================================================================
# Archivos y carpetas
# =========================================================================

_ROOT_ITEMS = {
    "pagefile.sys": (_I, "crit.path.pagefile", "crit.prisk.managed"),
    "hiberfil.sys": (_I, "crit.path.hiberfil", "crit.prisk.managed"),
    "swapfile.sys": (_I, "crit.path.swapfile", "crit.prisk.managed"),
    "bootmgr": (_V, "crit.path.boot", "crit.prisk.vital"),
    "bootnxt": (_V, "crit.path.boot", "crit.prisk.vital"),
    "boot": (_V, "crit.path.boot", "crit.prisk.vital"),
    "efi": (_V, "crit.path.boot", "crit.prisk.vital"),
    "recovery": (_I, "crit.path.recovery", "crit.prisk.important"),
    "$winreagent": (_I, "crit.path.recovery", "crit.prisk.important"),
    "dumpstack.log.tmp": (_I, "crit.path.dumpstack", "crit.prisk.managed"),
}
_ROOT_DIRS = {"boot", "efi", "recovery", "$winreagent"}   # estos cuentan con todo su contenido
_ANY_DRIVE_ITEMS = {
    "system volume information": (_I, "crit.path.restore_points", "crit.prisk.important"),
    "$recycle.bin": (_I, "crit.path.recycle_bin", "crit.prisk.recycle_bin"),
}

# Dentro de la carpeta de Windows: (subcarpeta, nivel, qué es, riesgo). Gana la primera.
_WINDOWS_ITEMS = (
    ("system32\\config", _V, "crit.path.registry", "crit.prisk.vital"),
    ("system32\\drivers", _V, "crit.path.drivers", "crit.prisk.vital"),
    ("system32", _V, "crit.path.system32", "crit.prisk.vital"),
    ("syswow64", _V, "crit.path.system32", "crit.prisk.vital"),
    ("winsxs", _V, "crit.path.winsxs", "crit.prisk.winsxs"),
    ("installer", _I, "crit.path.installer", "crit.prisk.important"),
    ("softwaredistribution\\download", _C, "crit.path.update_cache", "crit.prisk.regen"),
    ("softwaredistribution", _I, "crit.path.update_db", "crit.prisk.important"),
    ("temp", _C, "crit.path.windows_temp", "crit.prisk.regen"),
    ("prefetch", _C, "crit.path.prefetch", "crit.prisk.regen"),
    ("logs", _C, "crit.path.windows_logs", "crit.prisk.regen"),
    ("minidump", _C, "crit.path.dumps", "crit.prisk.regen"),
    ("livekernelreports", _C, "crit.path.dumps", "crit.prisk.regen"),
    ("memory.dmp", _C, "crit.path.dumps", "crit.prisk.regen"),
)

# Lo que es del propio sistema y cuya pérdida daña a Windows (no arranca, pierde funciones o
# deja la cuenta inservible). Queda fuera lo importante que NO es del sistema: programas
# instalados, datos de programas, carpetas personales, y lo que Windows regenera solo.
_SYSTEM_DAMAGE = {
    "crit.path.drive_root", "crit.path.windows", "crit.path.system32", "crit.path.registry",
    "crit.path.drivers", "crit.path.winsxs", "crit.path.installer", "crit.path.update_db",
    "crit.path.windows_component", "crit.path.boot", "crit.path.recovery", "crit.path.pagefile",
    "crit.path.hiberfil", "crit.path.swapfile", "crit.path.dumpstack", "crit.path.restore_points",
    "crit.path.program_files", "crit.path.programdata", "crit.path.store_apps", "crit.path.users_root",
    "crit.path.profile", "crit.path.user_registry", "crit.path.appdata_root",
}

_PERSONAL = ("desktop", "documents", "downloads", "pictures", "music", "videos", "onedrive",
             "favorites", "contacts", "saved games", "links", "searches")


_ENV: dict[str, object] | None = None


def real_env() -> dict[str, object]:
    """Las carpetas del sistema de este equipo (Windows no siempre está en C:)."""
    global _ENV
    if _ENV is None:
        _ENV = _read_env()
    return _ENV


def _read_env() -> dict[str, object]:
    sysdrive = os.environ.get("SystemDrive", "C:")
    profile = os.environ.get("USERPROFILE", "")
    return {
        "sysdrive": sysdrive,
        "windir": os.environ.get("WINDIR", rf"{sysdrive}\Windows"),
        "program_files": [os.environ.get("ProgramFiles", rf"{sysdrive}\Program Files"),
                          os.environ.get("ProgramFiles(x86)", rf"{sysdrive}\Program Files (x86)"),
                          os.environ.get("ProgramW6432", "")],
        "programdata": os.environ.get("ProgramData", rf"{sysdrive}\ProgramData"),
        "users": os.path.dirname(profile) if profile else rf"{sysdrive}\Users",
        "profile": profile,
        "app_root": str(APP_ROOT),
    }


def assess_path(path: str, env: dict | None = None, strict: bool = True) -> Assessment:
    """Qué es un archivo o carpeta y qué pasa si se borra.

    Con strict=True, lo que `safety.check_deletable` bloquea nunca sale como «normal».
    «env» permite fijar las carpetas del sistema (para los tests)."""
    e = env if env is not None else real_env()
    found = _classify(_nk(path), e)
    if found is not None:
        level, what, risk = found
        return Assessment(level, i18n.t(what), i18n.t(risk), system=what in _SYSTEM_DAMAGE)
    if strict and env is None and os.name == "nt":
        chk = check_deletable(path)
        if not chk.allowed:
            return Assessment(Level.IMPORTANT, chk.reason, i18n.t("crit.prisk.important"))
    return _a(Level.NORMAL, "crit.path.normal", "crit.prisk.normal")


def _classify(key: str, e: dict) -> tuple[Level, str, str] | None:
    if not key:
        return None
    sysdrive = _nk(str(e.get("sysdrive", "")))
    drive, _sep, rest = key.partition("\\")
    if len(drive) == 2 and drive[1] == ":":
        if not rest:
            return (_V if drive == sysdrive else _I), "crit.path.drive_root", "crit.prisk.drive_root"
        first = rest.partition("\\")[0]
        if first in _ANY_DRIVE_ITEMS:
            return _ANY_DRIVE_ITEMS[first]
        if drive == sysdrive and first in _ROOT_ITEMS and ("\\" not in rest or first in _ROOT_DIRS):
            return _ROOT_ITEMS[first]

    app_root = _nk(str(e.get("app_root", "")))
    if _under(key, app_root):
        return _I, "crit.path.own_app", "crit.prisk.own_app"

    windir = _nk(str(e.get("windir", "")))
    if _under(key, windir):
        if key == windir:
            return _V, "crit.path.windows", "crit.prisk.vital"
        rel = key[len(windir) + 1:]
        for sub, level, what, risk in _WINDOWS_ITEMS:
            if _under(rel, sub):
                return level, what, risk
        return _I, "crit.path.windows_component", "crit.prisk.important"

    for pf in {_nk(p) for p in e.get("program_files", []) if p}:
        if key == pf:
            return _I, "crit.path.program_files", "crit.prisk.program"
        if _under(key, pf):
            if _under(key, pf + "\\windowsapps"):
                return _I, "crit.path.store_apps", "crit.prisk.program"
            return _I, "crit.path.installed_program", "crit.prisk.program"

    programdata = _nk(str(e.get("programdata", "")))
    if _under(key, programdata):
        if key == programdata or _under(key, programdata + "\\microsoft"):
            return _I, "crit.path.programdata", "crit.prisk.important"
        if _under(key, programdata + "\\package cache"):
            return _C, "crit.path.package_cache", "crit.prisk.package_cache"
        return _C, "crit.path.app_data", "crit.prisk.app_data"

    profile = _nk(str(e.get("profile", "")))
    if _under(key, profile):
        if key == profile:
            return _V, "crit.path.profile", "crit.prisk.profile"
        rel = key[len(profile) + 1:]
        first = rel.partition("\\")[0]
        if "\\" not in rel and (first.startswith("ntuser.") or first.startswith("usrclass.")):
            return _V, "crit.path.user_registry", "crit.prisk.profile"
        if first == "appdata":
            if rel in ("appdata", "appdata\\local", "appdata\\roaming", "appdata\\locallow"):
                return _I, "crit.path.appdata_root", "crit.prisk.important"
            if _under(rel, "appdata\\local\\temp"):
                # la carpeta en sí no se borra; lo que hay dentro son temporales corrientes
                level = _C if rel == "appdata\\local\\temp" else Level.NORMAL
                return level, "crit.path.user_temp", "crit.prisk.regen"
            if _under(rel, "appdata\\local\\packages") or _under(rel, "appdata\\local\\microsoft\\windowsapps"):
                return _I, "crit.path.store_apps", "crit.prisk.program"
            if _under(rel, "appdata\\local\\microsoft") or _under(rel, "appdata\\roaming\\microsoft"):
                return _C, "crit.path.ms_user_data", "crit.prisk.app_data"
            return _C, "crit.path.app_data", "crit.prisk.app_data"
        if first in _PERSONAL:
            if rel == first:
                return _I, "crit.path.personal_folder", "crit.prisk.personal_folder"
            return Level.NORMAL, "crit.path.personal", "crit.prisk.personal"
        return None

    users = _nk(str(e.get("users", "")))
    if _under(key, users):
        rel = key[len(users) + 1:] if key != users else ""
        if rel in ("", "public", "default", "default user", "all users"):
            return _I, "crit.path.users_root", "crit.prisk.important"
        return _C, "crit.path.other_profile", "crit.prisk.other_profile"
    return None


def worst(items: list[Assessment]) -> Assessment | None:
    """La valoración más grave de una lista (None si está vacía)."""
    return max(items, key=lambda a: a.level, default=None)
