"""Lo que hay que saber de Linux: qué procesos y carpetas son vitales, cuáles se
protegen y cómo se reconocen los programas.

Es lógica pura (tablas y comparación de textos, sin llamadas al sistema), así que se
puede probar desde cualquier equipo. Los niveles son los de criticality.Level:
0 normal · 1 precaución · 2 importante · 3 vital.
"""

from __future__ import annotations

import os

_V, _I, _C = 3, 2, 1

# PID del núcleo y de sus hilos: «swapper», «init/systemd» y «kthreadd»
VITAL_PIDS = (0, 1, 2)

# Procesos que nunca se deben finalizar (el sistema se cuelga o se cierra la sesión)
PROTECTED_PROCESSES = {
    "systemd", "init", "kthreadd", "systemd-journald", "systemd-logind", "systemd-udevd",
    "dbus-daemon", "dbus-broker", "dbus-broker-launch", "xorg", "x", "xwayland", "gdm", "gdm3",
    "gdm-session-worker", "gdm-wayland-session", "gdm-x-session", "sddm", "lightdm", "login",
    "gnome-shell", "kwin_wayland", "sway", "mutter", "weston", "polkitd",
}

# Procesos que se pueden cerrar pero con aviso reforzado
SENSITIVE_PROCESSES = {
    "plasmashell", "kwin_x11", "xfwm4", "xfce4-session", "xfce4-panel", "cinnamon", "marco", "openbox",
    "gnome-session-binary", "gnome-session", "ksmserver", "pipewire", "pipewire-pulse", "wireplumber",
    "pulseaudio", "networkmanager", "wpa_supplicant", "ibus-daemon", "fcitx5", "fcitx",
}

# Seguridad: cerrarlos desprotege el equipo
SECURITY_PROCESSES = {
    "clamd", "freshclam", "firewalld", "ufw", "fail2ban-server", "auditd", "apparmor", "sssd",
    "gnome-keyring-daemon", "kwalletd5", "kwalletd6", "ssh-agent", "gpg-agent",
}
SECURITY_PATHS: tuple[str, ...] = ()

