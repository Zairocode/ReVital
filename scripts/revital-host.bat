@echo off
rem ReVital - documenta ESTE equipo Windows (solo lectura). Doble clic, o:  revital-host.bat NOMBRE-DE-LA-INSTITUCION
setlocal
cd /d "%~dp0.."
set ENT=%~1
if "%ENT%"=="" set ENT=MI-INSTITUCION
set PY=python
where python >nul 2>nul || set PY=py -3
%PY% -m revital.host --entidad "%ENT%" --out salida
if errorlevel 1 (
  echo.
  echo No se pudo ejecutar. Instala Python 3.8 o superior ^(python.org^) y vuelve a intentar.
  pause
  exit /b 1
)
echo.
echo Listo. El resultado esta en la carpeta "salida".
echo Para evaluar vulnerabilidades:  %PY% -m revital.cves --entidad "%ENT%"
echo Para verlo en pantalla:         %PY% -m revital.panel --abrir
pause
