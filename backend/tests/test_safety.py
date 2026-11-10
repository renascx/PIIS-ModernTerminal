import pytest

from app.ai.safety import Risk, assess, requires_confirmation


@pytest.mark.parametrize(
    "cmd",
    [
        "show vlan brief",
        "show running-config",
        "ping 10.0.0.1",
        "SHOW ip int brief",
        "show running-config | include vlan",
        "show run | section interface | exclude shutdown",
    ],
)
def test_read_only(cmd):
    a = assess(cmd)
    assert a.risk is Risk.READ_ONLY
    assert not a.needs_confirmation


@pytest.mark.parametrize(
    "cmd",
    ["vlan 20", "name USERS", "switchport mode access", "switchport port-security maximum 2"],
)
def test_config_needs_confirmation(cmd):
    a = assess(cmd)
    assert a.risk is Risk.CONFIG
    assert a.needs_confirmation


@pytest.mark.parametrize(
    "cmd", ["reload", "write erase", "erase startup-config", "no vlan 20", "shutdown", "no shutdown"]
)
def test_dangerous(cmd):
    assert assess(cmd).risk is Risk.DANGEROUS


@pytest.mark.parametrize(
    "cmd", ["show version; reload", "show version\nreload", "show run | reload", "vlan 20 | include x"]
)
def test_compound_command_not_read_only(cmd):
    assert assess(cmd).risk is not Risk.READ_ONLY


def test_empty_command():
    assert assess("   ").needs_confirmation


def test_requires_confirmation_modes():
    show = assess("show vlan")
    cfg = assess("vlan 20")
    danger = assess("reload")
    assert requires_confirmation(show, "confirm")
    assert not requires_confirmation(show, "readonly_auto")
    assert requires_confirmation(cfg, "readonly_auto")
    assert requires_confirmation(danger, "readonly_auto")