# nombre -> (nivel, clave de «qué es», clave del riesgo)
PROCESSES: dict[str, tuple[int, str, str]] = {
    "systemd": (_V, "crit.lproc.systemd", "crit.risk.vital"),
    "init": (_V, "crit.lproc.systemd", "crit.risk.vital"),
    "kthreadd": (_V, "crit.proc.system", "crit.risk.vital"),
    "systemd-journald": (_I, "crit.lproc.journald", "crit.risk.component"),
    "systemd-logind": (_V, "crit.lproc.logind", "crit.risk.session"),
    "systemd-udevd": (_I, "crit.lproc.udevd", "crit.risk.driver"),
    "systemd-resolved": (_I, "crit.lproc.resolved", "crit.risk.network"),
    "systemd-timesyncd": (_C, "crit.lproc.timesyncd", "crit.risk.relaunch"),
    "systemd-oomd": (_I, "crit.lproc.oomd", "crit.risk.component"),
    "dbus-daemon": (_V, "crit.lproc.dbus", "crit.risk.session"),
    "dbus-broker": (_V, "crit.lproc.dbus", "crit.risk.session"),
    "dbus-broker-launch": (_V, "crit.lproc.dbus", "crit.risk.session"),
    "xorg": (_V, "crit.lproc.display", "crit.risk.session"),
    "x": (_V, "crit.lproc.display", "crit.risk.session"),
    "xwayland": (_V, "crit.lproc.xwayland", "crit.risk.session"),
    "gnome-shell": (_V, "crit.lproc.desktop", "crit.risk.session"),
    "kwin_wayland": (_V, "crit.lproc.desktop", "crit.risk.session"),
    "sway": (_V, "crit.lproc.desktop", "crit.risk.session"),
    "mutter": (_V, "crit.lproc.desktop", "crit.risk.session"),
    "weston": (_V, "crit.lproc.desktop", "crit.risk.session"),
    "gdm": (_V, "crit.lproc.login", "crit.risk.session"),
    "gdm3": (_V, "crit.lproc.login", "crit.risk.session"),
    "gdm-session-worker": (_V, "crit.lproc.login", "crit.risk.session"),
    "gdm-wayland-session": (_V, "crit.lproc.login", "crit.risk.session"),
    "gdm-x-session": (_V, "crit.lproc.login", "crit.risk.session"),
    "sddm": (_V, "crit.lproc.login", "crit.risk.session"),
    "lightdm": (_V, "crit.lproc.login", "crit.risk.session"),
    "login": (_V, "crit.lproc.login", "crit.risk.session"),
    "polkitd": (_I, "crit.lproc.polkit", "crit.risk.component"),
    "plasmashell": (_C, "crit.proc.explorer", "crit.risk.shell"),
    "kwin_x11": (_C, "crit.lproc.wm", "crit.risk.shell"),
    "xfwm4": (_C, "crit.lproc.wm", "crit.risk.shell"),
    "marco": (_C, "crit.lproc.wm", "crit.risk.shell"),
    "openbox": (_C, "crit.lproc.wm", "crit.risk.shell"),
    "cinnamon": (_C, "crit.proc.explorer", "crit.risk.shell"),
    "xfce4-panel": (_C, "crit.proc.explorer", "crit.risk.shell"),
    "xfce4-session": (_I, "crit.lproc.session", "crit.risk.session"),
    "gnome-session-binary": (_I, "crit.lproc.session", "crit.risk.session"),
    "gnome-session": (_I, "crit.lproc.session", "crit.risk.session"),
    "ksmserver": (_I, "crit.lproc.session", "crit.risk.session"),
    "pipewire": (_C, "crit.proc.audiodg", "crit.risk.audio"),
    "pipewire-pulse": (_C, "crit.proc.audiodg", "crit.risk.audio"),
    "wireplumber": (_C, "crit.proc.audiodg", "crit.risk.audio"),
    "pulseaudio": (_C, "crit.proc.audiodg", "crit.risk.audio"),
    "networkmanager": (_I, "crit.lproc.network", "crit.risk.network"),
    "wpa_supplicant": (_I, "crit.proc.wlan", "crit.risk.network"),
    "cupsd": (_I, "crit.proc.spooler", "crit.risk.print"),
    "ibus-daemon": (_C, "crit.proc.ctfmon", "crit.risk.input"),
    "fcitx5": (_C, "crit.proc.ctfmon", "crit.risk.input"),
    "fcitx": (_C, "crit.proc.ctfmon", "crit.risk.input"),
    "packagekitd": (_I, "crit.lproc.packages", "crit.risk.update"),
    "apt": (_I, "crit.lproc.packages", "crit.risk.update"),
    "apt-get": (_I, "crit.lproc.packages", "crit.risk.update"),
    "dpkg": (_I, "crit.lproc.packages", "crit.risk.update"),
    "unattended-upgr": (_I, "crit.lproc.packages", "crit.risk.update"),
    "dnf": (_I, "crit.lproc.packages", "crit.risk.update"),
    "rpm": (_I, "crit.lproc.packages", "crit.risk.update"),
    "pacman": (_I, "crit.lproc.packages", "crit.risk.update"),
    "snapd": (_I, "crit.lproc.snapd", "crit.risk.store_apps"),
    "tracker-miner-fs-3": (_C, "crit.proc.indexer", "crit.risk.relaunch"),
    "tracker-miner-fs": (_C, "crit.proc.indexer", "crit.risk.relaunch"),
    "baloo_file": (_C, "crit.proc.indexer", "crit.risk.relaunch"),
    "dockerd": (_C, "crit.lproc.containers", "crit.risk.vm"),
    "containerd": (_C, "crit.lproc.containers", "crit.risk.vm"),
    "qemu-system-x86_64": (_C, "crit.proc.vmmem", "crit.risk.vm"),
    "sshd": (_C, "crit.lproc.sshd", "crit.risk.service"),
    "cron": (_C, "crit.lproc.cron", "crit.risk.service"),
    "crond": (_C, "crit.lproc.cron", "crit.risk.service"),
}

