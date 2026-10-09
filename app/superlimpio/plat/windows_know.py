"""Lo que hay que saber de Windows: qué procesos y carpetas son vitales, cuáles se
protegen y cómo se reconocen los programas.

Es lógica pura (tablas y comparación de textos, sin llamadas al sistema), así que se
puede probar desde cualquier equipo. Los niveles son los de criticality.Level:
0 normal · 1 precaución · 2 importante · 3 vital.
"""

from __future__ import annotations

import os

_V, _I, _C = 3, 2, 1

# PID que son del núcleo: «System Idle Process» y «System»
VITAL_PIDS = (0, 4)

# Procesos que nunca se deben finalizar (el sistema se cuelga o reinicia)
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe", "fontdrvhost.exe",
    "dwm.exe", "memory compression", "secure system", "msmpeng.exe", "nissrv.exe",
    "securityhealthservice.exe", "sgrmbroker.exe", "audiodg.exe", "spoolsv.exe",
}

# Procesos que se pueden cerrar pero con aviso reforzado
SENSITIVE_PROCESSES = {"explorer.exe", "sihost.exe", "ctfmon.exe", "searchhost.exe",
                       "startmenuexperiencehost.exe", "taskhostw.exe", "runtimebroker.exe"}

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

# nombre -> (nivel, clave de «qué es», clave del riesgo)
PROCESSES: dict[str, tuple[int, str, str]] = {
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
WINDOWS_TOOLS = {
    "notepad.exe", "cmd.exe", "powershell.exe", "powershell_ise.exe", "taskmgr.exe", "mspaint.exe",
    "regedit.exe", "mmc.exe", "control.exe", "snippingtool.exe", "calc.exe", "wordpad.exe", "write.exe",
    "charmap.exe", "osk.exe", "magnify.exe", "perfmon.exe", "resmon.exe", "cleanmgr.exe", "dfrgui.exe",
    "msinfo32.exe", "winver.exe", "openconsole.exe", "mstsc.exe", "eventvwr.exe", "msconfig.exe",
    "systemsettings.exe", "wscript.exe", "cscript.exe", "rundll32.exe",
}


# =========================================================================
# Rutas: comparación sin tocar el disco
# =========================================================================

def norm(path: str) -> str:
    """Clave de comparación de rutas de Windows (sin distinguir mayúsculas)."""
    return path.replace("/", "\\").rstrip("\\").lower()


def under(key: str, folder: str) -> bool:
    """True si la ruta (ya normalizada) es la carpeta o está dentro de ella."""
    return bool(folder) and (key == folder or key.startswith(folder + "\\"))


def install_dir(path: str) -> str:
    """Carpeta del ejecutable; '' si cuelga directamente de la raíz de una unidad (ahí
    «la misma carpeta» sería el disco entero)."""
    folder = norm(path).rpartition("\\")[0]
    return folder if "\\" in folder else ""


def system_dirs() -> tuple[str, ...]:
    """Carpetas cuyos programas son del propio sistema."""
    return (os.environ.get("WINDIR", r"C:\Windows"),)


def is_service(proc, parent) -> bool:
    """True si el proceso lo lanzó el Administrador de servicios."""
    return parent is not None and parent.name.lower() == "services.exe"


def process_info(name: str, path: str, pid: int, accessible: bool, service: bool,
                 sysdirs: tuple[str, ...]) -> tuple[int, str, str]:
    """(nivel, clave de «qué es», clave del riesgo) de un proceso."""
    n = name.lower()
    if pid in VITAL_PIDS:
        return _V, "crit.proc.system", "crit.risk.vital"
    known = PROCESSES.get(n)
    if known:
        return known
    if n in PROTECTED_PROCESSES:
        return _V, "crit.proc.essential", "crit.risk.vital"
    if n in SENSITIVE_PROCESSES:
        return _C, "crit.proc.shell", "crit.risk.shell"
    key = norm(path)
    if n in SECURITY_PROCESSES or any(h in key for h in SECURITY_PATHS):
        return _I, "crit.proc.security", "crit.risk.security"
    in_windows = bool(key) and any(under(key, norm(d)) for d in sysdirs)
    if in_windows and n in WINDOWS_TOOLS and not service:
        return 0, "crit.proc.windows_tool", "crit.risk.normal"
    if service:
        if in_windows or not key:
            return _I, "crit.proc.windows_service", "crit.risk.service"
        return _C, "crit.proc.app_service", "crit.risk.service"
    if in_windows:
        return _I, "crit.proc.windows_component", "crit.risk.component"
    if not key and not accessible:   # no se sabe qué es: se avisa, sin darlo por parte de Windows
        return _C, "crit.proc.no_access", "crit.risk.unknown"
    return 0, "crit.proc.normal", "crit.risk.normal"


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
SYSTEM_DAMAGE = {
    "crit.path.drive_root", "crit.path.windows", "crit.path.system32", "crit.path.registry",
    "crit.path.drivers", "crit.path.winsxs", "crit.path.installer", "crit.path.update_db",
    "crit.path.windows_component", "crit.path.boot", "crit.path.recovery", "crit.path.pagefile",
    "crit.path.hiberfil", "crit.path.swapfile", "crit.path.dumpstack", "crit.path.restore_points",
    "crit.path.program_files", "crit.path.programdata", "crit.path.store_apps", "crit.path.users_root",
    "crit.path.profile", "crit.path.user_registry", "crit.path.appdata_root",
}

_PERSONAL = ("desktop", "documents", "downloads", "pictures", "music", "videos", "onedrive",
             "favorites", "contacts", "saved games", "links", "searches")


def path_env(app_root: str = "") -> dict[str, object]:
    """Las carpetas del sistema de este equipo (Windows no siempre está en C:)."""
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
        "app_root": app_root,
    }


