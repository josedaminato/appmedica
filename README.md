# AppMedica

SaaS administrativo para profesionales de la salud en Argentina. Gestión simple de pacientes, agenda, obras sociales y cobros.

**Fase 1 incluye:** autenticación JWT, layout SaaS, dashboard inicial y módulo de pacientes completo.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recomendado para desarrollo local)
- O bien: Node.js 20+, Python 3.12+, PostgreSQL 16

## Producción (Hostinger VPS)

Para desplegar en **Hostinger VPS** (no hosting compartido):

```bash
cp .env.production.example .env
# Editar JWT_SECRET, passwords y dominio
docker compose -f docker-compose.prod.yml up -d --build
```

Guía completa: [docs/deploy-hostinger.md](docs/deploy-hostinger.md)


## Inicio rápido (Windows)

**Importante:** Docker Desktop debe estar **abierto y en ejecución** antes de levantar el proyecto.

```powershell
cd appmedica
.\start.ps1
```

Eso inicia la base de datos, el backend y el frontend. Luego abrí http://localhost:5173

**Cuenta demo** (creada automáticamente al iniciar el backend):

| Campo    | Valor                    |
|----------|--------------------------|
| Email    | `demo@consultorio.com`   |
| Password | `demo12345`              |

**Todo en Docker** (incluye frontend en contenedor):

```powershell
.\start.ps1 -DockerAll
```

**Verificar estabilidad** (tests + migraciones + seed):

```powershell
.\scripts\verify-stack.ps1
```

### Si localhost no abre

1. Verificá que Docker Desktop esté corriendo (ícono de ballena en la bandeja).
2. Ejecutá `.\start.ps1` o los pasos manuales de abajo.
3. Esperá ~30 segundos la primera vez (descarga imágenes).
4. Probá http://127.0.0.1:5173 si `localhost` falla.

### Estabilidad (Fase 2)

| Problema | Causa habitual | Solución |
|----------|----------------|----------|
| API timeout / conexión cerrada | `uvicorn --reload` + proyecto en **OneDrive** | Dejá `UVICORN_RELOAD=0` en `.env` (default). Reiniciá Docker Desktop si el contenedor backend no para. |
| `test_core_flow.py` falla login | Usuario demo inexistente | `docker compose exec backend python scripts/seed_demo.py` |
| Frontend no abre | `start.ps1` levanta frontend con **npm local**, no Docker | Corré `npm run dev` en `frontend/` o usá `.\start.ps1 -DockerAll` |
| Contenedor backend trabado | Bug conocido Docker Desktop en Windows | Reiniciá Docker Desktop → `docker compose down` → `docker compose up -d --build` |

Variables clave en `.env`:

- `VITE_API_URL=http://localhost:8000/api/v1` — frontend → backend
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` — CORS
- `UVICORN_RELOAD=0` — backend estable (recomendado)

## Inicio rápido con Docker (manual)

### 1. Configurar variables de entorno

```bash
cp .env.example .env
```

Editá `.env` si necesitás cambiar credenciales o `JWT_SECRET`.

### 2. Levantar todos los servicios

```bash
docker compose up --build
```

Esto inicia:

| Servicio   | URL                          |
|------------|------------------------------|
| Frontend   | http://localhost:5173        |
| Backend API| http://localhost:8000        |
| Swagger    | http://localhost:8000/docs   |
| PostgreSQL | localhost:5432               |

Las migraciones de Alembic y el seed demo se ejecutan automáticamente al iniciar el backend.

Validar el flujo core:

```bash
docker compose exec backend python scripts/test_core_flow.py
# Esperado: 15/15 pasaron
```

### 3. Crear tu cuenta (o usar demo)

1. Abrí http://localhost:5173/register
2. Completá nombre del consultorio, tu nombre, email y contraseña (mín. 8 caracteres)
3. Serás redirigido al dashboard

## Desarrollo local (sin Docker)

### Base de datos

```bash
# Con Docker solo para PostgreSQL
docker compose up db -d
```

O usá una instancia local y actualizá `DATABASE_URL` en `.env`:

```
DATABASE_URL=postgresql+psycopg://appmedica:appmedica_secret@localhost:5432/appmedica
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate

pip install -r requirements.txt

# Desde la carpeta backend, con .env en la raíz del monorepo
set DATABASE_URL=postgresql+psycopg://appmedica:appmedica_secret@localhost:5432/appmedica
alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend: http://localhost:5173

