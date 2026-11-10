from app.connectors.buffer import OutputBuffer


def test_strips_ansi_and_cr():
    buf = OutputBuffer()
    buf.append("\x1b[1mSwitch#\x1b[0m show vlan\r\n")
    assert buf.tail() == "Switch# show vlan\n"


def test_keeps_only_last_chars():
    buf = OutputBuffer(max_chars=10)
    buf.append("a" * 8)
    buf.append("b" * 8)
    assert buf.tail() == "aabbbbbbbb"


def test_tail_limit_and_clear():
    buf = OutputBuffer()
    buf.append("0123456789")
    assert buf.tail(3) == "789"
    assert buf.tail(0) == ""
    buf.clear()
    assert buf.tail() == ""
