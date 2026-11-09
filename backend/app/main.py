import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .ai import safety
from .ai.ollama_provider import OllamaProvider
from .config import AISettings, settings

app = FastAPI(title="PIIS-ModernTerminal")

_ai_settings = AISettings(
    ollama_url=settings.ollama_url,
    model=settings.ollama_model,
    approval_mode=settings.approval_mode,
)


class SafetyRequest(BaseModel):
    commands: list[str]


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ai/settings", response_model=AISettings)
async def get_ai_settings() -> AISettings:
    return _ai_settings


@app.put("/api/ai/settings", response_model=AISettings)
async def put_ai_settings(new: AISettings) -> AISettings:
    if new.approval_mode not in ("confirm", "readonly_auto"):
        raise HTTPException(422, "approval_mode must be 'confirm' or 'readonly_auto'")
    global _ai_settings
    _ai_settings = new
    return _ai_settings


@app.get("/api/ai/models")
async def list_models() -> dict[str, list[str]]:
    provider = OllamaProvider(
        _ai_settings.ollama_url, _ai_settings.model, settings.ollama_timeout
    )
    try:
        return {"models": await provider.list_models()}
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Ollama недоступен: {exc}") from exc
    finally:
        await provider.aclose()


@app.post("/api/safety/check")
async def check_commands(req: SafetyRequest) -> list[dict[str, object]]:
    return [
        {
            "command": a.command,
            "risk": a.risk.value,
            "reason": a.reason,
            "needs_confirmation": a.needs_confirmation,
        }
        for a in safety.assess_many(req.commands)
    ]
