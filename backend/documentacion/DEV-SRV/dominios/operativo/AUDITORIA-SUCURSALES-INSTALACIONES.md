# Auditoría de sucursales e instalaciones

## Resumen ejecutivo

Esta auditoría prepara el tramo administrativo/operativo posterior a usuarios, roles, permisos y asignaciones. La evidencia del repositorio muestra que `sucursal` e `instalacion` ya existen en el SQL base y están tratadas por CORE-EF como entidades sincronizables, versionadas y con metadata de instalación. También existe `usuario_sucursal`, `usuario_rol_sucursal` e `inmueble_sucursal`; no se encontró `usuario_instalacion`.

Decisión recomendada: mantener `sucursal` como entidad operativa/organizacional y `instalacion` como entidad técnica de sincronización con ownership operativo. La administración funcional de ambas debería exponerse bajo `/api/v1/operativo` cuando se implementen endpoints propios, porque `SRV-OPE-002` ya ubica `instalacion` en operativo y `DEV-API-INM-001` confirma que `instalacion` no pertenece al núcleo inmobiliario. El dominio administrativo puede consumir o administrar permisos/contextos sobre estas entidades, pero no debería convertirse en dueño semántico de `sucursal` ni `instalacion`.

No se modificó código de aplicación ni tests. Esta nota no implementa endpoints; solo documenta el estado verificado y propone el roadmap incremental.

## Fuentes auditadas

### Arquitectura y reglas de dominio

- `AGENTS.md` del repositorio.
- `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/analitico/DEV-ARCH-ANA-001.md`.

### DEV-SRV / DEV-API / decisiones / CORE-EF

- `backend/documentacion/DEV-SRV/dominios/operativo/SRV-OPE-001-gestion-de-sucursales.md`.
- `backend/documentacion/DEV-SRV/dominios/operativo/SRV-OPE-002-gestion-de-instalaciones.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/`.
- `backend/documentacion/DEV-API/dominios/administrativo/DEV-API-ADM-001.md`.
- `backend/documentacion/DEV-API/dominios/inmobiliario/DEV-API-INM-001.md`.
- `backend/documentacion/CORE-EF/CORE-EF-001-infraestructura-transversal.md`.
- `backend/documentacion/CORE-EF/CORE-EF-VALIDACION.md`.
- `backend/documentacion/CORE-EF/MATRIZ-CUMPLIMIENTO-ENDPOINTS-WRITE.md`.
- `backend/documentacion/DECISIONES/`.

### SQL, backend y tests

- `backend/database/schema_inmobiliaria_20260418.sql`.
- `backend/database/seed_test_baseline.sql`.
- Patches SQL con columnas `id_instalacion_origen` e `id_instalacion_ultima_modificacion`.
- `backend/app/main.py`.
- `backend/app/api/routers/administrativo_router.py`.
- Routers existentes bajo `backend/app/api/routers/`.
- Schemas y repositories administrativos existentes.
- Tests existentes bajo `backend/tests/` y `frontend/flet_app/tests/`.

## Estado actual del modelo SQL

### Tablas existentes directamente relacionadas

| Tabla | Estado | Clasificación | Observaciones |
| --- | --- | --- | --- |
| `sucursal` | Existe | Núcleo operativo/organizacional | Base para alcance operativo, contexto CORE-EF y futuras reglas por sucursal. |
| `instalacion` | Existe | Núcleo operativo técnico / sincronización | Unidad técnica real vinculada a una sucursal. |
| `inmueble_sucursal` | Existe | Soporte operativo-inmobiliario | Vincula inmueble con sucursal con vigencia. No convierte sucursal en entidad inmobiliaria. |
| `usuario_sucursal` | Existe | Soporte administrativo-operativo | Habilitación contextual de usuario por sucursal. |
| `usuario_instalacion` | No existe | No implementado | No se encontró tabla en el schema base. |
| `usuario_rol_sucursal` | Existe | Soporte de seguridad contextual | Asigna rol de seguridad a usuario con alcance de sucursal. |
| `sincronizacion_paquete` | Existe | Soporte técnico de sincronización | Paquetes originados en instalación. |
| `sincronizacion_recepcion` | Existe | Soporte técnico de sincronización | Recepción por instalación receptora. |
| `sincronizacion_operacion` | Existe | Soporte técnico de sincronización | Operaciones incluidas en paquetes. |
| `conflicto_sincronizacion` | Existe | Soporte técnico de sincronización | Registra conflictos por `op_id`, entidad y versión. |
| `outbox_event` | Existe | Soporte técnico/eventual | Outbox transaccional para eventos. |
| `lock_logico` | Existe | Soporte CORE-EF | Lock por entidad con instalación origen. |

