"""Linux: llamadas al sistema y listas de datos, solo con la biblioteca estándar.

Los procesos y la memoria se leen de /proc; la Papelera sigue la especificación de
FreeDesktop (la misma que usan los gestores de archivos); para abrir carpetas, lanzar
terminales o consultar paquetes se usan las herramientas que ya trae la distribución
(xdg-open, dpkg, rpm, flatpak...), y lo que no esté instalado simplemente no se ofrece.

Nunca se ejecuta nada como administrador por cuenta propia: las acciones que lo
necesitan se abren en una terminal con «sudo», donde el usuario ve el comando y
escribe su contraseña.
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse

from .. import i18n
from .common import (PRIORITY_ABOVE_NORMAL, PRIORITY_BELOW_NORMAL, PRIORITY_IDLE, PRIORITY_NORMAL,
                     MemoryStatus, PerfInfo, RawProcess, WindowInfo)

_PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
_TICK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
_NICE_OF = {PRIORITY_IDLE: 19, PRIORITY_BELOW_NORMAL: 10, PRIORITY_NORMAL: 0, PRIORITY_ABOVE_NORMAL: -5}


def _which(*names: str) -> str:
    """El primero de los programas que esté instalado ('' si ninguno)."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return ""


def _run(argv: list[str], timeout: float = 15.0, partial: bool = False) -> str:
    """Salida de un programa de consulta ('' si no existe, falla o tarda demasiado). Con
    partial=True vale lo que haya escrito aunque termine con error (dpkg lo hace cuando
    solo conoce parte de lo que se le pregunta)."""
    try:
        res = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, errors="replace",
                             env={**os.environ, "LC_ALL": "C"})
        return res.stdout if res.returncode == 0 or partial else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _spawn(argv: list[str]) -> tuple[bool, str]:
    """Lanza un programa sin esperar a que termine y sin atarlo a esta ventana."""
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True, i18n.t("winapi.launched")
    except FileNotFoundError:
        return False, i18n.t("winapi.not_found")
    except PermissionError:
        return False, i18n.t("winapi.access_denied")
    except OSError as exc:
        return False, str(exc.strerror or exc)


def capabilities() -> dict[str, bool]:
    """Lo que esta plataforma sabe hacer; la interfaz esconde lo que no."""
    root = is_admin()
    return {
        "elevate": False,          # una interfaz gráfica como root no es buena idea en Linux
        "trim": False,             # no hay forma estándar de recortar la RAM de otro proceso
        "boost": root,             # subir prioridad exige privilegios
        "throttle_undo": root,     # y devolver una prioridad bajada, también
        "windows": bool(_which("wmctrl")),
        "apps_settings": bool(_which("gnome-software", "plasma-discover", "mintinstall", "pamac-manager")),
    }


# =========================================================================
# Información general
# =========================================================================

def is_admin() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


_REAL_FS = {"ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs", "zfs", "vfat", "exfat", "ntfs", "ntfs3", "fuseblk",
            "reiserfs", "jfs", "bcachefs", "hfsplus", "apfs", "nfs", "nfs4", "cifs", "9p", "virtiofs"}


def list_drives() -> list[str]:
    """Puntos de montaje con archivos de verdad: la raíz y los demás discos."""
    out, seen = ["/"], {"/"}
    try:
        with open("/proc/mounts", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    devices: set[str] = set()
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount, fstype = parts[0], parts[1].replace("\\040", " "), parts[2]
        if fstype not in _REAL_FS or mount in seen:
            continue
        # Fuera lo que no son discos del usuario. /run/media sí lo es: ahí montan los USB
        # Fedora y Arch.
        if any(mount == d or mount.startswith(d + "/") for d in ("/boot", "/efi", "/snap", "/var/lib", "/sys",
                                                                  "/proc", "/dev")):
            continue
        if mount.startswith("/run/") and not mount.startswith("/run/media/"):
            continue
        if device in devices and fstype == "btrfs":   # subvolúmenes del mismo disco
            continue
        devices.add(device)
        seen.add(mount)
        out.append(mount)
    return out


def _meminfo() -> dict[str, int]:
    info: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="ascii", errors="replace") as fh:
            for line in fh:
                key, _sep, value = line.partition(":")
                parts = value.split()
                if parts and parts[0].isdigit():
                    info[key] = int(parts[0]) * 1024
    except OSError:
        pass
    return info


def memory_status() -> MemoryStatus | None:
    info = _meminfo()
    total = info.get("MemTotal", 0)
    if not total:
        return None
    avail = info.get("MemAvailable", info.get("MemFree", 0))
    # Linux reserva memoria «de más» a propósito: no hay un límite de compromiso comparable
    # al de Windows, así que esos dos datos se dejan a cero y no se enseñan.
    return MemoryStatus(total, avail, int((total - avail) * 100 / total), 0, 0)


