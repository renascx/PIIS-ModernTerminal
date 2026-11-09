from typing import Any

import httpx

from .base import AIProvider, ChatMessage, ChatResponse


class OllamaProvider(AIProvider):
    """Клиент локального сервера Ollama (REST API)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout, transport=transport
        )

    async def list_models(self) -> list[str]:
        resp = await self._client.get("/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": m.role, "content": m.content, **(
                    {"tool_calls": m.tool_calls} if m.tool_calls else {}
                )}
                for m in messages
            ],
        }
        if tools:
            payload["tools"] = tools
        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        msg = resp.json().get("message", {})
        return ChatResponse(
            message=ChatMessage(
                role=msg.get("role", "assistant"),
                content=msg.get("content", ""),
                tool_calls=msg.get("tool_calls") or [],
            )
        )

    async def aclose(self) -> None:
        await self._client.aclose()
