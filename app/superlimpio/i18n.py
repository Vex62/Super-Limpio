"""Internacionalización (español / inglés) sin dependencias externas.

Todas las cadenas visibles de la aplicación viven en el diccionario CATALOG como
``clave -> {"en": ..., "es": ...}``. ``t("clave")`` devuelve la cadena en el idioma
activo (con ``.format(**kw)`` si se pasan argumentos). El idioma se fija al arrancar
(detectado del sistema o leído de la configuración) y, al cambiarlo, la interfaz se
reconstruye entera, por lo que ``t`` solo se evalúa al construir cada pantalla.
"""

from __future__ import annotations

import sys

LANGUAGES = [("en", "English"), ("es", "Español")]
_DEFAULT = "en"
_lang = _DEFAULT


# Sufijo de las entradas propias de este sistema ('' en Windows, que es el texto base)
_PLATFORM_SUFFIX = "" if sys.platform == "win32" else "@linux"


def available() -> list[tuple[str, str]]:
    return list(LANGUAGES)


def current() -> str:
    return _lang


def set_language(lang: str | None) -> str:
    global _lang
    codes = {c for c, _ in LANGUAGES}
    _lang = lang if lang in codes else _DEFAULT
    return _lang


def detect_os_language() -> str:
    """Idioma inicial a partir del sistema: español si Windows está en español."""
    import locale

    candidates: list[str] = []
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is not None:
            lang_id = windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            if lang_id == 0x0A:  # LANG_SPANISH
                return "es"
            candidates.append("en")
    except Exception:  # noqa: BLE001 - cualquier fallo cae en la detección estándar
        pass
    import os
    # En Linux y macOS el idioma lo dicen estas variables, por este orden de preferencia.
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(var, "")
        if value and value not in ("C", "POSIX"):
            candidates.append(value)
            break
    try:
        lang, _enc = locale.getlocale()
        if lang:
            candidates.append(lang)
    except (ValueError, OSError):
        pass
    for cand in candidates:
        if cand and cand.lower().startswith("es"):
            return "es"
    return _DEFAULT


