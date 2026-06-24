#!/usr/bin/env python3
"""Prueba completa de AppMedica en produccion (API + endpoints publicos)."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("API_BASE_URL", "https://daminatoweb.com/api/v1")
TIMEOUT = 20
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "OK" if ok else "FAIL"
    print(f"{status:4} {name}" + (f" — {detail}" if detail else ""))


def req(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
            raw = resp.read().decode()
            return (json.loads(raw) if raw else {}), resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw), e.code
        except json.JSONDecodeError:
            return {"error": raw}, e.code


def main() -> int:
    print(f"=== Prueba produccion AppMedica ===\nAPI: {BASE}\n")

    # --- Publicos ---
    h, code = req("GET", "/health")
    record("Health + DB", code == 200 and h.get("database") == "ok", str(h))

    docs, code = req("GET", "/docs")
    # /docs is on backend root not /api/v1 - skip

    email = f"qa-{uuid.uuid4().hex[:10]}@daminatoweb-test.com"
    password = "TestQA2026!x"

    reg, code = req(
        "POST",
        "/auth/register",
        {
            "organization_name": "QA Consultorio Test",
            "full_name": "Usuario QA",
            "email": email,
            "password": password,
        },
    )
    record("Registro publico", code in (200, 201) and "access_token" in reg, f"{code}")

    if code >= 400:
        print("\nNo se pudo registrar usuario de prueba. Abortando flujo autenticado.")
        return 1

    token = reg["access_token"]

    login, code = req("POST", "/auth/login", {"email": email, "password": password})
    record("Login", code == 200 and "access_token" in login, f"{code}")
    token = login.get("access_token", token)

    fp, code = req("POST", "/auth/forgot-password", {"email": email})
    record("Forgot password", code == 200, f"{code} {fp}")

    dash, code = req("GET", "/dashboard/summary", token=token)
    record("Dashboard", code == 200, f"{code}")

    ins, code = req(
        "POST",
        "/health-insurances",
        {"name": f"OSDE QA {uuid.uuid4().hex[:4]}", "coverage_percent": 80, "estimated_payment_days": 30},
        token,
    )
    record("Crear obra social", code in (200, 201), f"{code}")
    insurance_id = ins.get("id")

    pat, code = req(
        "POST",
        "/patients",
        {
            "first_name": "Juan",
            "last_name": "Paciente QA",
            "dni": str(30000000 + int(uuid.uuid4().int % 9999999)),
            "phone": "2615551234",
            "health_insurance_id": insurance_id,
        },
        token,
    )
    record("Crear paciente", code in (200, 201), f"{code}")
    patient_id = pat.get("id")

    patients, code = req("GET", "/patients?page=1&page_size=10", token=token)
    record("Listar pacientes", code == 200 and patients.get("total", 0) >= 1, f"total={patients.get('total')}")

    start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    appt, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "expected_amount": 15000,
            "attention_type": "private",
        },
        token,
    )
    record("Crear turno", code in (200, 201), f"{code}")
    aid = appt.get("id")

    if aid:
        for step, path in [
            ("Confirmar turno", f"/appointments/{aid}/confirm"),
            ("Marcar asistio", f"/appointments/{aid}/attend"),
        ]:
            _, c = req("POST", path, token=token)
            record(step, c < 300, str(c))

        closed, c = req(
            "POST",
            f"/appointments/{aid}/close",
            {"closure_type": "paid", "amount": 15000, "method": "cash"},
            token,
        )
        record("Cerrar y cobrar", c < 300 and closed.get("closure_status") == "paid", closed.get("closure_status", c))

    agenda, code = req("GET", f"/appointments?date={start.date().isoformat()}&view=day", token=token)
    record("Agenda del dia", code == 200, f"{len(agenda) if isinstance(agenda, list) else 'n/a'} turnos")

    pays, code = req("GET", "/payments/summary", token=token)
    record("Resumen pagos", code == 200, f"{code}")

    reports, code = req("GET", "/reports/monthly?year=2026&month=6", token=token)
    record("Reporte mensual", code == 200, f"{code}")

    team, code = req("GET", "/users/team", token=token)
    record("Equipo", code == 200, f"{code}")

    cal, code = req("GET", "/calendar/feed", token=token)
    record("Feed iCal (info)", code == 200 and bool(cal.get("feed_url")), f"{code}")

    org, code = req("GET", "/organizations/settings", token=token)
    record("Config consultorio", code == 200, f"{code}")

    # Pages frontend
    import urllib.request as u

    for label, url in [
        ("Landing HTTPS", "https://daminatoweb.com/"),
        ("Register page", "https://daminatoweb.com/register"),
        ("Login page", "https://daminatoweb.com/login"),
        ("Privacidad", "https://daminatoweb.com/privacidad"),
        ("Terminos", "https://daminatoweb.com/terminos"),
    ]:
        try:
            r = u.urlopen(u.Request(url, method="GET"), timeout=15)
            record(label, r.status == 200, str(r.status))
        except Exception as e:
            record(label, False, str(e))

    print("\n--- Resumen ---")
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)}/{len(results)} pruebas OK")
    if failed:
        print("\nFallidas:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
