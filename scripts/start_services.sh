#!/usr/bin/env bash
# Запуск обоих сервисов в фоне (Linux/macOS/Git Bash). Остановка: Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."

uvicorn notification_service.main:app --port 8001 &
NOTIF_PID=$!
uvicorn task_service.main:app --port 8000 &
TASK_PID=$!
trap 'kill $NOTIF_PID $TASK_PID' EXIT
wait
