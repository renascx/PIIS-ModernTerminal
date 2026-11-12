import re

from app.connectors.base import Connector

SHOW = re.compile(r"^\s*sh(?:o(?:w)?)?\b", re.I)


def apply_pipe(output: str, command: str) -> str:
    if "|" not in command:
        return output
    parts = command.partition("|")[2].strip().split(None, 1)
    if len(parts) < 2:
        return output
    kind, arg = parts[0].lower(), parts[1].strip()
    try:
        pattern = re.compile(arg, re.I)
    except re.error:
        pattern = re.compile(re.escape(arg), re.I)
    lines = output.splitlines()
    if kind in ("include", "inc", "i", "section", "sec"):
        lines = [x for x in lines if pattern.search(x)]
    elif kind in ("exclude", "exc", "e"):
        lines = [x for x in lines if not pattern.search(x)]
    elif kind in ("begin", "beg", "b"):
        start = next((i for i, x in enumerate(lines) if pattern.search(x)), None)
        lines = lines[start:] if start is not None else []
    return "\n".join(lines)


class MockDevice:
    def __init__(self, outputs: list[dict], unmatched_show: str) -> None:
        self.outputs = [(re.compile(o["match"], re.I), o["output"]) for o in outputs]
        self.unmatched_show = unmatched_show

    def run(self, command: str) -> str:
        for pattern, output in self.outputs:
            if pattern.search(command):
                return apply_pipe(output, command)
        return self.unmatched_show if SHOW.search(command) else ""


class MockConnector(Connector):
    protocol = "mock"
    default_port = 0

    # Заполняется раннером перед каждым сценарием
    device: MockDevice | None = None
    scrollback: str = ""
    events: list[dict] | None = None

    def __init__(self, host, port, username=None, password=None):
        super().__init__(host, port, username, password)
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True
        if self.scrollback:
            self.buffer.append(self.scrollback + "\n")

    async def send(self, data: str) -> None:
        command = data.strip()
        if self.events is not None:
            self.events.append({"cmd": command, "status": "sent"})
        output = self.device.run(command) if self.device else ""
        self.buffer.append(f"{output}\n" if output else "")

    async def close(self) -> None:
        self._connected = False
