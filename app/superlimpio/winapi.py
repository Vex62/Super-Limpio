"""Envoltorios mínimos de la API de Windows mediante ctypes.

Solo se usan funciones documentadas y habituales (kernel32, psapi, shell32, user32,
dwmapi). No se inyecta código, no se tocan servicios ni se modifica el registro, y
nunca se pide acceso a la memoria de otros procesos.
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
    user32 = ctypes.WinDLL("user32", use_last_error=True)

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

    class PERFORMANCE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("CommitTotal", ctypes.c_size_t),
            ("CommitLimit", ctypes.c_size_t),
            ("CommitPeak", ctypes.c_size_t),
            ("PhysicalTotal", ctypes.c_size_t),
            ("PhysicalAvailable", ctypes.c_size_t),
            ("SystemCache", ctypes.c_size_t),
            ("KernelTotal", ctypes.c_size_t),
            ("KernelPaged", ctypes.c_size_t),
            ("KernelNonpaged", ctypes.c_size_t),
            ("PageSize", ctypes.c_size_t),
            ("HandleCount", wintypes.DWORD),
            ("ProcessCount", wintypes.DWORD),
            ("ThreadCount", wintypes.DWORD),
        ]

    class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
        _fields_ = [
            ("Version", wintypes.ULONG),
            ("ControlMask", wintypes.ULONG),
            ("StateMask", wintypes.ULONG),
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
    psapi.GetPerformanceInfo.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    kernel32.GetPriorityClass.restype = wintypes.DWORD
    kernel32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    try:  # Windows 8+; el modo de eficiencia (EcoQoS) existe desde Windows 10 1709
        _SetProcessInformation = kernel32.SetProcessInformation
        _SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    except AttributeError:
        _SetProcessInformation = None

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.FindWindowExW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    try:
        _dwmapi = ctypes.WinDLL("dwmapi")
        _dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
        _dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p,
                                                  wintypes.DWORD]
    except (OSError, AttributeError):
        _dwmapi = None
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
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_SET_INFORMATION = 0x0200
    _STILL_ACTIVE = 259
    _PROCESS_POWER_THROTTLING = 4            # clase ProcessPowerThrottling
    _POWER_THROTTLING_EXECUTION_SPEED = 0x1

# Clases de prioridad (las mismas que muestra el Administrador de tareas)
PRIORITY_IDLE = 0x40
PRIORITY_BELOW_NORMAL = 0x4000
PRIORITY_NORMAL = 0x20
PRIORITY_ABOVE_NORMAL = 0x8000
PRIORITY_HIGH = 0x80
PRIORITY_REALTIME = 0x100

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
    create_time: float = 0.0  # instante de creación: con el PID identifica al proceso sin ambigüedad
    handles: int = 0
    priority: int = 0


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
    n_handles = wintypes.DWORD()
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
                p.create_time = _filetime_seconds(t_create)
            if kernel32.GetProcessHandleCount(h, ctypes.byref(n_handles)):
                p.handles = n_handles.value
            p.priority = kernel32.GetPriorityClass(h)
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
                cpu_time=(int(fields[11]) + int(fields[12])) / tick, accessible=True,
                create_time=int(fields[19]) / tick))
        except (OSError, ValueError, IndexError):
            continue
    return out


def _open_verified(access: int, pid: int, create_time: float | None):
    """Abre el proceso y comprueba que sigue siendo el mismo que se analizó.

    Windows reutiliza los PID: entre que el usuario confirma y se actúa, el proceso pudo
    terminar y su número pasar a otro programa. Si el instante de creación no coincide
    no se devuelve el identificador y no se toca nada."""
    h = kernel32.OpenProcess(access | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None, i18n.t("winapi.proc_access_denied", err=ctypes.get_last_error())
    if create_time:
        ft = [wintypes.FILETIME() for _ in range(4)]
        ok = kernel32.GetProcessTimes(h, *(ctypes.byref(f) for f in ft))
        if not ok or abs(_filetime_seconds(ft[0]) - create_time) > 0.001:
            kernel32.CloseHandle(h)
            return None, i18n.t("winapi.proc_changed")
    return h, ""


def terminate_process(pid: int, create_time: float | None = None) -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    h, why = _open_verified(PROCESS_TERMINATE, pid, create_time)
    if not h:
        return False, why
    try:
        if kernel32.TerminateProcess(h, 1):
            return True, i18n.t("winapi.proc_ended")
        return False, i18n.t("winapi.proc_fail", err=ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(h)


def process_alive(pid: int, create_time: float | None = None) -> bool:
    """True si ese mismo proceso (PID + instante de creación) sigue en ejecución."""
    if not IS_WINDOWS:
        return False
    h, _why = _open_verified(0, pid, create_time)
    if not h:
        return False
    try:
        code = wintypes.DWORD()
        return bool(kernel32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(h)


def _set_throttling(h, on: bool) -> bool:
    """Activa EcoQoS (el «Modo de eficiencia» de Windows 11) o lo devuelve al sistema."""
    if _SetProcessInformation is None:
        return False
    state = PROCESS_POWER_THROTTLING_STATE()
    state.Version = 1
    if on:
        state.ControlMask = _POWER_THROTTLING_EXECUTION_SPEED
        state.StateMask = _POWER_THROTTLING_EXECUTION_SPEED
    # ControlMask = 0 deja que Windows vuelva a decidir por sí mismo (el estado por defecto).
    return bool(_SetProcessInformation(h, _PROCESS_POWER_THROTTLING, ctypes.byref(state),
                                       ctypes.sizeof(state)))


def _safe_priority(priority: int) -> int:
    """Super Limpio nunca asigna «Alta» ni «Tiempo real»: pueden dejar el equipo sin respuesta."""
    if priority in (PRIORITY_IDLE, PRIORITY_BELOW_NORMAL, PRIORITY_NORMAL, PRIORITY_ABOVE_NORMAL):
        return priority
    return PRIORITY_NORMAL


def set_efficiency(pid: int, create_time: float | None = None) -> tuple[bool, str, int]:
    """Pone el proceso en modo de eficiencia: prioridad baja + EcoQoS. No lo cierra ni lo
    suspende, y es reversible. Devuelve (ok, mensaje, prioridad_anterior)."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only"), 0
    h, why = _open_verified(PROCESS_SET_INFORMATION, pid, create_time)
    if not h:
        return False, why, 0
    try:
        prev = kernel32.GetPriorityClass(h) or PRIORITY_NORMAL
        if not kernel32.SetPriorityClass(h, PRIORITY_IDLE):
            return False, i18n.t("winapi.proc_op_fail", err=ctypes.get_last_error()), prev
        _set_throttling(h, True)   # en Windows antiguo no existe: basta con la prioridad
        return True, i18n.t("winapi.proc_throttled"), prev
    finally:
        kernel32.CloseHandle(h)


