from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import not_found
from app.core.timezone import org_timezone
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.organization import Organization
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.user_repository import UserRepository

_STATUS_LABELS = {
    AppointmentStatus.PENDING: "Pendiente",
    AppointmentStatus.CONFIRMED: "Confirmado",
    AppointmentStatus.ATTENDED: "Asistió",
}


def _attention_label(appt: Appointment) -> str:
    from app.models.enums import AttentionType

    if appt.attention_type == AttentionType.HEALTH_INSURANCE:
        if appt.health_insurance:
            return f"OS · {appt.health_insurance.name}"
        return "Obra social"
    return "Particular"


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def format_ics_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics_calendar(
    *,
    calendar_name: str,
    appointments: list[Appointment],
    tz: ZoneInfo,
    app_url: str,
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AppMedica//Agenda//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(calendar_name)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT3H",
        "X-PUBLISHED-TTL:PT3H",
    ]

    now_stamp = format_ics_utc(datetime.now(timezone.utc))

    for appt in appointments:
        lines.extend(
            _appointment_to_vevent(
                appt,
                tz=tz,
                app_url=app_url,
                dtstamp=now_stamp,
            ),
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _appointment_to_vevent(
    appt: Appointment,
    *,
    tz: ZoneInfo,
    app_url: str,
    dtstamp: str,
) -> list[str]:
    status_label = _STATUS_LABELS.get(appt.status, appt.status.value)
    prof_name = appt.professional.full_name if appt.professional else "Sin asignar"
    local_start = appt.start_at.astimezone(tz).strftime("%H:%M")
    local_end = appt.end_at.astimezone(tz).strftime("%H:%M")
    local_day = appt.start_at.astimezone(tz).date().isoformat()

    description_parts = [
        f"Fecha: {local_day}",
        f"Hora: {local_start}–{local_end}",
        f"Profesional: {prof_name}",
        f"Atención: {_attention_label(appt)}",
        f"Estado: {status_label}",
    ]

    summary = "Turno AppMedica"
    location = ""

    uid = f"appointment-{appt.id}@appmedica"

    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{format_ics_utc(appt.start_at)}",
        f"DTEND:{format_ics_utc(appt.end_at)}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(chr(10).join(description_parts))}",
        f"LOCATION:{ics_escape(location)}",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]


class CalendarFeedService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.appointments = AppointmentRepository(db)

    def get_feed_info(self, user: User) -> dict[str, str]:
        token = self._ensure_feed_token(user)
        feed_url = self._build_feed_url(token)
        return {
            "feed_url": feed_url,
            "webcal_url": feed_url.replace("https://", "webcal://", 1).replace("http://", "webcal://", 1),
            "scope": self._scope_key(user),
            "scope_label": self._scope_label(user),
        }

    def regenerate_feed_token(self, user: User) -> dict[str, str]:
        user.calendar_feed_token = secrets.token_urlsafe(32)
        self.users.update(user)
        self.db.commit()
        return self.get_feed_info(user)

    def build_feed_for_token(self, token: str) -> tuple[str, str]:
        user = self.users.get_by_calendar_feed_token(token)
        if not user or not user.organization:
            raise not_found("Enlace de calendario no válido")

        org = user.organization
        tz = org_timezone(org)
        now_local = datetime.now(timezone.utc).astimezone(tz)
        start_date = now_local.date() - timedelta(days=self.settings.calendar_feed_days_past)
        end_date = now_local.date() + timedelta(days=self.settings.calendar_feed_days_future + 1)

        professional_id = user.id if user.role == UserRole.PROFESSIONAL else None
        appointments = self.appointments.list_for_calendar_feed(
            org.id,
            start_date=start_date,
            end_date_exclusive=end_date,
            professional_id=professional_id,
        )

        calendar_name = (
            f"AppMedica — {user.full_name}"
            if user.role == UserRole.PROFESSIONAL
            else f"AppMedica — {org.name}"
        )
        body = build_ics_calendar(
            calendar_name=calendar_name,
            appointments=appointments,
            tz=tz,
            app_url=self.settings.public_app_url,
        )
        filename = "appmedica-agenda.ics"
        return body, filename

    def _ensure_feed_token(self, user: User) -> str:
        if user.calendar_feed_token:
            return user.calendar_feed_token
        user.calendar_feed_token = secrets.token_urlsafe(32)
        self.users.update(user)
        self.db.commit()
        self.db.refresh(user)
        return user.calendar_feed_token  # type: ignore[return-value]

    def _build_feed_url(self, token: str) -> str:
        base = self.settings.public_app_url.rstrip("/")
        api_base = base if base.endswith("/api/v1") else f"{base}/api/v1"
        return f"{api_base}/calendar/feed/{token}"

    def _scope_key(self, user: User) -> str:
        return "professional" if user.role == UserRole.PROFESSIONAL else "organization"

    def _scope_label(self, user: User) -> str:
        if user.role == UserRole.PROFESSIONAL:
            return "Solo tus turnos"
        return "Todos los turnos del consultorio"
