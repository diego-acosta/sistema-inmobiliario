# DEV-API-ADM-001 — Dominio Administrativo

## 1. Alcance y fuentes auditadas

Este documento consolida el contrato DEV-API vigente del dominio `administrativo` para los endpoints implementados después de las issues/PRs #249, #259, #260 y #261.

Fuentes verificadas:

- `backend/documentacion/DEV-API/`: convenciones de contrato API por dominio y envelopes documentales existentes.
- `backend/documentacion/DEV-SRV/dominios/administrativo/`: `SRV-ADM-001`, `SRV-ADM-002`, catálogos `EVT-ADM` y `RN-ADM`.
- `backend/documentacion/CORE-EF/`: headers técnicos, idempotencia, concurrencia, outbox e infraestructura transversal.
- `backend/documentacion/DECISIONES/`: decisión transversal de transactional outbox.
- `AGENTS.md`: reglas transversales de ownership de dominios y checklist CORE-EF para endpoints write.
- Implementación real: router, schemas, repositories, SQL visible en repositorios y tests existentes del dominio administrativo.

No se documentan endpoints inexistentes ni se cambian contratos API. Todo endpoint no listado en este documento queda `NO IMPLEMENTADO` para esta especificación.

## 2. Criterios generales del dominio

Clasificación de conceptos:

| Concepto | Clasificación | Regla |
| --- | --- | --- |
| `usuario` del sistema | núcleo administrativo | No es `persona`; no redefine identidad base del dominio Personas. |
| `rol_seguridad` | núcleo administrativo de seguridad | No es `rol_participacion`; no representa roles de negocio. |
| `permiso` | núcleo administrativo de seguridad | No es rol de negocio ni participación contextual. |
| `usuario_rol_seguridad` | núcleo administrativo de seguridad | Materializa asignación vigente o histórica entre usuario y rol de seguridad. |
| headers CORE-EF/outbox/versionado | soporte transversal | Se aplican sin redefinir la semántica de CORE-EF. |

Criterios explícitos:

- `usuario` del sistema **NO** es `persona`.
- `rol_seguridad` **NO** es `rol_participacion`.
- `permiso` **NO** es rol de negocio.
- Administrativo todavía **NO implementa login**.
- Administrativo todavía **NO implementa passwords**.
- Administrativo todavía **NO implementa OAuth/SSO**.
- Administrativo todavía **NO implementa middleware de autorización real**.
- Administrativo todavía **NO implementa menú dinámico**.
- Administrativo todavía **NO implementa alcance por sucursal**.

## 3. Criterios API globales aplicados

- Base path: `/api/v1`.
- Rutas: minúsculas, `kebab-case`, sustantivos y subrecursos explícitos.
- Envelope de éxito:

```json
{ "ok": true, "data": {} }
```

- Envelope de error:

```json
{
  "ok": false,
  "error_code": "...",
  "error_message": "...",
  "details": {}
}
```

- Writes sincronizables CORE-EF requieren headers:
  - `X-Op-Id`
  - `X-Usuario-Id`
  - `X-Sucursal-Id`
  - `X-Instalacion-Id`
- `If-Match-Version` es obligatorio cuando la operación modifica una entidad existente versionada.
- Las responses sincronizables exponen `version_registro` cuando la entidad persistida lo contiene.
- La baja lógica usa `deleted_at`; en asignaciones de roles también usa `fecha_hasta`.
- Outbox se registra en la misma transacción que el cambio de negocio cuando la operación sincronizable lo implementa.
- Los errores generados dentro de handlers usan el envelope propio del sistema (`{ "ok": false, "error_code", "error_message", "details" }`). Esto incluye headers CORE-EF faltantes/inválidos, `If-Match-Version` faltante/inválido y validaciones manuales de aplicación.
- Los errores de validación automática FastAPI/Pydantic que ocurren antes de entrar al handler responden actualmente HTTP `422 Unprocessable Entity` con el formato estándar de FastAPI (`{ "detail": [...] }`). Esto aplica a body, path y query inválidos, por ejemplo body mal tipado, campo requerido faltante o path/query con tipo incompatible.

## 4. Usuarios del sistema

### 4.1 `POST /api/v1/administrativo/usuarios`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Objetivo funcional: crear un usuario administrativo del sistema.
- Headers obligatorios:
  - `X-Op-Id`
  - `X-Usuario-Id`
  - `X-Sucursal-Id`
  - `X-Instalacion-Id`
- `If-Match-Version`: NO APLICA; es alta de entidad nueva.
- Idempotencia: aplica por `X-Op-Id` / `op_id_alta`.
  - mismo `X-Op-Id` + mismo payload: devuelve el mismo resultado sin duplicar usuario.
  - mismo `X-Op-Id` + payload distinto: `409 IDEMPOTENT_DUPLICATE`.
  - retry post-error: solo se considera idempotente si existe registro persistido con ese `op_id_alta`.
- Versionado: crea con `version_registro = 1`.
- Outbox: conceptualmente sincronizable según `SRV-ADM-001`/`EVT-ADM`; en la implementación vigente de usuario base no se evidencia evento outbox persistido en tests/repositorio, por lo que queda `NO CONFIRMADO` para esta operación.
- Lock lógico: NO APLICA; no hay lock lógico implementado para alta de usuario.
- Frontera transaccional: inserción de `usuario` y metadatos CORE-EF del alta.

Request principal:

```json
{
  "codigo_usuario": "USR-ADM-001",
  "login": "usr.adm.001",
  "email": "usr.adm.001@example.com",
  "estado_usuario": "ACTIVO",
  "usuario_sistema_interno": false,
  "observaciones": "Usuario administrativo"
}
```

Response principal (`201`):

```json
{
  "ok": true,
  "data": {
    "id_usuario": 1,
    "codigo_usuario": "USR-ADM-001",
    "login": "usr.adm.001",
    "email": "usr.adm.001@example.com",
    "estado_usuario": "ACTIVO",
    "fecha_alta": "2026-01-01T00:00:00",
    "fecha_baja": null,
    "fecha_ultimo_acceso": null,
    "usuario_sistema_interno": false,
    "observaciones": "Usuario administrativo",
    "version_registro": 1
  }
}
```

Errores esperados:

- `400 VALIDATION_ERROR`: headers CORE-EF faltantes/inválidos o validaciones manuales del handler.
- `422 Unprocessable Entity`: request body/path/query inválido detectado automáticamente por FastAPI/Pydantic antes de entrar al handler.
- `409 IDEMPOTENT_DUPLICATE`: mismo `X-Op-Id` con payload incompatible.
- `409 TECHNICAL_INCONSISTENCY`: código o login duplicado, u otra inconsistencia técnica controlada.
- `500 TECHNICAL_INCONSISTENCY`: fallo técnico no controlado.

Fuera de alcance del endpoint: autenticación real, password, login efectivo y autorización.

### 4.2 `GET /api/v1/administrativo/usuarios`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar usuarios del sistema.
- Headers CORE-EF: NO APLICA; endpoint read-only.
- Query params:
  - `incluir_bajas` (`bool`, default `false`): si es `false`, excluye registros con baja lógica.
- Idempotencia: NO APLICA.
- `If-Match-Version`: NO APLICA.
- Outbox: NO APLICA.

Response principal (`200`): envelope `{ "ok": true, "data": [UsuarioSistemaData] }`.

