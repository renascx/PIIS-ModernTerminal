from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения / файла .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout: float = 120.0
    approval_mode: str = "confirm"  # confirm | readonly_auto


class AISettings(BaseModel):
    """Изменяемые во время работы настройки ассистента."""

    ollama_url: str
    model: str
    approval_mode: str = "confirm"


settings = Settings()
