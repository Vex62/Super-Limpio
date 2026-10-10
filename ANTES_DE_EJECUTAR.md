# Antes de ejecutar

Qué necesita tu equipo para abrir Super Limpio, en Windows y en Linux, y cómo conseguirlo si falta algo.

*English version: [BEFORE_RUN.md](BEFORE_RUN.md)*

## En resumen

| | Windows | Linux |
|---|---|---|
| Sistema | Windows 10 u 11, de 64 bits | Una distribución con escritorio gráfico |
| Qué descargar | `SuperLimpio-<versión>-protegido.zip` | `SuperLimpio-<versión>-linux.tar.gz` |
| Hay que instalar algo | No. El zip lo trae todo | Python 3.11 o posterior, con tkinter |
| Espacio en disco | Unos 80 MB | Menos de 5 MB |
| Internet | Solo para la descarga | Solo para la descarga |
| Permisos de administrador | No | No |

Los dos archivos están en la página de [versiones (Releases)](https://github.com/Vex62/Super-Limpio/releases). Cada sistema tiene su propia entrada: descarga la que lleva el nombre de tu sistema.

Super Limpio no se instala. Es una carpeta: la descomprimes, la abres y, cuando ya no la quieras, la borras.

---

## Windows

### Lo que necesitas

- **Windows 10 o Windows 11, de 64 bits.** Casi todos los equipos de los últimos diez años lo son. Para comprobarlo: *Configuración › Sistema › Información*, y mira «Tipo de sistema».
- **Unos 80 MB libres** en el disco donde vayas a poner la carpeta. Puede ser el disco interno, uno externo o una memoria USB.
- **Nada más.** No hace falta instalar Python ni ningún otro programa: el zip incluye todo lo que la aplicación usa.

### Antes de abrirla

1. **Desbloquea el zip.** Windows marca los archivos que vienen de Internet. Haz clic derecho sobre el zip, elige **Propiedades**, marca **Desbloquear** (abajo del todo) y pulsa **Aceptar**. Si no ves esa casilla, no hace falta.
2. **Descomprime el zip entero.** Clic derecho sobre el zip y **Extraer todo…**. No abras el programa desde dentro del zip: no funcionaría.
3. **Mantén la carpeta junta.** `SuperLimpio.exe` necesita las carpetas `app` y `runtime` a su lado. Puedes mover o copiar la carpeta completa, pero no saques el `.exe` de ella. Si quieres tenerlo a mano, crea un acceso directo.

Después, doble clic en `SuperLimpio.exe`.

### Avisos que puede mostrar Windows

Son normales y no indican un problema.

| Aviso | Por qué aparece | Qué hacer |
|---|---|---|
| «Windows protegió su PC» (ventana azul) | El programa es nuevo y no lleva la firma de pago de un editor | Pulsa **Más información** y después **Ejecutar de todas formas**. Si desbloqueaste el zip, no suele aparecer |
| «¿Quieres permitir que esta aplicación haga cambios?» | Solo aparece si pides una acción que necesita administrador, por ejemplo limpiar carpetas del sistema | Comprueba que la ruta es la de tu carpeta de Super Limpio y acepta. Si dices que no, no se hace nada |
| El antivirus bloquea un borrado en Documentos o Imágenes | Tienes activado el «Acceso controlado a carpetas» | En *Seguridad de Windows › Protección contra ransomware*, permite `SuperLimpio.exe` |

### Consejos

- **Elige una carpeta sencilla.** Por ejemplo `C:\SuperLimpio` o una carpeta dentro de tu usuario. Evita rutas muy largas.
- **En un equipo de empresa** puede que no tengas permiso para ejecutar programas descargados. En ese caso, consulta con quien administra el equipo.
- **Si tu antivirus marca algún archivo**, no lo excluyas sin más: comprueba que la descarga es la original (ver «Comprobar la descarga», más abajo).
- **No necesitas abrirla «como administrador».** Funciona como usuario normal y pide permiso solo cuando una acción concreta lo requiere.

---

## Linux

### Lo que necesitas

- **Un escritorio gráfico** (GNOME, KDE, Xfce, Cinnamon, MATE…). Super Limpio es una aplicación con ventanas; no funciona en un servidor sin pantalla.
- **Python 3.11 o posterior.**
- **tkinter**, la parte de Python que dibuja las ventanas. En muchas distribuciones viene en un paquete aparte.

### Comprobar qué tienes

Abre una terminal y escribe:

```
python3 --version
python3 -c "import tkinter; print('tkinter disponible')"
```

- Si la primera línea muestra `Python 3.11` o un número mayor, y la segunda responde `tkinter disponible`, ya puedes ejecutar Super Limpio.
- Si no, instala lo que falte con la orden de tu distribución.

### Instalar lo que falte

| Distribución | Orden |
|---|---|
| Ubuntu 24.04 o posterior, Debian 12 o posterior, Linux Mint 22 | `sudo apt install python3 python3-tk` |
| Fedora | `sudo dnf install python3 python3-tkinter` |
| Arch Linux, Manjaro | `sudo pacman -S python tk` |
| openSUSE | `sudo zypper install python3 python3-tk` |

Estas órdenes piden tu contraseña porque instalan paquetes del sistema. Super Limpio en sí no necesita permisos de administrador.

**Si tu distribución trae un Python anterior al 3.11** (es el caso de Ubuntu 22.04 y Linux Mint 21, que traen el 3.10), tienes dos caminos:

- Actualizar a una versión más reciente de la distribución. Es lo más sencillo a largo plazo.
- Instalar un Python más nuevo junto al del sistema, sin sustituirlo. En Ubuntu y derivadas se puede hacer con el repositorio «deadsnakes»:

  ```
  sudo add-apt-repository ppa:deadsnakes/ppa
  sudo apt update
  sudo apt install python3.11 python3.11-tk
  ```

  No hace falta nada más: el lanzador de Super Limpio busca `python3.11`, `python3.12`, etc. y usa el primero que sirva.

### Antes de abrirla

```
tar -xzf SuperLimpio-<versión>-linux.tar.gz
cd SuperLimpio
./superlimpio.sh
```

Si quieres que aparezca en el menú de aplicaciones de tu usuario: `./superlimpio.sh --instalar` (se quita con `--quitar`).

Si falta Python o tkinter, el lanzador lo dice y muestra qué paquete instalar.

### Opcional

- **`wmctrl`**: permite a la sección «Optimizar» saber qué programas tienen una ventana abierta. Se instala con el gestor de paquetes (`sudo apt install wmctrl`, `sudo dnf install wmctrl`…).
- **Un emulador de terminal**: las «Herramientas del sistema» y la desinstalación de programas abren una terminal para que veas la orden y escribas tu contraseña. Cualquier escritorio trae una.

### Consejos

- **Descomprime en tu carpeta personal** (por ejemplo `~/SuperLimpio`). En memorias USB con formato FAT o exFAT no se conserva el permiso de ejecución; si ahí no arranca, usa `sh superlimpio.sh`.
- **«Permiso denegado» al ejecutar**: devuelve el permiso con `chmod +x superlimpio.sh`.
- **No la ejecutes con `sudo`.** La aplicación está pensada para tu usuario. Lo que necesita privilegios se abre en una terminal, a la vista, y te pide la contraseña ahí.
- **Probada en** Ubuntu 22.04 y 24.04. En Fedora, Arch y openSUSE debería funcionar, pero no se ha probado tanto.

---

## Comprobar la descarga (opcional, recomendado)

En la página de cada versión figura el **SHA-256** del archivo: una huella que solo coincide si el archivo es exactamente el publicado.

- **Windows** (en PowerShell): `Get-FileHash SuperLimpio-<versión>-protegido.zip`
- **Linux**: `sha256sum SuperLimpio-<versión>-linux.tar.gz`

Compara el resultado con el de la página. Si no coincide, vuelve a descargar el archivo y no lo abras.

Además, Super Limpio comprueba su propia integridad cada vez que arranca: si alguien ha modificado o añadido archivos en la carpeta, se niega a abrirse y lo indica.

## Qué puedes esperar al usarla

- **Funciona sin conexión.** No envía datos a ningún sitio.
- **Nada se borra ni se cierra sin que lo confirmes.** Cada acción muestra antes qué va a tocar.
- **Por defecto usa la Papelera**, de donde se puede recuperar. El borrado definitivo es una acción aparte.
- **No modifica tu sistema al abrirse**: no instala servicios, no se queda en segundo plano y no arranca sola.

## Si algo no funciona

| Qué ves | Qué hacer |
|---|---|
| Windows: «Falta la carpeta app» o «Falta el Python portable» | Descomprime el zip entero y abre el `.exe` desde la carpeta `SuperLimpio`, sin moverlo |
| Windows: no pasa nada al hacer doble clic | Comprueba que el antivirus no ha retirado archivos de la carpeta y vuelve a descomprimir el zip |
| Linux: «Super Limpio necesita Python 3.11 o posterior» | Sigue «Instalar lo que falte», más arriba |
| Linux: «Falta tkinter» | Instala el paquete de tkinter de tu distribución (tabla de arriba) |
| «Esta copia de Super Limpio ha sido modificada» | La carpeta no es la original. Bórrala y descarga de nuevo desde la página de versiones |
| «Super Limpio ya está abierto» | Ya hay una ventana abierta en tu sesión. Solo se permite una a la vez |

¿Sigue sin funcionar? Abre una incidencia en <https://github.com/Vex62/Super-Limpio/issues> indicando tu sistema, su versión y el mensaje exacto que ves.
