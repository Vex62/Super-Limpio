# Super Limpio

Aplicación de escritorio para **Windows 11** que enseña de un vistazo qué ocupa espacio y memoria en tu equipo, y ayuda a limpiarlo de forma segura. Aspecto inspirado en CCleaner (barra lateral oscura) y en el Explorador de archivos (árbol de carpetas con el **peso total de cada carpeta**).

Todo es **local**: la app no se conecta a Internet, no instala servicios, no se queda en segundo plano y no modifica el registro.

## Ponerla en marcha

Solo hay dos archivos `.bat`:

| Archivo | Cuándo | Qué hace |
|---|---|---|
| `preparar_entorno.bat` | **Una vez** | Trae el Python portable a `runtime\python` (y, si quieres, VS Code portable a `tools\VSCode`) |
| `SuperLimpio.bat` | **Siempre** | Abre la aplicación |

### 1. Crear el entorno (una sola vez)

1. Copia la carpeta del proyecto al disco externo, por ejemplo `E:\SuperLimpio`.
   Si la bajaste como zip de Internet: clic derecho en el zip › **Propiedades** › marca **Desbloquear** › Aceptar, y después descomprime. Así Windows no pregunta en cada arranque.
2. Doble clic en **`preparar_entorno.bat`**. Pregunta antes de cada paso (`S`/`N`):
   - **Python 3.12.10** — descarga 4 paquetes oficiales de python.org (14 MB), comprueba su **firma digital** y los *extrae* en `runtime\python` (45 MB). No se instala nada en Windows: ni registro, ni PATH, ni entrada en «Aplicaciones», ni permisos de administrador. No interfiere con otro Python que ya tengas.
   - **VS Code portable** (opcional, 150 MB) — solo hace falta si vas a modificar el código.
3. Listo. La carpeta `runtime\_descargas` ya se puede borrar.

A partir de aquí todo vive en el disco externo y funciona en cualquier PC con Windows 10/11 de 64 bits, sin volver a descargar nada.

> Si ya recibiste el zip `SuperLimpio-x.y.z-con-python.zip`, sáltate este apartado: el Python portable va dentro.

### 2. Usarla

Doble clic en **`SuperLimpio.bat`**. Aparece la ventana en un par de segundos y la consola se cierra sola.

- La app arranca como **usuario normal**. Para limpiar carpetas del sistema o ver procesos de otros usuarios, pulsa *Reiniciar como administrador…* (abajo a la izquierda): Windows mostrará su aviso UAC.
- Si Windows muestra «Windows protegió su PC» la primera vez, es SmartScreen avisando de un `.bat` bajado de Internet: *Más información* › *Ejecutar de todas formas* (o desbloquea el zip como se indica arriba).

### 3. Trabajar en el código con VS Code portable

1. Abre `tools\VSCode\Code.exe` (o el VS Code portable que ya tengas en el disco).
2. *Archivo › Abrir área de trabajo desde archivo…* › `SuperLimpio.code-workspace`.

El área de trabajo ya apunta al Python portable. Dentro de VS Code:

| Acción | Cómo |
|---|---|
| Ejecutar la app | **Ctrl+Shift+B** |
| Depurar | **F5** (necesita la extensión de Python) |
| Tests | *Terminal › Ejecutar tarea… › Tests* |
| Generar el zip | *Terminal › Ejecutar tarea… › Crear zip* |

Sin VS Code, desde una consola en la carpeta del proyecto:

```bat
runtime\python\python.exe -B -m unittest discover -s tests -v
runtime\python\python.exe -B tools\crear_zip.py
runtime\python\python.exe -B tools\crear_zip.py --con-python
```

### 4. Generar el zip para llevarlo a otro sitio

| Comando | Resultado | Para qué |
|---|---|---|
| `tools\crear_zip.py` | `dist\SuperLimpio-1.0.0.zip` (~100 KB, solo texto) | Compartir o guardar el código. Quien lo reciba ejecuta `preparar_entorno.bat` |
| `tools\crear_zip.py --con-python` | `dist\SuperLimpio-1.0.0-con-python.zip` (~17 MB) | Descomprimir y usar, sin Internet |

## Qué hace cada sección

