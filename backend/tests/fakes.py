from app.ai.base import AIProvider, ChatMessage, ChatResponse
from app.connectors.base import Connector


class FakeConnector(Connector):
    protocol = "ssh"
    default_port = 22
    sent: list[str] = []

    def __init__(self, host, port, username=None, password=None):
        super().__init__(host, port, username, password)
        self._connected = False

    @property
    def connected(self):
        return self._connected

    async def connect(self):
        self._connected = True

    async def send(self, data):
        FakeConnector.sent.append(data)
        self.buffer.append(f"{data.strip()} -> ok\n")

    async def close(self):
        self._connected = False


class FakeProvider(AIProvider):
    """Отдаёт заранее заготовленные ответы по очереди."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def list_models(self):
        return ["fake"]

    async def chat(self, messages, tools=None):
        self.calls.append([m.content for m in messages])
        return ChatResponse(self.replies.pop(0))


def say(text):
    return ChatMessage("assistant", text)


def call(command):
    tool_call = {"function": {"name": "run_command", "arguments": {"command": command}}}
    return ChatMessage("assistant", "", [tool_call])