def classify_path(key: str, e: dict) -> tuple[int, str, str] | None:
    """(nivel, qué es, riesgo) de una ruta ya normalizada con norm(); None si es corriente."""
    if not key:
        return None
    sysdrive = norm(str(e.get("sysdrive", "")))
    drive, _sep, rest = key.partition("\\")
    if len(drive) == 2 and drive[1] == ":":
        if not rest:
            return (_V if drive == sysdrive else _I), "crit.path.drive_root", "crit.prisk.drive_root"
        first = rest.partition("\\")[0]
        if first in _ANY_DRIVE_ITEMS:
            return _ANY_DRIVE_ITEMS[first]
        if drive == sysdrive and first in _ROOT_ITEMS and ("\\" not in rest or first in _ROOT_DIRS):
            return _ROOT_ITEMS[first]

    app_root = norm(str(e.get("app_root", "")))
    if under(key, app_root):
        return _I, "crit.path.own_app", "crit.prisk.own_app"

    windir = norm(str(e.get("windir", "")))
    if under(key, windir):
        if key == windir:
            return _V, "crit.path.windows", "crit.prisk.vital"
        rel = key[len(windir) + 1:]
        for sub, level, what, risk in _WINDOWS_ITEMS:
            if under(rel, sub):
                return level, what, risk
        return _I, "crit.path.windows_component", "crit.prisk.important"

    for pf in {norm(p) for p in e.get("program_files", []) if p}:
        if key == pf:
            return _I, "crit.path.program_files", "crit.prisk.program"
        if under(key, pf):
            if under(key, pf + "\\windowsapps"):
                return _I, "crit.path.store_apps", "crit.prisk.program"
            return _I, "crit.path.installed_program", "crit.prisk.program"

    programdata = norm(str(e.get("programdata", "")))
    if under(key, programdata):
        if key == programdata or under(key, programdata + "\\microsoft"):
            return _I, "crit.path.programdata", "crit.prisk.important"
        if under(key, programdata + "\\package cache"):
            return _C, "crit.path.package_cache", "crit.prisk.package_cache"
        return _C, "crit.path.app_data", "crit.prisk.app_data"

    profile = norm(str(e.get("profile", "")))
    if under(key, profile):
        if key == profile:
            return _V, "crit.path.profile", "crit.prisk.profile"
        rel = key[len(profile) + 1:]
        first = rel.partition("\\")[0]
        if "\\" not in rel and (first.startswith("ntuser.") or first.startswith("usrclass.")):
            return _V, "crit.path.user_registry", "crit.prisk.profile"
        if first == "appdata":
            if rel in ("appdata", "appdata\\local", "appdata\\roaming", "appdata\\locallow"):
                return _I, "crit.path.appdata_root", "crit.prisk.important"
            if under(rel, "appdata\\local\\temp"):
                # la carpeta en sí no se borra; lo que hay dentro son temporales corrientes
                level = _C if rel == "appdata\\local\\temp" else 0
                return level, "crit.path.user_temp", "crit.prisk.regen"
            if under(rel, "appdata\\local\\packages") or under(rel, "appdata\\local\\microsoft\\windowsapps"):
                return _I, "crit.path.store_apps", "crit.prisk.program"
            if under(rel, "appdata\\local\\microsoft") or under(rel, "appdata\\roaming\\microsoft"):
                return _C, "crit.path.ms_user_data", "crit.prisk.app_data"
            return _C, "crit.path.app_data", "crit.prisk.app_data"
        if first in _PERSONAL:
            if rel == first:
                return _I, "crit.path.personal_folder", "crit.prisk.personal_folder"
            return 0, "crit.path.personal", "crit.prisk.personal"
        return None

    users = norm(str(e.get("users", "")))
    if under(key, users):
        rel = key[len(users) + 1:] if key != users else ""
        if rel in ("", "public", "default", "default user", "all users"):
            return _I, "crit.path.users_root", "crit.prisk.important"
        return _C, "crit.path.other_profile", "crit.prisk.other_profile"
    return None