### `sucursal`

Columnas relevantes:

- Identidad y metadata CORE-EF: `id_sucursal`, `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Datos propios: `codigo_sucursal`, `nombre_sucursal`, `descripcion_sucursal`, `estado_sucursal`, `es_casa_central`, `permite_operacion`, `fecha_alta`, `fecha_baja`, `observaciones`.
- Check: `chk_sucursal_deleted_at`.
- PK: `sucursal_pkey` sobre `id_sucursal`.
- Unicidad: `uq_sucursal_codigo`, `uq_sucursal_uid_global`.
- Índices: `idx_sucursal_estado`, `idx_sucursal_uid_global`.

Relaciones entrantes verificadas:

- `instalacion.id_sucursal` → `sucursal.id_sucursal`.
- `inmueble_sucursal.id_sucursal` → `sucursal.id_sucursal`.
- `usuario_sucursal.id_sucursal` → `sucursal.id_sucursal`.
- `usuario_rol_sucursal.id_sucursal` → `sucursal.id_sucursal`.
- `evento_auditoria.id_sucursal`, `historial_acceso.id_sucursal_contexto`, `sesion_usuario.id_sucursal_operativa`, `numerador_serie.id_sucursal`, `valor_parametro.id_sucursal`, `cuenta_financiera.id_sucursal_operativa` y `movimiento_tesoreria.id_sucursal_operativa` referencian sucursal.

### `instalacion`

Columnas relevantes:

- Identidad y metadata CORE-EF: `id_instalacion`, `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Relación operativa: `id_sucursal` obligatorio.
- Datos propios: `codigo_instalacion`, `nombre_instalacion`, `descripcion_instalacion`, `estado_instalacion`, `es_principal`, `permite_sincronizacion`, `identificador_tecnico`, `direccion_local`, `fecha_alta`, `fecha_baja`, `observaciones`.
- Check: `chk_instalacion_deleted_at`.
- PK: `instalacion_pkey` sobre `id_instalacion`.
- Unicidad: `uq_instalacion_codigo`, `uq_instalacion_uid_global`.
- Índices: `idx_instalacion_estado`, `idx_instalacion_sucursal`, `idx_instalacion_sucursal_estado`, `idx_instalacion_uid_global`.

Relaciones:

- FK `fk_instalacion_sucursal`: `instalacion.id_sucursal` → `sucursal.id_sucursal`.
- FKs entrantes desde `documento_logico`, `historial_acceso`, `lock_logico`, `sesion_usuario`, `sincronizacion_paquete`, `sincronizacion_recepcion` y `valor_parametro`.

### `inmueble_sucursal`

Columnas relevantes:

