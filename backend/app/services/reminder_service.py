from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.timezone import (
    DEFAULT_ORG_TIMEZONE,
    REMINDER_MIN_LEAD,
    clamp_to_send_window,
    compute_reminder_send_at,
    has_min_reminder_lead,
    is_in_quiet_hours,
    org_timezone,
)
from app.integrations.reminders.base import ReminderPayload, ReminderProvider, ReminderSendResult
from app.integrations.reminders.factory import get_email_provider, get_whatsapp_provider
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentStatus,
    ReminderChannel,
    ReminderKind,
    ReminderStatus,
)
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.reminder import ReminderJob
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.reminder_repository import ReminderRepository

logger = logging.getLogger(__name__)

MAX_SEND_ATTEMPTS = 3


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


# Con 3 intentos se usan 5m y 30m. El backoff de 2h queda para si se sube el máximo.
RETRY_BACKOFFS = (
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
)
_SENDABLE_APPOINTMENT_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
_CANCEL_APPOINTMENT_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED)


@dataclass
class _PreparedSend:
    job_id: uuid.UUID
    organization_id: uuid.UUID
    channel: ReminderChannel
    appointment_start: datetime
    patient_name: str
    message: str
    phone: str | None
    email: str | None
    subject: str | None
    provider_name: str
    tz: ZoneInfo


