"""Zona horaria del consultorio (organizations.timezone)."""

from zoneinfo import ZoneInfo

from app.models.organization import Organization

DEFAULT_ORG_TIMEZONE = "America/Argentina/Buenos_Aires"


def org_timezone(org: Organization) -> ZoneInfo:
    """Resuelve la zona IANA del consultorio con fallback seguro."""
    try:
        return ZoneInfo(org.timezone or DEFAULT_ORG_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_ORG_TIMEZONE)
