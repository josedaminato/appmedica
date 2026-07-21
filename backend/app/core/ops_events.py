"""Registro en memoria de eventos operativos para diagnóstico rápido del SaaS.

Pensado para el panel /interno: ver fallas recientes (SMTP, 500, etc.) sin SSH.
Se pierde al reiniciar el contenedor — es intencional (liviano, sin DB extra).
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]

_MAX_EVENTS = 100
_lock = threading.Lock()
_events: deque[OpsEvent] = deque(maxlen=_MAX_EVENTS)


@dataclass(frozen=True)
class OpsEvent:
    id: str
    created_at: str
    severity: Severity
    source: str
    code: str
    message: str
    path: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_event(
    *,
    severity: Severity,
    source: str,
    code: str,
    message: str,
    path: str | None = None,
    detail: str | None = None,
) -> OpsEvent:
    event = OpsEvent(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        severity=severity,
        source=source,
        code=code,
        message=message[:500],
        path=path,
        detail=(detail[:1000] if detail else None),
    )
    with _lock:
        _events.appendleft(event)
    return event


def list_events(*, limit: int = 50, severity: Severity | None = None) -> list[OpsEvent]:
    with _lock:
        items = list(_events)
    if severity:
        items = [e for e in items if e.severity == severity]
    return items[: max(1, min(limit, _MAX_EVENTS))]


def clear_events() -> None:
    with _lock:
        _events.clear()


def count_by_severity() -> dict[str, int]:
    with _lock:
        items = list(_events)
    return {
        "error": sum(1 for e in items if e.severity == "error"),
        "warning": sum(1 for e in items if e.severity == "warning"),
        "info": sum(1 for e in items if e.severity == "info"),
        "total": len(items),
    }