def restore_efficiency(pid: int, priority: int, create_time: float | None = None) -> tuple[bool, str]:
    """Deshace set_efficiency: devuelve la prioridad anterior y quita EcoQoS."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    h, why = _open_verified(PROCESS_SET_INFORMATION, pid, create_time)
    if not h:
        return False, why
    try:
        _set_throttling(h, False)
        if kernel32.SetPriorityClass(h, _safe_priority(priority)):
            return True, i18n.t("winapi.proc_restored")
        return False, i18n.t("winapi.proc_op_fail", err=ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(h)


def set_priority(pid: int, priority: int, create_time: float | None = None) -> tuple[bool, str, int]:
    """Cambia la clase de prioridad. Devuelve (ok, mensaje, prioridad_anterior)."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only"), 0
    h, why = _open_verified(PROCESS_SET_INFORMATION, pid, create_time)
    if not h:
        return False, why, 0
    try:
        prev = kernel32.GetPriorityClass(h) or PRIORITY_NORMAL
        if kernel32.SetPriorityClass(h, _safe_priority(priority)):
            return True, i18n.t("winapi.proc_priority"), prev
        return False, i18n.t("winapi.proc_op_fail", err=ctypes.get_last_error()), prev
    finally:
        kernel32.CloseHandle(h)


def trim_working_set(pid: int, create_time: float | None = None) -> tuple[bool, str]:
    """Pide a Windows que saque de la RAM las páginas que el proceso no está usando.
    No se pierde nada: vuelven solas (algo más lentas) cuando el programa las necesita."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only")
    h, why = _open_verified(PROCESS_SET_QUOTA, pid, create_time)
    if not h:
        return False, why
    try:
        if psapi.EmptyWorkingSet(h):
            return True, i18n.t("winapi.proc_trimmed")
        return False, i18n.t("winapi.proc_op_fail", err=ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(h)


# =========================================================================
# Ventanas: qué procesos tienen una ventana a la vista
# =========================================================================

@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    title: str


def list_windows() -> list[WindowInfo]:
    """Ventanas principales visibles (las que saldrían en Alt+Tab), con su proceso."""
    if not IS_WINDOWS:
        return []
    GW_OWNER, GWL_EXSTYLE, WS_EX_TOOLWINDOW, DWMWA_CLOAKED = 4, -20, 0x80, 14
    out: list[WindowInfo] = []
    buf = ctypes.create_unicode_buffer(512)

    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        if user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        if _dwmapi is not None:  # ventanas «ocultas» de apps de la Tienda suspendidas
            cloaked = wintypes.DWORD()
            if _dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked),
                                             ctypes.sizeof(cloaked)) == 0 and cloaked.value:
                return True
        user32.GetWindowTextW(hwnd, buf, len(buf))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        # Las apps de la Tienda se dibujan dentro de ApplicationFrameHost: el proceso real
        # es el dueño de la ventana interior.
        core = user32.FindWindowExW(hwnd, None, "Windows.UI.Core.CoreWindow", None)
        if core:
            inner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(core, ctypes.byref(inner))
            if inner.value:
                pid = inner
        if pid.value:
            out.append(WindowInfo(int(hwnd or 0), pid.value, buf.value))
        return True

    callback = WNDENUMPROC(visit)
    user32.EnumWindows(callback, 0)
    return out


def close_window(hwnd: int) -> bool:
    """Pide a una ventana que se cierre (como pulsar su X). El programa decide: puede
    preguntar si guardar los cambios. No fuerza nada."""
    if not IS_WINDOWS:
        return False
    WM_CLOSE = 0x0010
    return bool(user32.PostMessageW(hwnd, WM_CLOSE, 0, 0))


# =========================================================================
# Contadores globales del sistema
# =========================================================================

@dataclass
class PerfInfo:
    commit_total: int
    commit_limit: int
    commit_peak: int
    system_cache: int
    kernel_paged: int
    kernel_nonpaged: int
    handles: int
    processes: int
    threads: int


def performance_info() -> PerfInfo | None:
    if not IS_WINDOWS:
        return None
    pi = PERFORMANCE_INFORMATION()
    pi.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
    if not psapi.GetPerformanceInfo(ctypes.byref(pi), pi.cb):
        return None
    page = pi.PageSize
    return PerfInfo(pi.CommitTotal * page, pi.CommitLimit * page, pi.CommitPeak * page,
                    pi.SystemCache * page, pi.KernelPaged * page, pi.KernelNonpaged * page,
                    pi.HandleCount, pi.ProcessCount, pi.ThreadCount)


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
