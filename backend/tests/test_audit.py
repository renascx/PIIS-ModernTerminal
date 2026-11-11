from app.audit import AuditLog
from app.connectors.buffer import OutputBuffer


def test_audit_returns_newest_first(tmp_path):
    log = AuditLog(str(tmp_path / "a.db"))
    log.add("s1", "show vlan", "read_only", "auto", "assistant")
    log.add("s1", "vlan 20", "config", "approved", "assistant")
    rows = log.list()
    assert [r["command"] for r in rows] == ["vlan 20", "show vlan"]
    assert rows[0]["decision"] == "approved"
    assert len(log.list(limit=1)) == 1


def test_buffer_since_mark():
    buf = OutputBuffer()
    buf.append("old\n")
    mark = buf.mark()
    assert buf.since(mark) == ""
    buf.append("new\n")
    assert buf.since(mark) == "new\n"
