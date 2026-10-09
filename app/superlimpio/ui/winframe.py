"""Estilo del marco nativo de la ventana en Windows 11 (barra de título y borde).

Usa DwmSetWindowAttribute (dwmapi) para pintar la barra de título y el borde con los
colores de la marca y redondear las esquinas, sin librerías externas. En Windows 10
antiguo o si la llamada falla, simplemente se deja el marco por defecto.
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
        child = root.winfo_id()
        hwnd = ctypes.windll.user32.GetParent(child) or child
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