# Carpetas cuyos programas son piezas del sistema o del escritorio, no programas del usuario
_SYSTEM_DIRS = ("/usr/lib/systemd", "/lib/systemd", "/usr/libexec", "/usr/sbin", "/sbin",
                "/usr/lib/polkit-1", "/usr/lib/x86_64-linux-gnu/libexec")
# Carpetas donde conviven los ejecutables de muchos programas: «misma carpeta» no significa nada
_SHARED_DIRS = {"/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin", "/usr/local/sbin",
                "/usr/libexec", "/usr/games", "/snap/bin", "/var/lib/flatpak/exports/bin"}


# =========================================================================
# Rutas: comparación sin tocar el disco
# =========================================================================

def norm(path: str) -> str:
    """Clave de comparación de rutas de Linux (aquí sí se distinguen mayúsculas)."""
    return path.rstrip("/") or ("/" if path else "")


def under(key: str, folder: str) -> bool:
    """True si la ruta (ya normalizada) es la carpeta o está dentro de ella."""
    if not folder:
        return False
    return key == folder or key.startswith(folder.rstrip("/") + "/")


def install_dir(path: str) -> str:
    """Carpeta del ejecutable; '' si es una de las compartidas (/usr/bin...) o la raíz."""
    folder = norm(path).rpartition("/")[0]
    return "" if not folder or folder in _SHARED_DIRS else folder


def system_dirs() -> tuple[str, ...]:
    """Carpetas cuyos programas son del propio sistema."""
    return _SYSTEM_DIRS


def is_service(proc, parent) -> bool:
    """True si al proceso lo lanzó directamente el gestor del sistema (PID 1)."""
    return parent is not None and parent.pid == 1


def process_info(name: str, path: str, pid: int, accessible: bool, service: bool,
                 sysdirs: tuple[str, ...]) -> tuple[int, str, str]:
    """(nivel, clave de «qué es», clave del riesgo) de un proceso."""
    n = name.lower()
    if pid in VITAL_PIDS:
        return _V, ("crit.lproc.systemd" if pid == 1 else "crit.proc.system"), "crit.risk.vital"
    known = PROCESSES.get(n)
    if known:
        return known
    if n in PROTECTED_PROCESSES:
        return _V, "crit.proc.essential", "crit.risk.vital"
    if n in SENSITIVE_PROCESSES:
        return _C, "crit.proc.shell", "crit.risk.shell"
    if n in SECURITY_PROCESSES:
        return _I, "crit.proc.security", "crit.risk.security"
    key = norm(path)
    in_system = bool(key) and any(under(key, norm(d)) for d in sysdirs)
    if service:
        if in_system or not key:
            return _I, "crit.lproc.system_service", "crit.risk.service"
        return _C, "crit.proc.app_service", "crit.risk.service"
    if in_system:
        return _C, "crit.lproc.desktop_component", "crit.risk.relaunch"
    if not key and not accessible:   # de otro usuario (casi siempre, del sistema): no se sabe qué es
        return _C, "crit.proc.no_access", "crit.risk.unknown"
    return 0, "crit.proc.normal", "crit.risk.normal"


# =========================================================================
# Archivos y carpetas
# =========================================================================

# Carpetas de la raíz: (nivel, qué es, riesgo). Cuentan con todo su contenido.
_ROOT_ITEMS = {
    "boot": (_V, "crit.path.boot", "crit.prisk.vital"),
    "efi": (_V, "crit.path.boot", "crit.prisk.vital"),
    "etc": (_V, "crit.lpath.etc", "crit.prisk.vital"),
    "usr": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "bin": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "sbin": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "lib": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "lib32": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "lib64": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "libx32": (_V, "crit.lpath.usr", "crit.prisk.vital"),
    "proc": (_V, "crit.lpath.virtual", "crit.prisk.vital"),
    "sys": (_V, "crit.lpath.virtual", "crit.prisk.vital"),
    "dev": (_V, "crit.lpath.virtual", "crit.prisk.vital"),
    "run": (_V, "crit.lpath.virtual", "crit.prisk.vital"),
    "root": (_I, "crit.lpath.root_home", "crit.prisk.important"),
    "opt": (_I, "crit.path.installed_program", "crit.prisk.program"),
    "snap": (_I, "crit.path.store_apps", "crit.prisk.program"),
    "srv": (_C, "crit.lpath.srv", "crit.prisk.app_data"),
    "lost+found": (_I, "crit.lpath.lost_found", "crit.prisk.important"),
    "swapfile": (_I, "crit.path.pagefile", "crit.prisk.managed"),
    "swap.img": (_I, "crit.path.pagefile", "crit.prisk.managed"),
    "tmp": (_C, "crit.path.windows_temp", "crit.prisk.regen"),
    "mnt": (_I, "crit.lpath.mounts", "crit.prisk.important"),
    "media": (_I, "crit.lpath.mounts", "crit.prisk.important"),
}

