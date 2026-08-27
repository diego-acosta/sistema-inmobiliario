# Sistema Inmobiliario

Sistema integral de gestión inmobiliaria en desarrollo, orientado a administrar activos, personas, compraventa, alquileres, finanzas, operación, administración y sincronización entre instalaciones.

El repositorio reúne actualmente un backend HTTP en FastAPI/PostgreSQL y una aplicación desktop en Flet.

## Estructura del repositorio

```text
.
├── backend/                  # API, dominio, persistencia, SQL, tests y documentación técnica
├── frontend/
│   └── flet_app/            # Aplicación desktop Flet
├── AGENTS.md                 # Reglas obligatorias de arquitectura y trabajo
├── CODEX-WORKFLOW.md         # Flujo de desarrollo y revisión
└── PROJECT-STATUS.md         # Estado operativo verificable del proyecto
```

## Componentes

### Backend

- Python + FastAPI.
- SQLAlchemy sobre PostgreSQL.
- API organizada por dominios y casos de uso.
- Infraestructura transversal CORE-EF para identidad global, versionado, concurrencia, idempotencia, outbox/inbox, locks y sincronización donde corresponde.
- Tests con `pytest` y bootstrap explícito de PostgreSQL.

Ver [backend/README.md](backend/README.md).

### Frontend

- Aplicación de escritorio en Flet.
- Cliente HTTP contra el backend local.
- Navegación y pantallas para frentes ya materializados, con otras áreas todavía en desarrollo.

Ver [frontend/README.md](frontend/README.md) y [frontend/flet_app/README.md](frontend/flet_app/README.md).

## Dominios del sistema

La arquitectura formal contempla, entre otros, los siguientes frentes:

- Personas y partes intervinientes.
- Inmobiliario.
- Comercial / compraventa.
- Locativo.
- Financiero.
- Documental.
- Operativo.
- Administrativo.
- Técnico / sincronización.
- Analítico y reportes.

El grado de implementación no es uniforme entre dominios. Para conocer el estado verificable y el próximo foco de cada frente, consultar [PROJECT-STATUS.md](PROJECT-STATUS.md).

## Puesta en marcha rápida

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\reset_db.bat
uvicorn app.main:app --reload
```

Backend por defecto:

- API: `http://127.0.0.1:8000`
- OpenAPI / Swagger: `http://127.0.0.1:8000/docs`

### 2. Frontend

En otra terminal:

```powershell
cd frontend\flet_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

La aplicación usa `http://localhost:8000` como backend por defecto. Puede cambiarse con la variable de entorno `API_BASE_URL`.

## Tests

El backend no crea el schema de test automáticamente desde `pytest`. Antes de una ejecución que dependa de PostgreSQL debe realizarse el reset oficial:

```powershell
cd backend
.\scripts\reset_db.bat
pytest
```

En Linux/Codex Cloud el reset equivalente es:

```bash
cd backend
./scripts/reset_db.sh
pytest
```

El frontend mantiene tests propios bajo `frontend/flet_app/tests/`.

## Documentación y fuentes de verdad

Antes de modificar el sistema deben respetarse, en este orden operativo:

1. [AGENTS.md](AGENTS.md).
2. Arquitectura formal en `backend/documentacion/DEV-ARCH/`.
3. SQL real en `backend/database/`.
4. Implementación real en `backend/app/`.
5. Tests reales en `backend/tests/`.
6. Issues y PR vigentes.
7. [PROJECT-STATUS.md](PROJECT-STATUS.md).
8. [CODEX-WORKFLOW.md](CODEX-WORKFLOW.md).

Los README son documentación de entrada y operación; no reemplazan esas fuentes de verdad.

## Estado del proyecto

El proyecto está en desarrollo activo. No debe inferirse que un módulo está completo solo por aparecer en la arquitectura o en la navegación del frontend. Toda capacidad debe verificarse contra implementación, SQL y tests reales.

## Desarrollo

Para cambios en el repositorio:

- leer `AGENTS.md` y `CODEX-WORKFLOW.md`;
- trabajar mediante issue y rama específica;
- mantener los dominios y ownership definidos por la arquitectura;
- no declarar tests ejecutados sin evidencia real;
- abrir PR incremental con la decisión de impacto sobre `PROJECT-STATUS.md` y CORE-EF cuando corresponda.
