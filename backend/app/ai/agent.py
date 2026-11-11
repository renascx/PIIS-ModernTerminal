import asyncio
import json
import uuid
from dataclasses import dataclass, field

from ..audit import audit_log
from ..config import ai_settings, settings
from ..connectors.base import ConnectorError
from ..session_registry import Session, registry
from . import safety
from .base import AIProvider, ChatMessage
from .ollama_provider import OllamaProvider
from .prompts import SYSTEM_PROMPT
from .tools import RUN_COMMAND_TOOL


class AgentError(Exception):
    pass


@dataclass
class PendingCommand:
    id: str
    session_id: str
    command: str
    risk: str
    reason: str

    def info(self) -> dict[str, str]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "command": self.command,
            "risk": self.risk,
            "reason": self.reason,
        }


@dataclass
class AgentReply:
    text: str
    pending: list[PendingCommand] = field(default_factory=list)

    def info(self) -> dict[str, object]:
        return {"text": self.text, "pending": [p.info() for p in self.pending]}


def default_provider() -> AIProvider:
    return OllamaProvider(ai_settings.ollama_url, ai_settings.model, settings.ollama_timeout)


def get_command(call: dict) -> str | None:
    # Ollama отдаёт аргументы то словарём, то строкой с JSON
    args = call.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return None
    command = args.get("command") if isinstance(args, dict) else None
    if isinstance(command, str) and command.strip():
        return command.strip()
    return None


class Agent:
    def __init__(self) -> None:
        self.provider_factory = default_provider
        self.history: dict[str, list[ChatMessage]] = {}
        self.pending: dict[str, PendingCommand] = {}

    def _messages(self, session_id: str) -> list[ChatMessage]:
        if session_id not in self.history:
            self.history[session_id] = [ChatMessage("system", SYSTEM_PROMPT)]
        return self.history[session_id]

    def pending_for(self, session_id: str) -> list[PendingCommand]:
        return [p for p in self.pending.values() if p.session_id == session_id]

    def forget(self, session_id: str) -> None:
        self.history.pop(session_id, None)
        for p in self.pending_for(session_id):
            del self.pending[p.id]

    async def chat(self, session: Session, user_text: str) -> AgentReply:
        if self.pending_for(session.id):
            raise AgentError("Сначала подтвердите или отклоните команды")
        output = session.connector.buffer.tail(2000)
        if output:
            user_text += f"\n\nПоследний вывод терминала:\n{output}"
        self._messages(session.id).append(ChatMessage("user", user_text))
        return await self._run(session)

    async def resolve(self, pending_id: str, approve: bool) -> AgentReply:
        pending = self.pending.get(pending_id)
        if pending is None:
            raise KeyError(pending_id)
        session = registry.get(pending.session_id)
        if session is None:
            self.forget(pending.session_id)
            raise AgentError("Сессия уже закрыта")
        del self.pending[pending_id]
        messages = self._messages(session.id)
        if approve:
            result = await self._execute(session, pending.command)
            audit_log.add(session.id, pending.command, pending.risk, "approved", "assistant")
            messages.append(
                ChatMessage("user", f"Я подтвердил команду {pending.command}. Вывод:\n{result}")
            )
        else:
            audit_log.add(session.id, pending.command, pending.risk, "denied", "assistant")
            messages.append(ChatMessage("user", f"Я отклонил команду {pending.command}"))
        left = self.pending_for(session.id)
        if left:
            return AgentReply("Остались неподтверждённые команды", left)
        return await self._run(session)

    async def _execute(self, session: Session, command: str) -> str:
        buffer = session.connector.buffer
        mark = buffer.mark()
        try:
            await session.connector.send_line(command)
        except ConnectorError as exc:
            return f"Ошибка: {exc}"
        await asyncio.sleep(settings.command_wait)
        return buffer.since(mark) or "(вывода нет)"

    async def _run(self, session: Session) -> AgentReply:
        provider = self.provider_factory()
        messages = self._messages(session.id)
        try:
            for _ in range(settings.agent_max_steps):
                reply = (await provider.chat(messages, [RUN_COMMAND_TOOL])).message
                messages.append(reply)
                if not reply.tool_calls:
                    return AgentReply(reply.content)
                waiting = await self._handle_calls(session, reply.tool_calls, messages)
                if waiting:
                    return AgentReply(reply.content, waiting)
        finally:
            await provider.aclose()
        return AgentReply("Достигнут лимит шагов, остановился")

    async def _handle_calls(
        self, session: Session, calls: list[dict], messages: list[ChatMessage]
    ) -> list[PendingCommand]:
        waiting = []
        for call in calls:
            command = get_command(call)
            if command is None:
                messages.append(ChatMessage("tool", "Ошибка: команда не указана"))
                continue
            assessment = safety.assess(command)
            if safety.requires_confirmation(assessment, ai_settings.approval_mode):
                pending = PendingCommand(
                    uuid.uuid4().hex, session.id, command,
                    assessment.risk.value, assessment.reason,
                )
                self.pending[pending.id] = pending
                waiting.append(pending)
                messages.append(ChatMessage("tool", "Команда ждёт подтверждения пользователя"))
                continue
            result = await self._execute(session, command)
            audit_log.add(session.id, command, assessment.risk.value, "auto", "assistant")
            messages.append(ChatMessage("tool", result))
        return waiting


agent = Agent()