def performance_info() -> PerfInfo | None:
    info = _meminfo()
    if not info:
        return None
    processes = threads = handles = 0
    try:
        with open("/proc/loadavg", encoding="ascii") as fh:
            threads = int(fh.read().split()[3].split("/")[1])
        processes = sum(1 for d in os.listdir("/proc") if d.isdigit())
        with open("/proc/sys/fs/file-nr", encoding="ascii") as fh:
            handles = int(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        pass
    return PerfInfo(info.get("Committed_AS", 0), 0, 0, info.get("Cached", 0) + info.get("Buffers", 0),
                    info.get("SReclaimable", 0), info.get("SUnreclaim", 0), handles, processes, threads)


# =========================================================================
# Procesos
# =========================================================================

def _stat_fields(pid: int) -> tuple[str, list[str]] | None:
    """(nombre corto, campos de /proc/PID/stat a partir del tercero) o None si ya no existe."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as fh:
            stat = fh.read()
        return stat[stat.index("(") + 1: stat.rindex(")")], stat[stat.rindex(")") + 2:].split()
    except (OSError, ValueError):
        return None


def _priority_of(nice: int) -> int:
    if nice == 0:
        return PRIORITY_NORMAL
    if nice < 0:
        return PRIORITY_ABOVE_NORMAL
    return PRIORITY_IDLE if nice >= 15 else PRIORITY_BELOW_NORMAL


def list_processes() -> list[RawProcess]:
    """Procesos en marcha. Los hilos del núcleo (no son programas ni ocupan memoria propia)
    se dejan fuera. De los procesos de otros usuarios solo se puede leer lo público."""
    out: list[RawProcess] = []
    me = os.geteuid() if hasattr(os, "geteuid") else -1
    try:
        pids = [int(d) for d in os.listdir("/proc") if d.isdigit()]
    except OSError:
        return out
    for pid in pids:
        got = _stat_fields(pid)
        if got is None:
            continue
        comm, f = got
        try:
            ppid = int(f[1])
            if pid == 2 or ppid == 2:   # kthreadd y sus hilos
                continue
            with open(f"/proc/{pid}/statm", encoding="ascii") as fh:
                statm = fh.read().split()
            try:
                path = os.readlink(f"/proc/{pid}/exe")
            except OSError:
                path = ""
            if path.endswith(" (deleted)"):   # el programa se actualizó mientras estaba abierto
                path = path[:-10]
            try:
                owner = os.stat(f"/proc/{pid}").st_uid
            except OSError:
                owner = -2
            resident, shared = int(statm[1]) * _PAGE, int(statm[2]) * _PAGE
            # El nombre de «stat» se corta a 15 letras: si se conoce el ejecutable, mejor el suyo.
            name = os.path.basename(path) if path and os.path.basename(path).startswith(comm[:15]) else comm
            out.append(RawProcess(
                pid=pid, ppid=ppid, name=name, threads=int(f[17]), path=path,
                working_set=resident, private=max(0, resident - shared),
                cpu_time=(int(f[11]) + int(f[12])) / _TICK,
                accessible=bool(path) or owner == me or me == 0,
                create_time=int(f[19]) / _TICK, priority=_priority_of(int(f[16]))))
        except (OSError, ValueError, IndexError):
            continue
    return out


def _same_process(pid: int, create_time: float | None) -> tuple[bool, str]:
    """Comprueba que ese PID sigue siendo el proceso que se analizó (los PID se reutilizan)."""
    got = _stat_fields(pid)
    if got is None:
        return False, i18n.t("winapi.proc_changed")
    try:
        if got[1][0] == "Z":   # zombi: ya terminó
            return False, i18n.t("winapi.proc_changed")
        if create_time and abs(int(got[1][19]) / _TICK - create_time) > 0.02:
            return False, i18n.t("winapi.proc_changed")
    except (ValueError, IndexError):
        return False, i18n.t("winapi.proc_changed")
    return True, ""


def process_alive(pid: int, create_time: float | None = None) -> bool:
    """True si ese mismo proceso (PID + instante de creación) sigue en ejecución."""
    return _same_process(pid, create_time)[0]


def _os_error(exc: OSError) -> str:
    if isinstance(exc, PermissionError):
        return i18n.t("winapi.proc_access_denied", err=exc.errno)
    return i18n.t("winapi.proc_fail", err=exc.errno)


def terminate_process(pid: int, create_time: float | None = None, grace: float = 1.5) -> tuple[bool, str]:
    """Pide al proceso que termine (SIGTERM) y, si no lo hace en un momento, lo finaliza
    (SIGKILL). Lo primero da ocasión al programa de cerrar bien sus archivos."""
    same, why = _same_process(pid, create_time)
    if not same:
        return False, why
    try:
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            time.sleep(0.1)
            if not process_alive(pid, create_time):
                return True, i18n.t("winapi.proc_ended")
        os.kill(pid, signal.SIGKILL)
        return True, i18n.t("winapi.proc_ended")
    except ProcessLookupError:
        return True, i18n.t("winapi.proc_ended")
    except OSError as exc:
        return False, _os_error(exc)


def _renice(pid: int, nice: int, create_time: float | None, done: str) -> tuple[bool, str, int]:
    same, why = _same_process(pid, create_time)
    if not same:
        return False, why, 0
    try:
        prev = os.getpriority(os.PRIO_PROCESS, pid)
        os.setpriority(os.PRIO_PROCESS, pid, nice)
        return True, i18n.t(done), _priority_of(prev)
    except PermissionError:
        return False, i18n.t("linux.nice_denied"), 0
    except OSError as exc:
        return False, i18n.t("winapi.proc_op_fail", err=exc.errno), 0


def set_efficiency(pid: int, create_time: float | None = None) -> tuple[bool, str, int]:
    """Baja la prioridad del proceso («nice» 10). No lo cierra ni lo suspende. Ojo: Linux
    solo deja devolverle la prioridad a un administrador (ver capabilities)."""
    return _renice(pid, 10, create_time, "winapi.proc_throttled")


def restore_efficiency(pid: int, priority: int, create_time: float | None = None) -> tuple[bool, str]:
    ok, msg, _prev = _renice(pid, _NICE_OF.get(priority, 0), create_time, "winapi.proc_restored")
    return ok, msg


def set_priority(pid: int, priority: int, create_time: float | None = None) -> tuple[bool, str, int]:
    """Cambia la prioridad. Nunca por encima de «algo más que normal»."""
    return _renice(pid, _NICE_OF.get(priority, 0), create_time, "winapi.proc_priority")


def trim_working_set(pid: int, create_time: float | None = None) -> tuple[bool, str]:
    return False, i18n.t("linux.not_available")


# =========================================================================
# Ventanas: solo si está instalado «wmctrl» (y la sesión es X11 o XWayland)
# =========================================================================

def list_windows() -> list[WindowInfo]:
    """Ventanas abiertas con su proceso. Sin wmctrl no se sabe, y se devuelve una lista vacía."""
    wmctrl = _which("wmctrl")
    if not wmctrl:
        return []
    out = []
    for line in _run([wmctrl, "-lp"], timeout=4).splitlines():
        parts = line.split(None, 4)   # id, escritorio, pid, equipo, título
        try:
            if len(parts) >= 5 and int(parts[1]) >= 0 and int(parts[2]) > 0 and parts[4].strip():
                out.append(WindowInfo(int(parts[0], 16), int(parts[2]), parts[4].strip()))
        except ValueError:
            continue
    return out


def close_window(hwnd: int) -> bool:
    """Pide a una ventana que se cierre (como pulsar su X). El programa decide."""
    wmctrl = _which("wmctrl")
    if not wmctrl:
        return False
    try:
        return subprocess.run([wmctrl, "-ic", hex(hwnd)], timeout=4, capture_output=True).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# =========================================================================
# Abrir, ejecutar y terminal
# =========================================================================

def shell_execute(file: str, params: str | None = None, verb: str = "open",
                  cwd: str | None = None, show: int = 1) -> tuple[bool, str]:
    """Lanza un programa con sus parámetros, o abre un archivo o carpeta con lo que el
    escritorio tenga asociado. Nunca pasa por un intérprete de comandos."""
    argv = [file] + (shlex.split(params) if params else [])
    if not params and not shutil.which(file) and (os.path.exists(file) or "://" in file):
        opener = _which("xdg-open", "gio")
        if not opener:
            return False, i18n.t("linux.no_opener")
        argv = [opener, "open", file] if os.path.basename(opener) == "gio" else [opener, file]
    return _spawn(argv)


def open_in_explorer(path: str) -> tuple[bool, str]:
    """Abre el gestor de archivos en esa carpeta (o en la que contiene el archivo, señalándolo
    si el gestor lo admite)."""
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        gdbus = _which("gdbus")
        if gdbus and os.path.exists(path):
            uri = "file://" + urllib.parse.quote(path)
            try:
                res = subprocess.run(
                    [gdbus, "call", "--session", "--dest", "org.freedesktop.FileManager1",
                     "--object-path", "/org/freedesktop/FileManager1",
                     "--method", "org.freedesktop.FileManager1.ShowItems", f"['{uri}']", ""],
                    capture_output=True, timeout=5)
                if res.returncode == 0:
                    return True, i18n.t("winapi.launched")
            except (OSError, subprocess.SubprocessError):
                pass
        path = os.path.dirname(path)
    return shell_execute(path)


# (programa, opción tras la que va el comando, True si lo quiere en UN solo argumento).
# Cada terminal lo pide a su manera, y con la opción equivocada se abre vacía o no se abre.
_TERMINALS = (
    ("gnome-terminal", ["--"], False), ("ptyxis", ["--"], False), ("kgx", ["-e"], False),
    ("konsole", ["-e"], False), ("xfce4-terminal", ["-x"], False), ("mate-terminal", ["-x"], False),
    ("tilix", ["-e"], False), ("terminator", ["-x"], False), ("lxterminal", ["-e"], True),
    ("qterminal", ["-e"], True), ("alacritty", ["-e"], False), ("kitty", [], False), ("foot", [], False),
    ("wezterm", ["start", "--"], False), ("xterm", ["-e"], False),
)


def _terminal() -> tuple[str, list[str], bool] | None:
    """La terminal que se usará: (ejecutable, opción, un solo argumento). Primero la que el
    usuario tiene elegida en su escritorio; si no hay forma de saberlo, la primera conocida."""
    exe = shutil.which("xdg-terminal-exec")
    if exe:
        return exe, [], False
    exe = shutil.which("x-terminal-emulator")   # la «alternativa» de Debian, Ubuntu y derivadas
    if exe:
        real = os.path.basename(os.path.realpath(exe))
        for name, flag, single in _TERMINALS:
            if real == name:   # apunta al programa tal cual: se le habla en su idioma
                return exe, flag, single
        return exe, ["-e"], False   # un envoltorio de la distribución: todos admiten «-e»
    for name, flag, single in _TERMINALS:
        exe = shutil.which(name)
        if exe:
            return exe, flag, single
    return None


def terminal_argv(command: str) -> list[str]:
    """Orden para abrir una terminal que ejecuta «command» y no se cierra hasta pulsar Intro,
    para que se pueda leer el resultado. Lista vacía si no hay ninguna terminal conocida."""
    script = f"{command}; echo; printf '%s' {shlex.quote(i18n.t('linux.press_enter'))}; read _"
    found = _terminal()
    if found is None:
        return []
    exe, flag, single = found
    inner = ["sh", "-c", script]
    return [exe, *flag, shlex.join(inner)] if single else [exe, *flag, *inner]


def run_in_terminal(command: str) -> tuple[bool, str]:
    argv = terminal_argv(command)
    if not argv:
        return False, i18n.t("linux.no_terminal")
    return _spawn(argv)


def admin_command(script: str) -> tuple[str, str]:
    """(ejecutable, parámetros) con los que se abriría la aplicación."""
    return sys.executable, shlex.quote(script)


def relaunch_as_admin(script: str) -> tuple[bool, str]:
    return False, i18n.t("linux.not_available")


# =========================================================================
# Papelera (especificación de FreeDesktop)
# =========================================================================

def _home_trash() -> str:
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(data, "Trash")


def _mount_point(path: str) -> str:
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def _trash_dirs() -> list[str]:
    """La papelera personal y las de los demás discos montados."""
    uid = os.getuid() if hasattr(os, "getuid") else 0
    dirs = [_home_trash()]
    for mount in list_drives():
        for candidate in (os.path.join(mount, ".Trash", str(uid)), os.path.join(mount, f".Trash-{uid}")):
            if os.path.isdir(os.path.join(candidate, "files")):
                dirs.append(candidate)
    return dirs


def _tree_size(path: str) -> int:
    total = 0
    try:
        if not os.path.isdir(path) or os.path.islink(path):
            return os.lstat(path).st_size
        for folder, _dirs, names in os.walk(path):
            for name in names:
                try:
                    total += os.lstat(os.path.join(folder, name)).st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def recycle_bin_info(drive: str | None = None) -> tuple[int, int]:
    """(bytes, elementos) en la papelera."""
    size = count = 0
    for trash in _trash_dirs():
        files = os.path.join(trash, "files")
        try:
            names = os.listdir(files)
        except OSError:
            continue
        count += len(names)
        size += sum(_tree_size(os.path.join(files, n)) for n in names)
    return size, count


def _remove(path: str) -> None:
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            os.remove(path)
        except OSError:
            pass


def empty_recycle_bin() -> tuple[bool, str]:
    left = 0
    for trash in _trash_dirs():
        for sub in ("files", "info"):
            folder = os.path.join(trash, sub)
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                _remove(os.path.join(folder, name))
            try:
                left += len(os.listdir(folder)) if sub == "files" else 0
            except OSError:
                pass
    if left:
        return False, i18n.t("winapi.bin_fail", hr=left)
    return True, i18n.t("winapi.bin_emptied")


def _trash_one(path: str) -> None:
    """Mueve un elemento a la papelera de su mismo disco y anota de dónde venía."""
    path = os.path.abspath(path)
    home_trash = _home_trash()
    os.makedirs(os.path.join(home_trash, "files"), mode=0o700, exist_ok=True)
    os.makedirs(os.path.join(home_trash, "info"), mode=0o700, exist_ok=True)
    device = os.lstat(path).st_dev
    if device == os.stat(home_trash).st_dev:
        trash, recorded = home_trash, path
    else:
        top = _mount_point(path)
        trash = os.path.join(top, f".Trash-{os.getuid()}")
        os.makedirs(os.path.join(trash, "files"), mode=0o700, exist_ok=True)
        os.makedirs(os.path.join(trash, "info"), mode=0o700, exist_ok=True)
        recorded = os.path.relpath(path, top)
    base = os.path.basename(path.rstrip("/")) or "archivo"
    name, n = base, 1
    while True:   # el archivo .trashinfo se crea en exclusiva: reserva el nombre sin carreras
        info_path = os.path.join(trash, "info", name + ".trashinfo")
        try:
            fd = os.open(info_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            n += 1
            name = f"{base}.{n}"
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("[Trash Info]\nPath=" + urllib.parse.quote(recorded) + "\nDeletionDate="
                 + _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "\n")
    try:
        os.rename(path, os.path.join(trash, "files", name))
    except OSError:
        os.remove(info_path)
        raise


def send_to_recycle_bin(paths: list[str]) -> tuple[bool, str]:
    """Mueve archivos/carpetas a la Papelera (recuperable desde el gestor de archivos).
    Si un elemento no se puede mover, se deja donde está: nunca se borra en su lugar."""
    if not paths:
        return True, i18n.t("winapi.recycle_nothing")
    failed = []
    for path in paths:
        try:
            _trash_one(path)
        except OSError as exc:
            failed.append(f"{path}: {exc.strerror or exc}")
    if failed:
        return False, i18n.t("winapi.recycle_fail", rc="\n".join(failed[:10]))
    return True, i18n.t("winapi.recycle_done")


# =========================================================================
# Limpieza: ubicaciones conocidas de Linux
# =========================================================================

def _chromium_caches(*bases: str) -> list[str]:
    out = []
    for base in bases:
        for sub in ("Cache", "Code Cache", "GPUCache", "Service Worker/CacheStorage"):
            out.append(os.path.join(base, "*", sub))
        out += [os.path.join(base, "ShaderCache"), os.path.join(base, "GrShaderCache")]
    return out


def cleaner_categories() -> list[dict]:
    """Categorías de limpieza. Cada una es una lista blanca cerrada de ubicaciones; «risk»
    es el valor de safety.Risk (1 bajo · 2 medio · 3 alto). No se toca /tmp: ahí viven
    archivos de programas en marcha, y el propio sistema lo vacía al reiniciar."""
    home = os.path.expanduser("~")
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")

    def cat(cat_id: str, group: str, **kw) -> dict:
        return {"id": cat_id, "group": group, **kw}

    def electron(name: str) -> list[str]:
        base = os.path.join(config, name)
        return [os.path.join(base, sub) for sub in ("Cache", "Code Cache", "GPUCache")]

    return [
        # ------------------------------------------------------------ Sistema
        cat("thumbs", "Linux", dirs=[os.path.join(cache, "thumbnails")], risk=1),
        cat("dumps", "Linux", dirs=["/var/crash", "/var/lib/systemd/coredump"], risk=1, admin=True),
        cat("pkgcache", "Linux",
            files=["/var/cache/apt/archives/*.deb", "/var/cache/apt/archives/partial/*",
                   "/var/cache/pacman/pkg/*.pkg.tar*"],
            dirs=["/var/cache/dnf", "/var/cache/yum", "/var/cache/zypp/packages"],
            risk=2, admin=True, default_on=False),
        cat("recycle", "Linux", special="recycle_bin", risk=3, default_on=False),
        # ------------------------------------------------------- Navegadores
        cat("chrome", "Navegadores",
            dirs=_chromium_caches(os.path.join(cache, "google-chrome"), os.path.join(cache, "chromium"),
                                  os.path.join(home, "snap/chromium/common/chromium")),
            close_apps="chrome"),
        cat("brave", "Navegadores",
            dirs=_chromium_caches(os.path.join(cache, "BraveSoftware/Brave-Browser")), close_apps="brave"),
        cat("edge", "Navegadores",
            dirs=_chromium_caches(os.path.join(cache, "microsoft-edge")), close_apps="msedge"),
        cat("firefox", "Navegadores",
            dirs=[os.path.join(cache, "mozilla/firefox/*/cache2"),
                  os.path.join(home, "snap/firefox/common/.cache/mozilla/firefox/*/cache2"),
                  os.path.join(home, ".var/app/org.mozilla.firefox/cache/mozilla/firefox/*/cache2")],
            close_apps="firefox"),
        # ------------------------------------------------------- Desarrollo
        cat("pip", "Desarrollo", dirs=[os.path.join(cache, "pip")], default_on=False),
        cat("npm", "Desarrollo",
            dirs=[os.path.join(home, ".npm/_cacache"), os.path.join(cache, "yarn"),
                  os.path.join(cache, "pnpm")], default_on=False),
        cat("nuget", "Desarrollo",
            dirs=[os.path.join(data, "NuGet/v3-cache"), os.path.join(data, "NuGet/http-cache"),
                  os.path.join(data, "NuGet/plugins-cache")], default_on=False),
        cat("gradle", "Desarrollo", dirs=[os.path.join(home, ".gradle/caches")], default_on=False),
        cat("cargo", "Desarrollo", dirs=[os.path.join(home, ".cargo/registry/cache")], default_on=False),
        cat("vscode", "Desarrollo",
            dirs=electron("Code") + [os.path.join(config, "Code/CachedData"),
                                     os.path.join(config, "Code/CachedExtensionVSIXs")], close_apps="code"),
        # --------------------------------------------------------- Programas
        cat("discord", "Aplicaciones", dirs=electron("discord") + electron("Slack"), default_on=False),
        cat("dx", "Aplicaciones",
            dirs=[os.path.join(cache, "mesa_shader_cache"), os.path.join(cache, "mesa_shader_cache_db"),
                  os.path.join(cache, "nvidia/GLCache"), os.path.join(home, ".nv/GLCache"),
                  os.path.join(cache, "radv_builtin_shaders")],
            default_on=False),
    ]


# =========================================================================
# Arranque: qué se inicia con la sesión (solo lectura)
# =========================================================================

def _desktop_entry(path: str) -> dict[str, str]:
    """Claves del grupo [Desktop Entry] de un archivo .desktop."""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            in_entry = False
            for line in fh:
                line = line.strip()
                if line.startswith("["):
                    in_entry = line == "[Desktop Entry]"
                elif in_entry and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    out.setdefault(key.strip(), value.strip())
    except OSError:
        pass
    return out


def _localized(entry: dict[str, str], key: str) -> str:
    lang = i18n.current()
    return entry.get(f"{key}[{lang}]") or entry.get(key, "")


def _exec_program(command: str) -> str:
    """Ruta del programa de una línea Exec= (sin «env VAR=x» ni códigos %f, %U...)."""
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    while words and (words[0] == "env" or "=" in words[0]):
        words.pop(0)
    if not words:
        return ""
    return words[0] if os.path.isabs(words[0]) else (shutil.which(words[0]) or "")


def startup_entries() -> list[dict]:
    """Entradas de arranque: {name, command, location, enabled, exe}. Son los .desktop de
    las carpetas «autostart» (los del usuario tapan a los del sistema del mismo nombre)
    y los servicios de usuario de systemd que están habilitados."""
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    items: list[dict] = []
    seen: set[str] = set()
    for folder, label in ((os.path.join(config, "autostart"), i18n.t("startup.src.autostart_user")),
                          ("/etc/xdg/autostart", i18n.t("startup.src.autostart_system"))):
        for path in sorted(glob.glob(os.path.join(folder, "*.desktop"))):
            base = os.path.basename(path)
            if base in seen:
                continue
            seen.add(base)
            entry = _desktop_entry(path)
            command = entry.get("Exec", "")
            off = (entry.get("Hidden", "").lower() == "true"
                   or entry.get("X-GNOME-Autostart-enabled", "").lower() == "false")
            items.append({"name": _localized(entry, "Name") or base[:-8], "command": command or path,
                          "location": label, "enabled": not off, "exe": _exec_program(command)})
    systemctl = _which("systemctl")
    if systemctl:
        listing = _run([systemctl, "--user", "list-unit-files", "--type=service", "--state=enabled",
                        "--no-legend", "--no-pager"], timeout=6)
        for line in listing.splitlines():
            unit = line.split()[0] if line.split() else ""
            if unit.endswith(".service") and "@" not in unit:
                items.append({"name": unit[:-8], "command": f"systemctl --user start {unit}",
                              "location": i18n.t("startup.src.systemd_user"), "enabled": True, "exe": ""})
    return items


def open_startup_manager() -> tuple[bool, str]:
    """Abre la herramienta de inicio del escritorio si la hay; si no, la carpeta «autostart»."""
    for name in ("gnome-session-properties", "gnome-tweaks", "xfce4-session-settings", "mate-session-properties"):
        exe = shutil.which(name)
        if exe:
            return _spawn([exe])
    kcm = _which("kcmshell6", "kcmshell5")
    if kcm:
        return _spawn([kcm, "kcm_autostart"])
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(config, "autostart")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return shell_execute(folder)


# =========================================================================
# Programas instalados: aplicaciones del menú y a qué paquete pertenecen
# =========================================================================

def _desktop_apps() -> dict[str, dict[str, str]]:
    """Aplicaciones del menú: ruta del .desktop -> sus claves. Se omiten las ocultas."""
    home = os.path.expanduser("~")
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    apps: dict[str, dict[str, str]] = {}
    for folder in ("/usr/share/applications", "/usr/local/share/applications", os.path.join(data, "applications")):
        for path in sorted(glob.glob(os.path.join(folder, "*.desktop"))):
            entry = _desktop_entry(path)
            if entry.get("Type", "Application") != "Application" or not entry.get("Name"):
                continue
            if entry.get("NoDisplay", "").lower() == "true" or entry.get("Hidden", "").lower() == "true":
                continue
            apps[path] = entry
    return apps


def _package_owners(paths: list[str]) -> dict[str, tuple[str, str]]:
    """ruta -> (gestor, paquete) para los archivos que pertenecen a un paquete del sistema."""
    owners: dict[str, tuple[str, str]] = {}
    paths = [p for p in paths if p.startswith("/usr/")]
    if not paths:
        return owners
    dpkg = _which("dpkg-query")
    if dpkg:
        for line in _run([dpkg, "-S", *paths], timeout=30, partial=True).splitlines():
            pkgs, _sep, path = line.partition(": ")
            if path.strip() in paths and pkgs:
                owners[path.strip()] = ("deb", pkgs.split(",")[0].strip().split(":")[0])
        if owners:
            return owners
    rpm = _which("rpm")
    if rpm:
        for path in paths:
            name = _run([rpm, "-qf", "--qf", "%{NAME}", path], timeout=10).strip()
            if name and " " not in name:
                owners[path] = ("rpm", name)
        if owners:
            return owners
    pacman = _which("pacman")
    if pacman:
        for path in paths:   # -Qqo no dice a qué archivo corresponde cada línea: uno a uno
            name = _run([pacman, "-Qqo", path], timeout=10).strip()
            if name:
                owners[path] = ("pacman", name)
    return owners


def _package_details(manager: str, names: set[str]) -> dict[str, tuple[str, int, str]]:
    """paquete -> (versión, bytes instalados, mantenedor)."""
    out: dict[str, tuple[str, int, str]] = {}
    if not names:
        return out
    if manager == "deb":
        listing = _run(["dpkg-query", "-W", "-f=${Package}\\t${Version}\\t${Installed-Size}\\t${Maintainer}\\n",
                        *sorted(names)], timeout=30)
        for line in listing.splitlines():
            f = line.split("\t")
            if len(f) >= 4:
                out[f[0]] = (f[1], int(f[2]) * 1024 if f[2].isdigit() else 0, f[3].split("<")[0].strip())
    elif manager == "rpm":
        listing = _run(["rpm", "-q", "--qf", "%{NAME}\\t%{VERSION}-%{RELEASE}\\t%{SIZE}\\t%{VENDOR}\\n",
                        *sorted(names)], timeout=30)
        for line in listing.splitlines():
            f = line.split("\t")
            if len(f) >= 4:
                out[f[0]] = (f[1], int(f[2]) if f[2].isdigit() else 0, "" if f[3] == "(none)" else f[3])
    elif manager == "pacman":
        for name in names:
            version = _run(["pacman", "-Q", name], timeout=10).split()
            out[name] = (version[1] if len(version) > 1 else "", 0, "")
    return out


def _parse_size(text: str) -> int:
    """«1,2 GB» / «350.4 MB» -> bytes."""
    parts = text.replace("\xa0", " ").split()
    if len(parts) != 2:
        return 0
    units = {"B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3}
    try:
        return int(float(parts[0].replace(",", ".")) * units.get(parts[1].upper(), 0))
    except ValueError:
        return 0


def installed_programs() -> list[dict]:
    """Programas instalados, como diccionarios con los campos de programs.Program: las
    aplicaciones del menú (con el paquete del sistema que las trae), las de Flatpak y
    las de Snap."""
    programs: list[dict] = []
    apps = _desktop_apps()
    owners = _package_owners(list(apps))
    details: dict[tuple[str, str], tuple[str, int, str]] = {}
    for manager in {m for m, _n in owners.values()}:
        for name, info in _package_details(manager, {n for m, n in owners.values() if m == manager}).items():
            details[(manager, name)] = info
    seen: set[tuple[str, str]] = set()
    for path, entry in apps.items():
        if "/flatpak/" in path or "/snapd/" in path:
            continue
        owner = owners.get(path)
        if owner is None:
            if not path.startswith(os.path.expanduser("~")):
                continue   # sin paquete y fuera del perfil: no hay forma oficial de quitarlo
            programs.append(dict(name=_localized(entry, "Name"), scope="user_app", reg_key=path,
                                 display_icon=_exec_program(entry.get("Exec", ""))))
            continue
        if owner in seen:
            continue
        seen.add(owner)
        version, size, vendor = details.get(owner, ("", 0, ""))
        programs.append(dict(name=_localized(entry, "Name"), publisher=vendor, version=version,
                             estimated_size=size, scope=owner[0], reg_key=owner[1],
                             display_icon=_exec_program(entry.get("Exec", ""))))
    flatpak = _which("flatpak")
    if flatpak:
        listing = _run([flatpak, "list", "--app", "--columns=application,name,version,size,installation"], timeout=20)
        for line in listing.splitlines():
            f = line.split("\t")
            if len(f) >= 5 and "." in f[0]:
                base = "/var/lib/flatpak" if f[4].strip() == "system" else os.path.join(
                    os.path.expanduser("~"), ".local/share/flatpak")
                programs.append(dict(name=f[1].strip() or f[0], version=f[2].strip(),
                                     estimated_size=_parse_size(f[3]), scope="flatpak", reg_key=f[0].strip(),
                                     install_location=os.path.join(base, "app", f[0].strip())))
    snap = _which("snap")
    if snap:
        for line in _run([snap, "list"], timeout=20).splitlines()[1:]:
            f = line.split()
            if len(f) >= 6 and not any(note in f[5] for note in ("base", "snapd", "core")) \
                    and f[0] not in ("snapd", "bare") and not f[0].startswith(("core", "gnome-", "gtk-", "kde-")):
                size = 0
                try:
                    size = os.path.getsize(f"/var/lib/snapd/snaps/{f[0]}_{f[2]}.snap")
                except OSError:
                    pass
                programs.append(dict(name=f[0], publisher=f[4].rstrip("*✓"), version=f[1], estimated_size=size,
                                     scope="snap", reg_key=f[0], install_location=f"/snap/{f[0]}/current"))
    programs.sort(key=lambda p: p["name"].lower())
    return programs


_REMOVE = {
    "deb": ("apt-get", "sudo apt-get remove {pkg}"),
    "rpm": ("dnf", "sudo dnf remove {pkg}"),
    "pacman": ("pacman", "sudo pacman -Rs {pkg}"),
    "flatpak": ("flatpak", "flatpak uninstall {pkg}"),
    "snap": ("snap", "sudo snap remove {pkg}"),
}


def uninstall_command(p) -> tuple:
    """(ejecutable, parámetros, avisos, crítico, texto a mostrar) para desinstalar con el
    gestor de paquetes, en una terminal: el gestor enseña lo que va a quitar y pide
    confirmación él mismo."""
    warnings: list[str] = []
    spec = _REMOVE.get(p.scope)
    if spec is None or not p.reg_key:
        return "", "", [i18n.t("linux.uninstall_manual", path=p.reg_key or p.name)], False, ""
    tool, template = spec
    if p.scope == "rpm" and not shutil.which("dnf"):
        tool, template = ("zypper", "sudo zypper remove {pkg}") if shutil.which("zypper") else ("yum", "sudo yum remove {pkg}")
    command = template.format(pkg=shlex.quote(p.reg_key))
    argv = terminal_argv(command)
    if not argv:
        return "", "", [i18n.t("linux.no_terminal")], False, command
    if not shutil.which(tool):
        warnings.append(i18n.t("programs.warn.missing"))
    if command.startswith("sudo "):
        warnings.append(i18n.t("linux.uninstall_sudo"))
    return argv[0], shlex.join(argv[1:]), warnings, False, command


def open_apps_settings() -> tuple[bool, str]:
    """Abre la tienda de aplicaciones del escritorio."""
    exe = _which("gnome-software", "plasma-discover", "mintinstall", "pamac-manager")
    return _spawn([exe]) if exe else (False, i18n.t("linux.not_available"))


# =========================================================================
# Herramientas del sistema: comandos oficiales de la distribución
# =========================================================================

def system_tools() -> list[dict]:
    """Herramientas que se ofrecen: solo las que están instaladas en este equipo."""
    def tool(tool_id: str, exe: str, params: str = "", **kw) -> dict:
        return {"id": tool_id, "exe": exe, "params": params, **kw}

    have = shutil.which
    out = []
    if have("baobab"):
        out.append(tool("lx_baobab", "baobab"))
    if have("journalctl"):
        out.append(tool("lx_journal_size", "journalctl", "--disk-usage", keep_console=True))
        out.append(tool("lx_journal_vacuum", "sudo", "journalctl --vacuum-time=2weeks",
                        admin=True, risk=3, keep_console=True))
    if have("apt-get"):
        out.append(tool("lx_apt_autoremove", "sudo", "apt-get autoremove", admin=True, risk=2, keep_console=True))
        out.append(tool("lx_apt_clean", "sudo", "apt-get clean", admin=True, risk=2, keep_console=True))
    if have("dnf"):
        out.append(tool("lx_dnf_autoremove", "sudo", "dnf autoremove", admin=True, risk=2, keep_console=True))
        out.append(tool("lx_dnf_clean", "sudo", "dnf clean all", admin=True, risk=2, keep_console=True))
    if have("paccache"):
        out.append(tool("lx_paccache", "sudo", "paccache -r", admin=True, risk=2, keep_console=True))
    if have("flatpak"):
        out.append(tool("lx_flatpak_unused", "flatpak", "uninstall --unused", risk=2, keep_console=True))
    if have("fstrim"):
        out.append(tool("lx_fstrim", "sudo", "fstrim -av", admin=True, risk=2, keep_console=True))
    return out


def run_system_tool(exe: str, params: str = "", admin: bool = False, keep_console: bool = False) -> tuple[bool, str]:
    """Las de consola se abren en una terminal que no se cierra sola; ahí pide «sudo» la
    contraseña cuando hace falta."""
    if keep_console or admin:
        return run_in_terminal(f"{exe} {params}".strip())
    return shell_execute(exe, params or None)
