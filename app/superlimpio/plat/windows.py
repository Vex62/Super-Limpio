"""Windows: envoltorios mínimos de su API mediante ctypes, y sus listas de datos.

Solo se usan funciones documentadas y habituales (kernel32, psapi, shell32, user32,
dwmapi). No se inyecta código, no se tocan servicios ni se modifica el registro (solo
se lee), y nunca se pide acceso a la memoria de otros procesos.

El módulo se puede importar en cualquier sistema (fuera de Windows las funciones dan
valores neutros): así los tests de su lógica pura corren en cualquier equipo.
"""

from __future__ import annotations

import datetime as _dt
import ntpath
import os
import re
import string
import sys
from typing import Any

from .. import i18n
from .windows_know import expand as _expand, split_command
from .common import (CLOUD_ONLY_MASK, FILE_ATTRIBUTE_REPARSE_POINT, PRIORITY_ABOVE_NORMAL,  # noqa: F401
                     PRIORITY_BELOW_NORMAL, PRIORITY_IDLE, PRIORITY_NORMAL, MemoryStatus, PerfInfo,
                     RawProcess, WindowInfo)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg
    import ctypes
    from ctypes import wintypes

    _LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800

    def system_dll(name: str, use_last_error: bool = False) -> ctypes.WinDLL:
        """Carga una DLL de Windows SOLO desde System32. Por nombre a secas, Windows la
        buscaría antes en la carpeta de la aplicación, donde cualquiera podría dejar una
        copia falsa (dwmapi.dll, bcrypt.dll…)."""
        return ctypes.WinDLL(name, use_last_error=use_last_error, winmode=_LOAD_LIBRARY_SEARCH_SYSTEM32)

    kernel32 = system_dll("kernel32", use_last_error=True)
    psapi = system_dll("psapi", use_last_error=True)
    shell32 = system_dll("shell32", use_last_error=True)
    user32 = system_dll("user32", use_last_error=True)
    ole32 = system_dll("ole32")

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

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8)]

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", wintypes.LPVOID),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
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
    _SetProcessInformation: Any
    _dwmapi: Any
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
    kernel32.GetSystemDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel32.GetWindowsDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel32.GetLogicalDrives.restype = wintypes.DWORD
    kernel32.GetLogicalDrives.argtypes = []
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    shell32.IsUserAnAdmin.restype = wintypes.BOOL
    shell32.IsUserAnAdmin.argtypes = []
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                                             ctypes.POINTER(ctypes.c_void_p)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    ole32.CoTaskMemFree.restype = None
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    try:
        _dwmapi = system_dll("dwmapi")
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


# =========================================================================
# Carpetas del sistema y del usuario: se le preguntan a Windows, no al entorno
# =========================================================================

_FOLDER_LOCAL_APPDATA = "F1B32785-6FBA-4FCF-9D55-7B8E7F157091"
_FOLDER_ROAMING_APPDATA = "3EB685DB-65F9-4CF6-A03A-E3EF65729F3D"
_FOLDER_PROFILE = "5E6C858F-0E22-4760-9AFE-EA3317B67173"
_FOLDER_PROGRAM_DATA = "62AB5D82-FDC1-4DC3-A9DD-070D1D495D97"


def _known_folder(folder_id: str, env: str) -> str:
    """Carpeta conocida de Windows (SHGetKnownFolderPath). Una variable del entorno la puede
    cambiar cualquier programa; esto es lo que Windows tiene anotado. Si la llamada falla
    (o fuera de Windows, en los tests), se usa la variable."""
    if IS_WINDOWS:
        import uuid
        guid = GUID.from_buffer_copy(uuid.UUID(folder_id).bytes_le)
        out = ctypes.c_void_p()
        try:
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0 and out.value:
                return ctypes.wstring_at(out.value)
        except OSError:
            pass   # se cae a la variable del entorno
        finally:
            if out.value:
                ole32.CoTaskMemFree(out)
    value = os.environ.get(env, "")
    return ntpath.normpath(value) if value and ntpath.isabs(value) and ntpath.splitdrive(value)[0] else ""