# Dentro de /var: (subcarpeta, nivel, qué es, riesgo). Gana la primera.
_VAR_ITEMS = (
    ("lib/dpkg", _V, "crit.lpath.pkgdb", "crit.prisk.vital"),
    ("lib/rpm", _V, "crit.lpath.pkgdb", "crit.prisk.vital"),
    ("lib/pacman", _V, "crit.lpath.pkgdb", "crit.prisk.vital"),
    ("lib/flatpak", _I, "crit.path.store_apps", "crit.prisk.program"),
    ("lib/snapd", _I, "crit.path.store_apps", "crit.prisk.program"),
    ("lib/docker", _C, "crit.lpath.containers", "crit.prisk.app_data"),
    ("lib/systemd/coredump", _C, "crit.path.dumps", "crit.prisk.regen"),
    ("lib", _I, "crit.path.programdata", "crit.prisk.important"),
    ("cache", _C, "crit.lpath.var_cache", "crit.prisk.regen"),
    ("log", _C, "crit.path.windows_logs", "crit.prisk.regen"),
    ("crash", _C, "crit.path.dumps", "crit.prisk.regen"),
    ("tmp", _C, "crit.path.windows_temp", "crit.prisk.regen"),
)

# Lo que es del propio sistema y cuya pérdida lo daña (no arranca, pierde funciones o deja
# la cuenta inservible). Queda fuera lo importante que NO es del sistema: programas
# instalados, datos de programas, carpetas personales, y lo que se regenera solo.
SYSTEM_DAMAGE = {
    "crit.path.drive_root", "crit.path.boot", "crit.lpath.etc", "crit.lpath.usr", "crit.lpath.virtual",
    "crit.lpath.root_home", "crit.lpath.lost_found", "crit.path.pagefile", "crit.lpath.pkgdb",
    "crit.path.programdata", "crit.lpath.var", "crit.path.users_root", "crit.path.profile",
    "crit.path.appdata_root", "crit.lpath.keys", "crit.lpath.mounts",
}

_PERSONAL = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "Public", "Templates",
             "Escritorio", "Documentos", "Descargas", "Imágenes", "Música", "Vídeos", "Público", "Plantillas")
_SHELL_FILES = (".bashrc", ".bash_profile", ".bash_logout", ".profile", ".zshrc", ".zprofile", ".xinitrc",
                ".Xauthority", ".ICEauthority", ".pam_environment", ".xprofile")


def path_env(app_root: str = "") -> dict[str, object]:
    """Las carpetas del sistema de este equipo."""
    home = os.path.expanduser("~")
    return {
        "home": home,
        "users": os.path.dirname(home.rstrip("/")) or "/home",
        "app_root": app_root,
        "mounts": [],   # raíces de otros discos montados (las rellena quien las conozca)
    }


