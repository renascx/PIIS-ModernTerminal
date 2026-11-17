from prometheus_client import Counter, Gauge, Histogram

COMMANDS = Counter(
    "piis_commands_total",
    "Команды из журнала аудита",
    ["risk", "decision", "source"],
)
HTTP_SECONDS = Histogram(
    "piis_http_request_seconds",
    "Время обработки HTTP-запросов",
    ["method", "path", "status"],
)
SESSIONS = Gauge("piis_sessions_active", "Открытые сессии с устройствами")
