"""Estilo del marco nativo de la ventana en Windows 11 (barra de título y borde).

Usa DwmSetWindowAttribute (dwmapi) para pintar la barra de título y el borde con los
colores de la marca y redondear las esquinas, sin librerías externas. En Windows 10
antiguo o si la llamada falla, simplemente se deja el marco por defecto.

También reúne la geometría de las ventanas: en qué monitor están, cuánto sitio útil hay
y cómo recolocarlas para que no se pierdan al mover la ventana o cambiar la resolución.
"""

from __future__ import annotations

import sys

# Atributos de DwmSetWindowAttribute (Windows 10 20H1+/Windows 11)
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_DWMWCP_ROUND = 2


def _colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)   # COLORREF = 0x00BBGGRR


def apply(root, caption: str, text: str, border: str) -> None:
    """Pinta la barra de título (fondo/letras), el borde y redondea las esquinas."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        root.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetParent.restype = wintypes.HWND
        user32.GetParent.argtypes = [wintypes.HWND]
        child = root.winfo_id()
        hwnd = user32.GetParent(child) or child
        dwm = ctypes.windll.dwmapi
        handle = wintypes.HWND(hwnd)

        def set_attr(attr: int, value: int) -> None:
            val = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(handle, ctypes.c_uint(attr), ctypes.byref(val), ctypes.sizeof(val))

        set_attr(_DWMWA_USE_IMMERSIVE_DARK_MODE, 1)       # botones del sistema en claro
        set_attr(_DWMWA_CAPTION_COLOR, _colorref(caption))
        set_attr(_DWMWA_TEXT_COLOR, _colorref(text))
        set_attr(_DWMWA_BORDER_COLOR, _colorref(border))
        set_attr(_DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)
    except Exception:  # noqa: BLE001 - en Windows antiguo se queda el marco por defecto
        pass


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


def monitor_info(win) -> tuple[str, Rect, Rect]:
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

        user32 = ctypes.windll.user32
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
    except Exception:  # noqa: BLE001
        return "", full, full


def mouse_button_down() -> bool:
    """True mientras el usuario mantiene pulsado el ratón (p. ej. arrastrando la ventana)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000
                    or ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000)
    except Exception:  # noqa: BLE001
        return False


def outer_rect(win) -> tuple[Rect, int, int]:
    """((x, y, ancho, alto) del marco exterior, borde lateral, alto de la barra de título)."""
    x, y = win.winfo_x(), win.winfo_y()
    border = max(0, win.winfo_rootx() - x)
    caption = max(0, win.winfo_rooty() - y)
    return (x, y, win.winfo_width() + 2 * border, win.winfo_height() + caption + border), border, caption


def set_outer_rect(win, x: int, y: int, w: int, h: int, border: int, caption: int) -> None:
    win.geometry(f"{max(1, w - 2 * border)}x{max(1, h - caption - border)}+{x}+{y}")


def place_dialog(dlg, parent, vertical: float = 1 / 3) -> None:
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