| Sección | Qué muestra | Qué puede hacer |
|---|---|---|
| **Resumen** | Ocupación de cada unidad, RAM, papelera y los 5 programas que más memoria usan | Atajos al resto |
| **Analizador de disco** | Árbol tipo Explorador con el **peso total de cada carpeta**, barra de uso y %; pestañas de *archivos más grandes* y *por tipo*. Filas coloreadas a partir de 100 MB / 1 GB / 10 GB y columna «Qué es» que explica carpetas típicas (WinSxS, node_modules, hiberfil.sys…) | Abrir en el Explorador, analizar una subcarpeta, enviar a la Papelera, borrar definitivamente |
| **Programas** | Programas instalados con tamaño **declarado** y **real** medido en disco | Desinstalar con el desinstalador **oficial** del programa |
| **Memoria y procesos** | Memoria privada, RAM física y CPU, agrupado por programa (p. ej. todos los `chrome.exe` juntos) | Finalizar procesos (los esenciales de Windows están bloqueados) |
| **Inicio de Windows** | Programas que arrancan solos, su estado y si apuntan a archivos ya borrados | Abre el Administrador de tareas para desactivarlos (vía oficial y reversible) |
| **Limpieza** | Temporales, informes de error, cachés de navegadores, de desarrollo (pip, npm, Gradle, Cargo, NuGet), de shaders, Windows Update, papelera… | Analiza primero sin tocar nada; luego limpia lo marcado |
| **Librerías de desarrollo** | `node_modules`, `.venv`, `__pycache__`, `target`, `bin/obj` de .NET, `.next`, `.gradle`… dentro de tus proyectos | Marcar (incluso «más de 6 meses sin tocar») y enviar a la Papelera o borrar |
| **Herramientas del sistema** | Comandos oficiales: Almacenamiento, Liberador de espacio, punto de restauración, análisis y limpieza de WinSxS (DISM), desactivar hibernación | Ejecutar, viendo antes el **comando literal** |
| **Registro de acciones** | Todo lo que la app ha hecho, con fecha y resultado (`logs\acciones.log`) | — |

## Seguridad

- **Nada se ejecuta sin tu permiso.** Cada acción abre una ventana que muestra exactamente qué rutas o qué comando se van a usar. El botón por defecto es *Cancelar*.
- **Niveles de riesgo**: *Medio* → confirmación simple. *Alto* → además hay que marcar «He revisado…». *Crítico* (borrado definitivo, DISM, powercfg) → además hay que **escribir CONFIRMAR**.
- **La Papelera es la opción por defecto**; el borrado definitivo es una acción aparte.
- **Rutas protegidas**: la app se niega a borrar la carpeta de Windows, *Archivos de programa*, `ProgramData\Microsoft`, la raíz de las unidades, `$Recycle.Bin` y `System Volume Information` de cualquier unidad, tu carpeta de usuario y sus carpetas principales (Escritorio, Documentos…), `pagefile.sys`/`hiberfil.sys` y la propia carpeta de la app. Para quitar programas usa siempre *Desinstalar*.
- **Procesos protegidos**: `csrss`, `lsass`, `winlogon`, `services`, `svchost`, `dwm`, antivirus de Defender… no se pueden finalizar.
- **La limpieza solo actúa sobre una lista cerrada de ubicaciones conocidas**, respeta los archivos en uso y en `%TEMP%` conserva lo modificado en las últimas 24 h.
- **No sigue enlaces simbólicos ni *junctions*** al analizar o borrar (evita contar doble o salirse de la carpeta). Los archivos de OneDrive «solo en la nube» se cuentan aparte porque no ocupan disco.
- **Administrador solo cuando hace falta**: «Reiniciar como administrador» pide confirmación y además Windows muestra su aviso UAC. Las herramientas que necesitan elevación (DISM, powercfg) se lanzan cada una con su propio aviso UAC y en una consola visible.

## Antivirus y falsos positivos

Los falsos positivos suelen venir de ejecutables empaquetados (PyInstaller, etc.), código ofuscado o comportamientos típicos de malware. Este proyecto los evita a propósito:

