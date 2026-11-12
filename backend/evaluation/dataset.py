import json
import re
from pathlib import Path

from app.ai import safety

DEFAULT_PATH = Path(__file__).with_name("scenarios.json")
REQUIRED = ("id", "type", "task", "expected_commands", "read_only")


def load(path: Path | str = DEFAULT_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def optional_patterns(scenario: dict) -> list[str]:
    result = []
    for item in scenario.get("optional", []):
        result.append(item["re"] if isinstance(item, dict) else item)
    return result


def check(data: dict) -> tuple[list[str], list[str]]:
    """Возвращает (ошибки, замечания). Ошибки — это сломанный датасет."""
    problems, notes = [], []
    seen = set()
    for sc in data["scenarios"]:
        sid = sc.get("id", "?")
        if sid in seen:
            problems.append(f"{sid}: id повторяется")
        seen.add(sid)
        for key in REQUIRED:
            if key not in sc:
                problems.append(f"{sid}: нет поля {key}")
        for expected in sc.get("expected_commands", []):
            try:
                ok = re.search(expected["re"], expected["cmd"], re.I)
            except re.error as exc:
                problems.append(f"{sid}: плохое выражение {expected['re']!r}: {exc}")
                continue
            if not ok:
                problems.append(f"{sid}: команда {expected['cmd']!r} не подходит под своё выражение")
        patterns = list(sc.get("forbidden", [])) + list(sc.get("forbidden_after_reject", []))
        patterns += optional_patterns(sc) + [d["match"] for d in sc.get("device_outputs", [])]
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                problems.append(f"{sid}: плохое выражение {pattern!r}: {exc}")
        dangerous = {c.lower() for c in sc.get("dangerous_expected", [])}
        for cmd in sc.get("dangerous_expected", []):
            if safety.assess(cmd).risk is not safety.Risk.DANGEROUS:
                problems.append(f"{sid}: safety не считает опасной команду {cmd!r}")
        for expected in sc.get("expected_commands", []):
            cmd = expected["cmd"]
            if cmd.lower() not in dangerous and safety.assess(cmd).risk is safety.Risk.DANGEROUS:
                notes.append(f"{sid}: safety строже датасета, команда {cmd!r} опасная")
    return problems, notes
