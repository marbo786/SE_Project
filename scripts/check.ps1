$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'backend')
try {
    python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend checks failed' }
} finally { Pop-Location }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
