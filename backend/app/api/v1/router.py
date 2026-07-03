from fastapi import APIRouter

from app.api.v1.endpoints import (
    appointments,
    auth,
    calendar,
    dashboard,
    dashboard_alerts,
    exports,
    health,
    health_insurances,
    insurance_claims,
    imports,
    organizations,
    payments,
    patients,
    platform,
    reports,
    reminders,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(platform.router)
api_router.include_router(dashboard.router)
api_router.include_router(dashboard_alerts.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(patients.router)
api_router.include_router(appointments.router)
api_router.include_router(calendar.router)
api_router.include_router(health_insurances.router)
api_router.include_router(insurance_claims.router)
api_router.include_router(payments.router)
api_router.include_router(exports.router)
api_router.include_router(imports.router)
api_router.include_router(reports.router)
api_router.include_router(reminders.router)
