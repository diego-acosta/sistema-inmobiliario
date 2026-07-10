# SRV-OPE-010 — Movimientos manuales de caja operativa

## Objetivo
Registrar y consultar movimientos manuales básicos de una caja operativa abierta, dentro del dominio operativo.

## Clasificación
- Concepto: núcleo del dominio operativo.
- POST: `COMMAND_WRITE_NEGOCIO` sincronizable.
- GETs: `QUERY_READLIKE` sin headers CORE-EF write.

## Endpoints
- `POST /api/v1/operativo/cajas/aperturas/{id_apertura_caja}/movimientos`
- `GET /api/v1/operativo/cajas/aperturas/{id_apertura_caja}/movimientos`
- `GET /api/v1/operativo/cajas/movimientos`
- `GET /api/v1/operativo/cajas/movimientos/{id_movimiento_caja}`

## Regla de apertura vigente obligatoria
No se registra movimiento si la apertura no está vigente. Una apertura vigente cumple: `estado_apertura = 'ABIERTA'`, `fecha_hora_cierre IS NULL` y `deleted_at IS NULL`.

## Reglas de negocio
- La caja asociada debe estar `ACTIVA` y no dada de baja.
- El movimiento queda asociado a apertura, caja, sucursal e instalación de la apertura.
- La moneda debe coincidir con la moneda de la apertura.
- `monto > 0`.
- `INGRESO` requiere `ENTRADA`; `EGRESO` requiere `SALIDA`; `AJUSTE` admite ambos sentidos.
- `fecha_hora_movimiento >= fecha_hora_apertura`.

## CORE-EF
- Headers obligatorios en POST: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` mediante helper común.
- `version_registro = 1` al alta.
- Se persisten `id_usuario_movimiento`, instalación origen/modificación y op ids.
- `If-Match-Version`: NO APLICA porque no hay update en #255.
- Lock lógico: NO APLICA; se valida apertura vigente y caja activa.
- Rollback/transacción: movimiento y outbox se registran en la misma transacción.

## Idempotencia
Aplica por `op_id_alta`: mismo `X-Op-Id` con mismo payload retorna el movimiento existente y no duplica outbox; mismo `X-Op-Id` con payload distinto devuelve `409 IDEMPOTENT_DUPLICATE`.

## Outbox
Alta real emite `EVT-OPE-017` (`caja_operativa_movimiento_registrado`) para `caja_operativa_movimiento`. Replay compatible no emite evento adicional.

## Catálogos
- `tipo_movimiento`: `INGRESO`, `EGRESO`, `AJUSTE`.
- `sentido`: `ENTRADA`, `SALIDA`.
- `estado_movimiento`: `REGISTRADO`, `ANULADO`.
- `moneda`: `ARS`, `USD`.
- `concepto_movimiento`: catálogo mínimo textual (`INGRESO_MANUAL`, `EGRESO_MANUAL`, `REPOSICION`, `RETIRO`, `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`).

## Fuera de alcance
Integración automática con pagos, imputaciones financieras, cobros, cuotas, motor financiero, arqueo avanzado, diferencias de caja, reportes analíticos, jornada operativa completa, anulación/update y UI frontend.
