@echo off
rem ======================================================================
rem  Super Limpio - preparar el entorno portable (solo la primera vez)
rem
rem  Qué hace (y pide permiso antes de cada paso):
rem    1. Descarga los paquetes OFICIALES de Python 3.12.10 desde python.org
rem    2. Comprueba su firma digital (Python Software Foundation)
rem    3. Los EXTRAE dentro de esta carpeta (runtime\python). No se instala
rem       nada en Windows: ni registro, ni PATH, ni accesos directos, ni
rem       entrada en "Aplicaciones". No necesita administrador.
rem    4. (Opcional) Descarga VS Code portable oficial de Microsoft en
rem       tools\VSCode y le instala la extensión de Python
rem
rem  Herramientas usadas, todas incluidas en Windows 11: curl.exe, tar.exe,
rem  msiexec.exe (solo para extraer, opción /a) y PowerShell solo para leer
rem  la firma digital. Nada se ejecuta oculto.
rem ======================================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PYVER=3.12.10"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/amd64"
set "PYPARTS=core exe lib tcltk"
set "DL=%~dp0runtime\_descargas"
set "PYDIR=%~dp0runtime\python"
set "VSDIR=%~dp0tools\VSCode"
set "VSURL=https://update.code.visualstudio.com/latest/win32-x64-archive/stable"
set "VSZIP=%DL%\vscode-portable.zip"

echo.
echo  =============================================================
echo    SUPER LIMPIO - Preparación del entorno portable
echo  =============================================================
echo.

where curl.exe >nul 2>nul || goto :no_curl
if not exist "%DL%" mkdir "%DL%"

rem ---------------------------------------------------------------- Python
if exist "%PYDIR%\pythonw.exe" (
    echo  [OK] Python portable ya presente en runtime\python
    goto :vscode
)

echo  Paso 1: Python %PYVER% oficial (descarga de unos 14 MB, ocupa 45 MB)
echo     Origen:  %PYURL%/   (%PYPARTS%)
echo     Destino: %PYDIR%
echo.
echo     Solo se copian archivos dentro de esta carpeta. No se instala
echo     nada en Windows y no afecta a otro Python que ya tengas.
echo.
choice /c SN /m "  ¿Descargar Python portable"
if errorlevel 2 goto :skip_python

for %%M in (%PYPARTS%) do (
    echo  Descargando %%M.msi ...
    curl.exe -L --fail --silent --show-error -o "%DL%\%%M.msi" "%PYURL%/%%M.msi" || goto :dl_error
)

echo  Comprobando firmas digitales...
for %%M in (%PYPARTS%) do (
    call :check_signature "%DL%\%%M.msi" "Python Software Foundation" || goto :sig_error
)
echo  [OK] Firma válida de Python Software Foundation en los 4 paquetes

echo  Extrayendo en runtime\python ...
for %%M in (%PYPARTS%) do (
    start "" /wait msiexec.exe /a "%DL%\%%M.msi" /qn TARGETDIR="%PYDIR%"
    if errorlevel 1 goto :install_error
)
rem La extracción deja una copia reducida de cada .msi: no hace falta
del /q "%PYDIR%\*.msi" 2>nul
if not exist "%PYDIR%\pythonw.exe" goto :install_error

"%PYDIR%\python.exe" -B -c "import tkinter, ctypes, winreg; print('  [OK] Python', __import__('sys').version.split()[0], 'con tkinter')" || goto :install_error
goto :vscode

:skip_python
echo  Python omitido. SuperLimpio.bat intentará usar un Python ya instalado.

rem ---------------------------------------------------------------- VS Code
:vscode
echo.
if exist "%VSDIR%\Code.exe" (
    echo  [OK] VS Code portable ya presente en tools\VSCode
    goto :extensions
)
echo  Paso 2 (opcional, solo para modificar el código): VS Code portable
echo     Origen:  %VSURL%   (unos 150 MB)
echo     Destino: %VSDIR%   (modo portable: datos en tools\VSCode\data)
echo     Si solo quieres USAR la aplicación, contesta N.
echo.
choice /c SN /m "  ¿Descargar VS Code portable"
if errorlevel 2 goto :done

curl.exe -L --fail --progress-bar -o "%VSZIP%" "%VSURL%" || goto :dl_error
if not exist "%VSDIR%" mkdir "%VSDIR%"
echo  Descomprimiendo...
tar.exe -xf "%VSZIP%" -C "%VSDIR%" || goto :install_error
call :check_signature "%VSDIR%\Code.exe" "Microsoft Corporation" || goto :sig_error
echo  [OK] Firma válida de Microsoft Corporation
if not exist "%VSDIR%\data" mkdir "%VSDIR%\data"

:extensions
if not exist "%VSDIR%\bin\code.cmd" goto :done
echo.
echo  Paso 3 (opcional): extensión oficial de Python para VS Code
echo     (ms-python.python, desde el Marketplace de Microsoft; se guarda en tools\VSCode\data)
choice /c SN /m "  ¿Instalar la extensión de Python"
if errorlevel 2 goto :done
call "%VSDIR%\bin\code.cmd" --install-extension ms-python.python --force

:done
echo.
echo  =============================================================
echo    Listo. Abre la aplicación con SuperLimpio.bat
echo    (la carpeta runtime\_descargas ya se puede borrar)
echo  =============================================================
echo.
pause
exit /b 0

rem ----------------------------------------------------------- subrutinas
:check_signature
rem %1 = archivo, %2 = firmante esperado
powershell.exe -NoProfile -NonInteractive -Command "$s = Get-AuthenticodeSignature -LiteralPath '%~1'; if ($s.Status -eq 'Valid' -and $s.SignerCertificate.Subject -like '*%~2*') { exit 0 } else { Write-Host ('  Firma: ' + $s.Status + ' / ' + $s.SignerCertificate.Subject); exit 1 }"
exit /b %errorlevel%

:no_curl
echo  No se encontró curl.exe (viene con Windows 10 1803+ y Windows 11).
goto :fail
:dl_error
echo  Error de descarga. Comprueba tu conexión a Internet.
goto :fail
:sig_error
echo  LA FIRMA DIGITAL NO ES VÁLIDA. Por seguridad se cancela la preparación.
echo  Borra la carpeta runtime\_descargas y vuelve a intentarlo.
goto :fail
:install_error
echo  La preparación no se completó correctamente.
goto :fail
:fail
echo.
pause
exit /b 1
