import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from .ai import safety
from .ai.ollama_provider import OllamaProvider
from .config import APPROVAL_MODES, AISettings, ai_settings, settings
from .metrics import HTTP_SECONDS, SESSIONS
from .routes import assistant, sessions, terminal
from .session_registry import registry
from .static import mount_static


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await registry.close_all()


app = FastAPI(title="PIIS-ModernTerminal", lifespan=lifespan)
app.include_router(sessions.router)
app.include_router(assistant.router)
app.include_router(terminal.router)
SESSIONS.set_function(lambda: len(registry.list()))


@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    HTTP_SECONDS.labels(request.method, path, str(response.status_code)).observe(
        time.perf_counter() - start
    )
    return response


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class SafetyRequest(BaseModel):
    commands: list[str]


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ai/settings", response_model=AISettings)
async def get_ai_settings() -> AISettings:
    return ai_settings


@app.put("/api/ai/settings", response_model=AISettings)
async def put_ai_settings(new: AISettings) -> AISettings:
    if new.approval_mode not in APPROVAL_MODES:
        raise HTTPException(422, f"approval_mode must be one of {APPROVAL_MODES}")
    ai_settings.ollama_url = new.ollama_url
    ai_settings.model = new.model
    ai_settings.approval_mode = new.approval_mode
    return ai_settings


@app.get("/api/ai/models")
async def list_models() -> dict[str, list[str]]:
    provider = OllamaProvider(ai_settings.ollama_url, ai_settings.model, settings.ollama_timeout)
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
            "needs_confirmation": safety.requires_confirmation(a, ai_settings.approval_mode),
        }
        for a in safety.assess_many(req.commands)
    ]


mount_static(app, settings.static_dir)