- `id_inmueble_sucursal`, `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- `id_inmueble`, `id_sucursal`, `fecha_desde`, `fecha_hasta`, `observaciones`.
- Check: `chk_inmueble_sucursal_vigencia`.
- PK: `inmueble_sucursal_pkey`.
- Unicidad: `uq_inmueble_sucursal_uid_global`.
- Índices: `idx_inmueble_sucursal_inmueble`, `idx_inmueble_sucursal_sucursal`, `idx_inmueble_sucursal_uid_global`, `ix_inmueble_sucursal_vigencia`.
- FKs: `fk_inmueble_sucursal_inmueble`, `fk_inmueble_sucursal_sucursal`.

### `usuario_sucursal`

Columnas relevantes:

- `id_usuario_sucursal`, `id_usuario`, `id_sucursal`.
- Permisos contextuales simples: `tipo_habilitacion_sucursal`, `es_sucursal_predeterminada`, `puede_operar`, `puede_consultar`, `puede_administrar`.
- Vigencia y estado: `fecha_desde`, `fecha_hasta`, `estado_vinculo`, `observaciones`.
- Check: `chk_usuario_sucursal_vigencia`.
- PK: `usuario_sucursal_pkey`.
- Índices: `idx_us_sucursal`, `idx_us_usuario`, `ix_usuario_sucursal_vigencia`.
- FKs: `fk_us_sucursal`, `fk_us_usuario`.

Observación: esta tabla no tiene en el schema base el bloque completo de metadata CORE-EF (`uid_global`, `version_registro`, `id_instalacion_*`, `op_id_*`, `deleted_at`), a diferencia de `usuario_rol_seguridad` implementado recientemente por el tramo administrativo.

### `usuario_rol_sucursal`

Columnas relevantes:

- `id_usuario_rol_sucursal`, `id_usuario`, `id_rol_seguridad`, `id_sucursal`, `fecha_desde`, `fecha_hasta`.
- Check: `chk_usuario_rol_sucursal_vigencia`.
- Índice de vigencia: `ix_usuario_rol_sucursal_vigencia`.
- FKs: usuario, rol de seguridad y sucursal.

Observación: representa alcance de seguridad por sucursal en SQL, pero no hay endpoints administrativos implementados para esta tabla en el backend actual.

### Tablas de sincronización relacionadas

- `sincronizacion_paquete`: `id_instalacion_origen`, `codigo_paquete`, `estado_paquete`, fechas de generación/envío/cierre, `cantidad_operaciones`, `hash_paquete`, `observaciones`. Índices por instalación origen y fecha.
- `sincronizacion_recepcion`: `op_id`, `id_instalacion_origen`, `id_instalacion_receptora`, entidad/evento/versionado, payload/hash, fechas de recepción/procesamiento, estado, conflicto y detalle. Índice por instalación receptora.
- `sincronizacion_operacion`: paquete, `op_id`, operación, entidad, `uid_entidad`, `id_entidad_principal`, `version_registro`, estado, fecha, orden, payload/hash y flag de resolución manual.
- `conflicto_sincronizacion`: conflicto por `op_id`, entidad, versión, tipo, estado y resolución.
- `outbox_event`: outbox transaccional genérico, con `event_id`, `event_type`, aggregate, payload, timestamps, status, retries y metadata.
- `lock_logico`: lock por entidad con `id_instalacion_origen`, `id_usuario_origen`, `op_id`, motivo, expiración y estado.

### Columnas CORE-EF que referencian instalación

El schema y patches usan de forma extendida:

- `id_instalacion_origen`.
- `id_instalacion_ultima_modificacion`.
- `op_id_alta`.
- `op_id_ultima_modificacion`.
- `version_registro`.
- `uid_global`.
- `deleted_at`.

CORE-EF exige distinguir ID local de UID distribuido, versionado, instalación origen, instalación de última modificación, outbox, locks e idempotencia para entidades sincronizables. `sucursal` e `instalacion` aparecen en la matriz CORE-EF como entidades SYNC, con versionado, soft delete, outbox, headers y auditoría requeridos.

## Endpoints existentes e inexistentes

### Endpoints administrativos existentes

El backend actual tiene un router administrativo con endpoints bajo `/api/v1/administrativo` para:

- `GET /api/v1/administrativo/roles-seguridad`.
- `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}`.
- `GET /api/v1/administrativo/permisos`.
- `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/permisos`.
- `POST /api/v1/administrativo/usuarios`.
- `GET /api/v1/administrativo/usuarios`.
- `GET /api/v1/administrativo/usuarios/{id_usuario}`.
- `GET /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad`.
- `POST /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad`.
- `PATCH /api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad/{id_asignacion}/baja`.
- `GET /api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/usuarios`.
- `PATCH /api/v1/administrativo/usuarios/{id_usuario}/baja`.

No se encontraron endpoints implementados para:

- CRUD/listado de `sucursal`.
- CRUD/listado de `instalacion`.
- Asociación `instalacion` ↔ `sucursal` fuera de la FK SQL.
- `usuario_sucursal`.
- `usuario_instalacion`.
- `usuario_rol_sucursal`.
- APIs de sincronización por paquete/recepción/operación.

### Endpoints operativos existentes

No se encontró router `/api/v1/operativo` implementado. Los routers existentes están agrupados como `Inmobiliario`, `Comercial`, `Locativo`, `Financiero`, `Personas`, `Administrativo` y `health`.

`SRV-OPE-001` ya existe y define la gestión de sucursales con alta, modificación, baja lógica y consulta. `SRV-OPE-002` ya existe y define la gestión de instalaciones dentro del dominio operativo. Por lo tanto, lo que falta es materializar la API operativa correspondiente bajo `/api/v1/operativo`, no definir nuevamente esos servicios DEV-SRV.

### Endpoints inmobiliarios y otros dominios

Los routers de inmuebles, desarrollos, edificaciones, servicios, personas y financiero ya usan headers CORE-EF (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) en writes. Esto confirma que sucursal/instalación ya son contexto transversal de operación y trazabilidad, pero no expone administración propia de esas entidades.

## Decisión recomendada de ubicación API

### Opción A: `/api/v1/operativo`

Recomendada.

Justificación:

1. `SRV-OPE-002` define `instalacion` como unidad técnica real vinculada a sucursal y ubica su gestión en operativo.
2. `DEV-API-INM-001` advierte que `instalacion` no pertenece al núcleo inmobiliario y mantiene ownership operativo.
3. CORE-EF usa instalación como entidad técnica de sincronización, no como entidad de seguridad administrativa.
4. `sucursal` define alcance operativo/organizacional, no identidad de usuario ni rol de seguridad.
5. Permite separar administración de entidades operativas de la administración de usuarios/roles/permisos.

Implicancia CORE-EF: los writes de alta, modificación, baja y asociación deberán nacer como `COMMAND_WRITE_TECNICO` o `COMMAND_WRITE_NEGOCIO` según el caso, usando helper común de headers y cumpliendo idempotencia, outbox, lock lógico, versionado y transacción.

### Opción B: `/api/v1/administrativo`

No recomendada como ownership principal.

Justificación:

1. El dominio administrativo existente está centrado en usuario, rol_seguridad, permiso y asignación.
2. `DEV-API-ADM-001` indica que administrativo todavía no implementa alcance por sucursal y deja fuera ampliar sucursal sin issue/documentación específica.
3. Ubicar CRUD de sucursal/instalación en administrativo puede confundir gestión de seguridad con ownership operativo.

Uso aceptable: endpoints administrativos futuros para permisos por contexto (`usuario_sucursal`, `usuario_rol_sucursal`) pueden vivir bajo `/api/v1/administrativo` si se documenta que son soporte de autorización y no redefinen la entidad `sucursal`.

### Opción C: `/api/v1/inmobiliario`

No recomendada.

Justificación:

1. `DEV-API-INM-001` confirma que `instalacion` no pertenece al núcleo inmobiliario.
2. `inmueble_sucursal` puede vincular activos con sucursal, pero no transfiere ownership de sucursal al dominio inmobiliario.

## Decisión funcional recomendada

- `sucursal`: entidad operativa/organizacional. Núcleo operativo para alcance físico/organizacional, visibilidad, operación, contexto de headers y futuras reglas de permisos por contexto.
- `instalacion`: entidad técnica de sincronización. Núcleo operativo técnico vinculado obligatoriamente a una sucursal, con `permite_sincronizacion`, identificador técnico y metadata CORE-EF.
- `usuario_sucursal`: soporte administrativo-operativo para habilitación contextual; no reemplaza permisos por rol ni define sucursal.
- `usuario_rol_sucursal`: soporte de seguridad contextual por sucursal; su API debe tratarse como administración de permisos/contexto, no como gestión de sucursal.
- `inmueble_sucursal`: soporte de asignación/visibilidad operativa sobre activos inmobiliarios; no debe invadir propiedad semántica de inmueble ni de sucursal.

## Riesgos CORE-EF

1. **Bootstrap de headers:** crear la primera sucursal/instalación requiere criterio explícito, porque los writes sincronizables exigen `X-Sucursal-Id` y `X-Instalacion-Id`. Puede requerir seed, comando técnico inicial o endpoint de bootstrap no sincronizable cuidadosamente acotado.
2. **Idempotencia:** altas de sucursal e instalación deben definir criterio de payload para `mismo op_id + mismo payload`, conflicto para `mismo op_id + payload distinto` y retry post-error.
3. **Versionado:** modificaciones y bajas deben exigir `If-Match-Version` si actualizan entidades versionadas.
4. **Outbox:** `sucursal` e `instalacion` están en matriz CORE-EF como sincronizables; los writes deben registrar evento en la misma transacción que el cambio de negocio/técnico.
5. **Lock lógico:** cambios de instalación/sucursal pueden afectar sync, contexto de operación y visibilidad; debe definirse entidad bloqueada y operaciones incompatibles.
6. **Errores estándar:** no usar `{"detail": "..."}` para errores de headers; usar `ErrorResponse` y helper común CORE-EF.
7. **No cumplimiento declarativo:** no afirmar cumplimiento CORE-EF profundo sin evidencia en router/service/repository/SQL/tests.

## Riesgos de sincronización

1. `instalacion` es FK obligatoria de paquetes y recepción; una baja o cambio de estado debe contemplar paquetes pendientes.
2. `sucursal` y `instalacion` son entidades sincronizables; deben tener `uid_global` como identidad distribuida y no depender del ID local entre instalaciones.
3. La relación instalación-sucursal debe ser consistente durante replicación; si se permite modificar `id_sucursal`, debe definirse impacto sobre paquetes, sesiones, parámetros y auditoría.
4. Conflictos de código único (`codigo_sucursal`, `codigo_instalacion`) entre instalaciones requieren política de resolución.
5. `usuario_sucursal` carece de metadata CORE-EF completa en el schema base; si se sincroniza, debe evaluarse patch de estructura antes de implementar writes.
6. No existe `usuario_instalacion`; no debe inventarse hasta definir necesidad real, ownership y SQL.

## Qué queda fuera de alcance de la primera implementación

- Caja operativa, jornada, recibos fiscales persistidos y documental real.
- Sincronización avanzada entre instalaciones y resolución completa de conflictos.
- Permisos efectivos por contexto en runtime.
- CRUD de `usuario_sucursal`, `usuario_rol_sucursal` o `usuario_instalacion`.
- Cambios de dominio inmobiliario o financiero por sucursal.
- Migraciones no respaldadas por diseño CORE-EF y tests.
- Creación de `usuario_instalacion` sin evidencia SQL/documental.

## Propuesta de issues siguientes

1. **Operativo: contrato DEV-API de sucursales.** Derivar el contrato DEV-API desde `SRV-OPE-001` para read/CRUD base de sucursales.
2. **Operativo: CRUD/read de sucursales.** Implementar API según `SRV-OPE-001` con router, schemas, repository, tests y CORE-EF para `sucursal`.
3. **Operativo: contrato DEV-API de instalaciones.** Alinear `SRV-OPE-002` con endpoints, payloads, estados y errores.
4. **Operativo: CRUD/read de instalaciones.** Implementar router, schemas, repository, tests y CORE-EF para `instalacion`.
5. **Operativo: asociación instalación-sucursal.** Definir si la asociación se modifica solo como campo de instalación o con endpoint específico; documentar versionado y lock.
6. **Administrativo/seguridad: alcance por sucursal.** Diseñar APIs para `usuario_sucursal` y/o `usuario_rol_sucursal` sin redefinir sucursal.
7. **CORE-EF: bootstrap técnico.** Definir cómo crear/sembrar la primera sucursal e instalación sin romper headers obligatorios.
8. **Sincronización: eventos y conflictos.** Definir eventos outbox y resolución de conflictos para `sucursal` e `instalacion`.

## Propuesta de roadmap incremental

### Fase 1: CRUD/read base de sucursales

- Ubicación recomendada: `/api/v1/operativo/sucursales`.
- Lecturas: `QUERY_READLIKE`; no deberían exigir headers write.
- Writes: `COMMAND_WRITE_NEGOCIO` o `COMMAND_WRITE_TECNICO` según se decida para gestión organizacional; deben exigir headers CORE-EF, idempotencia, outbox, versionado y tests mínimos.
- Alcance: implementar API según `SRV-OPE-001` para alta, listado, detalle, modificación y baja lógica de `sucursal`.

### Fase 2: CRUD/read base de instalaciones

- Ubicación recomendada: `/api/v1/operativo/instalaciones`.
- Lecturas: `QUERY_READLIKE`.
- Writes: probablemente `COMMAND_WRITE_TECNICO`, porque `instalacion` es unidad técnica de sincronización.
- Alcance: alta, listado, detalle, modificación técnica y baja lógica, siempre vinculada a sucursal existente.

### Fase 3: asociación instalación ↔ sucursal

- Confirmar si se permite cambiar `id_sucursal` de una instalación existente.
- Si se permite, requerir `If-Match-Version`, lock lógico de instalación y validación de paquetes/sesiones/contextos pendientes.
- Si no se permite, documentar asociación inmutable post-alta y usar baja/alta controlada para relocalización.

### Fase 4: uso de sucursal/instalación para alcance operativo

- Usar `X-Sucursal-Id` y `X-Instalacion-Id` como contexto verificable contra SQL.
- Validar existencia, estado y coherencia instalación-sucursal en writes sincronizables.
- Evaluar impacto en visibilidad de inmuebles, desarrollos, servicios y operaciones físicas.

### Fase 5: integración con permisos/contexto

- Implementar o documentar `usuario_sucursal` y/o `usuario_rol_sucursal` como soporte de autorización contextual.
- Mantener endpoints de permisos en administrativo si el recurso principal es asignación de seguridad.
- No introducir `usuario_instalacion` sin SQL, necesidad funcional y reglas CORE-EF.

### Fase 6: caja/jornada

- Recién después de sucursal/instalación y permisos contextuales, diseñar caja operativa y jornada.
- Nacer con CORE-EF completo: headers, idempotencia, outbox, locks, versionado, rollback, tests y decisión de sincronización.

## Checklist CORE-EF para futuros PR write

Para cada endpoint write futuro de sucursal/instalación debe incluirse decisión explícita:

- Clasificación: `COMMAND_WRITE_NEGOCIO`, `COMMAND_WRITE_TECNICO` o `NO_CONFIRMADO` hasta cerrar contrato.
- Headers: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; `If-Match-Version` en modificación/baja.
- Idempotencia: aplica en altas y commands sincronizables; definir criterio de payload y conflictos.
- Outbox: aplica si la entidad es sincronizable; evento en la misma transacción.
- Lock lógico: aplica/no aplica por operación con entidad bloqueada explícita.
- Versionado: `version_registro` debe incrementarse en modificaciones/bajas.
- Rollback/transacción: frontera transaccional del caso de uso.
- Tests mínimos: headers faltantes/inválidos, happy path, `If-Match-Version`, mismatch real, idempotencia, rollback y outbox cuando aplique.
