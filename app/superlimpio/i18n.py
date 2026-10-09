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
}
