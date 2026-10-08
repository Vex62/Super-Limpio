"""Punto de entrada de Super Limpio.

Ejecutar:  SuperLimpio.exe   (o SuperLimpio.bat, o runtime\\python\\pythonw.exe app\\main.py)
"""

import os
import sys
import traceback

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Con python/pythonw el código compilado (.pyc) se guarda en UNA sola carpeta,
# runtime\_pycache, en vez de repartirse por el proyecto. Así la ventana abre en torno
# a 1 s antes a partir de la segunda vez. Se puede borrar cuando se quiera: se regenera sola.
# Con SuperLimpio.exe se usan los __pycache__ normales, junto a cada archivo: el zip
# portable ya los trae hechos y siguen valiendo aunque la carpeta se mueva de sitio.
if not sys.pycache_prefix and os.path.basename(sys.executable).lower().startswith("python"):
    sys.pycache_prefix = os.path.join(os.path.dirname(_APP_DIR), "runtime", "_pycache")
sys.path.insert(0, _APP_DIR)


def _enable_dpi_awareness() -> None:
    """Texto nítido en pantallas con escalado (125 %, 150 %...)."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def main() -> int:
    if sys.version_info < (3, 10):
        print("Super Limpio necesita Python 3.10 o superior.")
        return 1
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Falta tkinter. Ejecuta preparar_entorno.bat para instalar el Python portable completo.")
        return 1
    _enable_dpi_awareness()

    from superlimpio.safety import log_action
    from superlimpio.ui.app import App

    app = App()

    def report(exc, val, tb):
        text = "".join(traceback.format_exception(exc, val, tb))
        log_action("error_interno", "", text[-1500:], ok=False)
        traceback.print_exception(exc, val, tb)
        from superlimpio.ui import dialogs
        dialogs.error(app.root, "Error inesperado",
                      f"{val}\n\nLa aplicación sigue funcionando. Detalle guardado en logs\\acciones.log")

    app.root.report_callback_exception = report
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
