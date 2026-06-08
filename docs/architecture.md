# AppMedica — Arquitectura

SaaS administrativo para profesionales de la salud en Argentina.

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | React 19, Vite, TypeScript, Tailwind 4, shadcn/ui, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic, JWT |
| Base de datos | PostgreSQL 16 |
| Dev | Docker Compose, `start.ps1` (Windows) |
| Producción | Docker + Nginx host → ver [DEPLOY.md](./DEPLOY.md) |
| CI | GitHub Actions: pytest + cobertura, build frontend |

## Capas backend

```
API (routers) → Services (negocio) → Repositories (datos) → Models (ORM)
```

## Multi-tenant

Todo recurso pertenece a una `Organization`. El JWT incluye `organization_id`; los endpoints filtran por el consultorio del usuario autenticado.

## RBAC

| Rol | Alcance |
|-----|---------|
| `owner` | Todo el consultorio; gestión de equipo |
| `staff` | Consultorio completo; no puede dar de baja pacientes |
| `professional` | Solo su cartera (turnos/cobros filtrados por `professional_id`) |

Reglas en `app/core/rbac.py`; filtro aplicado en agenda, cobros y resúmenes.

## Módulos

| Módulo | Estado |
|--------|--------|
| Auth (registro, login, reset mock) | ✅ |
| Dashboard + alertas operativas | ✅ |
| Pacientes (CRUD, import Excel/CSV) | ✅ |
| Agenda (estados, cierre, reprogramar, cobro) | ✅ |
| Obras sociales (catálogo, reclamos, ranking) | ✅ |
| Cobros (`/payments`) | ✅ |
| Reportes mensuales + export | ✅ |
| Equipo (CRUD usuarios, solo owner) | ✅ |
| Exportación (pacientes, deuda, pagos, reclamos) | ✅ |
| Recordatorios | ✅ WhatsApp manual (wa.me, $0); email vía SMTP Hostinger opcional — [REMINDERS.md](./REMINDERS.md) |
| Deep links (agenda, cobros, OS, dashboard) | ✅ |

## Integraciones futuras

- `app/integrations/reminders/` — adapters WhatsApp y email (stubs)

## Repositorio

https://github.com/josedaminato/appmedica
