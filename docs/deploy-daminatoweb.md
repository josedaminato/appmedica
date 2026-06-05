# Deploy — daminatoweb.com

Configuración concreta para tu Hostinger KVM 1.

| Dato | Valor |
|------|--------|
| VPS ID | 1035833 |
| IP | `72.60.166.24` |
| Hostname | `srv1035833.hstgr.cloud` |
| Ubicación | Estados Unidos (Boston) |
| Dominio AppMedica | `app.daminatoweb.com` (recomendado) o `daminatoweb.com` |
| Dominio | `daminatoweb.com` |
| Renovación VPS | 29 jun 2026 |

**Nota:** El VPS (`72.60.166.24`) puede alojar **otros servicios no relacionados** con AppMedica ni con daminatoweb.com (proyectos distintos, otros puertos/datos). AppMedica es un producto aparte; solo comparte la máquina si vos elegís desplegarlo ahí.

## Acceso SSH — importante (leer antes de conectar)

Hostinger puede mostrar **dos accesos distintos** con la misma IP:

| Tipo | Usuario | Puerto | ¿Sirve para AppMedica? |
|------|---------|--------|-------------------------|
| **Hosting web** (hPanel → SSH) | `u906481625` | **65002** | **No** — sin Docker, entorno PHP/limitado |
| **VPS KVM** (hPanel → VPS → 1035833) | `root` (habitual) | **22** (habitual) | **Sí** — ahí va Docker |

El comando que te muestra hPanel en “Detalles de SSH” del **dominio/hosting**:

```bash
ssh -p 65002 u906481625@72.60.166.24
```

Ese acceso sirve para **subir archivos PHP** o administrar hosting compartido. **AppMedica no corre ahí** (necesita Docker + PostgreSQL + FastAPI).

Para desplegar AppMedica, conectate al **VPS KVM 1035833**:

1. **hPanel → VPS → Overview** (servidor 1035833)
2. Buscá **SSH access** / credenciales del VPS (suele ser `root` y puerto `22`)
3. Si agregaste la clave **“PC José”** (09/10/2025), podés usarla en el VPS para no depender de contraseña

```bash
# Ejemplo típico VPS (confirmar en hPanel → VPS, no en SSH del dominio)
ssh root@72.60.166.24

# Si el VPS usa otro puerto:
ssh -p PUERTO root@72.60.166.24
```

**Firewall:** abrí **80**, **443** y el puerto SSH que uses (**22** en VPS o **65002** solo si administrás hosting por ahí).

## DNS

Registro **A** para `@` → `72.60.166.24`  
Registro **A** o **CNAME** para `www` → `daminatoweb.com` o la misma IP  
**AppMedica (VPS compartido):** registro **A** `app` → `72.60.166.24`

Estado actual (resuelto): `daminatoweb.com` → `72.60.166.24` ✓

## VPS con otros servicios (no relacionados con AppMedica)

Si en el **mismo KVM** ya hay otros procesos (APIs, bases, sitios de **otros proyectos**), AppMedica va **aislado**:

| Regla | Por qué |
|-------|---------|
| **Subdominio** `app.daminatoweb.com` | Solo daminatoweb / AppMedica |
| **Puerto** `8082` | No usa el `:80` del host si ya está ocupado |
| **Docker propio** | Contenedores `appmedica-*`, volumen `appmedica_postgres_data` |
| **Sin mezclar datos** | La DB de AppMedica es solo para consultorios AppMedica |

**RAM AppMedica:** ~1,6 GB en KVM 1. Sumá lo que consuman tus otros servicios en el VPS y revisá con `docker stats` / `free -h`.

```bash
cd /opt/appmedica
cp deploy/env.daminatoweb.example .env
docker compose -f docker-compose.prod.yml -p appmedica up -d --build
curl http://127.0.0.1:8082/api/v1/health
```

nginx del host: ver [`deploy/nginx/host-vps-shared.conf`](../deploy/nginx/host-vps-shared.conf).

**RAM (4 GB):** AppMedica ~1,6 GB + tus otros proyectos. Si el VPS se queda sin memoria, usá `docker stats` y considerá KVM 2.

## 1. Conectar al VPS KVM (no al SSH del hosting)

```bash
# Hosting web (NO usar para AppMedica):
# ssh -p 65002 u906481625@72.60.166.24

# VPS KVM — usar credenciales de hPanel → VPS → 1035833:
ssh root@72.60.166.24
```

## 2. Instalar Docker (si falta)

```bash
curl -fsSL https://get.docker.com | sh
```

## 3. Subir proyecto

```bash
mkdir -p /opt/appmedica
cd /opt/appmedica
# git clone TU_REPO .   — o subir por SFTP desde hPanel
```

## 4. Configurar .env

```bash
cp deploy/env.daminatoweb.example .env
nano .env
```

Cambiar **obligatorio**:
- `JWT_SECRET` — generar: `openssl rand -hex 32`
- `POSTGRES_PASSWORD` — password fuerte
- Actualizar `DATABASE_URL` con el mismo password

Dejar:
- `PUBLIC_URL=https://daminatoweb.com`
- `CORS_ORIGINS=https://daminatoweb.com,https://www.daminatoweb.com`
- `SEED_DEMO=0`

## 5. Levantar (primero HTTP)

```bash
docker compose -f docker-compose.prod.yml up -d --build
curl http://127.0.0.1/api/v1/health
```

Probar en navegador: **http://daminatoweb.com**

## 6. SSL (HTTPS) — recomendado

Opción A — **Certbot en el VPS** (antes de levantar web en 443):

```bash
apt update && apt install -y certbot
docker compose -f docker-compose.prod.yml stop web

certbot certonly --standalone -d daminatoweb.com -d www.daminatoweb.com

mkdir -p deploy/certs
cp /etc/letsencrypt/live/daminatoweb.com/fullchain.pem deploy/certs/
cp /etc/letsencrypt/live/daminatoweb.com/privkey.pem deploy/certs/
```

Descomentar bloque `443` y redirect HTTP en `deploy/nginx/app.conf`, montar certs en `docker-compose.prod.yml`:

```yaml
web:
  volumes:
    - ./deploy/certs:/etc/nginx/certs:ro
```

```bash
docker compose -f docker-compose.prod.yml up -d --build web
```

Opción B — SSL desde **hPanel → Dominios → daminatoweb.com → SSL**

## 7. Firewall hPanel

Puertos abiertos: **80**, **443**, y SSH del **VPS** (normalmente **22**)  
Si solo administrás hosting por **65002**, ese puerto también — pero AppMedica va en el **VPS**, no en hosting compartido  
Cerrado: **5432** (PostgreSQL)

## URLs finales

| Qué | URL |
|-----|-----|
| App | https://daminatoweb.com |
| Registro | https://daminatoweb.com/register |
| API health | https://daminatoweb.com/api/v1/health |

## Actualizar después de cambios en código

```bash
cd /opt/appmedica
git pull   # o subir archivos
docker compose -f docker-compose.prod.yml up -d --build
```
