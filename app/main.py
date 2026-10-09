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


def _setup_language() -> None:
    """Fija el idioma: el guardado en la configuración o, la primera vez, el del sistema."""
    from superlimpio import config, i18n
    lang = config.get("language")
    if not lang:
        lang = i18n.detect_os_language()
    i18n.set_language(lang)


def _check_integrity() -> bool:
    """Verifica la firma de la distribución. Devuelve False si está manipulada."""
    from superlimpio import i18n, integrity
    from superlimpio.safety import log_action

    result = integrity.verify_distribution()
    if result.ok:
        if result.enforced:
            log_action("integridad", "", "ok")
        return True
    log_action("integridad", "", result.detail, ok=False)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(i18n.t("integrity.tampered_title"),
                             i18n.t("integrity.tampered_body", detail=result.detail))
        root.destroy()
    except Exception:  # noqa: BLE001
        print(i18n.t("integrity.tampered_body", detail=result.detail))
    return False


def main() -> int:
    if sys.version_info < (3, 10):
        print("Super Limpio needs Python 3.10 or newer.")
        return 1

    _setup_language()
    from superlimpio import i18n

    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(i18n.t("main.need_tkinter"))
        return 1
    _enable_dpi_awareness()

    if not _check_integrity():
        return 2

    from superlimpio import recovery
    from superlimpio.safety import log_action
    from superlimpio.ui.app import App

    # Recuperación: a petición (--recuperar) o si el arranque anterior no se completó.
    force_repair = any(a in ("--recuperar", "--repair") for a in sys.argv[1:])
    if force_repair or recovery.pending_recovery():
        actions = recovery.repair("manual" if force_repair else "unclean_shutdown")
        log_action("recuperacion", "", "; ".join(actions))
        _setup_language()  # la config pudo restablecerse: vuelve a fijar el idioma

    recovery.mark_starting()
    try:
        app = App()
    except Exception:  # noqa: BLE001 - un fallo al construir la UI dispara reparación y un reintento
        log_action("error_arranque", "", traceback.format_exc()[-1500:], ok=False)
        recovery.repair("startup_error")
        _setup_language()
        app = App()

    def report(exc, val, tb):
        text = "".join(traceback.format_exception(exc, val, tb))
        log_action("error_interno", "", text[-1500:], ok=False)
        traceback.print_exception(exc, val, tb)
        from superlimpio.ui import dialogs
        dialogs.error(app.root, i18n.t("error.unexpected.title"),
                      i18n.t("error.unexpected.body", detail=str(val)))

    app.root.report_callback_exception = report
    # Cuando la ventana lleva unos segundos en pie, el arranque se considera correcto.
    app.root.after(4000, recovery.mark_started)
    try:
        app.run()
    finally:
        recovery.mark_started()
    return 0


if __name__ == "__main__":
    sys.exit(main())
