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
