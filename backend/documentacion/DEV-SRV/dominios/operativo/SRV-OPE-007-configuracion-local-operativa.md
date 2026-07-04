# SRV-OPE-007 — Configuración local operativa

## Propósito

Gestionar una configuración local mínima por `sucursal`/`instalacion` para que la aplicación opere con contexto local consistente.

## Clasificación

- Dominio: `operativo`.
- Concepto: núcleo operativo acotado.
- No es autorización, sesión, login, caja, jornada, pagos ni permisos.

## Modelo usado

Se usa `configuracion_local`, creada por `backend/database/patch_configuracion_local_operativa_20260703.sql`, porque `valor_parametro` existe pero no cubre metadata CORE-EF completa ni unicidad/idempotencia sincronizable para este write.

## Casos de uso

- Consultar configuración local activa por `id_sucursal` e `id_instalacion`.
- Crear configuración local con idempotencia por `op_id_alta`.
- Modificar configuración local con `If-Match-Version` y aumento de `version_registro`.

## CORE-EF

- GET: `QUERY_READLIKE`, sin headers write.
- POST/PUT: `COMMAND_WRITE_TECNICO` sincronizable con headers CORE-EF obligatorios.
- POST: idempotencia por `op_id_alta`.
- PUT: concurrencia por `If-Match-Version`.
- Outbox: `configuracion_local_creada` (`EVT-OPE-012`) y `configuracion_local_modificada` (`EVT-OPE-013`) en la misma transacción que el write.
- Lock lógico: NO APLICA en esta primera versión.

## Fuera de alcance

No implementa permisos complejos, autorización real, contexto de sesión, caja, jornada, movimientos, pagos ni sincronización avanzada.