Errores esperados: `500 TECHNICAL_INCONSISTENCY`.

### 4.3 `GET /api/v1/administrativo/usuarios/{id_usuario}`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: obtener detalle de un usuario del sistema.
- Headers CORE-EF: NO APLICA.
- Idempotencia: NO APLICA.
- `If-Match-Version`: NO APLICA.
- Outbox: NO APLICA.

Response principal (`200`): envelope `{ "ok": true, "data": UsuarioSistemaData }`.

Errores esperados:

- `404 NOT_FOUND`: usuario inexistente.
- `500 TECHNICAL_INCONSISTENCY`.

### 4.4 `PATCH /api/v1/administrativo/usuarios/{id_usuario}/baja`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Objetivo funcional: dar de baja lógica a un usuario del sistema.
- Headers obligatorios:
  - `X-Op-Id`
  - `X-Usuario-Id`
  - `X-Sucursal-Id`
  - `X-Instalacion-Id`
  - `If-Match-Version`
- Idempotencia: aplica por `X-Op-Id` / `op_id_ultima_modificacion` para retry de baja ya aplicada.
  - mismo `X-Op-Id` sobre la misma baja ya persistida: devuelve el estado ya dado de baja sin incrementar dos veces `version_registro`.
  - versión distinta sin baja previa por ese `X-Op-Id`: `409 CONCURRENCY_ERROR`.
- Versionado: requiere `If-Match-Version`; al aplicar baja incrementa `version_registro + 1`.
- Baja lógica: establece `estado_usuario = INACTIVO`, `fecha_baja` y `deleted_at`.
- Outbox: conceptualmente sincronizable según `SRV-ADM-001`/`EVT-ADM` (`usuario_desactivado`); en la implementación vigente no se evidencia evento outbox persistido en tests/repositorio, por lo que queda `NO CONFIRMADO` para esta operación.
- Lock lógico: NO APLICA; no hay lock lógico implementado.
- Frontera transaccional: actualización del usuario y metadatos CORE-EF de modificación.

Response principal (`200`): envelope `{ "ok": true, "data": UsuarioSistemaData }` con `fecha_baja`, `estado_usuario = INACTIVO`, `deleted_at` persistido y `version_registro` incrementado.

Errores esperados:

- `400 VALIDATION_ERROR`: headers CORE-EF faltantes/inválidos o `If-Match-Version` faltante/inválido.
- `404 NOT_FOUND`: usuario inexistente.
- `409 CONCURRENCY_ERROR`: mismatch real de versión.
- `500 TECHNICAL_INCONSISTENCY`.

Fuera de alcance del endpoint: autenticación real, password, login efectivo y autorización.

## 5. Roles de seguridad y permisos

Estos endpoints son read-only sobre catálogos/asociaciones de seguridad ya persistidos. No asignan roles a usuarios.

### 5.1 `GET /api/v1/administrativo/roles-seguridad`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar roles de seguridad.
- Headers CORE-EF: NO APLICA.
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.

Response principal (`200`): `{ "ok": true, "data": [RolSeguridadData] }`.

### 5.2 `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: obtener detalle de un rol de seguridad.
- Headers CORE-EF: NO APLICA.
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.

Response principal (`200`): `{ "ok": true, "data": RolSeguridadData }`.

Errores esperados: `404 NOT_FOUND`, `500 TECHNICAL_INCONSISTENCY`.

### 5.3 `GET /api/v1/administrativo/permisos`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar permisos de seguridad.
- Headers CORE-EF: NO APLICA.
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.

Response principal (`200`): `{ "ok": true, "data": [PermisoData] }`.

### 5.4 `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/permisos`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar permisos asociados a un rol de seguridad.
- Headers CORE-EF: NO APLICA.
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.
- No asigna roles a usuarios.

Response principal (`200`): `{ "ok": true, "data": [PermisoData] }`.

Errores esperados: `404 NOT_FOUND`, `500 TECHNICAL_INCONSISTENCY`.

Modelos de lectura:

```json
{
  "id_rol_seguridad": 1,
  "codigo_rol": "ADMIN",
  "nombre_rol": "Administrador",
  "descripcion": "...",
  "estado_rol": "ACTIVO"
}
```

```json
{
  "id_permiso": 1,
  "codigo_permiso": "ADM_USUARIOS_LEER",
  "nombre_permiso": "Leer usuarios",
  "descripcion": "...",
  "estado_permiso": "ACTIVO"
}
```

## 6. Asignación de roles de seguridad a usuarios

- Tabla física: `usuario_rol_seguridad`.
- Unicidad activa: no puede existir más de una asignación activa para `(id_usuario, id_rol_seguridad)` con `deleted_at IS NULL` y `fecha_hasta IS NULL`.
- Duplicado activo con otro `X-Op-Id`: rechaza con HTTP `409` y error de inconsistencia técnica controlada.
- Eventos outbox sincronizables implementados:
  - `rol_asignado_a_usuario`
  - `rol_revocado_de_usuario`
- Aggregate outbox: `usuario_rol_seguridad`.

### 6.1 `GET /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar roles de seguridad asignados a un usuario.
- Headers CORE-EF: NO APLICA.
- Query params:
  - `incluir_bajas` (`bool`, default `false`): si es `false`, excluye asignaciones con `deleted_at` o `fecha_hasta`.
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.

Response principal (`200`): `{ "ok": true, "data": [UsuarioRolSeguridadData] }`.

Errores esperados: `404 NOT_FOUND`, `500 TECHNICAL_INCONSISTENCY`.

### 6.2 `POST /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Objetivo funcional: asignar un rol de seguridad existente a un usuario existente.
- Headers obligatorios:
  - `X-Op-Id`
  - `X-Usuario-Id`
  - `X-Sucursal-Id`
  - `X-Instalacion-Id`
- `If-Match-Version`: NO APLICA; es alta de asignación nueva.
- Idempotencia: aplica por `op_id_alta`.
  - mismo `X-Op-Id` + mismo `id_usuario`/`id_rol_seguridad`: devuelve la misma asignación.
  - mismo `X-Op-Id` + rol o usuario distinto: `409 IDEMPOTENT_DUPLICATE`.
  - retry idempotente de alta no duplica asignación ni outbox.
- Versionado: crea la asignación con `version_registro = 1`.
- Baja lógica: NO APLICA en alta.
- Outbox: aplica, registra `rol_asignado_a_usuario` en la misma transacción que el alta.
- Lock lógico: NO APLICA; no hay lock lógico implementado.
- Frontera transaccional: inserción de `usuario_rol_seguridad` + evento outbox; si falla outbox, se revierte la asignación.

Request principal:

```json
{ "id_rol_seguridad": 1 }
```

Response principal (`201`):

```json
{
  "ok": true,
  "data": {
    "id_usuario_rol_seguridad": 10,
    "id_usuario": 1,
    "id_rol_seguridad": 1,
    "fecha_desde": "2026-01-01T00:00:00",
    "fecha_hasta": null,
    "version_registro": 1,
    "updated_at": "2026-01-01T00:00:00",
    "deleted_at": null,
    "id_instalacion_origen": 1,
    "id_instalacion_ultima_modificacion": 1,
    "op_id_alta": "...",
    "op_id_ultima_modificacion": "...",
    "codigo_rol": "ADMIN",
    "nombre_rol": "Administrador",
    "descripcion": "...",
    "estado_rol": "ACTIVO"
  }
}
```

