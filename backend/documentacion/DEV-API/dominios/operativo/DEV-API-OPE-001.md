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

## Configuración local operativa (#252)

La configuración local pertenece al dominio `operativo` porque parametriza el comportamiento mínimo de una sucursal/instalación técnica. Es núcleo operativo acotado, no autorización, no sesión, no caja, no jornada y no permisos.

### Modelo SQL auditado/usado

Se auditó el modelo existente: `sucursal`, `instalacion`, `parametro_sistema` y `valor_parametro`. `valor_parametro` ya permite alcance por `id_sucursal`/`id_instalacion`, pero en el dump vigente no contiene metadata CORE-EF completa (`uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, instalación origen/modificación, `op_id_alta`, `op_id_ultima_modificacion`) ni índices de idempotencia para writes sincronizables. Por eso se agrega el patch mínimo `backend/database/patch_configuracion_local_operativa_20260703.sql` con `configuracion_local`.

### GET `/api/v1/operativo/configuracion-local`

Consulta read-like (`QUERY_READLIKE`) por `id_sucursal` e `id_instalacion`. No requiere headers CORE-EF write.

Reglas:

- Valida que la sucursal exista, no tenga `deleted_at` y no esté `DADA_DE_BAJA`.
- Valida que la instalación exista, no tenga `deleted_at` y no esté `DADA_DE_BAJA`.
- Valida pertenencia de instalación a sucursal mediante `instalacion.id_sucursal`.
- Si no hay configuración local activa para el contexto, devuelve `data: []`. Se elige lista vacía para no inventar valores efectivos no persistidos.

Errores:

- `404 NOT_FOUND` para sucursal o instalación inexistente/dada de baja.
- `400 VALIDATION_ERROR` si la instalación no pertenece a la sucursal.

### POST `/api/v1/operativo/configuracion-local`

Crea configuración local. Clasificación CORE-EF: `COMMAND_WRITE_TECNICO` sincronizable.

Payload:

- `id_sucursal`
- `id_instalacion`
- `clave_configuracion`
- `valor_configuracion`
- `tipo_valor`: `TEXTO`, `NUMERO`, `DECIMAL`, `BOOLEANO`, `FECHA`, `JSON`
- `descripcion`
- `estado_configuracion`: `ACTIVA`, `INACTIVA`

Claves mínimas permitidas en esta primera versión:

- `modo_operacion_local`
- `permite_operar_offline`
- `requiere_jornada_abierta`
- `requiere_caja_abierta`
- `observaciones_locales`

Headers CORE-EF obligatorios mediante helper común:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`

Idempotencia:

- Aplica por `op_id_alta` con índice único parcial `ux_configuracion_local_op_id_alta`.
- Mismo `X-Op-Id` con payload compatible devuelve el registro existente sin duplicar fila ni outbox.
- Mismo `X-Op-Id` con payload distinto devuelve `409 IDEMPOTENT_DUPLICATE`.

Outbox:

- Aplica; emite `configuracion_local_creada` (`EVT-OPE-012`) en `outbox_event` en la misma transacción del alta real.

Versionado:

- El alta crea `version_registro = 1`.
- `If-Match-Version` no aplica al POST porque no modifica una entidad existente/versionada.

### PUT `/api/v1/operativo/configuracion-local/{id_configuracion_local}`

Actualiza configuración local existente. Se elige POST para creación y PUT por identificador para actualización para mantener CORE-EF limpio y exigir concurrencia optimista en modificaciones versionadas.

Clasificación CORE-EF: `COMMAND_WRITE_TECNICO` sincronizable.

Headers:

- Requiere los headers CORE-EF obligatorios.
- Requiere `If-Match-Version`; debe coincidir con `version_registro` actual.

Reglas:

- Incrementa `version_registro`.
- Actualiza `updated_at`, `id_instalacion_ultima_modificacion` y `op_id_ultima_modificacion`.
- Mantiene unicidad activa por `(id_sucursal, id_instalacion, clave_configuracion)`.
- Emite `configuracion_local_modificada` (`EVT-OPE-013`) en `outbox_event` en la misma transacción del update real.

Errores:

- `400 VALIDATION_ERROR` por headers CORE-EF faltantes/inválidos, `If-Match-Version` faltante/inválido o pertenencia inválida.
- `404 NOT_FOUND` por configuración, sucursal o instalación inexistente/dada de baja.
- `409 TECHNICAL_INCONSISTENCY` por duplicado activo de clave/contexto.
- `412 CONCURRENCY_ERROR` por mismatch de `If-Match-Version`.
- `422 Unprocessable Entity` por payload inválido (`clave_configuracion` vacía/no catalogada, `tipo_valor` inválido o estado inválido).

### Decisión CORE-EF configuración local

- Naturaleza endpoints: GET `QUERY_READLIKE`; POST/PUT `COMMAND_WRITE_TECNICO` sincronizable.
- Headers: POST/PUT usan helper común CORE-EF; GET no requiere headers write.
- Idempotencia: aplica en creación por `op_id_alta`; no aplica idempotencia profunda al update, que se protege con `If-Match-Version`.
- Outbox: aplica para creación y modificación con eventos `configuracion_local_creada` y `configuracion_local_modificada`.
- Lock lógico: NO APLICA en esta versión; no se bloquean caja, jornada ni operaciones de negocio.
- Versionado: `configuracion_local.version_registro` nace en 1 y aumenta en cada PUT.
- Rollback/transacción: escritura de `configuracion_local` y `outbox_event` comparten transacción del repository.

### Fuera de alcance

No implementa autorización real, middleware de seguridad, login, contexto de sesión, `usuario_instalacion`, permisos complejos, caja, jornada, movimientos, pagos, sincronización avanzada, frontend, configuración global administrativa (#263) ni catálogos maestros (#264).

Closes #252. Refs #248.

## Caja operativa base (#253 / Refs #248)

### Modelo SQL auditado/usado

Se auditó el modelo SQL existente para `caja`, `caja_operativa`, `cuenta_financiera`, `movimiento_tesoreria`, `jornada_operativa`, `sucursal`, `instalacion`, `configuracion_local` y tablas relacionadas con caja/tesorería/efectivo. No se encontró una tabla formal `caja`/`caja_operativa` suficiente en el dump vigente. Se crea `caja_operativa` con `backend/database/patch_caja_operativa_base_20260704.sql` porque `cuenta_financiera` y `movimiento_tesoreria` corresponden a tesorería/finanzas y no deben usarse como núcleo de caja operativa.

### POST `/api/v1/operativo/cajas`

Crea una caja operativa base. Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO` sincronizable.

Payload: `id_sucursal`, `id_instalacion`, `codigo_caja`, `nombre_caja`, `tipo_caja`, `moneda_base`, `estado_caja`, `permite_efectivo`, `permite_transferencia`, `permite_cheque`, `descripcion`, `observaciones`.

Reglas:
- Requiere `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` mediante helper CORE-EF.
- Valida que sucursal e instalación existan, no estén dadas de baja y pertenezcan entre sí.
- `codigo_caja` activo es único por `(id_sucursal, id_instalacion)`.
- Persiste `uid_global`, `version_registro = 1`, timestamps, instalación origen/modificación y op_ids.
- Idempotencia por `op_id_alta`: mismo op/payload devuelve la caja existente; mismo op/payload distinto devuelve `409 IDEMPOTENT_DUPLICATE`.
- Outbox: emite `caja_operativa_creada` (`EVT-OPE-014`) en la misma transacción del alta real; replay compatible no duplica outbox.
- Lock lógico: NO APLICA en #253.
- `If-Match-Version`: NO APLICA porque es alta y no modifica entidad existente versionada.

Errores: `400 VALIDATION_ERROR` para headers o pertenencia inválida, `404 NOT_FOUND` para sucursal/instalación inexistente o dada de baja, `409 TECHNICAL_INCONSISTENCY` para duplicado activo, `409 IDEMPOTENT_DUPLICATE` para replay incompatible y `422` para validación de payload.

### GET `/api/v1/operativo/cajas`

Listado read-like (`QUERY_READLIKE`), sin headers CORE-EF write. Filtros opcionales: `id_sucursal`, `id_instalacion`, `estado_caja`, `tipo_caja`. Excluye `deleted_at IS NOT NULL` y devuelve lista vacía si no hay resultados.

### GET `/api/v1/operativo/cajas/{id_caja}`

Ficha read-like (`QUERY_READLIKE`), sin headers CORE-EF write. Excluye `deleted_at IS NOT NULL`; si no existe devuelve `404 NOT_FOUND`.

### Fuera de alcance explícito

Apertura/cierre de caja, caja abierta/cerrada, saldos, movimientos, arqueo, observaciones de control, pagos, imputaciones, lectura financiera, jornada operativa, reportes, autorización real, usuario_instalacion y frontend.