def classify_path(key: str, e: dict) -> tuple[int, str, str] | None:
    """(nivel, qué es, riesgo) de una ruta ya normalizada con norm(); None si es corriente."""
    if not key or not key.startswith("/"):
        return None
    if key == "/":
        return _V, "crit.path.drive_root", "crit.prisk.drive_root"
    if key in {norm(m) for m in e.get("mounts", []) if m}:
        return _I, "crit.path.drive_root", "crit.prisk.drive_root"

    app_root = norm(str(e.get("app_root", "")))
    if under(key, app_root):
        return _I, "crit.path.own_app", "crit.prisk.own_app"

    home = norm(str(e.get("home", "")))
    if under(key, home):
        if key == home:
            return _V, "crit.path.profile", "crit.prisk.profile"
        rel = key[len(home) + 1:]
        first = rel.partition("/")[0]
        if rel in (".config", ".local", ".local/share", ".local/state", ".var", ".var/app", "snap"):
            return _I, "crit.path.appdata_root", "crit.prisk.important"
        if first in (".ssh", ".gnupg", ".pki"):
            return _I, "crit.lpath.keys", "crit.lprisk.keys"
        if under(rel, ".local/share/Trash"):
            return _C, "crit.path.recycle_bin", "crit.prisk.recycle_bin"
        if under(rel, ".local/share/flatpak"):
            return _I, "crit.path.store_apps", "crit.prisk.program"
        if first == ".cache":
            # la carpeta en sí no se borra; lo que hay dentro son cachés corrientes
            return (_C if rel == ".cache" else 0), "crit.path.user_temp", "crit.prisk.regen"
        if rel in _SHELL_FILES:
            return _C, "crit.lpath.shell_config", "crit.prisk.app_data"
        if first in (".config", ".local", ".var", "snap", ".mozilla", ".thunderbird"):
            return _C, "crit.path.app_data", "crit.prisk.app_data"
        if first in _PERSONAL:
            if rel == first:
                return _I, "crit.path.personal_folder", "crit.prisk.personal_folder"
            return 0, "crit.path.personal", "crit.prisk.personal"
        if first.startswith(".") and "/" not in rel:
            return _C, "crit.path.app_data", "crit.prisk.app_data"
        return None

    users = norm(str(e.get("users", "")))
    if under(key, users):
        if key == users:
            return _I, "crit.path.users_root", "crit.prisk.important"
        return _C, "crit.path.other_profile", "crit.prisk.other_profile"

    first, _sep, rest = key[1:].partition("/")
    if first == "var":
        if not rest:
            return _I, "crit.lpath.var", "crit.prisk.important"
        for sub, level, what, risk in _VAR_ITEMS:
            if under(rest, sub):
                return level, what, risk
        return _C, "crit.path.app_data", "crit.prisk.app_data"
    if first in ("mnt", "media"):
        # el punto de montaje se protege; lo que hay en el disco montado son archivos corrientes
        return _ROOT_ITEMS[first] if not rest else None
    if first in ("tmp", "srv") and rest:
        return (0, "crit.path.windows_temp", "crit.prisk.regen") if first == "tmp" else None
    if first == "usr" and under(rest, "local"):
        return _I, "crit.path.installed_program", "crit.prisk.program"
    if first in _ROOT_ITEMS:
        if rest and first in ("swapfile", "swap.img"):
            return None
        return _ROOT_ITEMS[first]
    return None


# =========================================================================
# Borrado: rutas que la aplicación se niega a tocar
# =========================================================================

# Carpetas del sistema que existen en la raíz de todas las unidades (se incluyen las de
# Windows: un disco compartido con Windows las tiene, y siguen sin deber tocarse)
PER_DRIVE_SYSTEM_DIRS = {"lost+found", "system volume information", "$recycle.bin"}

# Archivos del sistema con explicación propia: nombre -> clave i18n del motivo
SYSTEM_FILE_HINTS = {
    "swapfile": "safety.file.pagefile",
    "swap.img": "safety.file.pagefile",
    "pagefile.sys": "safety.file.pagefile",
    "hiberfil.sys": "safety.file.hiberfil",
}


def user_dirs(home: str) -> list[str]:
    """Carpetas personales según ~/.config/user-dirs.dirs (sus nombres dependen del idioma)."""
    found = []
    try:
        with open(os.path.join(home, ".config", "user-dirs.dirs"), encoding="utf-8",
                  errors="surrogateescape") as fh:   # igual que el sistema lee los nombres de archivo
            for line in fh:
                line = line.strip()
                if line.startswith("XDG_") and "=" in line:
                    value = line.split("=", 1)[1].strip().strip('"').replace("$HOME", home)
                    if value and os.path.normpath(value) != os.path.normpath(home):
                        found.append(value)
    except OSError:
        pass
    return found


