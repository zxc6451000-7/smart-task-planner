# Распределение ролей

| Участник    | Роль                                     | Зона ответственности |
|-------------|------------------------------------------|----------------------|
| Хря Гле  | Архитектор / Tech Lead                   | Контракт, CI, ревью PR, разрешение конфликтов, интеграционные тесты, итоговый отчёт |
| Ив Вик  | Backend-разработчик Task Service         | REST API задач, хранилище, юнит-тесты API |
| Рог Вад  | Backend-разработчик Task Service         | Клиент вебхука, очередь повторных отправок в памяти, тесты доставки |
| Кул Ник  | Backend-разработчик Notification Service | Приём вебхука, запись уведомлений, защита от дублей, тесты |

## Ветки

| Ветка                           | Владелец        | Создана от |
|---------------------------------|-----------------|------------|
| `main` (защищена)               | Tech Lead       | —          |
| `dev`                           | Tech Lead       | `main`     |
| `feature/tasks-service`         | Ив Вик, Рог Вад  | `dev`      |
| `feature/notifications-service` | Кул Ник      | `dev`      |
| `docs/integration-report`       | Tech Lead       | `dev`      |

## Порядок слияния

1. PR `feature/tasks-service` → `dev` (ревью Tech Lead).
2. `feature/notifications-service`: `git pull --rebase origin dev`, разрешение конфликта, PR → `dev`.
3. PR `docs/integration-report` → `dev` (интеграционные тесты и отчёт).
4. PR `dev` → `main`.