class ReminderService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.reminders = ReminderRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)

    def list_jobs(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ReminderJob]:
        return self.reminders.list_for_organization(
            organization_id,
            professional_id=professional_id,
            limit=limit,
        )

    def schedule_for_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> list[ReminderJob]:
        if not self.settings.reminders_enabled:
            return []

        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            return []
        if appointment.status not in _SENDABLE_APPOINTMENT_STATUSES:
            return []

        patient = self.patients.get_by_id(organization_id, appointment.patient_id)
        if not patient:
            return []

        org = self.db.get(Organization, organization_id)
        org_name = org.name if org else "tu consultorio"
        tz = org_timezone(org) if org else ZoneInfo(DEFAULT_ORG_TIMEZONE)
        now = now or datetime.now(timezone.utc)

        self.reminders.cancel_scheduled_for_appointment(organization_id, appointment_id)

        send_at = compute_reminder_send_at(
            start_at=appointment.start_at,
            now=now,
            tz=tz,
            hours_before=self.settings.reminder_hours_before,
        )
        if send_at is None:
            logger.info(
                "Reminder not scheduled appointment_id=%s org_id=%s: outside send window",
                appointment_id,
                organization_id,
            )
            self.db.commit()
            return []

        created: list[ReminderJob] = []

        if patient.phone and self._whatsapp_api_enabled():
            job = self._try_create_job(
                organization_id,
                patient.id,
                ReminderChannel.WHATSAPP,
                send_at,
                appointment_id,
            )
            if job:
                created.append(job)
        if patient.email and self._email_api_enabled():
            job = self._try_create_job(
                organization_id,
                patient.id,
                ReminderChannel.EMAIL,
                send_at,
                appointment_id,
                subject=f"Recordatorio de turno — {org_name}",
            )
            if job:
                created.append(job)

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
        *,
        email_provider: ReminderProvider | None = None,
        whatsapp_provider: ReminderProvider | None = None,
    ) -> dict[str, int]:
        """Procesa jobs vencidos. Sin organization_id: todas las orgs (cron).

        Semántica at-least-once: si el proceso muere después de que el proveedor
        aceptó el mensaje y antes de persistir `sent`, el job huérfano en
        `sending` se reintenta. El proveedor puede recibir un duplicado.
        """
        now = datetime.now(timezone.utc)
        recovered = self.reminders.recover_orphan_sending(
            before=now, organization_id=organization_id,
        )
        if recovered:
            self.db.commit()
            logger.info("Recovered orphan sending jobs count=%s", recovered)

        email_provider = email_provider or get_email_provider(self.settings)
        whatsapp_provider = whatsapp_provider or get_whatsapp_provider(self.settings)

        processed = 0
        sent = 0
        failed = 0
        skipped = 0
        retried = 0

        while True:
            now = datetime.now(timezone.utc)
            job = self.reminders.lock_due_job(before=now, organization_id=organization_id)
            if job is None:
                break
            processed += 1

            prepared = self._revalidate_locked_job(job, now)
            if prepared is None:
                if job.status == ReminderStatus.SKIPPED:
                    skipped += 1
                self.db.commit()
                continue

            if is_in_quiet_hours(now, prepared.tz):
                if self._apply_quiet_hours_defer(job, prepared, now) == "skipped":
                    skipped += 1
                self.db.commit()
                continue

            job.status = ReminderStatus.SENDING
            job.updated_at = now
            job.provider = prepared.provider_name
            self.db.commit()

            if not self._revalidate_before_provider(prepared):
                self.db.expire_all()
                current = self.db.get(ReminderJob, prepared.job_id)
                if current is not None and current.status == ReminderStatus.SKIPPED:
                    skipped += 1
                continue

            provider = (
                email_provider
                if prepared.channel == ReminderChannel.EMAIL
                else whatsapp_provider
            )
            try:
                result = await provider.send(
                    ReminderPayload(
                        patient_name=prepared.patient_name,
                        message=prepared.message,
                        phone=prepared.phone,
                        email=prepared.email,
                        subject=prepared.subject,
                    ),
                )
            except Exception as exc:
                logger.exception(
                    "Reminder provider error job_id=%s appointment_id=%s org_id=%s",
                    prepared.job_id,
                    job.appointment_id,
                    prepared.organization_id,
                )
                result = ReminderSendResult.failure(
                    retryable=True,
                    error_code="provider_exception",
                    error_message=type(exc).__name__,
                )

            self.db.expire_all()
            job = self.db.get(ReminderJob, prepared.job_id)
            if job is None:
                continue
            if job.status != ReminderStatus.SENDING:
                logger.info(
                    "Reminder result ignored job_id=%s appointment_id=%s org_id=%s status=%s",
                    job.id,
                    job.appointment_id,
                    job.organization_id,
                    job.status.value,
                )
                continue
            outcome, values = self._compute_send_result(job, prepared, result, now)
            if not self.reminders.update_if_sending(job.id, values):
                self.db.rollback()
                self.db.expire_all()
                current = self.db.get(ReminderJob, prepared.job_id)
                logger.info(
                    "Reminder result ignored job_id=%s appointment_id=%s org_id=%s status=%s",
                    prepared.job_id,
                    current.appointment_id if current else prepared.job_id,
                    prepared.organization_id,
                    current.status.value if current else "missing",
                )
                continue
            self.db.expire(job)
            if outcome == "sent":
                sent += 1
            elif outcome == "failed":
                failed += 1
            elif outcome == "retried":
                retried += 1
            else:
                skipped += 1
            self.db.commit()

        return {
            "processed": processed,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "retried": retried,
        }

    def _revalidate_locked_job(
        self,
        job: ReminderJob,
        now: datetime,
    ) -> _PreparedSend | None:
        appointment = self.appointments.get_by_id_for_update(
            job.organization_id, job.appointment_id,
        )
        if appointment is None:
            self._finish(job, ReminderStatus.SKIPPED, "appointment_missing", "Turno inexistente")
            return None
        if appointment.organization_id != job.organization_id:
            self._finish(job, ReminderStatus.SKIPPED, "org_mismatch", "organization_id mismatch")
            return None
        if appointment.status in _CANCEL_APPOINTMENT_STATUSES:
            self._finish(
                job,
                ReminderStatus.CANCELLED,
                "appointment_cancelled",
                f"Turno {appointment.status.value}",
            )
            return None
        start_utc = _as_utc(appointment.start_at)
        now_utc = _as_utc(now)
        if start_utc <= now_utc:
            self._finish(job, ReminderStatus.SKIPPED, "appointment_past", "Turno ya comenzó")
            return None
        if not has_min_reminder_lead(start_utc, now_utc):
            self._finish(
                job,
                ReminderStatus.SKIPPED,
                "too_close_to_start",
                "Less than 30 minutes before appointment start",
            )
            return None
        if appointment.status not in _SENDABLE_APPOINTMENT_STATUSES:
            self._finish(
                job,
                ReminderStatus.SKIPPED,
                "appointment_not_sendable",
                f"Turno {appointment.status.value}",
            )
            return None

        if job.channel == ReminderChannel.WHATSAPP and not self._whatsapp_api_enabled():
            self._finish(job, ReminderStatus.SKIPPED, "channel_disabled", "WhatsApp API desactivado")
            return None
        if job.channel == ReminderChannel.EMAIL and not self._email_api_enabled():
            self._finish(job, ReminderStatus.SKIPPED, "channel_disabled", "Email SMTP no configurado")
            return None

        patient = self.patients.get_by_id(job.organization_id, appointment.patient_id)
        if not patient:
            self._finish(job, ReminderStatus.SKIPPED, "patient_missing", "Paciente inexistente")
            return None

        phone = (patient.phone or "").strip() or None
        email = (patient.email or "").strip() or None
        if job.channel == ReminderChannel.WHATSAPP and not phone:
            self._finish(job, ReminderStatus.SKIPPED, "missing_contact", "Paciente sin teléfono")
            return None
        if job.channel == ReminderChannel.EMAIL and not email:
            self._finish(job, ReminderStatus.SKIPPED, "missing_contact", "Paciente sin email")
            return None

        org = self.db.get(Organization, job.organization_id)
        org_name = org.name if org else "tu consultorio"
        tz = org_timezone(org) if org else ZoneInfo(DEFAULT_ORG_TIMEZONE)
        message = self._build_appointment_message(patient, appointment, org_name, tz)
        subject = None
        if job.channel == ReminderChannel.EMAIL:
            subject = f"Recordatorio de turno — {org_name}"
        provider_name = (
            (self.settings.email_provider or "smtp")
            if job.channel == ReminderChannel.EMAIL
            else (self.settings.whatsapp_provider or "unknown")
        )
        return _PreparedSend(
            job_id=job.id,
            organization_id=job.organization_id,
            channel=job.channel,
            appointment_start=appointment.start_at,
            patient_name=f"{patient.last_name}, {patient.first_name}",
            message=message,
            phone=phone,
            email=email,
            subject=subject,
            provider_name=provider_name[:32],
            tz=tz,
        )

    def _revalidate_before_provider(self, prepared: _PreparedSend) -> bool:
        """Relee turno y job después de COMMIT sending, antes del HTTP. No deja locks abiertos."""
        now = datetime.now(timezone.utc)
        self.db.expire_all()
        job = self.db.get(ReminderJob, prepared.job_id)
        if job is None or job.status != ReminderStatus.SENDING:
            return False

        refreshed = self._revalidate_locked_job(job, now)
        if refreshed is None:
            self.db.commit()
            return False

        if _as_utc(refreshed.appointment_start) != _as_utc(prepared.appointment_start):
            self._finish(
                job,
                ReminderStatus.SKIPPED,
                "appointment_start_changed",
                "Appointment start changed before send",
            )
            self.db.commit()
            return False

        self.db.commit()
        return True

    def _apply_quiet_hours_defer(
        self,
        job: ReminderJob,
        prepared: _PreparedSend,
        now: datetime,
    ) -> str:
        next_at = clamp_to_send_window(now, prepared.tz)
        skip_code = self._next_attempt_skip_code(
            next_at,
            prepared.appointment_start,
            after_start="quiet_hours_after_start",
            too_close="quiet_hours_too_close_to_start",
        )
        if skip_code:
            message = (
                "Next send window is at or after appointment start"
                if skip_code == "quiet_hours_after_start"
                else "Next send window is less than 30 minutes before appointment start"
            )
            self._finish(job, ReminderStatus.SKIPPED, skip_code, message)
            return "skipped"

        job.next_attempt_at = next_at
        logger.info(
            "Reminder deferred for quiet hours job_id=%s appointment_id=%s org_id=%s",
            job.id,
            job.appointment_id,
            job.organization_id,
        )
        return "deferred"

    @staticmethod
    def _next_attempt_skip_code(
        next_at: datetime,
        start_at: datetime,
        *,
        after_start: str,
        too_close: str,
    ) -> str | None:
        start_utc = _as_utc(start_at)
        next_utc = _as_utc(next_at)
        if next_utc >= start_utc:
            return after_start
        if start_utc - next_utc < REMINDER_MIN_LEAD:
            return too_close
        return None

    def _compute_send_result(
        self,
        job: ReminderJob,
        prepared: _PreparedSend,
        result: ReminderSendResult,
        now: datetime,
    ) -> tuple[str, dict]:
        attempt_count = (job.attempt_count or 0) + 1
        base: dict = {
            "attempt_count": attempt_count,
            "provider": prepared.provider_name,
            "updated_at": now,
        }

        if result.ok:
            logger.info(
                "Reminder sent job_id=%s appointment_id=%s org_id=%s channel=%s provider=%s",
                job.id,
                job.appointment_id,
                job.organization_id,
                job.channel.value,
                prepared.provider_name,
            )
            return "sent", {
                **base,
                "status": ReminderStatus.SENT,
                "sent_at": now,
                "error_code": None,
                "error_message": None,
                "payload": {
                    "patient_name": prepared.patient_name,
                    "message": prepared.message,
                    "subject": prepared.subject,
                },
            }

        error_code = result.error_code or "send_failed"
        error_message = (result.error_message or "")[:500]
        retryable = result.retryable and error_code != "missing_contact"

        if not retryable:
            logger.info(
                "Reminder failed job_id=%s appointment_id=%s org_id=%s error_code=%s",
                job.id,
                job.appointment_id,
                job.organization_id,
                error_code,
            )
            return "failed", {
                **base,
                "status": ReminderStatus.FAILED,
                "error_code": error_code,
                "error_message": error_message or "Permanent provider error",
            }

        if attempt_count >= MAX_SEND_ATTEMPTS:
            return "failed", {
                **base,
                "status": ReminderStatus.FAILED,
                "error_code": "max_attempts",
                "error_message": error_message or "Max send attempts reached",
            }

        backoff_index = min(attempt_count - 1, len(RETRY_BACKOFFS) - 1)
        delay = RETRY_BACKOFFS[backoff_index]
        if result.retry_after_seconds is not None and result.retry_after_seconds >= 0:
            delay = timedelta(seconds=result.retry_after_seconds)
        next_at = clamp_to_send_window(now + delay, prepared.tz)
        skip_code = self._next_attempt_skip_code(
            next_at,
            prepared.appointment_start,
            after_start="retry_after_start",
            too_close="retry_too_close_to_start",
        )
        if skip_code:
            message = (
                "Next retry would be after appointment start"
                if skip_code == "retry_after_start"
                else "Next retry would be less than 30 minutes before appointment start"
            )
            return "skipped", {
                **base,
                "status": ReminderStatus.SKIPPED,
                "error_code": skip_code,
                "error_message": message,
            }

        logger.info(
            "Reminder retry job_id=%s appointment_id=%s org_id=%s attempt=%s error_code=%s",
            job.id,
            job.appointment_id,
            job.organization_id,
            attempt_count,
            error_code,
        )
        return "retried", {
            **base,
            "status": ReminderStatus.SCHEDULED,
            "next_attempt_at": next_at,
            "error_code": error_code,
            "error_message": error_message or "Retry scheduled",
        }

    def _apply_send_result(
        self,
        job: ReminderJob,
        prepared: _PreparedSend,
        result: ReminderSendResult,
        now: datetime,
    ) -> str:
        outcome, values = self._compute_send_result(job, prepared, result, now)
        for key, value in values.items():
            setattr(job, key, value)
        return outcome

    @staticmethod
    def _finish(
        job: ReminderJob,
        status: ReminderStatus,
        error_code: str,
        error_message: str,
    ) -> None:
        job.status = status
        job.error_code = error_code
        job.error_message = error_message
        logger.info(
            "Reminder %s job_id=%s appointment_id=%s org_id=%s error_code=%s",
            status.value,
            job.id,
            job.appointment_id,
            job.organization_id,
            error_code,
        )

    def _try_create_job(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        channel: ReminderChannel,
        scheduled_at: datetime,
        appointment_id: uuid.UUID,
        *,
        subject: str | None = None,
    ) -> ReminderJob | None:
        job = ReminderJob(
            organization_id=organization_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            kind=ReminderKind.APPOINTMENT_REMINDER_24H,
            channel=channel,
            status=ReminderStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            next_attempt_at=scheduled_at,
            attempt_count=0,
            payload={"subject": subject} if subject else None,
        )
        try:
            with self.db.begin_nested():
                return self.reminders.create(job)
        except IntegrityError:
            logger.info(
                "Active reminder already exists appointment_id=%s org_id=%s channel=%s",
                appointment_id,
                organization_id,
                channel.value,
            )
            return None

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
