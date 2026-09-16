#!/usr/bin/env bash
# Ручная сквозная проверка через curl. Сервисы должны быть запущены на 8000 и 8001.
set -euo pipefail
TASKS=${TASKS:-http://localhost:8000}
NOTIF=${NOTIF:-http://localhost:8001}

echo "== 1. Создаём задачу (ожидаем 201)"
curl -s -i -X POST "$TASKS/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Сдать лабораторную", "description": "МДК 02.02, ЛР 2", "status": "new"}'
echo; sleep 1

echo "== 2. Задача сохранена в Task Service"
curl -s "$TASKS/api/tasks"; echo

echo "== 3. Счётчики доставки вебхука"
curl -s "$TASKS/health"; echo

echo "== 4. Notification Service получил событие"
curl -s "$NOTIF/api/notifications"; echo

echo "== 5. Лог уведомлений"
tail -n 3 logs/notifications.log
