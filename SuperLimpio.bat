@echo off
rem ======================================================================
rem  Super Limpio - lanzador
rem  Abre la aplicación con el Python portable de runtime\python (firmado
rem  por la Python Software Foundation). No instala nada, no descarga nada
rem  y no modifica el sistema.
rem ======================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem -I = modo aislado: Python no hace caso a PYTHONPATH, PYTHONSTARTUP ni a los paquetes
rem del usuario, y no busca módulos en la carpeta actual. Es lo mismo que hace SuperLimpio.exe.
rem (El código compilado va a runtime\_pycache: lo decide app\main.py.)
set "PYW=%~dp0runtime\python\pythonw.exe"
if exist "%PYW%" goto :run

rem Sin Python portable: probar con un Python ya instalado en el equipo (3.11 o posterior)
"%SystemRoot%\System32\where.exe" pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 -I "%~dp0app\main.py"
    exit /b 0
)

echo.
echo  No se ha encontrado el Python portable en runtime\python.
echo  Ejecuta primero  preparar_entorno.bat  (solo hace falta una vez).
echo.
pause
exit /b 1

:run
start "" "%PYW%" -I "%~dp0app\main.py"
exit /b 0
