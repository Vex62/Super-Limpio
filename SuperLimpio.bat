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

rem Todo el código compilado en una sola carpeta (se puede borrar)
set "PYTHONPYCACHEPREFIX=%~dp0runtime\_pycache"

set "PYW=%~dp0runtime\python\pythonw.exe"
if exist "%PYW%" goto :run

rem Sin Python portable: probar con un Python ya instalado en el equipo
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%~dp0app\main.py"
    exit /b 0
)

echo.
echo  No se ha encontrado el Python portable en runtime\python.
echo  Ejecuta primero  preparar_entorno.bat  (solo hace falta una vez).
echo.
pause
exit /b 1

:run
start "" "%PYW%" "%~dp0app\main.py"
exit /b 0