def protected_roots() -> tuple[set[str], set[str], set[str]]:
    """(rutas exactas, rutas con todo su contenido, carpetas de programas) protegidas.
    Las de programas van también en la segunda lista; se separan para dar otro mensaje."""
    home = os.path.expanduser("~")
    programs = {"/opt", "/snap", "/usr/local", "/var/lib/flatpak", "/var/lib/snapd",
                os.path.join(home, ".local", "share", "flatpak")}
    tree = set(programs) | {
        "/bin", "/boot", "/dev", "/efi", "/etc", "/lib", "/lib32", "/lib64", "/libx32", "/proc", "/root",
        "/run", "/sbin", "/sys", "/usr", "/var/lib", "/var/log", "/var/spool", "/var/mail",
    }
    exact = {
        "/home", "/var", "/var/cache", "/var/tmp", "/tmp", "/mnt", "/media", "/srv", "/swapfile", "/swap.img",
        home, os.path.dirname(home.rstrip("/")),
    }
    for name in (".config", ".local", ".local/share", ".local/state", ".cache", ".ssh", ".gnupg", ".pki",
                 ".var", ".var/app", "snap", ".mozilla", ".bashrc", ".profile", ".zshrc", ".bash_profile",
                 ".Xauthority", "Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "Public",
                 "Templates"):
        exact.add(os.path.join(home, name))
    exact.update(user_dirs(home))
    return exact, tree, programs


# =========================================================================
# Optimizar: programas conocidos
# =========================================================================

CATALOG: dict[str, tuple[str, ...]] = {
    "updater": (
        "update-notifier", "update-manager", "gnome-software", "plasma-discover", "discover-notifier",
        "mintupdate", "mintupdate-launcher", "pamac-tray", "apport-gtk",
    ),
    "widget": (
        "gnome-calendar", "gnome-weather", "gnome-clocks", "evolution-alarm-notify", "zeitgeist-daemon",
    ),
    "cloud": (
        "dropbox", "nextcloud", "megasync", "insync", "onedrive", "rclone", "syncthing", "pcloud",
        "google-drive-ocamlfuse",
    ),
    "browser": (
        "firefox", "firefox-bin", "firefox-esr", "chrome", "chromium", "chromium-browser", "brave",
        "brave-browser", "opera", "vivaldi-bin", "msedge", "librewolf", "epiphany", "falkon",
    ),
    "comms": (
        "discord", "slack", "teams", "teams-for-linux", "zoom", "skypeforlinux", "telegram-desktop",
        "signal-desktop", "element-desktop", "thunderbird", "mumble", "ts3client_linux_amd64", "whatsdesk",
    ),
    "media": (
        "spotify", "obs", "vlc", "mpv", "rhythmbox", "audacious", "audacity", "clementine", "strawberry",
        "elisa", "totem", "celluloid",
    ),
    "launcher": (
        "steam", "steamwebhelper", "heroic", "lutris", "bottles", "itch", "minigalaxy", "gamescope",
    ),
    "gpu": (
        "nvidia-settings", "corectrl", "mangohud", "goverlay",
    ),
    "peripheral": (
        "solaar", "piper", "openrgb", "ckb-next", "blueman-applet", "blueman-tray", "polychromatic-tray-applet",
        "easyeffects", "pavucontrol", "input-remapper-gtk", "antimicrox",
    ),
    "network": (
        "openvpn", "nm-applet", "tailscaled", "protonvpn-app", "nordvpnd", "mullvad-gui", "wg-quick",
    ),
}
CATEGORY_OF = {name: cat for cat, names in CATALOG.items() for name in names}

# Procesos auxiliares que siempre pertenecen al programa que los lanzó
HELPERS = {"chrome_crashpad_handler", "crashpad_handler", "chrome-sandbox", "bwrap", "xdg-dbus-proxy"}

# Utilidades de dispositivos que no están en el catálogo: se reconocen por el nombre.
PERIPHERAL_HINTS = ("wacom", "touchpad", "synaptics", "logi", "razer", "corsair", "steelseries", "bluetooth")
