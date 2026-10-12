"""Estilo del marco nativo de la ventana en Windows 11 (barra de título y borde).

Usa DwmSetWindowAttribute (dwmapi) para pintar la barra de título y el borde con los
colores de la marca y redondear las esquinas, sin librerías externas. En Windows 10
antiguo o si la llamada falla, simplemente se deja el marco por defecto.

También reúne la geometría de las ventanas: en qué monitor están, cuánto sitio útil hay
y cómo recolocarlas para que no se pierdan al mover la ventana o cambiar la resolución.
"""

from __future__ import annotations

import sys
from typing import Any

# Atributos de DwmSetWindowAttribute (Windows 10 20H1+/Windows 11)
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_DWMWCP_ROUND = 2


_user32_dll = None


def _tcl_error() -> type[BaseException]:
    """El error de Tk (la ventana ya no existe), sin obligar a tener tkinter para usar la
    parte de geometría de este módulo, que es aritmética pura."""
    tk = sys.modules.get("tkinter")
    return tk.TclError if tk is not None else OSError


def _user32() -> Any:
    """user32.dll, cargada solo desde System32 y una sola vez."""
    global _user32_dll
    if sys.platform != "win32":
        raise OSError("user32 solo existe en Windows")
    if _user32_dll is None:
        from ..plat.windows import system_dll
        _user32_dll = system_dll("user32")
    return _user32_dll


def _colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)   # COLORREF = 0x00BBGGRR


_GCLP_HICONSM = -34
_SM_CXSMICON, _SM_CYSMICON = 49, 50
_SWP_FRAME = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020   # sin mover, redimensionar ni activar: solo el marco
_blank_icon: int | None = None


def _hwnd(root: Any) -> int:
    """La ventana con marco (la de Tk es hija suya)."""
    from ctypes import wintypes
    user32 = _user32()
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    child = root.winfo_id()
    return int(user32.GetParent(child) or child)


def hide_caption_icon(root: Any) -> None:
    """Deja sin dibujo el icono de la barra de título: el logo ya está en la propia interfaz.

    Windows pinta ahí el icono «pequeño» de la clase de ventana; se sustituye por uno
    transparente. No se le da un icono propio a la ventana, porque entonces la barra de
    tareas usaría ese (vacío): así sigue enseñando el del programa, como hasta ahora. La
    clase es la de todas las ventanas de la aplicación, así que los diálogos tampoco lo
    llevan. Se puede llamar las veces que haga falta: solo actúa si Tk ha repuesto el suyo."""
    global _blank_icon
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = _user32()
        if _blank_icon is None:
            user32.GetSystemMetrics.restype = ctypes.c_int
            user32.GetSystemMetrics.argtypes = [ctypes.c_int]
            user32.CreateIcon.restype = wintypes.HICON
            user32.CreateIcon.argtypes = [wintypes.HINSTANCE, ctypes.c_int, ctypes.c_int, ctypes.c_ubyte,
                                          ctypes.c_ubyte, ctypes.c_char_p, ctypes.c_char_p]
            w = user32.GetSystemMetrics(_SM_CXSMICON) or 16
            h = user32.GetSystemMetrics(_SM_CYSMICON) or 16
            size = ((w + 15) // 16) * 2 * h   # filas de 1 bit por píxel, alineadas a 16 bits
            # Máscara toda a 1 (transparente) y color todo a 0: un icono que no pinta nada.
            _blank_icon = int(user32.CreateIcon(None, w, h, 1, 1, b"\xff" * size, b"\x00" * size) or 0)
        if not _blank_icon:
            return
        user32.GetClassLongPtrW.restype = ctypes.c_size_t
        user32.GetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetClassLongPtrW.restype = ctypes.c_size_t
        user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, wintypes.UINT]
        hwnd = _hwnd(root)
        if user32.GetClassLongPtrW(hwnd, _GCLP_HICONSM) != _blank_icon:
            user32.SetClassLongPtrW(hwnd, _GCLP_HICONSM, _blank_icon)
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, _SWP_FRAME)   # que el marco se vuelva a pintar
    except (OSError, AttributeError, ImportError, _tcl_error()):
        pass   # sin esa llamada se queda el icono de siempre


