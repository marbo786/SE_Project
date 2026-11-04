# Start backend (from SE_Project root)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot '.venv313/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    py -3.13 -m venv (Join-Path $projectRoot '.venv313')
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
}
Push-Location (Join-Path $projectRoot 'backend')
$analysisWorker = $null
try {
    & $python -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
    $analysisWorker = Start-Process -FilePath $python -ArgumentList @('-m', 'app.jobs.worker') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} finally {
    if ($analysisWorker -and -not $analysisWorker.HasExited) {
        & taskkill /PID $analysisWorker.Id /T /F | Out-Null
    }
    Pop-Location
}
