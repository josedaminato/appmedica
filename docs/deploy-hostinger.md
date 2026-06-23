# Despliegue en Hostinger

AppMedica está pensado para correr en **Hostinger VPS** (no en hosting compartido PHP).

## Tu plan: KVM 1

| Recurso | Valor | Implicación para AppMedica |
|---------|-------|----------------------------|
| vCPU | 1 | `UVICORN_WORKERS=1` (no usar 2+) |
| RAM | 4 GB | Suficiente para Postgres + API + nginx (~1,6 GB reservados) |
| Disco | 50 GB NVMe | Más que suficiente para años de consultorios |
| Ancho de banda | 4 TB/mes | Holgado para uso administrativo |
| Renovación | 29 jun 2026 | Recordá renovar antes de esa fecha |

La config de producción (`docker-compose.prod.yml`) ya incluye límites de memoria pensados para **KVM 1**.

| Plan Hostinger | ¿Sirve? |
|----------------|---------|
| **VPS KVM 1** (el tuyo) | Sí |
| **KVM 2+** | Sí, podés subir `UVICORN_WORKERS=2` |
| **Web hosting compartido** | No |

## Arquitectura en producción

```
Internet → nginx (puerto 80/443)
              ├── /          → React estático (build)
              └── /api/v1/*  → FastAPI (backend:8000, red interna)
                                    └── PostgreSQL (solo red interna)
```

- El frontend usa `VITE_API_URL=/api/v1` (misma URL, sin CORS cross-origin).
- PostgreSQL **no** se expone a internet.
- Swagger deshabilitado cuando `APP_ENV=production`.

## Requisitos VPS

- **OS:** Ubuntu 24.04 LTS (plantilla recomendada en hPanel al crear/reinstalar el VPS)
- Docker + Docker Compose
- Dominio apuntando a la IP del VPS (opcional al inicio)
- **KVM 1:** 4 GB RAM — no instales otros servicios pesados en el mismo VPS

## Pasos en hPanel (VPS ID 1035833)

1. **hPanel → VPS → Overview** — anotá la **IP pública** y credenciales SSH
2. **Firewall** — abrí puertos **22**, **80** y **443** (cuando uses SSL)
3. **Backups** — activá backups semanales (incluidos en KVM 1)
4. **OS** — si reinstalás, elegí **Ubuntu 24.04** con Docker (o instalalo después)

## Pasos rápidos

### 1. Conectar al VPS

Desde hPanel → VPS → SSH, o:

```bash
ssh root@TU-IP-VPS
```

### 2. Instalar Docker (si no está)

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
```

### 3. Subir el proyecto

Opciones:

- `git clone` del repo en el VPS
- SFTP / File Manager de Hostinger
- `scp -r appmedica root@TU-IP:/opt/appmedica`

### 4. Configurar entorno

```bash
cd /opt/appmedica
cp .env.production.example .env
nano .env
```

**Cambiar obligatoriamente:**

| Variable | Ejemplo |
|----------|---------|
| `JWT_SECRET` | string aleatorio largo (32+ chars) |
| `POSTGRES_PASSWORD` | password fuerte |
| `PUBLIC_APP_URL` | `https://app.tudominio.com` |
| `CORS_ORIGINS` | `https://app.tudominio.com` |
| `SEED_DEMO` | `0` en producción real |

### 5. Levantar

```bash
chmod +x deploy/hostinger-vps.sh
./deploy/hostinger-vps.sh
```

O manualmente:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 6. Verificar

```bash
curl http://127.0.0.1/api/v1/health
# {"status":"ok"}
```

Abrí `http://TU-IP` o tu dominio.

## SSL (HTTPS)

Hostinger suele ofrecer SSL gratis en el panel del dominio. Opciones:

1. **Certificado en Hostinger** → descargar e instalar en `deploy/certs/` y descomentar el bloque `443` en `deploy/nginx/app.conf`.
2. **Certbot en el VPS** (Let's Encrypt):

```bash
apt install certbot
certbot certonly --standalone -d app.tudominio.com
# Copiar certs a deploy/certs/ y reiniciar web
docker compose -f docker-compose.prod.yml restart web
```

Actualizá `.env`:

```
PUBLIC_APP_URL=https://app.tudominio.com
CORS_ORIGINS=https://app.tudominio.com
```

## Firewall Hostinger

En hPanel → VPS → Firewall, abrí:

- **80** (HTTP)
- **443** (HTTPS, cuando uses SSL)
- **22** (SSH, restringí a tu IP si podés)

**No abras** el puerto 5432 (PostgreSQL).

## Actualizar la app

```bash
cd /opt/appmedica
git pull   # o subir archivos nuevos
docker compose -f docker-compose.prod.yml up -d --build
```

Las migraciones Alembic corren solas al iniciar el backend.

## Backups

PostgreSQL persiste en el volumen Docker `postgres_data`. Backup manual:

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U appmedica appmedica > backup-$(date +%F).sql
```

Programá backups desde hPanel o cron en el VPS.

## Desarrollo local vs producción

| | Local (`docker-compose.yml`) | Hostinger (`docker-compose.prod.yml`) |
|--|------------------------------|----------------------------------------|
| Frontend | Vite dev :5173 | nginx + build estático |
| Backend | uvicorn, volumen montado | uvicorn 2 workers, sin volumen |
| DB | puerto 5432 expuesto | solo red interna |
| Demo seed | automático | solo si `SEED_DEMO=1` |
| Swagger | `/docs` | oculto en production |

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Página en blanco | Revisá `docker compose -f docker-compose.prod.yml logs web` |
| API 502 | Backend no levantó: `logs backend`, verificar `.env` y DB |
| CORS error | `CORS_ORIGINS` debe coincidir exactamente con la URL del navegador |
| Login falla | Verificar que `JWT_SECRET` no cambió entre deploys |
| Poca RAM | Subir plan VPS o bajar `UVICORN_WORKERS` a 1 |

## Base de datos externa (opcional)

Si preferís PostgreSQL administrado (Neon, Supabase, Hostinger DB si lo ofrecen):

1. Cambiá `DATABASE_URL` en `.env` apuntando al host externo.
2. Comentá o eliminá el servicio `db` en `docker-compose.prod.yml`.
3. Corré migraciones: `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`
