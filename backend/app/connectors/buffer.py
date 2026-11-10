import re

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class OutputBuffer:
    """Кольцевой буфер последнего вывода терминала (без ANSI-последовательностей)."""

    def __init__(self, max_chars: int = 20000) -> None:
        self.max_chars = max_chars
        self._text = ""

    def append(self, data: str) -> None:
        clean = _ANSI.sub("", data).replace("\r\n", "\n").replace("\r", "")
        self._text = (self._text + clean)[-self.max_chars :]

    def tail(self, chars: int | None = None) -> str:
        if chars is None or chars >= len(self._text):
            return self._text
        return self._text[-chars:] if chars > 0 else ""

    def clear(self) -> None:
        self._text = ""
