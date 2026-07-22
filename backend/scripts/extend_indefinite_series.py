"""Extiende turnos fijos indefinidos (cron diario).

Ejemplo crontab a las 4:00 AM:
0 4 * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/extend_indefinite_series.py
"""

import sys

from app.db.session import SessionLocal
from app.services.recurring_series import extend_indefinite_series


def main() -> int:
    db = SessionLocal()
    try:
        result = extend_indefinite_series(db)
        print(
            f"Series revisadas: {result['series_checked']} | "
            f"Extendidas: {result['series_extended']} | "
            f"Turnos nuevos: {result['appointments_created']} | "
            f"Conflictos salteados: {result['skipped_conflicts']}",
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
