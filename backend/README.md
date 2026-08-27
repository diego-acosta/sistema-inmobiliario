# Backend — Sistema Inmobiliario

Backend HTTP del Sistema Inmobiliario, construido con **FastAPI**, **SQLAlchemy** y **PostgreSQL**.

La implementación está organizada por dominios y casos de uso. La arquitectura y el ownership semántico no se definen en este README: deben verificarse contra `AGENTS.md`, `backend/documentacion/DEV-ARCH/`, SQL, implementación y tests reales.

## Stack

- Python 3.11+.
- FastAPI.
- Uvicorn.
- SQLAlchemy 2.x.
- PostgreSQL mediante `psycopg`.
- `pytest` + `httpx` para tests.
- Argon2 para credenciales administrativas.
- RFC 8785 para canonicalización usada por infraestructura de idempotencia.

## Estructura principal

```text
backend/
├── app/
│   ├── api/                    # Routers, dependencias y schemas HTTP
│   ├── application/            # Servicios/casos de uso de aplicación
│   ├── config/                 # Settings y conexión
│   ├── domain/                 # Conceptos y reglas de dominio
│   ├── infrastructure/         # Persistencia e infraestructura transversal
│   └── main.py                 # Aplicación FastAPI
├── database/                   # Schema, patches, seeds y SQL de soporte
├── documentacion/              # DEV-ARCH, DEV-SRV, DEV-API y documentos técnicos
├── scripts/                    # Bootstrap/reset de PostgreSQL
├── tests/                      # Tests backend
└── requirements.txt
```

## Dominios expuestos actualmente

`app/main.py` registra routers para:

- Personas.
- Inmobiliario: desarrollos, inmuebles, unidades funcionales, edificaciones y servicios.
- Comercial.
- Locativo.
- Financiero.
- Administrativo.
- Operativo.
- Salud técnica (`/health`).

La existencia de un router no implica que todo el dominio esté completo. El estado verificable se mantiene en `../PROJECT-STATUS.md` y debe contrastarse con código y tests.

## Instalación

Desde `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crear `.env` a partir de `.env.example` y ajustar la conexión PostgreSQL cuando corresponda.

## Bootstrap de PostgreSQL

El flujo oficial recrea las bases de desarrollo y test y aplica el schema/patches/seeds vigentes.

### Windows

Desde `backend/`:

```powershell
.\scripts\reset_db.bat
```

### Linux / Codex Cloud

```bash
./scripts/reset_db.sh
```

`pytest` no debe considerarse validado contra PostgreSQL si el reset correspondiente no terminó correctamente.

## Ejecución

Desde `backend/`:

```powershell
uvicorn app.main:app --reload
```

Por defecto:

- API: `http://127.0.0.1:8000`
- Swagger / OpenAPI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Endpoint técnico básico:

```http
GET /health
```

Respuesta esperada:

```json
{"status":"ok"}
```

## API y contratos

La API se expone principalmente bajo `/api/v1` y opera sobre casos de uso, no sobre tablas crudas.

Los contratos formales viven en `documentacion/DEV-API/` y el diseño de servicios en `documentacion/DEV-SRV/`. Antes de modificar un endpoint debe verificarse también la implementación real del router, schema, service, repository y tests.

Los writes sincronizables siguen la política CORE-EF vigente en `../AGENTS.md`, incluyendo, según aplique:

- `X-Op-Id`.
- `X-Sucursal-Id`.
- `X-Instalacion-Id`.
- `If-Match-Version` para mutaciones de entidades existentes/versionadas.
- identidad humana derivada de Bearer/`AuthenticatedPrincipal` en commands nuevos o migrados que usan autenticación.
- idempotencia, outbox, locks, versionado y frontera transaccional explícitos.

No debe asumirse que todos los endpoints heredados ya están migrados al mismo nivel de contrato.

## Tests

Con PostgreSQL preparado mediante el reset oficial:

```powershell
pytest
```

También pueden ejecutarse suites focales por archivo o dominio, por ejemplo:

```powershell
pytest tests/test_personas_api.py
```

No se documenta un número fijo de tests porque la suite cambia con frecuencia. Para el baseline verificable vigente consultar `../PROJECT-STATUS.md` y los PR correspondientes.

## Fuentes de verdad

Orden operativo recomendado para cambios:

1. `../AGENTS.md`.
2. `documentacion/DEV-ARCH/`.
3. SQL real en `database/`.
4. Implementación real en `app/`.
5. Tests reales en `tests/`.
6. Issues y PR vigentes.
7. `../PROJECT-STATUS.md`.
8. `../CODEX-WORKFLOW.md`.

Este README es una guía de entrada y operación; no reemplaza esas fuentes.
