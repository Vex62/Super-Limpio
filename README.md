# Super Limpio

<img src="launcher/logo.png" alt="Logo de Super Limpio" width="160">

Aplicación de escritorio para **Windows 10/11** y **Linux** que enseña de un vistazo qué ocupa espacio y memoria en tu equipo, y ayuda a limpiarlo de forma segura. Aspecto inspirado en CCleaner (barra lateral de navegación) y en el Explorador de archivos (árbol de carpetas con el **peso total de cada carpeta**).

Todo es **local**: la app no se conecta a Internet, no instala servicios, no se queda en segundo plano y no modifica el registro.

**¿Primera vez?** Lee [Antes de ejecutar](ANTES_DE_EJECUTAR.md) ([Before run](BEFORE_RUN.md), in English): qué necesita tu equipo en Windows y en Linux y cómo conseguirlo.

## Descargas

Cada versión se publica dos veces en [Releases](https://github.com/Vex62/Super-Limpio/releases), una por sistema. La actual es la **1.4.2**:

| Sistema | Release | Archivo | Cómo se abre |
|---|---|---|---|
| Windows 10 y 11 (64 bits) | [Super Limpio 1.4.2 para Windows](https://github.com/Vex62/Super-Limpio/releases/tag/v1.4.2-windows) | `SuperLimpio-1.4.2-protegido.zip` (unos 22 MB, con Python incluido) | [Windows, opción A](#opción-a-zip-del-release-lo-más-fácil) |
| Linux | [Super Limpio 1.4.2 para Linux](https://github.com/Vex62/Super-Limpio/releases/tag/v1.4.2-linux) | `SuperLimpio-1.4.2-linux.tar.gz` (unos 220 KB, usa el Python del sistema) | [Linux](#linux) |

Los dos paquetes van **firmados**: llevan un manifiesto con la huella de cada archivo y la aplicación lo comprueba al arrancar. Si alguien ha modificado algo, se niega a continuar.

## Cómo abrirla en Windows, paso a paso

Funciona en Windows 10 y 11 de 64 bits. No se instala nada: todo vive dentro de una carpeta que puedes poner en el disco interno, en uno externo o en un USB.

Si ya tienes un zip, mira **cuál es**:

| Tu zip se llama… | Qué es | Sigue… |
|---|---|---|
| `SuperLimpio-<versión>-protegido.zip` (el de Releases) o `SuperLimpio-<versión>-portable.zip` | Todo incluido, listo para usar | [Opción A](#opción-a-zip-del-release-lo-más-fácil) |
| `Super-Limpio-main.zip` (botón verde **Code › Download ZIP** de GitHub) o `SuperLimpio-<versión>.zip` | Solo el código: le falta Python | [Opción B](#opción-b-zip-de-código-el-que-se-baja-de-github) |
| `SuperLimpio-<versión>-con-python.zip` | Código + Python | Opción B, saltándote el paso 3 |

### Opción A: zip del release (lo más fácil)

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

- La app trabaja siempre como **usuario normal**; no hay «reiniciar como administrador». Cuando una operación concreta lo necesita (vaciar la carpeta temporal de Windows, borrar algo que tu usuario no puede), te lo ofrece al momento: un **auxiliar aparte** hace solo esa operación, tras otra confirmación y el aviso de permisos de Windows (UAC).
- Nada se borra sin que lo confirmes antes: cada acción enseña exactamente qué va a tocar.
- Para quitar Super Limpio del equipo, borra su carpeta y, si quieres, `%LOCALAPPDATA%\SuperLimpio` (el registro de acciones). No instala nada más.

## Linux

Hay un paquete aparte, `SuperLimpio-<versión>-linux.tar.gz`, con el mismo código y un lanzador para Linux. Se baja del release «Super Limpio <versión> para Linux». No lleva Python: usa el del sistema (**3.11 o posterior**, con tkinter). En Ubuntu 22.04, cuyo Python es el 3.10, hay que instalar uno más nuevo (por ejemplo `python3.11` y `python3.11-tk`); el lanzador lo encuentra solo.

```
tar -xzf SuperLimpio-<versión>-linux.tar.gz
cd SuperLimpio
./superlimpio.sh                # abre la aplicación
./superlimpio.sh --instalar     # opcional: la añade al menú de aplicaciones de tu usuario
```

Si falta Python o tkinter, el lanzador dice qué paquete instalar (en Debian/Ubuntu, `sudo apt install python3-tk`). No instala nada en el sistema ni necesita permisos de administrador. Para quitarla: `./superlimpio.sh --quitar` y borra la carpeta. El lanzador también funciona a través de un enlace simbólico (por ejemplo, `ln -s "$PWD/superlimpio.sh" ~/.local/bin/superlimpio`).

Opcional: `wmctrl`, para que el Modo eficiente sepa qué programas tienen una ventana abierta. Solo ve las ventanas de X11 y XWayland.

Qué cambia respecto a Windows:

| Sección | En Linux |
|---|---|
| **Analizador de disco**, **Librerías de desarrollo**, compresor 7z/ZIP | Igual. La contraseña de los archivos usa OpenSSL |
| **Papelera** | La del escritorio (especificación de FreeDesktop): lo enviado se recupera desde el gestor de archivos |
| **Programas** | Aplicaciones del menú con el paquete que las trae (deb, rpm, pacman), más Flatpak y Snap. Desinstalar abre una terminal con el comando del gestor de paquetes, que pide confirmación él mismo |
| **Memoria y procesos**, **Optimizar** | Se lee de `/proc`. «Finalizar» pide primero al programa que termine y solo después lo fuerza. Los hilos del núcleo no se listan |
| **Modo eficiente** | Ralentizar baja la prioridad, pero Linux solo deja devolverla a un administrador, así que no se propone por defecto. Para saber qué programas tienen ventana hace falta `wmctrl` |
| **Inicio** | Carpetas `autostart` y servicios de usuario de systemd |
| **Limpieza** | Miniaturas, informes de fallo, paquetes descargados, cachés de navegadores y de desarrollo, shaders y Papelera. No toca `/tmp` |
| **Herramientas** | Las de la distribución que estén instaladas: journalctl, apt/dnf/pacman, Flatpak, fstrim. Se abren en una terminal, donde `sudo` pide la contraseña |
| **Terminal** | La que tengas elegida en el escritorio (`xdg-terminal-exec` o `x-terminal-emulator`); si no se sabe, la primera que haya de GNOME Terminal, Ptyxis, Konsole, Xfce, MATE, Tilix, Terminator, LXTerminal, QTerminal, Alacritty, kitty, foot, WezTerm o xterm |
| **Nombres de archivo** | Los que no son UTF-8 válido (discos antiguos, copias de otros sistemas) se analizan, se envían a la Papelera y se comprimen igual; dentro de un 7z o ZIP sus letras ilegibles se guardan con el signo de sustitución de Unicode |

La aplicación nunca corre como root: una interfaz gráfica con privilegios no es buena idea. Lo que los necesita se hace en una terminal con `sudo`, a la vista.

**Qué está probado.** En cada cambio, GitHub Actions ejecuta en Windows y en Ubuntu 22.04 y 24.04, con Python 3.11 y 3.13, las pruebas de la lógica y las de seguridad, llamadas reales al sistema (procesos, Papelera, prioridades) y un recorrido por toda la interfaz (en Linux bajo un servidor gráfico virtual, guardando capturas de cada sección), y pasa ruff, bandit, mypy para las dos plataformas y pip-audit (`.github/workflows/linux.yml`). El paquete publicado se descarga y se prueba tal cual, firma incluida. Fedora, Arch y openSUSE están contemplados en el código (rpm, pacman, dnf, zypper y sus rutas) pero **no se han probado**, ni tampoco un escritorio real con GNOME o KDE.

Lo que depende del sistema operativo está aislado en `app/superlimpio/plat/`: `windows.py` y `linux.py` hacen las llamadas al sistema, y `windows_know.py` y `linux_know.py` saben qué procesos y carpetas son vitales en cada uno.

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
runtime\python\python.exe -I -B -m unittest discover -s tests -v
runtime\python\python.exe -B tools\crear_zip.py
runtime\python\python.exe -B tools\crear_zip.py --con-python
runtime\python\python.exe -B tools\crear_exe.py
runtime\python\python.exe -B tools\crear_zip.py --portable
runtime\python\python.exe -B tools\crear_zip.py --protegido
runtime\python\python.exe -B tools\crear_linux.py
```

En Linux es lo mismo con `python3` y barras normales (`python3 -I -B -m unittest discover -s tests -v`). `tests/test_core.py` prueba la lógica y `tests/test_seguridad.py` lo que exige la ficha de seguridad para el código que borra, limpia o se eleva (rutas con `..`, enlaces y junctions, nombres reservados, rutas largas, archivos bloqueados, cancelación a mitad de lote, órdenes al auxiliar…). `tests/smoke_gui.py` recorre la interfaz real sin pulsar nada que borre o cierre; sin escritorio se lanza con `xvfb-run -a python3 tests/smoke_gui.py capturas`.

Las herramientas de revisión (ruff, bandit, mypy, pip-audit, coverage) **no** se instalan en el Python portable: van en un entorno virtual, con cada paquete fijado por versión y por huella.

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-dev.txt
.venv\Scripts\ruff check app tools tests
.venv\Scripts\bandit -c pyproject.toml -r app tools
.venv\Scripts\mypy --platform win32 --exclude "plat/linux\.py$"
.venv\Scripts\mypy --platform linux --exclude "plat/windows\.py$"
.venv\Scripts\pip-audit --require-hashes --disable-pip -r requirements-dev.txt
```

`pyproject.toml` recoge la configuración y las excepciones, cada una con su motivo. El núcleo pasa `mypy --strict`; la interfaz (tkinter) está exceptuada de momento.

### Generar los paquetes

| Comando | Resultado | Para qué |
|---|---|---|
| `tools\crear_zip.py --protegido` | `dist\SuperLimpio-<versión>-protegido.zip` (~22 MB) | **El que se publica para Windows.** Como el portable, pero el paquete `superlimpio` va compilado (`.pyc`, sin los `.py`) y con el manifiesto de integridad firmado. Necesita `SuperLimpio.exe` y la clave de firma (`tools\firmar.py --generar-claves`, una sola vez) |
| `tools\crear_linux.py` | `dist\SuperLimpio-<versión>-linux.tar.gz` (~200 KB) | **El que se publica para Linux.** Código fuente legible con finales de línea de Unix, `superlimpio.sh` con permiso de ejecución y manifiesto firmado si existe la clave (`--sin-firma` para omitirlo). Se puede generar desde Windows o desde Linux |
| `tools\crear_zip.py --portable` | `dist\SuperLimpio-<versión>-portable.zip` (~21 MB) | **Descomprimir y doble clic en `SuperLimpio.exe`**, sin Internet y sin firma. Lleva el `.exe`, la app, el Python portable y el código ya compilado. Necesita haber ejecutado antes `tools\crear_exe.py` |
| `tools\crear_zip.py` | `dist\SuperLimpio-<versión>.zip` (~100 KB, solo texto) | Compartir o guardar el código. Quien lo reciba ejecuta `preparar_entorno.bat` |
| `tools\crear_zip.py --con-python` | `dist\SuperLimpio-<versión>-con-python.zip` (~17 MB) | Código + Python portable, para seguir desarrollando sin Internet |

La clave privada de firma vive fuera del repositorio (`%USERPROFILE%\.superlimpio\clave_firma.hex`) y nunca debe subirse. `tools\firmar.py --verificar <carpeta>` comprueba un paquete descomprimido igual que lo hace la app al arrancar.

### Publicar una versión

1. Sube el número en `app\superlimpio\__init__.py` y comprueba que el flujo **Linux** de GitHub Actions pasa.
2. Genera `SuperLimpio.exe`, el zip protegido y el paquete de Linux (comandos de arriba).
3. Crea dos etiquetas sobre el mismo commit, `v<versión>-windows` y `v<versión>-linux`, y un release por cada una con su archivo. GitHub no admite dos releases sobre la misma etiqueta.
4. Antes de publicar el de Linux, déjalo como borrador y lanza la verificación del paquete tal cual se descarga: `gh workflow run linux.yml --ref main -f etiqueta=v<versión>-linux`. Comprueba que arranca, que acepta la firma y que rechaza un archivo modificado.

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
| **Memoria y procesos** | Memoria privada, RAM física y CPU, agrupado por programa (p. ej. todos los `chrome.exe` juntos). La columna **Importancia** y el panel inferior dicen qué es cada proceso, si Windows lo necesita y qué pasa si se cierra | Finalizar procesos (los esenciales de Windows están bloqueados). Si eliges el propio Super Limpio, se cierra de forma ordenada en vez de matarse |
| **Optimizar** | *Análisis exhaustivo*: observa todos los procesos durante 10–60 s y señala qué programas acaparan RAM, cuáles no dejan de crecer (posible fuga), cuáles usan CPU sin tener ventana y cuánto falta para agotar la memoria. *Modo eficiente*: eliges el programa o juego que vas a usar y propone qué hacer con cada uno de los demás | Ralentizar (modo de eficiencia de Windows, reversible), cerrar, dar prioridad a tu programa; **Deshacer** y **Reabrir cerrados** al terminar |
| **Inicio de sesión** | Programas que arrancan solos, su estado y si apuntan a archivos ya borrados | Abre el Administrador de tareas para desactivarlos (vía oficial y reversible) |
| **Limpieza** | Temporales, informes de error, cachés de navegadores, de desarrollo (pip, npm, Gradle, Cargo, NuGet), de shaders, Windows Update, papelera… | Analiza primero sin tocar nada; luego limpia lo marcado |
| **Librerías de desarrollo** | `node_modules`, `.venv`, `__pycache__`, `target`, `bin/obj` de .NET, `.next`, `.gradle`… dentro de tus proyectos | Marcar (incluso «más de 6 meses sin tocar») y enviar a la Papelera o borrar |
| **Herramientas del sistema** | Comandos oficiales: Almacenamiento, Liberador de espacio, punto de restauración, análisis y limpieza de WinSxS (DISM), desactivar hibernación | Ejecutar, viendo antes el **comando literal** |
| **Registro de acciones** | Todo lo que la app ha hecho, con fecha y resultado. Se guarda en la carpeta del usuario (`%LOCALAPPDATA%\SuperLimpio\logs\acciones.log` en Windows, `~/.local/state/superlimpio/logs/` en Linux), rota al llegar a 1 MiB y conserva tres archivos anteriores | — |

La tabla describe Windows. En Linux las secciones son las mismas con los equivalentes del sistema: ver [Linux](#linux).

**Tamaño de la interfaz**: con el control «− 100 % +» de la barra lateral o con **Ctrl +**, **Ctrl −** y **Ctrl 0** (vuelve al 100 %). Cambiar el tamaño o el idioma no interrumpe un análisis en marcha. La ventana se adapta a la pantalla: los paneles divididos conservan su proporción al redimensionarla, si cambia la resolución conserva sus proporciones y, si se arrastra fuera, vuelve a un sitio donde se puede agarrar.

## Seguridad

- **Nada se ejecuta sin tu permiso.** Cada acción abre una ventana que muestra exactamente qué rutas o qué comando se van a usar. El botón por defecto es *Cancelar*.
- **Niveles de riesgo**: *Medio* → confirmación simple. *Alto* → además hay que marcar «He revisado…». *Crítico* (borrado definitivo, DISM, powercfg) → además hay que **escribir CONFIRMAR**.
- **La Papelera es la opción por defecto**; el borrado definitivo es una acción aparte.
- **Rutas protegidas**: la app se niega a borrar la carpeta de Windows, *Archivos de programa*, `ProgramData\Microsoft`, la raíz de las unidades y de cualquier disco montado, `$Recycle.Bin` y `System Volume Information` de cualquier unidad, tu carpeta de usuario y sus carpetas principales (Escritorio, Documentos…), **las carpetas de otros usuarios**, `pagefile.sys`/`hiberfil.sys` y la propia carpeta de la app. Para quitar programas usa siempre *Desinstalar*. Se compara la ruta **real**, no el texto: da igual que se escriba con otro uso de mayúsculas, con `/`, con `..`, con el nombre corto (`PROGRA~1`), con el prefijo `\\?\`, como recurso de red del propio equipo (`\\localhost\C$`) o a través de un enlace o *junction*. Los nombres de dispositivo de Windows (`CON`, `NUL`…) y los flujos alternativos (`archivo:flujo`) se rechazan.
- **Procesos protegidos**: `csrss`, `lsass`, `winlogon`, `services`, `svchost`, `dwm`, antivirus de Defender… no se pueden finalizar.
- **Importancia para el sistema**: cada proceso y cada archivo o carpeta lleva un nivel (*Normal*, *Precaución*, *Importante*, *Vital*) con una frase que explica qué es y otra con el riesgo de cerrarlo o borrarlo. Se ve en «Memoria y procesos», en el análisis de «Optimizar» y en el «Analizador de disco», y los avisos de confirmación lo repiten cuando la selección incluye algo delicado (`app\superlimpio\criticality.py`).
- **Cierre ordenado**: al salir (la X, Ctrl+Q o «Finalizar» sobre el propio Super Limpio) se avisa si hay un borrado o una limpieza a medias, se ofrece deshacer el Modo eficiente y se detienen los análisis en marcha.
- **El Modo eficiente propone, no decide.** Se basa en lo que hacen el modo de eficiencia de Windows 11, Process Lasso, Microsoft PC Manager o Razer Cortex, pero sin automatismos: enseña la lista exacta (qué se ralentiza, a qué se le pide que se cierre, qué se finaliza) y espera tu confirmación. La acción por defecto es **ralentizar**, que no cierra nada y se deshace con un botón. A los programas con ventana se les *pide* que se cierren, como si pulsaras su X, así que pueden preguntarte si guardas; forzar el cierre es una casilla aparte y sube el riesgo a *Alto*. Nunca aparecen en la lista Windows y sus servicios, el antivirus, los anti-trampas, la propia app ni nada relacionado con el programa que has elegido (su carpeta, sus procesos hijos y quien lo lanzó). Tampoco se detienen servicios ni se asigna prioridad «Alta» o «Tiempo real». Antes de actuar se comprueba que cada proceso sigue siendo el mismo que se analizó (Windows reutiliza los PID). Los cambios duran lo que la sesión: si cierras la app con el modo activo, pregunta si deshacerlo.
- **Comprimir no toca los originales.** El compresor es propio (biblioteca estándar de Python, sin programas externos) y genera archivos estándar que abren 7-Zip y WinRAR: **7z** con LZMA2 en bloque sólido (los mejores índices; varios hilos si la memoria del equipo lo permite) o **ZIP** con Deflate (lo abre cualquier sistema). La contraseña es opcional y cifra con **AES-256** usando la criptografía del propio sistema (CNG en Windows, OpenSSL en Linux); en 7z se cifran también los nombres de los archivos. La contraseña no se guarda ni se registra, y si se olvida no hay forma de recuperar el contenido. En ZIP solo se admiten contraseñas ASCII, porque cada programa interpreta de forma distinta las tildes y la «ñ». Se escribe en un archivo `.part` que solo recibe su nombre al terminar bien: si se detiene o falla, no queda nada a medias. Al acabar se **relee y comprueba** el archivo entero. No se siguen enlaces ni se descargan archivos «solo en la nube»: se omiten y se avisa. Enviar los originales a la Papelera es una casilla aparte, exige que la comprobación haya salido bien y que no se haya omitido nada, y pide su propia confirmación.
- **La limpieza solo actúa sobre una lista cerrada de ubicaciones conocidas**, respeta los archivos en uso y en `%TEMP%` conserva lo modificado en las últimas 24 h. Las carpetas del sistema se le preguntan a Windows (no se toman de variables de entorno, que cualquier programa puede cambiar) y, antes de vaciar una, se comprueba dónde está de verdad: si es un enlace, o resulta ser tu carpeta de usuario, un disco entero o una zona con carpetas protegidas dentro, se deja sin tocar y se avisa. Como no pasa por la Papelera, la confirmación exige marcar «He revisado…».
- **No sigue enlaces simbólicos ni *junctions*** al analizar o borrar (evita contar doble o salirse de la carpeta): de un enlace se quita el enlace, nunca su destino, y el tipo de cada elemento se vuelve a mirar justo antes de tocarlo. Tampoco se sale a otros discos montados dentro de la carpeta ni entra en `/proc`, `/sys`, `/dev` o `/run`. Los archivos de OneDrive «solo en la nube» se cuentan aparte porque no ocupan disco.
- **Un fallo no detiene el lote y el resumen dice lo que pasó de verdad**: si un archivo está en uso o falta el permiso, se sigue con los demás y se informa de cuáles quedaron; lo que ya no existía se cuenta aparte. Un borrado en marcha se puede detener y deja hecho solo lo que ya estaba hecho.
- **Una sola ventana**: no se pueden abrir dos Super Limpio a la vez en la misma sesión, para que no haya dos limpiezas sobre las mismas carpetas.
- **Sin privilegios, salvo una operación concreta**: la ventana corre siempre como usuario normal (el manifiesto del `.exe` es `asInvoker`). Lo que necesita administrador lo hace un **auxiliar** aparte, mínimo y sin interfaz (`app\superlimpio\helper.py`): recibe una orden concreta —nunca un comando libre—, comprueba que es exactamente la que confirmaste (por su huella SHA-256), vuelve a validar cada ruta con las mismas reglas de rutas protegidas y termina. Las categorías de limpieza las saca de su propia lista; la orden solo trae sus nombres. Las herramientas del sistema que necesitan elevación (DISM, powercfg) se lanzan cada una con su propio aviso UAC, por su ruta completa de System32 y en una consola visible. Si abres la app «como administrador» por tu cuenta, lo indica y recuerda que no hace falta.

## Antivirus y falsos positivos

Los falsos positivos suelen venir de ejecutables empaquetados (PyInstaller, etc.), código ofuscado o comportamientos típicos de malware. Este proyecto los evita a propósito:

- **`SuperLimpio.exe` no es un empaquetado.** No lleva Python ni la app comprimidos dentro, no extrae nada a carpetas temporales y no usa UPX ni nada parecido, que es justo lo que hace saltar a los antivirus con PyInstaller y similares. Solo carga la DLL oficial de Python, **firmada** por la Python Software Foundation, que está a la vista en `runtime\python`. Importa 13 funciones de Windows, lleva icono, información de versión y manifiesto como cualquier programa normal, y su código fuente está en `launcher\launcher.c`.
- La aplicación es el código Python de la carpeta `app`. En el repositorio, en el zip de código y en el paquete de Linux va como fuente legible (`.py`); en el zip protegido de Windows el paquete `superlimpio` va ya compilado por el propio Python (`.pyc`), que es ese mismo código y se puede contrastar con el del repositorio. Quien prefiera no usar el `.exe` puede abrir el código con `SuperLimpio.bat`, que usa `pythonw.exe`.
- Sin empaquetadores, sin Base64, sin PowerShell codificado, sin `-ExecutionPolicy Bypass`, sin ventanas ocultas. La ofuscación con PyArmor existe como opción de `tools\crear_zip.py` (`--pyarmor`), pero los paquetes publicados no la usan.
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
| UAC «¿Quieres permitir que esta aplicación haga cambios?» | Al encargar una operación al auxiliar elevado (limpiar carpetas del sistema, borrar algo que requiere administrador) o lanzar DISM/powercfg | Con `SuperLimpio.exe` el aviso es amarillo y dice *Editor desconocido* (no está firmado): comprueba que la ruta es la de tu carpeta. Con `SuperLimpio.bat` el editor es *Python Software Foundation*; en DISM/powercfg, *Microsoft Windows* |
| «Acceso controlado a carpetas» de Defender | Si lo tienes activado y borras dentro de Documentos, Imágenes… | Permitir `SuperLimpio.exe` (o `pythonw.exe` si usas el `.bat`) en *Seguridad de Windows › Protección contra ransomware* |

Si algún antivirus marcase un archivo, no lo excluyas a ciegas: súbelo a [VirusTotal](https://www.virustotal.com) y revisa qué motor lo detecta. Todo el código es texto legible.

## Estructura

```
SuperLimpio/
├─ SuperLimpio.exe              abre la aplicación (lo genera tools/crear_exe.py; no va a git)
├─ SuperLimpio.bat              abre la aplicación con pythonw.exe, sin el .exe
├─ superlimpio.sh               abre la aplicación en Linux con el Python del sistema
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
│     ├─ criticality.py  importancia para el sistema de cada proceso, archivo y carpeta
│     ├─ fileops.py      Papelera y borrado con comprobaciones
│     ├─ helper.py       auxiliar elevado: la única parte que corre como administrador, orden a orden
│     ├─ archiver.py     compresor 7z / ZIP (LZMA2 sólido, Deflate, AES-256, verificación)
│     ├─ aes.py          AES-256 con la criptografía del sistema (CNG en Windows, OpenSSL en Linux)
│     ├─ config.py       preferencias (idioma, tamaño, divisores), con escritura atómica
│     ├─ i18n.py         textos en español e inglés
│     ├─ integrity.py    comprobación del manifiesto firmado al arrancar (Ed25519)
│     ├─ recovery.py     reparación si el arranque anterior no terminó bien
│     ├─ plat/           todo lo que depende del sistema operativo
│     │  ├─ windows.py / linux.py            llamadas al sistema y listas de datos
│     │  └─ windows_know.py / linux_know.py  qué procesos y carpetas son vitales en cada uno
│     └─ ui/             interfaz (tkinter, sin dependencias externas)
│        └─ assets/      icono y logo de la ventana (los genera tools/crear_exe.py)
├─ launcher/
│  ├─ launcher.c            código del lanzador SuperLimpio.exe
│  ├─ SuperLimpio.manifest  manifiesto de Windows (arranca siempre sin elevar)
│  └─ logo.png              logo; de aquí salen el icono del .exe y el de la ventana
├─ tests/test_core.py    tests de la lógica (y, en Linux, llamadas reales al sistema)
├─ tests/test_seguridad.py  tests de seguridad: rutas, enlaces, borrado, limpieza, auxiliar, integridad
├─ tests/smoke_gui.py    recorrido automático por la interfaz real
├─ tools/crear_exe.py    compila SuperLimpio.exe
├─ tools/crear_zip.py    genera los zips de Windows en dist/
├─ tools/crear_linux.py  genera el .tar.gz de Linux en dist/
├─ tools/firmar.py       claves, firma y verificación del manifiesto de integridad
├─ .github/workflows/    flujo que prueba la aplicación en Windows y Ubuntu y pasa las herramientas de revisión
├─ pyproject.toml        versión de Python admitida y configuración de ruff, mypy y bandit
├─ requirements-dev.txt  herramientas de revisión, fijadas por versión y por huella (no son dependencias de la app)
├─ runtime/              Python portable y caché de código compilado (no van a git)
└─ tools/VSCode/         VS Code portable, opcional (no va a git)
```

Solo usa la biblioteca estándar de Python: no hay que instalar paquetes con pip.

`runtime\_pycache` guarda el código ya compilado para que la ventana abra antes cuando se usa `SuperLimpio.bat`; se puede borrar cuando quieras y se regenera sola. Con `SuperLimpio.exe` el código compilado va en las carpetas `__pycache__` de siempre, junto a cada archivo: el zip portable ya las trae hechas y siguen valiendo aunque muevas la carpeta. `build\` guarda los archivos intermedios de compilar el `.exe`. El registro de acciones y las órdenes al auxiliar viven en la carpeta del usuario (`%LOCALAPPDATA%\SuperLimpio` en Windows, `~/.local/state/superlimpio` en Linux): para no dejar rastro, bórrala también al quitar la aplicación.

## Limitaciones conocidas

- Las apps de **Microsoft Store** no siempre aparecen en el registro clásico: el botón «Apps de Microsoft Store…» abre Configuración para gestionarlas.
- Sin permisos de administrador algunas carpetas del sistema no se pueden leer: el análisis indica cuántas. La app ya no se reinicia elevada para verlas; lo que sí ofrece con elevación es terminar una limpieza o un borrado concretos.
- En Windows, los archivos con enlaces duros (p. ej. dentro de `WinSxS`) pueden contarse más de una vez, igual que en el Explorador. Para WinSxS usa *Herramientas › Analizar almacén de componentes*, que da la cifra real. En Linux cada archivo se cuenta una sola vez y los archivos dispersos por lo que ocupan de verdad.
- Los tamaños se muestran en base 1024 con sus nombres (KiB, MiB, GiB): 1 GiB son 1024 MiB.
- `SuperLimpio.exe` sigue **sin firma Authenticode** (requiere un certificado de pago): es el único punto bloqueante de la ficha de seguridad que no se puede resolver desde el código.
- **Linux**: probado solo en Ubuntu 22.04 y 24.04, y de forma automática (sin un escritorio real). En otras distribuciones puede haber rutas o herramientas que no se reconozcan.
- **Linux**: el Modo eficiente necesita `wmctrl` para saber qué programas tienen ventana, y bajo Wayland solo ve las de XWayland. Ralentizar un programa no se puede deshacer sin ser administrador, así que no se propone por defecto.
- **Linux**: no hay auxiliar elevado. Lo que pertenece a otros usuarios o al sistema se muestra como «sin acceso», y lo que necesita privilegios se hace en una terminal con `sudo`, a la vista.
