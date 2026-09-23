param([switch]$Lite)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskEnvironment = Join-Path $taskRoot '.venv-documents'
python -m venv $taskEnvironment
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno PDF. Revisa Python 3.10 o superior.' }
$taskPython = Join-Path $taskEnvironment 'Scripts\python.exe'
if ($Lite) {
    & $taskPython -m pip install 'pypdf==6.19.0' 'psutil==7.2.2'
} else {
    & $taskPython -m pip install -r (Join-Path $taskRoot 'requirements-documents.txt') --extra-index-url https://download.pytorch.org/whl/cpu
}
if ($LASTEXITCODE -ne 0) { throw 'La instalación PDF no terminó. El programa principal sigue disponible.' }
Write-Output 'Soporte documental instalado. Reinicia el servicio local si estaba abierto.'