# =========================================================================
# Borrado: rutas que la aplicación se niega a tocar
# =========================================================================

# Carpetas del sistema que existen en la raíz de TODAS las unidades
PER_DRIVE_SYSTEM_DIRS = {"system volume information", "$recycle.bin"}

# Archivos del sistema con explicación propia: nombre -> clave i18n del motivo
SYSTEM_FILE_HINTS = {
    "pagefile.sys": "safety.file.pagefile",
    "hiberfil.sys": "safety.file.hiberfil",
    "swapfile.sys": "safety.file.swapfile",
}


def protected_roots() -> tuple[set[str], set[str], set[str]]:
    """(rutas exactas, rutas con todo su contenido, carpetas de programas) protegidas.
    Las de programas van también en la segunda lista; se separan para dar otro mensaje."""
    def expand(path: str) -> str:
        return os.path.normpath(os.path.expanduser(os.path.expandvars(path)))

    sysdrive = os.environ.get("SystemDrive", "C:")   # Windows no siempre está en C:
    windir = os.environ.get("WINDIR", rf"{sysdrive}\Windows")
    programdata = os.environ.get("ProgramData", rf"{sysdrive}\ProgramData")
    programs = {
        os.environ.get("ProgramFiles", rf"{sysdrive}\Program Files"),
        os.environ.get("ProgramFiles(x86)", rf"{sysdrive}\Program Files (x86)"),
        os.environ.get("ProgramW6432", rf"{sysdrive}\Program Files"),
    }
    tree = set(programs) | {
        windir,
        rf"{sysdrive}\Recovery",
        rf"{sysdrive}\Boot",
        rf"{sysdrive}\$WinREAgent",
        expand(r"%LOCALAPPDATA%\Microsoft\WindowsApps"),
        expand(r"%LOCALAPPDATA%\Packages"),
        rf"{programdata}\Microsoft",
    }
    exact = {
        programdata,
        os.environ.get("USERPROFILE", ""),
        os.environ.get("APPDATA", ""),
        os.environ.get("LOCALAPPDATA", ""),
        expand(r"%USERPROFILE%\AppData"),
        expand(r"%USERPROFILE%\AppData\LocalLow"),
        rf"{sysdrive}\Users",
        rf"{sysdrive}\Users\Public",
        rf"{sysdrive}\Users\Default",
    }
    for name in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
                 "OneDrive", "Favorites", "Contacts", "Saved Games", "Links", "Searches"):
        exact.add(expand(rf"%USERPROFILE%\{name}"))
    for f in ("DumpStack.log.tmp", "bootmgr"):
        exact.add(rf"{sysdrive}\{f}")
    return exact, tree, programs


# =========================================================================
# Optimizar: programas conocidos
# =========================================================================

