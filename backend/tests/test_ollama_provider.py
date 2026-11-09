import httpx

from app.ai.base import ChatMessage
from app.ai.ollama_provider import OllamaProvider


def _provider(handler):
    return OllamaProvider(
        "http://ollama.test", "test-model", transport=httpx.MockTransport(handler)
    )


async def test_list_models():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "qwen3:8b"}, {"name": "llama3"}]})

    assert await _provider(handler).list_models() == ["qwen3:8b", "llama3"]


async def test_chat_returns_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "run_command", "arguments": {"command": "show vlan"}}}
                    ],
                }
            },
        )

    resp = await _provider(handler).chat([ChatMessage("user", "покажи vlan")])
    assert resp.message.tool_calls[0]["function"]["name"] == "run_command"