## Migraciones (Alembic)

```bash
cd backend

# Aplicar migraciones
alembic upgrade head

# Crear nueva migración (después de cambiar models)
alembic revision --autogenerate -m "descripcion"

# Revertir última migración
alembic downgrade -1
```

Con Docker, las migraciones corren al iniciar `backend`. Para ejecutarlas manualmente:

```bash
docker compose exec backend alembic upgrade head
```

## Probar autenticación

### Desde la UI

- **Registro:** http://localhost:5173/register
- **Login:** http://localhost:5173/login
- **Recuperar contraseña:** http://localhost:5173/forgot-password  
  El token se imprime en los logs del backend (`[MOCK EMAIL]`).

### Desde Swagger

Abrí http://localhost:8000/docs

**Registro**

```http
POST /api/v1/auth/register
{
  "organization_name": "Consultorio Demo",
  "full_name": "Dr. Juan Pérez",
  "email": "demo@appmedica.test",
  "password": "password123"
}
```

Copiá el `access_token` de la respuesta.

**Autorizar en Swagger:** botón **Authorize** → `Bearer <token>`

**Usuario actual**

```http
GET /api/v1/auth/me
```

**Login**

```http
POST /api/v1/auth/login
{
  "email": "demo@appmedica.test",
  "password": "password123"
}
```

**Recuperar contraseña (mock)**

```http
POST /api/v1/auth/forgot-password
{ "email": "demo@appmedica.test" }
```

Revisá los logs: `docker compose logs backend | findstr MOCK`

**Restablecer contraseña**

```http
POST /api/v1/auth/reset-password
{
  "token": "<token del log>",
  "new_password": "nuevaPassword123"
}
```

## Endpoints principales — Pacientes

Todos requieren header `Authorization: Bearer <token>`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/patients?page=1&page_size=20&q=garcia&is_active=true` | Listar con búsqueda y filtro |
| POST | `/api/v1/patients` | Crear paciente |
| GET | `/api/v1/patients/{id}` | Detalle |
| PATCH | `/api/v1/patients/{id}` | Editar |
| DELETE | `/api/v1/patients/{id}` | Baja lógica |

### Importar pacientes desde Excel

En la UI: **Pacientes → Importar Excel**.

1. Descargá la plantilla o usá tu `.xlsx` / `.csv` (primera fila = encabezados).
2. El archivo se **lee en tu navegador** (no hace falta subir el Excel completo).
3. Confirmá cuántos pacientes se importan.

**Si no podés abrir el archivo:** cerrá Excel, guardá como `.xlsx` y evitá archivos bloqueados por OneDrive.

API:

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/imports/patients/analyze` | Valida filas ya leídas en el cliente (JSON) |
| POST | `/api/v1/imports/patients/preview` | Alternativa: sube `.xlsx` (`multipart`) |
| POST | `/api/v1/imports/patients/commit` | Importa filas validadas (omite duplicados por DNI) |

### Obras sociales — reclamos y ranking

En la UI: **Obras sociales → Reclamos** (marcar facturado/cobrado) y **Ranking** (demora atención → cobro).

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/insurance-claims` | Listar reclamos (`open_only`, filtros por OS/estado) |
| PATCH | `/api/v1/insurance-claims/{id}` | Actualizar estado y fechas de facturación/cobro |
| GET | `/api/v1/health-insurances/ranking` | Ranking de obras sociales por demora y score |

**Ejemplo crear paciente**

```json
{
  "first_name": "María",
  "last_name": "García",
  "dni": "30123456",
  "phone": "+54 11 5555-1234",
  "email": "maria@email.com",
  "birth_date": "1990-05-15",
  "affiliate_number": null,
  "notes": "Paciente nueva",
  "is_active": true
}
```

## Estructura del proyecto

```
appmedica/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── frontend/         # React + Vite + shadcn/ui
├── docs/             # Documentación de arquitectura
├── docker-compose.yml
└── .env.example
```

## Próximas fases

- **Fase 2:** Agenda y turnos
- **Fase 3:** Obras sociales
- **Fase 4:** Cobros y deuda
- **Fase 5:** Reportes con datos reales
- **Fase 6:** Recordatorios (WhatsApp / email)

## Licencia

Proyecto privado — AppMedica.
