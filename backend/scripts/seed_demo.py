"""Carga datos demo idempotentes. Ejecutar: python scripts/seed_demo.py"""
import sys
from pathlib import Path

# `python scripts/seed_demo.py` no incluye /app en sys.path (p. ej. Docker)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository

DEMO_EMAIL = "demo@consultorio.com"
DEMO_PASSWORD = "demo12345"
DEMO_ORG = "Consultorio Demo"
DEMO_USER = "Dr. Juan Perez"

PATIENTS = [
    {"first_name": "María", "last_name": "García", "dni": "30123456", "phone": "11-5555-1001"},
    {"first_name": "Carlos", "last_name": "López", "dni": "28987654", "phone": "11-5555-1002"},
]


def main() -> int:
    db = SessionLocal()
    try:
        users = UserRepository(db)
        orgs = OrganizationRepository(db)
        patients = PatientRepository(db)

        user = users.get_by_email(DEMO_EMAIL)
        if user:
            org = orgs.get_by_id(user.organization_id)
            print(f"OK demo ya existe: {DEMO_EMAIL} ({org.name if org else 'sin org'})")
        else:
            org = Organization(name=DEMO_ORG, slug="consultorio-demo")
            orgs.create(org)
            user = User(
                organization_id=org.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=DEMO_USER,
                role=UserRole.OWNER,
                is_active=True,
            )
            users.create(user)
            db.commit()
            print(f"OK usuario demo creado: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        org_id = user.organization_id
        created = 0
        for row in PATIENTS:
            if patients.get_by_dni(org_id, row["dni"]):
                continue
            patients.create(
                Patient(
                    organization_id=org_id,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    dni=row["dni"],
                    phone=row["phone"],
                    is_active=True,
                )
            )
            created += 1
        if created:
            db.commit()
            print(f"OK {created} paciente(s) demo creados")
        else:
            print("OK pacientes demo ya existían")

        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR seed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
