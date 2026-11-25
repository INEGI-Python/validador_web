@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1

echo Creando entorno virtual local...
if not exist ".venv" (
    py -m venv .venv
    if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Construyendo ValidadorTopologico...
python -m PyInstaller --clean --noconfirm validador_topologico.spec
if errorlevel 1 exit /b 1

echo.
echo Paquete generado en: dist\ValidadorTopologico
endlocal
