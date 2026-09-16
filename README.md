# Умный планировщик задач

Учебный прототип из двух микросервисов (МДК 02.02, лабораторная работа №2).

```
 клиент ──POST /api/tasks──▶ Task Service :8000 ──вебхук POST /api/webhooks/task_created──▶ Notification Service :8001
                               │ хранилище в памяти                                           │ консоль + logs/notifications.log
                               └ очередь повторов в памяти                                    └ защита от дублей по X-Event-Id
```

- **Task Service** — создание, редактирование, удаление и получение списка задач ([README](task_service/README.md)).
- **Notification Service** — принимает событие о создании задачи и фиксирует уведомление ([README](notification_service/README.md)).
- Контракт взаимодействия — [API_CONTRACT.md](API_CONTRACT.md).
- Роли и ветки — [docs/ROLES.md](docs/ROLES.md). Отчёт о слиянии — [REPORT.md](REPORT.md).

## Быстрый старт

Нужен Python 3.12+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r task_service/requirements.txt -r notification_service/requirements.txt -r requirements-dev.txt
```

Запуск обоих сервисов:

```bash
# Windows (откроет два окна)
.\scripts\start_services.ps1
# Linux/macOS/Git Bash
./scripts/start_services.sh
```

Сквозная проверка (в другом терминале):

```bash
.\scripts\e2e_check.ps1      # Windows
./scripts/e2e_check.sh       # Linux/macOS/Git Bash
```

или вручную:

```bash
curl -i -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "e2e", "status": "new"}'
curl http://localhost:8001/api/notifications
```

Документация Swagger: <http://localhost:8000/docs>, <http://localhost:8001/docs>.

## Тесты

```bash
python -m pytest                 # всё: юнит + интеграционные
python -m pytest task_service    # только Task Service
```

Те же тесты запускает GitHub Actions на каждый Pull Request в `dev` и `main`.

## Структура

```
API_CONTRACT.md            контракт API (contract-first)
REPORT.md                  отчёт о конфликтах и принятых решениях
docs/ROLES.md              роли, ветки, порядок слияния
task_service/              Task Service (FastAPI) + tests/
notification_service/      Notification Service (FastAPI) + tests/
tests/integration/         сквозные тесты с запуском обоих сервисов
scripts/                   запуск сервисов и e2e-проверка
.github/                   CI, шаблон PR, CODEOWNERS
```

## Правила работы с репозиторием

- `main` — защищённая ветка, изменения только через Pull Request с ревью и зелёным CI.
- `dev` — ветка интеграции.
- `feature/*` — рабочие ветки, создаются от `dev`.
