# Deploy AppMedica en VPS (Ubuntu 24.04 LTS)

Objetivo: **https://app.daminatoweb.com**

## Arquitectura

| Componente | Puerto host | Descripción |
|------------|-------------|-------------|
| Nginx (host) | 80 / 443 | Proxy público + SSL (Certbot) |
| Frontend Docker | `127.0.0.1:3000` | React build + nginx:alpine |
| Backend Docker | `127.0.0.1:8000` | FastAPI + Uvicorn |
| PostgreSQL | *(interno)* | Sin puerto expuesto |

## Requisitos previos

- VPS Ubuntu 24.04 con acceso SSH (`root` o usuario con `sudo`)
- DNS: registro **A** `app` → IP del VPS
- Repositorio Git con el código de AppMedica

---

## 1. Conectarse al VPS

```bash
ssh root@IP_DEL_VPS
```

*(Reemplazá `IP_DEL_VPS` por la IP real, ej. `45.152.46.212`.)*

---

## 2. Instalación inicial del servidor

Desde el repo (después de clonar) o copiando el script:

```bash
bash scripts/setup-vps.sh
```

Instala: Docker (repo oficial), Nginx, Certbot, UFW, crea `/opt/appmedica`.

---

## 3. Clonar el repositorio

```bash
cd /opt/appmedica
git clone URL_DE_TU_REPO .
```

Ejemplo:

```bash
git clone https://github.com/tu-usuario/appmedica.git .
```

---

## 4. Variables de entorno

```bash
cp backend/.env.prod.example backend/.env.prod
nano backend/.env.prod
```

**Obligatorio cambiar:**

- `POSTGRES_PASSWORD` — password fuerte
- `DATABASE_URL` — mismo password que arriba
- `JWT_SECRET` — generar con: `openssl rand -hex 32`

**Verificar:**

- `APP_ENV=production`
- `CORS_ORIGINS=https://app.daminatoweb.com`
- `VITE_API_URL=https://app.daminatoweb.com/api/v1`
- `SEED_DEMO=0` (salvo prueba inicial)

---

## 5. Configurar Nginx en el host

```bash
sudo cp nginx/app.daminatoweb.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/app.daminatoweb.com.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # opcional, si choca el default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Certificado SSL

```bash
sudo certbot --nginx -d app.daminatoweb.com
```

Seguí las preguntas de Certbot (email, términos, redirect HTTPS).

---

## 7. Primer deploy

```bash
cd /opt/appmedica
bash scripts/deploy.sh
```

El script hace: `git pull`, `docker compose build`, `up -d`, `alembic upgrade head`.

---

## 8. Verificar

```bash
curl -s https://app.daminatoweb.com/api/v1/health
```

En el navegador:

- https://app.daminatoweb.com
- https://app.daminatoweb.com/register

---

## 9. Datos demo (opcional)

Solo para staging o primera prueba:

```bash
cd /opt/appmedica
# En backend/.env.prod poner SEED_DEMO=1 y redeploy, o ejecutar:
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec backend python scripts/seed_demo.py
```

Cuenta demo: `demo@consultorio.com` / `demo12345`

---

## Actualizaciones posteriores

```bash
cd /opt/appmedica
bash scripts/deploy.sh
```

---

## Comandos útiles

```bash
# Logs
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod logs -f backend
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod logs -f frontend

# Reiniciar un servicio
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod restart backend

# Estado
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod ps
```

---

## Notas

- **No exponer** el puerto `5432` de PostgreSQL.
- El `docker-compose.yml` de desarrollo monta volúmenes y usa `uvicorn --reload`; **no usar en producción**.
- Si el VPS comparte IP con otros proyectos, AppMedica solo usa `127.0.0.1:3000` y `:8000`; el dominio `app.daminatoweb.com` es independiente.

---

## Pasos manuales que no automatiza el repo

1. Crear registro DNS `app` → IP del VPS
2. Crear repositorio Git remoto y subir el código (si aún no existe)
3. Completar `backend/.env.prod` con secretos reales
4. Ejecutar `setup-vps.sh` una sola vez
5. Ejecutar `certbot` la primera vez
6. Renovación SSL: Certbot instala un timer automático (`certbot renew`)