def _api_dir(getter_name: str, fallback: str) -> str:
    if IS_WINDOWS:
        buf = ctypes.create_unicode_buffer(32768)
        try:
            if getattr(kernel32, getter_name)(buf, len(buf)):
                return buf.value
        except OSError:
            pass   # se cae al valor por defecto
    return fallback


def windows_dir() -> str:
    return _api_dir("GetWindowsDirectoryW", os.environ.get("WINDIR") or r"C:\Windows")


def system_dir() -> str:
    return _api_dir("GetSystemDirectoryW", ntpath.join(os.environ.get("WINDIR") or r"C:\Windows", "System32"))


def system_exe(name: str) -> str:
    """Ruta completa de un programa de Windows (System32). Nunca se lanza por su nombre a
    secas: Windows lo buscaría antes en la carpeta actual y en el PATH."""
    return ntpath.join(system_dir(), name)


def _explorer() -> str:
    return ntpath.join(windows_dir(), "explorer.exe")


def _user_dir() -> str:
    base = _known_folder(_FOLDER_LOCAL_APPDATA, "LOCALAPPDATA")
    return ntpath.join(base, "SuperLimpio") if base else ""


def state_dir() -> str:
    """Carpeta del usuario para el registro de acciones y las órdenes al auxiliar."""
    return _user_dir()


def config_dir() -> str:
    """Carpeta del usuario para las preferencias cuando la de la aplicación no se puede escribir."""
    return _user_dir()


def prepare_process() -> None:
    """Ajustes del proceso al arrancar: texto nítido en pantallas con escalado (125 %, 150 %...)."""
    if not IS_WINDOWS:
        return
    try:
        shcore = system_dll("shcore")
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness(1)  # System DPI aware
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass   # Windows muy antiguo: la ventana se ve igual, algo menos nítida


_instance_mutex = None


def acquire_instance_lock() -> bool:
    """True si esta es la única ventana de Super Limpio de la sesión. Dos a la vez podrían
    lanzar dos limpiezas sobre las mismas carpetas."""
    global _instance_mutex
    if not IS_WINDOWS or _instance_mutex:
        return True
    handle = kernel32.CreateMutexW(None, False, "Local\\SuperLimpio.una-sola-ventana")
    if not handle:
        return True   # no se pudo comprobar: no se impide trabajar
    if ctypes.get_last_error() == 183:   # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _instance_mutex = handle   # se suelta solo al terminar el proceso
    return True


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
        return []
    if hasattr(os, "listdrives"):  # Python 3.12+
        try:
            return sorted(os.listdrives())
        except OSError:
            pass
    mask = kernel32.GetLogicalDrives()
    return [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask & (1 << i)]


def memory_status() -> MemoryStatus | None:
    if not IS_WINDOWS:
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

