# Pasos finales — AppMedica en producción

URL: **https://daminatoweb.com** (landing + AppMedica en el mismo sitio)

---

## Un solo comando (recomendado)

### Desde Windows (PowerShell)

```powershell
cd C:\Users\damin\OneDrive\Desktop\appmedica
.\scripts\finalize-vps.ps1
```

Te pide la contraseña SSH del VPS **una o dos veces**. Esperá 5–10 minutos.

### O desde el VPS (si ya estás conectado por SSH)

```bash
cd /opt/appmedica
git pull origin main
chmod +x scripts/vps-finish-install.sh
bash scripts/vps-finish-install.sh
```

Eso hace todo: DB nueva, deploy, nginx, cron.

---

## Antes de ejecutar

1. Completá `SMTP_PASSWORD` en `backend\.env.prod` (correo contacto@daminatoweb.com)
2. Validá: `.\scripts\validate-env-prod.ps1`

---

## Después — probar en el navegador

| Qué | URL |
|-----|-----|
| Landing | https://daminatoweb.com |
| Registro AppMedica | https://daminatoweb.com/register |
| API health | https://daminatoweb.com/api/v1/health |

Si HTTPS no abre (solo HTTP), en el VPS una vez:

```bash
sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com
```

---

## Si falla SSH

| Error | Solución |
|-------|----------|
| Permission denied | hPanel → VPS → Reset root password |
| Mejor sin contraseña | hPanel → VPS → SSH keys → agregar tu clave pública |
| Sin SSH desde PC | hPanel → VPS → **Browser terminal** → pegar comandos de arriba |

---

## Detalle técnico (por qué fallaba antes)

PostgreSQL guarda la contraseña del **primer** deploy. Cambiar `.env.prod` no la actualiza sola.  
`vps-finish-install.sh` recrea el volumen con la contraseña correcta y alinea nginx a `daminatoweb.com`.

