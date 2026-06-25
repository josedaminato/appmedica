#!/usr/bin/env python3
"""Prueba importación de pacientes en producción."""
import io
import json
import random
import urllib.error
import urllib.request

BASE = "https://daminatoweb.com/api/v1"


def req(method: str, path: str, body=None, token: str | None = None, multipart=None):
    if multipart:
        data, headers = multipart
        r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    else:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return (json.loads(raw) if raw else {}), resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw), e.code
        except json.JSONDecodeError:
            return {"raw": raw}, e.code


def main():
    suffix = random.randint(10000, 99999)
    email = f"import-qa-{suffix}@daminatoweb-test.com"
    pw = "TestQA2026!x"
    dni1 = str(36000000 + suffix)
    dni2 = str(36010000 + suffix)

    reg, code = req(
        "POST",
        "/auth/register",
        {
            "organization_name": f"Import QA {suffix}",
            "full_name": "Import QA",
            "email": email,
            "password": pw,
        },
    )
    print(f"register {code} {email}")
    token = reg["access_token"]

    ins, code = req(
        "POST",
        "/health-insurances",
        {"name": "OSDE", "coverage_percent": 80, "estimated_payment_days": 30},
        token,
    )
    print(f"insurance {code} {ins.get('name')}")

    columns = ["Nombre", "Apellido", "DNI", "Teléfono", "Email", "Obra social", "Nº afiliado", "Notas"]
    rows = [
        {
            "Nombre": "Ana",
            "Apellido": "Excel Uno",
            "DNI": dni1,
            "Teléfono": "2614001122",
            "Email": f"ana{suffix}@test.com",
            "Obra social": "OSDE",
            "Nº afiliado": "111",
            "Notas": "import ok",
        },
        {
            "Nombre": "Luis",
            "Apellido": "Excel Dos",
            "DNI": dni2,
            "Teléfono": "",
            "Email": "",
            "Obra social": "Swiss Medical",
            "Nº afiliado": "",
            "Notas": "obra sin match",
        },
        {
            "Nombre": "",
            "Apellido": "Sin DNI",
            "DNI": "",
            "Teléfono": "",
            "Email": "",
            "Obra social": "",
            "Nº afiliado": "",
            "Notas": "error",
        },
        {
            "Nombre": "Ana",
            "Apellido": "Dup",
            "DNI": dni1,
            "Teléfono": "",
            "Email": "",
            "Obra social": "",
            "Nº afiliado": "",
            "Notas": "dup en archivo",
        },
    ]

    preview, code = req("POST", "/imports/patients/analyze", {"columns": columns, "rows": rows}, token)
    print(f"\nanalyze (JSON) {code}")
    print("mapping:", preview.get("suggested_mapping"))
    print("summary:", preview.get("summary"))
    for r in preview.get("rows", []):
        print(f"  fila {r['row_number']}: {r['status']} errors={r.get('errors')} warnings={r.get('warnings')}")

    valid = [r["data"] for r in preview.get("rows", []) if r["status"] == "valid" and r["data"]]
    commit, code = req("POST", "/imports/patients/commit", {"rows": valid, "on_duplicate": "skip"}, token)
    print(f"\ncommit {code}: {commit}")

    # xlsx upload preview endpoint
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(columns)
        ws.append(["Carlos", "Xlsx Test", dni2, "2614112233", "", "OSDE", "", "via xlsx"])
        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()

        boundary = f"----WebKitFormBoundary{suffix}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test.xlsx"\r\n'
            f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
        ).encode() + xlsx_bytes + f"\r\n--{boundary}--\r\n".encode()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        preview_xlsx, code_x = req("POST", "/imports/patients/preview", multipart=(body, headers))
        print(f"\npreview xlsx {code_x} summary={preview_xlsx.get('summary')}")
    except ImportError:
        print("\npreview xlsx: omitido (openpyxl no instalado localmente)")

    patients, _ = req("GET", f"/patients?page=1&page_size=20&search={dni1}", token=token)
    print(f"\nsearch {dni1}:", patients)


if __name__ == "__main__":
    main()
