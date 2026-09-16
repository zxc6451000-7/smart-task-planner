# Ручная сквозная проверка через curl (Windows). Сервисы должны быть запущены на 8000 и 8001.
# Использование (из корня репозитория):  .\scripts\e2e_check.ps1
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$body = Join-Path $env:TEMP "e2e_task.json"
[IO.File]::WriteAllText($body, '{"title": "Сдать лабораторную", "description": "МДК 02.02, ЛР 2", "status": "new"}')

Write-Host "== 1. Создаём задачу (ожидаем 201)"
curl.exe -s -i -X POST "http://localhost:8000/api/tasks" -H "Content-Type: application/json" --data-binary "@$body"
Write-Host ""; Start-Sleep -Seconds 1

Write-Host "== 2. Задача сохранена в Task Service"
curl.exe -s "http://localhost:8000/api/tasks"; Write-Host ""

Write-Host "== 3. Счётчики доставки вебхука"
curl.exe -s "http://localhost:8000/health"; Write-Host ""

Write-Host "== 4. Notification Service получил событие"
curl.exe -s "http://localhost:8001/api/notifications"; Write-Host ""

Write-Host "== 5. Лог уведомлений"
Get-Content -Encoding UTF8 -Tail 3 "logs\notifications.log"
