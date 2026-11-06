$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv313\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Install the backend dependencies in .venv313 first. See docs/DEMO.md.' }
$node = (Get-Command node -ErrorAction Stop).Source
$vite = Join-Path $repoRoot 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path $vite)) { throw 'Run npm ci in frontend first.' }
foreach ($port in @(8001, 5174)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop the old server before starting the demo."
    }
}
$runtime = Join-Path $repoRoot '.demo-runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$settings = @{
    APP_ENV='development'; COOKIE_SECURE='false'; LLM_PROVIDER='mock'; JOB_BACKEND='local'
    PUBLIC_URL='http://localhost:5174'; CORS_ORIGINS='http://localhost:5174,http://127.0.0.1:5174'
    DATABASE_URL=('sqlite:///' + (Join-Path $runtime 'demo.db').Replace('\','/'))
    UPLOAD_DIR=(Join-Path $runtime 'uploads'); MAIL_SINK_DIR=(Join-Path $runtime 'mail')
    SMTP_HOST=''; GROQ_API_KEY=''; API_PROXY_TARGET='http://127.0.0.1:8001'
    LLM_PRICING='{"mock/mock-model-v2":{"input":0,"output":0}}'; LLM_RUN_COST_BUDGET_MICROUSD='1000000'
}
$previous = @{}
$children = @()
Push-Location $repoRoot
try {
    foreach ($key in $settings.Keys) { $previous[$key]=[Environment]::GetEnvironmentVariable($key); [Environment]::SetEnvironmentVariable($key,$settings[$key]) }
    Push-Location (Join-Path $repoRoot 'backend')
    try { & $python -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { throw 'Migrations failed.' } } finally { Pop-Location }
    $children += Start-Process -FilePath $python -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8001' -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'api.log') -RedirectStandardError (Join-Path $runtime 'api.err.log')
    $children += Start-Process -FilePath $python -ArgumentList '-m app.jobs.worker' -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'worker.log') -RedirectStandardError (Join-Path $runtime 'worker.err.log')
    $children += Start-Process -FilePath $node -ArgumentList ('"' + $vite + '" --host 127.0.0.1 --port 5174 --strictPort') -WorkingDirectory (Join-Path $repoRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'frontend.log') -RedirectStandardError (Join-Path $runtime 'frontend.err.log')
    $ready=$false
    for ($attempt=0; $attempt -lt 45; $attempt++) {
        if ($children.Where({ $_.HasExited }).Count) { throw 'A demo process stopped. See .demo-runtime logs.' }
        try { if ((Invoke-RestMethod 'http://127.0.0.1:5174/api/ready' -TimeoutSec 2).status -eq 'ready') { $ready=$true; break } } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Demo did not become ready. See .demo-runtime logs.' }
    Write-Host 'Demo ready: http://localhost:5174'
    Write-Host 'Keep this terminal open. Ctrl+C stops all demo processes. Data stays in .demo-runtime.'
    while ($true) {
        if ($children.Where({ $_.HasExited }).Count) { throw 'A demo process stopped. See .demo-runtime logs.' }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($child in $children) { if (-not $child.HasExited) { Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue } }
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key,$previous[$key]) }
    Pop-Location
}
