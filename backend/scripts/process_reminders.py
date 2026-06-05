"""Procesa recordatorios vencidos (para cron en el VPS).

Ejemplo crontab cada 5 minutos:
*/5 * * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml exec -T backend python scripts/process_reminders.py
"""

import asyncio
import sys

from app.db.session import SessionLocal
from app.services.reminder_service import ReminderService


async def main() -> int:
    db = SessionLocal()
    try:
        # Sin organization_id: procesa todas las organizaciones (cron del VPS).
        result = await ReminderService(db).process_due_jobs()
        print(
            f"Procesados: {result['processed']} | "
            f"Enviados: {result['sent']} | Fallidos: {result['failed']}",
        )
        return 0 if result["failed"] == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
