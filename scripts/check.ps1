$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv313/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run ./run_backend.ps1 first to create the virtual environment' }
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend checks failed' }
} finally { Pop-Location }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
