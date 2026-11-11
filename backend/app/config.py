from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

APPROVAL_MODES = ("confirm", "readonly_auto")


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения / файла .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout: float = 120.0
    approval_mode: str = "confirm"  # confirm | readonly_auto
    connect_timeout: float = 10.0
    output_buffer_chars: int = 20000
    audit_db: str = "audit.db"
    command_wait: float = 1.0
    agent_max_steps: int = 6


class AISettings(BaseModel):
    """Изменяемые во время работы настройки ассистента."""

    ollama_url: str
    model: str
    approval_mode: str = "confirm"


settings = Settings()

# Текущие настройки ассистента; изменяются через PUT /api/ai/settings
# и читаются в других модулях (например, при подтверждении команд).
ai_settings = AISettings(
    ollama_url=settings.ollama_url,
    model=settings.ollama_model,
    approval_mode=settings.approval_mode,
)
