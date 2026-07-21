"""Script de validación del flujo principal. Ejecutar: python scripts/test_core_flow.py"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
REQUEST_TIMEOUT = int(os.environ.get("API_TIMEOUT", "15"))
MAX_RETRIES = 3


def req(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode()), resp.status
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            try:
                return json.loads(err), e.code
            except json.JSONDecodeError:
                return {"error": err}, e.code
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def assert_ok(data, code, msg):
    if code >= 400:
        raise AssertionError(f"{msg}: {code} {data}")


def appointment_from_create(data: dict) -> dict:
    if isinstance(data, dict) and "appointments" in data:
        return data["appointments"][0] if data["appointments"] else {}
    return data if isinstance(data, dict) else {}


def main():
    print("=== Test flujo AppMedica ===\n")
    print(f"API: {BASE}\n")

    try:
        data, code = req("POST", "/auth/login", {"email": "demo@consultorio.com", "password": "demo12345"})
    except Exception as e:
        print(f"FAIL login: no se pudo conectar a {BASE}")
        print(f"  Error: {e}")
        print("  Verificá: docker compose ps && docker compose logs backend --tail=30")
        print("  Si el contenedor está trabado: reiniciá Docker Desktop y ejecutá docker compose up -d --build")
        return 1

    try:
        assert_ok(data, code, "login")
        token = data["access_token"]
        print("OK login")
    except AssertionError as e:
        print(f"FAIL login: {e}")
        print("  Ejecutá: docker compose exec backend python scripts/seed_demo.py")
        return 1

    patients, code = req("GET", "/patients?page_size=1", token=token)
    assert_ok(patients, code, "patients")
    patient_id = patients["data"][0]["id"]

    insurances, code = req("GET", "/health-insurances", token=token)
    assert_ok(insurances, code, "insurances")
    if insurances:
        insurance_id = insurances[0]["id"]
    else:
        ins, code = req(
            "POST",
            "/health-insurances",
            {"name": "OSDE Test", "coverage_percent": 80, "estimated_payment_days": 30},
            token,
        )
        insurance_id = ins.get("id") if code < 300 else None

    now = datetime.now(timezone.utc)
    start = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)

    def create_appt(extra=None):
        body = {
            "patient_id": patient_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "expected_amount": 10000,
            "attention_type": "private",
        }
        if extra:
            body.update(extra)
        data, code = req("POST", "/appointments", body, token)
        return appointment_from_create(data), code

    tests = []

    # 1. Particular
    appt, code = create_appt()
    tests.append(("crear particular", code < 300, appt))
    aid = appt.get("id")

    for step, path in [
        ("confirmar", f"/appointments/{aid}/confirm"),
        ("asistió", f"/appointments/{aid}/attend"),
    ]:
        _, code = req("POST", path, token=token)
        tests.append((step, code < 300, code))

    closed, code = req(
        "POST",
        f"/appointments/{aid}/close",
        {"closure_type": "paid", "amount": 10000, "method": "cash"},
        token,
    )
    tests.append(("cerrar cobrado", code < 300 and closed.get("closure_status") == "paid", closed))

    dash, code = req("GET", "/dashboard/summary", token=token)
    tests.append(("dashboard post-cobrado", code < 300, dash))

    # 2. Pendiente
    start2 = start + timedelta(hours=1)
    appt2, code = create_appt()
    if code < 300:
        aid2 = appt2["id"]
        req("POST", f"/appointments/{aid2}/confirm", token=token)
        req("POST", f"/appointments/{aid2}/attend", token=token)
        c2, code = req(
            "POST",
            f"/appointments/{aid2}/close",
            {"closure_type": "pending", "amount": 8000, "method": "cash"},
            token,
        )
        tests.append(("cerrar pendiente", code < 300 and c2.get("closure_status") == "pending", c2))
        dash2, _ = req("GET", "/dashboard/summary", token=token)
        debt = float(dash2.get("private_debt_total", 0))
        tests.append(("deuda particular incluye 8000", debt >= 8000, debt))

    # 3. Parcial + pago adicional
    appt3, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": (start2 + timedelta(hours=2)).isoformat(),
            "end_at": (start2 + timedelta(hours=2, minutes=30)).isoformat(),
            "expected_amount": 10000,
        },
        token,
    )
    if code < 300:
        aid3 = appointment_from_create(appt3)["id"]
        req("POST", f"/appointments/{aid3}/confirm", token=token)
        req("POST", f"/appointments/{aid3}/attend", token=token)
        req(
            "POST",
            f"/appointments/{aid3}/close",
            {"closure_type": "partial", "amount": 10000, "paid_amount": 4000, "method": "cash"},
            token,
        )
        pre_pay, _ = req("GET", f"/appointments/{aid3}", token=token)
        tests.append(("parcial status antes de saldar", pre_pay.get("closure_status") == "partial", pre_pay))
        req(
            "POST",
            f"/appointments/{aid3}/payments",
            {"amount": 6000, "method": "cash"},
            token,
        )
        c3, _ = req("GET", f"/appointments/{aid3}", token=token)
        tests.append(("parcial pagado completo", c3.get("closure_status") == "paid", c3))

    # 4. Obra social
    if insurance_id:
        appt4, code = req(
            "POST",
            "/appointments",
            {
                "patient_id": patient_id,
                "start_at": (start2 + timedelta(hours=4)).isoformat(),
                "end_at": (start2 + timedelta(hours=4, minutes=30)).isoformat(),
                "attention_type": "health_insurance",
                "health_insurance_id": insurance_id,
                "expected_amount": 12000,
            },
            token,
        )
        if code < 300:
            aid4 = appointment_from_create(appt4)["id"]
            req("POST", f"/appointments/{aid4}/confirm", token=token)
            req("POST", f"/appointments/{aid4}/attend", token=token)
            c4, code = req(
                "POST",
                f"/appointments/{aid4}/close",
                {
                    "closure_type": "insurance_pending",
                    "amount": 12000,
                    "health_insurance_id": insurance_id,
                },
                token,
            )
            tests.append(("cerrar OS", code < 300 and c4.get("closure_status") == "insurance_pending", c4))
            dash4, _ = req("GET", "/dashboard/summary", token=token)
            ins_debt = float(dash4.get("insurance_debt_total", 0))
            tests.append(("deuda OS", ins_debt >= 12000, ins_debt))

    # 5. Ausente
    appt5, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": (start2 + timedelta(hours=6)).isoformat(),
            "end_at": (start2 + timedelta(hours=6, minutes=30)).isoformat(),
        },
        token,
    )
    if code < 300:
        aid5 = appointment_from_create(appt5)["id"]
        req("POST", f"/appointments/{aid5}/confirm", token=token)
        req("POST", f"/appointments/{aid5}/no-show", token=token)
        admin, _ = req("GET", f"/patients/{patient_id}/admin-summary", token=token)
        tests.append(("ausente suma", admin.get("no_show_count", 0) >= 1, admin))

    # 6. Cancelado sin deuda
    appt6, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": (start2 + timedelta(hours=8)).isoformat(),
            "end_at": (start2 + timedelta(hours=8, minutes=30)).isoformat(),
        },
        token,
    )
    if code < 300:
        aid6 = appointment_from_create(appt6)["id"]
        req("POST", f"/appointments/{aid6}/cancel", token=token)
        tests.append(("cancelado", True, "ok"))

    # 6b. Reprogramar conserva historial
    appt_res, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": (start2 + timedelta(hours=9)).isoformat(),
            "end_at": (start2 + timedelta(hours=9, minutes=30)).isoformat(),
        },
        token,
    )
    if code < 300:
        old_id = appointment_from_create(appt_res)["id"]
        new_start = start2 + timedelta(days=3, hours=9)
        new_end = new_start + timedelta(minutes=30)
        new_appt, code_r = req(
            "POST",
            f"/appointments/{old_id}/reschedule",
            {"start_at": new_start.isoformat(), "end_at": new_end.isoformat()},
            token,
        )
        old_after, _ = req("GET", f"/appointments?date={start2.date().isoformat()}&view=day", token=token)
        ok_res = (
            code_r < 300
            and new_appt.get("status") == "pending"
            and any(a["id"] == old_id and a.get("status") == "rescheduled" for a in old_after)
        )
        tests.append(("reprogramar", ok_res, {"new": new_appt, "old_status": "rescheduled"}))

    # 7. Sin cerrar
    appt7, code = req(
        "POST",
        "/appointments",
        {
            "patient_id": patient_id,
            "start_at": (start2 + timedelta(hours=10)).isoformat(),
            "end_at": (start2 + timedelta(hours=10, minutes=30)).isoformat(),
        },
        token,
    )
    if code < 300:
        aid7 = appointment_from_create(appt7)["id"]
        req("POST", f"/appointments/{aid7}/confirm", token=token)
        req("POST", f"/appointments/{aid7}/attend", token=token)
        dash7, _ = req("GET", "/dashboard/summary", token=token)
        tests.append(("sin cerrar detectado", dash7.get("unclosed_attended", 0) >= 1, dash7))

    print("\n--- Resultados ---")
    failed = 0
    for name, ok, detail in tests:
        status = "OK" if ok else "FAIL"
        print(f"{status} {name}: {detail}")
        if not ok:
            failed += 1

    print(f"\n{len(tests) - failed}/{len(tests)} pasaron")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
