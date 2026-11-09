from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # system | user | assistant | tool
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ChatResponse:
    message: ChatMessage


class AIProvider(ABC):
    """Провайдер LLM. Цикл агента зависит только от этого интерфейса."""

    @abstractmethod
    async def list_models(self) -> list[str]: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse: ...
