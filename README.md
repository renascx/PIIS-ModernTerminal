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
| 3 | Цикл агента, подтверждение команд, журнал аудита, 32 эталонных сценария, скрипт оценки | готово |
| 4 | WebSocket терминала, frontend (терминал, чат, подтверждение, журнал) | готово (статистика команд в Grafana) |
| 5 | Docker, CI/CD, мониторинг, раздача frontend | готово, стенд запущен в Docker, CI проходит |
| 6 | Прогон оценки на реальной модели, метрики, презентация, защита | оценка выполнена (0.781), тест на реальном коммутаторе пройден; впереди приёмка и защита |

## Документация

- [docs/requirements.md](docs/requirements.md) — требования, сценарии, метрики успеха
- [docs/architecture.md](docs/architecture.md) — архитектура и компоненты
- [docs/roles.md](docs/roles.md) — роли, зоны ответственности, RACI
- [docs/roadmap.md](docs/roadmap.md) — план по этапам
- [docs/board-tasks.md](docs/board-tasks.md) и [docs/board-tasks.csv](docs/board-tasks.csv) — задачи для Jira/Trello
- [docs/model-evaluation-qwen3-8b.md](docs/model-evaluation-qwen3-8b.md) — результаты оценки модели
- [docs/stage-acceptance.md](docs/stage-acceptance.md) — приёмка этапов

## Быстрый старт

Нужны Python 3.11+, Node.js 20+ и локально запущенный Ollama (для тестов он не нужен).

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Linux/macOS: cp .env.example .env
uvicorn app.main:app --reload
pytest
```

Frontend (в другом терминале, backend должен работать на порту 8000):

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
npm test
```

Всё вместе в Docker (порты открыты только на localhost, Ollama берётся с хоста):

```bash
cd backend
docker compose up --build
```

- интерфейс и API: http://localhost:8000 (собранный frontend раздаёт сам backend);
- Prometheus: http://localhost:9090, метрики backend: `/metrics`;
- Grafana: http://localhost:3000, логин `admin`, пароль из переменной `GRAFANA_PASSWORD`.

Сборка образа и compose проверены на реальном Docker (Docker Desktop, Windows): backend, Prometheus и Grafana поднимаются, backend видит Ollama на хосте.

Тесты и сборка проверяются автоматически в GitHub Actions (`.github/workflows/ci.yml`):

## API

| Метод и путь | Назначение |
|--------------|-----------|
| `GET /api/health` | проверка работы |
| `GET /metrics` | метрики для Prometheus |
| `GET`, `PUT /api/ai/settings` | URL Ollama, модель, режим подтверждения |
| `GET /api/ai/models` | список моделей Ollama |
| `POST /api/safety/check` | оценка риска списка команд |
| `POST /api/sessions` | подключиться к устройству по SSH или Telnet |
| `GET /api/sessions`, `DELETE /api/sessions/{id}` | список и закрытие сессий |
| `GET /api/sessions/{id}/output` | последний вывод терминала |
| `WS /api/sessions/{id}/terminal` | терминал в браузере: ввод и вывод в реальном времени |
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

Результат на локальной модели `qwen3:8b` (температура 0, контекст 8192): `command_accuracy` 0.781
(25 из 32), `dangerous_gated` 1.00. Подробности в
[docs/model-evaluation-qwen3-8b.md](docs/model-evaluation-qwen3-8b.md). Подключение, диалог с
ассистентом и выполнение команд с подтверждением проверены на реальном коммутаторе.

## Команда

| Роль | Участник |
|------|----------|
| ML + Data Engineer | Ярослав |
| DevOps + Backend | Всеволод |
| Frontend / Визуализатор | Виталий |
| Тимлид + Аналитик | Роман |
