import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..connectors.base import ConnectorError
from ..session_registry import registry

router = APIRouter(tags=["terminal"])


@router.websocket("/api/sessions/{session_id}/terminal")
async def terminal(ws: WebSocket, session_id: str) -> None:
    session = registry.get(session_id)
    if session is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    buffer = session.connector.buffer
    queue: asyncio.Queue[str] = asyncio.Queue()
    push = queue.put_nowait
    history = buffer.tail()
    buffer.listeners.append(push)

    async def sender() -> None:
        while True:
            await ws.send_text(await queue.get())

    sender_task = asyncio.create_task(sender())
    try:
        if history:
            await ws.send_text(history)
        while True:
            # Это ввод самого пользователя, поэтому проверка команд здесь не нужна
            await session.connector.send(await ws.receive_text())
    except WebSocketDisconnect:
        pass
    except ConnectorError:
        await ws.close(code=1011)
    finally:
        sender_task.cancel()
        buffer.listeners.remove(push)
