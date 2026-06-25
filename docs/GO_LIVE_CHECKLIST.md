# AppMedica — Checklist de salida a producción (go-live)

Pasos reproducibles para verificar que el entorno está listo antes del **primer cliente pago**.

Ejecutar en el VPS (`/opt/appmedica`) salvo que se indique lo contrario.

---

## 0. Prerrequisitos

```bash
cd /opt/appmedica
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod ps
```

**Esperado:** `backend`, `frontend`, `db` en estado `running` / `healthy`.

---

## 1. Variables de entorno obligatorias

```bash
grep -E '^(APP_ENV|JWT_SECRET|REGISTRATION_ENABLED|EMAIL_PROVIDER|SMTP_HOST|SMTP_USER|SMTP_PASSWORD|REMINDER_BACKGROUND_LOOP|CORS_ORIGINS|PUBLIC_APP_URL)=' backend/.env.prod
```

| Variable | Valor esperado |
|----------|----------------|
| `APP_ENV` | `production` |
| `JWT_SECRET` | ≥ 32 caracteres, no el valor por defecto |
| `REGISTRATION_ENABLED` | `false` |
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Configurados (Hostinger u otro) |
| `REMINDER_BACKGROUND_LOOP` | `false` |
| `CORS_ORIGINS` | Dominio(s) real(es), sin `*` |
| `PUBLIC_APP_URL` | `https://daminatoweb.com` (o tu dominio) |

**Verificar que el backend arranca con config segura:**

```bash
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python -c "
from app.core.config import Settings
s = Settings()
print('OK production config' if s.is_production and not s.registration_enabled else 'REVISAR')
"
```

**Esperado:** `OK production config`. Si falla al arrancar con `REGISTRATION_ENABLED=true`, corregir `.env.prod`.

---

## 2. Health check

```bash
curl -fsS https://daminatoweb.com/api/v1/health
```

**Esperado:** `{"status":"ok","database":"ok"}`

---

## 3. Backups automáticos

### 3.1 Cron configurado

```bash
crontab -l | grep backup-db.sh
```

**Esperado:** línea similar a:

```
0 3 * * * cd /opt/appmedica && bash scripts/backup-db.sh >> /var/log/appmedica-backup.log 2>&1
```

### 3.2 Backup manual

```bash
cd /opt/appmedica && bash scripts/backup-db.sh
ls -lh backups/ | tail -3
```

**Esperado:** archivo `appmedica-YYYY-MM-DD_HHMMSS.sql.gz` recién creado.

### 3.3 Restauración (prueba en entorno aislado)

> No restaurar sobre producción activa. Usar una copia del `.sql.gz` en un contenedor temporal.

```bash
# En directorio de prueba (NO sobre prod en uso):
BACKUP=$(ls -t /opt/appmedica/backups/appmedica-*.sql.gz | head -1)
gunzip -c "$BACKUP" | docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T db \
  psql -U appmedica -d appmedica_restore_test -f - 2>/dev/null || echo "Crear DB de prueba primero"
```

**Criterio mínimo:** el backup se genera sin error y el archivo es > 0 bytes. Restauración completa probada al menos una vez antes del primer cliente.

---

## 4. SMTP y recuperación de contraseña

### 4.1 SMTP configurado

```bash
grep '^SMTP_PASSWORD=' backend/.env.prod | grep -v CAMBIAR
```

**Esperado:** contraseña real (no placeholder).

### 4.2 Prueba forgot-password (manual)

1. Abrir `https://daminatoweb.com/forgot-password`
2. Ingresar email de un usuario owner de prueba
3. Verificar recepción del correo (o logs si está en mock)

**Esperado:** correo recibido con enlace de reset en < 2 minutos.

---

## 5. Cron — recordatorios y digest diario

```bash
crontab -l | grep -E 'process_reminders|send_daily_agenda'
```

**Esperado:**

```
*/5 * * * * ... process_reminders.py ...
0 0 * * * ... send_daily_agenda.py ...
```

### 5.1 Ejecución manual de recordatorios

```bash
cd /opt/appmedica
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/process_reminders.py
echo "exit: $?"
```

**Esperado:** exit code 0 (sin traceback).

### 5.2 Ejecución manual del digest

```bash
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/send_daily_agenda.py
echo "exit: $?"
```

**Esperado:** exit code 0.

### 5.3 Logs recientes

```bash
tail -20 /var/log/appmedica-reminders.log 2>/dev/null || echo "Sin log aún"
tail -20 /var/log/appmedica-digest.log 2>/dev/null || echo "Sin log aún"
```

---

## 6. Registro público deshabilitado

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST https://daminatoweb.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"organization_name":"Test","full_name":"Test","email":"blocked@test.com","password":"testpass123"}'
```

**Esperado:** `403`

---

## 7. Smoke funcional (manual, 10 min)

Con un usuario owner de prueba en `https://daminatoweb.com`:

1. Login
2. Crear paciente
3. Crear turno
4. Marcar **Asistió**
5. Cerrar turno (cobro parcial o total)
6. Ver deuda en **Cobros**
7. Abrir **Inicio** → alertas cargan sin error (HTTP 200)

---

## 8. Feed iCal (privacidad)

1. En la app: obtener enlace de calendario
2. Abrir `https://daminatoweb.com/api/v1/calendar/feed/{token}` en navegador
3. Verificar que el `.ics` **no** contiene nombres de pacientes ni DNI

**Esperado:** `SUMMARY:Turno AppMedica` y profesional en descripción; sin datos identificatorios del paciente.

---

## 9. Tests automatizados (antes de cada deploy)

En máquina de desarrollo o CI:

```bash
cd backend
python -m pytest tests/test_config_security.py tests/test_tenant_validation.py \
  tests/test_appointment_closure_concurrency.py tests/test_appointment_booking_concurrency.py \
  tests/test_calendar_feed.py tests/test_critical_flows.py tests/test_dashboard_alerts.py -v
```

**Esperado:** todos los tests en verde.

---

## 10. Criterio de go-live

Marcar **LISTO** solo si:

- [ ] Health OK
- [ ] `REGISTRATION_ENABLED=false` y backend arranca
- [ ] Backup manual OK + cron activo
- [ ] SMTP + forgot-password probados
- [ ] Cron recordatorios y digest activos
- [ ] Smoke funcional completo
- [ ] Feed iCal sin PHI de pacientes
- [ ] Suite de tests críticos en verde

---

## Onboarding del primer cliente pago

1. Crear organización manualmente (SQL o script interno) — **no** vía registro público.
2. Crear usuario owner con contraseña temporal.
3. Entregar credenciales por canal seguro.
4. Verificar checklist de este documento en prod.
5. Rotar enlace iCal si se compartió durante pruebas.
