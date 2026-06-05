# Recordatorios — estrategia de costo mínimo

## Resumen diario para el profesional (agenda de mañana)

Cada noche (por defecto **21:00**, hora del consultorio — cuando el día ya cerró) se envía un email con los turnos **del día siguiente**:

| Rol | Qué recibe |
|-----|------------|
| **Profesional** | Solo sus turnos (pendientes y confirmados) |
| **Dueño (owner)** | Todos los turnos del consultorio, agrupados por profesional |

Requisitos: `EMAIL_PROVIDER=smtp` (Hostinger) o `mock` (desarrollo, solo logs). Sin costo extra de APIs.

```env
DAILY_AGENDA_DIGEST_ENABLED=true
DAILY_AGENDA_DIGEST_HOUR=21
DAILY_AGENDA_DIGEST_MINUTE=0
EMAIL_PROVIDER=smtp
# ... SMTP_HOST, SMTP_USER, etc.
PUBLIC_APP_URL=https://app.daminatoweb.com
```

El email incluye hora, paciente, DNI, teléfono, estado y un enlace a la agenda. No se envía dos veces el mismo día (tabla `daily_digest_logs`).

Cron opcional en el VPS (si preferís no depender del loop del backend):

```cron
0 23 * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml exec -T backend python scripts/send_daily_agenda.py
```

(Ajustá la hora del cron según la zona horaria del servidor.)

---

## Recomendación actual (casi $0)

| Canal | Cómo | Costo |
|-------|------|--------|
| **WhatsApp** | Botón **WhatsApp** en la agenda → abre `wa.me` con el texto listo. Lo envía el consultorio desde su celular. | **$0** |
| **Email automático** | Solo si activás SMTP de tu hosting (ej. correo de Hostinger con daminatoweb.com). | **$0** (incluido en el plan) |
| **Twilio / Meta API** | Desactivado por defecto. Activar solo cuando quieras pagar envío automático. | De pago |

Config por defecto en el proyecto:

```env
WHATSAPP_PROVIDER=disabled
EMAIL_PROVIDER=mock
REMINDERS_ENABLED=true
```

Con eso **no se crean jobs de WhatsApp** en la base ni se llama a APIs de pago. El email automático queda en logs hasta que configures SMTP gratis.

---

## Activar email automático gratis (Hostinger)

Si tenés casilla de correo en Hostinger:

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=noreply@tudominio.com
SMTP_PASSWORD=contraseña-del-correo
SMTP_FROM_EMAIL=noreply@tudominio.com
SMTP_USE_TLS=true
PUBLIC_APP_URL=https://app.daminatoweb.com
```

Ahí sí se programan recordatorios por email 24 h antes del turno (si el paciente tiene email).

---

## WhatsApp manual desde la agenda

1. El paciente debe tener **teléfono** cargado.
2. En un turno pendiente o confirmado, clic en **WhatsApp**.
3. Se abre WhatsApp Web o la app con el mensaje armado.
4. Vos tocás Enviar.

Sin Twilio, sin Meta, sin mensajes por conversación.

---

## Cuándo activar APIs de pago (futuro)

Solo si querés envío **100% automático** por WhatsApp:

```env
WHATSAPP_PROVIDER=twilio   # o meta
# + credenciales del proveedor
```

| Proveedor | Orden de magnitud |
|-----------|-------------------|
| Twilio WhatsApp | ~USD 0,05–0,10 por conversación |
| Meta Cloud API | Variable; cuenta business + plantillas |

---

## Variables útiles

```env
REMINDERS_ENABLED=true
REMINDER_HOURS_BEFORE=24
REMINDER_BACKGROUND_LOOP=true
EMAIL_PROVIDER=mock|smtp|disabled
WHATSAPP_PROVIDER=disabled|mock|twilio|meta
```

- `mock`: prueba en logs del servidor (desarrollo).
- `disabled`: no programa ese canal.

## API (opcional)

- `GET /api/v1/reminders` — cola de envíos automáticos (solo si usás SMTP/API).
- `POST /api/v1/reminders/process-due` — owner, forzar procesamiento.

## Cron

Solo necesario si usás `EMAIL_PROVIDER=smtp`:

```bash
docker compose exec backend python scripts/process_reminders.py
```

Con solo WhatsApp manual (`disabled`), el cron no hace falta.
