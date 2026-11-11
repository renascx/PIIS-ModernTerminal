from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..ai import safety
from ..ai.agent import agent
from ..audit import audit_log
from ..config import ai_settings
from ..connectors.base import ConnectorError
from ..session_registry import Session, registry

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    protocol: str = Field(pattern="^(ssh|telnet)$")
    host: str = Field(min_length=1)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None


class CommandRequest(BaseModel):
    command: str
    confirmed: bool = False


def _get(session_id: str) -> Session:
    session = registry.get(session_id)
    if session is None:
        raise HTTPException(404, "Сессия не найдена")
    return session


@router.post("", status_code=201)
async def create_session(req: SessionCreate) -> dict[str, object]:
    try:
        session = await registry.create(
            req.protocol, req.host, req.port, req.username, req.password
        )
    except ConnectorError as exc:
        raise HTTPException(502, str(exc)) from exc
    return session.info()


@router.get("")
async def list_sessions() -> list[dict[str, object]]:
    return [s.info() for s in registry.list()]


@router.delete("/{session_id}", status_code=204)
async def close_session(session_id: str) -> None:
    if not await registry.close(session_id):
        raise HTTPException(404, "Сессия не найдена")
    agent.forget(session_id)


@router.get("/{session_id}/output")
async def get_output(session_id: str, chars: int = 4000) -> dict[str, str]:
    return {"output": _get(session_id).connector.buffer.tail(chars)}


@router.post("/{session_id}/commands")
async def run_command(session_id: str, req: CommandRequest) -> dict[str, object]:
    """Отправляет команду в сессию. Без confirmed=true выполняются только те команды,
    для которых подтверждение не требуется в текущем режиме."""
    session = _get(session_id)
    assessment = safety.assess(req.command)
    if safety.requires_confirmation(assessment, ai_settings.approval_mode) and not req.confirmed:
        raise HTTPException(
            409,
            {
                "message": "Требуется подтверждение пользователя",
                "risk": assessment.risk.value,
                "reason": assessment.reason,
            },
        )
    try:
        await session.connector.send_line(req.command)
    except ConnectorError as exc:
        raise HTTPException(502, str(exc)) from exc
    decision = "confirmed" if req.confirmed else "auto"
    audit_log.add(session_id, req.command, assessment.risk.value, decision, "manual")
    return {"sent": req.command, "risk": assessment.risk.value}
