# PIIS-ModernTerminal — интеллектуальная система автоматизированной конфигурации сетевого оборудования

Веб-терминал для SSH/Telnet-сессий с LLM-помощником (Ollama). Ассистент читает вывод
терминала, предлагает команды для настройки оборудования (VLAN, port-security, trunk,
ACL и т. п.) и **выполняет их только после подтверждения пользователя**.

Идея и архитектура вдохновлены проектом [ModernTerminal](https://github.com/CORD1ALCH1P/ModernTerminal).

## Статус

Проект развивается поэтапно, см. [docs/roadmap.md](docs/roadmap.md).

| Этап | Содержание | Статус |
|------|-----------|--------|
| 0 | Документация, роли, backlog | готово |
| 1 | Каркас backend, Ollama-провайдер, модуль безопасности команд | готово |
| 2 | Коннекторы SSH/Telnet, реестр сессий | запланировано |
| 3 | Цикл агента (tool-calling) и подтверждение команд | запланировано |
| 4 | Frontend (терминал + чат ассистента) | запланировано |
| 5 | Docker, CI/CD, мониторинг | запланировано |

## Документация

- [docs/requirements.md](docs/requirements.md) — требования, сценарии, метрики успеха
- [docs/architecture.md](docs/architecture.md) — архитектура и компоненты
- [docs/roles.md](docs/roles.md) — роли, зоны ответственности, RACI
- [docs/roadmap.md](docs/roadmap.md) — план по этапам
- [docs/board-tasks.md](docs/board-tasks.md) и [docs/board-tasks.csv](docs/board-tasks.csv) — задачи для Jira/Trello

## Быстрый старт (этап 1)

Нужен Python 3.11+ и запущенный локально Ollama (модель разворачивать не требуется для тестов).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example .env     # Linux/macOS: cp ../.env.example .env
uvicorn app.main:app --reload
pytest
```

API: `GET /api/health`, `GET|PUT /api/ai/settings`, `GET /api/ai/models`, `POST /api/safety/check`.

## Команда

| Роль | Участник |
|------|----------|
| ML + Data Engineer | Ярослав |
| DevOps + Backend | Всеволод |
| Product Owner / Аналитик | Андрей |
| Frontend / Визуализатор | Виталий |
| Тимлид / Scrum-мастер | Роман |
