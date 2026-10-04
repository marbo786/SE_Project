# Start backend (from SE_Project root)
Write-Host "Starting SRS Reviewer Backend..." -ForegroundColor Cyan
Set-Location backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
