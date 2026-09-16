# Запуск обоих сервисов в отдельных окнах PowerShell (Windows).
# Использование (из корня репозитория):  .\scripts\start_services.ps1
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Notification Service :8001'; & '$python' -m uvicorn notification_service.main:app --port 8001"
Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='Task Service :8000'; & '$python' -m uvicorn task_service.main:app --port 8000"

Write-Host "Task Service:         http://localhost:8000/docs"
Write-Host "Notification Service: http://localhost:8001/docs"
