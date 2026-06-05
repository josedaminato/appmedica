"""Envía el resumen de agenda del día siguiente (cron opcional en el VPS).

Ejemplo crontab a las 21:00 hora Argentina (ajustar si el VPS usa UTC):
0 0 * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml exec -T backend python scripts/send_daily_agenda.py
"""

import asyncio
import sys

from app.db.session import SessionLocal
from app.services.daily_agenda_digest_service import DailyAgendaDigestService


async def main() -> int:
    db = SessionLocal()
    try:
        result = await DailyAgendaDigestService(db).process_all_organizations()
        print(
            f"Organizaciones: {result['organizations']} | "
            f"Enviados: {result['sent']} | "
            f"Omitidos: {result['skipped']} | "
            f"Fallidos: {result['failed']}",
        )
        return 0 if result["failed"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
