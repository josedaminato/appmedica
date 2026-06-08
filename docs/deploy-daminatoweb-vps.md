# Deploy AppMedica en daminatoweb.com

AppMedica vive en el **dominio raíz**: landing en `/`, app en `/login`, `/register`, `/inicio`, etc., API en `/api/v1`.

| Dato | Valor |
|------|--------|
| VPS Hostinger KVM | `72.60.166.24` (ID 1035833) |
| SSH | `ssh root@72.60.166.24` (puerto **22**, no el 65002 del hosting PHP) |
| URL final | https://daminatoweb.com |

---

## Arquitectura

```
Internet → Nginx host (:80 / :443)
              ├── /api/  → 127.0.0.1:8000 (FastAPI)
              └── /      → 127.0.0.1:3000 (React build + landing)
                                    └── PostgreSQL (solo red Docker interna)
```

---

## 1. DNS (hPanel → Dominios)

| Tipo | Nombre | Valor |
|------|--------|-------|
| A | `@` | `72.60.166.24` |
| A o CNAME | `www` | `daminatoweb.com` o la misma IP |

---

## 2. Preparar el VPS (una sola vez)

```bash
ssh root@72.60.166.24

# Instalar Docker, Nginx, Certbot, UFW
bash /opt/appmedica/scripts/setup-vps.sh
# (si el repo aún no está, clonalo primero — paso 3)
```

Firewall hPanel: abrir **22**, **80**, **443**. **No** abrir 5432.

---

## 3. Subir el código

```bash
mkdir -p /opt/appmedica
cd /opt/appmedica
git clone https://github.com/josedaminato/appmedica.git .
```

---

## 4. Variables de producción

```bash
cp backend/.env.prod.example backend/.env.prod
nano backend/.env.prod
```

**Cambiar obligatorio:**

```bash
openssl rand -hex 32   # → JWT_SECRET
```

| Variable | Valor |
|----------|--------|
| `POSTGRES_PASSWORD` | Password fuerte (mismo en `DATABASE_URL`) |
| `JWT_SECRET` | Output de openssl (≥32 chars) |
| `SEED_DEMO` | `0` |
| `CORS_ORIGINS` | `https://daminatoweb.com,https://www.daminatoweb.com` |
| `VITE_API_URL` | `/api/v1` |
| `PUBLIC_APP_URL` | `https://daminatoweb.com` |

**SMTP (recomendado para reset de contraseña y emails):**

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=noreply@daminatoweb.com
SMTP_PASSWORD=<password del correo>
SMTP_FROM_EMAIL=noreply@daminatoweb.com
```

---

## 5. Nginx del host

```bash
cd /opt/appmedica
sudo cp nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf
sudo ln -sf /etc/nginx/sites-available/daminatoweb.com.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 6. Primer deploy

```bash
cd /opt/appmedica
bash scripts/deploy.sh
```

Verificar en el VPS:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/
```

Probar en navegador: **http://daminatoweb.com** (landing + links a registro).

---

## 7. HTTPS

```bash
sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com
```

Verificar:

```bash
curl -s https://daminatoweb.com/api/v1/health
```

URLs finales:

| Qué | URL |
|-----|-----|
| Landing | https://daminatoweb.com |
| Registro | https://daminatoweb.com/register |
| Login | https://daminatoweb.com/login |
| Panel | https://daminatoweb.com/inicio |
| API health | https://daminatoweb.com/api/v1/health |

---

## 8. Checklist post-deploy

- [ ] Registro de consultorio nuevo funciona
- [ ] Cargar obras sociales en **Mis obras sociales**
- [ ] Paciente + turno + cierre + cobro
- [ ] Export Excel
- [ ] Recuperar contraseña (requiere SMTP)
- [ ] Backup DB programado (ver abajo)

---

## Actualizar después de cambios

```bash
cd /opt/appmedica
bash scripts/deploy.sh
```

---

## Backup PostgreSQL (manual)

```bash
cd /opt/appmedica
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T db \
  pg_dump -U appmedica appmedica > backup-$(date +%F).sql
```

Programar con cron o backups de Hostinger.

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Conexión rechazada | `docker compose -f docker-compose.prod.yml --env-file backend/.env.prod ps` |
| 502 Bad Gateway | `docker compose ... logs backend --tail=50` |
| CORS | `CORS_ORIGINS` debe coincidir con la URL del navegador (con/sin www) |
| Página en blanco | Rebuild frontend: `deploy.sh` o `docker compose ... build frontend --no-cache` |
| Backend no arranca | Revisar `JWT_SECRET` y `POSTGRES_PASSWORD` en `.env.prod` |

---

## Nota sobre subdominio

Si preferís `app.daminatoweb.com` en lugar de la raíz, usá `nginx/app.daminatoweb.com.conf` y ajustá URLs en `.env.prod`. Para tu caso (landing + app en daminatoweb.com), usá **`nginx/daminatoweb.com.conf`**.
