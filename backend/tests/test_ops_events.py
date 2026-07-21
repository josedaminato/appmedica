from app.core.ops_events import clear_events, count_by_severity, list_events, record_event


def test_ops_events_ring_buffer():
    clear_events()
    record_event(severity="info", source="test", code="A", message="ok")
    record_event(severity="error", source="email", code="SMTP", message="falló envío")
    counts = count_by_severity()
    assert counts["error"] == 1
    assert counts["info"] == 1
    errors = list_events(severity="error")
    assert len(errors) == 1
    assert errors[0].code == "SMTP"
    clear_events()
