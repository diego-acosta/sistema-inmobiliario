# Sistema Inmobiliario Backend

Backend base para un sistema inmobiliario construido con FastAPI, SQLAlchemy y PostgreSQL, organizado con una arquitectura limpia por capas.

## Requisitos

- Python 3.11 o superior
- PostgreSQL disponible

## Instalacion

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear el archivo `.env` a partir de `.env.example`:

```bash
cp .env.example .env
```

4. Ajustar `DATABASE_URL` con tus credenciales de PostgreSQL.

## Ejecucion

Desde la carpeta `backend/`, iniciar el servidor con:

```bash
uvicorn app.main:app --reload
```

La API quedara disponible en:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

## Bootstrap de base de datos

El proyecto mantiene un modelo basado en schema completo.

El bootstrap oficial de bases `dev` y `test` es:

```powershell
backend\scripts\reset_db.bat
```

Ese script:

1. recrea `inmobiliaria_dev`
2. recrea `inmobiliaria_test`
3. aplica el schema completo `backend/database/schema_inmobiliaria_20260418.sql`
4. aplica `seed_test_baseline.sql` en `dev` y `test` para asegurar el contexto tecnico minimo usado por headers y metadata operativa
5. aplica `seed_minimo.sql` solo en `dev`

El `seed_minimo.sql` de `dev` deja:

- un activo inmobiliario disponible para pruebas basicas
- una persona y un rol de participacion minimos para el flujo comercial
- una venta confirmada con `outbox_event` `venta_confirmada` pendiente
- una escrituracion registrada con `outbox_event` `escrituracion_registrada` pendiente

`pytest` no crea ni parchea tablas del schema. La sesion de test valida que `inmobiliaria_test` haya sido bootstrappeada previamente con el flujo oficial.

Antes de correr tests:

```powershell
backend\scripts\reset_db.bat
pytest
```

## Endpoint disponible

- `GET /health` devuelve:

```json
{"status": "ok"}
```

## Estructura base

- `app/main.py`: inicializacion de FastAPI
- `app/config/`: configuracion general y conexion a base de datos
- `app/api/`: routers y dependencias
- `app/application/common/`: clases base de aplicacion
- `app/domain/common/`: entidades y excepciones base de dominio
- `app/infrastructure/persistence/`: repositorio base para SQLAlchemy
