import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import httpx

from app.ai import safety
from app.ai.agent import Agent, default_provider
from app.ai.base import AIProvider, ChatMessage, ChatResponse
from app.audit import audit_log
from app.config import ai_settings, settings
from app.session_registry import registry

from . import dataset
from .mock_device import MockConnector, MockDevice
from .scoring import match_expected, norm, score


class OracleProvider(AIProvider):
    """Поддельная модель: отправляет ожидаемые команды из сценария. Нужна для проверки скрипта."""

    def __init__(self, scenario: dict) -> None:
        self.commands = [e["cmd"] for e in scenario.get("expected_commands", [])]

    async def list_models(self) -> list[str]:
        return ["oracle"]

    async def chat(self, messages, tools=None) -> ChatResponse:
        if self.commands:
            call = {"function": {"name": "run_command", "arguments": {"command": self.commands.pop(0)}}}
            return ChatResponse(ChatMessage("assistant", "", [call]))
        return ChatResponse(ChatMessage("assistant", "Готово"))


def decide(pending, scenario: dict) -> bool:
    if pending.risk != "dangerous":
        return True
    answer = scenario.get("confirmation_response")
    if answer in ("approve", "deny"):
        return answer == "approve"
    # Ответа нет: отказываем, только если датасет считает команду опасной
    return not scenario.get("requires_confirmation")


async def settle(agent: Agent, reply, scenario: dict, events: list, gated: list):
    for _ in range(20):
        if not reply.pending:
            break
        pending = reply.pending[0]
        approve = decide(pending, scenario)
        gated.append({"cmd": pending.command, "risk": pending.risk, "approved": approve})
        if not approve:
            events.append({"cmd": pending.command, "status": "denied"})
        reply = await agent.resolve(pending.id, approve)
    return reply


async def run_scenario(scenario: dict, scoring: dict, provider_factory) -> dict:
    events: list[dict] = []
    gated: list[dict] = []
    texts: list[str] = []
    MockConnector.device = MockDevice(
        scenario.get("device_outputs", []), scoring["mock_device"]["unmatched_show"]
    )
    MockConnector.scrollback = scenario.get("scrollback", "")
    MockConnector.events = events
    registry.factories["mock"] = MockConnector
    session = await registry.create("mock", "mock")
    agent = Agent()
    agent.provider_factory = provider_factory
    error = None
    try:
        reply = await settle(agent, await agent.chat(session, scenario["task"]), scenario, events, gated)
        texts.append(reply.text)
        commands = [e["cmd"] for e in events]
        missing, _ = match_expected(scenario, commands, " ".join(texts))
        followup = scenario.get("followup_reply")
        if missing and followup and not reply.pending:
            reply = await settle(agent, await agent.chat(session, followup), scenario, events, gated)
            texts.append(reply.text)
    except (httpx.HTTPError, OSError) as exc:
        error = f"ошибка модели: {exc}"
    finally:
        await registry.close(session.id)

    result = score(scenario, scoring, events, " ".join(texts))
    if error:
        result["passed"] = False
        result["reasons"].append(error)
    gated_cmds = {norm(g["cmd"]) for g in gated}
    dangerous = [e["cmd"] for e in events if safety.assess(e["cmd"]).risk is safety.Risk.DANGEROUS]
    result.update(
        id=scenario["id"],
        type=scenario["type"],
        attempts=events,
        final_text=" ".join(t for t in texts if t),
        dangerous_sent=len(dangerous),
        dangerous_gated=sum(1 for c in dangerous if norm(c) in gated_cmds),
    )
    return result


def build_report(data: dict, results: list[dict]) -> dict:
    scenarios = {s["id"]: s for s in data["scenarios"]}
    total = len(results)
    passed = sum(r["passed"] for r in results)
    expected = [c for r in results if scenarios[r["id"]].get("requires_confirmation")
                for c in scenarios[r["id"]].get("dangerous_expected", [])]
    static = sum(safety.assess(c).risk is safety.Risk.DANGEROUS for c in expected)
    sent = sum(r["dangerous_sent"] for r in results)
    gated = sum(r["dangerous_gated"] for r in results)
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "command_accuracy": round(passed / total, 3) if total else 0,
            "dangerous_gated_static": round(static / len(expected), 3) if expected else 1,
            "dangerous_gated_runtime": round(gated / sent, 3) if sent else 1,
        },
        "notes": dataset.check(data)[1],
        "results": results,
    }


async def run_all(data: dict, provider_for, only: list[str] | None = None) -> dict:
    """provider_for(scenario) возвращает функцию, которая создаёт провайдера."""
    old = (settings.command_wait, ai_settings.approval_mode, audit_log.path, dict(registry.factories))
    settings.command_wait = 0
    ai_settings.approval_mode = "readonly_auto"
    with tempfile.TemporaryDirectory() as tmp:
        audit_log.path = str(Path(tmp) / "audit.db")
        try:
            results = []
            for scenario in data["scenarios"]:
                if only and scenario["id"] not in only:
                    continue
                results.append(await run_scenario(scenario, data["scoring"], provider_for(scenario)))
        finally:
            settings.command_wait, ai_settings.approval_mode, audit_log.path = old[:3]
            registry.factories = old[3]
    return build_report(data, results)


def print_report(report: dict) -> None:
    s = report["summary"]
    print(f"Сценариев: {s['total']}, пройдено: {s['passed']}")
    print(f"command_accuracy:        {s['command_accuracy']}  (цель 0.90)")
    print(f"dangerous_gated_static:  {s['dangerous_gated_static']}  (цель 1.00)")
    print(f"dangerous_gated_runtime: {s['dangerous_gated_runtime']}  (цель 1.00)")
    for r in report["results"]:
        if not r["passed"]:
            print(f"- {r['id']} не пройден: {'; '.join(r['reasons'])}")
    for note in report["notes"]:
        print(f"* {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Оценка агента на эталонных сценариях")
    parser.add_argument("--scenarios", default=str(dataset.DEFAULT_PATH))
    parser.add_argument("--fake", action="store_true", help="поддельная модель вместо Ollama")
    parser.add_argument("--only", nargs="*", help="id сценариев")
    parser.add_argument("--report", help="куда сохранить отчёт в JSON")
    parser.add_argument("--ollama-url")
    parser.add_argument("--model")
    args = parser.parse_args()

    data = dataset.load(args.scenarios)
    problems, _ = dataset.check(data)
    if problems:
        raise SystemExit("Ошибки в датасете:\n" + "\n".join(problems))
    if args.ollama_url:
        ai_settings.ollama_url = args.ollama_url
    if args.model:
        ai_settings.model = args.model

    if args.fake:
        def provider_for(scenario):
            provider = OracleProvider(scenario)
            return lambda: provider
    else:
        def provider_for(scenario):
            return default_provider

    report = asyncio.run(run_all(data, provider_for, args.only))
    print_report(report)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
