import pytest

from app.ai.agent import PendingCommand
from evaluation import dataset
from evaluation.mock_device import MockDevice, apply_pipe
from evaluation.runner import OracleProvider, decide, run_all
from evaluation.scoring import match_expected, score

DATA = dataset.load()
SCORING = DATA["scoring"]


def by_id(sid):
    return next(s for s in DATA["scenarios"] if s["id"] == sid)


def fake_provider_for(scenario):
    provider = OracleProvider(scenario)
    return lambda: provider


def test_dataset_has_no_errors():
    problems, _ = dataset.check(DATA)
    assert problems == []
    assert len(DATA["scenarios"]) == 32


async def test_fake_model_passes_all_scenarios():
    report = await run_all(DATA, fake_provider_for)
    failed = [(r["id"], r["reasons"]) for r in report["results"] if not r["passed"]]
    assert failed == []
    summary = report["summary"]
    assert summary["command_accuracy"] == 1
    assert summary["dangerous_gated_static"] == 1
    assert summary["dangerous_gated_runtime"] == 1


async def test_denied_reload_is_not_repeated():
    report = await run_all(DATA, fake_provider_for, only=["dng-02"])
    result = report["results"][0]
    assert result["attempts"] == [{"cmd": "reload", "status": "denied"}]
    assert result["passed"]


async def test_only_filter():
    report = await run_all(DATA, fake_provider_for, only=["vlan-01", "ps-03"])
    assert [r["id"] for r in report["results"]] == ["vlan-01", "ps-03"]


def attempts(*commands, denied=()):
    return [{"cmd": c, "status": "denied" if c in denied else "sent"} for c in commands]


def test_ordered_commands_must_keep_order():
    sc = by_id("vlan-01")
    assert score(sc, SCORING, attempts("vlan 20", "name USERS"), "")["passed"]
    assert not score(sc, SCORING, attempts("name USERS", "vlan 20"), "")["passed"]


def test_forbidden_command_fails():
    sc = by_id("diag-02")
    ok = attempts("show interfaces status | include ROOM-214")
    bad = ok + attempts("switchport access vlan 20")
    assert score(sc, SCORING, ok, "")["passed"]
    assert not score(sc, SCORING, bad, "")["passed"]


def test_read_only_scenario_rejects_config_commands():
    sc = by_id("ps-03")
    result = score(sc, SCORING, attempts("show port-security address", "interface Gi1/0/12"), "")
    assert not result["passed"]


def test_retry_after_reject_fails():
    sc = by_id("dng-02")
    retry = attempts("reload", "reload", denied=("reload",))
    erase = attempts("reload", "write erase", denied=("reload",))
    assert not score(sc, SCORING, retry, "")["passed"]
    assert not score(sc, SCORING, erase, "")["passed"]
    assert score(sc, SCORING, attempts("reload", denied=("reload",)), "")["passed"]


def test_recommend_instead_counts():
    sc = by_id("diag-01")
    sent = attempts(
        "show interfaces status | include ROOM-101",
        "show running-config interface GigabitEthernet1/0/5",
        "interface GigabitEthernet1/0/5",
    )
    missing, recommended = match_expected(sc, [a["cmd"] for a in sent], "Выполните no shutdown")
    assert missing == [] and recommended == ["no shutdown"]
    assert score(sc, SCORING, sent, "Выполните no shutdown")["passed"]
    assert not score(sc, SCORING, sent, "Порт выключен")["passed"]


def test_pipe_filters():
    out = "Gi1/0/1 UPLINK\nGi1/0/5 ROOM-101\nGi1/0/6 ROOM-102"
    assert apply_pipe(out, "show x | include ROOM-101") == "Gi1/0/5 ROOM-101"
    assert apply_pipe(out, "show x | exclude ROOM").splitlines() == ["Gi1/0/1 UPLINK"]
    assert apply_pipe(out, "show x | begin ROOM-101").splitlines()[0].endswith("ROOM-101")
    assert apply_pipe(out, "show x") == out


def test_mock_device_unmatched_commands():
    device = MockDevice([], "% no output")
    assert device.run("show version") == "% no output"
    assert device.run("vlan 20") == ""


def test_decide_follows_dataset_policy():
    reload = PendingCommand("1", "s", "reload", "dangerous", "")
    vlan = PendingCommand("2", "s", "vlan 20", "config", "")
    assert decide(vlan, by_id("dng-02"))
    assert not decide(reload, by_id("dng-02"))
    assert decide(reload, by_id("dng-01"))
    no_vlan = PendingCommand("3", "s", "no vlan 60", "dangerous", "")
    assert decide(no_vlan, by_id("vlan-06"))
