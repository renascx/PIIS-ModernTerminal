# Архитектура

```
Браузер (React + xterm.js)
   │  REST / WebSocket
FastAPI backend
   ├─ api/            маршруты (здоровье, настройки ИИ, безопасность, сессии)
   ├─ ai/
   │   ├─ base.py             интерфейс AIProvider
   │   ├─ ollama_provider.py  клиент Ollama (/api/chat, /api/tags)
   │   ├─ safety.py           оценка риска команд
   │   └─ loop.py             цикл tool-calling (этап 3)
   ├─ connectors/     SSH / Telnet (этап 2)
   └─ session_registry.py  связь вкладки с коннектором (этап 2)
   │
Ollama (локально, http://localhost:11434)
```

## Принципы
- Провайдер ИИ подменяемый: цикл агента зависит только от `AIProvider`.
- Каждая команда проходит через `safety.assess` до выполнения.
- По умолчанию режим «подтверждать всё»; автоисполнение — только для read-only (`show ...`).
- История чата хранится в памяти, журнал аудита — в БД (этап 3).
