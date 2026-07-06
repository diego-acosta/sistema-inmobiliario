# SRV-OPE-009 — Apertura y cierre de caja operativa

## Objetivo
Implementar el ciclo operativo básico de apertura vigente y cierre simple de una `caja_operativa`.

## Clasificación
- Concepto: núcleo del dominio `operativo`.
- Writes: `COMMAND_WRITE_NEGOCIO` sincronizables.
- Reads: `QUERY_READLIKE`.

## Modelo SQL auditado/usado
Se auditaron nombres equivalentes (`apertura_caja`, `caja_apertura`, `caja_sesion`, `caja_operativa_apertura`, `jornada_caja`). Al no existir modelo suficiente se agrega `caja_operativa_apertura` mediante `backend/database/patch_apertura_cierre_caja_operativa_20260706.sql` y se actualiza el dump principal.

## Regla principal
Una caja operativa puede tener como máximo una apertura vigente, definida por:
- `estado_apertura = 'ABIERTA'`;
- `fecha_hora_cierre IS NULL`;
- `deleted_at IS NULL`.

La apertura puede ocurrir un día y cerrarse otro. No se fuerza cierre diario. La consulta de vigentes permite detectar cajas abiertas desde días anteriores para advertencias de UI al iniciar el sistema o entrar al módulo de caja.

## Endpoints

### POST `/api/v1/operativo/cajas/{id_caja}/aperturas`
Abre una caja activa en sucursal/instalación activas y pertenecientes entre sí. Si no se informa `fecha_hora_apertura`, usa hora actual UTC según patrón backend.

### PATCH `/api/v1/operativo/cajas/aperturas/{id_apertura_caja}/cerrar`
Cierra una apertura vigente. Requiere `If-Match-Version`, incrementa `version_registro`, setea cierre declarado y marca `estado_apertura = 'CERRADA'`. Permite cierre en día posterior; rechaza fecha de cierre anterior a apertura.

### GET `/api/v1/operativo/cajas/{id_caja}/apertura-vigente`
Consulta read-like de apertura vigente por caja. Devuelve `data: null` si no existe.

### GET `/api/v1/operativo/cajas/aperturas-vigentes`
Consulta read-like por contexto con filtros `id_sucursal`, `id_instalacion`, `abiertas_desde_antes_de` y `solo_abiertas_de_dias_anteriores`. Incluye datos de caja para advertencias.

## CORE-EF
- Apertura: headers `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; idempotencia por `op_id_alta`; replay compatible no duplica apertura ni outbox; replay incompatible devuelve `409 IDEMPOTENT_DUPLICATE`.
- Cierre: mismos headers y `If-Match-Version` obligatorio; mismatch devuelve `412 CONCURRENCY_ERROR`.
- Outbox: apertura real emite `EVT-OPE-015` (`caja_operativa_abierta`); cierre real emite `EVT-OPE-016` (`caja_operativa_cerrada`) en la misma transacción.
- Lock lógico: NO APLICA en este alcance; la unicidad parcial de apertura vigente cubre la regla crítica.
- Rollback: operación de negocio y outbox comparten transacción del repository.

## Fuera de alcance
Movimientos de caja, ingresos/egresos manuales, pagos, imputaciones, arqueo avanzado, diferencias automáticas, reportes, jornada operativa completa, permisos avanzados y UI frontend.

Closes #254. Refs #248.
