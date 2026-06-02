import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    PROFESSIONAL = "professional"
    STAFF = "staff"


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class AppointmentModality(str, enum.Enum):
    IN_PERSON = "presencial"
    ONLINE = "online"


class AttentionType(str, enum.Enum):
    PRIVATE = "private"
    HEALTH_INSURANCE = "health_insurance"


class AppointmentClosureStatus(str, enum.Enum):
    NONE = "none"
    PAID = "paid"
    PENDING = "pending"
    PARTIAL = "partial"
    INSURANCE_PENDING = "insurance_pending"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    MERCADOPAGO = "mercadopago"
    HEALTH_INSURANCE = "health_insurance"


class InsuranceClaimStatus(str, enum.Enum):
    PENDING = "pending"
    INVOICED = "invoiced"
    COLLECTED = "collected"
    REJECTED = "rejected"


class ReminderChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class ReminderStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