def t(key: str, /, **kw) -> str:
    # «key» es solo posicional: así un texto puede tener un marcador {key} (o {n}, {text}...)
    # sin chocar con el nombre del parámetro.
    # Un texto que en otro sistema dice otra cosa tiene una segunda entrada «clave@sistema».
    entry = (CATALOG.get(key + _PLATFORM_SUFFIX) if _PLATFORM_SUFFIX else None) or CATALOG.get(key)
    if entry is None:
        return key.format(**kw) if kw else key
    text = entry.get(_lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


def plural(n: int, key: str, /, **kw) -> str:
    """Elige la forma singular/plural: usa las claves ``key.one`` y ``key.other``."""
    return t(f"{key}.one" if n == 1 else f"{key}.other", n=n, **kw)


# Formato numérico dependiente del idioma
def decimal_sep() -> str:
    return "," if _lang == "es" else "."


def group_sep() -> str:
    return "." if _lang == "es" else ","


def percent(text: str) -> str:
    return f"{text} %" if _lang == "es" else f"{text}%"


# =========================================================================
# Catálogo de traducciones
# =========================================================================
CATALOG: dict[str, dict[str, str]] = {
    # ----------------------------------------------------------------- común
    "common.ready": {"en": "Ready", "es": "Listo"},
    "common.cancel": {"en": "Cancel", "es": "Cancelar"},
    "common.continue": {"en": "Continue", "es": "Continuar"},
    "common.refresh": {"en": "Refresh", "es": "Actualizar"},
    "common.analyze": {"en": "Analyze", "es": "Analizar"},
    "common.stop": {"en": "Stop", "es": "Detener"},
    "common.search": {"en": "Search", "es": "Buscar"},
    "common.browse": {"en": "Browse…", "es": "Examinar…"},
    "common.open_location": {"en": "Open location", "es": "Abrir ubicación"},
    "common.open_explorer": {"en": "Open in File Explorer", "es": "Abrir en Explorador"},
    "common.copy_path": {"en": "Copy path", "es": "Copiar ruta"},
    "common.nothing_selected": {"en": "Nothing selected", "es": "Nada seleccionado"},
    "common.result": {"en": "Result", "es": "Resultado"},
    "common.protected": {"en": "Protected", "es": "Protegido"},
    "common.error": {"en": "Error", "es": "Error"},
    "common.deleting": {"en": "Deleting…", "es": "Eliminando…"},
    "common.windows_only": {"en": "Only available on Windows", "es": "Solo disponible en Windows"},
    "common.recycle": {"en": "Send to Recycle Bin…", "es": "Enviar a la Papelera…"},
    "common.delete_perm": {"en": "Delete permanently…", "es": "Eliminar definitivamente…"},
    "items.one": {"en": "{n} item", "es": "{n} elemento"},
    "items.other": {"en": "{n} items", "es": "{n} elementos"},

    # --------------------------------------------------------------- arranque
    "main.need_python": {"en": "Super Limpio needs Python 3.10 or newer.",
                         "es": "Super Limpio necesita Python 3.10 o superior."},
    "main.need_tkinter": {
        "en": "tkinter is missing. Run preparar_entorno.bat to install the full portable Python.",
        "es": "Falta tkinter. Ejecuta preparar_entorno.bat para instalar el Python portable completo."},
    "error.unexpected.title": {"en": "Unexpected error", "es": "Error inesperado"},
    "error.unexpected.body": {
        "en": "{detail}\n\nThe application is still running. Details saved to logs\\acciones.log",
        "es": "{detail}\n\nLa aplicación sigue funcionando. Detalle guardado en logs\\acciones.log"},

    # ------------------------------------------------------- marco / barra lateral
    "app.admin_suffix": {"en": "  —  Administrator", "es": "  —  Administrador"},
    "app.brand_sub": {"en": "v{v} · local, no network", "es": "v{v} · local y sin red"},
    "app.role.admin": {"en": "Administrator", "es": "Administrador"},
    "app.role.user": {"en": "Standard user", "es": "Usuario estándar"},
    "app.relaunch_admin_link": {"en": "Restart as administrator…", "es": "Reiniciar como administrador…"},
    "app.status_hint": {
        "en": "Every action asks for confirmation · logged to logs\\acciones.log",
        "es": "Todas las acciones piden confirmación · registro en logs\\acciones.log"},
    "app.language": {"en": "Language", "es": "Idioma"},
    "app.ui_size": {"en": "Size", "es": "Tamaño"},
    "app.ui_size_tip": {"en": "Shrink/enlarge the whole interface",
                        "es": "Reducir/aumentar toda la interfaz"},
    "app.relaunch.title": {"en": "Restart as administrator", "es": "Reiniciar como administrador"},
    "app.relaunch.body": {
        "en": "A new Super Limpio window will open with administrator rights and this one will close. "
              "Windows will show its User Account Control (UAC) prompt.\n\n"
              "Only needed to clean system folders, end other users' processes or run DISM/powercfg.",
        "es": "Se abrirá una nueva ventana de Super Limpio con permisos de administrador y esta se cerrará. "
              "Windows mostrará su aviso de Control de cuentas de usuario (UAC).\n\n"
              "Solo es necesario para limpiar carpetas del sistema, finalizar procesos de otros usuarios "
              "o ejecutar DISM/powercfg."},
    "app.relaunch.ok": {"en": "Restart elevated", "es": "Reiniciar elevado"},
    "app.relaunch.failed": {"en": "Could not elevate", "es": "No se pudo elevar"},

    # ------------------------------------------------------------------ navegación
    "nav.summary": {"en": "Overview", "es": "Resumen"},
    "nav.disk": {"en": "Disk analyzer", "es": "Analizador de disco"},
    "nav.programs": {"en": "Programs", "es": "Programas"},
    "nav.memory": {"en": "Memory & processes", "es": "Memoria y procesos"},
    "nav.optimizer": {"en": "Optimize", "es": "Optimizar"},
    "nav.startup": {"en": "Windows startup", "es": "Inicio de Windows"},
    "nav.cleaner": {"en": "Cleanup", "es": "Limpieza"},
    "nav.devdeps": {"en": "Dev libraries", "es": "Librerías de desarrollo"},
    "nav.tools": {"en": "System tools", "es": "Herramientas del sistema"},
    "nav.log": {"en": "Action log", "es": "Registro de acciones"},

    # ----------------------------------------------------------------- riesgos
    "risk.1": {"en": "Low", "es": "Bajo"},
    "risk.2": {"en": "Medium", "es": "Medio"},
    "risk.3": {"en": "High", "es": "Alto"},
    "risk.4": {"en": "Critical", "es": "Crítico"},
    "risk.badge": {"en": "{label} risk", "es": "Riesgo {label}"},
    "confirm.word": {"en": "CONFIRM", "es": "CONFIRMAR"},

    # ----------------------------------------------------------------- diálogos
    "dialog.risk_level": {"en": "Risk level: {label}", "es": "Nivel de riesgo: {label}"},
    "dialog.exact_target": {"en": "This will run / affect exactly:",
                            "es": "Se va a ejecutar / afectar exactamente a:"},
    "dialog.ack": {"en": "I have reviewed what will happen and want to continue",
                   "es": "He revisado lo que se va a hacer y quiero continuar"},
    "dialog.critical_type": {"en": "Critical action. Type {word} to enable the button:",
                             "es": "Acción crítica. Escribe {word} para habilitar el botón:"},
    "dialog.nothing_without_permission": {"en": "Nothing runs without your permission.",
                                          "es": "Nada se ejecuta sin tu permiso."},
    "dialog.more_items": {"en": "... and {n} more items", "es": "... y {n} elementos más"},

    # ------------------------------------------------------------------ util
    "util.file": {"en": "File", "es": "Archivo"},

    # ----------------------------------------------------------------- Resumen
    "summary.title": {"en": "Overview", "es": "Resumen"},
    "summary.subtitle": {"en": "Your drives, memory and Recycle Bin at a glance.",
                         "es": "Estado de tus unidades, memoria y papelera de un vistazo."},
    "summary.drives": {"en": "Drives", "es": "Unidades"},
    "summary.ram": {"en": "RAM", "es": "Memoria RAM"},
    "summary.ram_used": {"en": "{used} in use of {total}", "es": "{used} en uso de {total}"},
    "summary.top_memory": {"en": "What's using the most memory now",
                           "es": "Lo que más memoria usa ahora"},
    "summary.view_processes": {"en": "View processes", "es": "Ver procesos"},
    "summary.recycle_bin": {"en": "Recycle Bin", "es": "Papelera de reciclaje"},
    "summary.go_cleanup": {"en": "Go to Cleanup", "es": "Ir a Limpieza"},
    "summary.where_to_start": {"en": "Where to start", "es": "Por dónde empezar"},
    "summary.free_of_total": {"en": "{free} free of {total}", "es": "{free} libres de {total}"},
    "summary.status": {"en": "Recycle Bin: {items} items · {drives} drives detected",
                       "es": "Papelera: {items} elementos · {drives} unidades detectadas"},
    "summary.tip.disk.t": {"en": "Disk analyzer", "es": "Analizador de disco"},
    "summary.tip.disk.d": {"en": "Find which folders weigh the most, largest first.",
                           "es": "Descubre qué carpetas pesan más, ordenadas de mayor a menor."},
    "summary.tip.programs.t": {"en": "Programs", "es": "Programas"},
    "summary.tip.programs.d": {"en": "Real on-disk size of each program and official uninstall.",
                               "es": "Tamaño real en disco de cada programa y desinstalación oficial."},
    "summary.tip.optimizer.t": {"en": "Optimize", "es": "Optimizar"},
    "summary.tip.optimizer.d": {"en": "Find what is eating your RAM; Efficient mode for gaming.",
                                "es": "Qué se come tu RAM y Modo eficiente para jugar."},
    "summary.tip.devdeps.t": {"en": "Dev libraries", "es": "Librerías de desarrollo"},
    "summary.tip.devdeps.d": {"en": "node_modules, .venv, target… forgotten in old projects.",
                              "es": "node_modules, .venv, target… olvidados en proyectos viejos."},
    "summary.tip.cleaner.t": {"en": "Cleanup", "es": "Limpieza"},
    "summary.tip.cleaner.d": {"en": "Regenerable temp files and caches, CCleaner style.",
                              "es": "Temporales y cachés regenerables, al estilo CCleaner."},

    # ------------------------------------------------------------- Analizador
    "disk.title": {"en": "Disk analyzer", "es": "Analizador de disco"},
    "disk.subtitle": {"en": "How much each folder really weighs, largest to smallest.",
                      "es": "Cuánto pesa realmente cada carpeta, ordenado de mayor a menor."},
    "disk.location": {"en": "Location", "es": "Ubicación"},
    "disk.browse_title": {"en": "Folder to analyze", "es": "Carpeta a analizar"},
    "disk.prompt": {"en": "Pick a drive or folder and press Analyze.",
                    "es": "Elige una unidad o carpeta y pulsa Analizar."},
    "disk.invalid_path": {"en": "Invalid path", "es": "Ruta no válida"},
    "disk.no_folder": {"en": "This folder does not exist:\n{path}", "es": "No existe la carpeta:\n{path}"},
    "disk.analyzing": {"en": "Analyzing {path} …", "es": "Analizando {path} …"},
    "disk.analyzing_status": {"en": "Analyzing {path}", "es": "Analizando {path}"},
    "disk.stopping": {"en": "Stopping…", "es": "Deteniendo…"},
    "disk.scan_error": {"en": "Analysis error", "es": "Error al analizar"},
    "disk.scan_progress": {"en": "{files} files · {dirs} folders · {bytes} · {secs} s   {current}",
                           "es": "{files} archivos · {dirs} carpetas · {bytes} · {secs} s   {current}"},
    "disk.scan_done_status": {"en": "Analysis finished: {path}", "es": "Análisis completado: {path}"},
    "disk.result_summary": {
        "en": "{size} in {files} files and {dirs} folders · {secs} s",
        "es": "{size} en {files} archivos y {dirs} carpetas · {secs} s"},
    "disk.extra.cancelled": {"en": "analysis stopped: partial results",
                             "es": "análisis detenido: resultados parciales"},
    "disk.extra.errors": {"en": "{n} items without read permission",
                          "es": "{n} elementos sin permiso de lectura"},
    "disk.extra.errors_admin": {"en": " (try as administrator)", "es": " (prueba como administrador)"},
    "disk.extra.cloud": {"en": "{size} cloud-only (uses no disk)",
                         "es": "{size} solo en la nube (no ocupan disco)"},
    "disk.extra.links": {"en": "{n} links/junctions not followed",
                         "es": "{n} enlaces/junctions no seguidos"},
    "disk.tab.folders": {"en": "  Folders  ", "es": "  Carpetas  "},
    "disk.tab.files": {"en": "  Largest files  ", "es": "  Archivos más grandes  "},
    "disk.tab.types": {"en": "  By file type  ", "es": "  Por tipo de archivo  "},
    "disk.col.name": {"en": "Name", "es": "Nombre"},
    "disk.col.size": {"en": "Size", "es": "Tamaño"},
    "disk.col.usage": {"en": "Usage", "es": "Uso"},
    "disk.col.files": {"en": "Files", "es": "Archivos"},
    "disk.col.modified": {"en": "Modified", "es": "Modificado"},
    "disk.col.what": {"en": "What it is", "es": "Qué es"},
    "disk.col.file": {"en": "File", "es": "Archivo"},
    "disk.col.type": {"en": "Type", "es": "Tipo"},
    "disk.col.folder": {"en": "Folder", "es": "Carpeta"},
    "disk.col.desc": {"en": "Description", "es": "Descripción"},
    "disk.col.count": {"en": "Files", "es": "Archivos"},
    "disk.legend.mid": {"en": "≥100 MB", "es": "≥100 MB"},
    "disk.legend.big": {"en": "≥1 GB", "es": "≥1 GB"},
    "disk.legend.huge": {"en": "≥10 GB", "es": "≥10 GB"},
    "disk.show_more": {"en": " Show more ({n} remaining)…", "es": " Mostrar más ({n} restantes)…"},
    "disk.show_more_hint": {"en": "Click to load the next ones", "es": "Pulsa aquí para cargar los siguientes"},
    "disk.small_files": {"en": " ({n} small files)", "es": " ({n} archivos pequeños)"},
    "disk.small_files_hint": {"en": "Grouped to save memory", "es": "Agrupados para ahorrar memoria"},
    "disk.subdirs_unreadable": {"en": "Some subfolders could not be read",
                                "es": "Algunas subcarpetas no se pudieron leer"},
    "disk.cloud_extra": {"en": "+{size} cloud-only", "es": "+{size} solo en la nube"},
    "disk.scan_here": {"en": "Analyze here", "es": "Analizar aquí"},
    "disk.scan_this_folder": {"en": "Analyze this folder", "es": "Analizar esta carpeta"},
    "disk.sel_single": {"en": "{name}  ·  {size}", "es": "{name}  ·  {size}"},
    "disk.sel_multi": {"en": "{n} items  ·  {size}", "es": "{n} elementos  ·  {size}"},
    "disk.path_copied": {"en": "Path copied to clipboard", "es": "Ruta copiada al portapapeles"},
    "disk.blocked_title": {"en": "Protected", "es": "Protegido"},
    "disk.blocked_body": {"en": "Super Limpio will not delete this:\n\n{items}",
                          "es": "Super Limpio no permite borrar esto:\n\n{items}"},
    "disk.recycle.title": {"en": "Send to Recycle Bin", "es": "Enviar a la Papelera"},
    "disk.recycle.body": {
        "en": "{n} items ({size}) will be moved to the Recycle Bin. You can restore them from the "
              "Recycle Bin until you empty it.\nIf the drive has no Recycle Bin (e.g. some external "
              "disks), Windows will warn you first.",
        "es": "Se moverán {n} elementos ({size}) a la Papelera de reciclaje. Podrás restaurarlos desde la "
              "Papelera mientras no la vacíes.\nSi la unidad no tiene Papelera (p. ej. algunos discos "
              "externos), Windows te avisará antes."},
    "disk.delete.title": {"en": "Delete permanently", "es": "Eliminar definitivamente"},
    "disk.delete.body": {
        "en": "{n} items ({size}) will be deleted FOREVER, without going through the Recycle Bin. "
              "They cannot be recovered.",
        "es": "Se borrarán PARA SIEMPRE {n} elementos ({size}), sin pasar por la Papelera. "
              "No se podrán recuperar."},
    "disk.delete.ok": {"en": "Delete forever", "es": "Eliminar para siempre"},
    "disk.delete_status": {"en": "{msg} · {size} freed ({removed}/{total})",
                           "es": "{msg} · {size} liberados ({removed}/{total})"},
    "disk.deleting_progress": {"en": "Deleting {done}/{total}…  {name}",
                               "es": "Eliminando {done}/{total}…  {name}"},

    # --------------------------------------------------------------- Programas
    "programs.title": {"en": "Programs", "es": "Programas"},
    "programs.subtitle": {
        "en": "Installed programs with their real on-disk size. Uninstall uses the official uninstaller.",
        "es": "Programas instalados con su tamaño real en disco. La desinstalación usa el desinstalador "
              "oficial."},
    "programs.measure": {"en": "Measure real size", "es": "Medir tamaño real"},
    "programs.measure_stop": {"en": "Stop measuring", "es": "Detener medición"},
    "programs.uninstall": {"en": "Uninstall…", "es": "Desinstalar…"},
    "programs.store_apps": {"en": "Microsoft Store apps…", "es": "Apps de Microsoft Store…"},
    "programs.col.name": {"en": "Name", "es": "Nombre"},
    "programs.col.real": {"en": "Real size", "es": "Tamaño real"},
    "programs.col.declared": {"en": "Declared", "es": "Declarado"},
    "programs.col.publisher": {"en": "Publisher", "es": "Editor"},
    "programs.col.version": {"en": "Version", "es": "Versión"},
    "programs.col.installed": {"en": "Installed", "es": "Instalado"},
    "programs.col.scope": {"en": "Scope", "es": "Ámbito"},
    "programs.col.location": {"en": "Location", "es": "Ubicación"},
    "programs.scope.machine64": {"en": "Machine (64-bit)", "es": "Equipo (64 bits)"},
    "programs.scope.machine32": {"en": "Machine (32-bit)", "es": "Equipo (32 bits)"},
    "programs.scope.user": {"en": "User", "es": "Usuario"},
    "programs.detail_hint": {"en": "Select a program to see its uninstall command.",
                             "es": "Selecciona un programa para ver su comando de desinstalación."},
    "programs.detail": {"en": "Uninstaller: {cmd}\nRegistry: {key}",
                        "es": "Desinstalador: {cmd}\nRegistro: {key}"},
    "programs.reading": {"en": "Reading installed programs…", "es": "Leyendo programas instalados…"},
    "programs.found": {"en": "{n} programs found", "es": "{n} programas encontrados"},
    "programs.summary": {
        "en": "{n} programs · {total} total · {measured} measured on disk. \"Declared\" is what the "
              "installer reports (often inaccurate); \"Real size\" is measured by walking the program "
              "folder.",
        "es": "{n} programas · {total} en total · {measured} medidos en disco. «Declarado» es lo que dice "
              "el instalador (a menudo inexacto); «Tamaño real» se mide recorriendo la carpeta del "
              "programa."},
    "programs.measuring": {"en": "Measuring {i}/{n}: {name}", "es": "Midiendo {i}/{n}: {name}"},
    "programs.measure_done": {"en": "Measurement finished", "es": "Medición terminada"},
    "programs.no_location": {"en": "This program does not declare its install folder",
                             "es": "Este programa no declara su carpeta de instalación"},
    "programs.select_one": {"en": "Select a program from the list.",
                            "es": "Selecciona un programa de la lista."},
    "programs.one_at_a_time": {
        "en": "Uninstall programs one at a time: each uninstaller has its own wizard.",
        "es": "Desinstala los programas de uno en uno: cada desinstalador tiene su propio asistente."},
    "programs.uninstall_dialog.title": {"en": "Uninstall {name}", "es": "Desinstalar {name}"},
    "programs.uninstall_dialog.body": {
        "en": "The program's official uninstaller will open (the same one Windows Settings uses). "
              "Follow its steps; Super Limpio does not delete files or keys on its own.\n\n"
              "Tip: create a restore point first if it's an important program (System tools).",
        "es": "Se abrirá el desinstalador oficial de este programa (el mismo que usa Configuración de "
              "Windows). Sigue sus pasos; Super Limpio no borra archivos ni claves por su cuenta.\n\n"
              "Consejo: crea un punto de restauración antes si es un programa importante "
              "(Herramientas del sistema)."},
    "programs.uninstall_dialog.ok": {"en": "Open uninstaller", "es": "Abrir desinstalador"},
    "programs.uninstall.detail": {
        "en": "Program:   {name} {version}\nPublisher: {publisher}\nSize:      {size}\nCommand:   {cmd}",
        "es": "Programa:  {name} {version}\nEditor:    {publisher}\nTamaño:    {size}\nComando:   {cmd}"},
    "programs.uninstall.warnings": {"en": "\n\nWarnings:\n{items}", "es": "\n\nAvisos:\n{items}"},
    "programs.uninstall.opened": {"en": "{name} uninstaller opened. Press Refresh when it finishes.",
                                  "es": "Desinstalador de {name} abierto. Pulsa Actualizar cuando termine."},
    "programs.uninstall.failed_title": {"en": "Could not open the uninstaller",
                                        "es": "No se pudo abrir el desinstalador"},
    "programs.uninstall.failed_body": {"en": "{msg}\n\nTry from Settings > Apps.",
                                       "es": "{msg}\n\nPrueba desde Configuración > Aplicaciones."},
    "programs.warn.missing": {
        "en": "The uninstaller is not on disk: the program may already be half-removed. Use "
              "Settings > Apps to clean up the entry.",
        "es": "El desinstalador no existe en disco: el programa puede estar ya borrado a medias. Usa "
              "Configuración > Aplicaciones para limpiar la entrada."},
    "programs.warn.interpreter": {"en": "The uninstaller uses \"{base}\"; review the parameters before "
                                        "continuing.",
                                  "es": "El desinstalador usa «{base}»; revisa los parámetros antes de "
                                        "continuar."},
    "programs.warn.machine": {"en": "Installed for the whole machine: Windows will ask for administrator "
                                    "rights (UAC).",
                              "es": "Instalado para todo el equipo: Windows pedirá permisos de "
                                    "administrador (UAC)."},

    # ------------------------------------------------------------- Memoria
    "memory.title": {"en": "Memory & processes", "es": "Memoria y procesos"},
    "memory.subtitle": {"en": "Running programs ordered by the memory they reserve.",
                        "es": "Programas en ejecución ordenados por la memoria que reservan."},
    "memory.ram": {"en": "RAM", "es": "RAM"},
    "memory.ram_header": {"en": "RAM · {pct}% in use", "es": "Memoria RAM · {pct} % en uso"},
    "memory.ram_detail": {"en": "{used} used of {total} · {avail} available{commit}",
                          "es": "{used} usados de {total} · {avail} disponibles{commit}"},
    "memory.commit": {"en": " · Committed memory (RAM + page file): {used} of {total}",
                      "es": " · Memoria comprometida (RAM + archivo de paginación): {used} de {total}"},
    "memory.auto": {"en": "Refresh every 3 s", "es": "Actualizar cada 3 s"},
    "memory.group": {"en": "Group by program", "es": "Agrupar por programa"},
    "memory.kill": {"en": "End task…", "es": "Finalizar…"},
    "memory.col.program": {"en": "Program", "es": "Programa"},
    "memory.col.processes": {"en": "Processes", "es": "Procesos"},
    "memory.col.private": {"en": "Private memory", "es": "Memoria privada"},
    "memory.col.ws": {"en": "In RAM now", "es": "En RAM ahora"},
    "memory.col.cpu": {"en": "CPU", "es": "CPU"},
    "memory.col.threads": {"en": "Threads", "es": "Hilos"},
    "memory.col.path": {"en": "Path", "es": "Ruta"},
    "memory.no_access": {"en": "no access", "es": "sin acceso"},
    "memory.note": {
        "en": "\"Private memory\" is the memory the program reserved only for itself (the best indicator "
              "of its usage). \"In RAM now\" is the part physically resident right now. System processes "
              "without access require running as administrator.",
        "es": "«Memoria privada» es la memoria que el programa ha reservado solo para él (la cifra que "
              "mejor indica su consumo). «En RAM ahora» es la parte que ocupa físicamente en este "
              "momento. Los procesos del sistema sin acceso necesitan ejecutar como administrador."},
    "memory.processes": {"en": "{n} processes", "es": "{n} procesos"},
    "memory.kill.protected_title": {"en": "Protected", "es": "Protegido"},
    "memory.kill.protected_body": {"en": "Super Limpio does not end essential processes:\n\n{items}",
                                   "es": "Super Limpio no finaliza procesos esenciales:\n\n{items}"},
    "memory.kill.more": {"en": "\n... and {n} more", "es": "\n... y {n} más"},
    "memory.kill.skipped": {"en": "\n\nWill be skipped (protected):\n{items}",
                            "es": "\n\nSe omitirán (protegidos):\n{items}"},
    "memory.kill.body": {"en": "The listed processes will be force-closed (like \"End task\"). {reasons}",
                         "es": "Se forzará el cierre de los procesos indicados (equivale a «Finalizar "
                               "tarea»). {reasons}"},
    "memory.kill.title": {"en": "End processes", "es": "Finalizar procesos"},
    "memory.kill.ok": {"en": "End", "es": "Finalizar"},
    "memory.kill.fail_title": {"en": "Some processes did not close",
                               "es": "Algunos procesos no se cerraron"},
    "memory.kill.done": {"en": "{n} processes ended", "es": "{n} procesos finalizados"},

    # ------------------------------------------------------------- Comprimir
    "zip.button": {"en": "Compress…", "es": "Comprimir…"},
    "zip.title": {"en": "Compress", "es": "Comprimir"},
    "zip.counting": {"en": "{n} items selected · counting…", "es": "{n} elementos seleccionados · contando…"},
    "zip.selection": {"en": "{files} files in {dirs} folders · {size}",
                      "es": "{files} archivos en {dirs} carpetas · {size}"},
    "zip.selection_skipped": {"en": " · {n} will be skipped (links or cloud-only)",
                              "es": " · {n} se omitirán (enlaces o solo en la nube)"},
    "zip.dest": {"en": "Save as", "es": "Guardar como"},
    "zip.format": {"en": "Format", "es": "Formato"},
    "zip.fmt.7z": {"en": "7z — best compression", "es": "7z — máxima compresión"},
    "zip.fmt.zip": {"en": "ZIP — best compatibility", "es": "ZIP — máxima compatibilidad"},
    "zip.fmt.7z.note": {
        "en": "LZMA2 in one solid block: all files are compressed together, which gives the best ratios. "
              "Opens with 7-Zip, WinRAR and recent Windows 11.",
        "es": "LZMA2 en un bloque sólido: todos los archivos se comprimen juntos, que es lo que da los "
              "mejores índices. Se abre con 7-Zip, WinRAR y Windows 11 reciente."},
    "zip.fmt.zip.note": {
        "en": "Deflate, file by file: compresses less, but any system opens it without installing anything "
              "(with a password, 7-Zip, WinRAR or WinZip is needed).",
        "es": "Deflate, archivo a archivo: comprime menos, pero lo abre cualquier sistema sin instalar "
              "nada (con contraseña hace falta 7-Zip, WinRAR o WinZip)."},
    "zip.level": {"en": "Level", "es": "Nivel"},
    "zip.level.ultra": {"en": "Ultra", "es": "Ultra"},
    "zip.level.max": {"en": "Maximum", "es": "Máxima"},
    "zip.level.normal": {"en": "Normal", "es": "Normal"},
    "zip.level.fast": {"en": "Fast", "es": "Rápida"},
    "zip.plan": {"en": "On this PC: {dict} dictionary · threads: {threads} · about {mem} of memory.",
                 "es": "En este equipo: diccionario de {dict} · hilos: {threads} · unos {mem} de memoria."},
    "zip.password": {"en": "Password", "es": "Contraseña"},
    "zip.password_again": {"en": "Repeat", "es": "Repetir"},
    "zip.show": {"en": "Show", "es": "Mostrar"},
    "zip.pw.none": {"en": "Optional. Leave empty for no encryption.",
                    "es": "Opcional. Déjala vacía para no cifrar."},
    "zip.pw.mismatch": {"en": "The two passwords do not match.", "es": "Las dos contraseñas no coinciden."},
    "zip.pw.note.7z": {
        "en": "AES-256. File names are encrypted too. If you forget it, there is no way to recover the "
              "contents.",
        "es": "AES-256. También se cifran los nombres de los archivos. Si la olvidas, no hay forma de "
              "recuperar el contenido."},
    "zip.pw.note.zip": {
        "en": "AES-256. File names stay visible (a limit of the ZIP format). If you forget it, there is no "
              "way to recover the contents.",
        "es": "AES-256. Los nombres de los archivos quedan a la vista (límite del formato ZIP). Si la "
              "olvidas, no hay forma de recuperar el contenido."},
    "zip.opt.verify": {"en": "Test the archive when finished", "es": "Comprobar el archivo al terminar"},
    "zip.opt.recycle": {
        "en": "Then offer to send the originals to the Recycle Bin (only if the test passes)",
        "es": "Después, ofrecer enviar los originales a la Papelera (solo si la comprobación sale bien)"},
    "zip.go": {"en": "Compress", "es": "Comprimir"},
    "zip.close": {"en": "Close", "es": "Cerrar"},
    "zip.read_only": {"en": "The originals are only read.", "es": "Los originales solo se leen."},
    "zip.overwrite": {"en": "This file already exists:\n{path}\n\nReplace it?",
                      "es": "Ya existe este archivo:\n{path}\n\n¿Reemplazarlo?"},
    "zip.phase.start": {"en": "Preparing…", "es": "Preparando…"},
    "zip.phase.start_detail": {"en": "Deriving the encryption key from the password.",
                               "es": "Derivando la clave de cifrado a partir de la contraseña."},
    "zip.phase.compress": {"en": "Compressing · {pct}% · {name}", "es": "Comprimiendo · {pct} % · {name}"},
    "zip.phase.verify": {"en": "Testing the archive · {pct}%", "es": "Comprobando el archivo · {pct} %"},
    "zip.progress.compress": {
        "en": "{done} of {total} · archive so far: {out} ({ratio}%) · {speed}/s · elapsed {elapsed} · "
              "about {eta} left",
        "es": "{done} de {total} · archivo hasta ahora: {out} ({ratio} %) · {speed}/s · transcurrido "
              "{elapsed} · quedan unos {eta}"},
    "zip.progress.verify": {"en": "{done} of {total} read back · elapsed {elapsed}",
                            "es": "{done} de {total} releídos · transcurrido {elapsed}"},
    "zip.stopping": {"en": "Stopping…", "es": "Deteniendo…"},
    "zip.cancelled": {"en": "Stopped. No archive was created.", "es": "Detenido. No se ha creado ningún archivo."},
    "zip.failed": {"en": "Could not create the archive: {why}", "es": "No se pudo crear el archivo: {why}"},
    "zip.done": {"en": "Created {name}", "es": "Creado {name}"},
    "zip.done.sizes": {
        "en": "{files} files · {before} → {after} ({pct}% of the original) · {time}",
        "es": "{files} archivos · {before} → {after} ({pct} % del original) · {time}"},
    "zip.done.saved": {"en": "It takes {size} less than the originals.",
                       "es": "Ocupa {size} menos que los originales."},
    "zip.done.no_gain": {
        "en": "It does not take less: this content was already compressed (video, photos, other archives).",
        "es": "No ocupa menos: este contenido ya estaba comprimido (vídeo, fotos, otros archivos "
              "comprimidos)."},
    "zip.done.verified": {"en": "✔ Tested: the archive was read back and every file matches.",
                          "es": "✔ Comprobado: se ha releído el archivo y todos los ficheros coinciden."},
    "zip.done.encrypted": {"en": "🔒 Encrypted with AES-256. Keep the password safe.",
                           "es": "🔒 Cifrado con AES-256. Guarda bien la contraseña."},
    "zip.done.skipped": {"en": "⚠ {n} items were NOT included:\n{items}",
                         "es": "⚠ {n} elementos NO se han incluido:\n{items}"},
    "zip.done.no_recycle": {
        "en": "The originals stay where they are, because not everything is inside the archive.",
        "es": "Los originales se quedan donde están, porque no todo está dentro del archivo."},
    "zip.status": {"en": "Created {name}: {before} → {after}", "es": "Creado {name}: {before} → {after}"},
    "zip.recycle.title": {"en": "Send the originals to the Recycle Bin",
                          "es": "Enviar los originales a la Papelera"},
    "zip.recycle.body": {
        "en": "{name} was created and tested. The {n} selected items ({size}) will be sent to the Recycle "
              "Bin; you can restore them from there until you empty it.",
        "es": "{name} se ha creado y comprobado. Los {n} elementos seleccionados ({size}) se enviarán a la "
              "Papelera; puedes restaurarlos desde ahí mientras no la vacíes."},
    "zip.skip.link": {"en": "link or junction (not followed)", "es": "enlace o junction (no se siguen)"},
    "zip.skip.cloud": {"en": "cloud-only file (not downloaded)", "es": "archivo solo en la nube (no se descarga)"},
    "zip.skip.partial": {"en": "read error, saved incomplete ({why})",
                         "es": "error de lectura, guardado incompleto ({why})"},
    "zip.err.nothing": {"en": "There is nothing to compress.", "es": "No hay nada que comprimir."},
    "zip.err.no_folder": {"en": "This is not a valid place to save: {path}",
                          "es": "No es un sitio válido para guardar: {path}"},
    "zip.err.dest_is_source": {
        "en": "The archive cannot have the same name as one of the files being compressed.",
        "es": "El archivo no puede llamarse igual que uno de los que se van a comprimir."},
    "zip.err.ascii_password": {
        "en": "In ZIP, use only unaccented letters, digits and symbols: each program reads other characters "
              "differently and the archive might not open. 7z has no such limit.",
        "es": "En ZIP usa solo letras sin tilde, números y símbolos: cada programa interpreta los demás "
              "caracteres a su manera y el archivo podría no abrirse. En 7z no hay este límite."},
    "zip.err.verify_header": {"en": "The test failed: the archive index does not read back correctly.",
                              "es": "La comprobación ha fallado: el índice del archivo no se relee bien."},
    "zip.err.verify_data": {"en": "The test failed at \"{name}\". The disk may be faulty.",
                            "es": "La comprobación ha fallado en «{name}». Puede que el disco tenga errores."},
    "zip.err.grew": {"en": "\"{name}\" grew past 4 GB while it was being read.",
                     "es": "«{name}» ha crecido por encima de 4 GB mientras se leía."},

    # ------------------------------------------------------------ Optimizar
    "opt.title": {"en": "Optimize", "es": "Optimizar"},
    "opt.subtitle": {"en": "Find out what is slowing the PC down and make room for the program or game "
                           "you want to use.",
                     "es": "Averigua qué frena el equipo y deja sitio al programa o juego que quieres usar."},
    "opt.tab.analysis": {"en": "In-depth analysis", "es": "Análisis exhaustivo"},
    "opt.tab.efficient": {"en": "Efficient mode", "es": "Modo eficiente"},

    "opt.an.run": {"en": "Analyze", "es": "Analizar"},
    "opt.an.duration": {"en": "Watch for", "es": "Observar durante"},
    "opt.an.prompt": {"en": "Read-only: nothing is changed.", "es": "Solo lectura: no se cambia nada."},
    "opt.an.running": {"en": "Measuring every process for {s} s… keep using the PC as usual.",
                       "es": "Midiendo todos los procesos durante {s} s… usa el equipo con normalidad."},
    "opt.an.cancelled": {"en": "Analysis stopped.", "es": "Análisis detenido."},
    "opt.an.done": {"en": "Analysis finished ({s} s observed).", "es": "Análisis terminado ({s} s observados)."},
    "opt.an.status": {"en": "{n} findings · {p} programs measured", "es": "{n} hallazgos · {p} programas medidos"},
    "opt.an.explain": {
        "en": "The analysis samples every process once per second to see not only how much memory each "
              "program holds, but which ones keep growing, which use CPU without a window, and how close "
              "the system is to running out of memory.",
        "es": "El análisis mide todos los procesos una vez por segundo para ver no solo cuánta memoria "
              "tiene cada programa, sino cuáles no dejan de crecer, cuáles usan CPU sin tener ventana y "
              "cuánto le falta al sistema para quedarse sin memoria."},
    "opt.an.head.none": {"en": "No analysis yet", "es": "Aún no hay análisis"},
    "opt.an.head.0": {"en": "Everything looks fine", "es": "Todo en orden"},
    "opt.an.head.1": {"en": "Fine, with a few things worth a look", "es": "Bien, con algún detalle que mirar"},
    "opt.an.head.2": {"en": "There is room for improvement", "es": "Hay margen de mejora"},
    "opt.an.head.3": {"en": "The PC is under memory pressure", "es": "El equipo va justo de memoria"},
    "opt.an.level.0": {"en": "Info", "es": "Información"},
    "opt.an.level.1": {"en": "Minor", "es": "Leve"},
    "opt.an.level.2": {"en": "Review", "es": "A revisar"},
    "opt.an.level.3": {"en": "Urgent", "es": "Urgente"},
    "opt.an.col.level": {"en": "Level", "es": "Nivel"},
    "opt.an.col.finding": {"en": "Finding", "es": "Hallazgo"},
    "opt.an.col.detail": {"en": "Detail", "es": "Detalle"},
    "opt.an.col.growth": {"en": "Change", "es": "Variación"},
    "opt.an.col.cpu_avg": {"en": "CPU avg", "es": "CPU media"},
    "opt.an.col.cpu_peak": {"en": "CPU peak", "es": "CPU pico"},
    "opt.an.col.handles": {"en": "Handles", "es": "Identificadores"},
    "opt.an.goto": {"en": "Take me there", "es": "Llévame ahí"},
    "opt.an.close": {"en": "Close selected…", "es": "Cerrar seleccionados…"},
    "opt.an.close_hint": {"en": "Select one or more programs (Ctrl or Shift + click) to close them.",
                          "es": "Selecciona uno o varios programas (Ctrl o Mayús + clic) para cerrarlos."},
    "opt.an.close.title": {"en": "Close programs", "es": "Cerrar programas"},
    "opt.an.close.closing": {"en": "Closing the selected programs…",
                             "es": "Cerrando los programas seleccionados…"},
    "opt.an.close.done": {"en": "{n} programs closed.", "es": "{n} programas cerrados."},
    "opt.an.close.blocked_body": {"en": "Super Limpio does not close these programs:\n\n{items}",
                                  "es": "Super Limpio no cierra estos programas:\n\n{items}"},
    "opt.kept.system": {"en": "part of Windows", "es": "forma parte de Windows"},
    "opt.kept.service": {"en": "it is a Windows service", "es": "es un servicio de Windows"},
    "opt.kept.security": {"en": "security or anti-cheat software",
                          "es": "software de seguridad o anti-trampas"},
    "opt.kept.self": {"en": "it is Super Limpio itself or what launched it",
                      "es": "es el propio Super Limpio o quien lo abrió"},
    "opt.kept.no_access": {"en": "Windows does not allow access to it (try as administrator)",
                           "es": "Windows no permite acceder a él (prueba como administrador)"},
    "opt.an.sum.perf": {
        "en": "Committed {commit} of {limit} · file cache {cache} · kernel {kernel} · {procs} processes, "
              "{threads} threads, {handles} handles",
        "es": "Comprometida {commit} de {limit} · caché de archivos {cache} · núcleo {kernel} · {procs} "
              "procesos, {threads} hilos, {handles} identificadores"},

    "opt.find.ram_crit": {"en": "RAM is almost full ({pct})", "es": "La RAM está casi llena ({pct})"},
    "opt.find.ram_warn": {"en": "RAM usage is high ({pct})", "es": "El uso de RAM es alto ({pct})"},
    "opt.find.ram_ok": {"en": "RAM has headroom ({pct} in use)", "es": "La RAM tiene margen ({pct} en uso)"},
    "opt.find.ram_detail": {"en": "{used} of {total} in use, {avail} available",
                            "es": "{used} de {total} en uso, {avail} disponibles"},
    "opt.find.ram_crit_advice": {
        "en": "Windows is moving memory to the page file on disk, which makes everything slower. Close "
              "what you are not using, or let Efficient mode propose what to stop.",
        "es": "Windows está moviendo memoria al archivo de paginación del disco, y eso lo vuelve todo más "
              "lento. Cierra lo que no uses o deja que el Modo eficiente proponga qué detener."},
    "opt.find.ram_warn_advice": {
        "en": "There is still room, but a heavy program or game may not fit comfortably. Efficient mode "
              "can free memory before you start it.",
        "es": "Aún hay sitio, pero un programa pesado o un juego puede no caber con holgura. El Modo "
              "eficiente puede liberar memoria antes de abrirlo."},
    "opt.find.commit": {"en": "Committed memory at {pct} of the limit",
                        "es": "Memoria comprometida al {pct} del límite"},
    "opt.find.commit_detail": {"en": "{used} of {total} (RAM + page file)",
                               "es": "{used} de {total} (RAM + archivo de paginación)"},
    "opt.find.commit_advice": {
        "en": "This is what programs have reserved, used or not. At 100% programs start failing with "
              "\"out of memory\". Close the ones with the most private memory.",
        "es": "Es lo que los programas han reservado, lo usen o no. Al llegar al 100 % empiezan a fallar "
              "por «memoria insuficiente». Cierra los que más memoria privada tienen."},
    "opt.find.hog": {"en": "{name} holds {size} ({pct} of RAM)", "es": "{name} reserva {size} ({pct} de la RAM)"},
    "opt.find.procs.one": {"en": "{n} process", "es": "{n} proceso"},
    "opt.find.procs.other": {"en": "{n} processes", "es": "{n} procesos"},
    "opt.find.hog_browser_advice": {
        "en": "In a browser, each tab and extension is a process. Close tabs you do not need, review "
              "extensions, or turn on its memory saver / sleeping tabs.",
        "es": "En un navegador cada pestaña y cada extensión es un proceso. Cierra pestañas que no "
              "necesites, revisa las extensiones o activa su ahorro de memoria / pestañas en suspensión."},
    "opt.find.hog_advice": {
        "en": "If you are not using it right now, closing it is the single most effective thing to do. "
              "If you need it, restarting it usually returns memory it accumulated.",
        "es": "Si no lo estás usando ahora, cerrarlo es lo más efectivo que puedes hacer. Si lo necesitas, "
              "reiniciarlo suele devolver la memoria que ha ido acumulando."},
    "opt.find.growth": {"en": "{name} keeps growing: +{size} in {s} s",
                        "es": "{name} no deja de crecer: +{size} en {s} s"},
    "opt.find.growth_detail": {"en": "Now at {size}", "es": "Ahora en {size}"},
    "opt.find.growth_advice": {
        "en": "Normal while it is loading something. If it keeps growing while idle, it may be a memory "
              "leak: restart that program. Run a longer analysis to confirm.",
        "es": "Es normal mientras carga algo. Si sigue creciendo sin que lo uses, puede ser una fuga de "
              "memoria: reinicia ese programa. Repite el análisis con más tiempo para confirmarlo."},
    "opt.find.bg_cpu": {"en": "{name} uses {pct} CPU in the background",
                        "es": "{name} usa un {pct} de CPU en segundo plano"},
    "opt.find.bg_cpu_detail": {"en": "Peak {peak}, no visible window", "es": "Pico del {peak}, sin ventana visible"},
    "opt.find.bg_cpu_advice": {
        "en": "It has no window, yet it is working. If it is an antivirus scan, an update or a sync it "
              "will usually finish by itself; otherwise Efficient mode can slow it down without closing it.",
        "es": "No tiene ventana y aun así está trabajando. Si es un análisis del antivirus, una "
              "actualización o una sincronización suele acabar solo; si no, el Modo eficiente puede "
              "ralentizarlo sin cerrarlo."},
    "opt.find.handles": {"en": "{name} holds {n} handles", "es": "{name} tiene {n} identificadores abiertos"},
    "opt.find.handles_advice": {
        "en": "An unusually high number of open handles often means the program is leaking resources. "
              "Restarting it fixes it.",
        "es": "Un número de identificadores tan alto suele indicar que el programa pierde recursos. "
              "Reiniciarlo lo soluciona."},
    "opt.find.kernel": {"en": "The Windows kernel holds {size} of non-pageable memory",
                        "es": "El núcleo de Windows retiene {size} de memoria no paginable"},
    "opt.find.kernel_advice": {
        "en": "No program can release this memory. It is usually caused by a driver (network, graphics, "
              "antivirus). Updating drivers and restarting the PC is what helps.",
        "es": "Ningún programa puede liberar esta memoria. Suele deberse a un controlador (red, gráficos, "
              "antivirus). Lo que ayuda es actualizar los controladores y reiniciar el equipo."},
    "opt.find.startup": {"en": "{n} programs start with Windows", "es": "{n} programas arrancan con Windows"},
    "opt.find.startup_advice": {
        "en": "Each one uses memory from the moment you sign in. Review them in \"Windows startup\".",
        "es": "Cada uno ocupa memoria desde que inicias sesión. Revísalos en «Inicio de Windows»."},
    "opt.find.blind": {"en": "{n} system processes could not be measured",
                       "es": "{n} procesos del sistema no se pudieron medir"},
    "opt.find.blind_advice": {
        "en": "Windows only lets an administrator read them. For a complete picture, use \"Restart as "
              "administrator\" and analyze again.",
        "es": "Windows solo deja leerlos a un administrador. Para verlo todo, usa «Reiniciar como "
              "administrador» y repite el análisis."},
    "opt.find.reclaim": {"en": "Efficient mode has a proposal for {n} programs ({size} in RAM)",
                         "es": "El Modo eficiente tiene una propuesta para {n} programas ({size} en RAM)"},
    "opt.find.reclaim_advice": {
        "en": "Background programs that can be slowed down or closed while you use something else. You "
              "review the list and decide.",
        "es": "Programas en segundo plano que se pueden ralentizar o cerrar mientras usas otra cosa. Tú "
              "revisas la lista y decides."},
    "opt.find.all_ok": {"en": "No problems detected", "es": "No se han detectado problemas"},
    "opt.find.all_ok_advice": {
        "en": "Memory and CPU look healthy. If the PC still feels slow, check free disk space in "
              "\"Disk analyzer\".",
        "es": "La memoria y la CPU están bien. Si aun así el equipo va lento, mira el espacio libre en "
              "«Analizador de disco»."},

    "opt.eff.target": {"en": "I want to use:", "es": "Quiero usar:"},
    "opt.eff.no_target": {"en": "(nothing in particular: just lighten the PC)",
                          "es": "(nada en concreto: solo aligerar el equipo)"},
    "opt.eff.profile.game": {"en": "It is a game", "es": "Es un juego"},
    "opt.eff.profile.program": {"en": "It is a program", "es": "Es un programa"},
    "opt.eff.col.kind": {"en": "Kind", "es": "Tipo"},
    "opt.eff.col.window": {"en": "On screen", "es": "En pantalla"},
    "opt.eff.col.action": {"en": "Action", "es": "Acción"},
    "opt.eff.col.reason": {"en": "Why", "es": "Por qué"},
    "opt.eff.window.yes": {"en": "Window", "es": "Ventana"},
    "opt.eff.window.no": {"en": "Background", "es": "Segundo plano"},
    "opt.eff.set_action": {"en": "For the selection:", "es": "Para lo seleccionado:"},
    "opt.eff.recommended": {"en": "Back to proposal", "es": "Volver a la propuesta"},
    "opt.eff.apply": {"en": "Apply…", "es": "Aplicar…"},
    "opt.eff.opt.trim": {"en": "Also move out of RAM what gets slowed down",
                         "es": "Sacar además de la RAM lo que se ralentice"},
    "opt.eff.opt.boost": {"en": "Give my program priority", "es": "Dar prioridad a mi programa"},
    "opt.eff.opt.force": {"en": "Force-close what does not close by itself",
                          "es": "Forzar el cierre de lo que no se cierre solo"},
    "opt.eff.note": {
        "en": "Double-click a row to change its action. \"Slow down\" is Windows' own efficiency mode "
              "(low priority + EcoQoS): the program keeps running and you can undo it. \"Close\" asks "
              "programs with a window to close, as if you clicked their X, and ends those without one. "
              "Windows, its services, your antivirus and anti-cheat are never listed.",
        "es": "Doble clic en una fila para cambiar su acción. «Ralentizar» es el modo de eficiencia del "
              "propio Windows (prioridad baja + EcoQoS): el programa sigue funcionando y se puede "
              "deshacer. «Cerrar» pide a los programas con ventana que se cierren, como si pulsaras su X, "
              "y finaliza los que no tienen. Windows, sus servicios, tu antivirus y los anti-trampas no "
              "aparecen nunca en la lista."},
    "opt.eff.summary": {
        "en": "As it stands: close {close} ({ram} in RAM) · slow down {slow}.   Never touched: {kept} "
              "processes ({system} Windows and services, {security} security, {target} of your program, "
              "{other} others).",
        "es": "Tal como está: cerrar {close} ({ram} en RAM) · ralentizar {slow}.   No se tocan: {kept} "
              "procesos ({system} de Windows y servicios, {security} de seguridad, {target} de tu "
              "programa, {other} más)."},
    "opt.eff.status": {"en": "{n} programs · {close} to close · {slow} to slow down",
                       "es": "{n} programas · {close} para cerrar · {slow} para ralentizar"},
    "opt.eff.banner": {
        "en": "Efficient mode active: {slow} processes slowed down · {boost} prioritized · {closed} "
              "programs closed",
        "es": "Modo eficiente activo: {slow} procesos ralentizados · {boost} priorizados · {closed} "
              "programas cerrados"},
    "opt.eff.restore": {"en": "Undo…", "es": "Deshacer…"},
    "opt.eff.reopen": {"en": "Reopen closed…", "es": "Reabrir cerrados…"},
    "opt.eff.nothing": {"en": "Every program is set to \"Keep\": there is nothing to apply.",
                        "es": "Todos los programas están en «Mantener»: no hay nada que aplicar."},
    "opt.eff.applying": {"en": "Applying Efficient mode…", "es": "Aplicando el Modo eficiente…"},
    "opt.eff.confirm.title": {"en": "Efficient mode", "es": "Modo eficiente"},
    "opt.eff.confirm.ok": {"en": "Apply", "es": "Aplicar"},
    "opt.eff.confirm.throttle": {
        "en": "SLOW DOWN: these programs keep running, with low priority and Windows efficiency mode. "
              "Nothing is lost and you can undo it with \"Undo…\".",
        "es": "RALENTIZAR: estos programas siguen funcionando, con prioridad baja y el modo de eficiencia "
              "de Windows. No se pierde nada y se deshace con «Deshacer…»."},
    "opt.eff.confirm.trim": {
        "en": "Their memory will also be moved out of RAM. It comes back by itself when they need it, a "
              "little slower the first time.",
        "es": "Además su memoria saldrá de la RAM. Vuelve sola cuando la necesiten, algo más despacio la "
              "primera vez."},
    "opt.eff.confirm.close": {
        "en": "CLOSE: programs with a window are asked to close and may ask you to save; the ones that "
              "do not close are left open. Background programs without a window are ended directly.",
        "es": "CERRAR: a los programas con ventana se les pide que se cierren y pueden preguntarte si "
              "guardas; los que no se cierren se dejan abiertos. Los de segundo plano sin ventana se "
              "finalizan directamente."},
    "opt.eff.confirm.close_force": {
        "en": "CLOSE (FORCED): programs with a window are asked to close and, if they have not done so "
              "after a few seconds, they are ended. Anything unsaved in them WILL BE LOST.",
        "es": "CERRAR (FORZADO): a los programas con ventana se les pide que se cierren y, si a los pocos "
              "segundos no lo han hecho, se finalizan. Lo que tengan sin guardar SE PERDERÁ."},
    "opt.eff.confirm.boost": {
        "en": "PRIORITIZE: {name} gets \"Above normal\" priority (never \"High\" or \"Realtime\").",
        "es": "PRIORIZAR: {name} pasa a prioridad «Por encima de lo normal» (nunca «Alta» ni «Tiempo "
              "real»)."},
    "opt.eff.result": {"en": "{slow} programs slowed down · {closed} closed.",
                       "es": "{slow} programas ralentizados · {closed} cerrados."},
    "opt.eff.result.freed": {"en": "Available RAM went up by {size}.",
                             "es": "La RAM disponible ha subido {size}."},
    "opt.eff.result.boosted": {"en": "{n} processes of your program prioritized.",
                               "es": "{n} procesos de tu programa priorizados."},
    "opt.eff.result.pending": {
        "en": "Still open (they may be asking whether to save, or have gone to the tray): {items}",
        "es": "Siguen abiertos (puede que pregunten si guardar o que se hayan ido a la bandeja): {items}"},
    "opt.eff.result.failures": {"en": "Could not be changed:\n{items}", "es": "No se pudieron cambiar:\n{items}"},
    "opt.eff.result.undo": {
        "en": "When you finish, come back here and press \"Undo…\". If you close Super Limpio it will "
              "ask first.",
        "es": "Cuando termines, vuelve aquí y pulsa «Deshacer…». Si cierras Super Limpio, te lo "
              "preguntará antes."},
    "opt.eff.restore.title": {"en": "Undo Efficient mode", "es": "Deshacer el Modo eficiente"},
    "opt.eff.restore.body": {
        "en": "These processes get back the priority they had and leave efficiency mode. Programs that "
              "were closed are not reopened here (use \"Reopen closed…\").",
        "es": "Estos procesos recuperan la prioridad que tenían y salen del modo de eficiencia. Los "
              "programas que se cerraron no se reabren aquí (usa «Reabrir cerrados…»)."},
    "opt.eff.restore.ok": {"en": "Undo", "es": "Deshacer"},
    "opt.eff.restore.done": {"en": "{n} processes restored", "es": "{n} procesos restaurados"},
    "opt.eff.reopen.title": {"en": "Reopen closed programs", "es": "Reabrir programas cerrados"},
    "opt.eff.reopen.body": {
        "en": "These programs will be started again. They open as if from the Start menu: they will not "
              "restore what you had open in them.",
        "es": "Se volverán a abrir estos programas. Arrancan como desde el menú Inicio: no recuperan lo "
              "que tenías abierto en ellos."},
    "opt.eff.reopen.ok": {"en": "Reopen", "es": "Reabrir"},
    "opt.eff.reopen.failed": {
        "en": "These could not be started (Microsoft Store apps must be opened from the Start menu):\n{items}",
        "es": "Estos no se pudieron abrir (las apps de Microsoft Store hay que abrirlas desde el menú "
              "Inicio):\n{items}"},
    "opt.exit.title": {"en": "Efficient mode is still active", "es": "El Modo eficiente sigue activo"},
    "opt.exit.body": {
        "en": "{n} processes are still slowed down or prioritized.\n\nYes: undo it and exit.\nNo: exit and "
              "leave them as they are (they return to normal when those programs restart).\nCancel: do "
              "not exit.",
        "es": "{n} procesos siguen ralentizados o priorizados.\n\nSí: deshacerlo y salir.\nNo: salir y "
              "dejarlos como están (vuelven a la normalidad cuando esos programas se reinicien).\n"
              "Cancelar: no salir."},

    "opt.action.keep": {"en": "Keep", "es": "Mantener"},
    "opt.action.throttle": {"en": "Slow down", "es": "Ralentizar"},
    "opt.action.close": {"en": "Close", "es": "Cerrar"},
    "opt.do.ask_close": {"en": "ASK TO CLOSE", "es": "PEDIR CIERRE"},
    "opt.do.end": {"en": "END", "es": "FINALIZAR"},
    "opt.do.throttle": {"en": "SLOW DOWN", "es": "RALENTIZAR"},
    "opt.do.boost": {"en": "PRIORITIZE", "es": "PRIORIZAR"},
    "opt.log.ended": {"en": "ended (no window)", "es": "finalizado (sin ventana)"},
    "opt.log.closed": {"en": "closed by itself", "es": "se cerró solo"},
    "opt.log.forced": {"en": "force-closed", "es": "cierre forzado"},
    "opt.log.still_open": {"en": "still open", "es": "sigue abierto"},

    "opt.cat.updater": {"en": "Updater", "es": "Actualizador"},
    "opt.cat.widget": {"en": "Windows extra", "es": "Extra de Windows"},
    "opt.cat.cloud": {"en": "Cloud sync", "es": "Sincronización en la nube"},
    "opt.cat.browser": {"en": "Browser", "es": "Navegador"},
    "opt.cat.comms": {"en": "Chat and calls", "es": "Chat y llamadas"},
    "opt.cat.media": {"en": "Audio and video", "es": "Audio y vídeo"},
    "opt.cat.launcher": {"en": "Game platform", "es": "Plataforma de juegos"},
    "opt.cat.gpu": {"en": "Graphics card", "es": "Tarjeta gráfica"},
    "opt.cat.peripheral": {"en": "Devices", "es": "Dispositivos"},
    "opt.cat.network": {"en": "VPN", "es": "VPN"},
    "opt.cat.other": {"en": "Program", "es": "Programa"},

    "opt.reason.updater": {"en": "Only checks for updates; it will run again on its own later.",
                           "es": "Solo busca actualizaciones; volverá a ejecutarse solo más adelante."},
    "opt.reason.widget": {"en": "Widgets, Phone Link, assistants: Windows restarts them when needed.",
                          "es": "Widgets, Enlace Móvil, asistentes: Windows los reabre cuando hacen falta."},
    "opt.reason.cloud": {"en": "Sync will be slower meanwhile; nothing is lost.",
                         "es": "La sincronización irá más lenta mientras tanto; no se pierde nada."},
    "opt.reason.browser": {"en": "Usually the biggest memory user. Choose Close if you do not need it now.",
                           "es": "Suele ser lo que más memoria usa. Elige Cerrar si ahora no lo necesitas."},
    "opt.reason.comms": {"en": "Calls and voice chat would stutter if slowed down.",
                         "es": "Las llamadas y el chat de voz se entrecortarían al ralentizarlo."},
    "opt.reason.media": {"en": "Music, video or recording would stutter if slowed down.",
                         "es": "La música, el vídeo o la grabación se entrecortarían al ralentizarlo."},
    "opt.reason.peripheral": {"en": "Mouse, keyboard, tablet or audio settings depend on it.",
                              "es": "De él dependen ajustes de ratón, teclado, tableta o audio."},
    "opt.reason.gpu": {"en": "Graphics driver software and overlay.",
                       "es": "Software del controlador gráfico y su superposición."},
    "opt.reason.network": {"en": "Closing a VPN would expose or cut your connection.",
                           "es": "Cerrar una VPN dejaría tu conexión expuesta o cortada."},
    "opt.reason.launcher_game": {"en": "Your game may need it to start, save or play online.",
                                 "es": "Tu juego puede necesitarla para arrancar, guardar o jugar en línea."},
    "opt.reason.launcher": {"en": "You are not going to play: it can wait in the background.",
                            "es": "No vas a jugar: puede esperar en segundo plano."},
    "opt.reason.open_app": {"en": "You have it open. Decide yourself; it may hold unsaved work.",
                            "es": "Lo tienes abierto. Decide tú; puede tener trabajo sin guardar."},
    "opt.reason.small": {"en": "Uses so little that touching it is not worth it.",
                         "es": "Consume tan poco que no merece la pena tocarlo."},
    "opt.reason.background": {"en": "Runs without a window; slowing it down gives room to your program.",
                              "es": "Trabaja sin ventana; ralentizarlo deja sitio a tu programa."},
    "opt.reason.throttled": {"en": "Already slowed down in this session.",
                             "es": "Ya está ralentizado en esta sesión."},

    # -------------------------------------------------------------- Inicio
    "startup.title": {"en": "Windows startup", "es": "Inicio de Windows"},
    "startup.subtitle": {"en": "Programs that start on their own and use memory from the moment you turn "
                               "the PC on.",
                         "es": "Programas que arrancan solos y ocupan memoria desde que enciendes el "
                               "equipo."},
    "startup.manage": {"en": "Manage in Task Manager", "es": "Administrar en el Administrador de tareas"},
    "startup.col.name": {"en": "Name", "es": "Nombre"},
    "startup.col.state": {"en": "State", "es": "Estado"},
    "startup.col.source": {"en": "Source", "es": "Origen"},
    "startup.col.command": {"en": "Command", "es": "Comando"},
    "startup.state.once": {"en": "Once", "es": "Una vez"},
    "startup.state.on": {"en": "Enabled", "es": "Activado"},
    "startup.state.off": {"en": "Disabled", "es": "Desactivado"},
    "startup.missing_file": {"en": "   ⚠ the file does not exist", "es": "   ⚠ el archivo no existe"},
    "startup.note": {
        "en": "For safety, Super Limpio only shows this list. To disable a program use Task Manager "
              "(Startup tab): it is the official Windows way and can be reverted at any time. Entries "
              "marked ⚠ point to programs that were already deleted.",
        "es": "Por seguridad, Super Limpio solo muestra esta lista. Para desactivar un programa usa el "
              "Administrador de tareas (pestaña Inicio): es la vía oficial de Windows y se puede "
              "revertir en cualquier momento. Las entradas marcadas con ⚠ apuntan a programas ya "
              "borrados."},
    "startup.status": {"en": "{n} startup entries · {on} enabled", "es": "{n} entradas de inicio · {on} activadas"},
    "startup.src.hkcu_run": {"en": "HKCU Run", "es": "HKCU Run"},
    "startup.src.hkcu_runonce": {"en": "HKCU RunOnce", "es": "HKCU RunOnce"},
    "startup.src.hklm_run": {"en": "HKLM Run", "es": "HKLM Run"},
    "startup.src.hklm_run32": {"en": "HKLM Run (32-bit)", "es": "HKLM Run (32 bits)"},
    "startup.src.hklm_runonce": {"en": "HKLM RunOnce", "es": "HKLM RunOnce"},
    "startup.src.folder_user": {"en": "Startup folder (user)", "es": "Carpeta Inicio (usuario)"},
    "startup.src.folder_all": {"en": "Startup folder (all users)", "es": "Carpeta Inicio (todos)"},
    "startup.default_name": {"en": "(default)", "es": "(predeterminado)"},

    # -------------------------------------------------------------- Limpieza
    "cleaner.title": {"en": "Cleanup", "es": "Limpieza"},
    "cleaner.subtitle": {
        "en": "Regenerable temp files and caches. First it analyzes without touching anything; then you "
              "decide.",
        "es": "Temporales y cachés regenerables. Primero se analiza sin tocar nada; luego tú decides."},
    "cleaner.admin_tag": {"en": "admin", "es": "admin"},
    "cleaner.irreversible_tag": {"en": "irreversible", "es": "irreversible"},
    "cleaner.col.category": {"en": "Category", "es": "Categoría"},
    "cleaner.col.size": {"en": "Size", "es": "Tamaño"},
    "cleaner.col.files": {"en": "Files", "es": "Archivos"},
    "cleaner.col.notes": {"en": "Notes", "es": "Notas"},
    "cleaner.hero_prompt": {"en": "Press \"Analyze\" to compute how much space can be freed.",
                            "es": "Pulsa «Analizar» para calcular cuánto espacio se puede liberar."},
    "cleaner.run": {"en": "Run cleanup…", "es": "Ejecutar limpieza…"},
    "cleaner.mark_recommended": {"en": "Select recommended", "es": "Marcar recomendadas"},
    "cleaner.analyzing": {"en": "Analyzing…", "es": "Analizando…"},
    "cleaner.recent_kept": {"en": "{n} recent files kept.", "es": "{n} recientes se conservan."},
    "cleaner.not_found": {"en": "Not found on this PC.", "es": "No encontrado en este equipo."},
    "cleaner.analysis_done": {
        "en": "can be freed across {files} files.\nReview the list and press \"Run cleanup\".",
        "es": "se pueden liberar en {files} archivos.\nRevisa la lista y pulsa «Ejecutar limpieza»."},
    "cleaner.analysis_status": {"en": "Cleanup analysis: {size} recoverable",
                                "es": "Análisis de limpieza: {size} recuperables"},
    "cleaner.more_locations": {"en": "… and {n} more locations", "es": "… y {n} ubicaciones más"},
    "cleaner.run.body": {
        "en": "About {size} of temp files and caches will be deleted. Only the CONTENTS of the listed "
              "locations are touched; files in use are skipped automatically.",
        "es": "Se borrarán unos {size} de archivos temporales y cachés. Solo se toca el CONTENIDO de las "
              "ubicaciones listadas; los archivos en uso se omiten automáticamente."},
    "cleaner.run.close_apps": {
        "en": "\n\nYou should close first: {apps} (their in-use caches can't be deleted).",
        "es": "\n\nConviene cerrar antes: {apps} (sus cachés en uso no se pueden borrar)."},
    "cleaner.run.recycle_warn": {
        "en": "\n\nIncludes emptying the Recycle Bin: those files CANNOT be recovered.",
        "es": "\n\nIncluye vaciar la Papelera: esos archivos NO se podrán recuperar."},
    "cleaner.run.title": {"en": "Run cleanup", "es": "Ejecutar limpieza"},
    "cleaner.run.ok": {"en": "Clean now", "es": "Limpiar ahora"},
    "cleaner.cleaned": {"en": "✔ Clean. {note}", "es": "✔ Limpio. {note}"},
    "cleaner.done": {"en": "freed. Files in use were kept.\nYou can analyze again to check.",
                     "es": "liberados. Los archivos en uso se han conservado.\nPuedes volver a analizar "
                           "para comprobarlo."},
    "cleaner.done_status": {"en": "Cleanup finished: {freed} freed · Recycle Bin: {bin}",
                            "es": "Limpieza completada: {freed} liberados · papelera: {bin}"},

    # Grupos de categorías de limpieza
    "cleaner.group.Windows": {"en": "Windows", "es": "Windows"},
    "cleaner.group.Navegadores": {"en": "Browsers", "es": "Navegadores"},
    "cleaner.group.Desarrollo": {"en": "Development", "es": "Desarrollo"},
    "cleaner.group.Aplicaciones": {"en": "Applications", "es": "Aplicaciones"},

    # ------------------------------------------------------- Librerías dev
    "devdeps.title": {"en": "Dev libraries", "es": "Librerías de desarrollo"},
    "devdeps.subtitle": {
        "en": "Dependencies and build outputs that can be regenerated: node_modules, virtualenvs, "
              "target…",
        "es": "Dependencias y compilaciones que se pueden regenerar: node_modules, entornos virtuales, "
              "target…"},
    "devdeps.search_in": {"en": "Search in", "es": "Buscar en"},
    "devdeps.browse_title": {"en": "Projects folder", "es": "Carpeta de proyectos"},
    "devdeps.intro": {"en": "Search for dependency folders in your projects. Check the ones from projects "
                            "you no longer use.",
                      "es": "Busca carpetas de dependencias en tus proyectos. Marca las de proyectos que "
                            "ya no uses."},
    "devdeps.col.size": {"en": "Size", "es": "Tamaño"},
    "devdeps.col.kind": {"en": "Type", "es": "Tipo"},
    "devdeps.col.modified": {"en": "Modified", "es": "Modificado"},
    "devdeps.col.files": {"en": "Files", "es": "Archivos"},
    "devdeps.col.path": {"en": "Path", "es": "Ruta"},
    "devdeps.mark_all": {"en": "Select all", "es": "Marcar todo"},
    "devdeps.unmark": {"en": "Clear", "es": "Desmarcar"},
    "devdeps.mark_old": {"en": "Select untouched > 6 months", "es": "Marcar > 6 meses sin tocar"},
    "devdeps.recycle_marked": {"en": "Send selected to Recycle Bin…", "es": "Enviar marcadas a la Papelera…"},
    "devdeps.searching": {"en": "Searching… {n} found · {cur}", "es": "Buscando… {n} encontradas · {cur}"},
    "devdeps.done": {"en": "{n} regenerable folders · {total} total",
                     "es": "{n} carpetas regenerables · {total} en total"},
    "devdeps.status": {"en": "Dev libraries: {total}", "es": "Librerías de desarrollo: {total}"},
    "devdeps.marked": {"en": "{n} selected · {size} to free", "es": "{n} marcadas · {size} a liberar"},
    "devdeps.nothing_title": {"en": "Nothing selected", "es": "Nada marcado"},
    "devdeps.nothing_body": {"en": "Check folders by clicking the ☐ box on each row.",
                             "es": "Marca las carpetas pulsando en la casilla ☐ de cada fila."},
    "devdeps.delete.body": {
        "en": "{n} folders ({size}) will be deleted forever. They are regenerable, but cannot be "
              "recovered from the Recycle Bin.",
        "es": "Se borrarán para siempre {n} carpetas ({size}). Son regenerables, pero no se podrán "
              "recuperar de la Papelera."},
    "devdeps.delete.ok": {"en": "Delete forever", "es": "Eliminar para siempre"},
    "devdeps.recycle.body": {"en": "{n} folders ({size}) will be moved to the Recycle Bin.",
                             "es": "Se moverán {n} carpetas ({size}) a la Papelera."},
    "devdeps.deleted_status": {"en": "{msg} · {size} freed", "es": "{msg} · {size} liberados"},
    "devdeps.note": {
        "en": "Tip: node_modules usually has tens of thousands of tiny files; deleting it permanently is "
              "much faster than sending it to the Recycle Bin. It regenerates with \"npm install\" / "
              "\"pip install -r requirements.txt\" / \"cargo build\".",
        "es": "Consejo: node_modules suele tener decenas de miles de archivos pequeños; borrarlo "
              "definitivamente es mucho más rápido que enviarlo a la Papelera. Se regenera con "
              "«npm install» / «pip install -r requirements.txt» / «cargo build»."},

    # ------------------------------------------------------- Herramientas
    "tools.title": {"en": "System tools", "es": "Herramientas del sistema"},
    "tools.subtitle": {"en": "Shortcuts to official Windows tools. You see the exact command before "
                             "running it.",
                       "es": "Accesos a herramientas oficiales de Windows. Ves el comando exacto antes de "
                             "ejecutarlo."},
    "tools.run": {"en": "Run…", "es": "Ejecutar…"},
    "tools.open": {"en": "Open", "es": "Abrir"},
    "tools.run_btn": {"en": "Run", "es": "Ejecutar"},
    "tools.requires_admin": {"en": "Requires administrator", "es": "Requiere administrador"},
    "tools.admin_note": {
        "en": "\n\nWindows will also show the User Account Control (UAC) prompt. The console will stay "
              "open so you can see the result.",
        "es": "\n\nWindows mostrará además el aviso de Control de cuentas de usuario (UAC). La consola "
              "quedará abierta para que veas el resultado."},
    "tools.status": {"en": "{title}: {msg}", "es": "{title}: {msg}"},

    # ----------------------------------------------------------------- Registro
    "log.title": {"en": "Action log", "es": "Registro de acciones"},
    "log.subtitle": {"en": "Everything Super Limpio has done on this PC (saved to the logs folder, next "
                           "to the app).",
                     "es": "Todo lo que Super Limpio ha hecho en este equipo (se guarda en la carpeta "
                           "logs, junto a la app)."},
    "log.open_folder": {"en": "Open logs folder", "es": "Abrir carpeta de registros"},
    "log.col.date": {"en": "Date", "es": "Fecha"},
    "log.col.action": {"en": "Action", "es": "Acción"},
    "log.col.ok": {"en": "OK", "es": "OK"},
    "log.col.target": {"en": "Target", "es": "Objetivo"},
    "log.col.result": {"en": "Result", "es": "Resultado"},

    # ------------------------------------------------------- safety / fileops
    "safety.empty_path": {"en": "Empty path", "es": "Ruta vacía"},
    "safety.drive_root": {"en": "A drive root cannot be deleted.",
                          "es": "No se puede borrar la raíz de una unidad."},
    "safety.per_drive_system": {
        "en": "Drive system folder (Recycle Bin or restore points). Empty the Recycle Bin from "
              "\"Cleanup\".",
        "es": "Carpeta del sistema de la unidad (papelera o puntos de restauración). Vacía la papelera "
              "desde «Limpieza»."},
    "safety.essential": {"en": "It is an essential system or user-profile folder.",
                         "es": "Es una carpeta esencial del sistema o de tu perfil de usuario."},
    "safety.program_files": {
        "en": "It is inside Program Files. Use \"Programs > Uninstall\" to remove software without "
              "breaking Windows.",
        "es": "Está dentro de Archivos de programa. Usa «Programas > Desinstalar» para quitar software "
              "sin romper Windows."},
    "safety.own_app": {"en": "It is part of the Super Limpio application itself.",
                       "es": "Forma parte de la propia aplicación Super Limpio."},
    "safety.protected_zone": {"en": "It is in a protected area of the operating system.",
                              "es": "Está en una zona protegida del sistema operativo."},
    "safety.contains_protected": {"en": "It contains protected system folders.",
                                  "es": "Contiene carpetas protegidas del sistema."},
    "safety.file.pagefile": {
        "en": "Paging file (virtual memory). Adjust it in System > Advanced > Performance.",
        "es": "Archivo de paginación (memoria virtual). Ajústalo en Sistema > Configuración avanzada > "
              "Rendimiento."},
    "safety.file.hiberfil": {
        "en": "Hibernation file. Remove it by turning off hibernation in \"System tools\".",
        "es": "Archivo de hibernación. Se elimina desactivando la hibernación en «Herramientas del "
              "sistema»."},
    "safety.file.swapfile": {"en": "Virtual memory for modern apps. Managed by Windows.",
                             "es": "Memoria virtual de apps modernas. Lo gestiona Windows."},
    "safety.proc.essential": {
        "en": "Essential Windows process: ending it can hang or restart the PC.",
        "es": "Proceso esencial de Windows: finalizarlo puede colgar o reiniciar el equipo."},
    "safety.proc.self": {"en": "It is the application itself.", "es": "Es la propia aplicación."},
    "safety.proc.sensitive": {
        "en": "Windows interface component: the desktop may disappear for a few seconds.",
        "es": "Componente de la interfaz de Windows: el escritorio puede desaparecer unos segundos."},
    "safety.proc.normal": {"en": "Unsaved data in that program will be lost.",
                           "es": "Se perderán los datos no guardados de ese programa."},
    "fileops.blocked": {"en": "Operation blocked for safety:\n{msg}",
                        "es": "Operación bloqueada por seguridad:\n{msg}"},
    "fileops.deleted_perm": {"en": "Permanently deleted", "es": "Eliminado definitivamente"},
    "fileops.some_failed": {"en": "Some items could not be deleted:\n{items}",
                            "es": "Algunos elementos no se pudieron borrar:\n{items}"},
    "fileops.in_use": {"en": "{path}: items left in use or without permission",
                       "es": "{path}: quedaron elementos en uso o sin permisos"},

    # ------------------------------------------------------- winapi mensajes
    "winapi.launched": {"en": "Launched", "es": "Lanzado"},
    "winapi.access_denied": {"en": "Access denied or elevation cancelled by the user",
                             "es": "Acceso denegado o elevación cancelada por el usuario"},
    "winapi.not_found": {"en": "File or path not found", "es": "No se encontró el archivo o la ruta"},
    "winapi.shellexec_code": {"en": "ShellExecute returned code {rc}",
                              "es": "ShellExecute devolvió el código {rc}"},
    "winapi.proc_ended": {"en": "Process ended", "es": "Proceso finalizado"},
    "winapi.proc_access_denied": {"en": "Access denied (error {err}). Try as administrator.",
                                  "es": "Acceso denegado (error {err}). Prueba como administrador."},
    "winapi.proc_fail": {"en": "Could not end (error {err})", "es": "No se pudo finalizar (error {err})"},
    "winapi.proc_op_fail": {"en": "Windows refused the change (error {err})",
                            "es": "Windows rechazó el cambio (error {err})"},
    "winapi.proc_changed": {"en": "The process is no longer the one that was analyzed; skipped.",
                            "es": "El proceso ya no es el que se analizó; se ha omitido."},
    "winapi.proc_throttled": {"en": "Efficiency mode on", "es": "Modo de eficiencia activado"},
    "winapi.proc_restored": {"en": "Priority restored", "es": "Prioridad restaurada"},
    "winapi.proc_priority": {"en": "Priority changed", "es": "Prioridad cambiada"},
    "winapi.proc_trimmed": {"en": "Working set trimmed", "es": "Memoria en RAM recortada"},
    "winapi.bin_emptied": {"en": "Recycle Bin emptied", "es": "Papelera vaciada"},
    "winapi.bin_fail": {"en": "Could not empty the Recycle Bin (HRESULT {hr})",
                        "es": "No se pudo vaciar la papelera (HRESULT {hr})"},
    "winapi.recycle_nothing": {"en": "Nothing to move", "es": "Nada que mover"},
    "winapi.recycle_done": {"en": "Sent to Recycle Bin", "es": "Enviado a la Papelera"},
    "winapi.recycle_cancelled": {"en": "Operation cancelled", "es": "Operación cancelada"},
    "winapi.recycle_fail": {"en": "Could not send to the Recycle Bin (code {rc}). File in use or without "
                                  "permissions?",
                            "es": "No se pudo enviar a la Papelera (código {rc}). ¿Archivo en uso o sin "
                                  "permisos?"},

    # ------------------------------------------------------- integridad
    "integrity.tampered_title": {"en": "Distribution modified", "es": "Distribución modificada"},
    "integrity.tampered_body": {
        "en": "Super Limpio detected that its files were changed after they were signed:\n\n{detail}\n\n"
              "For your safety the app will not continue. Download a fresh copy from the official source.",
        "es": "Super Limpio ha detectado que sus archivos se modificaron después de firmarse:\n\n{detail}"
              "\n\nPor tu seguridad la aplicación no continuará. Descarga una copia nueva desde el origen "
              "oficial."},
    "integrity.bad_signature": {"en": "the integrity signature is not valid",
                                "es": "la firma de integridad no es válida"},
    "integrity.changed_files": {"en": "{n} modified or missing files", "es": "{n} archivos modificados o que faltan"},

    # ------------------------------------------------- pistas del escáner
    "scanner.no_ext": {"en": "(no extension)", "es": "(sin extensión)"},
    "hint.folder.node_modules": {"en": "npm/Node dependencies. Regenerate with \"npm install\".",
                                 "es": "Dependencias npm/Node. Se regeneran con «npm install»."},
    "hint.folder.venv_dot": {"en": "Python virtual environment. Regenerate with pip.",
                             "es": "Entorno virtual de Python. Se regenera con pip."},
    "hint.folder.venv": {"en": "Python virtual environment (if it contains pyvenv.cfg).",
                         "es": "Entorno virtual de Python (si contiene pyvenv.cfg)."},
    "hint.folder.pycache": {"en": "Python bytecode. Regenerates itself.",
                            "es": "Bytecode de Python. Se regenera solo."},
    "hint.folder.gradle": {"en": "Gradle cache. Regenerable.", "es": "Caché de Gradle. Regenerable."},
    "hint.folder.m2": {"en": "Local Maven repository. Regenerable (re-downloaded).",
                       "es": "Repositorio local de Maven. Regenerable (se descarga de nuevo)."},
    "hint.folder.nuget": {"en": "NuGet packages. Regenerable.", "es": "Paquetes NuGet. Regenerables."},
    "hint.folder.cargo": {"en": "Rust toolchain/cache.", "es": "Toolchain/caché de Rust."},
    "hint.folder.target": {"en": "Build output (Rust/Maven). Regenerable if it's a project.",
                           "es": "Salida de compilación (Rust/Maven). Regenerable si es un proyecto."},
    "hint.folder.winsxs": {"en": "Windows component store. Do NOT delete; use \"Component cleanup\".",
                           "es": "Almacén de componentes de Windows. NO borrar; usa «Limpieza de componentes»."},
    "hint.folder.installer": {"en": "Windows Installer packages. Do NOT delete manually.",
                              "es": "Instaladores de Windows Installer. NO borrar a mano."},
    "hint.folder.softwaredistribution": {"en": "Windows Update downloads. Cleanable from \"Cleanup\".",
                                         "es": "Descargas de Windows Update. Limpiable desde «Limpieza»."},
    "hint.folder.temp": {"en": "Temporary files. Usually cleanable.",
                         "es": "Archivos temporales. Normalmente limpiable."},
    "hint.folder.cache": {"en": "Cache. Usually regenerable.", "es": "Caché. Normalmente regenerable."},
    "hint.folder.crashdumps": {"en": "Program crash dumps. Cleanable.",
                               "es": "Volcados de errores de programas. Limpiable."},
    "hint.folder.steamapps": {"en": "Steam games. Uninstall them from Steam.",
                              "es": "Juegos de Steam. Desinstálalos desde Steam."},
    "hint.folder.docker": {"en": "Docker data. Use \"docker system prune\".",
                           "es": "Datos de Docker. Usa «docker system prune»."},
    "hint.folder.wsl": {"en": "WSL disks. Use \"wsl --unregister\" carefully.",
                        "es": "Discos de WSL. Usa «wsl --unregister» con cuidado."},
    "hint.folder.onedrive": {"en": "Folder synced with OneDrive.", "es": "Carpeta sincronizada con OneDrive."},
    "hint.folder.downloads": {"en": "Downloads: tends to pile up forgotten installers.",
                              "es": "Descargas: suele acumular instaladores olvidados."},
    "hint.folder.recyclebin": {"en": "Recycle Bin. Empty it from \"Cleanup\".",
                               "es": "Papelera de reciclaje. Vacíala desde «Limpieza»."},
    "hint.folder.svi": {"en": "Restore points. Manage them from System Protection.",
                        "es": "Puntos de restauración. Gestiónalos desde Protección del sistema."},
    "hint.folder.packages": {"en": "Microsoft Store app data. Manage from Settings > Apps.",
                             "es": "Datos de apps de Microsoft Store. Gestiona desde Configuración > Aplicaciones."},
    "hint.folder.windowsapps": {"en": "Microsoft Store apps. Uninstall from Settings.",
                                "es": "Apps de Microsoft Store. Desinstala desde Configuración."},
    "hint.folder.programfiles": {"en": "Installed programs. Use \"Programs > Uninstall\".",
                                 "es": "Programas instalados. Usa «Programas > Desinstalar»."},
    "hint.folder.programfiles86": {"en": "32-bit programs. Use \"Programs > Uninstall\".",
                                   "es": "Programas de 32 bits. Usa «Programas > Desinstalar»."},
    "hint.file.pagefile": {"en": "Windows virtual memory.", "es": "Memoria virtual de Windows."},
    "hint.file.hiberfil": {"en": "Hibernation/fast startup. See \"System tools\".",
                           "es": "Hibernación/inicio rápido. Ver «Herramientas del sistema»."},
    "hint.file.swapfile": {"en": "Virtual memory for Store apps.", "es": "Memoria virtual de apps Store."},
    "hint.file.memorydmp": {"en": "Blue-screen crash dump. Safe to delete.",
                            "es": "Volcado de pantallazo azul. Se puede borrar."},
    "hint.file.ext4vhdx": {"en": "A WSL distro disk.", "es": "Disco de una distro WSL."},
    "hint.ext.iso": {"en": "Disk image", "es": "Imagen de disco"},
    "hint.ext.vhdx": {"en": "Virtual disk", "es": "Disco virtual"},
    "hint.ext.vmdk": {"en": "VMware disk", "es": "Disco de VMware"},
    "hint.ext.dmp": {"en": "Memory dump", "es": "Volcado de memoria"},
    "hint.ext.msi": {"en": "Installer", "es": "Instalador"},
    "hint.ext.exe": {"en": "Executable / installer", "es": "Ejecutable / instalador"},
    "hint.ext.archive": {"en": "Archive", "es": "Comprimido"},
    "hint.ext.video": {"en": "Video", "es": "Vídeo"},
    "hint.ext.log": {"en": "Log", "es": "Registro"},
    "hint.ext.tmp": {"en": "Temporary", "es": "Temporal"},
    "hint.ext.bak": {"en": "Backup", "es": "Copia de seguridad"},
    "hint.ext.pst": {"en": "Outlook mail", "es": "Correo Outlook"},
    "hint.ext.ost": {"en": "Outlook cache", "es": "Caché de Outlook"},

    # ---------------------------------------------- categorías de limpieza
    "clean.temp_user.name": {"en": "User temp files", "es": "Temporales del usuario"},
    "clean.temp_user.desc": {"en": "%TEMP% folder. Only files older than 24 h so in-progress installs "
                                   "aren't broken.",
                             "es": "Carpeta %TEMP%. Solo archivos con más de 24 h para no romper "
                                   "instalaciones en curso."},
    "clean.temp_win.name": {"en": "Windows temp files", "es": "Temporales de Windows"},
    "clean.temp_win.desc": {"en": "C:\\Windows\\Temp. Requires administrator for most files.",
                            "es": "C:\\Windows\\Temp. Requiere administrador para la mayoría de archivos."},
    "clean.thumbs.name": {"en": "Thumbnail and icon cache", "es": "Caché de miniaturas e iconos"},
    "clean.thumbs.desc": {"en": "Regenerates itself. Explorer locks part of it while open.",
                          "es": "Se regenera sola. Explorer bloquea parte de ella mientras está abierto."},
    "clean.wer.name": {"en": "Windows error reports", "es": "Informes de errores de Windows"},
    "clean.wer.desc": {"en": "Reports already sent or pending from Windows Error Reporting.",
                       "es": "Informes ya enviados o pendientes de Windows Error Reporting."},
    "clean.dumps.name": {"en": "Program memory dumps", "es": "Volcados de memoria de programas"},
    "clean.dumps.desc": {"en": ".dmp files generated when an application crashes.",
                         "es": "Archivos .dmp generados cuando una aplicación se cuelga."},
    "clean.wu.name": {"en": "Windows Update downloads", "es": "Descargas de Windows Update"},
    "clean.wu.desc": {"en": "Already installed packages. Windows re-downloads them if needed. Requires "
                            "admin.",
                      "es": "Paquetes ya instalados. Windows los vuelve a descargar si los necesita. "
                            "Requiere admin."},
    "clean.do.name": {"en": "Delivery Optimization cache", "es": "Caché de Optimización de distribución"},
    "clean.do.desc": {"en": "Updates shared between PCs. Requires admin.",
                      "es": "Actualizaciones compartidas entre equipos. Requiere admin."},
    "clean.recycle.name": {"en": "Recycle Bin", "es": "Papelera de reciclaje"},
    "clean.recycle.desc": {"en": "Empties the Recycle Bin on all drives. This CANNOT be undone.",
                           "es": "Vacía la Papelera de todas las unidades. NO se puede deshacer."},
    "clean.edge.name": {"en": "Microsoft Edge: cache", "es": "Microsoft Edge: caché"},
    "clean.edge.desc": {"en": "Web and shader cache. Does not delete passwords, history or cookies.",
                        "es": "Caché web y de shaders. No borra contraseñas, historial ni cookies."},
    "clean.chrome.name": {"en": "Google Chrome: cache", "es": "Google Chrome: caché"},
    "clean.chrome.desc": {"en": "Web and shader cache. Does not delete passwords, history or cookies.",
                          "es": "Caché web y de shaders. No borra contraseñas, historial ni cookies."},
    "clean.brave.name": {"en": "Brave: cache", "es": "Brave: caché"},
    "clean.brave.desc": {"en": "Web and shader cache.", "es": "Caché web y de shaders."},
    "clean.firefox.name": {"en": "Firefox: cache", "es": "Firefox: caché"},
    "clean.firefox.desc": {"en": "Web cache (cache2). Does not delete bookmarks or sessions.",
                           "es": "Caché web (cache2). No borra marcadores ni sesiones."},
    "clean.pip.name": {"en": "pip cache", "es": "Caché de pip"},
    "clean.pip.desc": {"en": "Downloaded Python packages. Regenerable.",
                       "es": "Paquetes Python descargados. Regenerable."},
    "clean.npm.name": {"en": "npm / Yarn / pnpm cache", "es": "Caché de npm / Yarn / pnpm"},
    "clean.npm.desc": {"en": "Downloaded Node packages. Regenerable (re-downloaded).",
                       "es": "Paquetes Node descargados. Regenerable (se vuelve a descargar)."},
    "clean.nuget.name": {"en": "NuGet HTTP cache", "es": "Caché HTTP de NuGet"},
    "clean.nuget.desc": {"en": "Only the HTTP cache (not the packages folder).",
                         "es": "Solo la caché HTTP (no la carpeta de paquetes)."},
    "clean.gradle.name": {"en": "Gradle cache", "es": "Caché de Gradle"},
    "clean.gradle.desc": {"en": "Gradle dependencies and builds. Regenerable, next build will be slower.",
                          "es": "Dependencias y builds de Gradle. Regenerable, la próxima compilación "
                                "será más lenta."},
    "clean.cargo.name": {"en": "Cargo cache (Rust)", "es": "Caché de Cargo (Rust)"},
    "clean.cargo.desc": {"en": "Downloaded crates (registry/cache).",
                         "es": "Crates descargados (registry/cache)."},
    "clean.vscode.name": {"en": "VS Code caches", "es": "Cachés de VS Code"},
    "clean.vscode.desc": {"en": "Web, code and old-extension caches of installed VS Code.",
                          "es": "Caché web, de código y de extensiones antiguas de VS Code instalado."},
    "clean.discord.name": {"en": "Discord / Teams / Slack: cache", "es": "Discord / Teams / Slack: caché"},
    "clean.discord.desc": {"en": "Caches of Electron messaging apps.",
                           "es": "Cachés de apps Electron de mensajería."},
    "clean.dx.name": {"en": "DirectX / GPU shader cache", "es": "Caché de shaders DirectX / GPU"},
    "clean.dx.desc": {"en": "Shaders compiled by games and drivers. They regenerate.",
                      "es": "Shaders compilados por juegos y drivers. Se regeneran."},
    "clean.recycle_location": {"en": "Recycle Bin (all drives)", "es": "Papelera de reciclaje (todas las unidades)"},
    "clean.partial_admin": {"en": "Without admin only part will be deleted.",
                            "es": "Sin admin solo se borrará una parte."},
    "clean.skipped_note": {"en": "{n} files in use or without permission were skipped.",
                           "es": "{n} archivos en uso o sin permiso se han omitido."},

    # ----------------------------------------- tipos de librerías de dev
    "devkind.node": {"en": "Node dependencies (npm/yarn/pnpm)", "es": "Dependencias Node (npm/yarn/pnpm)"},
    "devkind.venv": {"en": "Python virtual environment", "es": "Entorno virtual Python"},
    "devkind.pycache": {"en": "Python bytecode", "es": "Bytecode Python"},
    "devkind.pytest": {"en": "pytest cache", "es": "Caché de pytest"},
    "devkind.mypy": {"en": "mypy cache", "es": "Caché de mypy"},
    "devkind.ruff": {"en": "ruff cache", "es": "Caché de ruff"},
    "devkind.tox": {"en": "tox environments", "es": "Entornos tox"},
    "devkind.rustmaven": {"en": "Rust/Maven build", "es": "Compilación Rust/Maven"},
    "devkind.gradlecache": {"en": "Project Gradle cache", "es": "Caché Gradle del proyecto"},
    "devkind.gradlecmake": {"en": "Gradle/CMake build", "es": "Compilación Gradle/CMake"},
    "devkind.next": {"en": "Next.js build", "es": "Compilación Next.js"},
    "devkind.nuxt": {"en": "Nuxt build", "es": "Compilación Nuxt"},
    "devkind.angular": {"en": "Angular cache", "es": "Caché Angular"},
    "devkind.parcel": {"en": "Parcel cache", "es": "Caché Parcel"},
    "devkind.turbo": {"en": "Turborepo cache", "es": "Caché Turborepo"},
    "devkind.dotnet_obj": {"en": ".NET intermediates", "es": ".NET intermedios"},
    "devkind.dotnet_bin": {"en": ".NET build output", "es": ".NET compilados"},
    "devkind.haskell": {"en": "Haskell build", "es": "Compilación Haskell"},
    "devkind.dart": {"en": "Dart/Flutter tools", "es": "Herramientas Dart/Flutter"},
    "devkind.cocoapods": {"en": "CocoaPods dependencies", "es": "Dependencias CocoaPods"},

    # ---------------------------------------- herramientas del sistema
    "systool.storage.title": {"en": "Open Windows Storage", "es": "Abrir Almacenamiento de Windows"},
    "systool.storage.desc": {"en": "Official Settings > System > Storage view.",
                             "es": "Vista oficial de Configuración > Sistema > Almacenamiento."},
    "systool.storage.effect": {"en": "Only opens Settings.", "es": "Solo abre Configuración."},
    "systool.apps.title": {"en": "Open Installed apps", "es": "Abrir Aplicaciones instaladas"},
    "systool.apps.desc": {"en": "Includes Microsoft Store apps, which don't always appear in the classic "
                                "registry.",
                          "es": "Incluye apps de Microsoft Store, que no siempre aparecen en el registro "
                                "clásico."},
    "systool.apps.effect": {"en": "Only opens Settings.", "es": "Solo abre Configuración."},
    "systool.taskmgr_startup.title": {"en": "Manage startup programs", "es": "Administrar programas de inicio"},
    "systool.taskmgr_startup.desc": {"en": "Opens Task Manager on the Startup tab to disable entries "
                                           "reversibly.",
                                     "es": "Abre el Administrador de tareas en la pestaña Inicio para "
                                           "desactivar entradas de forma reversible."},
    "systool.taskmgr_startup.effect": {"en": "Only opens Task Manager.",
                                       "es": "Solo abre el Administrador de tareas."},
    "systool.cleanmgr.title": {"en": "Windows Disk Cleanup", "es": "Liberador de espacio de Windows"},
    "systool.cleanmgr.desc": {"en": "Classic Microsoft tool (includes \"Clean up system files\").",
                              "es": "Herramienta clásica de Microsoft (incluye «Limpiar archivos del "
                                    "sistema»)."},
    "systool.cleanmgr.effect": {"en": "Opens the tool; deletes nothing until you use it.",
                                "es": "Abre la herramienta; no borra nada hasta que la uses."},
    "systool.restore.title": {"en": "Create a restore point", "es": "Crear punto de restauración"},
    "systool.restore.desc": {"en": "Opens System Protection. Recommended before bulk uninstalls.",
                             "es": "Abre Protección del sistema. Recomendado antes de desinstalar en "
                                   "masa."},
    "systool.restore.effect": {"en": "Only opens the window.", "es": "Solo abre la ventana."},
    "systool.analyze_sxs.title": {"en": "Analyze component store (WinSxS)",
                                  "es": "Analizar almacén de componentes (WinSxS)"},
    "systool.analyze_sxs.desc": {"en": "Reports how much can be recovered from WinSxS. Changes nothing.",
                                 "es": "Informa cuánto se puede recuperar de WinSxS. No modifica nada."},
    "systool.analyze_sxs.effect": {"en": "Runs DISM in analysis mode (read-only) in a visible console.",
                                   "es": "Ejecuta DISM en modo análisis (solo lectura) en una consola "
                                         "visible."},
    "systool.clean_sxs.title": {"en": "Clean Windows components (WinSxS)",
                                "es": "Limpiar componentes de Windows (WinSxS)"},
    "systool.clean_sxs.desc": {"en": "Removes old versions of components replaced by updates. After this "
                                     "you won't be able to uninstall those old updates.",
                               "es": "Elimina versiones antiguas de componentes reemplazados por "
                                     "actualizaciones. Tras esto no podrás desinstalar esas "
                                     "actualizaciones antiguas."},
    "systool.clean_sxs.effect": {"en": "DISM deletes old components. May take several minutes. "
                                       "Irreversible.",
                                 "es": "DISM borra componentes antiguos. Puede tardar varios minutos. "
                                       "Irreversible."},
    "systool.hiber_off.title": {"en": "Disable hibernation (deletes hiberfil.sys)",
                                "es": "Desactivar hibernación (borra hiberfil.sys)"},
    "systool.hiber_off.desc": {"en": "Frees as many GB as ~40% of your RAM. Also disables \"Fast "
                                     "startup\".",
                               "es": "Libera tantos GB como ~40 % de tu RAM. Desactiva también el "
                                     "«Inicio rápido»."},
    "systool.hiber_off.effect": {"en": "Disables hibernation. Reversible with \"powercfg /hibernate "
                                       "on\".",
                                 "es": "Desactiva la hibernación. Reversible con «powercfg /hibernate "
                                       "on»."},
    "systool.hiber_on.title": {"en": "Re-enable hibernation", "es": "Reactivar hibernación"},
    "systool.hiber_on.desc": {"en": "Recreates hiberfil.sys and enables Fast startup.",
                              "es": "Vuelve a crear hiberfil.sys y habilita el Inicio rápido."},
    "systool.hiber_on.effect": {"en": "Re-enables hibernation.", "es": "Reactiva la hibernación."},

    # ------------------------------------------------- ventana, tamaño y salida
    "app.ui_size_hint": {
        "en": "Interface size: Ctrl + to enlarge, Ctrl − to shrink, Ctrl 0 (or click the percentage) for 100%.",
        "es": "Tamaño de la interfaz: Ctrl + para ampliar, Ctrl − para reducir, Ctrl 0 (o clic en el "
              "porcentaje) para volver al 100 %."},
    "app.busy_wait": {"en": "Wait until this finishes: {what}", "es": "Espera a que termine: {what}"},
    "app.pending.delete": {"en": "deleting files", "es": "borrado de archivos"},
    "app.pending.clean": {"en": "cleanup in progress", "es": "limpieza en curso"},
    "app.pending.optimize": {"en": "closing or slowing down programs", "es": "cierre o ralentización de programas"},
    "app.exit.busy_title": {"en": "Operation in progress", "es": "Operación en curso"},
    "app.exit.busy_body": {
        "en": "Super Limpio is still working:\n\n{what}\n\nIf you exit now it stops halfway: what is already "
              "done stays done and the rest is left untouched.\n\nExit anyway?",
        "es": "Super Limpio sigue trabajando:\n\n{what}\n\nSi sales ahora se queda a medias: lo que ya está "
              "hecho, hecho queda, y el resto no se toca.\n\n¿Salir de todos modos?"},
    "app.exit.self_title": {"en": "Close Super Limpio", "es": "Cerrar Super Limpio"},
    "app.exit.self_body": {
        "en": "This is Super Limpio itself. It is not force-ended like other processes: it closes in an "
              "orderly way. Running analyses are stopped, your preferences are kept and, if Efficient mode "
              "is on, you will be asked whether to undo it first.",
        "es": "Este es el propio Super Limpio. No se finaliza a la fuerza como los demás procesos: se cierra "
              "de forma ordenada. Se detienen los análisis en marcha, se conservan tus preferencias y, si el "
              "Modo eficiente está activo, se te pregunta antes si quieres deshacerlo."},
    "app.exit.self_ok": {"en": "Close Super Limpio", "es": "Cerrar Super Limpio"},

    # ------------------------------------------ importancia para el sistema
    "crit.level.0": {"en": "Normal", "es": "Normal"},
    "crit.level.1": {"en": "Caution", "es": "Precaución"},
    "crit.level.2": {"en": "Important", "es": "Importante"},
    "crit.level.3": {"en": "Vital", "es": "Vital"},

    "crit.proc.self": {"en": "This is Super Limpio, the application you are using.",
                       "es": "Es Super Limpio, la aplicación que estás usando."},
    "crit.proc.system": {"en": "The Windows kernel and its drivers.",
                         "es": "El núcleo de Windows y sus controladores."},
    "crit.proc.idle": {"en": "Not a program: it stands for the processor time nobody is using.",
                       "es": "No es un programa: representa el tiempo de procesador que nadie usa."},
    "crit.proc.registry": {"en": "Holds the Windows registry in memory.",
                           "es": "Mantiene en memoria el registro de Windows."},
    "crit.proc.memcompression": {
        "en": "Windows memory compression: it squeezes RAM that is not in use so more fits. Its size is "
              "memory saved, not wasted.",
        "es": "Compresión de memoria de Windows: aprieta la RAM que no se usa para que quepa más. Lo que "
              "ocupa es memoria ahorrada, no gastada."},
    "crit.proc.secure": {"en": "Isolated security environment of Windows (virtualization-based security).",
                         "es": "Entorno de seguridad aislado de Windows (seguridad basada en virtualización)."},
    "crit.proc.smss": {"en": "Session Manager: starts the user sessions and the rest of the system.",
                       "es": "Administrador de sesiones: arranca las sesiones de usuario y el resto del sistema."},
    "crit.proc.csrss": {"en": "Client/Server Runtime: every Windows program depends on it.",
                        "es": "Subsistema cliente/servidor: todos los programas de Windows dependen de él."},
    "crit.proc.wininit": {"en": "Windows start-up process: it launches the services and the security system.",
                          "es": "Proceso de arranque de Windows: lanza los servicios y el sistema de seguridad."},
    "crit.proc.services": {"en": "Service Control Manager: starts and supervises every Windows service.",
                           "es": "Administrador de servicios: inicia y vigila todos los servicios de Windows."},
    "crit.proc.lsass": {"en": "Local Security Authority: checks passwords and logons.",
                        "es": "Autoridad de seguridad local: comprueba contraseñas e inicios de sesión."},
    "crit.proc.lsaiso": {"en": "Credential Guard: keeps passwords in an isolated area.",
                         "es": "Credential Guard: guarda las contraseñas en una zona aislada."},
    "crit.proc.winlogon": {"en": "Windows logon: owns your session and the lock screen.",
                           "es": "Inicio de sesión de Windows: sostiene tu sesión y la pantalla de bloqueo."},
    "crit.proc.svchost": {
        "en": "Service host: each copy runs Windows services (network, audio, updates, Bluetooth...).",
        "es": "Host de servicios: cada copia ejecuta servicios de Windows (red, sonido, actualizaciones, "
              "Bluetooth...)."},
    "crit.proc.dwm": {"en": "Desktop Window Manager: draws every window on screen.",
                      "es": "Administrador de ventanas del escritorio: dibuja todas las ventanas en pantalla."},
    "crit.proc.fontdrvhost": {"en": "Font driver host: renders the text of every program.",
                              "es": "Host del controlador de fuentes: dibuja el texto de todos los programas."},
    "crit.proc.essential": {"en": "Essential Windows process.", "es": "Proceso esencial de Windows."},
    "crit.proc.defender": {"en": "Microsoft Defender antivirus engine.",
                           "es": "Motor del antivirus Microsoft Defender."},
    "crit.proc.defender_net": {"en": "Microsoft Defender network inspection.",
                               "es": "Inspección de red de Microsoft Defender."},
    "crit.proc.security_center": {"en": "Windows Security service.", "es": "Servicio de Seguridad de Windows."},
    "crit.proc.sgrm": {"en": "System Guard: checks that Windows has not been tampered with.",
                       "es": "System Guard: comprueba que Windows no ha sido manipulado."},
    "crit.proc.security": {"en": "Security or anti-cheat software.", "es": "Software de seguridad o anti-trampas."},
    "crit.proc.audiodg": {"en": "Windows audio engine.", "es": "Motor de sonido de Windows."},
    "crit.proc.spooler": {"en": "Print spooler.", "es": "Cola de impresión."},
    "crit.proc.wudfhost": {"en": "Host for device drivers (USB, sensors, card readers...).",
                           "es": "Host de controladores de dispositivos (USB, sensores, lectores de tarjetas...)."},
    "crit.proc.update": {"en": "Windows Update: it is installing or preparing updates.",
                         "es": "Windows Update: está instalando o preparando actualizaciones."},
    "crit.proc.msiexec": {"en": "Windows Installer: a program is being installed, repaired or removed.",
                          "es": "Windows Installer: se está instalando, reparando o quitando un programa."},
    "crit.proc.explorer": {"en": "File Explorer: also the desktop, the taskbar and the Start menu.",
                           "es": "Explorador de archivos: también el escritorio, la barra de tareas y el menú Inicio."},
    "crit.proc.sihost": {"en": "Shell infrastructure: notifications, action center and Start menu.",
                         "es": "Infraestructura del escritorio: notificaciones, centro de actividades y menú Inicio."},
    "crit.proc.shell": {"en": "Part of the Windows desktop.", "es": "Parte del escritorio de Windows."},
    "crit.proc.ctfmon": {"en": "Text input: keyboard layouts, accents, emoji panel and handwriting.",
                         "es": "Entrada de texto: idiomas del teclado, acentos, panel de emojis y escritura a mano."},
    "crit.proc.search": {"en": "Windows search box.", "es": "Buscador de Windows."},
    "crit.proc.indexer": {"en": "Search indexer: keeps the index that makes file searches instant.",
                          "es": "Indexador de búsqueda: mantiene el índice que hace instantáneas las búsquedas."},
    "crit.proc.startmenu": {"en": "The Start menu.", "es": "El menú Inicio."},
    "crit.proc.shellexp": {"en": "Taskbar panels: clock, calendar, volume and network.",
                           "es": "Paneles de la barra de tareas: reloj, calendario, volumen y red."},
    "crit.proc.taskhost": {"en": "Host for Windows background tasks.",
                           "es": "Host de tareas en segundo plano de Windows."},
    "crit.proc.runtimebroker": {"en": "Permission broker for Microsoft Store apps.",
                                "es": "Gestor de permisos de las aplicaciones de la Tienda."},
    "crit.proc.appframe": {"en": "Window frame of Microsoft Store apps.",
                           "es": "Marco de las ventanas de las aplicaciones de la Tienda."},
    "crit.proc.dllhost": {"en": "COM surrogate: runs components on behalf of other programs (thumbnails, "
                                "previews...).",
                          "es": "Sustituto COM: ejecuta componentes por cuenta de otros programas (miniaturas, "
                                "vistas previas...)."},
    "crit.proc.conhost": {"en": "Console window host: the window of a command-line program.",
                          "es": "Host de consola: la ventana de un programa de línea de comandos."},
    "crit.proc.wmi": {"en": "WMI provider: answers system queries from other programs.",
                      "es": "Proveedor WMI: responde consultas del sistema que hacen otros programas."},
    "crit.proc.dashost": {"en": "Device pairing (Bluetooth, wireless displays, printers).",
                          "es": "Emparejamiento de dispositivos (Bluetooth, pantallas inalámbricas, impresoras)."},
    "crit.proc.wlan": {"en": "Wi-Fi adapter extension.", "es": "Extensión del adaptador Wi-Fi."},
    "crit.proc.vmmem": {"en": "Memory of a virtual machine (WSL, Docker, Windows Sandbox or Hyper-V).",
                        "es": "Memoria de una máquina virtual (WSL, Docker, Windows Sandbox o Hyper-V)."},
    "crit.proc.windows_tool": {"en": "A Windows program that you opened.",
                               "es": "Programa de Windows que has abierto tú."},
    "crit.proc.windows_service": {"en": "Windows service.", "es": "Servicio de Windows."},
    "crit.proc.app_service": {"en": "Background service installed by a program.",
                              "es": "Servicio en segundo plano instalado por un programa."},
    "crit.proc.windows_component": {"en": "Windows component.", "es": "Componente de Windows."},
    "crit.proc.no_access": {
        "en": "Windows does not let a standard user inspect it: it is usually a service or a system component.",
        "es": "Windows no deja inspeccionarlo como usuario estándar: suele ser un servicio o un componente "
              "del sistema."},
    "crit.proc.normal": {"en": "Ordinary program: Windows does not depend on it.",
                         "es": "Programa corriente: Windows no depende de él."},

    "crit.risk.self": {"en": "It can be closed safely: nothing is left half done.",
                       "es": "Se puede cerrar con seguridad: no deja nada a medias."},
    "crit.risk.vital": {
        "en": "If it stops, Windows halts with a blue screen or restarts at once: everything unsaved is lost.",
        "es": "Si se detiene, Windows se para con una pantalla azul o se reinicia al momento: se pierde todo "
              "lo que no esté guardado."},
    "crit.risk.session": {
        "en": "If it stops, the screen goes black and the session is closed: everything unsaved is lost.",
        "es": "Si se detiene, la pantalla se queda en negro y se cierra la sesión: se pierde todo lo que no "
              "esté guardado."},
    "crit.risk.svchost": {
        "en": "Ending one can cut the network or the sound, and some copies restart the PC.",
        "es": "Finalizar una copia puede dejarte sin red o sin sonido, y algunas reinician el equipo."},
    "crit.risk.security": {"en": "Closing it leaves the PC unprotected (or gets you kicked out of online games).",
                           "es": "Cerrarlo deja el equipo desprotegido (o te expulsa de los juegos en línea)."},
    "crit.risk.audio": {"en": "Without it there is no sound until Windows starts it again.",
                        "es": "Sin él no hay sonido hasta que Windows lo vuelva a lanzar."},
    "crit.risk.print": {"en": "Without it nothing can be printed and pending jobs are lost.",
                        "es": "Sin él no se puede imprimir y se pierden los trabajos pendientes."},
    "crit.risk.driver": {"en": "The devices that depend on it stop working until they are reconnected.",
                         "es": "Los dispositivos que dependen de él dejan de funcionar hasta reconectarlos."},
    "crit.risk.update": {"en": "Interrupting it can leave an installation half done and broken.",
                         "es": "Interrumpirlo puede dejar una instalación a medias y estropeada."},
    "crit.risk.shell": {
        "en": "If it closes, the desktop and the taskbar vanish for a few seconds, and open folder windows "
              "are lost.",
        "es": "Si se cierra, el escritorio y la barra de tareas desaparecen unos segundos y se pierden las "
              "carpetas abiertas."},
    "crit.risk.input": {"en": "If it closes you may be unable to type accents or switch keyboard language.",
                        "es": "Si se cierra puede que no puedas escribir acentos ni cambiar el idioma del teclado."},
    "crit.risk.relaunch": {"en": "Windows starts it again on its own; something may fail for a moment.",
                           "es": "Windows lo vuelve a lanzar solo; algo puede fallar un momento."},
    "crit.risk.store_apps": {"en": "Closing it closes every open Microsoft Store app.",
                             "es": "Cerrarlo cierra todas las aplicaciones de la Tienda que estén abiertas."},
    "crit.risk.console": {"en": "Closing it ends the command-line program running inside.",
                          "es": "Cerrarlo termina el programa de línea de comandos que hay dentro."},
    "crit.risk.network": {"en": "The Wi-Fi connection drops until it starts again.",
                          "es": "La conexión Wi-Fi se corta hasta que se reinicie."},
    "crit.risk.vm": {"en": "Ending it powers the virtual machine off abruptly. Shut it down from its own program "
                           "(for WSL: wsl --shutdown).",
                     "es": "Finalizarlo apaga la máquina virtual de golpe. Apágala desde su programa (en WSL: "
                           "wsl --shutdown)."},
    "crit.risk.service": {"en": "Stop it from Services (services.msc), not by ending the process: whatever "
                                "depends on it stops working.",
                          "es": "Se detiene desde Servicios (services.msc), no finalizando el proceso: lo que "
                                "dependa de él deja de funcionar."},
    "crit.risk.component": {"en": "Closing it is not recommended: a Windows feature may stop working until "
                                  "the next restart.",
                            "es": "No se recomienda cerrarlo: alguna función de Windows puede dejar de funcionar "
                                  "hasta reiniciar."},
    "crit.risk.unknown": {"en": "Run Super Limpio as administrator to find out what it is before closing it.",
                          "es": "Ejecuta Super Limpio como administrador para saber qué es antes de cerrarlo."},
    "crit.risk.normal": {"en": "Closing it only loses whatever was not saved in it.",
                         "es": "Cerrarlo solo hace perder lo que no esté guardado en él."},

    "crit.path.drive_root": {"en": "The root of a drive.", "es": "La raíz de una unidad."},
    "crit.path.windows": {"en": "The Windows folder: the operating system itself.",
                          "es": "La carpeta de Windows: el propio sistema operativo."},
    "crit.path.system32": {"en": "Windows core: its programs, libraries and drivers.",
                           "es": "El corazón de Windows: sus programas, bibliotecas y controladores."},
    "crit.path.registry": {"en": "The Windows registry (all system and program settings).",
                           "es": "El registro de Windows (toda la configuración del sistema y de los programas)."},
    "crit.path.drivers": {"en": "Device drivers.", "es": "Controladores de dispositivos."},
    "crit.path.winsxs": {"en": "Windows component store: every version of the system files.",
                         "es": "Almacén de componentes de Windows: todas las versiones de los archivos del sistema."},
    "crit.path.installer": {"en": "Installers Windows keeps to repair, update or uninstall programs.",
                            "es": "Instaladores que Windows guarda para reparar, actualizar o desinstalar programas."},
    "crit.path.update_cache": {"en": "Updates already downloaded by Windows Update.",
                               "es": "Actualizaciones ya descargadas por Windows Update."},
    "crit.path.update_db": {"en": "Windows Update database.", "es": "Base de datos de Windows Update."},
    "crit.path.windows_temp": {"en": "Windows temporary files.", "es": "Archivos temporales de Windows."},
    "crit.path.prefetch": {"en": "Start-up traces that make programs open faster.",
                           "es": "Trazas de arranque que hacen que los programas abran antes."},
    "crit.path.windows_logs": {"en": "Windows logs.", "es": "Registros (logs) de Windows."},
    "crit.path.dumps": {"en": "Memory dumps saved after a crash.", "es": "Volcados de memoria guardados tras un fallo."},
    "crit.path.windows_component": {"en": "Part of Windows.", "es": "Parte de Windows."},
    "crit.path.boot": {"en": "Boot files: what starts Windows.", "es": "Archivos de arranque: lo que inicia Windows."},
    "crit.path.recovery": {"en": "Windows recovery environment.", "es": "Entorno de recuperación de Windows."},
    "crit.path.pagefile": {"en": "Paging file (virtual memory).", "es": "Archivo de paginación (memoria virtual)."},
    "crit.path.hiberfil": {"en": "Hibernation and Fast startup file.",
                           "es": "Archivo de hibernación y del Inicio rápido."},
    "crit.path.swapfile": {"en": "Virtual memory of modern apps.", "es": "Memoria virtual de las apps modernas."},
    "crit.path.dumpstack": {"en": "Crash-dump log of Windows.", "es": "Registro de volcados de fallos de Windows."},
    "crit.path.restore_points": {"en": "Restore points and the search index of the drive.",
                                 "es": "Puntos de restauración e índice de búsqueda de la unidad."},
    "crit.path.recycle_bin": {"en": "The Recycle Bin of the drive.", "es": "La Papelera de reciclaje de la unidad."},
    "crit.path.program_files": {"en": "The folder where programs are installed.",
                                "es": "La carpeta donde se instalan los programas."},
    "crit.path.installed_program": {"en": "Files of an installed program.", "es": "Archivos de un programa instalado."},
    "crit.path.store_apps": {"en": "Microsoft Store apps and their data.",
                             "es": "Aplicaciones de la Tienda y sus datos."},
    "crit.path.programdata": {"en": "Data shared by Windows and the installed programs.",
                              "es": "Datos compartidos de Windows y de los programas instalados."},
    "crit.path.package_cache": {"en": "Installers saved by programs to repair or uninstall themselves.",
                                "es": "Instaladores que guardan los programas para repararse o desinstalarse."},
    "crit.path.app_data": {"en": "Settings and data of a program.", "es": "Configuración y datos de un programa."},
    "crit.path.ms_user_data": {"en": "Your settings for Windows and Microsoft programs.",
                               "es": "Tu configuración de Windows y de programas de Microsoft."},
    "crit.path.appdata_root": {"en": "Where every program keeps your settings.",
                               "es": "Donde todos los programas guardan tu configuración."},
    "crit.path.user_temp": {"en": "Your temporary files.", "es": "Tus archivos temporales."},
    "crit.path.profile": {"en": "Your user profile: documents, desktop and all your settings.",
                          "es": "Tu perfil de usuario: documentos, escritorio y toda tu configuración."},
    "crit.path.user_registry": {"en": "Your part of the Windows registry.", "es": "Tu parte del registro de Windows."},
    "crit.path.personal_folder": {"en": "One of your personal folders.", "es": "Una de tus carpetas personales."},
    "crit.path.personal": {"en": "A personal file: Windows does not need it.",
                           "es": "Archivo personal: Windows no lo necesita."},
    "crit.path.users_root": {"en": "User profiles of this PC.", "es": "Perfiles de usuario de este equipo."},
    "crit.path.other_profile": {"en": "Files of another user of this PC.",
                                "es": "Archivos de otro usuario de este equipo."},
    "crit.path.own_app": {"en": "Part of Super Limpio itself.", "es": "Forma parte del propio Super Limpio."},
    "crit.path.normal": {"en": "Not part of Windows or of an installed program.",
                         "es": "No forma parte de Windows ni de un programa instalado."},

    "crit.prisk.vital": {"en": "Without it Windows does not start or stops working. Super Limpio will not "
                               "delete it.",
                         "es": "Sin ello Windows no arranca o deja de funcionar. Super Limpio no lo borra."},
    "crit.prisk.drive_root": {"en": "Deleting it would erase the whole drive. Super Limpio will not delete it.",
                              "es": "Borrarla sería borrar la unidad entera. Super Limpio no la borra."},
    "crit.prisk.important": {"en": "Deleting it breaks Windows features or programs. Super Limpio will not "
                                   "delete it.",
                             "es": "Borrarlo estropea funciones de Windows o programas. Super Limpio no lo borra."},
    "crit.prisk.winsxs": {"en": "It must never be deleted by hand: reduce it with \"System tools\" (DISM).",
                          "es": "Nunca se borra a mano: se reduce desde «Herramientas del sistema» (DISM)."},
    "crit.prisk.managed": {"en": "Windows manages it; it is resized or removed from the system settings, "
                                 "not by deleting it.",
                           "es": "Lo gestiona Windows; se ajusta o se quita desde la configuración del sistema, "
                                 "no borrándolo."},
    "crit.prisk.regen": {"en": "Windows recreates it. Empty it from \"Cleanup\", which knows what is safe.",
                         "es": "Windows lo vuelve a crear. Vacíalo desde «Limpieza», que sabe qué es seguro."},
    "crit.prisk.recycle_bin": {"en": "Empty it from \"Cleanup\" instead of deleting the folder.",
                               "es": "Vacíala desde «Limpieza» en vez de borrar la carpeta."},
    "crit.prisk.program": {"en": "Deleting it by hand leaves the program broken and still registered. Use "
                                 "\"Programs > Uninstall\".",
                           "es": "Borrarlo a mano deja el programa roto y todavía registrado. Usa «Programas > "
                                 "Desinstalar»."},
    "crit.prisk.package_cache": {"en": "Without them some programs cannot be repaired, updated or uninstalled.",
                                 "es": "Sin ellos algunos programas no se pueden reparar, actualizar ni desinstalar."},
    "crit.prisk.app_data": {"en": "Windows keeps working, but that program may lose its settings, accounts or "
                                  "saved data.",
                            "es": "Windows sigue funcionando, pero ese programa puede perder su configuración, "
                                  "sus cuentas o sus datos guardados."},
    "crit.prisk.profile": {"en": "Deleting it destroys your account on this PC. Super Limpio will not delete it.",
                           "es": "Borrarlo destruye tu cuenta en este equipo. Super Limpio no lo borra."},
    "crit.prisk.personal_folder": {"en": "The folder itself cannot be deleted; what you keep inside can.",
                                   "es": "La carpeta en sí no se borra; lo que guardas dentro, sí."},
    "crit.prisk.personal": {"en": "No risk for the system, but it is yours and cannot be regenerated: check "
                                  "that you do not need it.",
                            "es": "Sin riesgo para el sistema, pero es tuyo y no se regenera: comprueba que no "
                                  "lo necesitas."},
    "crit.prisk.other_profile": {"en": "Windows keeps working, but that person loses their files.",
                                 "es": "Windows sigue funcionando, pero esa persona pierde sus archivos."},
    "crit.prisk.own_app": {"en": "Deleting it breaks this application.", "es": "Borrarlo estropea esta aplicación."},
    "crit.prisk.normal": {"en": "No risk for the system; just check that you do not need it.",
                          "es": "Sin riesgo para el sistema; solo comprueba que no lo necesitas."},

    # ------------------------------------------- avisos de importancia en las vistas
    "memory.col.level": {"en": "Importance", "es": "Importancia"},
    "memory.this_app": {"en": "this application", "es": "esta aplicación"},
    "memory.detail_hint": {
        "en": "Select a process to see what it is, whether Windows needs it and what happens if it is closed.",
        "es": "Selecciona un proceso para ver qué es, si Windows lo necesita y qué pasa si se cierra."},
    "memory.detail_title": {"en": "{name}  ·  {level}", "es": "{name}  ·  {level}"},
    "memory.detail_multi": {"en": "{n} selected; the most delicate one:  ",
                            "es": "{n} seleccionados; el más delicado:  "},
    "memory.detail_blocked": {"en": "Super Limpio will not end it.", "es": "Super Limpio no lo finaliza."},
    "memory.kill.warnings": {"en": "\n\nWhat these are for the system:\n{items}",
                             "es": "\n\nQué son para el sistema:\n{items}"},
    "memory.kill.system_warning": {
        "en": "\n\nWarning: the list includes Windows components or services. Read below what each one is "
              "before continuing.",
        "es": "\n\nAtención: la lista incluye componentes o servicios de Windows. Lee abajo qué es cada uno "
              "antes de continuar."},
    "disk.legend.vital": {"en": "Vital for Windows", "es": "Vital para Windows"},
    "disk.legend.important": {"en": "System file", "es": "Del sistema"},
    "disk.risk_line": {"en": "{level}  ·  {text}", "es": "{level}  ·  {text}"},
    "disk.risk_multi": {"en": "{n} of {total} need care; the most delicate one:  ",
                        "es": "{n} de {total} requieren cuidado; el más delicado:  "},
    "disk.delicate_warning": {
        "en": "\n\nWarning: {n} of them are not ordinary files (program data, other users' files...). Read "
              "below what each one is.",
        "es": "\n\nAtención: {n} no son archivos corrientes (datos de programas, archivos de otros "
              "usuarios...). Lee abajo qué es cada uno."},
    "disk.delicate_details": {"en": "\n\nWhat these are for the system:\n{items}",
                              "es": "\n\nQué son para el sistema:\n{items}"},
    "opt.find.hog_system_advice": {
        "en": "Do not close it. If the figure looks abnormal, restart the PC: that is what returns this "
              "memory.",
        "es": "No lo cierres. Si la cifra te parece anormal, reinicia el equipo: es lo que devuelve esta "
              "memoria."},
    "opt.find.growth_system_advice": {
        "en": "It usually settles on its own. If it keeps growing for hours, restart the PC and check for "
              "pending driver or Windows updates.",
        "es": "Suele estabilizarse solo. Si sigue creciendo durante horas, reinicia el equipo y revisa si "
              "hay actualizaciones de controladores o de Windows pendientes."},
    "opt.find.bg_cpu_system_advice": {
        "en": "It is usually temporary work (antivirus scan, updates, indexing): let it finish. If it goes "
              "on for hours, restart the PC.",
        "es": "Suele ser trabajo temporal (análisis del antivirus, actualizaciones, indexado): déjalo "
              "terminar. Si dura horas, reinicia el equipo."},
    "opt.find.system_share": {"en": "Windows itself holds {size} ({pct} of RAM)",
                              "es": "El propio Windows reserva {size} ({pct} de la RAM)"},
    "opt.find.system_share_detail": {"en": "{n} system programs, {vital} of them vital",
                                     "es": "{n} programas del sistema, {vital} de ellos vitales"},
    "opt.find.system_share_advice": {
        "en": "This memory belongs to the system processes marked \"Vital\" or \"Important\" in the table. "
              "It is not freed by closing anything, and Super Limpio never proposes them: the room to gain "
              "is in the programs marked as normal.",
        "es": "Es la memoria de los procesos del sistema marcados como «Vital» o «Importante» en la tabla. "
              "No se libera cerrando nada, y Super Limpio nunca los propone: el margen está en los "
              "programas marcados como normales."},

    # ------------------------------------------------------ varias plataformas
    "zip.err.no_aes": {"en": "This computer has no system AES provider, so archives cannot be password-protected.",
                       "es": "Este equipo no tiene cifrado AES del sistema, así que no se puede poner contraseña."},
    "opt.reason.no_undo": {
        "en": "On this system a lowered priority cannot be restored without administrator rights, so it "
              "is not proposed. You can still choose it.",
        "es": "En este sistema una prioridad bajada no se puede devolver sin permisos de administrador, "
              "así que no se propone. Puedes elegirla tú."},
    "opt.eff.confirm.no_undo": {
        "en": "Warning: on this system slowing down CANNOT be undone from Super Limpio. Each program "
              "recovers its normal priority when you close and reopen it.",
        "es": "Atención: en este sistema ralentizar NO se puede deshacer desde Super Limpio. Cada programa "
              "recupera su prioridad normal cuando lo cierras y lo vuelves a abrir."},

    # ---------------------------------------------------------------- Linux
    "linux.not_available": {"en": "Not available on Linux", "es": "No disponible en Linux"},
    "linux.nice_denied": {
        "en": "Linux only lets an administrator raise a priority again; it returns to normal when the "
              "program is restarted.",
        "es": "Linux solo deja volver a subir una prioridad a un administrador; vuelve a la normal al "
              "reiniciar el programa."},
    "linux.no_opener": {"en": "xdg-open is not installed, so nothing can be opened from here.",
                        "es": "No está instalado xdg-open, así que no se puede abrir nada desde aquí."},
    "linux.no_terminal": {"en": "No terminal emulator was found. Run the command yourself in a terminal.",
                          "es": "No se ha encontrado ninguna terminal. Ejecuta tú el comando en una terminal."},
    "linux.press_enter": {"en": "Press Enter to close this window...",
                          "es": "Pulsa Intro para cerrar esta ventana..."},
    "linux.uninstall_manual": {
        "en": "This application does not belong to any package, so there is no official way to remove it. "
              "Its menu entry is:\n{path}",
        "es": "Esta aplicación no pertenece a ningún paquete, así que no hay una vía oficial para quitarla. "
              "Su entrada del menú es:\n{path}"},
    "linux.uninstall_sudo": {"en": "It affects the whole system: the terminal will ask for your sudo password.",
                             "es": "Afecta a todo el sistema: la terminal pedirá tu contraseña de sudo."},
    "startup.src.autostart_user": {"en": "Autostart (your user)", "es": "Autoarranque (tu usuario)"},
    "startup.src.autostart_system": {"en": "Autostart (all users)", "es": "Autoarranque (todos los usuarios)"},
    "startup.src.systemd_user": {"en": "systemd user service", "es": "Servicio de usuario de systemd"},
    "programs.scope.deb": {"en": "System package (deb)", "es": "Paquete del sistema (deb)"},
    "programs.scope.rpm": {"en": "System package (rpm)", "es": "Paquete del sistema (rpm)"},
    "programs.scope.pacman": {"en": "System package (pacman)", "es": "Paquete del sistema (pacman)"},
    "programs.scope.flatpak": {"en": "Flatpak", "es": "Flatpak"},
    "programs.scope.snap": {"en": "Snap", "es": "Snap"},
    "programs.scope.user_app": {"en": "Your user, no package", "es": "Tu usuario, sin paquete"},
    "cleaner.group.Linux": {"en": "System", "es": "Sistema"},
    "clean.pkgcache.name": {"en": "Downloaded packages", "es": "Paquetes descargados"},
    "clean.pkgcache.desc": {"en": "Installers kept by the package manager (apt, dnf, pacman) after installing. "
                                  "They are downloaded again if needed.",
                            "es": "Instaladores que guarda el gestor de paquetes (apt, dnf, pacman) tras instalar. "
                                  "Se vuelven a descargar si hacen falta."},
    "clean.thumbs.name@linux": {"en": "Thumbnail cache", "es": "Caché de miniaturas"},
    "clean.thumbs.desc@linux": {"en": "Previews made by the file manager. Rebuilt on demand.",
                                "es": "Vistas previas que crea el gestor de archivos. Se regeneran solas."},
    "clean.dumps.name@linux": {"en": "Crash reports and core dumps", "es": "Informes de fallo y volcados de memoria"},
    "clean.dumps.desc@linux": {"en": "Files saved when a program crashes (/var/crash, systemd-coredump).",
                               "es": "Archivos guardados cuando un programa se cuelga (/var/crash, systemd-coredump)."},
    "clean.recycle.name@linux": {"en": "Trash", "es": "Papelera"},
    "clean.recycle.desc@linux": {"en": "Empties your Trash on every mounted disk. It CANNOT be undone.",
                                 "es": "Vacía tu Papelera en todos los discos montados. NO se puede deshacer."},
    "clean.chrome.name@linux": {"en": "Chrome / Chromium: cache", "es": "Chrome / Chromium: caché"},
    "clean.dx.name@linux": {"en": "GPU shader cache", "es": "Caché de shaders de la GPU"},
    "clean.discord.name@linux": {"en": "Discord / Slack: cache", "es": "Discord / Slack: caché"},
    "clean.recycle_location@linux": {"en": "Trash (all mounted disks)", "es": "Papelera (todos los discos montados)"},

    "systool.lx_baobab.title": {"en": "Disk Usage Analyzer", "es": "Analizador de uso de disco"},
    "systool.lx_baobab.desc": {"en": "The desktop's own tool to see what takes up space.",
                               "es": "La herramienta del propio escritorio para ver qué ocupa espacio."},
    "systool.lx_baobab.effect": {"en": "Opens the tool.", "es": "Abre la herramienta."},
    "systool.lx_journal_size.title": {"en": "System log size", "es": "Tamaño del registro del sistema"},
    "systool.lx_journal_size.desc": {"en": "Shows how much disk the systemd journal uses. Changes nothing.",
                                     "es": "Muestra cuánto disco ocupa el registro (journal) de systemd. No cambia nada."},
    "systool.lx_journal_size.effect": {"en": "Read-only query.", "es": "Solo consulta."},
    "systool.lx_journal_vacuum.title": {"en": "Trim the system log to two weeks",
                                        "es": "Recortar el registro del sistema a dos semanas"},
    "systool.lx_journal_vacuum.desc": {"en": "Deletes journal entries older than two weeks.",
                                       "es": "Borra las entradas del registro de más de dos semanas."},
    "systool.lx_journal_vacuum.effect": {"en": "Deletes old system logs. It cannot be undone.",
                                         "es": "Borra registros antiguos del sistema. No se puede deshacer."},
    "systool.lx_apt_autoremove.title": {"en": "Remove packages nobody needs (apt)",
                                        "es": "Quitar paquetes que ya nadie necesita (apt)"},
    "systool.lx_apt_autoremove.desc": {"en": "Dependencies left behind and old kernels. apt lists them and asks first.",
                                       "es": "Dependencias que quedaron sueltas y núcleos antiguos. apt los enumera y pregunta antes."},
    "systool.lx_apt_autoremove.effect": {"en": "Uninstalls the packages apt lists, after you confirm in the terminal.",
                                         "es": "Desinstala los paquetes que apt enumere, tras confirmar tú en la terminal."},
    "systool.lx_apt_clean.title": {"en": "Empty the package cache (apt)", "es": "Vaciar la caché de paquetes (apt)"},
    "systool.lx_apt_clean.desc": {"en": "Deletes the installers apt downloaded.",
                                  "es": "Borra los instaladores que apt ha descargado."},
    "systool.lx_apt_clean.effect": {"en": "Deletes downloaded .deb files. They are fetched again if needed.",
                                    "es": "Borra los .deb descargados. Se vuelven a bajar si hacen falta."},
    "systool.lx_dnf_autoremove.title": {"en": "Remove packages nobody needs (dnf)",
                                        "es": "Quitar paquetes que ya nadie necesita (dnf)"},
    "systool.lx_dnf_autoremove.desc": {"en": "Dependencies left behind. dnf lists them and asks first.",
                                       "es": "Dependencias que quedaron sueltas. dnf las enumera y pregunta antes."},
    "systool.lx_dnf_autoremove.effect": {"en": "Uninstalls the packages dnf lists, after you confirm in the terminal.",
                                         "es": "Desinstala los paquetes que dnf enumere, tras confirmar tú en la terminal."},
    "systool.lx_dnf_clean.title": {"en": "Empty the package cache (dnf)", "es": "Vaciar la caché de paquetes (dnf)"},
    "systool.lx_dnf_clean.desc": {"en": "Deletes downloaded packages and repository data.",
                                  "es": "Borra los paquetes descargados y los datos de los repositorios."},
    "systool.lx_dnf_clean.effect": {"en": "Deletes the dnf cache. It is rebuilt on the next update.",
                                    "es": "Borra la caché de dnf. Se reconstruye en la próxima actualización."},
    "systool.lx_paccache.title": {"en": "Trim the package cache (pacman)", "es": "Recortar la caché de paquetes (pacman)"},
    "systool.lx_paccache.desc": {"en": "Keeps the last three versions of each package and deletes the rest.",
                                 "es": "Conserva las tres últimas versiones de cada paquete y borra el resto."},
    "systool.lx_paccache.effect": {"en": "Deletes old cached packages.", "es": "Borra paquetes antiguos de la caché."},
    "systool.lx_flatpak_unused.title": {"en": "Remove unused Flatpak runtimes",
                                        "es": "Quitar entornos de Flatpak sin uso"},
    "systool.lx_flatpak_unused.desc": {"en": "Runtimes no installed app needs any more. Flatpak lists them and asks first.",
                                       "es": "Entornos que ya no necesita ninguna aplicación. Flatpak los enumera y pregunta antes."},
    "systool.lx_flatpak_unused.effect": {"en": "Uninstalls what Flatpak lists, after you confirm in the terminal.",
                                         "es": "Desinstala lo que Flatpak enumere, tras confirmar tú en la terminal."},
    "systool.lx_fstrim.title": {"en": "Trim SSDs (fstrim)", "es": "Optimizar discos SSD (fstrim)"},
    "systool.lx_fstrim.desc": {"en": "Tells SSDs which blocks are free. Most distributions already do it weekly.",
                               "es": "Indica a los SSD qué bloques están libres. Casi todas las distribuciones ya lo hacen cada semana."},
    "systool.lx_fstrim.effect": {"en": "Runs TRIM on the mounted disks. It deletes no files.",
                                 "es": "Ejecuta TRIM en los discos montados. No borra ningún archivo."},

    "crit.lproc.systemd": {"en": "systemd: starts and supervises everything else in the system.",
                           "es": "systemd: arranca y vigila todo lo demás del sistema."},
    "crit.lproc.journald": {"en": "System log service.", "es": "Servicio de registro del sistema."},
    "crit.lproc.logind": {"en": "Manages user sessions, seats and suspend.",
                          "es": "Gestiona las sesiones de usuario y la suspensión."},
    "crit.lproc.udevd": {"en": "Detects and sets up devices as they are plugged in.",
                         "es": "Detecta y prepara los dispositivos al conectarlos."},
    "crit.lproc.resolved": {"en": "Name resolution (DNS).", "es": "Resolución de nombres (DNS)."},
    "crit.lproc.timesyncd": {"en": "Keeps the clock in sync.", "es": "Mantiene el reloj en hora."},
    "crit.lproc.oomd": {"en": "Steps in when memory runs out, before the system freezes.",
                        "es": "Actúa cuando se agota la memoria, antes de que el sistema se bloquee."},
    "crit.lproc.dbus": {"en": "D-Bus: the channel programs and the desktop use to talk to each other.",
                        "es": "D-Bus: el canal por el que hablan entre sí los programas y el escritorio."},
    "crit.lproc.display": {"en": "The graphical server: draws every window.",
                           "es": "El servidor gráfico: dibuja todas las ventanas."},
    "crit.lproc.xwayland": {"en": "Runs X11 programs inside the Wayland session.",
                            "es": "Hace funcionar los programas X11 dentro de la sesión Wayland."},
    "crit.lproc.desktop": {"en": "The desktop itself: windows, panels and the session.",
                           "es": "El propio escritorio: ventanas, paneles y la sesión."},
    "crit.lproc.login": {"en": "Login screen and session manager.",
                         "es": "Pantalla de inicio de sesión y gestor de la sesión."},
    "crit.lproc.polkit": {"en": "Decides which programs may ask for administrator rights.",
                          "es": "Decide qué programas pueden pedir permisos de administrador."},
    "crit.lproc.wm": {"en": "Window manager: borders, moving and resizing windows.",
                      "es": "Gestor de ventanas: bordes, mover y redimensionar ventanas."},
    "crit.lproc.session": {"en": "Keeps your desktop session together.",
                           "es": "Mantiene en pie tu sesión de escritorio."},
    "crit.lproc.network": {"en": "NetworkManager: wired, Wi-Fi and VPN connections.",
                           "es": "NetworkManager: conexiones por cable, Wi-Fi y VPN."},
    "crit.lproc.packages": {"en": "The package manager: it is installing or updating software.",
                            "es": "El gestor de paquetes: está instalando o actualizando software."},
    "crit.lproc.snapd": {"en": "Runs and updates Snap applications.",
                         "es": "Hace funcionar y actualiza las aplicaciones Snap."},
    "crit.lproc.containers": {"en": "Container engine (Docker / containerd).",
                              "es": "Motor de contenedores (Docker / containerd)."},
    "crit.lproc.sshd": {"en": "SSH server: remote access to this computer.",
                        "es": "Servidor SSH: acceso remoto a este equipo."},
    "crit.lproc.cron": {"en": "Runs scheduled tasks.", "es": "Ejecuta las tareas programadas."},
    "crit.lproc.system_service": {"en": "System service.", "es": "Servicio del sistema."},
    "crit.lproc.desktop_component": {"en": "A helper piece of the system or the desktop.",
                                     "es": "Pieza auxiliar del sistema o del escritorio."},
    "crit.lpath.etc": {"en": "System-wide configuration: users, passwords, services and network.",
                       "es": "La configuración de todo el sistema: usuarios, contraseñas, servicios y red."},
    "crit.lpath.usr": {"en": "The system's programs and libraries.",
                       "es": "Los programas y las bibliotecas del sistema."},
    "crit.lpath.virtual": {"en": "Not real files: a window onto the kernel and the devices.",
                           "es": "No son archivos reales: son una ventana al núcleo y a los dispositivos."},
    "crit.lpath.root_home": {"en": "The administrator's personal folder.",
                             "es": "La carpeta personal del administrador."},
    "crit.lpath.srv": {"en": "Data served by this computer (web, FTP...).",
                       "es": "Datos que sirve este equipo (web, FTP...)."},
    "crit.lpath.lost_found": {"en": "Where the disk check keeps recovered fragments.",
                              "es": "Donde la comprobación del disco guarda fragmentos recuperados."},
    "crit.lpath.mounts": {"en": "Where other disks and USB drives are attached.",
                          "es": "Donde se conectan los demás discos y memorias USB."},
    "crit.lpath.pkgdb": {"en": "The package manager's database: what is installed.",
                         "es": "La base de datos del gestor de paquetes: qué hay instalado."},
    "crit.lpath.containers": {"en": "Docker images, containers and volumes.",
                              "es": "Imágenes, contenedores y volúmenes de Docker."},
    "crit.lpath.var_cache": {"en": "System caches.", "es": "Cachés del sistema."},
    "crit.lpath.var": {"en": "Data that system services change while running.",
                       "es": "Datos que los servicios del sistema van cambiando al funcionar."},
    "crit.lpath.keys": {"en": "Your keys and certificates (SSH, GPG).",
                        "es": "Tus claves y certificados (SSH, GPG)."},
    "crit.lpath.shell_config": {"en": "Configuration of your terminal and session.",
                                "es": "Configuración de tu terminal y de tu sesión."},
    "crit.lprisk.keys": {"en": "Without them you lose access to servers and encrypted data, and they cannot "
                               "be regenerated.",
                         "es": "Sin ellas pierdes el acceso a servidores y a datos cifrados, y no se pueden "
                               "regenerar."},

    # ---- textos que en Linux dicen otra cosa (clave@linux sustituye a la clave)
    "common.open_explorer@linux": {"en": "Open in file manager", "es": "Abrir en el gestor de archivos"},
    "common.windows_only@linux": {"en": "Not available on Linux", "es": "No disponible en Linux"},
    "app.status_hint@linux": {"en": "Every action asks for confirmation · logged to logs/acciones.log",
                              "es": "Todas las acciones piden confirmación · registro en logs/acciones.log"},
    "nav.startup@linux": {"en": "Session startup", "es": "Inicio de sesión"},
    "startup.title@linux": {"en": "Session startup", "es": "Inicio de sesión"},
    "startup.manage@linux": {"en": "Manage startup applications", "es": "Administrar aplicaciones de inicio"},
    "startup.note@linux": {
        "en": "For safety, Super Limpio only shows this list. To turn an entry off use your desktop's "
              "startup settings (or the «autostart» folder): that is the official, reversible way.",
        "es": "Por seguridad, Super Limpio solo muestra esta lista. Para desactivar una entrada usa los "
              "ajustes de inicio de tu escritorio (o la carpeta «autostart»): es la vía oficial y reversible."},
    "summary.recycle_bin@linux": {"en": "Trash", "es": "Papelera"},
    "summary.drives@linux": {"en": "Disks", "es": "Discos"},
    "disk.prompt@linux": {"en": "Choose a disk or folder and press Analyze.",
                          "es": "Elige un disco o carpeta y pulsa Analizar."},
    "programs.store_apps@linux": {"en": "Software store…", "es": "Tienda de aplicaciones…"},
    "programs.detail@linux": {"en": "Removed with: {cmd}\nPackage: {key}",
                              "es": "Se quita con: {cmd}\nPaquete: {key}"},
    "programs.uninstall_dialog.body@linux": {
        "en": "A terminal will open with the package manager's own command. It lists what it is going to "
              "remove and asks you to confirm; Super Limpio deletes nothing on its own.",
        "es": "Se abrirá una terminal con el comando del propio gestor de paquetes. Enumera lo que va a "
              "quitar y te pide confirmación; Super Limpio no borra nada por su cuenta."},
    "tools.subtitle@linux": {
        "en": "Shortcuts to your distribution's own tools. You see the exact command before running it.",
        "es": "Accesos a las herramientas de tu propia distribución. Ves el comando exacto antes de ejecutarlo."},
    "tools.admin_note@linux": {
        "en": "\n\nIt opens in a terminal, where sudo asks for your password. The terminal stays open so you "
              "can read the result.",
        "es": "\n\nSe abre en una terminal, donde sudo te pide la contraseña. La terminal queda abierta para "
              "que veas el resultado."},
    "safety.drive_root@linux": {"en": "The root of a disk cannot be deleted.",
                                "es": "No se puede borrar la raíz de un disco."},
    "safety.per_drive_system@linux": {
        "en": "System folder of the disk (recovered fragments or another system's trash).",
        "es": "Carpeta del sistema del disco (fragmentos recuperados o la papelera de otro sistema)."},
    "safety.program_files@linux": {
        "en": "It is where programs are installed. Use \"Programs > Uninstall\" so the package manager "
              "removes them properly.",
        "es": "Es donde se instalan los programas. Usa «Programas > Desinstalar» para que el gestor de "
              "paquetes los quite bien."},
    "safety.file.pagefile@linux": {"en": "Swap file (virtual memory). It is managed with swapoff/swapon.",
                                   "es": "Archivo de intercambio (memoria virtual). Se gestiona con swapoff/swapon."},
    "safety.proc.essential@linux": {
        "en": "Essential system process: ending it can freeze the computer or close your session.",
        "es": "Proceso esencial del sistema: finalizarlo puede colgar el equipo o cerrar tu sesión."},
    "safety.proc.sensitive@linux": {
        "en": "Part of the desktop: panels, sound or network may fail for a few seconds.",
        "es": "Parte del escritorio: los paneles, el sonido o la red pueden fallar unos segundos."},
    "memory.detail_hint@linux": {
        "en": "Select a process to see what it is, whether the system needs it and what happens if it is closed.",
        "es": "Selecciona un proceso para ver qué es, si el sistema lo necesita y qué pasa si se cierra."},
    "memory.kill.system_warning@linux": {
        "en": "\n\nWarning: the list includes system components or services. Read below what each one is "
              "before continuing.",
        "es": "\n\nAtención: la lista incluye componentes o servicios del sistema. Lee abajo qué es cada uno "
              "antes de continuar."},
    "memory.kill.body@linux": {
        "en": "The listed processes will be asked to quit and, if they do not, force-closed. {reasons}",
        "es": "Se pedirá a los procesos indicados que terminen y, si no lo hacen, se forzará su cierre. {reasons}"},
    "disk.legend.vital@linux": {"en": "Vital for the system", "es": "Vital para el sistema"},
    "opt.an.sum.perf@linux": {
        "en": "Committed {commit} · file cache {cache} · kernel {kernel} · {procs} processes, "
              "{threads} threads, {handles} open files",
        "es": "Comprometida {commit} · caché de archivos {cache} · núcleo {kernel} · {procs} procesos, "
              "{threads} hilos, {handles} archivos abiertos"},
    "opt.eff.note@linux": {
        "en": "On Linux: closing asks the program to quit (and its window to close, if «wmctrl» is "
              "installed); without wmctrl Super Limpio cannot tell which programs have a window. Slowing "
              "down lowers the priority and, without administrator rights, lasts until the program is "
              "restarted.",
        "es": "En Linux: cerrar pide al programa que termine (y a su ventana que se cierre, si está "
              "instalado «wmctrl»); sin wmctrl Super Limpio no sabe qué programas tienen ventana. "
              "Ralentizar baja la prioridad y, sin permisos de administrador, dura hasta que el programa "
              "se reinicia."},
    "crit.proc.system@linux": {"en": "The Linux kernel and its threads.", "es": "El núcleo de Linux y sus hilos."},
    "crit.proc.essential@linux": {"en": "Essential system process.", "es": "Proceso esencial del sistema."},
    "crit.proc.audiodg@linux": {"en": "Sound server (PipeWire / PulseAudio).",
                                "es": "Servidor de sonido (PipeWire / PulseAudio)."},
    "crit.proc.explorer@linux": {"en": "Desktop shell: panel, launcher and desktop.",
                                 "es": "Entorno del escritorio: panel, lanzador y escritorio."},
    "crit.proc.shell@linux": {"en": "Part of the desktop.", "es": "Parte del escritorio."},
    "crit.proc.vmmem@linux": {"en": "A virtual machine (QEMU/KVM).", "es": "Una máquina virtual (QEMU/KVM)."},
    "crit.proc.no_access@linux": {
        "en": "It belongs to another user (usually the system): a standard user cannot inspect it.",
        "es": "Es de otro usuario (casi siempre, del sistema): un usuario estándar no puede inspeccionarlo."},
    "crit.proc.normal@linux": {"en": "Ordinary program: the system does not depend on it.",
                               "es": "Programa corriente: el sistema no depende de él."},
    "crit.proc.spooler@linux": {"en": "Print service (CUPS).", "es": "Servicio de impresión (CUPS)."},
    "crit.proc.wlan@linux": {"en": "Wi-Fi authentication.", "es": "Autenticación de la Wi-Fi."},
    "crit.proc.ctfmon@linux": {"en": "Input method: keyboard layouts, accents and other alphabets.",
                               "es": "Método de entrada: idiomas del teclado, acentos y otros alfabetos."},
    "crit.proc.indexer@linux": {"en": "File indexer: makes desktop searches instant.",
                                "es": "Indexador de archivos: hace instantáneas las búsquedas del escritorio."},
    "crit.risk.vital@linux": {
        "en": "If it stops, the system freezes or restarts at once: everything unsaved is lost.",
        "es": "Si se detiene, el sistema se bloquea o se reinicia al momento: se pierde todo lo que no esté "
              "guardado."},
    "crit.risk.audio@linux": {"en": "Without it there is no sound until it starts again.",
                              "es": "Sin él no hay sonido hasta que se vuelva a lanzar."},
    "crit.risk.relaunch@linux": {"en": "It usually starts again on its own; something may fail for a moment.",
                                 "es": "Suele volver a lanzarse solo; algo puede fallar un momento."},
    "crit.risk.store_apps@linux": {"en": "Without it Snap applications stop working or updating.",
                                   "es": "Sin él las aplicaciones Snap dejan de funcionar o de actualizarse."},
    "crit.risk.component@linux": {
        "en": "Closing it is not recommended: a system feature may stop working until the next restart.",
        "es": "No se recomienda cerrarlo: alguna función del sistema puede dejar de funcionar hasta reiniciar."},
    "crit.risk.service@linux": {
        "en": "Stop it with systemctl, not by ending the process: whatever depends on it stops working.",
        "es": "Se detiene con systemctl, no finalizando el proceso: lo que dependa de él deja de funcionar."},
    "crit.risk.network@linux": {"en": "The network connection drops until it starts again.",
                                "es": "La conexión de red se corta hasta que se reinicie."},
    "crit.risk.vm@linux": {
        "en": "Ending it powers the virtual machine or the containers off abruptly. Shut them down from "
              "their own program.",
        "es": "Finalizarlo apaga de golpe la máquina virtual o los contenedores. Apágalos desde su programa."},
    "crit.risk.unknown@linux": {"en": "Run Super Limpio with sudo to find out what it is before closing it.",
                                "es": "Ejecuta Super Limpio con sudo para saber qué es antes de cerrarlo."},
    "crit.path.drive_root@linux": {"en": "The root of a disk.", "es": "La raíz de un disco."},
    "crit.path.windows_temp@linux": {"en": "Temporary files.", "es": "Archivos temporales."},
    "crit.path.windows_logs@linux": {"en": "System logs.", "es": "Registros (logs) del sistema."},
    "crit.path.boot@linux": {"en": "Boot files: the kernel and the boot loader.",
                             "es": "Archivos de arranque: el núcleo y el cargador de arranque."},
    "crit.path.recycle_bin@linux": {"en": "Your Trash.", "es": "Tu Papelera."},
    "crit.path.store_apps@linux": {"en": "Flatpak or Snap applications and their data.",
                                   "es": "Aplicaciones Flatpak o Snap y sus datos."},
    "crit.path.programdata@linux": {"en": "Internal data of the system and its services.",
                                    "es": "Datos internos del sistema y de sus servicios."},
    "crit.path.personal@linux": {"en": "A personal file: the system does not need it.",
                                 "es": "Archivo personal: el sistema no lo necesita."},
    "crit.path.pagefile@linux": {"en": "Swap file (virtual memory).", "es": "Archivo de intercambio (memoria virtual)."},
    "crit.path.dumps@linux": {"en": "Crash reports and memory dumps.", "es": "Informes de fallo y volcados de memoria."},
    "crit.path.user_temp@linux": {"en": "Your programs' caches.", "es": "Cachés de tus programas."},
    "crit.path.appdata_root@linux": {"en": "Where every program keeps your settings and data.",
                                     "es": "Donde todos los programas guardan tu configuración y tus datos."},
    "crit.prisk.vital@linux": {"en": "Without it the system does not start or stops working. Super Limpio "
                                     "will not delete it.",
                               "es": "Sin ello el sistema no arranca o deja de funcionar. Super Limpio no lo borra."},
    "crit.prisk.drive_root@linux": {"en": "Deleting it would erase the whole disk. Super Limpio will not delete it.",
                                    "es": "Borrarla sería borrar el disco entero. Super Limpio no la borra."},
    "crit.prisk.important@linux": {"en": "Deleting it breaks system features or programs. Super Limpio will "
                                         "not delete it.",
                                   "es": "Borrarlo estropea funciones del sistema o programas. Super Limpio no lo borra."},
    "crit.prisk.managed@linux": {"en": "The system manages it; it is resized or removed with swapoff, not by "
                                       "deleting it.",
                                 "es": "Lo gestiona el sistema; se ajusta o se quita con swapoff, no borrándolo."},
    "crit.prisk.regen@linux": {"en": "It is recreated on its own. Empty it from \"Cleanup\", which knows what is safe.",
                               "es": "Se vuelve a crear solo. Vacíalo desde «Limpieza», que sabe qué es seguro."},
    "crit.prisk.program@linux": {"en": "Deleting it by hand leaves the program broken and still registered. "
                                       "Use \"Programs > Uninstall\".",
                                 "es": "Borrarlo a mano deja el programa roto y todavía registrado. Usa «Programas > "
                                       "Desinstalar»."},
    "crit.prisk.app_data@linux": {"en": "The system keeps working, but that program may lose its settings, "
                                        "accounts or saved data.",
                                  "es": "El sistema sigue funcionando, pero ese programa puede perder su configuración, "
                                        "sus cuentas o sus datos guardados."},
    "crit.prisk.other_profile@linux": {"en": "The system keeps working, but that person loses their files.",
                                       "es": "El sistema sigue funcionando, pero esa persona pierde sus archivos."},
    "crit.prisk.recycle_bin@linux": {"en": "Empty it from \"Cleanup\" instead of deleting the folder.",
                                     "es": "Vacíala desde «Limpieza» en vez de borrar la carpeta."},
}