Errores esperados:

- `400 VALIDATION_ERROR`: headers CORE-EF faltantes/inválidos o validaciones manuales del handler.
- `422 Unprocessable Entity`: request body/path/query inválido detectado automáticamente por FastAPI/Pydantic antes de entrar al handler.
- `404 NOT_FOUND`: usuario o rol inexistente.
- `409 IDEMPOTENT_DUPLICATE`: mismo `X-Op-Id` con payload incompatible.
- `409 TECHNICAL_INCONSISTENCY`: duplicado activo de `(id_usuario, id_rol_seguridad)` u otra inconsistencia técnica controlada.
- `500 TECHNICAL_INCONSISTENCY`: fallo técnico; si ocurre durante outbox, la asignación debe quedar revertida.

### 6.3 `PATCH /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad/{id_asignacion}/baja`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Objetivo funcional: revocar/dar de baja lógica una asignación de rol de seguridad de un usuario.
- Headers obligatorios:
  - `X-Op-Id`
  - `X-Usuario-Id`
  - `X-Sucursal-Id`
  - `X-Instalacion-Id`
  - `If-Match-Version`
- Idempotencia: aplica por `op_id_ultima_modificacion` para retry de baja ya aplicada.
  - retry idempotente de baja no duplica outbox ni incrementa versión dos veces.
  - mismatch real de versión: `409 CONCURRENCY_ERROR`.
- Versionado: requiere `If-Match-Version`; al aplicar baja usa `version_registro + 1`.
- Baja lógica: establece `fecha_hasta`, `deleted_at`, `updated_at`, `id_instalacion_ultima_modificacion` y `op_id_ultima_modificacion`.
- Outbox: aplica, registra `rol_revocado_de_usuario` en la misma transacción que la baja.
- Lock lógico: NO APLICA; no hay lock lógico implementado.
- Frontera transaccional: actualización de `usuario_rol_seguridad` + evento outbox; si falla outbox, se revierte la baja.

Response principal (`200`): `{ "ok": true, "data": UsuarioRolSeguridadData }` con `fecha_hasta`, `deleted_at` y versión incrementada.

Errores esperados:

- `400 VALIDATION_ERROR`: headers CORE-EF faltantes/inválidos o `If-Match-Version` faltante/inválido.
- `404 NOT_FOUND`: asignación inexistente o no perteneciente al usuario indicado.
- `409 CONCURRENCY_ERROR`: mismatch real de versión.
- `500 TECHNICAL_INCONSISTENCY`: fallo técnico; si ocurre durante outbox, la baja debe quedar revertida.

### 6.4 `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/usuarios`

- Estado: implementado.
- Clasificación CORE-EF: `QUERY_READLIKE`.
- Objetivo funcional: listar usuarios/asignaciones asociados a un rol de seguridad.
- Headers CORE-EF: NO APLICA.
- Query params:
  - `incluir_bajas` (`bool`, default `false`).
- Writes/outbox/idempotencia/`If-Match-Version`: NO APLICA.

Response principal (`200`): `{ "ok": true, "data": [UsuarioRolSeguridadData] }`.

Errores esperados: `404 NOT_FOUND`, `500 TECHNICAL_INCONSISTENCY`.

Fuera de alcance de asignaciones:

- autorización real;
- permisos efectivos;
- alcance por sucursal;
- UI/menú dinámico.

## 7. Errores estándar usados

| Error code | HTTP habitual | Uso |
| --- | ---: | --- |
| `VALIDATION_ERROR` | 400 | Header CORE-EF faltante/inválido, `If-Match-Version` faltante/inválido o validación manual de aplicación generada dentro del handler con envelope propio. |
| Validación automática FastAPI/Pydantic | 422 | Body, path o query inválidos detectados antes de entrar al handler; usa formato estándar `{ "detail": [...] }`, no el envelope propio. |
| `NOT_FOUND` | 404 | Usuario, rol o asignación inexistente según endpoint. |
| `IDEMPOTENT_DUPLICATE` | 409 | Reuso de `X-Op-Id` con payload incompatible. |
| `CONCURRENCY_ERROR` | 409 | `If-Match-Version` no coincide con `version_registro` vigente. |
| `TECHNICAL_INCONSISTENCY` | 409/500 | Duplicados activos, inconsistencias controladas o fallos técnicos. |

Formato estándar:

```json
{
  "ok": false,
  "error_code": "VALIDATION_ERROR",
  "error_message": "Mensaje legible",
  "details": {
    "header": "X-Op-Id",
    "reason": "missing"
  }
}
```

## 8. Alcance fuera de implementación vigente

No implementado/no confirmado en estos contratos:

- login, sesiones, tokens y autenticación real;
- passwords, credenciales, recuperación o rotación;
- OAuth/SSO;
- middleware de autorización real;
- cálculo de permisos efectivos;
- menú dinámico;
- alcance por sucursal;
- CRUD write de roles de seguridad;
- CRUD write de permisos;
- asignación write de permisos a roles por API;
- usuario como extensión de `persona`;
- rol de seguridad como `rol_participacion`.

## 9. Definition of Done documental para futuras issues

Toda issue o PR futuro del dominio Administrativo debe cumplir:

1. Si agrega o modifica endpoints, actualizar este DEV-API o justificar explícitamente por qué no aplica.
2. Si cambia reglas de negocio, actualizar `DEV-SRV`, catálogos (`RN-ADM`, `EVT-ADM`, `ERR-ADM`, `EST-ADM`) o `DECISIONES` según corresponda.
3. Todo PR debe indicar qué documentación se actualizó o justificar por qué no aplica.
4. Si agrega una operación sincronizable, documentar evento/outbox, aggregate, payload mínimo y frontera transaccional.
5. Si agrega write CORE-EF, documentar headers, versionado, idempotencia, baja lógica si aplica, rollback/transacción y tests mínimos.
6. No declarar cumplimiento CORE-EF profundo sin evidencia verificable en router/service/repository/SQL/tests.
7. Si se implementa un handler global para `RequestValidationError` o cambia el formato/status de validación automática, actualizar el DEV-API global y los documentos por dominio afectados.
8. No ampliar el alcance administrativo hacia autenticación, autorización real, sucursal o menú dinámico sin issue/documentación específica.

## 10. Referencias internas

- `SRV-ADM-001`: `backend/documentacion/DEV-SRV/dominios/administrativo/SRV-ADM-001-gestion-de-usuarios.md`.
- `SRV-ADM-002`: `backend/documentacion/DEV-SRV/dominios/administrativo/SRV-ADM-002-gestion-de-roles-y-permisos.md`.
- `EVT-ADM`: `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/EVT-ADM.md`.
- `RN-ADM`: `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/RN-ADM.md`.
- `CORE-EF`: `backend/documentacion/CORE-EF/CORE-EF-001-infraestructura-transversal.md` y documentos complementarios en `backend/documentacion/CORE-EF/`.
- Outbox: `backend/documentacion/DECISIONES/infraestructura/CORE-DEC-OUTBOX-001-transactional-outbox.md`.
- Issues/PRs relacionados: #249, #259, #260, #261, #292, #297, #298.

## 7. Alcance operativo administrativo por sucursal (#262)