def _filetime_seconds(ft: Any) -> float:
    return float(((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 10_000_000)


def list_processes() -> list[RawProcess]:
    if not IS_WINDOWS:
        return []
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


def _open_verified(access: int, pid: int, create_time: float | None) -> Any:
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


def _set_throttling(h: Any, on: bool) -> bool:
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

def list_windows() -> list[WindowInfo]:
    """Ventanas principales visibles (las que saldrían en Alt+Tab), con su proceso."""
    if not IS_WINDOWS:
        return []
    GW_OWNER, GWL_EXSTYLE, WS_EX_TOOLWINDOW, DWMWA_CLOAKED = 4, -20, 0x80, 14
    out: list[WindowInfo] = []
    buf = ctypes.create_unicode_buffer(512)

    def visit(hwnd: Any, _lparam: Any) -> Any:
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
    if verb == "runas" and cwd is None:
        cwd = system_dir()   # lo elevado nunca arranca en una carpeta que escriba el usuario
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
        return shell_execute(_explorer(), f'"{path}"')
    return shell_execute(_explorer(), f'/select,"{path}"')


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


def reopen_program(path: str) -> tuple[bool, str]:
    """Vuelve a abrir un programa que se cerró. Si esta ventana corre como administrador
    se abre a través del Explorador, que lo lanza con los permisos normales del usuario:
    un programa corriente no debe heredar los de administrador."""
    if is_admin():
        return shell_execute(_explorer(), f'"{path}"')
    return shell_execute(path)


def helper_command(script: str, request: str, digest: str) -> tuple[str, str]:
    """(ejecutable, parámetros) con los que se lanza el auxiliar elevado para UNA orden.

    La orden va en un archivo y su huella SHA-256 en la línea de comandos: el auxiliar solo
    la acepta si coinciden. Con python/pythonw se añade «-I» (modo aislado) para que el
    proceso elevado no haga caso a PYTHONPATH ni a los paquetes del usuario; SuperLimpio.exe
    ya arranca siempre así."""
    order = f'--auxiliar "{request}" --sha256 {digest}'
    exe = sys.executable
    if not ntpath.basename(exe).lower().startswith("python"):
        return exe, order   # SuperLimpio.exe ya sabe dónde está la aplicación
    if exe.lower().endswith("python.exe"):
        alt = exe[:-10] + "pythonw.exe"
        if os.path.exists(alt):
            exe = alt
    return exe, f'-I "{script}" {order}'


def run_elevated(exe: str, params: str, timeout: float = 3600.0) -> tuple[bool, str, int]:
    """Lanza un programa con elevación (Windows muestra su aviso UAC), espera a que termine
    y devuelve (se lanzó, mensaje, código de salida)."""
    if not IS_WINDOWS:
        return False, i18n.t("common.windows_only"), -1
    SEE_MASK_NOCLOSEPROCESS, SEE_MASK_NOASYNC, SEE_MASK_FLAG_NO_UI = 0x40, 0x100, 0x400
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC | SEE_MASK_FLAG_NO_UI
    info.lpVerb = "runas"
    info.lpFile = exe
    info.lpParameters = params
    info.lpDirectory = system_dir()
    info.nShow = 1
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.get_last_error()
        if err == 1223:   # ERROR_CANCELLED: se contestó «No» al aviso UAC
            return False, i18n.t("winapi.elevation_cancelled"), -1
        return False, i18n.t("winapi.shellexec_code", rc=err), -1
    if not info.hProcess:
        return False, i18n.t("winapi.shellexec_code", rc=0), -1
    try:
        if kernel32.WaitForSingleObject(info.hProcess, int(timeout * 1000)) != 0:
            return False, i18n.t("winapi.elevation_timeout"), -1
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code)):
            return False, i18n.t("winapi.shellexec_code", rc=ctypes.get_last_error()), -1
        return True, i18n.t("winapi.launched"), int(code.value)
    finally:
        kernel32.CloseHandle(info.hProcess)


def capabilities() -> dict[str, bool]:
    """Lo que esta plataforma sabe hacer; la interfaz esconde lo que no."""
    return {
        "elevate": True,         # hay un auxiliar que hace con elevación una orden concreta
        "trim": True,            # recortar la RAM de un proceso
        "boost": True,           # subir la prioridad del programa objetivo
        "throttle_undo": True,   # el modo de eficiencia se puede deshacer
        "windows": True,         # se sabe qué programas tienen una ventana abierta
        "apps_settings": True,   # hay un panel del sistema para las apps de la tienda
    }


# =========================================================================
# Limpieza: ubicaciones conocidas de Windows
# =========================================================================

def _temp_dir(local_appdata: str) -> str:
    """La carpeta temporal del usuario. %TEMP% es una variable que cualquiera puede cambiar:
    solo se acepta si apunta a una carpeta llamada Temp o Tmp; si no, se usa la de Windows."""
    raw = os.environ.get("TEMP") or os.environ.get("TMP") or ""
    path = ntpath.normpath(os.path.expandvars(raw)) if raw else ""
    if path and ntpath.splitdrive(path)[0] and ntpath.isabs(path) \
            and ntpath.basename(path).lower() in ("temp", "tmp"):
        return path
    return ntpath.join(local_appdata, "Temp") if local_appdata else ""


