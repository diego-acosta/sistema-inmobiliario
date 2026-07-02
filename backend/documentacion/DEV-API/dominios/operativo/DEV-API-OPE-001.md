# DEV-API-OPE-001 — API operativa inicial de sucursales

## Relación con issues

- Implementación inicial: #250.
- Referencia técnica previa: #248.

## Dominio y clasificación

`sucursal` es una entidad núcleo del dominio operativo/organizacional. La API se expone bajo `/api/v1/operativo` para no invadir los dominios administrativo, comercial, financiero, inmobiliario ni analítico.

## Endpoints implementados

### POST `/api/v1/operativo/sucursales`

Alta mínima de sucursal.

Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO` sincronizable.

Headers obligatorios:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`

Payload mínimo:

- `codigo_sucursal` obligatorio.
- `nombre_sucursal` obligatorio.
- `descripcion_sucursal` opcional.
- `estado_sucursal` opcional, default `ACTIVA`.
- `es_casa_central` opcional, default `false`.
- `permite_operacion` opcional, default `true`.
- `observaciones` opcional.

Persistencia CORE-EF:

- `uid_global` por default SQL.
- `version_registro = 1`.
- `created_at` y `updated_at` por default SQL.
- `id_instalacion_origen` e `id_instalacion_ultima_modificacion` desde `X-Instalacion-Id`.
- `op_id_alta` y `op_id_ultima_modificacion` desde `X-Op-Id`.
- `deleted_at` no se setea en alta.

Idempotencia:

- Mismo `X-Op-Id` con payload compatible devuelve la sucursal ya creada.
- Mismo `X-Op-Id` con payload incompatible devuelve `409 IDEMPOTENT_DUPLICATE`.

Outbox:

- Se registra `sucursal_creada` en `outbox_event` en la misma transacción del alta, alineado con `EVT-OPE-001`.

Errores esperados:

- `400 VALIDATION_ERROR` por headers CORE-EF faltantes o inválidos.
- `409 IDEMPOTENT_DUPLICATE` por reutilización incompatible de `X-Op-Id`.
- `409 TECHNICAL_INCONSISTENCY` por duplicado activo de `codigo_sucursal` o restricción SQL.
- `500 TECHNICAL_INCONSISTENCY` ante error técnico no controlado.

### GET `/api/v1/operativo/sucursales`

Listado read-like de sucursales activas, sin headers CORE-EF write.

Clasificación CORE-EF: `QUERY_READLIKE`.

Reglas:

- Excluye registros con `deleted_at IS NOT NULL`.
- Permite filtro opcional `estado_sucursal`.
- Devuelve envelope estándar `{ "ok": true, "data": [...] }`.

### GET `/api/v1/operativo/sucursales/{id_sucursal}`

Ficha read-like de sucursal, sin headers CORE-EF write.

Clasificación CORE-EF: `QUERY_READLIKE`.

Reglas:

- Excluye registros con `deleted_at IS NOT NULL`.
- Si no existe, devuelve `404 NOT_FOUND`.
- Devuelve envelope estándar `{ "ok": true, "data": {...} }`.

## Fuera de alcance

No se implementa todavía:

- modificación de sucursal;
- baja lógica;
- instalaciones;
- usuario_sucursal;
- usuario_rol_sucursal;
- alcance operativo;
- autorización real;
- permisos efectivos;
- menú dinámico;
- caja;
- jornada.

## Decisión CORE-EF

- Naturaleza POST: `COMMAND_WRITE_NEGOCIO` sincronizable.
- Headers POST: obligatorios mediante helper común CORE-EF.
- Idempotencia: aplica por `op_id_alta`; mismo op/payload compatible retorna el registro, mismo op/payload incompatible devuelve conflicto.
- Outbox: aplica; evento `sucursal_creada` en misma transacción.
- Lock lógico: NO APLICA en alta mínima porque no modifica una entidad existente ni orquesta recursos compartidos; queda para modificación/baja.
- Versionado: alta crea entidad con `version_registro = 1`; `If-Match-Version` NO APLICA porque no modifica entidad existente.
- Rollback/transacción: alta de `sucursal` y outbox comparten commit/rollback del repository.
- GETs: `QUERY_READLIKE`; no fuerzan headers write.
