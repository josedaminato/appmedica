import uuid

from datetime import date, datetime



from pydantic import BaseModel, EmailStr, Field



from app.models.enums import UserRole

from app.models.patient import Patient

from app.models.user import User





class PatientBase(BaseModel):

    first_name: str = Field(min_length=1, max_length=120)

    last_name: str = Field(min_length=1, max_length=120)

    dni: str = Field(min_length=7, max_length=20)

    phone: str | None = Field(default=None, max_length=30)

    email: EmailStr | None = None

    birth_date: date | None = None

    health_insurance_id: uuid.UUID | None = None

    affiliate_number: str | None = Field(default=None, max_length=50)

    notes: str | None = None

    is_active: bool = True





class PatientCreate(PatientBase):

    pass





class PatientUpdate(BaseModel):

    first_name: str | None = Field(default=None, min_length=1, max_length=120)

    last_name: str | None = Field(default=None, min_length=1, max_length=120)

    dni: str | None = Field(default=None, min_length=7, max_length=20)

    phone: str | None = Field(default=None, max_length=30)

    email: EmailStr | None = None

    birth_date: date | None = None

    health_insurance_id: uuid.UUID | None = None

    affiliate_number: str | None = Field(default=None, max_length=50)

    notes: str | None = None

    is_active: bool | None = None





class PatientAdminResponse(BaseModel):

    """Respuesta administrativa de paciente (sin datos clínicos)."""



    id: uuid.UUID

    organization_id: uuid.UUID

    first_name: str

    last_name: str

    dni: str | None = None

    phone: str | None = None

    email: EmailStr | None = None

    birth_date: date | None = None

    health_insurance_id: uuid.UUID | None = None

    affiliate_number: str | None = None

    notes: str | None = None

    is_active: bool = True

    created_at: datetime

    updated_at: datetime



    model_config = {"from_attributes": True}





class PatientResponse(BaseModel):

    id: uuid.UUID

    organization_id: uuid.UUID

    first_name: str

    last_name: str

    dni: str | None = None

    phone: str | None = None

    email: EmailStr | None = None

    birth_date: date | None = None

    health_insurance_id: uuid.UUID | None = None

    affiliate_number: str | None = None

    notes: str | None = None

    medical_history: str | None = None

    allergies: str | None = None

    current_medications: str | None = None

    clinical_notes: str | None = None

    is_active: bool = True

    created_at: datetime

    updated_at: datetime



    model_config = {"from_attributes": True}





CLINICAL_PATIENT_FIELDS = (

    "medical_history",

    "allergies",

    "current_medications",

    "clinical_notes",

)





def patient_response_for_user(
    patient: Patient,
    user: User,
    *,
    has_clinical_relationship: bool = False,
) -> PatientAdminResponse | PatientResponse:
    if user.role == UserRole.STAFF:
        return PatientAdminResponse.model_validate(patient)
    if user.role == UserRole.PROFESSIONAL and not has_clinical_relationship:
        return PatientAdminResponse.model_validate(patient)
    return PatientResponse.model_validate(patient)