### 7.1 Clasificación y ownership

- Concepto: `usuario_sucursal`.
- Clasificación: soporte administrativo-operativo para habilitación contextual básica de usuarios por sucursal.
- Dominio API: `administrativo`, porque el vínculo pertenece a administración/seguridad de usuarios.
- Relación con operativo: consume `sucursal` existente sin redefinirla ni crear asignación directa a instalación.
- Fuera de alcance: autorización efectiva por permiso, middleware de seguridad, login, menú dinámico, permisos complejos, `usuario_instalacion`, edición/baja del alcance y reglas por dominio.

### 7.2 `GET /api/v1/administrativo/usuarios/{id_usuario}/alcance-operativo`

Consulta read-like del alcance operativo consolidado de un usuario.

- CORE-EF: `QUERY_READLIKE`; no requiere headers write.
- Devuelve:
  - `usuario`;
  - `sucursales_asignadas` activas;
  - `sucursal_predeterminada` si existe;
  - flags consolidados `puede_operar`, `puede_consultar`, `puede_administrar`;
  - `estado_vigencia` (`ACTIVO` o `SIN_ALCANCE`).
- Excluye vínculos con `deleted_at`, `fecha_hasta` o `estado_vinculo` distinto de `ACTIVO`, y sucursales dadas de baja.
- Errores: `404 NOT_FOUND` si el usuario no existe; `500 TECHNICAL_INCONSISTENCY` ante falla técnica controlada.

### 7.3 `GET /api/v1/administrativo/usuarios/{id_usuario}/sucursales`

Lista read-like de sucursales asignadas a un usuario.

- CORE-EF: `QUERY_READLIKE`; no requiere headers write.
- Excluye vínculos dados de baja o no activos y sucursales dadas de baja.
- Errores: `404 NOT_FOUND` si el usuario no existe; `500 TECHNICAL_INCONSISTENCY` ante falla técnica controlada.

### 7.4 `POST /api/v1/administrativo/usuarios/{id_usuario}/sucursales`

Asigna alcance operativo básico de un usuario a una sucursal existente.

- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO` sincronizable.
- Headers obligatorios: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` mediante helper común CORE-EF.
- `If-Match-Version`: NO APLICA, porque crea un vínculo nuevo y no modifica entidad versionada existente.
- Payload: `id_sucursal`, `tipo_habilitacion_sucursal`, `es_sucursal_predeterminada`, `puede_operar`, `puede_consultar`, `puede_administrar`, `fecha_desde` (obligatoria), `fecha_hasta`, `observaciones`. Si falta `fecha_desde`, la validación automática devuelve `422`.
- Persistencia CORE-EF: `uid_global`, `version_registro = 1`, `created_at`, `updated_at`, `deleted_at = NULL`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Idempotencia: aplica por `op_id_alta` (`ux_usuario_sucursal_op_id_alta`). Mismo `X-Op-Id` + payload compatible devuelve el vínculo existente sin duplicar outbox; mismo `X-Op-Id` + payload distinto devuelve `409 IDEMPOTENT_DUPLICATE`.
- Duplicado activo: no permite dos vínculos activos para `(id_usuario, id_sucursal)`; devuelve `409 TECHNICAL_INCONSISTENCY`.
- Sucursal predeterminada: el POST es create-only y no desmarca automáticamente una predeterminada anterior. Si `es_sucursal_predeterminada = true` y ya existe otra predeterminada activa para el usuario, devuelve `409 TECHNICAL_INCONSISTENCY`. El cambio de predeterminada queda fuera de alcance de #262 y deberá nacer como endpoint versionado con `If-Match-Version` y outbox propio.
- Outbox: aplica; usa evento formal `usuario_asociado_a_sucursal` (`EVT-ADM-008`) en la misma transacción que el alta real. El replay idempotente compatible no duplica outbox.
- Lock lógico: NO APLICA en esta primera versión acotada; la consistencia se apoya en transacción e índices únicos parciales.
- Versionado: `usuario_sucursal.version_registro` nace en `1`; no se modifican vínculos existentes en este endpoint create-only.
- Rollback/transacción: la validación de duplicado/predeterminada activa, alta de vínculo y outbox comparten la misma transacción.
- Validaciones: usuario activo/no dado de baja, sucursal activa/no dada de baja, vigencia (`fecha_hasta >= fecha_desde`), no duplicado activo.
- Errores: `400 VALIDATION_ERROR` para headers CORE-EF o validaciones manuales, `404 NOT_FOUND`, `409 IDEMPOTENT_DUPLICATE`, `409 TECHNICAL_INCONSISTENCY`, `422` para validación automática FastAPI/Pydantic.

### 7.5 SQL asociado

`usuario_sucursal` se completa con bloque CORE-EF mediante `backend/database/patch_usuario_sucursal_core_ef_20260702.sql` y el dump principal actualizado. Se agregan índices únicos para `uid_global` e idempotencia por `op_id_alta`, y parciales para duplicado activo `(id_usuario, id_sucursal)` y predeterminada activa por usuario.

### 7.6 Relación con issues

- Closes #262.
- Refs #249.
- Refs #248.

## 8. Catálogos maestros e ítems read-only (#360)

### 8.1 Alcance implementado

Primera capa read-only de #264 para consultar `catalogo_maestro` e `item_catalogo`. No anticipa writes, migraciones SQL ni migración CORE-EF de comandos administrativos.

### 8.2 `GET /api/v1/administrativo/catalogos`

- Clasificación CORE-EF: `QUERY_READLIKE`.
- Headers write: `NO APLICA`.
- Query params:
  - `q`: búsqueda por `codigo_catalogo_maestro` o `nombre_catalogo_maestro`.
  - `page`: entero `>= 1`.
  - `page_size`: entero `>= 1` y `<= 200`.
