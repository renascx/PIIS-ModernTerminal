import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..ai.agent import AgentError, AgentReply, agent
from ..audit import audit_log
from ..session_registry import registry

router = APIRouter(prefix="/api", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str


async def _call(coro) -> dict[str, object]:
    try:
        reply: AgentReply = await coro
    except AgentError as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Команда не найдена") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Ollama недоступен: {exc}") from exc
    return reply.info()


@router.post("/sessions/{session_id}/assistant")
async def chat(session_id: str, req: ChatRequest) -> dict[str, object]:
    session = registry.get(session_id)
    if session is None:
        raise HTTPException(404, "Сессия не найдена")
    return await _call(agent.chat(session, req.message))


@router.get("/sessions/{session_id}/pending")
async def list_pending(session_id: str) -> list[dict[str, str]]:
    return [p.info() for p in agent.pending_for(session_id)]


@router.post("/pending/{pending_id}/approve")
async def approve(pending_id: str) -> dict[str, object]:
    return await _call(agent.resolve(pending_id, True))


@router.post("/pending/{pending_id}/deny")
async def deny(pending_id: str) -> dict[str, object]:
    return await _call(agent.resolve(pending_id, False))


@router.get("/audit")
async def get_audit(limit: int = 100) -> list[dict[str, object]]:
    return audit_log.list(min(max(limit, 1), 1000))
