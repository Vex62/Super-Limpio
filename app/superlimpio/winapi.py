"""Envoltorios mínimos de la API de Windows mediante ctypes.

Solo se usan funciones documentadas y habituales (kernel32, psapi, shell32).
No se inyecta código, no se tocan servicios ni se modifica el registro.
En sistemas que no son Windows todas las funciones devuelven valores neutros,
lo que permite ejecutar los tests de lógica en cualquier plataforma.
"""

from __future__ import annotations

import os
import string
import sys
from dataclasses import dataclass

from . import i18n
from .util import IS_WINDOWS

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)

    # ---------------------------------------------------------------- memoria
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("i64Size", ctypes.c_longlong),
            ("i64NumItems", ctypes.c_longlong),
        ]

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    shell32.ShellExecuteW.argtypes = [
        wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.LPCWSTR, ctypes.c_int]
    shell32.SHQueryRecycleBinW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(SHQUERYRBINFO)]
    shell32.SHEmptyRecycleBinW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD]
    shell32.SHFileOperationW.argtypes = [ctypes.POINTER(SHFILEOPSTRUCTW)]

    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_TERMINATE = 0x0001

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
CLOUD_ONLY_MASK = FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS


# =========================================================================
# Información general
# =========================================================================

def is_admin() -> bool:
    if not IS_WINDOWS:
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        return bool(shell32.IsUserAnAdmin())
    except OSError:
        return False


def list_drives() -> list[str]:
    """Devuelve las unidades montadas (C:\\, D:\\ ...)."""
    if not IS_WINDOWS:
        return ["/"]
    if hasattr(os, "listdrives"):  # Python 3.12+
        try:
            return sorted(os.listdrives())
        except OSError:
            pass
    mask = kernel32.GetLogicalDrives()
    return [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask & (1 << i)]


@dataclass
class MemoryStatus:
    total: int
    available: int
    load_pct: int
    commit_total: int
    commit_available: int

    @property
    def used(self) -> int:
        return self.total - self.available


def memory_status() -> MemoryStatus | None:
    if not IS_WINDOWS:
        try:
            info = {}
            with open("/proc/meminfo", encoding="ascii") as fh:
                for line in fh:
                    k, v = line.split(":", 1)
                    info[k] = int(v.strip().split()[0]) * 1024
            total, avail = info["MemTotal"], info["MemAvailable"]
            return MemoryStatus(total, avail, int((total - avail) * 100 / total), 0, 0)
        except (OSError, KeyError, ValueError):
            return None
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return MemoryStatus(st.ullTotalPhys, st.ullAvailPhys, st.dwMemoryLoad,
                        st.ullTotalPageFile, st.ullAvailPageFile)


# =========================================================================
# Procesos
# =========================================================================

@dataclass
class RawProcess:
    pid: int
    ppid: int
    name: str
    threads: int
    path: str = ""
    working_set: int = 0
    private: int = 0
    cpu_time: float = 0.0  # segundos de CPU acumulados (kernel + usuario)
    accessible: bool = False


def _filetime_seconds(ft) -> float:
    return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 10_000_000


def list_processes() -> list[RawProcess]:
    if not IS_WINDOWS:
        return _list_processes_posix()
    procs: list[RawProcess] = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return procs
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            procs.append(RawProcess(entry.th32ProcessID, entry.th32ParentProcessID,
                                    entry.szExeFile, entry.cntThreads))
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    buf = ctypes.create_unicode_buffer(32768)
    t_create, t_exit, t_kernel, t_user = (wintypes.FILETIME() for _ in range(4))
    for p in procs:
        if p.pid == 0:
            continue
        # Solo el permiso mínimo de consulta: basta para leer contadores de memoria, ruta
        # y tiempos de CPU. Nunca se pide acceso a la memoria de otros procesos.
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, p.pid)
        if not h:
            continue
        try:
            p.accessible = True
            if psapi.GetProcessMemoryInfo(h, ctypes.byref(counters), counters.cb):
                p.working_set = counters.WorkingSetSize
                p.private = counters.PrivateUsage
            size = wintypes.DWORD(len(buf))
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                p.path = buf.value
            if kernel32.GetProcessTimes(h, ctypes.byref(t_create), ctypes.byref(t_exit),
                                        ctypes.byref(t_kernel), ctypes.byref(t_user)):
                p.cpu_time = _filetime_seconds(t_kernel) + _filetime_seconds(t_user)
        finally:
            kernel32.CloseHandle(h)
    return procs