- Orden determinista: `codigo_catalogo_maestro`, `id_catalogo_maestro`.
- Respuesta exitosa:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_catalogo_maestro": 1,
        "codigo_catalogo_maestro": "TIPO_DOCUMENTO",
        "nombre_catalogo_maestro": "Tipo de documento",
        "descripcion": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }
}
```

### 8.3 `GET /api/v1/administrativo/catalogos/{id_catalogo_maestro}`

- Clasificación CORE-EF: `QUERY_READLIKE`.
- Headers write: `NO APLICA`.
- `404 NOT_FOUND` si el catálogo no existe.
- Respuesta exitosa: `CatalogoMaestroDetailResponse` con `id_catalogo_maestro`, `codigo_catalogo_maestro`, `nombre_catalogo_maestro` y `descripcion`.

### 8.4 `GET /api/v1/administrativo/catalogos/{id_catalogo_maestro}/items`

- Clasificación CORE-EF: `QUERY_READLIKE`.
- Headers write: `NO APLICA`.
- Query params:
  - `q`: búsqueda por `codigo_item_catalogo` o `nombre_item_catalogo`.
  - `estado_item_catalogo`: filtro literal sobre el valor persistido; no es enum cerrado.
  - `page`: entero `>= 1`.
  - `page_size`: entero `>= 1` y `<= 200`.
- Orden determinista: `codigo_item_catalogo`, `id_item_catalogo`.
- La consulta queda acotada al `id_catalogo_maestro` del path y no mezcla ítems de otros catálogos.
- `404 NOT_FOUND` si el catálogo no existe.
- `NULL` en `estado_item_catalogo` se preserva como `null`.

### 8.5 Schemas agregados

- `CatalogoMaestroData`.
- `CatalogoMaestroListData`.
- `CatalogoMaestroListResponse`.
- `CatalogoMaestroDetailResponse`.
- `ItemCatalogoData`.
- `ItemCatalogoListData`.
- `ItemCatalogoListResponse`.

### 8.6 Decisión CORE-EF

- Clasificación: `QUERY_READLIKE`.
- Headers: `NO APLICA`.
- `If-Match-Version`: `NO APLICA`.
- Idempotencia: `NO APLICA`.
- Outbox: `NO APLICA`.
- Lock lógico: `NO APLICA`.
- Versionado: `NO APLICA`.
- Transacción/Rollback: `NO APLICA`.
- Efectos persistentes: ninguno.

### 8.7 Pendiente / fuera de alcance

- Alta, modificación, baja, activación o desactivación de catálogos e ítems.
- Migraciones SQL.
- Jerarquías e historial.
- Defaults, orden configurable, vigencias, configuración por sucursal o instalación.
- Migración de enums existentes.
- Estados formales de `estado_item_catalogo`: `NO CONFIRMADOS`.
- Semántica del estado nulo: `NO CONFIRMADA`.


## Incremento #363 — Estructura SQL CORE-EF de catálogos

- `catalogo_maestro` e `item_catalogo` quedan preparados para futuros comandos sincronizables con `uid_global`, versionado físico, timestamps, baja lógica, metadata de instalación y `op_id`.
- Los triggers genéricos CORE-EF aplican defaults de alta, preservan metadata original y aumentan `version_registro` ante modificaciones materiales, incluida la baja lógica.
- La lectura read-only implementada en #360 excluye explícitamente filas con `deleted_at IS NOT NULL`; no hay cambios de rutas, schemas ni contratos de respuesta.
- La unicidad de códigos se conserva para todas las filas, incluidas las bajas lógicas: no hay evidencia que autorice reutilización ni reactivación de códigos históricos.
- No se agregó `CHECK` para `estado_item_catalogo`: los valores definitivos y la semántica de `NULL` permanecen **NO CONFIRMADOS**. No se agrega estado físico a `catalogo_maestro` por falta de evidencia física vigente.
- No se crearon tablas `_legacy`, tablas espejo, lectura dual ni compatibilidad transitoria. Los datos existentes de las tablas y dependencias inmediatas son descartables y el patch los limpia de manera controlada; queda una única estructura definitiva.
- No hay endpoints write ni outbox runtime en este incremento. El CRUD futuro deberá persistir el cambio de negocio y su evento outbox en la misma transacción. Jerarquías, historial, defaults, vigencias y UI permanecen fuera de alcance.

### Decisión CORE-EF

- Endpoints / clasificación HTTP / headers / `If-Match-Version` / idempotencia HTTP / outbox runtime / lock lógico: **NO APLICA**; el incremento es únicamente SQL/infrastructural.
- Versionado físico y triggers: aplica y queda implementado en ambas tablas.
- Transacción y rollback: el patch usa una transacción; ante error revierte. La reversión posterior requiere restaurar backup previo porque la limpieza de datos es deliberada.

## 11. Catálogos maestros — comandos write (#368)

`catalogo_maestro` es núcleo del dominio Administrativo; headers CORE-EF, versionado y outbox son soporte transversal. La instalación usada para metadata no traslada ownership de `instalacion` desde Operativo.

### 11.1 `POST /api/v1/administrativo/catalogos`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Headers obligatorios: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
- `If-Match-Version`: **NO APLICA** (alta).
- Idempotencia: por `op_id_alta`; mismo `X-Op-Id` y payload devuelve el recurso creado sin un segundo evento. Payload incompatible devuelve `409 IDEMPOTENT_DUPLICATE`.
- Versionado: versión inicial `1` y `deleted_at = null`.
- Outbox: `catalogo_maestro_creado`, aggregate `catalogo_maestro`, en la misma transacción que el insert.

Request:
```json
{"codigo_catalogo_maestro":"TIPO_DOCUMENTO","nombre_catalogo_maestro":"Tipos de documento","descripcion":"Valores admitidos para documentos"}
```

### 11.2 `PUT /api/v1/administrativo/catalogos/{id_catalogo_maestro}`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Headers obligatorios: los cuatro headers CORE-EF y `If-Match-Version`.
- Payload: los mismos tres campos del alta; actualiza código, nombre y descripción.
- Optimistic locking: update condicional por id, `deleted_at IS NULL` y versión. Mismatch real devuelve `409 CONCURRENCY_ERROR` sin outbox.
- Replay: `op_id_ultima_modificacion` con payload resultante idéntico devuelve la respuesta previa sin incrementar versión ni emitir otro evento.
- Outbox: `catalogo_maestro_modificado` dentro de la transacción.

### 11.3 `PATCH /api/v1/administrativo/catalogos/{id_catalogo_maestro}/baja`

- Estado: implementado.
- Clasificación CORE-EF: `COMMAND_WRITE_NEGOCIO`.
- Headers obligatorios: los cuatro headers CORE-EF y `If-Match-Version`.
- Baja lógica: establece `deleted_at`, incrementa una vez `version_registro` y actualiza metadata de última modificación. Conserva físicamente la fila y su código único.
- Replay: el mismo `X-Op-Id` de una baja ya aplicada devuelve el resultado persistido; otro `X-Op-Id` sobre el catálogo dado de baja devuelve `404 NOT_FOUND`.
- Outbox: `catalogo_maestro_desactivado` dentro de la misma transacción.

### Errores y transacción

Los headers faltantes o inválidos devuelven `400 VALIDATION_ERROR` en el envelope administrativo. Catálogo inexistente o dado de baja no operable devuelve `404 NOT_FOUND`; código duplicado devuelve `409 DUPLICATE_CODE`; conflicto de versión devuelve `409 CONCURRENCY_ERROR`. Cada repository confirma el cambio de negocio y el evento outbox con un único `commit`; ante fallo de outbox o constraint hace rollback y no deja efectos parciales.

Fuera de alcance: writes de `item_catalogo`, reactivación, jerarquías, historial, defaults, vigencias, migración incidental de enums y UI. La política futura de reactivación, reutilización de código, estado persistido de catálogo, jerarquías e historial queda **NO CONFIRMADA**.

### Corrección #370 — idempotencia concurrente y conflicto de código

La alta conserva la consulta previa por `op_id_alta` como optimización y además resuelve la carrera de inserción por la constraint `ux_catalogo_maestro_op_id_alta`: luego de `rollback`, recupera y compara la fila persistida. El mismo payload devuelve el replay sin una nueva fila, versión ni evento; un payload incompatible devuelve `409 IDEMPOTENT_DUPLICATE`. Si la fila no aparece tras el rollback, se propaga la inconsistencia técnica real.

La constraint `uq_catalogo_maestro_codigo` se traduce en el conflicto funcional `409 DUPLICATE_CODE` en alta y modificación. No se exponen nombres de constraints ni mensajes SQL. Las colisiones de constraint y los fallos de outbox hacen rollback antes de devolver la respuesta; por ello no dejan catálogo ni outbox parcial.

## Incremento #393 — Ciclo de vida de ítems de catálogo

### Auditoría y decisión

La auditoría confirma `ACTIVO` como estado inicial por `EST-ADM-001` y por la suite read-only que ya usa ese valor. `EST-ADM-002` y `ERR-ADM-048` confirman la existencia y semántica de `INACTIVO`. El modelo SQL anterior era nullable y no tenía `CHECK`; esa ausencia no contradice la formalización actual porque los datos de esta etapa son descartables.

El patch `patch_item_catalogo_estado_20260724.sql` adopta la estrategia A: normaliza `NULL` a `ACTIVO`, elimina filas con valores distintos de `ACTIVO`/`INACTIVO` junto con sus relaciones jerárquicas, y deja `DEFAULT 'ACTIVO'`, `NOT NULL` y `chk_item_catalogo_estado`. No crea tablas `_legacy`, espejos ni lectura dual.

| Estado físico | `deleted_at` | Significado | Transiciones permitidas |
| --- | --- | --- | --- |
| `ACTIVO` | `NULL` | Ítem disponible administrativamente para ser ofrecido a dominios consumidores. | A `INACTIVO` o a baja lógica. |
| `INACTIVO` | `NULL` | Ítem existente y visible administrativamente, no disponible para nuevas selecciones. El dominio consumidor conserva la decisión de aceptación. | A `ACTIVO` o a baja lógica. |
| Baja lógica | no `NULL` | Fila conservada, fuera de consultas normales. No es un tercer valor de `estado_item_catalogo`. | Sin reactivación en este incremento. |

La reactivación futura sólo significa `INACTIVO -> ACTIVO` con `deleted_at IS NULL`; no hay endpoint ni flujo write implementado. La baja lógica se representa exclusivamente con `deleted_at IS NOT NULL`; la eliminación física queda fuera de alcance. La constraint `uq_item_catalogo` conserva el código dentro del catálogo también después de baja, por lo que no se reutiliza.

### Contrato read-only preservado

`GET /api/v1/administrativo/catalogos/{id_catalogo_maestro}/items` sigue siendo `QUERY_READLIKE`: no requiere headers write ni produce efectos persistentes. Sin filtro devuelve ítems `ACTIVO` e `INACTIVO` no dados de baja; con filtro literal devuelve el estado físico solicitado; un valor no válido produce una lista vacía, sin convertir el query param en enum contractual. Las filas con `deleted_at IS NOT NULL` siempre quedan excluidas. `NULL` deja de ser un valor persistible y no se expone para ítems creados tras el patch.

### CORE-EF y alcance

No se agregan endpoints: clasificación HTTP, headers, `If-Match-Version`, idempotencia HTTP, outbox runtime y lock lógico son **NO APLICA**. Se preservan versionado físico y triggers; el patch SQL es transaccional y sus efectos persistentes son normalización/limpieza estructural controlada. Quedan fuera de alcance el CRUD write de `item_catalogo`, jerarquías, historial funcional, defaults por catálogo, vigencias, configuración contextual y UI.

### NO CONFIRMADO

No se confirma ninguna regla de negocio particular de los dominios consumidores ni una reactivación de bajas lógicas. Tampoco se implementa ni confirma la operativa futura de jerarquía o historial.

## Incremento #399 — CRUD write de ítems de catálogo

Se implementan `POST /api/v1/administrativo/catalogos/{id_catalogo_maestro}/items`, `PUT /api/v1/administrativo/catalogos/{id_catalogo_maestro}/items/{id_item_catalogo}`, `PATCH .../estado` y `PATCH .../baja`. Todos son `COMMAND_WRITE_NEGOCIO` y exigen `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id` y `X-Instalacion-Id`; los tres comandos sobre una fila existente además exigen `If-Match-Version`. Alta recibe código, nombre y descripción opcional, fija `ACTIVO`; update modifica esos tres valores; estado acepta exclusivamente `ACTIVO` o `INACTIVO`; baja fija `deleted_at`.

Los comandos son idempotentes: alta usa `op_id_alta` y los restantes `op_id_ultima_modificacion`; replay compatible no cambia versión ni duplica outbox, y payload/op incompatibles retornan `409 IDEMPOTENT_DUPLICATE`. El control de concurrencia retorna `409 CONCURRENCY_ERROR`; código duplicado dentro del catálogo retorna `409 DUPLICATE_CODE`. Cada cambio y su evento (`item_catalogo_creado`, `item_catalogo_modificado`, `item_catalogo_estado_cambiado`, `item_catalogo_desactivado`) se confirma en la misma transacción. El mismo estado con una operación nueva es `409 INVALID_STATE_TRANSITION`; no es cambio material. Jerarquías, historial y reactivación de bajas quedan fuera de alcance.

## Incremento #407 — Inventario read-only de definiciones de parámetros

### `GET /api/v1/administrativo/configuracion/parametros`

- Clasificación CORE-EF: `QUERY_READLIKE`.
- Devuelve el listado completo, sin paginación, búsqueda ni filtros.
- Orden estable: `codigo_parametro`, con `id_parametro_sistema` como desempate.
- Headers write, `If-Match-Version`, idempotencia, outbox, lock lógico,
  versionado y rollback de negocio: **NO APLICA**, porque es una consulta pura.
- `200` admite `items: []` y `total: 0`.
- Ante una falla técnica devuelve `500 TECHNICAL_INCONSISTENCY` con
  `details: {}` y sin información interna.

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_parametro_sistema": 1,
        "codigo_parametro": "EJEMPLO",
        "nombre_parametro": "Ejemplo",
        "descripcion": null,
        "tipo": {
          "id_tipo_dato_parametro": 1,
          "codigo_tipo_dato": "TEXTO",
          "nombre_tipo_dato": "Texto"
        },
        "alcance": {
          "id_alcance_parametro": 1,
          "codigo_alcance": "GLOBAL",
          "nombre_alcance": "Global"
        }
      }
    ],
    "total": 1
  }
}
```

