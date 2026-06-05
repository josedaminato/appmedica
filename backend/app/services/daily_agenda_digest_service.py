from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.timezone import org_timezone
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.email_adapter import EmailReminderProvider
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.organization import Organization
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_STATUS_LABELS = {
    AppointmentStatus.PENDING: "Pendiente",
    AppointmentStatus.CONFIRMED: "Confirmado",
}

_MODALITY_LABELS = {
    "presencial": "Presencial",
    "online": "Online",
}

def _attention_label(appt: Appointment) -> str:
    from app.models.enums import AttentionType

    if appt.attention_type == AttentionType.HEALTH_INSURANCE:
        if appt.health_insurance:
            return f"OS · {appt.health_insurance.name}"
        return "Obra social"
    return "Particular"


def digest_send_window_open(
    now_local: datetime,
    *,
    hour: int,
    minute: int,
    window_minutes: int = 30,
) -> bool:
    target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now_local < target:
        return False
    return now_local < target + timedelta(minutes=window_minutes)


def build_agenda_digest_message(
    *,
    recipient_name: str,
    org_name: str,
    target_date: date,
    appointments: list[Appointment],
    app_url: str,
    for_owner: bool,
    tz: ZoneInfo | None = None,
) -> str:
    weekday_names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    day_name = weekday_names[target_date.weekday()]
    date_str = target_date.strftime("%d/%m/%Y")

    lines = [
        f"Hola {recipient_name},",
        "",
        f"Resumen de tu agenda para mañana {day_name} {date_str} — {org_name}",
        "",
    ]

    if not appointments:
        lines.append("No hay turnos pendientes o confirmados para ese día.")
    elif for_owner:
        lines.extend(_format_owner_agenda(appointments, tz))
    else:
        lines.extend(_format_professional_agenda(appointments, tz))

    agenda_link = f"{app_url.rstrip('/')}/agenda?date={target_date.isoformat()}"
    lines.extend(
        [
            "",
            f"Total: {len(appointments)} turno(s)",
            "",
            f"Ver en la app: {agenda_link}",
            "",
            "— AppMedica",
        ],
    )
    return "\n".join(lines)


def _format_professional_agenda(
    appointments: list[Appointment],
    tz: ZoneInfo | None,
) -> list[str]:
    return [_format_appointment_line(appt, tz) for appt in appointments]


def _format_owner_agenda(
    appointments: list[Appointment],
    tz: ZoneInfo | None,
) -> list[str]:
    by_prof: dict[str, list[Appointment]] = {}
    for appt in appointments:
        if appt.professional:
            key = appt.professional.full_name
        else:
            key = "Sin profesional asignado"
        by_prof.setdefault(key, []).append(appt)

    lines: list[str] = []
    for prof_name in sorted(by_prof.keys(), key=lambda n: (n == "Sin profesional asignado", n)):
        lines.append(f"— {prof_name} —")
        for appt in by_prof[prof_name]:
            lines.append(_format_appointment_line(appt, tz))
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _format_appointment_line(appt: Appointment, tz: ZoneInfo | None) -> str:
    zone = tz or appt.start_at.tzinfo or timezone.utc
    local_start = appt.start_at.astimezone(zone)
    time_str = local_start.strftime("%H:%M")
    patient = appt.patient
    if patient:
        name = f"{patient.last_name}, {patient.first_name}"
        extra = []
        if patient.dni:
            extra.append(f"DNI {patient.dni}")
        if patient.phone:
            extra.append(f"Tel {patient.phone}")
        patient_part = f"{name} ({', '.join(extra)})" if extra else name
    else:
        patient_part = "Paciente"

    status = _STATUS_LABELS.get(appt.status, appt.status.value)
    modality = _MODALITY_LABELS.get(appt.modality.value, appt.modality.value)
    attention = _attention_label(appt)
    detail = f"{status} | {modality} | {attention}"
    if appt.notes:
        detail += f" | Notas: {appt.notes[:80]}"
    return f"  {time_str} — {patient_part} | {detail}"


class DailyAgendaDigestService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.appointments = AppointmentRepository(db)
        self.users = UserRepository(db)
        self.digest_log = DailyDigestRepository(db)
        self.email = EmailReminderProvider(self.settings)

    def _email_enabled(self) -> bool:
        provider = (self.settings.email_provider or "mock").lower()
        return provider in ("mock", "smtp")

    async def process_all_organizations(self) -> dict[str, int]:
        if not self.settings.daily_agenda_digest_enabled or not self._email_enabled():
            return {"organizations": 0, "sent": 0, "skipped": 0, "failed": 0}

        orgs = list(self.db.scalars(select(Organization)).all())
        sent = 0
        skipped = 0
        failed = 0

        for org in orgs:
            result = await self.process_organization(org)
            sent += result["sent"]
            skipped += result["skipped"]
            failed += result["failed"]

        if sent or failed:
            self.db.commit()

        return {
            "organizations": len(orgs),
            "sent": sent,
            "skipped": skipped,
            "failed": failed,
        }

    async def process_organization(self, org: Organization) -> dict[str, int]:
        tz = org_timezone(org)
        now_local = datetime.now(timezone.utc).astimezone(tz)

        if not digest_send_window_open(
            now_local,
            hour=self.settings.daily_agenda_digest_hour,
            minute=self.settings.daily_agenda_digest_minute,
        ):
            return {"sent": 0, "skipped": 0, "failed": 0}

        target_date = now_local.date() + timedelta(days=1)
        active_statuses = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
        day_end = target_date + timedelta(days=1)

        all_tomorrow = self.appointments.list_in_range(
            org.id,
            start=datetime.min.replace(tzinfo=timezone.utc),
            end=datetime.max.replace(tzinfo=timezone.utc),
            use_date_filter=True,
            start_date=target_date,
            end_date=day_end,
        )
        tomorrow = [a for a in all_tomorrow if a.status in active_statuses]

        members = self.users.list_by_organization(org.id, active_only=True)
        sent = skipped = failed = 0

        for user in members:
            if user.role == UserRole.STAFF:
                continue
            if self.digest_log.was_sent(user.id, target_date):
                skipped += 1
                continue

            if user.role == UserRole.OWNER:
                appts = tomorrow
                for_owner = True
            else:
                appts = [a for a in tomorrow if a.professional_id == user.id]
                for_owner = False

            ok = await self._send_to_user(org, user, target_date, appts, for_owner=for_owner)
            if ok:
                self.digest_log.mark_sent(org.id, user.id, target_date)
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "skipped": skipped, "failed": failed}

    async def _send_to_user(
        self,
        org: Organization,
        user: User,
        target_date: date,
        appointments: list[Appointment],
        *,
        for_owner: bool,
    ) -> bool:
        tz = org_timezone(org)
        sorted_appts = sorted(appointments, key=lambda a: a.start_at)

        date_label = target_date.strftime("%d/%m/%Y")
        subject = f"Agenda de mañana {date_label} — {org.name}"
        body = build_agenda_digest_message(
            recipient_name=user.full_name,
            org_name=org.name,
            target_date=target_date,
            appointments=sorted_appts,
            app_url=self.settings.public_app_url,
            for_owner=for_owner,
            tz=tz,
        )

        try:
            return await self.email.send(
                ReminderPayload(
                    patient_name=user.full_name,
                    message=body,
                    email=user.email,
                    subject=subject,
                ),
            )
        except Exception:
            logger.exception("Error enviando resumen diario a %s", user.email)
            return False
