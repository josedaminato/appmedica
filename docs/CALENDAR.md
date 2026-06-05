# Calendario externo (feed iCal)

Sincronización **solo lectura** con Google Calendar, Outlook o Apple. Costo **$0** (sin API de Google).

## Uso

1. En **Agenda** → botón **Calendario**
2. Copiá el enlace de suscripción
3. En Google Calendar: **Configuración → Añadir calendario → Desde URL**
4. Pegá el enlace y guardá

El calendario se actualiza solo cada pocas horas (comportamiento del cliente).

## Alcance

| Rol | Turnos en el feed |
|-----|-------------------|
| Profesional | Solo los suyos |
| Dueño / staff | Todo el consultorio |

## Seguridad

- Cada usuario tiene un **token secreto** en la URL
- **Regenerar enlace** invalida el anterior
- No permite crear ni editar turnos desde Google

## Migración

```bash
alembic upgrade head
```

Incluye columna `users.calendar_feed_token`.

## Variables opcionales

```env
CALENDAR_FEED_DAYS_PAST=7
CALENDAR_FEED_DAYS_FUTURE=90
PUBLIC_APP_URL=https://app.daminatoweb.com
```

El feed excluye turnos cancelados, reprogramados y ausentes.
