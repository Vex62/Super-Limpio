"""Punto de entrada de Super Limpio.

Ejecutar:  SuperLimpio.exe   (o SuperLimpio.bat, o runtime\\python\\pythonw.exe -I app\\main.py)

Con «--auxiliar <orden> --sha256 <huella>» no abre la ventana: es el auxiliar elevado, que
hace UNA operación concreta que la ventana le ha encargado (ver superlimpio/helper.py).
"""

import os
import signal
import sys
import traceback

MIN_PYTHON = (3, 11)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Con python/pythonw el código compilado (.pyc) se guarda en UNA sola carpeta,
# runtime\_pycache, en vez de repartirse por el proyecto. Así la ventana abre en torno
# a 1 s antes a partir de la segunda vez. Se puede borrar cuando se quiera: se regenera sola.
# Con SuperLimpio.exe se usan los __pycache__ normales, junto a cada archivo: el zip
# portable ya los trae hechos y siguen valiendo aunque la carpeta se mueva de sitio.
if not sys.pycache_prefix and os.path.basename(sys.executable).lower().startswith("python"):
    sys.pycache_prefix = os.path.join(os.path.dirname(_APP_DIR), "runtime", "_pycache")
# La aplicación se lanza en modo aislado (-I), que no añade a la búsqueda de módulos ni la
# carpeta del script ni la actual: hay que añadir la del propio programa, que es fija y es
# esta misma carpeta (no una ruta que venga de fuera).
sys.path.insert(0, _APP_DIR)


def _utf8_console() -> None:
    """La consola de Windows no es UTF-8: sin esto, imprimir un nombre de archivo con
    caracteres que no caben en su página de códigos lanza UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)   # con pythonw no hay consola: es None
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass   # consola redirigida a algo que no admite cambios: se queda como está


def _setup_language() -> None:
    """Fija el idioma: el guardado en la configuración o, la primera vez, el del sistema."""
    from superlimpio import config, i18n
    lang = config.get("language")
    if not lang:
        lang = i18n.detect_os_language()
    i18n.set_language(lang)


def _show_error(title: str, body: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, body)
        root.destroy()
    except Exception:  # noqa: BLE001 - sin tkinter o sin pantalla, el aviso va a la consola
        print(body)


def _check_integrity(interactive: bool = True) -> bool:
    """Verifica la firma de la distribución. Devuelve False si está manipulada."""
    from superlimpio import i18n, integrity
    from superlimpio.safety import log_action

    result = integrity.verify_distribution()
    if result.ok:
        if result.enforced:
            log_action("integridad", "", "ok")
        return True
    log_action("integridad", "", result.detail, ok=False)
    if interactive:
        _show_error(i18n.t("integrity.tampered_title"), i18n.t("integrity.tampered_body", detail=result.detail))
    return False


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print("Super Limpio needs Python {}.{} or newer.".format(*MIN_PYTHON))
        return 1
    _utf8_console()

    from superlimpio import plat
    plat.prepare_process()
    _setup_language()
    from superlimpio import i18n

    if "--auxiliar" in sys.argv[1:]:
        # Auxiliar elevado: sin ventana. Si la copia está manipulada, no hace nada.
        if not _check_integrity(interactive=False):
            return 2
        from superlimpio import helper
        return helper.main(sys.argv[1:])

    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(i18n.t("main.need_tkinter"))
        return 1

    if not _check_integrity():
        return 2

    if not plat.acquire_instance_lock():
        _show_error(i18n.t("app.already_open.title"), i18n.t("app.already_open.body"))
        return 3

    from superlimpio import recovery
    from superlimpio.safety import close_log, log_action
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
        # La traza completa va al registro; en pantalla, solo un mensaje claro.
        text = "".join(traceback.format_exception(exc, val, tb))
        log_action("error_interno", "", text[-1500:], ok=False)
        traceback.print_exception(exc, val, tb)
        from superlimpio.ui import dialogs
        dialogs.error(app.root, i18n.t("error.unexpected.title"),
                      i18n.t("error.unexpected.body", detail=str(val)))

    def terminate(_signum, _frame) -> None:
        # Petición de cierre del sistema (apagado, «kill»): se cierra con orden, sin preguntas.
        app.terminate()

    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), terminate)
            except (OSError, ValueError):
                pass   # esa señal no se puede capturar en este sistema

    app.root.report_callback_exception = report
    # Cuando la ventana lleva unos segundos en pie, el arranque se considera correcto.
    app.root.after(4000, recovery.mark_started)
    try:
        app.run()
    finally:
        recovery.mark_started()
        close_log()
    return 0


if __name__ == "__main__":
    sys.exit(main())