La respuesta expone exclusivamente columnas reales de `parametro_sistema`,
`tipo_dato_parametro` y `alcance_parametro`. Quedan fuera de alcance valores,
defaults, overrides, secretos, resolución por sucursal o instalación,
`configuracion_general`, writes, autorización nueva y configuración local operativa.

### Corrección PR #400 — contratos de transición, baja y errores técnicos

Con un `X-Op-Id` nuevo, solicitar el estado físico ya vigente no es una colisión idempotente: responde `409 INVALID_STATE_TRANSITION` con el mensaje de que el destino ya es el estado actual. El replay que reutiliza el `X-Op-Id` de la transición anterior y el mismo estado sí devuelve la representación persistida, sin incrementar versión ni crear otro evento.

Para baja lógica, el repository primero verifica pertenencia, existencia física y `deleted_at`: la repetición con el mismo `X-Op-Id` devuelve replay; con otro identificador devuelve `404 NOT_FOUND`. Las respuestas `500 TECHNICAL_INCONSISTENCY` se sanitizan y no incluyen SQL, constraints, parámetros ni mensajes de driver. La recuperación posterior a una colisión de `ux_item_catalogo_op_id_alta` propaga la excepción técnica original si la fila no puede recuperarse tras rollback.

## Incremento #408 — Sin cambios de API

#408 congela arquitectura y **no agrega ni modifica endpoints**. El GET de #407 continúa exponiendo únicamente definiciones; no devuelve `valor_parametro`, no ejecuta resolución contextual y no constituye el read de #425.