- **No hay ningún `.exe` propio.** Se ejecuta código fuente legible (`.py`) con `pythonw.exe` **firmado** por la Python Software Foundation. Es lo que Windows muestra en el aviso UAC.
- Sin ofuscación, sin Base64, sin PowerShell codificado, sin `-ExecutionPolicy Bypass`, sin ventanas ocultas.
- Sin persistencia (no crea tareas programadas, servicios ni entradas de inicio) y sin escribir en el registro.
- Sin red en tiempo de ejecución. Las únicas descargas están en `preparar_entorno.bat`, se piden con permiso, vienen de python.org / Microsoft y se **verifica su firma digital** antes de usarlas. No se ejecuta ningún instalador: los paquetes solo se extraen.
- Para medir procesos pide a Windows **el permiso mínimo** (`PROCESS_QUERY_LIMITED_INFORMATION`). Nunca solicita acceso a la memoria de otros procesos, que es justo lo que los antivirus vigilan (por ejemplo sobre `lsass.exe`).
- El zip solo lleva texto y, opcionalmente, los binarios oficiales de Python sin tocar.

Lo que **sí** puede preguntar Windows, y es lo esperado:

| Aviso | Cuándo | Qué hacer |
|---|---|---|
| SmartScreen «Windows protegió su PC» | Primer arranque de un `.bat` venido de Internet | *Más información › Ejecutar de todas formas*, o desbloquear el zip antes de descomprimir |
| UAC «¿Quieres permitir que esta aplicación haga cambios?» | Al reiniciar como administrador o lanzar DISM/powercfg | Comprueba que el editor es *Python Software Foundation* o *Microsoft Windows* |
| «Acceso controlado a carpetas» de Defender | Si lo tienes activado y borras dentro de Documentos, Imágenes… | Permitir `pythonw.exe` en *Seguridad de Windows › Protección contra ransomware* |

Si algún antivirus marcase un archivo, no lo excluyas a ciegas: súbelo a [VirusTotal](https://www.virustotal.com) y revisa qué motor lo detecta. Todo el código es texto legible.

## Estructura

```
SuperLimpio/
├─ SuperLimpio.bat              abre la aplicación
├─ preparar_entorno.bat         descarga verificada de Python / VS Code portables
├─ SuperLimpio.code-workspace   + .vscode/ (intérprete portable, tareas, depuración)
├─ app/
│  ├─ main.py
│  └─ superlimpio/
│     ├─ scanner.py      peso recursivo de carpetas (lectura en paralelo)
│     ├─ programs.py     programas instalados y desinstalación
│     ├─ processes.py    memoria/CPU por proceso
│     ├─ startup.py      programas de inicio (solo lectura)
│     ├─ cleaner.py      categorías de limpieza (lista blanca)
│     ├─ devdeps.py      librerías de desarrollo regenerables
│     ├─ systools.py     comandos del sistema con confirmación
│     ├─ safety.py       rutas/procesos protegidos, riesgos, registro
│     ├─ fileops.py      Papelera y borrado con comprobaciones
│     ├─ winapi.py       llamadas a la API de Windows (ctypes)
│     └─ ui/             interfaz (tkinter, sin dependencias externas)
├─ tests/                tests de la lógica
├─ tools/crear_zip.py    genera el zip en dist/
├─ runtime/              Python portable y caché de código compilado (no van a git)
└─ tools/VSCode/         VS Code portable, opcional (no va a git)
```

Solo usa la biblioteca estándar de Python: no hay que instalar paquetes con pip.

`runtime\_pycache` guarda el código ya compilado para que la ventana abra antes; se puede borrar cuando quieras y se regenera sola. `logs\` guarda el registro de acciones.

## Limitaciones conocidas

- Las apps de **Microsoft Store** no siempre aparecen en el registro clásico: el botón «Apps de Microsoft Store…» abre Configuración para gestionarlas.
- Sin permisos de administrador algunas carpetas del sistema no se pueden leer; el análisis indica cuántas y la app ofrece reiniciarse elevada.
- Los archivos con enlaces duros (p. ej. dentro de `WinSxS`) pueden contarse más de una vez, igual que en el Explorador. Para WinSxS usa *Herramientas › Analizar almacén de componentes*, que da la cifra real.
