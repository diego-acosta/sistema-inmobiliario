# DEV-API-OPE-001 — API operativa inicial de sucursales

## Relación con issues

- Implementación inicial: #250.
- Referencia técnica previa: #248.

## Dominio y clasificación

`sucursal` es una entidad núcleo del dominio operativo/organizacional. La API se expone bajo `/api/v1/operativo` para no invadir los dominios administrativo, comercial, financiero, inmobiliario ni analítico.

## Endpoints implementados

### POST `/api/v1/operativo/sucursales`

Alta mínima de sucursal. La creación real devuelve `201 Created`.

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
- `estado_sucursal` opcional, default `ACTIVA`; valores permitidos: `ACTIVA`, `INACTIVA`, `DADA_DE_BAJA`.
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

- `op_id_alta` tiene unicidad estructural mediante índice único parcial `ux_sucursal_op_id_alta`.
- Mismo `X-Op-Id` con payload compatible devuelve la sucursal ya creada, sin duplicar registro ni outbox.
- Decisión actual: el replay idempotente compatible devuelve el mismo status del endpoint (`201`) aunque no cree una fila nueva.
- Mismo `X-Op-Id` con payload incompatible devuelve `409 IDEMPOTENT_DUPLICATE`.

Outbox:

- Se registra `sucursal_creada` en `outbox_event` en la misma transacción del alta real, alineado con `EVT-OPE-001`; el replay idempotente compatible no duplica outbox.

Errores esperados:

- `400 VALIDATION_ERROR` por headers CORE-EF faltantes o inválidos.
- `422 Unprocessable Entity` por payload inválido, incluyendo `estado_sucursal` fuera del catálogo permitido.
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
- Status POST: creación real devuelve `201 Created`; replay compatible mantiene `201` como decisión actual del endpoint.
- Catálogo `estado_sucursal`: `ACTIVA`, `INACTIVA`, `DADA_DE_BAJA`; otros valores devuelven `422`.
- Idempotencia: aplica por `op_id_alta` con unicidad estructural `ux_sucursal_op_id_alta`; mismo op/payload compatible retorna el registro sin duplicar fila ni outbox, mismo op/payload incompatible devuelve conflicto.
- Outbox: aplica; evento `sucursal_creada` en misma transacción solo para creación real.
- Lock lógico: NO APLICA en alta mínima porque no modifica una entidad existente ni orquesta recursos compartidos; queda para modificación/baja.
- Versionado: alta crea entidad con `version_registro = 1`; `If-Match-Version` NO APLICA porque no modifica entidad existente.
- Rollback/transacción: alta de `sucursal` y outbox comparten commit/rollback del repository.
- GETs: `QUERY_READLIKE`; no fuerzan headers write.

## Instalaciones

### POST `/api/v1/operativo/instalaciones`

Alta mínima de instalación como entidad base del dominio operativo. Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO` sincronizable.

Headers CORE-EF obligatorios mediante helper común:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`

Validaciones y persistencia:

- `id_sucursal`, `codigo_instalacion` y `nombre_instalacion` son obligatorios.
- `id_sucursal` debe referenciar una sucursal existente y activa (`deleted_at IS NULL`).
- `estado_instalacion` admite `ACTIVA`, `INACTIVA` o `DADA_DE_BAJA`.
- No se permite duplicado activo de `codigo_instalacion`.
- Persiste `uid_global`, `version_registro = 1`, timestamps base, instalación de origen/última modificación y `op_id_alta`/`op_id_ultima_modificacion`.
- Devuelve `201 Created` con envelope estándar y `version_registro`.

Idempotencia:

- Aplica por `instalacion.op_id_alta` con índice único parcial `ux_instalacion_op_id_alta`.
- Mismo `X-Op-Id` con payload compatible devuelve la instalación existente sin duplicar fila ni outbox.
- Mismo `X-Op-Id` con payload incompatible devuelve `409 IDEMPOTENT_DUPLICATE`.
- Duplicado activo de `codigo_instalacion` con otro `X-Op-Id` devuelve `409 TECHNICAL_INCONSISTENCY`.

Outbox:

- Emite `instalacion_creada` (`EVT-OPE-004 — Instalación creada`) en `outbox_event` en la misma transacción del alta real.
- Replay idempotente compatible no duplica outbox.

Errores esperados:

- `400 VALIDATION_ERROR` por headers CORE-EF faltantes o inválidos.
- `404 NOT_FOUND` si la sucursal no existe o está dada de baja.
- `409 IDEMPOTENT_DUPLICATE` por replay con payload incompatible.
- `409 TECHNICAL_INCONSISTENCY` por duplicado activo u otra restricción técnica.
- `422` por validaciones de schema, incluido estado inválido.

### GET `/api/v1/operativo/instalaciones`

Listado read-like de instalaciones activas, sin headers CORE-EF write.

Clasificación CORE-EF: `QUERY_READLIKE`.

Filtros opcionales:

- `id_sucursal`
- `estado_instalacion`

Excluye registros con `deleted_at IS NOT NULL` y devuelve envelope estándar.

### GET `/api/v1/operativo/instalaciones/{id_instalacion}`

Ficha read-like de instalación, sin headers CORE-EF write.

Clasificación CORE-EF: `QUERY_READLIKE`.

Excluye registros con `deleted_at IS NOT NULL`. Si no existe, devuelve `404 NOT_FOUND`.

### Fuera de alcance instalaciones

- Modificación de instalación.
- Baja lógica.
- Sincronización avanzada.
- `usuario_sucursal`, `usuario_rol_sucursal` y alcance operativo.
- Autorización real.
- Caja y jornada.

### Decisión CORE-EF instalaciones

- Naturaleza POST: `COMMAND_WRITE_NEGOCIO` sincronizable.
- Headers POST: obligatorios mediante helper común CORE-EF; no aplica `If-Match-Version` porque es alta y no modifica entidad existente versionada.
- Idempotencia: aplica por `op_id_alta`; mismo op/payload compatible retorna registro existente, mismo op/payload distinto devuelve conflicto.
- Outbox: aplica, evento `instalacion_creada`, misma transacción que negocio.
- Lock lógico: NO APLICA; no hay modificación concurrente de entidad existente.
- Versionado: entidad `instalacion` nace con `version_registro = 1`.
- Rollback/transacción: alta de `instalacion` y outbox comparten commit/rollback del repository.
- Read-like: listados/fichas son `QUERY_READLIKE`, sin headers write.