CATALOG: dict[str, tuple[str, ...]] = {
    "updater": (
        "googleupdate.exe", "microsoftedgeupdate.exe", "braveupdate.exe", "adobearm.exe", "acrotray.exe",
        "jusched.exe", "jucheck.exe", "ccxprocess.exe", "adobenotificationclient.exe",
        "opera_autoupdate.exe", "ituneshelper.exe", "dropboxupdate.exe", "onedrivestandaloneupdater.exe",
    ),
    "widget": (
        "widgets.exe", "widgetservice.exe", "phoneexperiencehost.exe", "yourphone.exe", "copilot.exe",
        "cortana.exe", "hxtsr.exe", "widgetboard.exe", "microsoftstartfeedprovider.exe",
        "crossdeviceservice.exe",
    ),
    "cloud": (
        "onedrive.exe", "dropbox.exe", "googledrivefs.exe", "iclouddrive.exe", "icloudservices.exe",
        "megasync.exe", "pcloud.exe", "nextcloud.exe", "box.exe", "coresync.exe",
    ),
    "browser": (
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe", "arc.exe",
        "librewolf.exe", "waterfox.exe", "iexplore.exe",
    ),
    "comms": (
        "discord.exe", "discordptb.exe", "discordcanary.exe", "ms-teams.exe", "teams.exe", "slack.exe",
        "zoom.exe", "skype.exe", "telegram.exe", "whatsapp.exe", "whatsapp.root.exe", "signal.exe",
        "ts3client_win64.exe", "teamspeak.exe", "mumble.exe", "element.exe",
    ),
    "media": (
        "spotify.exe", "obs64.exe", "obs32.exe", "streamlabs obs.exe", "vlc.exe", "itunes.exe",
        "applemusic.exe", "foobar2000.exe", "musicbee.exe", "tidal.exe", "audacity.exe",
    ),
    "launcher": (
        "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "battle.net.exe", "eadesktop.exe",
        "origin.exe", "upc.exe", "ubisoftconnect.exe", "galaxyclient.exe", "riotclientservices.exe",
        "riotclientux.exe", "xboxpcapp.exe", "xboxapp.exe", "playnite.desktopapp.exe", "gamebar.exe",
        "gamebarftserver.exe",
    ),
    "gpu": (
        "nvidia share.exe", "nvidia web helper.exe", "nvidia overlay.exe", "nvcontainer.exe",
        "nvdisplay.container.exe", "nvsphelper64.exe", "nvidia geforce experience.exe",
        "radeonsoftware.exe", "amdrsserv.exe", "amdow.exe", "cncmd.exe", "igfxem.exe", "igcc.exe",
        "msiafterburner.exe", "rtss.exe",
    ),
    "peripheral": (
        "lghub.exe", "lghub_agent.exe", "lghub_system_tray.exe", "razer synapse 3.exe",
        "razer synapse.exe", "razerappengine.exe", "razer central.exe", "icue.exe", "steelseriesgg.exe",
        "steelseriesengine.exe", "steelseriessonar.exe", "armourycrate.exe", "streamdeck.exe",
        "voicemeeter.exe", "voicemeeterpro.exe", "voicemeeter8.exe", "nahimicsvc64.exe",
        "rtkauduservice64.exe", "ds4windows.exe", "joytokey.exe", "autohotkey.exe", "autohotkey64.exe",
        "autohotkeyu64.exe", "powertoys.exe",
    ),
    "network": (
        "openvpn-gui.exe", "nordvpn.exe", "protonvpn.client.exe", "wireguard.exe", "expressvpn.exe",
        "mullvad vpn.exe", "tailscale-ipn.exe",
    ),
}
CATEGORY_OF = {name: cat for cat, names in CATALOG.items() for name in names}

# Procesos auxiliares que siempre pertenecen al programa que los lanzó, aunque su
# ejecutable esté en otra carpeta (p. ej. la vista web incrustada de Teams o Widgets).
HELPERS = {"msedgewebview2.exe", "crashpad_handler.exe", "cefsharp.browsersubprocess.exe"}

# Utilidades de dispositivos que no están en el catálogo: se reconocen por el nombre.
PERIPHERAL_HINTS = ("tablet", "wacom", "audio", "hotkey", "touchpad", "synaptics", "logi", "razer",
                     "corsair", "steelseries")
