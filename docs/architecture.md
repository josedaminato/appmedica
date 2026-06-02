# AppMedica — Arquitectura

SaaS administrativo para profesionales de la salud en Argentina.

## Stack

- **Frontend:** React, Vite, TypeScript, Tailwind, shadcn/ui
- **Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Auth:** JWT
- **Infra dev:** Docker Compose

## Capas backend

```
API (routers) → Services (negocio) → Repositories (datos) → Models (ORM)
```

## Multi-tenant

Todo recurso pertenece a una `Organization`. El JWT incluye `organization_id` y los endpoints filtran por el usuario autenticado.

## Módulos

| Fase | Módulo | Estado |
|------|--------|--------|
| 1 | Auth, Pacientes, Dashboard shell | ✅ |
| 2 | Agenda y turnos, cierre administrativo | ✅ |
| 3 | Obras sociales | ✅ (catálogo) |
| 3b | Importación pacientes desde Excel | ✅ (mapeo asistido) |
| 3c | Reclamos OS + ranking de demoras de pago | ✅ |
| 4 | Cobros (módulo dedicado) | Pendiente |
| 5 | Reportes | Pendiente |
| 6 | Recordatorios (integración) | Estructura preparada |

## Integraciones futuras

- `app/integrations/reminders/` — adapters WhatsApp y email (stubs)
