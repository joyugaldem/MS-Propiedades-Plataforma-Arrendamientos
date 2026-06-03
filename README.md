# MS-Propiedades — Plataforma Arrendamientos CR

Microservicio REST para la gestión de propiedades en arrendamiento de la Plataforma Arrendamientos Costa Rica. Expone un CRUD completo de propiedades con filtros, paginación y búsqueda de texto.

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [API Reference](#api-reference)
- [Modelo de datos](#modelo-de-datos)
- [Variables de entorno](#variables-de-entorno)
- [Desarrollo local](#desarrollo-local)
- [Migraciones de base de datos](#migraciones-de-base-de-datos)
- [Seed de datos de prueba](#seed-de-datos-de-prueba)
- [Tests](#tests)
- [CI/CD y deploy en Azure](#cicd-y-deploy-en-azure)
- [Infraestructura Azure](#infraestructura-azure)

---

## Arquitectura

Este microservicio forma parte de una arquitectura de microservicios con API Gateway centralizado:

```
Frontend (React/Vite)
        │
        ▼
Azure API Management (APIM)
  plataforma-arrendamientos-api.azure-api.net
        │
        ├──► MS-Propiedades  (este servicio)   ──► PostgreSQL propiedades_db
        ├──► MS-Usuarios                        ──► PostgreSQL usuarios_db
        ├──► MS-Contratos                       ──► PostgreSQL contratos_db
        └──► MS-Mensajes                        ──► PostgreSQL mensajes_db
```

**Principios aplicados:**
- **DB per microservice**: cada servicio tiene su propia base de datos PostgreSQL en Azure Flexible Server. No existen foreign keys entre servicios; las referencias a otras entidades (e.g. `idDueno`) se almacenan como strings (UUID loose reference).
- **Gateway centralizado**: el APIM maneja autenticación JWT, rate limiting y routing. El microservicio asume que el tráfico que llega ya fue autenticado.
- **Async first**: toda la capa de acceso a datos usa SQLAlchemy async + asyncpg.

---

## Stack tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Framework | FastAPI 0.115.6 |
| Servidor | Gunicorn + Uvicorn Workers |
| Base de datos | PostgreSQL 16 (Azure Flexible Server) |
| ORM | SQLAlchemy 2.0 (async) |
| Driver BD | asyncpg 0.30 |
| Migraciones | Alembic 1.14 |
| Validación | Pydantic 2.10 |
| Tests | pytest + pytest-asyncio + httpx |
| Deploy | Azure App Service (Linux, B1) |
| CI/CD | GitHub Actions |
| Gateway | Azure API Management |
| Hosting frontend | Azure Static Web Apps |

---

## Estructura del proyecto

```
MS-Propiedades-Plataforma-Arrendamientos/
├── app/
│   ├── main.py               # FastAPI app, lifespan, CORS, health check
│   ├── config.py             # Settings (pydantic-settings, .env)
│   ├── database.py           # Engine async, sesión, Base declarativa
│   ├── models/
│   │   └── propiedad.py      # Modelo SQLAlchemy Propiedad
│   ├── schemas/
│   │   └── propiedad.py      # Schemas Pydantic (Create, Update, Response)
│   └── routers/
│       └── propiedades.py    # Endpoints CRUD + filtros
├── migrations/
│   ├── env.py                # Config Alembic (asyncpg → psycopg2)
│   └── versions/
│       └── 8c075582a761_add_fecha_actualizacion_to_propiedades.py
├── tests/
│   └── test_propiedades.py   # 10 tests unitarios con mock de DB
├── scripts/
│   └── seed_db.py            # Inserta propiedades de prueba en la BD
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD: deploy + migración + smoke test
├── startup.sh                # Script de arranque para Azure App Service
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## API Reference

**Base URL producción:** `https://plataforma-arrendamientos-api.azure-api.net/propiedades`

**Base URL directa (App Service):** `https://ms-propiedades.azurewebsites.net/propiedades`

Todos los endpoints que pasan por el APIM requieren el header:
```
Ocp-Apim-Subscription-Key: <subscription-key>
```

---

### GET /propiedades

Lista propiedades con paginación y filtros opcionales.

**Query params:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `page` | int | 1 | Número de página (≥ 1) |
| `limit` | int | 6 | Registros por página (1–100) |
| `search` | string | — | Búsqueda en título, provincia, cantón y distrito |
| `provincia` | string | — | Filtro exacto por provincia |
| `tipo` | string | — | `casa`, `apartamento`, `local`, `bodega`, `oficina` |
| `estado` | string | — | `disponible`, `alquilada`, `mantenimiento` |
| `precioMin` | decimal | — | Precio mínimo (inclusive) |
| `precioMax` | decimal | — | Precio máximo (inclusive) |
| `duenoId` | string | — | UUID del propietario |

**Respuesta 200:**
```json
{
  "data": [
    {
      "idPropiedad": "uuid",
      "titulo": "Casa en Escazú",
      "descripcion": "...",
      "precio": "500000.00",
      "moneda": "CRC",
      "provincia": "San José",
      "canton": "Escazú",
      "distrito": "Escazú",
      "tipo": "casa",
      "estado": "disponible",
      "imagenes": ["https://..."],
      "idDueno": "uuid",
      "amenidades": ["parqueo", "piscina"],
      "fechaCreacion": "2026-01-15T10:00:00Z",
      "fechaActualizacion": null
    }
  ],
  "total": 87,
  "page": 1,
  "pageSize": 6,
  "totalPages": 15
}
```

**Errores:**
- `400` — `precioMin` > `precioMax`

---

### GET /propiedades/{id}

Obtiene una propiedad por su UUID.

**Respuesta 200:** objeto `PropiedadResponse` (ver estructura arriba)

**Errores:**
- `404` — propiedad no encontrada
- `422` — `id` no es un UUID válido

---

### POST /propiedades

Crea una nueva propiedad.

**Body (application/json):**
```json
{
  "titulo": "Apartamento moderno en San Pedro",
  "descripcion": "Hermoso apartamento con acabados de primera...",
  "precio": "350000.00",
  "moneda": "CRC",
  "provincia": "San José",
  "canton": "Montes de Oca",
  "distrito": "San Pedro",
  "tipo": "apartamento",
  "estado": "disponible",
  "imagenes": ["https://example.com/img1.jpg"],
  "idDueno": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "amenidades": ["parqueo", "internet fibra óptica"]
}
```

**Validaciones:**
- `titulo`: 3–200 caracteres
- `descripcion`: 10–2000 caracteres
- `precio`: > 0
- `moneda`: `CRC` o `USD`
- `tipo`: enum (`casa`, `apartamento`, `local`, `bodega`, `oficina`)
- `estado`: enum (`disponible`, `alquilada`, `mantenimiento`)
- `idDueno`: UUID válido

**Respuesta 201:** objeto `PropiedadResponse`

---

### PUT /propiedades/{id}

Actualiza parcialmente una propiedad. Solo se actualizan los campos enviados.

**Body:** cualquier subconjunto de los campos de `POST /propiedades` (todos opcionales)

**Respuesta 200:** objeto `PropiedadResponse` con `fechaActualizacion` actualizada

**Errores:**
- `404` — propiedad no encontrada

---

### DELETE /propiedades/{id}

Elimina una propiedad permanentemente.

**Respuesta 204:** sin cuerpo

**Errores:**
- `404` — propiedad no encontrada

---

### GET /health

Verifica el estado del servicio y la conectividad con la base de datos.

**Respuesta 200 (DB disponible):**
```json
{ "status": "ok", "db": "ok" }
```

**Respuesta 503 (DB no disponible):**
```json
{ "status": "degraded", "db": "unreachable" }
```

---

## Modelo de datos

**Tabla:** `propiedades`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_propiedad` | UUID (PK) | Identificador único |
| `titulo` | VARCHAR(200) | Título descriptivo |
| `descripcion` | TEXT | Descripción detallada |
| `precio` | NUMERIC(12,2) | Precio mensual |
| `moneda` | VARCHAR(3) | `CRC` o `USD` |
| `provincia` | VARCHAR(50) | Provincia de Costa Rica |
| `canton` | VARCHAR(100) | Cantón |
| `distrito` | VARCHAR(100) | Distrito |
| `tipo` | VARCHAR(20) | Tipo de propiedad |
| `estado` | VARCHAR(20) | Estado actual |
| `imagenes` | TEXT[] | URLs de imágenes |
| `id_dueno` | VARCHAR(100) | UUID del propietario (loose reference) |
| `amenidades` | TEXT[] | Lista de amenidades |
| `fecha_creacion` | TIMESTAMPTZ | Fecha de creación (auto) |
| `fecha_actualizacion` | TIMESTAMPTZ | Última modificación (auto) |

**Índices:**
- `ix_propiedades_id_dueno` — búsquedas por dueño
- `ix_propiedades_provincia_tipo` — filtros combinados
- `ix_propiedades_precio` — filtros de rango de precio
- `ix_propiedades_estado` — filtro por estado

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto (ver `.env.example`):

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/propiedades_db?ssl=require
ALLOWED_ORIGINS=http://localhost:5173,https://tu-frontend.azurestaticapps.net
```

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `DATABASE_URL` | Cadena de conexión PostgreSQL async | Sí |
| `ALLOWED_ORIGINS` | Orígenes CORS permitidos, separados por coma | No (default: `http://localhost:5173`) |

---

## Desarrollo local

### Prerrequisitos

- Python 3.12+
- PostgreSQL 14+ (local o Azure)

### Setup

```bash
# Clonar el repositorio
git clone https://github.com/joyugaldem/MS-Propiedades-Plataforma-Arrendamientos.git
cd MS-Propiedades-Plataforma-Arrendamientos

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
# Editar .env con los datos de tu BD local

# Arrancar el servidor
uvicorn app.main:app --reload --port 8000
```

El servidor queda disponible en `http://localhost:8000`.

Documentación interactiva (Swagger UI): `http://localhost:8000/docs`

Documentación alternativa (ReDoc): `http://localhost:8000/redoc`

Schema OpenAPI (JSON): `http://localhost:8000/openapi.json`

> **Tip:** El schema OpenAPI puede usarse para generar types TypeScript en el frontend:
> ```bash
> npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
> ```

---

## Migraciones de base de datos

El proyecto usa **Alembic** para versionar el esquema de la base de datos.

```bash
# Verificar estado actual de migraciones
alembic current

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Crear una nueva migración (después de cambiar models/propiedad.py)
alembic revision --autogenerate -m "descripcion del cambio"

# Revertir la última migración
alembic downgrade -1
```

> **Nota:** Alembic usa psycopg2 (conexión síncrona) para las migraciones. El `migrations/env.py` convierte automáticamente la URL de asyncpg a psycopg2.

---

## Seed de datos de prueba

El script `scripts/seed_db.py` inserta propiedades con datos realistas de Costa Rica (7 provincias, 34 ubicaciones, precios en CRC y USD).

```bash
# Insertar 100 propiedades (default)
python scripts/seed_db.py

# Insertar N propiedades
python scripts/seed_db.py --n 50

# Limpiar tabla e insertar desde cero
python scripts/seed_db.py --clean --n 100
```

El script requiere la variable `DATABASE_URL` en el entorno (`.env` o variable de shell).

---

## Tests

Los tests unitarios usan mocks de la sesión de base de datos — no requieren PostgreSQL.

```bash
# Correr todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --tb=short
```

**Casos cubiertos:**

| Test | Descripción |
|------|-------------|
| `test_health_ok` | GET /health retorna 200 con DB disponible |
| `test_retorna_estructura_correcta` | GET /propiedades retorna `{data, total, page, pageSize, totalPages}` |
| `test_precio_min_mayor_que_max_retorna_400` | Validación cruzada de precios |
| `test_filtro_estado_acepta_disponible` | Filtro `?estado=disponible` retorna 200 |
| `test_paginacion` | Parámetros `page` y `limit` funcionan |
| `test_retorna_404_si_no_existe` | GET /propiedades/{id} inexistente → 404 |
| `test_retorna_propiedad_existente` | GET /propiedades/{id} existente → 200 |
| `test_uuid_invalido_retorna_422` | GET /propiedades/no-es-uuid → 422 |
| `test_body_invalido_retorna_422` | POST con body incompleto → 422 |
| `test_id_dueno_invalido_retorna_422` | POST con idDueno no UUID → 422 |

---

## CI/CD y deploy en Azure

El pipeline en `.github/workflows/deploy.yml` se dispara en cada push a `main`:

```
Push a main
    │
    ├── 1. Setup Python 3.12 (con cache de pip)
    ├── 2. pip install -r requirements.txt
    ├── 3. Azure Login (Service Principal)
    ├── 4. Deploy a Azure App Service (ms-propiedades)
    ├── 5. alembic upgrade head  ← aplica migraciones pendientes
    └── 6. Smoke test: curl GET /health
```

### Secrets requeridos en GitHub Actions

| Secret | Descripción |
|--------|-------------|
| `AZURE_CREDENTIALS` | JSON del Service Principal para azure/login |
| `DATABASE_URL` | Cadena de conexión PostgreSQL (para migraciones) |

### Configurar `AZURE_CREDENTIALS`

```bash
az ad sp create-for-rbac \
  --name sp-ms-propiedades \
  --role contributor \
  --scopes /subscriptions/<SUB_ID>/resourceGroups/JosephResourceGroup \
  --sdk-auth
```

El JSON resultante se pega como valor del secret `AZURE_CREDENTIALS`.

---

## Infraestructura Azure

| Recurso | Nombre | Tipo |
|---------|--------|------|
| App Service | `ms-propiedades` | Linux B1 |
| App Service Plan | `ASP-JosephResourceGroup-9d82` | B1 |
| PostgreSQL | `ms-propiedades-53383.postgres.database.azure.com` | Flexible Server |
| Base de datos | `propiedades_db` | PostgreSQL 16 |
| API Gateway | `plataforma-arrendamientos-api` | Azure API Management |
| Frontend | `PlataformaAriendamientosCR` | Azure Static Web Apps |
| Resource Group | `JosephResourceGroup` | — |

### URLs

| Entorno | URL |
|---------|-----|
| API via APIM (producción) | `https://plataforma-arrendamientos-api.azure-api.net/propiedades` |
| App Service (directo) | `https://ms-propiedades.azurewebsites.net/propiedades` |
| Health check | `https://ms-propiedades.azurewebsites.net/health` |
| Swagger UI | `https://ms-propiedades.azurewebsites.net/docs` |
| Frontend | `https://agreeable-ground-0b1436910.6.azurestaticapps.net` |
