# SRV-OPE-008 — Caja operativa base

## Clasificación

- Dominio: operativo.
- Concepto: núcleo del dominio operativo acotado a estructura de caja.
- CORE-EF POST: `COMMAND_WRITE_NEGOCIO` sincronizable.
- GET listado y ficha: `QUERY_READLIKE`.

## Modelo SQL auditado y decisión

Se auditó el dump vigente buscando `caja`, `caja_operativa`, `cuenta_financiera`, `movimiento_tesoreria`, `jornada_operativa`, `sucursal`, `instalacion`, `configuracion_local` y referencias de efectivo/tesorería.

Decisión: no existía una tabla formal `caja`/`caja_operativa` suficiente para el alta estructural operativa. `cuenta_financiera` y `movimiento_tesoreria` son modelos de tesorería/finanzas y no se reutilizan para no mezclar caja operativa con pagos, saldos ni movimientos financieros. Se agrega `caja_operativa` mediante `backend/database/patch_caja_operativa_base_20260704.sql`.

## Operaciones

- Crear caja operativa base.
- Listar cajas operativas no eliminadas.
- Consultar ficha de caja operativa no eliminada.

## Decisión CORE-EF

- Headers POST: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` mediante helper común.
- Idempotencia: aplica por `op_id_alta`; mismo op/payload retorna la caja existente, mismo op/payload distinto devuelve `IDEMPOTENT_DUPLICATE`.
- Outbox: aplica evento `caja_operativa_creada` (`EVT-OPE-014`) en la misma transacción que el alta real; replay compatible no duplica outbox.
- Lock lógico: NO APLICA en #253 porque no se abre/cierra ni mueve caja.
- Versionado: `version_registro = 1` al alta; modificaciones futuras deberán exigir `If-Match-Version`.
- Transacción: validación contextual, alta e outbox comparten frontera transaccional.

## Fuera de alcance

Apertura, cierre, movimientos, arqueo, control, saldos, pagos, imputaciones, jornada, reportes, autorización real, usuario_instalacion y UI.