def _browser_profiles(base: str) -> list[str]:
    """Rutas de caché de navegadores Chromium para todos los perfiles."""
    out = []
    for sub in (r"Cache\Cache_Data", "Code Cache", "GPUCache", r"Service Worker\CacheStorage"):
        out.append(os.path.join(base, "*", sub))
    out.append(os.path.join(base, "ShaderCache"))
    out.append(os.path.join(base, "GrShaderCache"))
    return out


def cleaner_categories() -> list[dict[str, Any]]:
    """Categorías de limpieza. Cada una es una lista blanca cerrada de ubicaciones; «risk»
    es el valor de safety.Risk (1 bajo · 2 medio · 3 alto)."""
    # Rutas absolutas pedidas a Windows. Si alguna no se conoce queda vacía, y las ubicaciones
    # que dependen de ella se descartan (nunca se convierten en rutas relativas).
    L = _known_folder(_FOLDER_LOCAL_APPDATA, "LOCALAPPDATA") or "?"
    A = _known_folder(_FOLDER_ROAMING_APPDATA, "APPDATA") or "?"
    U = _known_folder(_FOLDER_PROFILE, "USERPROFILE") or "?"
    W = windows_dir() or "?"
    P = _known_folder(_FOLDER_PROGRAM_DATA, "ProgramData") or "?"
    T = _temp_dir("" if L == "?" else L) or "?"

    def cat(cat_id: str, group: str, **kw: Any) -> dict[str, Any]:
        for key in ("dirs", "files"):
            if key in kw:
                kw[key] = [p for p in kw[key] if not p.startswith("?")]
        return {"id": cat_id, "group": group, **kw}

    return [
        # ----------------------------------------------------------- Windows
        cat("temp_user", "Windows", dirs=[T], min_age_hours=24, risk=1),
        cat("temp_win", "Windows", dirs=[rf"{W}\Temp"], min_age_hours=24, risk=2, admin=True),
        cat("thumbs", "Windows",
            files=[rf"{L}\Microsoft\Windows\Explorer\thumbcache_*.db",
                   rf"{L}\Microsoft\Windows\Explorer\iconcache_*.db"], risk=1),
        cat("wer", "Windows",
            dirs=[rf"{L}\Microsoft\Windows\WER", rf"{P}\Microsoft\Windows\WER\ReportArchive",
                  rf"{P}\Microsoft\Windows\WER\ReportQueue", rf"{P}\Microsoft\Windows\WER\Temp"],
            risk=1),
        cat("dumps", "Windows",
            dirs=[rf"{L}\CrashDumps"], files=[rf"{W}\Minidump\*.dmp", rf"{W}\MEMORY.DMP"],
            risk=1),
        cat("wu", "Windows",
            dirs=[rf"{W}\SoftwareDistribution\Download"], risk=2, admin=True, default_on=False),
        cat("do", "Windows",
            dirs=[rf"{W}\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache"],
            risk=2, admin=True, default_on=False),
        cat("recycle", "Windows", special="recycle_bin", risk=3, default_on=False),
        # ------------------------------------------------------- Navegadores
        cat("edge", "Navegadores", dirs=_browser_profiles(rf"{L}\Microsoft\Edge\User Data"),
            close_apps="msedge.exe"),
        cat("chrome", "Navegadores", dirs=_browser_profiles(rf"{L}\Google\Chrome\User Data"),
            close_apps="chrome.exe"),
        cat("brave", "Navegadores",
            dirs=_browser_profiles(rf"{L}\BraveSoftware\Brave-Browser\User Data"), close_apps="brave.exe"),
        cat("firefox", "Navegadores",
            dirs=[rf"{L}\Mozilla\Firefox\Profiles\*\cache2"], close_apps="firefox.exe"),
        # ------------------------------------------------------- Desarrollo
        cat("pip", "Desarrollo", dirs=[rf"{L}\pip\Cache"], default_on=False),
        cat("npm", "Desarrollo",
            dirs=[rf"{L}\npm-cache", rf"{A}\npm-cache", rf"{L}\Yarn\Cache", rf"{L}\pnpm-cache"],
            default_on=False),
        cat("nuget", "Desarrollo",
            dirs=[rf"{L}\NuGet\v3-cache", rf"{L}\NuGet\plugins-cache"], default_on=False),
        cat("gradle", "Desarrollo", dirs=[rf"{U}\.gradle\caches"], default_on=False),
        cat("cargo", "Desarrollo", dirs=[rf"{U}\.cargo\registry\cache"], default_on=False),
        cat("vscode", "Desarrollo",
            dirs=[rf"{A}\Code\Cache", rf"{A}\Code\CachedData", rf"{A}\Code\CachedExtensionVSIXs",
                  rf"{A}\Code\Code Cache", rf"{A}\Code\GPUCache"], close_apps="Code.exe"),
        # --------------------------------------------------------- Programas
        cat("discord", "Aplicaciones",
            dirs=[rf"{A}\discord\Cache", rf"{A}\discord\Code Cache", rf"{A}\discord\GPUCache",
                  rf"{A}\Slack\Cache", rf"{A}\Slack\Code Cache",
                  rf"{L}\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView\Default\Cache"],
            default_on=False),
        cat("dx", "Aplicaciones",
            dirs=[rf"{L}\D3DSCache", rf"{L}\NVIDIA\DXCache", rf"{L}\NVIDIA\GLCache", rf"{L}\AMD\DxCache"],
            default_on=False),
    ]


