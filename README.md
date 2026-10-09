# Super Limpio

<img src="launcher/logo.png" alt="Logo de Super Limpio" width="160">

Aplicación de escritorio para **Windows 11** que enseña de un vistazo qué ocupa espacio y memoria en tu equipo, y ayuda a limpiarlo de forma segura. Aspecto inspirado en CCleaner (barra lateral de navegación) y en el Explorador de archivos (árbol de carpetas con el **peso total de cada carpeta**).

Todo es **local**: la app no se conecta a Internet, no instala servicios, no se queda en segundo plano y no modifica el registro.

## Cómo abrirla, paso a paso

Funciona en Windows 10 y 11 de 64 bits. No se instala nada: todo vive dentro de una carpeta que puedes poner en el disco interno, en uno externo o en un USB.

**Para descargarla**, ve a la página [Releases](https://github.com/Vex62/Super-Limpio/releases) del repositorio y baja `SuperLimpio-1.0.0-portable.zip`: es el que lo trae todo.

Si ya tienes un zip, mira **cuál es**:

| Tu zip se llama… | Qué es | Sigue… |
|---|---|---|
| `SuperLimpio-1.0.0-portable.zip` | Todo incluido, listo para usar | [Opción A](#opción-a-zip-portable-lo-más-fácil) |
| `Super-Limpio-main.zip` (botón verde **Code › Download ZIP** de GitHub) o `SuperLimpio-1.0.0.zip` | Solo el código: le falta Python | [Opción B](#opción-b-zip-de-código-el-que-se-baja-de-github) |
| `SuperLimpio-1.0.0-con-python.zip` | Código + Python | Opción B, saltándote el paso 3 |

### Opción A: zip portable (lo más fácil)

1. **Desbloquea el zip.** Clic derecho sobre el zip › **Propiedades** › abajo del todo marca **Desbloquear** › **Aceptar**. (Si no aparece esa casilla, no hace falta.) Así Windows no pone pegas al abrir la app.
2. **Descomprímelo entero.** Clic derecho sobre el zip › **Extraer todo…** › elige dónde › **Extraer**. No abras el `.exe` desde dentro del zip: no funcionaría.
3. **Entra en la carpeta `SuperLimpio`** que ha aparecido. Dentro verás `SuperLimpio.exe` y las carpetas `app` y `runtime`.
4. **Doble clic en `SuperLimpio.exe`.** Se abre la ventana. La primera vez tarda unos segundos (el antivirus revisa los archivos nuevos); después abre en torno a un segundo.

No saques `SuperLimpio.exe` de su carpeta: necesita `app` y `runtime` a su lado. Para tenerlo a mano, clic derecho sobre el `.exe` › **Mostrar más opciones** › **Enviar a** › **Escritorio (crear acceso directo)**. La carpeta entera sí se puede mover o copiar a otro PC tal cual.

### Opción B: zip de código (el que se baja de GitHub)

1. **Desbloquea el zip.** Clic derecho sobre el zip › **Propiedades** › marca **Desbloquear** › **Aceptar**.
2. **Descomprímelo entero.** Clic derecho › **Extraer todo…** y entra en la carpeta que aparece (`Super-Limpio-main` o `SuperLimpio`).
3. **Doble clic en `preparar_entorno.bat`** (solo esta vez; necesita Internet). Pregunta antes de cada paso y se contesta con `S` o `N`:
   - **Python 3.12.10** — contesta `S`. Descarga 4 paquetes oficiales de python.org (14 MB), comprueba su **firma digital** y los *extrae* en `runtime\python` (45 MB). No se instala nada en Windows: ni registro, ni PATH, ni entrada en «Aplicaciones», ni permisos de administrador. No interfiere con otro Python que ya tengas.
   - **VS Code portable** (150 MB) — contesta `N`, salvo que vayas a modificar el código.
4. **Doble clic en `SuperLimpio.bat`.** Se abre la ventana y la consola negra se cierra sola. A partir de ahora solo necesitas este paso.

En este zip no viene `SuperLimpio.exe`, porque los programas compilados no se guardan en el repositorio. No hace falta: el `.bat` abre exactamente la misma aplicación. Si quieres el `.exe`, mira [Compilar `SuperLimpio.exe`](#compilar-superlimpioexe).

### Si algo no sale como esperas

| Qué ves | Por qué | Qué hacer |
|---|---|---|
| Ventana azul «Windows protegió su PC» | SmartScreen avisa de cualquier programa nuevo bajado de Internet que no esté firmado | **Más información** › **Ejecutar de todas formas**. No vuelve a salir si desbloqueaste el zip (paso 1) |
| «Falta la carpeta app» o «Falta el Python portable» | Has abierto el `.exe` desde dentro del zip, o lo has movido fuera de su carpeta | Descomprime el zip entero y abre el `.exe` desde la carpeta `SuperLimpio` |
| «No se ha encontrado el Python portable» al abrir `SuperLimpio.bat` | Falta el paso 3 de la opción B | Ejecuta `preparar_entorno.bat` y contesta `S` a Python |
| «Error de descarga» en `preparar_entorno.bat` | No hay conexión a Internet | Conéctate y vuelve a ejecutarlo, o pide el zip portable |

### Una vez abierta

- La app arranca como **usuario normal** y con eso basta para casi todo. Para limpiar carpetas del sistema o ver procesos de otros usuarios, pulsa *Reiniciar como administrador…* (abajo a la izquierda): Windows mostrará su aviso de permisos (UAC).
- Nada se borra sin que lo confirmes antes: cada acción enseña exactamente qué va a tocar.
- Para quitar Super Limpio del equipo, borra su carpeta. No deja nada más.

## Para quien modifica el código

### Trabajar con VS Code portable

1. Abre `tools\VSCode\Code.exe` (o el VS Code portable que ya tengas en el disco).
2. *Archivo › Abrir área de trabajo desde archivo…* › `SuperLimpio.code-workspace`.

El área de trabajo ya apunta al Python portable. Dentro de VS Code:

| Acción | Cómo |
|---|---|
| Ejecutar la app | **Ctrl+Shift+B** |
| Depurar | **F5** (necesita la extensión de Python) |
| Tests | *Terminal › Ejecutar tarea… › Tests* |
| Generar el zip | *Terminal › Ejecutar tarea… › Crear zip* |
| Compilar el `.exe` | *Terminal › Ejecutar tarea… › Compilar SuperLimpio.exe* |

Sin VS Code, desde una consola en la carpeta del proyecto:

```bat
runtime\python\python.exe -B -m unittest discover -s tests -v
runtime\python\python.exe -B tools\crear_zip.py
runtime\python\python.exe -B tools\crear_zip.py --con-python
runtime\python\python.exe -B tools\crear_exe.py
runtime\python\python.exe -B tools\crear_zip.py --portable
```

### Generar los zips

| Comando | Resultado | Para qué |
|---|---|---|
| `tools\crear_zip.py --portable` | `dist\SuperLimpio-1.0.0-portable.zip` (~21 MB) | **Descomprimir y doble clic en `SuperLimpio.exe`**, sin Internet. Lleva el `.exe`, la app, el Python portable y el código ya compilado. Necesita haber ejecutado antes `tools\crear_exe.py` |
| `tools\crear_zip.py` | `dist\SuperLimpio-1.0.0.zip` (~100 KB, solo texto) | Compartir o guardar el código. Quien lo reciba ejecuta `preparar_entorno.bat` |
| `tools\crear_zip.py --con-python` | `dist\SuperLimpio-1.0.0-con-python.zip` (~17 MB) | Código + Python portable, para seguir desarrollando sin Internet |

### Compilar `SuperLimpio.exe`

```bat
runtime\python\python.exe -B tools\crear_exe.py
```

Deja `SuperLimpio.exe` (unos 170 KB, casi todo es el icono) en la raíz del proyecto. Necesita el compilador de C de Visual Studio o de *Build Tools for Visual Studio* (carga «Desarrollo para el escritorio con C++»); no hace falta el SDK de Windows.

El `.exe` es un **lanzador**: unas 150 líneas de C legible en `launcher\launcher.c` que cargan `runtime\python\python312.dll` y le piden que ejecute `app\main.py`, igual que haría `pythonw.exe`. La aplicación sigue siendo el mismo código Python, así que va igual de rápido y consume lo mismo. El icono sale de `launcher\logo.png` (un PNG cuadrado con fondo transparente): el mismo script lo reduce a todos los tamaños y deja también en `app\superlimpio\ui\assets` el icono y el logo que usa la ventana, para que se vean igual al abrirla con el `.bat`. La compilación es reproducible: el mismo código fuente da siempre el mismo `.exe`, byte a byte (el script imprime su SHA-256).

## Qué hace cada sección

| Sección | Qué muestra | Qué puede hacer |
|---|---|---|
| **Resumen** | Ocupación de cada unidad, RAM, papelera y los 5 programas que más memoria usan | Atajos al resto |
| **Analizador de disco** | Árbol tipo Explorador con el **peso total de cada carpeta**, barra de uso y %; pestañas de *archivos más grandes* y *por tipo*. Filas coloreadas a partir de 100 MB / 1 GB / 10 GB y columna «Qué es» que explica carpetas típicas (WinSxS, node_modules, hiberfil.sys…) | Abrir en el Explorador, analizar una subcarpeta, **comprimir** lo seleccionado (7z o ZIP, con contraseña opcional), enviar a la Papelera, borrar definitivamente |
| **Programas** | Programas instalados con tamaño **declarado** y **real** medido en disco | Desinstalar con el desinstalador **oficial** del programa |
| **Memoria y procesos** | Memoria privada, RAM física y CPU, agrupado por programa (p. ej. todos los `chrome.exe` juntos) | Finalizar procesos (los esenciales de Windows están bloqueados) |
| **Optimizar** | *Análisis exhaustivo*: observa todos los procesos durante 10–60 s y señala qué programas acaparan RAM, cuáles no dejan de crecer (posible fuga), cuáles usan CPU sin tener ventana y cuánto falta para agotar la memoria. *Modo eficiente*: eliges el programa o juego que vas a usar y propone qué hacer con cada uno de los demás | Ralentizar (modo de eficiencia de Windows, reversible), cerrar, dar prioridad a tu programa; **Deshacer** y **Reabrir cerrados** al terminar |
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
- **El Modo eficiente propone, no decide.** Se basa en lo que hacen el modo de eficiencia de Windows 11, Process Lasso, Microsoft PC Manager o Razer Cortex, pero sin automatismos: enseña la lista exacta (qué se ralentiza, a qué se le pide que se cierre, qué se finaliza) y espera tu confirmación. La acción por defecto es **ralentizar**, que no cierra nada y se deshace con un botón. A los programas con ventana se les *pide* que se cierren, como si pulsaras su X, así que pueden preguntarte si guardas; forzar el cierre es una casilla aparte y sube el riesgo a *Alto*. Nunca aparecen en la lista Windows y sus servicios, el antivirus, los anti-trampas, la propia app ni nada relacionado con el programa que has elegido (su carpeta, sus procesos hijos y quien lo lanzó). Tampoco se detienen servicios ni se asigna prioridad «Alta» o «Tiempo real». Antes de actuar se comprueba que cada proceso sigue siendo el mismo que se analizó (Windows reutiliza los PID). Los cambios duran lo que la sesión: si cierras la app con el modo activo, pregunta si deshacerlo.
- **Comprimir no toca los originales.** El compresor es propio (biblioteca estándar de Python, sin programas externos) y genera archivos estándar que abren 7-Zip y WinRAR: **7z** con LZMA2 en bloque sólido (los mejores índices; varios hilos si la memoria del equipo lo permite) o **ZIP** con Deflate (lo abre cualquier sistema). La contraseña es opcional y cifra con **AES-256** usando la criptografía del propio Windows; en 7z se cifran también los nombres de los archivos. La contraseña no se guarda ni se registra, y si se olvida no hay forma de recuperar el contenido. En ZIP solo se admiten contraseñas ASCII, porque cada programa interpreta de forma distinta las tildes y la «ñ». Se escribe en un archivo `.part` que solo recibe su nombre al terminar bien: si se detiene o falla, no queda nada a medias. Al acabar se **relee y comprueba** el archivo entero. No se siguen enlaces ni se descargan archivos «solo en la nube»: se omiten y se avisa. Enviar los originales a la Papelera es una casilla aparte, exige que la comprobación haya salido bien y que no se haya omitido nada, y pide su propia confirmación.
- **La limpieza solo actúa sobre una lista cerrada de ubicaciones conocidas**, respeta los archivos en uso y en `%TEMP%` conserva lo modificado en las últimas 24 h.
- **No sigue enlaces simbólicos ni *junctions*** al analizar o borrar (evita contar doble o salirse de la carpeta). Los archivos de OneDrive «solo en la nube» se cuentan aparte porque no ocupan disco.
- **Administrador solo cuando hace falta**: «Reiniciar como administrador» pide confirmación y además Windows muestra su aviso UAC. Las herramientas que necesitan elevación (DISM, powercfg) se lanzan cada una con su propio aviso UAC y en una consola visible.

## Antivirus y falsos positivos

Los falsos positivos suelen venir de ejecutables empaquetados (PyInstaller, etc.), código ofuscado o comportamientos típicos de malware. Este proyecto los evita a propósito:

- **`SuperLimpio.exe` no es un empaquetado.** No lleva Python ni la app comprimidos dentro, no extrae nada a carpetas temporales y no usa UPX ni nada parecido, que es justo lo que hace saltar a los antivirus con PyInstaller y similares. Solo carga la DLL oficial de Python, **firmada** por la Python Software Foundation, que está a la vista en `runtime\python`. Importa 13 funciones de Windows, lleva icono, información de versión y manifiesto como cualquier programa normal, y su código fuente está en `launcher\launcher.c`.
- La aplicación sigue siendo código fuente legible (`.py`) en la carpeta `app`. Quien prefiera no usar el `.exe` puede abrirla con `SuperLimpio.bat`, que usa `pythonw.exe`.
- Sin ofuscación, sin Base64, sin PowerShell codificado, sin `-ExecutionPolicy Bypass`, sin ventanas ocultas.
- Sin persistencia (no crea tareas programadas, servicios ni entradas de inicio) y sin escribir en el registro.
- Sin red en tiempo de ejecución. Las únicas descargas están en `preparar_entorno.bat`, se piden con permiso, vienen de python.org / Microsoft y se **verifica su firma digital** antes de usarlas. No se ejecuta ningún instalador: los paquetes solo se extraen.
- Para medir procesos pide a Windows **el permiso mínimo** (`PROCESS_QUERY_LIMITED_INFORMATION`). El Modo eficiente pide además, solo sobre los procesos que has confirmado, los permisos para cambiar su prioridad, recortar su RAM o finalizarlos. Nunca solicita acceso a la memoria de otros procesos, que es justo lo que los antivirus vigilan (por ejemplo sobre `lsass.exe`).
- El zip solo lleva texto, los binarios oficiales de Python sin tocar y, en el portable, el lanzador y los `.pyc` (el mismo código de `app` y de la biblioteca de Python ya compilado por el propio Python).

Comprobado con Microsoft Defender (protección en tiempo real activa): ni `SuperLimpio.exe`, ni el zip portable, ni la carpeta descomprimida dan ninguna detección.

Lo que no se puede prometer es que **ningún** antivirus del mercado lo marque nunca: `SuperLimpio.exe` **no está firmado digitalmente**, porque eso requiere un certificado de firma de código de pago a nombre de una persona o empresa. Sin firma, SmartScreen avisa la primera vez si el zip viene de Internet, y algún motor que desconfía de todo ejecutable nuevo y sin firmar podría dar un aviso genérico. Si llegas a distribuirlo mucho, firmarlo es lo único que quita ese aviso de raíz.

Lo que **sí** puede preguntar Windows, y es lo esperado:

| Aviso | Cuándo | Qué hacer |
|---|---|---|
| SmartScreen «Windows protegió su PC» | Primer arranque de un `.exe` o `.bat` venido de Internet | *Más información › Ejecutar de todas formas*, o desbloquear el zip antes de descomprimir |
| UAC «¿Quieres permitir que esta aplicación haga cambios?» | Al reiniciar como administrador o lanzar DISM/powercfg | Con `SuperLimpio.exe` el aviso es amarillo y dice *Editor desconocido* (no está firmado): comprueba que la ruta es la de tu carpeta. Con `SuperLimpio.bat` el editor es *Python Software Foundation*; en DISM/powercfg, *Microsoft Windows* |
| «Acceso controlado a carpetas» de Defender | Si lo tienes activado y borras dentro de Documentos, Imágenes… | Permitir `SuperLimpio.exe` (o `pythonw.exe` si usas el `.bat`) en *Seguridad de Windows › Protección contra ransomware* |

Si algún antivirus marcase un archivo, no lo excluyas a ciegas: súbelo a [VirusTotal](https://www.virustotal.com) y revisa qué motor lo detecta. Todo el código es texto legible.

## Estructura

```
SuperLimpio/
├─ SuperLimpio.exe              abre la aplicación (lo genera tools/crear_exe.py; no va a git)
├─ SuperLimpio.bat              abre la aplicación con pythonw.exe, sin el .exe
├─ preparar_entorno.bat         descarga verificada de Python / VS Code portables
├─ SuperLimpio.code-workspace   + .vscode/ (intérprete portable, tareas, depuración)
├─ paleta.txt                   colores de la marca; la interfaz los toma de app/superlimpio/ui/theme.py
├─ app/
│  ├─ main.py
│  └─ superlimpio/
│     ├─ scanner.py      peso recursivo de carpetas (lectura en paralelo)
│     ├─ programs.py     programas instalados y desinstalación
│     ├─ processes.py    memoria/CPU por proceso
│     ├─ optimizer.py    análisis exhaustivo y Modo eficiente (catálogo, propuesta, deshacer)
│     ├─ startup.py      programas de inicio (solo lectura)
│     ├─ cleaner.py      categorías de limpieza (lista blanca)
│     ├─ devdeps.py      librerías de desarrollo regenerables
│     ├─ systools.py     comandos del sistema con confirmación
│     ├─ safety.py       rutas/procesos protegidos, riesgos, registro
│     ├─ fileops.py      Papelera y borrado con comprobaciones
│     ├─ archiver.py     compresor 7z / ZIP (LZMA2 sólido, Deflate, AES-256, verificación)
│     ├─ aes.py          AES-256 con la criptografía de Windows (CNG)
│     ├─ winapi.py       llamadas a la API de Windows (ctypes)
│     └─ ui/             interfaz (tkinter, sin dependencias externas)
│        └─ assets/      icono y logo de la ventana (los genera tools/crear_exe.py)
├─ launcher/
│  ├─ launcher.c            código del lanzador SuperLimpio.exe
│  ├─ SuperLimpio.manifest  manifiesto de Windows (arranca siempre sin elevar)
│  └─ logo.png              logo; de aquí salen el icono del .exe y el de la ventana
├─ tests/                tests de la lógica
├─ tools/crear_exe.py    compila SuperLimpio.exe
├─ tools/crear_zip.py    genera el zip en dist/
├─ runtime/              Python portable y caché de código compilado (no van a git)
└─ tools/VSCode/         VS Code portable, opcional (no va a git)
```

Solo usa la biblioteca estándar de Python: no hay que instalar paquetes con pip.

`runtime\_pycache` guarda el código ya compilado para que la ventana abra antes cuando se usa `SuperLimpio.bat`; se puede borrar cuando quieras y se regenera sola. Con `SuperLimpio.exe` el código compilado va en las carpetas `__pycache__` de siempre, junto a cada archivo: el zip portable ya las trae hechas y siguen valiendo aunque muevas la carpeta. `build\` guarda los archivos intermedios de compilar el `.exe`. `logs\` guarda el registro de acciones.

## Limitaciones conocidas

- Las apps de **Microsoft Store** no siempre aparecen en el registro clásico: el botón «Apps de Microsoft Store…» abre Configuración para gestionarlas.
- Sin permisos de administrador algunas carpetas del sistema no se pueden leer; el análisis indica cuántas y la app ofrece reiniciarse elevada.
- Los archivos con enlaces duros (p. ej. dentro de `WinSxS`) pueden contarse más de una vez, igual que en el Explorador. Para WinSxS usa *Herramientas › Analizar almacén de componentes*, que da la cifra real.
