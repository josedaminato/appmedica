from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.timezone import DEFAULT_ORG_TIMEZONE, org_timezone
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.factory import get_email_provider, get_whatsapp_provider
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, ReminderChannel, ReminderStatus
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.reminder import ReminderJob
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.reminder_repository import ReminderRepository

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.reminders = ReminderRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)

    def list_jobs(self, organization_id: uuid.UUID, limit: int = 50) -> list[ReminderJob]:
        return self.reminders.list_for_organization(organization_id, limit=limit)

    def schedule_for_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> list[ReminderJob]:
        if not self.settings.reminders_enabled:
            return []

        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            return []
        if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
            return []

        patient = self.patients.get_by_id(organization_id, appointment.patient_id)
        if not patient:
            return []

        org = self.db.get(Organization, organization_id)
        org_name = org.name if org else "tu consultorio"
        tz = org_timezone(org) if org else ZoneInfo(DEFAULT_ORG_TIMEZONE)

        self.reminders.cancel_scheduled_for_appointment(organization_id, appointment_id)

        when = appointment.start_at - timedelta(hours=self.settings.reminder_hours_before)
        if when <= datetime.now(timezone.utc):
            when = datetime.now(timezone.utc) + timedelta(minutes=2)

        message = self._build_appointment_message(patient, appointment, org_name, tz)
        created: list[ReminderJob] = []

        if patient.phone and self._whatsapp_api_enabled():
            created.append(
                self._create_job(
                    organization_id,
                    patient.id,
                    ReminderChannel.WHATSAPP,
                    when,
                    message,
                    appointment_id,
                ),
            )
        if patient.email and self._email_api_enabled():
            created.append(
                self._create_job(
                    organization_id,
                    patient.id,
                    ReminderChannel.EMAIL,
                    when,
                    message,
                    appointment_id,
                    subject=f"Recordatorio de turno — {org_name}",
                ),
            )

        if created:
            self.db.commit()
        return created

    def cancel_for_appointment(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> int:
        count = self.reminders.cancel_scheduled_for_appointment(organization_id, appointment_id)
        if count:
            self.db.commit()
        return count

    async def process_due_jobs(
        self,
        organization_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Procesa jobs vencidos. Sin organization_id: todas las orgs (cron/background)."""
        now = datetime.now(timezone.utc)
        due = self.reminders.list_due(before=now, organization_id=organization_id)
        sent = 0
        failed = 0

        email_provider = get_email_provider(self.settings)
        whatsapp_provider = get_whatsapp_provider(self.settings)

        for job in due:
            if job.channel == ReminderChannel.WHATSAPP and not self._whatsapp_api_enabled():
                job.status = ReminderStatus.CANCELLED
                job.error_message = "WhatsApp API desactivado (usar enlace manual en agenda)"
                continue
            if job.channel == ReminderChannel.EMAIL and not self._email_api_enabled():
                job.status = ReminderStatus.CANCELLED
                job.error_message = "Email SMTP no configurado"
                continue

            payload_data = job.payload or {}
            patient_name = payload_data.get("patient_name", "Paciente")
            message = payload_data.get("message", "")
            phone = payload_data.get("phone")
            email = payload_data.get("email")
            subject = payload_data.get("subject")

            reminder = ReminderPayload(
                patient_name=patient_name,
                message=message,
                phone=phone,
                email=email,
                subject=subject,
            )
            try:
                if job.channel == ReminderChannel.EMAIL:
                    ok = await email_provider.send(reminder)
                else:
                    ok = await whatsapp_provider.send(reminder)
                if ok:
                    job.status = ReminderStatus.SENT
                    job.error_message = None
                    sent += 1
                else:
                    job.status = ReminderStatus.FAILED
                    job.error_message = "Proveedor no envió el mensaje"
                    failed += 1
            except Exception as exc:
                job.status = ReminderStatus.FAILED
                job.error_message = str(exc)[:500]
                failed += 1
                logger.exception("Error enviando recordatorio %s", job.id)

        if due:
            self.db.commit()

        return {"processed": len(due), "sent": sent, "failed": failed}

    def _create_job(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        channel: ReminderChannel,
        scheduled_at: datetime,
        message: str,
        appointment_id: uuid.UUID,
        *,
        subject: str | None = None,
    ) -> ReminderJob:
        patient = self.patients.get_by_id(organization_id, patient_id)
        payload = {
            "appointment_id": str(appointment_id),
            "patient_name": f"{patient.last_name}, {patient.first_name}" if patient else "Paciente",
            "message": message,
            "phone": patient.phone if patient else None,
            "email": patient.email if patient else None,
            "subject": subject,
        }
        job = ReminderJob(
            organization_id=organization_id,
            patient_id=patient_id,
            channel=channel,
            status=ReminderStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            payload=payload,
        )
        return self.reminders.create(job)

    def _whatsapp_api_enabled(self) -> bool:
        return (self.settings.whatsapp_provider or "disabled").lower() in ("twilio", "meta")

    def _email_api_enabled(self) -> bool:
        return (self.settings.email_provider or "mock").lower() == "smtp"

    def _build_appointment_message(
        self,
        patient: Patient,
        appointment: Appointment,
        org_name: str,
        tz: ZoneInfo,
    ) -> str:
        local_start = appointment.start_at.astimezone(tz)
        date_str = local_start.strftime("%d/%m/%Y")
        time_str = local_start.strftime("%H:%M")
        return (
            f"Hola {patient.first_name}, te recordamos tu turno en {org_name} "
            f"el {date_str} a las {time_str} (hora del consultorio). "
            f"Si necesitás reprogramar, contactá al consultorio."
        )