CORE-EF para endpoints: **NO APLICA**, porque este incremento es exclusivamente documental. Los futuros read/write, envelopes, autorización, manejo de secretos, versionado, idempotencia, outbox, historial y rollback de #425 permanecen pendientes; no se declara aquí ningún contrato runtime.

## Incremento #409 — Sin cambios de API

#409 incorpora únicamente datos estructurales SQL (`ENTERO` y `GLOBAL`). No
agrega endpoints ni vuelve editables esos datos. El GET de #407 conserva su
contrato y puede exponer los códigos al inventariar una definición que los
referencie; las nuevas descripciones estructurales no se agregan a su response.
#409 no crea definiciones ni valores funcionales y no implementa #425.

## Incremento #410 — Sin API nueva

#410 es exclusivamente preparación SQL CORE-EF de `valor_parametro`. No agrega ni modifica endpoints, schemas, headers, errores o contratos runtime. El GET de definiciones de #407 permanece sin cambios y no lee valores. El read de valores #411, los commands #412 y las claves/valores/runtime de #425 continúan no implementados; tampoco existen resolución de overrides, precedencia o fallback, outbox ni historial para este incremento.

## Incremento #438 — Sin endpoint nuevo

#438 es preparación SQL y contractual de exposición segura en `parametro_sistema`; no agrega ni modifica rutas, schemas, repositories runtime, services, comandos, headers, errores runtime u outbox. El GET de #407 (`GET /api/v1/administrativo/configuracion/parametros`) conserva su contrato: lista sólo definición, tipo y alcance, y no expone `exponible_api_administrativa`, `es_sensible`, valores ni política interna de seguridad.

Para el futuro #411, un valor administrativo sólo podrá devolverse si la definición cumple `exponible_api_administrativa = true AND es_sensible = false`. Si la definición no existe o no cumple esa condición, el contrato recomendado es `404 Not Found`, usando el error estándar de parámetro no encontrado si el catálogo real lo permite, para no revelar por enumeración la existencia de definiciones sensibles o no exponibles.

#438/#441 no implementan autenticación ni autorización. Los headers CORE-EF de write no equivalen a autorización; el endpoint administrativo de #411 no debe tratarse como público y deberá incorporar una dependencia de autorización cuando exista infraestructura real. #441 agrega sólo metadata física `editable_administrativamente` default-deny, independiente de exposición y sensibilidad; no agrega endpoint write y #412 sigue pendiente por autorización, idempotencia/replay, outbox e historial. Futuros reads no deben registrar valores, secretos, op IDs, credenciales, payload SQL ni contenido sensible.

## Incremento #441 — Sin endpoint write ni exposición de editabilidad

#441 es preparación SQL y contractual: agrega `editable_administrativamente boolean NOT NULL DEFAULT false` a `parametro_sistema` sin modificar rutas, schemas, repositories runtime, services, comandos, headers, errores runtime u outbox. El inventario #407 y el valor GLOBAL #411 no exponen la nueva metadata ni cambian su política de lectura.

La editabilidad administrativa es independiente de `exponible_api_administrativa` y `es_sensible`; no se infiere por código, tipo, alcance, existencia de valor, exposición o sensibilidad. Ninguna definición queda editable automáticamente. Cualquier habilitación futura debe realizarse por migración versionada explícita y #412 continúa no implementado.

## Incremento #411 — Valor GLOBAL marcado vigente de un parámetro

### `GET /api/v1/administrativo/configuracion/parametros/{codigo_parametro}/valor-global`

Ruta administrativa no pública, `QUERY_READLIKE`, sin headers write CORE-EF y sin `If-Match-Version`. Puede devolver `Cache-Control: no-store`. El selector de `codigo_parametro` es exacto y case-sensitive.

#### Respuesta `200 OK`

Usa el envelope estándar:

```json
{
  "ok": true,
  "data": {
    "definicion": {
      "id_parametro_sistema": 123,
      "codigo_parametro": "CODIGO_EXACTO",
      "nombre_parametro": "Nombre",
      "descripcion": "Descripción",
      "tipo": {
        "id_tipo_dato_parametro": 1,
        "codigo_tipo_dato": "ENTERO",
        "nombre_tipo_dato": "Entero",
        "descripcion_tipo_dato": "Valor numérico entero sin componente decimal."
      },
      "alcance": {
        "id_alcance_parametro": 1,
        "codigo_alcance": "GLOBAL",
        "nombre_alcance": "Global",
        "descripcion_alcance": "Aplicable sin contexto de sucursal o instalación."
      }
    },
    "estado_valor": "CON_VALOR_MARCADO_VIGENTE",
    "valor_marcado_vigente": {
      "id_valor_parametro": 456,
      "uid_global": "00000000-0000-0000-0000-000000000000",
      "valor_raw": "15",
      "valor_tipado": 15,
      "version_registro": 3,
      "es_valor_vigente": true,
      "fecha_desde": null,
      "fecha_hasta": null,
      "created_at": "2026-08-05T12:00:00",
      "updated_at": "2026-08-05T12:00:00"
    }
  }
}
```

Si la definición es exponible, no sensible y `GLOBAL`, pero no existe valor global marcado vigente no eliminado, `estado_valor` es `SIN_VALOR` y `valor_marcado_vigente` es `null`.

#### Errores

- `404 parametro_no_encontrado`: definición inexistente, no exponible o sensible; las tres respuestas son indistinguibles.
- `409 conflicto_parametro`: definición existente, exponible y no sensible con alcance distinto de `GLOBAL`.
- `500 inconsistencia_parametro`: `ENTERO` persistido inválido, tipo no soportado aun sin valor, cardinalidad mayor que uno o estructura inconsistente de tipo/alcance, siempre con mensaje sanitizado.
- `500 TECHNICAL_INCONSISTENCY`: error SQL/driver inesperado sanitizado.

No expone `deleted_at`, contexto, op IDs, `exponible_api_administrativa`, `es_sensible`, `editable_administrativamente`, historial, outbox, SQL, constraints ni detalles de driver. No implementa autorización completa, writes #412, calendario #425 ni contexto #435.

## Incremento #412 — contrato final del update GLOBAL (no implementado)

`PATCH /api/v1/administrativo/configuracion/parametros/{codigo_parametro}/valor-global`
queda congelado como `COMMAND_WRITE_NEGOCIO`, update-only de un único
`valor_parametro` GLOBAL vigente existente. No es `PUT`, creación ni UPSERT.

Requiere Bearer y `require_administrative_permission(
"ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR")`. La identidad humana procede sólo de
`get_authenticated_principal` y `AuthenticatedPrincipal.id_usuario`.
`X-Usuario-Id` no se requiere, parsea, compara ni usa; si llega de un cliente
heredado se ignora para identidad y autorización. Un helper CORE-EF autenticado
reusable, no parsing manual del router, leerá sólo `X-Op-Id`, `X-Sucursal-Id`,
`X-Instalacion-Id` e `If-Match-Version`, todos obligatorios.

El selector `codigo_parametro` usa igualdad exacta y case-sensitive, sin trim,
normalización, aliases ni fallback. La definición debe ser exponible, no sensible,
editable administrativamente, `ENTERO` y `GLOBAL`. El target debe ser exactamente
un valor con contexto nulo, vigente, no eliminado y `version_registro >= 1`. Su
ausencia es `409 conflicto_parametro`: nunca crea un valor.