def apply(root: Any, caption: str, text: str, border: str) -> bool:
    """Pinta la barra de título (fondo/letras), el borde y redondea las esquinas. Devuelve
    si Windows ha aceptado los colores de la barra (Windows 11); en los anteriores, no."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        from ..plat.windows import system_dll   # las DLL de Windows, solo desde System32

        root.update_idletasks()
        user32 = _user32()
        user32.GetParent.restype = wintypes.HWND
        user32.GetParent.argtypes = [wintypes.HWND]
        child = root.winfo_id()
        hwnd = user32.GetParent(child) or child
        dwm = system_dll("dwmapi")
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        handle = wintypes.HWND(hwnd)

        def set_attr(attr: int, value: int) -> bool:
            val = ctypes.c_int(value)
            return dwm.DwmSetWindowAttribute(handle, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0

        set_attr(_DWMWA_USE_IMMERSIVE_DARK_MODE, 1)       # botones del sistema en claro
        painted = set_attr(_DWMWA_CAPTION_COLOR, _colorref(caption))
        painted = set_attr(_DWMWA_TEXT_COLOR, _colorref(text)) and painted
        set_attr(_DWMWA_BORDER_COLOR, _colorref(border))
        set_attr(_DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)
        return painted
    except (OSError, AttributeError, ImportError, _tcl_error()):
        return False   # en Windows antiguo no existen esos atributos: se queda el marco por defecto


# =========================================================================
# Geometría: que la ventana nunca se pierda fuera de la pantalla
# =========================================================================

Rect = tuple[int, int, int, int]   # izquierda, arriba, derecha, abajo


def fit_rect(x: int, y: int, w: int, h: int, area: Rect) -> Rect:
    """Mete un rectángulo (x, y, ancho, alto) entero dentro del área: lo encoge si no cabe
    y lo recoloca si se sale. Devuelve (x, y, ancho, alto)."""
    left, top, right, bottom = area
    w, h = max(1, min(w, right - left)), max(1, min(h, bottom - top))
    return min(max(x, left), right - w), min(max(y, top), bottom - h), w, h


def keep_reachable(x: int, y: int, w: int, h: int, area: Rect, grab: int = 120,
                   title: int = 40) -> tuple[int, int]:
    """Posición más cercana a (x, y) con la que la ventana sigue siendo alcanzable: la barra
    de título dentro del área y al menos «grab» píxeles de ancho a la vista. Una ventana a
    medias fuera de la pantalla (algo normal al aparcarla en un lado) no se toca."""
    left, top, right, bottom = area
    grab = min(grab, w)
    return min(max(x, left - w + grab), right - grab), min(max(y, top), max(top, bottom - title))


def rescale_rect(x: int, y: int, w: int, h: int, old: Rect, new: Rect,
                 min_size: tuple[int, int] = (1, 1)) -> Rect:
    """Traslada un rectángulo de un área de pantalla a otra conservando las proporciones:
    ocupa la misma fracción de la pantalla y queda en el mismo sitio relativo."""
    ow, oh = max(1, old[2] - old[0]), max(1, old[3] - old[1])
    fx, fy = (new[2] - new[0]) / ow, (new[3] - new[1]) / oh
    return fit_rect(new[0] + round((x - old[0]) * fx), new[1] + round((y - old[1]) * fy),
                    max(min_size[0], round(w * fx)), max(min_size[1], round(h * fy)), new)


def monitor_info(win: Any) -> tuple[str, Rect, Rect]:
    """(nombre, rectángulo completo, área útil sin barra de tareas) del monitor en el que
    está la ventana. Sin Windows, o si falla, se usa la pantalla que conoce Tk."""
    full = (0, 0, win.winfo_screenwidth(), win.winfo_screenheight())
    if sys.platform != "win32":
        return "", full, full
    try:
        import ctypes
        from ctypes import wintypes

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                        ("szDevice", wintypes.WCHAR * 32)]

        user32 = _user32()
        user32.GetParent.restype = wintypes.HWND
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        child = win.winfo_id()
        hwnd = user32.GetParent(child) or child
        monitor = user32.MonitorFromWindow(hwnd, 2)   # MONITOR_DEFAULTTONEAREST
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return "", full, full
        m, k = info.rcMonitor, info.rcWork
        return info.szDevice, (m.left, m.top, m.right, m.bottom), (k.left, k.top, k.right, k.bottom)
    except (OSError, AttributeError, _tcl_error()):
        return "", full, full   # se usa la pantalla que conoce Tk


def mouse_button_down() -> bool:
    """True mientras el usuario mantiene pulsado el ratón (p. ej. arrastrando la ventana)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        user32 = _user32()
        user32.GetAsyncKeyState.restype = ctypes.c_short
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        return bool(user32.GetAsyncKeyState(0x01) & 0x8000 or user32.GetAsyncKeyState(0x02) & 0x8000)
    except (OSError, AttributeError):
        return False   # sin esa función no se sabe: se supone que no hay arrastre


def outer_rect(win: Any) -> tuple[Rect, int, int]:
    """((x, y, ancho, alto) del marco exterior, borde lateral, alto de la barra de título)."""
    x, y = win.winfo_x(), win.winfo_y()
    border = max(0, win.winfo_rootx() - x)
    caption = max(0, win.winfo_rooty() - y)
    return (x, y, win.winfo_width() + 2 * border, win.winfo_height() + caption + border), border, caption


def set_outer_rect(win: Any, x: int, y: int, w: int, h: int, border: int, caption: int) -> None:
    win.geometry(f"{max(1, w - 2 * border)}x{max(1, h - caption - border)}+{x}+{y}")


def place_dialog(dlg: Any, parent: Any, vertical: float = 1 / 3) -> None:
    """Centra un diálogo sobre su ventana, sin dejar que se salga de la pantalla ni que sea
    más grande que ella (con zoom alto o pantallas pequeñas se encoge y aparece entero)."""
    dlg.update_idletasks()
    top = parent.winfo_toplevel()
    _name, _full, area = monitor_info(top)
    _rect, border, caption = outer_rect(top)   # un diálogo lleva el mismo marco que la ventana
    caption = caption or 32
    req_w, req_h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    x = top.winfo_rootx() + (top.winfo_width() - req_w) // 2 - border
    y = top.winfo_rooty() + int((top.winfo_height() - req_h) * vertical) - caption
    x, y, w, h = fit_rect(x, y, req_w + 2 * border, req_h + caption + border, area)
    if w < req_w + 2 * border or h < req_h + caption + border:
        dlg.geometry(f"{max(1, w - 2 * border)}x{max(1, h - caption - border)}+{x}+{y}")
    else:
        dlg.geometry(f"+{x}+{y}")
