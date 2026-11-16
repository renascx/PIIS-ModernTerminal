# PIIS-ModernTerminal — интеллектуальная система автоматизированной конфигурации сетевого оборудования

Веб-терминал для SSH/Telnet-сессий с LLM-помощником (Ollama). Ассистент читает вывод
терминала, предлагает команды для настройки оборудования (VLAN, port-security, trunk,
ACL и т. п.) и **выполняет их только после подтверждения пользователя**.


## Статус

Проект развивается поэтапно, см. [docs/roadmap.md](docs/roadmap.md).

| Этап | Содержание | Статус |
|------|-----------|--------|
| 0 | Документация, роли, backlog | готово |
| 1 | Каркас backend, Ollama-провайдер, модуль безопасности команд | готово |
| 2 | Коннекторы SSH/Telnet, реестр сессий, API сессий | готово |
| 3 | Цикл агента (tool-calling), подтверждение команд, журнал аудита | готово |
| 3 | Эталонный набор из 32 сценариев и скрипт оценки | готово |
| 4 | Frontend (терминал + чат ассистента), WebSocket терминала | запланировано |
| 5 | Docker, CI/CD, мониторинг | запланировано |
| 6 | Прогон оценки на реальной модели, метрики, защита | запланировано |

## Документация

- [docs/requirements.md](docs/requirements.md) — требования, сценарии, метрики успеха
- [docs/architecture.md](docs/architecture.md) — архитектура и компоненты
- [docs/roles.md](docs/roles.md) — роли, зоны ответственности, RACI
- [docs/roadmap.md](docs/roadmap.md) — план по этапам
- [docs/board-tasks.md](docs/board-tasks.md) и [docs/board-tasks.csv](docs/board-tasks.csv) — задачи для Jira/Trello

## Быстрый старт

Нужен Python 3.11+ и локально запущенный Ollama (для тестов он не нужен).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Linux/macOS: cp .env.example .env
uvicorn app.main:app --reload
pytest
```

## API

| Метод и путь | Назначение |
|--------------|-----------|
| `GET /api/health` | проверка работы |
| `GET`, `PUT /api/ai/settings` | URL Ollama, модель, режим подтверждения |
| `GET /api/ai/models` | список моделей Ollama |
| `POST /api/safety/check` | оценка риска списка команд |
| `POST /api/sessions` | подключиться к устройству по SSH или Telnet |
| `GET /api/sessions`, `DELETE /api/sessions/{id}` | список и закрытие сессий |
| `GET /api/sessions/{id}/output` | последний вывод терминала |
| `POST /api/sessions/{id}/commands` | отправить команду (нужен `confirmed`, если требуется подтверждение) |
| `POST /api/sessions/{id}/assistant` | написать ассистенту |
| `GET /api/sessions/{id}/pending` | команды, ждущие подтверждения |
| `POST /api/pending/{id}/approve`, `/deny` | подтвердить или отклонить команду |
| `GET /api/audit` | журнал выполненных и отклонённых команд |

## Оценка качества модели

Эталонные сценарии лежат в `backend/evaluation/scenarios.json` (32 сценария: диагностика, VLAN,
port-security, trunk, ACL, опасные команды). Скрипт запускает агента на поддельном устройстве
и считает метрики из требований.

```bash
cd backend
python -m evaluation.runner --fake                        # проверка самого скрипта, без модели
python -m evaluation.runner --model qwen3:8b --report report.json   # с локальной Ollama
```

Метрики: `command_accuracy` (цель ≥ 0.90) и `dangerous_gated` (цель 1.00). Выводы устройств в
сценариях синтетические и пока не сверены с реальным оборудованием.

## Команда

| Роль | Участник |
|------|----------|
| ML + Data Engineer | Ярослав |
| DevOps + Backend | Всеволод |
| Product Owner / Аналитик | Андрей |
| Frontend / Визуализатор | Виталий |
| Тимлид / Scrum-мастер | Роман |
