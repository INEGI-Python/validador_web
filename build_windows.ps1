$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Creando entorno virtual local..."
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Construyendo ValidadorTopologico..."
python -m PyInstaller --clean --noconfirm validador_topologico.spec

Write-Host ""
Write-Host "Paquete generado en: dist\ValidadorTopologico"
