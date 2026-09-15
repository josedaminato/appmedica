from app.core.exceptions import AppException
from app.models.enums import ConsultationStatus, UserRole
from app.models.user import User
from fastapi import status


def forbidden(message: str = "No tenés permiso para esta acción") -> AppException:
    return AppException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def assert_can_delete(user: User) -> None:
    if user.role == UserRole.STAFF:
        raise forbidden("El rol staff no puede eliminar registros")


def assert_owner(user: User) -> None:
    if user.role != UserRole.OWNER:
        raise forbidden("Solo el owner puede gestionar el equipo")


def resolve_professional_filter(
    user: User,
    requested_professional_id,
):
    """Professional solo ve su cartera; owner/staff ven todo el consultorio."""
    if user.role == UserRole.PROFESSIONAL:
        return user.id
    return requested_professional_id


def assert_can_access_appointment(user: User, appointment) -> None:
    """Professional solo puede operar sus propios turnos.

    Owner y staff operan cualquier turno del consultorio. El aislamiento entre
    consultorios ya lo garantiza el filtro por organization_id en las consultas.
    """
    if user.role == UserRole.PROFESSIONAL and appointment.professional_id != user.id:
        raise forbidden("Solo podés operar tus propios turnos")


def assert_clinical_access(user: User) -> None:
    """Staff no tiene acceso a información clínica en esta versión."""
    if user.role == UserRole.STAFF:
        raise forbidden("El rol staff no tiene acceso a información clínica")


def assert_can_read_consultation(
    user: User,
    consultation,
    *,
    has_relationship: bool = False,
) -> None:
    """Owner: toda la org. Professional: propias, o finalized de colegas con relación."""
    assert_clinical_access(user)
    if user.role != UserRole.PROFESSIONAL:
        return
    if consultation.professional_id == user.id:
        return
    status_value = getattr(consultation.status, "value", consultation.status)
    if status_value == ConsultationStatus.FINALIZED.value and has_relationship:
        return
    raise forbidden("Solo podés acceder a tus propias consultas")


def assert_can_access_consultation(user: User, consultation) -> None:
    """Escritura: owner org-wide; professional solo consultas propias."""
    assert_can_modify_consultation(user, consultation)


def assert_can_modify_consultation(user: User, consultation) -> None:
    """Owner: toda la org. Professional: solo las propias. Staff: bloqueado."""
    assert_clinical_access(user)
    if user.role == UserRole.PROFESSIONAL and consultation.professional_id != user.id:
        raise forbidden("No podés modificar consultas de otro profesional")


def assert_can_access_patient_clinical_profile(user: User, *, has_relationship: bool) -> None:
    """Owner: org-wide. Professional: solo pacientes con relación. Staff: bloqueado."""
    assert_clinical_access(user)
    if user.role == UserRole.PROFESSIONAL and not has_relationship:
        raise forbidden("No tenés relación clínica con este paciente")


def assert_can_create_standalone_consultation(user: User) -> None:
    """Primera nota sin turno: no exige Appointment ni Consultation previa.

    Staff: bloqueado. Owner y professional de la org autenticada: permitido.
    El aislamiento de paciente lo aplica el servicio por organization_id.
    No otorga lectura del perfil clínico ni del timeline.
    """
    assert_clinical_access(user)
