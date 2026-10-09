"""Internacionalización (español / inglés) sin dependencias externas.

Todas las cadenas visibles de la aplicación viven en el diccionario CATALOG como
``clave -> {"en": ..., "es": ...}``. ``t("clave")`` devuelve la cadena en el idioma
activo (con ``.format(**kw)`` si se pasan argumentos). El idioma se fija al arrancar
(detectado del sistema o leído de la configuración) y, al cambiarlo, la interfaz se
reconstruye entera, por lo que ``t`` solo se evalúa al construir cada pantalla.
"""

from __future__ import annotations

LANGUAGES = [("en", "English"), ("es", "Español")]
_DEFAULT = "en"
_lang = _DEFAULT


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
    try:
        lang, _enc = locale.getdefaultlocale()
        if lang:
            candidates.append(lang)
    except (ValueError, OSError):
        pass
    for cand in candidates:
        if cand and cand.lower().startswith("es"):
            return "es"
    return _DEFAULT


def t(key: str, **kw) -> str:
    entry = CATALOG.get(key)
    if entry is None:
        return key.format(**kw) if kw else key
    text = entry.get(_lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


def plural(n: int, key: str, **kw) -> str:
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
}