El body exacto es `{"valor_tipado": 15}`: schema `BaseModel` con `extra="forbid"`
y `valor_tipado: StrictInt`. Rechaza boolean, string, float, null, ausencia y extras;
persiste `str(valor_tipado)` como decimal ASCII, sin rango funcional adicional.

La respuesta `200` exacta, también almacenada sin cambios como
`response_snapshot`, es:

```json
{
  "ok": true,
  "data": {
    "codigo_parametro": "CODIGO_EXACTO",
    "uid_global": "00000000-0000-0000-0000-000000000000",
    "valor_tipado": 15,
    "version_registro": 4,
    "updated_at": "2026-08-12T12:00:00Z"
  }
}
```

No incluye IDs internos, usuario, sucursal, instalación, `op_id`, metadata de
seguridad ni `valor_raw`. `REPLAY` devuelve ese snapshot original sin SELECT
funcional para reconstruirlo, CAS, UPDATE, versión, outbox o receipt nuevos.

El CAS es un único `UPDATE ... WHERE version_registro = :if_match_version ...
RETURNING`. Un `op_id` nuevo con versión vieja devuelve `412 CONCURRENCY_ERROR`;
un replay compatible se resuelve antes de revalidar la versión actual.

La idempotencia consume el runtime de #470 con `command_code =
ADMIN.CONFIG.PARAMETRO.VALOR_GLOBAL.UPDATE`, target exacto
`("VALOR_PARAMETRO", valor_parametro.uid_global, codigo_parametro)` y hash RFC 8785
v1 de `{"codigo_parametro": codigo_parametro, "valor_tipado": valor_tipado,
"if_match_version": if_match_version}`. No incorpora identidad, contexto, bearer,
`op_id`, timestamps ni resultado. Los conflictos `COMMAND`, `TARGET` y `PAYLOAD`
son, respectivamente, `409 IDEMPOTENCY_COMMAND_CONFLICT`,
`409 IDEMPOTENCY_TARGET_CONFLICT` y `409 IDEMPOTENCY_PAYLOAD_CONFLICT`.

Errores adicionales: `401 INVALID_SESSION`; `403 autorizacion_insuficiente`; `404
parametro_no_encontrado` indistinguible para inexistente/no exponible/sensible;
`409 conflicto_parametro` para no editable, tipo/alcance fuera de scope, ausencia
update-only o valor no operable; y los errores `500` sanitizados definidos en
ERR-ADM. La validación estructural de FastAPI puede ocurrir antes o durante las
dependencies; no se promete una precedencia pública más fuerte sin tests.

## 12. Credenciales y autenticación — estado posterior a #448

#448 no agrega ni modifica endpoints. No existe endpoint administrativo implementado para crear credenciales, setear passwords, login, logout, refresh, sesiones nuevas, recuperación, rotación ni validación de hashes. Por lo tanto, no se documenta request/response de credenciales como API vigente.

La tabla `credencial_usuario` existe sólo como contrato SQL inicial: `PASSWORD`, estados `ACTIVA`/`REVOCADA`, hash sensible y metadata CORE-EF física. `hash_credencial` no debe exponerse por API ni aparecer en errores. Usuarios sin credencial no autentican porque no hay runtime de autenticación implementado. #449, #450 y #446 siguen pendientes.

Decisión CORE-EF API: **NO APLICA** para headers write, `If-Match-Version`, idempotencia HTTP, outbox y lock lógico, porque #448 no crea endpoints.

## 10. Incremento #449 — Sin contrato HTTP nuevo

#449 agrega sólo primitivas internas Argon2id para credenciales futuras. No se agrega ni modifica ningún endpoint administrativo; por lo tanto no existe autenticación, login, logout, sesiones, tokens, principal autenticado ni endpoints de credenciales en este incremento.

CORE-EF para endpoints: `NO APLICA`, porque no hay rutas nuevas ni modificadas. Los futuros consumidores deberán persistir `hash_credencial` como PHC Argon2id y `algoritmo_hash` como `argon2id:v1`, pero esa persistencia no forma parte de #449. #450 y #446 continúan pendientes.
# Seguridad administrativa implementada por #446

- `POST /api/v1/administrativo/seguridad/login`: recibe exclusivamente `login` y
  `password`; devuelve un bearer opaco, `expires_at` y UID público de sesión con
  `Cache-Control: no-store`.
- `POST /api/v1/administrativo/seguridad/logout`: recibe exactamente
  `Authorization: Bearer <token>` y responde 204 de forma idempotente, incluso
  para tokens bien formados desconocidos o sesiones ya finalizadas.
- Login inválido es siempre `INVALID_CREDENTIALS`; fallos de instalación se
  publican como `AUTHENTICATION_UNAVAILABLE`. No existe `/seguridad/me`, principal,
  roles, permisos, scopes, refresh ni autorización en #446.

# Seguridad administrativa implementada por #447

## `GET /api/v1/administrativo/seguridad/me`

Clasificación CORE-EF: `QUERY_READLIKE`. Requiere únicamente `Authorization: Bearer <access_token>` y devuelve `ok` más los campos exactos `id_usuario`, `codigo_usuario`, `login`, `id_sesion` (UUID público), `mecanismo_autenticacion = SESION_SERVIDOR`, `autenticado_en`, `id_instalacion_origen_sesion` e `id_sucursal_operativa` nullable. Éxitos y errores usan `Cache-Control: no-store`.

No exige `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` ni `If-Match-Version`. `Authorization` identifica a la persona; los demás headers representan operación, contexto o concurrencia y no autentican. `X-Usuario-Id` queda deprecado como identidad HTTP y su migración corresponde a #461.

Una ausencia o invalidez de bearer, sesión o usuario devuelve el mismo `401 INVALID_SESSION`; una falla de persistencia devuelve `500 SESSION_TECHNICAL_ERROR`, ambos sin detalle interno. La query es read-only, sin locks, actividad, outbox o sync. No hay roles, permisos, scopes ni autorización (#443 pendiente). No hubo cambio SQL.

La afirmación histórica de la introducción de que Administrativo no implementaba login queda superada por #446 y esta sección; se conserva únicamente como registro del corte anterior.

# Infraestructura de autorización administrativa #443

#443 no agrega ni protege endpoints productivos. Provee
`require_administrative_permission(permission_code)` para que rutas posteriores
reutilicen `BearerAuth` y el principal canónico de #447. Una ruta consumidora debe
documentar 401/403/500 con `ErrorResponse`; no debe declarar `Authorization` como
header raw ni usar OAuth scopes.

Principal válido sin concesión devuelve `403 autorizacion_insuficiente` y el mensaje
"La autorización efectiva es insuficiente para ejecutar la operación.". Permiso
contractual inexistente o inconsistencia devuelve `500 inconsistencia_roles_permisos`
y "No fue posible resolver la autorización administrativa.". Ambos incluyen details
vacío y `Cache-Control: no-store`, sin código de permiso ni información interna. El
401 `INVALID_SESSION` permanece a cargo de #447. Clasificación CORE-EF:
`QUERY_READLIKE`; no aplican headers write, idempotencia, outbox, locks, versionado o
sync. #461 (migración), #412 (primer command) y #435 (contexto) siguen pendientes.