def _list_processes_posix() -> list[RawProcess]:
    """Implementación mínima para desarrollo/tests fuera de Windows."""
    out = []
    page = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
    tick = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
    for d in os.listdir("/proc") if os.path.isdir("/proc") else []:
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat", encoding="utf-8", errors="replace") as fh:
                stat = fh.read()
            name = stat[stat.index("(") + 1: stat.rindex(")")]
            fields = stat[stat.rindex(")") + 2:].split()
            with open(f"/proc/{d}/statm", encoding="ascii") as fh:
                statm = fh.read().split()
            try:
                path = os.readlink(f"/proc/{d}/exe")
            except OSError:
                path = ""
            out.append(RawProcess(
                pid=int(d), ppid=int(fields[1]), name=name, threads=int(fields[17]), path=path,
                working_set=int(statm[1]) * page,
                private=(int(statm[1]) - int(statm[2])) * page,
                cpu_time=(int(fields[11]) + int(fields[12])) / tick, accessible=True))
        except (OSError, ValueError, IndexError):
            continue
    return out


def terminate_process(pid: int) -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    h = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h:
        return False, i18n.t("winapi.proc_access_denied", err=ctypes.get_last_error())
    try:
        if kernel32.TerminateProcess(h, 1):
            return True, i18n.t("winapi.proc_ended")
        return False, i18n.t("winapi.proc_fail", err=ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(h)


# =========================================================================
# Shell: abrir, ejecutar, papelera
# =========================================================================

def shell_execute(file: str, params: str | None = None, verb: str = "open",
                  cwd: str | None = None, show: int = 1) -> tuple[bool, str]:
    """Lanza un programa mediante ShellExecute (respeta UAC: Windows pide elevación
    si el ejecutable la requiere). Nunca se usa un intérprete de comandos intermedio
    salvo que el llamante lo indique explícitamente."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    rc = shell32.ShellExecuteW(None, verb, file, params, cwd, show)
    rc = rc or 0
    if rc > 32:
        return True, i18n.t("winapi.launched")
    if rc == 5:
        return False, i18n.t("winapi.access_denied")
    if rc in (2, 3):
        return False, i18n.t("winapi.not_found")
    return False, i18n.t("winapi.shellexec_code", rc=rc)


def open_in_explorer(path: str) -> tuple[bool, str]:
    """Abre el Explorador seleccionando el elemento."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    path = os.path.normpath(path)
    if os.path.isdir(path):
        return shell_execute("explorer.exe", f'"{path}"')
    return shell_execute("explorer.exe", f'/select,"{path}"')


def recycle_bin_info(drive: str | None = None) -> tuple[int, int]:
    """(bytes, elementos) en la papelera."""
    if not IS_WINDOWS:
        return 0, 0
    info = SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
    if shell32.SHQueryRecycleBinW(drive, ctypes.byref(info)) != 0:
        return 0, 0
    return int(info.i64Size), int(info.i64NumItems)


def empty_recycle_bin() -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    SHERB_NOCONFIRMATION, SHERB_NOPROGRESSUI, SHERB_NOSOUND = 0x1, 0x2, 0x4
    # La confirmación la ha dado ya el usuario en nuestra ventana.
    hr = shell32.SHEmptyRecycleBinW(None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND)
    if hr in (0, -2147418113):  # S_OK o E_UNEXPECTED (papelera ya vacía)
        return True, i18n.t("winapi.bin_emptied")
    return False, i18n.t("winapi.bin_fail", hr=f"{hr & 0xFFFFFFFF:#x}")


def send_to_recycle_bin(paths: list[str]) -> tuple[bool, str]:
    """Mueve archivos/carpetas a la Papelera (recuperable). Si la unidad no tiene
    papelera, Windows mostrará su propio aviso antes de borrar definitivamente."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    if not paths:
        return True, i18n.t("winapi.recycle_nothing")
    FO_DELETE = 3
    FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO = 0x4, 0x10, 0x40
    FOF_NOERRORUI, FOF_WANTNUKEWARNING = 0x400, 0x4000
    joined = "\0".join(os.path.abspath(p) for p in paths) + "\0\0"
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = joined
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_WANTNUKEWARNING | FOF_SILENT | FOF_NOERRORUI
    rc = shell32.SHFileOperationW(ctypes.byref(op))
    if rc == 0 and not op.fAnyOperationsAborted:
        return True, i18n.t("winapi.recycle_done")
    if op.fAnyOperationsAborted:
        return False, i18n.t("winapi.recycle_cancelled")
    return False, i18n.t("winapi.recycle_fail", rc=f"{rc:#x}")


def admin_command(script: str) -> tuple[str, str]:
    """(ejecutable, parámetros) con los que se reabre la aplicación elevada."""
    exe = sys.executable
    if not os.path.basename(exe).lower().startswith("python"):
        return exe, ""  # SuperLimpio.exe ya sabe dónde está la aplicación
    if exe.lower().endswith("python.exe"):
        alt = exe[:-10] + "pythonw.exe"
        if os.path.exists(alt):
            exe = alt
    return exe, f'"{script}"'


def relaunch_as_admin(script: str) -> tuple[bool, str]:
    """Vuelve a abrir la aplicación con elevación. Windows muestra el aviso UAC."""
    exe, params = admin_command(script)
    return shell_execute(exe, params, verb="runas")
