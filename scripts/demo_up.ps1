param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9.-]+$')]
    [string]$Domain
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    foreach ($command in @('docker', 'ngrok')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            throw "Install $command and add it to PATH first. See docs/DEMO.md."
        }
    }
    if ($Domain -match 'YOUR-NAME' -or -not (Test-Path -LiteralPath 'backend/.env')) {
        throw 'Set your ngrok domain and prepare backend/.env using docs/DEMO.md.'
    }
    if (Select-String -LiteralPath 'backend/.env' -Pattern 'YOUR-PROJECT' -Quiet) {
        throw 'Replace the Vercel URL placeholders in backend/.env first.'
    }
    & docker compose up -d --build postgres redis migrate backend worker dispatcher
    if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed; the tunnel was not started.' }
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-RestMethod 'http://127.0.0.1:8001/ready' -TimeoutSec 2
            if ($response.status -eq 'ready') { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'API not ready. Inspect docker compose logs backend migrate worker dispatcher.' }
    Write-Host 'The tunnel exposes open signup. Keep this terminal open; Ctrl+C stops the tunnel.'
    Write-Host 'After the demo, run docker compose down from the repo root (without -v).'
    & ngrok http 8001 --url "https://$Domain"
    if ($LASTEXITCODE -ne 0) { throw 'ngrok exited unsuccessfully. Local containers are still running.' }
} finally {
    Pop-Location
}
