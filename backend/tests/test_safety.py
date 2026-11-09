import pytest

from app.ai.safety import Risk, assess


@pytest.mark.parametrize(
    "cmd", ["show vlan brief", "show running-config", "ping 10.0.0.1", "SHOW ip int brief"]
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


def test_compound_command_not_read_only():
    assert assess("show version; reload").risk is Risk.DANGEROUS


def test_empty_command():
    assert assess("   ").needs_confirmation