# =========================================================================
# Arranque: qué se inicia con Windows (solo lectura del registro)
# =========================================================================

_APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


def _approved_map(hive: Any, sub: str, view: int) -> dict[str, bool]:
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


def startup_entries() -> list[dict[str, Any]]:
    """Entradas de arranque: {name, command, location, enabled (None = una sola vez), exe}."""
    if not IS_WINDOWS:
        return []
    items: list[dict[str, Any]] = []
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
                    exe, _ = split_command(_expand(cmd) if "%" in cmd else cmd)
                    items.append({"name": name or i18n.t("startup.default_name"), "command": cmd,
                                  "location": label, "exe": exe,
                                  "enabled": approved.get(name.lower(), True) if approved_sub else None})
        except OSError:
            continue

    folders = [
        (_expand(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"),
         i18n.t("startup.src.folder_user"), winreg.HKEY_CURRENT_USER),
        (_expand(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\StartUp"),
         i18n.t("startup.src.folder_all"), winreg.HKEY_LOCAL_MACHINE),
    ]
    for folder, label, hive in folders:
        approved = _approved_map(hive, "StartupFolder", 0)
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name.lower() == "desktop.ini":
                        continue
                    items.append({"name": entry.name, "command": entry.path, "location": label,
                                  "exe": entry.path, "enabled": approved.get(entry.name.lower(), True)})
        except OSError:
            continue
    return items


def open_startup_manager() -> tuple[bool, str]:
    """Abre el Administrador de tareas por la pestaña Inicio: la vía oficial y reversible."""
    return shell_execute(system_exe("taskmgr.exe"), "/0 /startup")


# =========================================================================
# Programas instalados (lectura del registro) y su desinstalador oficial
# =========================================================================

UNINSTALL_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


def _read_value(key: Any, name: str) -> Any:
    try:
        val, _typ = winreg.QueryValueEx(key, name)
        return val
    except OSError:
        return None


def _fmt_install_date(raw: Any) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if re.fullmatch(r"\d{8}", s):
        try:
            return _dt.datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return s
    return s


def installed_programs() -> list[dict[str, Any]]:
    """Programas instalados, como diccionarios con los campos de programs.Program."""
    if not IS_WINDOWS:
        return []
    sources = [
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY, "machine64", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY, "machine32", "HKLM"),
        (winreg.HKEY_CURRENT_USER, 0, "user", "HKCU"),
    ]
    seen: set[tuple[str, str]] = set()
    programs: list[dict[str, Any]] = []
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
                        programs.append(dict(
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
    programs.sort(key=lambda p: p["name"].lower())
    return programs



def uninstall_command(p: Any) -> tuple[str, str, list[str], bool]:
    """(ejecutable, parámetros, avisos, crítico) para desinstalar con el desinstalador
    oficial del programa. «Crítico» = usa un intérprete de comandos."""
    warnings: list[str] = []
    critical = False
    if p.msi_code:
        # Windows Installer: /X = desinstalar (nunca /I, que reinstala/modifica)
        exe, params = system_exe("msiexec.exe"), f"/x {p.msi_code}"
    else:
        exe, params = split_command(p.uninstall_string)
        if ntpath.basename(exe).lower() == "msiexec.exe":
            params = re.sub(r"(?i)/I(\s*\{)", r"/X\1", params)
    if exe and not ntpath.dirname(exe):
        # Nombre a secas («MsiExec.exe», «rundll32»): se lanza el de System32, no el que
        # aparezca antes en la carpeta actual o en el PATH.
        named = exe if ntpath.splitext(exe)[1] else exe + ".exe"
        if not IS_WINDOWS or os.path.isfile(system_exe(named)):
            exe = system_exe(named)
        else:
            warnings.append(i18n.t("programs.warn.not_absolute", name=exe))
            critical = True
    base = ntpath.basename(exe).lower()
    if ntpath.isabs(exe) and IS_WINDOWS and not os.path.exists(exe):
        warnings.append(i18n.t("programs.warn.missing"))
    if base in ("cmd.exe", "powershell.exe", "pwsh.exe", "wscript.exe", "cscript.exe", "rundll32.exe"):
        warnings.append(i18n.t("programs.warn.interpreter", base=base))
        critical = True
    if p.scope.startswith("machine"):
        warnings.append(i18n.t("programs.warn.machine"))
    return exe, params, warnings, critical


def open_apps_settings() -> tuple[bool, str]:
    """Las apps de Microsoft Store se quitan desde Configuración."""
    return shell_execute("ms-settings:appsfeatures")


# =========================================================================
# Herramientas del sistema: comandos oficiales de Windows
# =========================================================================

def system_tools() -> list[dict[str, Any]]:
    """Herramientas que se ofrecen; «risk» es el valor de safety.Risk (hasta 4, crítico)."""
    def tool(tool_id: str, exe: str, params: str = "", **kw: Any) -> dict[str, Any]:
        return {"id": tool_id, "exe": exe, "params": params, **kw}

    # Todo por su ruta completa de System32: ni el intérprete de comandos ni lo que este
    # lanza se buscan por nombre. «/k ""ruta" argumentos"» es la forma de cmd.exe de recibir
    # un programa entre comillas con sus argumentos.
    cmd, dism, powercfg = system_exe("cmd.exe"), system_exe("Dism.exe"), system_exe("powercfg.exe")

    def console(program: str, args: str) -> str:
        return f'/k ""{program}" {args}"'

    return [
        tool("storage", "ms-settings:storagesense"),
        tool("apps", "ms-settings:appsfeatures"),
        tool("taskmgr_startup", system_exe("taskmgr.exe"), "/0 /startup"),
        tool("cleanmgr", system_exe("cleanmgr.exe")),
        tool("restore", system_exe("SystemPropertiesProtection.exe")),
        tool("analyze_sxs", cmd, console(dism, "/Online /Cleanup-Image /AnalyzeComponentStore"),
             admin=True, risk=2, keep_console=True),
        tool("clean_sxs", cmd, console(dism, "/Online /Cleanup-Image /StartComponentCleanup"),
             admin=True, risk=4, keep_console=True),
        tool("hiber_off", cmd, console(powercfg, "/hibernate off"),
             admin=True, risk=4, keep_console=True),
        tool("hiber_on", cmd, console(powercfg, "/hibernate on"),
             admin=True, risk=3, keep_console=True),
    ]


def run_system_tool(exe: str, params: str = "", admin: bool = False, keep_console: bool = False) -> tuple[bool, str]:
    """Las que requieren administrador se lanzan con «runas»: Windows muestra su aviso UAC."""
    return shell_execute(exe, params or None, verb="runas" if admin else "open")
