# Baseline estructural inmobiliaria - 2026-04-18

## Archivo principal
- esquema: [schema_inmobiliaria_20260418.sql](/C:/Users/Diego/Downloads/SISTEMA%20INMOBILIARIO%2020260418/SISTEMA%20INMOBILIARIO/backend/database/schema_inmobiliaria_20260418.sql)

## Origen
- base fuente: `inmobiliaria_dev`
- fecha de extraccion: `2026-04-18`
- criterio de seleccion: `inmobiliaria_dev` se uso como fuente porque su estructura esta alineada con `inmobiliaria_test`

## Alcance
- incluye solo esquema
- incluye tablas, funciones, secuencias, defaults, PK, FK, UNIQUE, CHECK e indices
- no incluye datos de prueba ni inserts de baseline

## Comando equivalente usado
```powershell
$env:PGPASSWORD='gc001'
& 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' `
  --schema-only `
  --no-owner `
  --no-privileges `
  --host localhost `
  --port 5432 `
  --username postgres `
  --dbname inmobiliaria_dev `
  --file 'backend/database/schema_inmobiliaria_20260418.sql'
```

## Nota
- este archivo representa el baseline estructural actual del sistema tomando la base real como fuente de verdad

## Patch #393 — estado de ítems de catálogo

`patch_item_catalogo_estado_20260724.sql` formaliza el ciclo de vida físico de `item_catalogo`: normaliza `NULL` a `ACTIVO`, mantiene sólo `ACTIVO` e `INACTIVO`, fija `DEFAULT 'ACTIVO'`, `NOT NULL` y `chk_item_catalogo_estado`. El patch es transaccional y se ejecuta después de `patch_catalogos_core_ef_20260716.sql` en ambos resets. La baja lógica continúa representándose por `deleted_at`; no cambia la constraint de código ni crea estructuras legacy.
