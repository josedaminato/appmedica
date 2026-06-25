"""Crea (o reactiva) un consultorio con su usuario dueño (owner).

Uso dentro del contenedor backend en producción:

    docker compose -f docker-compose.prod.yml --env-file backend/.env.prod \
        exec -T backend python scripts/create_owner.py \
        --org "Consultorio de Ana" --name "Dra. Ana Pérez" \
        --email ana@ejemplo.com --password "ClaveFuerte123!"

Si el email ya existe, reasigna la contraseña y reactiva la cuenta
(útil para recuperar acceso sin el flujo de email).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository


def _slugify(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    return base or "consultorio"


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear/reactivar owner de un consultorio")
    parser.add_argument("--org", required=True, help="Nombre del consultorio")
    parser.add_argument("--name", required=True, help="Nombre completo del dueño")
    parser.add_argument("--email", required=True, help="Email de login")
    parser.add_argument("--password", required=True, help="Contraseña (>=8 caracteres)")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres", file=sys.stderr)
        return 2

    email = args.email.lower().strip()
    db = SessionLocal()
    try:
        users = UserRepository(db)
        orgs = OrganizationRepository(db)

        existing = users.get_by_email(email)
        if existing:
            existing.password_hash = hash_password(args.password)
            existing.is_active = True
            db.commit()
            org = orgs.get_by_id(existing.organization_id)
            print(f"OK cuenta existente actualizada: {email}")
            print(f"   consultorio: {org.name if org else 'sin org'}")
            print(f"   contraseña reasignada y cuenta activada")
            return 0

        org = Organization(name=args.org, slug=_slugify(args.org))
        orgs.create(org)
        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password(args.password),
            full_name=args.name,
            role=UserRole.OWNER,
            is_active=True,
        )
        users.create(user)
        db.commit()
        print(f"OK consultorio y owner creados:")
        print(f"   consultorio: {org.name}")
        print(f"   email: {email}")
        print(f"   rol: owner")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
