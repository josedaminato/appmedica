# Pasos finales — AppMedica en producción

URL objetivo: **https://app.daminatoweb.com**

---

## Lo que ya está listo en el repo

- Configuración alineada (`CORS_ORIGINS`, `PUBLIC_APP_URL`, `VITE_API_URL`)
- Scripts de deploy: `scripts/deploy-remote.ps1`, `scripts/run-prod-checklist.ps1`
- Validación local: `scripts/validate-env-prod.ps1`
- Nginx: `nginx/app.daminatoweb.com.conf` (puerto frontend **3002**)

---

## Paso 1 — Completar contraseña del correo (solo vos)

1. Entrá a **hPanel → Correos → contacto@daminatoweb.com**
2. Copiá la contraseña del buzón
3. En tu PC, abrí el archivo:

   ```
   C:\Users\damin\OneDrive\Desktop\appmedica\backend\.env.prod
   ```

4. Cambiá esta línea (reemplazá `TU_PASSWORD`):

   ```
   SMTP_PASSWORD=TU_PASSWORD
   ```

5. Guardá el archivo.

---

## Paso 2 — Validar configuración local

En PowerShell:

```powershell
cd C:\Users\damin\OneDrive\Desktop\appmedica
.\scripts\validate-env-prod.ps1
```

Si hay avisos de `SMTP_PASSWORD`, corregilos en el Paso 1.

---

## Paso 3 — Subir cambios a GitHub (si aún no lo hiciste)

En PowerShell, desde la carpeta del proyecto:

```powershell
cd C:\Users\damin\OneDrive\Desktop\appmedica
git add .
git status
git commit -m "Alinear config produccion app.daminatoweb.com y scripts de deploy"
git push origin main
```

*(Si `git push` pide credenciales, usá tu usuario y token de GitHub.)*

---

## Paso 4 — Deploy al VPS (te pide contraseña SSH)

Contraseña: **hPanel → VPS → SSH** (no la del correo, no la del hosting PHP).

```powershell
cd C:\Users\damin\OneDrive\Desktop\appmedica
.\scripts\deploy-remote.ps1
```

O con contraseña SMTP en el mismo paso:

```powershell
.\scripts\run-prod-checklist.ps1 -SmtpPassword 'TU_PASSWORD_CORREO'
```

El script hace automáticamente:

1. Sube `backend/.env.prod` al servidor
2. `git pull` + build Docker + migraciones
3. Configura nginx para `app.daminatoweb.com`
4. Backup, cron y smoke test

---

## Paso 5 — SSL (solo la primera vez en el VPS)

Si https://app.daminatoweb.com da error de certificado, conectate al VPS:

```powershell
ssh root@72.60.166.24
```

En el servidor:

```bash
sudo certbot --nginx -d app.daminatoweb.com
```

Seguí las preguntas (email, aceptar términos, redirect a HTTPS).

---

## Paso 6 — Verificar en el navegador

| Prueba | URL |
|--------|-----|
| Health API | https://app.daminatoweb.com/api/v1/health |
| Registro | https://app.daminatoweb.com/register |
| Login | https://app.daminatoweb.com/login |
| Olvidé contraseña | https://app.daminatoweb.com/forgot-password |

Checklist funcional:

1. Registro de consultorio nuevo
2. Crear obra social
3. Crear paciente
4. Crear turno en agenda
5. Cerrar turno + registrar cobro
6. Exportar deuda en pagos
7. Probar forgot-password con email real (debe llegar el correo)

---

## Si algo falla

| Síntoma | Qué hacer |
|---------|-----------|
| `Permission denied` en SSH | Contraseña del **VPS** en hPanel, usuario `root`, puerto **22** |
| CORS error en el navegador | Verificar `CORS_ORIGINS=https://app.daminatoweb.com` en el VPS: `cat /opt/appmedica/backend/.env.prod` |
| 404 en `/api/v1/health` | Nginx mal configurado: repetir Paso 4 o copiar nginx manualmente |
| SSL roto | Paso 5 (certbot) |
| Email no llega | Revisar `SMTP_PASSWORD` y que el buzón `contacto@daminatoweb.com` exista en Hostinger |
| Link de reset va a localhost | Falta `PUBLIC_APP_URL` — volver a correr `deploy-remote.ps1` |

---

## DNS (verificar una vez)

En hPanel → Dominios → DNS:

| Tipo | Nombre | Valor |
|------|--------|-------|
| A | `app` | `72.60.166.24` |

---

## Comandos útiles después del lanzamiento

```powershell
# Re-deploy tras cambios
.\scripts\deploy-remote.ps1

# Solo validar .env local
.\scripts\validate-env-prod.ps1
```

En el VPS:

```bash
cd /opt/appmedica
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod ps
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod logs -f backend
```
