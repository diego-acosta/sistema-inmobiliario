# CORE-EF-001 — Infraestructura Transversal de Aplicación y Sincronización

## 0. Metadatos del documento
- **Nombre formal:** Especificación Formal de Infraestructura Transversal de Aplicación y Sincronización
- **Versión:** 1.0
- **Estado:** Lista para desarrollo
- **Naturaleza:** Documento normativo de arquitectura e implementación
- **Ámbito:** Backend local FastAPI + PostgreSQL + sincronización distribuida entre instalaciones
- **Objetivo:** Definir requisitos obligatorios de infraestructura transversal para implementación directa de servicios, repositorios, endpoints y procesos de sincronización

## 1. Objeto

### 1.1. Finalidad
La presente especificación define los requisitos obligatorios que debe respetar el backend del sistema en materia de:

- identidad global
- versionado de registros
- timestamps transversales
- transacciones
- locks lógicos
- operaciones distribuidas
- sincronización entre instalaciones
- outbox / inbox
- idempotencia
- resolución de conflictos
- borrado lógico

### 1.2. Alcance técnico
Esta especificación aplica a:

- entidades sincronizables de negocio
- entidades sincronizables administrativas
- tablas técnicas de sincronización
- servicios de aplicación
- repositorios
- endpoints de comando
- endpoints de sincronización
- procesos internos de aplicación de cambios remotos

### 1.3. Separación obligatoria de problemas
Se establecen dos planos técnicos distintos:

- concurrencia local dentro de una instalación
- sincronización distribuida entre instalaciones

Queda prohibido implementar ambos problemas como si fueran el mismo.

## 2. Convenciones normativas

### 2.1. Fuerza normativa
En este documento:

- **DEBE** = obligatorio
- **NO DEBE** = prohibido
- **DEBERÍA** = recomendación fuerte
- **PUEDE** = permitido
- **PENDIENTE** = abierto, no congelado en esta versión

### 2.2. Convención de requisitos
Todos los requisitos normativos se identifican con IDs del tipo:

- `REQ-SYNC-XXX`

### 2.3. Regla de prevalencia
Si una decisión de implementación contradice un requisito de este documento, la implementación se considera incorrecta.

## 3. Definiciones

### 3.1. Sucursal
Unidad operativa del negocio.

### 3.2. Instalación
Unidad técnica real con base de datos propia.

Dentro de una instalación pueden existir múltiples PCs conectadas a la misma DB.

### 3.3. Entidad sincronizable
Toda entidad cuyo estado deba viajar, compararse, replicarse o auditarse entre instalaciones.

### 3.4. ID local
Identificador interno de base de datos usado para joins, FKs y performance local.

### 3.5. UID global
Identificador global inmutable de una fila sincronizable.

### 3.6. version_registro
Versión entera monotónica de una fila sincronizable.

### 3.7. op_id
Identificador global único de una operación distribuida persistente.

### 3.8. Outbox
Registro local persistido de cambios emitibles.

### 3.9. Inbox
Registro local persistido de cambios recibidos.

### 3.10. Lock lógico
Mecanismo de exclusividad operativa persistida.

### 3.11. Conflicto de sincronización
Divergencia material entre un cambio entrante y el estado local.

### 3.12. Borrado lógico
Invalidación funcional sin borrado físico.

## 4. Requisitos formales

### 4.1 Identidad global
**Reglas**

**REQ-SYNC-001**  
Toda entidad sincronizable DEBE poseer simultáneamente:

- ID local técnico
- UID global inmutable

**REQ-SYNC-002**  
El ID local DEBE usarse para joins internos, claves foráneas físicas y performance local.

**REQ-SYNC-003**  
El ID local NO DEBE usarse como identidad distribuida entre instalaciones.

**REQ-SYNC-004**  
Toda entidad sincronizable DEBE incluir `uid_global NOT NULL`.

**REQ-SYNC-005**  
Toda tabla sincronizable DEBE tener restricción `UNIQUE(uid_global)`.

**REQ-SYNC-006**  
Toda tabla sincronizable DEBE tener índice sobre `uid_global`.

**REQ-SYNC-007**  
`uid_global` DEBE ser inmutable.

**REQ-SYNC-008**  
`uid_global` NO DEBE reutilizarse.

**REQ-SYNC-009**  
Todo flujo de sincronización, comparación remota y resolución de conflictos DEBE operar por `uid_global`.

**REQ-SYNC-010**  
Las tablas puramente temporales, efímeras o locales PUEDEN quedar sin `uid_global`.

**Pendiente**

**PENDIENTE-001**  
Congelar si `uid_global` será UUID v4 o UUID v7.

### 4.2 Versionado
**REQ-SYNC-011**  
Toda entidad sincronizable DEBE incluir `version_registro`.

**REQ-SYNC-012**  
Toda inserción sincronizable DEBE crear el registro con `version_registro = 1`.

**REQ-SYNC-013**  
Toda modificación lógica DEBE incrementar `version_registro` en 1.

**REQ-SYNC-014**  
Toda baja lógica DEBE incrementar `version_registro`.

**REQ-SYNC-015**  
Toda actualización de entidad crítica DEBE validar optimistic locking usando la versión esperada.

**REQ-SYNC-016**  
Si una mutación condicionada por versión no afecta filas, el backend DEBE devolver error de concurrencia local.

**REQ-SYNC-017**  
El backend NO DEBE sobrescribir silenciosamente una fila si la versión esperada ya no coincide.

**REQ-SYNC-018**  
La comparación remota entre dos versiones del mismo `uid_global` DEBE tomar como criterio primario `version_registro`.

**REQ-SYNC-019**  
Si dos registros con igual `uid_global` tienen igual `version_registro` pero distinto payload material, DEBE registrarse inconsistencia o conflicto.

**REQ-SYNC-020**  
En operaciones de criticidad alta, `version_registro` NO DEBE considerarse mecanismo suficiente por sí solo.

### 4.3 Timestamps
**REQ-SYNC-021**  
Toda entidad sincronizable DEBE incluir:

- `created_at`
- `updated_at`
- `deleted_at`

**REQ-SYNC-022**  
Toda inserción DEBE establecer `created_at` y `updated_at`.

**REQ-SYNC-023**  
Toda modificación material DEBE actualizar `updated_at`.

**REQ-SYNC-024**  
Toda baja lógica DEBE establecer `deleted_at` y actualizar `updated_at`.

**REQ-SYNC-025**  
Los timestamps DEBEN usarse para trazabilidad, ordenamiento y desempate secundario.

**REQ-SYNC-026**  
Los timestamps NO DEBEN reemplazar ni a `uid_global`, ni a `version_registro`, ni a `op_id`.

**Pendiente**

**PENDIENTE-002**  
Congelar si el estándar físico será timestamp con convención UTC o timestamptz.

### 4.4 Transacciones
**REQ-SYNC-027**  
Toda operación de negocio indivisible DEBE ejecutarse dentro de una transacción local.

**REQ-SYNC-028**  
La frontera transaccional DEBE definirse por caso de uso, no por operación parcial.

**REQ-SYNC-029**  
Toda operación que modifique datos sincronizables y genere cambio distribuible DEBE persistir el dato de negocio y el outbox en la misma transacción.

**REQ-SYNC-030**  
Si falla una validación, restricción, trigger, lock, escritura técnica o integridad vinculada al caso de uso, la transacción DEBE revertirse completa.

**REQ-SYNC-031**  
La aplicación NO DEBE dejar persistido el cambio de negocio sin su registro técnico de sincronización cuando la operación lo requiera.

**REQ-SYNC-032**  
Los procesos masivos DEBERÍAN dividirse en lotes controlados.

### 4.5 Lock lógico
**REQ-SYNC-033**  
El sistema DEBE implementar un mecanismo persistido de lock lógico para exclusividad operativa.

**REQ-SYNC-034**  
El lock lógico DEBE ser independiente del optimistic locking y de la transacción SQL.

**REQ-SYNC-035**  
El lock lógico DEBE usarse en edición prolongada o procesos críticos donde optimistic locking no sea suficiente.

**REQ-SYNC-036**  
El sistema DEBE impedir operaciones incompatibles sobre una entidad mientras exista lock activo válido.

**REQ-SYNC-037**  
La tabla de locks DEBE permitir identificar:

- tipo de entidad
- uid_entidad
- usuario
- instalación origen
- token de lock
- timestamps de alta, renovación y expiración
- estado del lock

**REQ-SYNC-038**  
Solo DEBE existir un lock activo por entidad y contexto funcional incompatible.

**REQ-SYNC-039**  
Todo lock DEBE tener expiración automática.

**REQ-SYNC-040**  
Todo lock en uso legítimo DEBE poder renovarse.

**REQ-SYNC-041**  
Todo lock DEBE poder pasar por estados equivalentes a:

- ACTIVO
- LIBERADO
- EXPIRADO
- FORZADO
- ABANDONADO

**REQ-SYNC-042**  
Los ABM simples NO DEBEN usar lock lógico cuando alcance con optimistic locking.

### 4.6 op_id
**REQ-SYNC-043**  
Toda operación que cree, modifique, elimine lógicamente o aplique cambios sincronizables DEBE tener `op_id`.

**REQ-SYNC-044**  
`op_id` DEBE ser globalmente único.

**REQ-SYNC-045**  
`op_id` DEBE identificar una operación distribuida persistente y no una mera llamada HTTP.

**REQ-SYNC-046**  
Un mismo `op_id` PUEDE abarcar múltiples filas si forman parte de una misma operación indivisible.

**REQ-SYNC-047**  
`op_id` DEBE quedar persistido en la infraestructura técnica de sincronización.

**REQ-SYNC-048**  
Toda entidad sincronizable DEBE registrar `op_id_alta`.

**REQ-SYNC-049**  
Toda modificación sincronizable DEBE registrar `op_id_ultima_modificacion`.

**REQ-SYNC-050**  
Toda resolución de conflicto con impacto en datos DEBE generar un nuevo `op_id`.

**Pendiente**

**PENDIENTE-003**  
Congelar formato exacto de `op_id`.

### 4.7 Concurrencia local
**REQ-SYNC-051**  
Dentro de una instalación NO DEBE modelarse sincronización distribuida.

**REQ-SYNC-052**  
Dentro de una instalación la concurrencia DEBE resolverse con:

- transacciones
- optimistic locking
- locks lógicos cuando corresponda
- restricciones y triggers

**REQ-SYNC-053**  
Los conflictos de edición simultánea local DEBEN tratarse como conflictos de concurrencia, no de réplica.

**REQ-SYNC-054**  
Los servicios de aplicación DEBEN detectar y devolver en forma explícita los errores de concurrencia local.

### 4.8 Sincronización distribuida
**REQ-SYNC-055**  
La sincronización entre instalaciones DEBE implementarse con consistencia eventual.

**REQ-SYNC-056**  
Entre instalaciones NO DEBE asumirse commit distribuido único.

**REQ-SYNC-057**  
Todo cambio sincronizable local DEBE poder emitirse mediante outbox.

**REQ-SYNC-058**  
Todo cambio remoto recibido DEBE registrarse y procesarse mediante inbox o estructura equivalente.

**REQ-SYNC-059**  
La unidad semántica mínima de cambio distribuido DEBE ser la operación.

**REQ-SYNC-060**  
La sincronización DEBE ser trazable, reintentable e idempotente.

### 4.9 Outbox
**REQ-SYNC-061**  
El sistema DEBE persistir un registro de salida por cada operación distribuible local.

**REQ-SYNC-062**  
La escritura del outbox DEBE formar parte de la misma transacción del cambio de negocio.

**REQ-SYNC-063**  
Cada registro de outbox DEBE incluir, como mínimo:

- `op_id`
- `uid_entidad`
- `tipo_entidad`
- `tipo_evento`
- `version_registro`
- `payload`
- hash o huella del payload
- instalación origen
- timestamp técnico
- estado

**REQ-SYNC-064**  
El outbox DEBE soportar tipos de evento equivalentes a:

- INSERT
- UPDATE
- DELETE_LOGICO

**REQ-SYNC-065**  
El outbox DEBE soportar estados equivalentes a:

- PENDIENTE
- EMPAQUETADO
- ENVIADO
- CONFIRMADO
- ERROR
- ANULADO

**REQ-SYNC-066**  
No DEBE haber duplicación funcional de outbox para un mismo `op_id`.

### 4.10 Inbox
**REQ-SYNC-067**  
Todo cambio remoto recibido DEBE quedar registrado antes o durante su procesamiento controlado.

**REQ-SYNC-068**  
Cada registro de inbox DEBE incluir, como mínimo:

- `op_id`
- instalación origen
- `uid_entidad`
- `tipo_entidad`
- `tipo_evento`
- `version_registro`
- `payload`
- hash o huella del payload
- fecha de recepción
- fecha de procesamiento
- estado
- referencia a conflicto si existiera

**REQ-SYNC-069**  
El inbox DEBE soportar estados equivalentes a:

- RECIBIDO
- EN_PROCESO
- APLICADO
- DUPLICADO
- RECHAZADO
- CONFLICTO

**REQ-SYNC-070**  
Un cambio con `op_id` ya aplicado NO DEBE volver a producir efectos de negocio.

**REQ-SYNC-071**  
Un cambio rechazado DEBE quedar trazado.

**REQ-SYNC-072**  
Un cambio conflictivo DEBE quedar persistido como conflicto.

### 4.11 Idempotencia
**REQ-SYNC-073**  
La sincronización DEBE ser segura ante duplicados, reintentos, reprocesamientos y reenvíos.

**REQ-SYNC-074**  
La clave primaria de idempotencia DEBE ser `op_id`.

**REQ-SYNC-075**  
Si un `op_id` ya fue aplicado, el reprocesamiento DEBE clasificarse como duplicado seguro o equivalente, sin generar nuevo efecto de negocio.

**REQ-SYNC-076**  
El sistema DEBE distinguir entre:

- DUPLICADO
- RECHAZADO
- CONFLICTO

**REQ-SYNC-077**  
Los endpoints de sincronización DEBEN ser idempotentes.

**REQ-SYNC-078**  
La idempotencia DEBE tratarse como criticidad máxima en cobranzas, movimientos financieros, aplicaciones financieras, tesorería y recibos.

**REQ-SYNC-079**  
Ningún reintento técnico DEBE duplicar efecto económico.

### 4.12 Conflictos
**REQ-SYNC-080**  
El sistema DEBE clasificar las entidades sincronizables por criticidad:

- baja
- media
- alta

**REQ-SYNC-081**  
La resolución de conflictos DEBE evaluar, como mínimo:

- `uid_global`
- `version_registro`
- `op_id`
- `updated_at` como criterio secundario
- instalación origen como criterio auxiliar
- reglas funcionales por entidad

**REQ-SYNC-082**  
Las entidades de baja criticidad PUEDEN admitir auto-resolución controlada.

**REQ-SYNC-083**  
Las entidades de media criticidad DEBEN regirse por reglas explícitas.

**REQ-SYNC-084**  
Las entidades de alta criticidad NO DEBEN auto-fusionarse salvo regla específica formalizada.

**REQ-SYNC-085**  
Toda divergencia material no resoluble en forma segura DEBE persistirse como conflicto.

**REQ-SYNC-086**  
La tabla de conflictos DEBE soportar estados equivalentes a:

- DETECTADO
- EN_ANALISIS
- RESUELTO_AUTOMATICO
- RESUELTO_MANUAL
- DESCARTADO

**REQ-SYNC-087**  
Toda resolución de conflicto con persistencia DEBE dejar trazabilidad completa.

**REQ-SYNC-088**  
Toda resolución de conflicto con impacto en datos DEBE generar nuevo `op_id`.

**Pendiente**

**PENDIENTE-004**  
Definir si persona admitirá merge automático por campo.

### 4.13 Borrado lógico
**REQ-SYNC-089**  
En entidades sincronizables, el mecanismo estándar DEBE ser borrado lógico.

**REQ-SYNC-090**  
La baja lógica DEBE representarse con `deleted_at` y aumento de `version_registro`.

**REQ-SYNC-091**  
Toda baja lógica DEBE viajar como evento sincronizable.

**REQ-SYNC-092**  
El borrado lógico NO DEBE destruir trazabilidad, auditoría ni historial financiero.

**REQ-SYNC-093**  
El borrado lógico NO DEBE invalidar ilegítimamente comprobantes emitidos ni registros técnicos.

**Pendiente**

**PENDIENTE-005**  
Congelar política exacta de reactivación por tipo de entidad.

### 4.14 Tablas técnicas
**REQ-SYNC-094**  
El sistema DEBE contar con tablas técnicas suficientes para representar:

- instalación técnica de sync
- outbox
- inbox
- conflictos
- locks

**REQ-SYNC-095**  
Las tablas técnicas DEBEN ser consultables para diagnóstico.

**REQ-SYNC-096**  
Las tablas técnicas DEBEN ser auditables y no ambiguas en sus estados.

**REQ-SYNC-097**  
Las tablas ya existentes de sincronización PUEDEN absorber parte de esta semántica, siempre que no se pierda ninguna función requerida.

### 4.15 Columnas transversales
**REQ-SYNC-098**  
Toda entidad sincronizable DEBE incluir, como mínimo:

- `uid_global`
- `version_registro`
- `created_at`
- `updated_at`
- `deleted_at`
- `id_instalacion_origen`
- `id_instalacion_ultima_modificacion`
- `op_id_alta`
- `op_id_ultima_modificacion`

**REQ-SYNC-099**  
Toda alta sincronizable DEBE registrar identidad global, instalación origen, timestamps y `op_id_alta`.

**REQ-SYNC-100**  
Toda modificación sincronizable DEBE registrar nueva versión, `updated_at`, instalación de última modificación y `op_id_ultima_modificacion`.

## 5. Tablas resumidas

### 5.1. Leyenda
- **UID** = `uid_global`
- **VER** = `version_registro`
- **TS** = `created_at / updated_at / deleted_at`
- **OP** = `op_id_alta / op_id_ultima_modificacion`
- **SYNC** = participa en sincronización entre instalaciones
- **LOCK** = requiere lock lógico en algún caso de uso
- **IDEMP** = requiere idempotencia estricta
- **CONFLICTO** = clase de criticidad ante conflicto

### 5.2. Entidades maestras y operativas
| Entidad | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| persona | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Media |
| sucursal | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| instalacion | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| desarrollo | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Media |
| inmueble | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Alta |
| unidad_funcional | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Alta |
| disponibilidad | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Alta |
| ocupacion | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Alta |

### 5.3. Entidades comerciales y contractuales
| Entidad | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| venta | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| venta_objeto_inmobiliario | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| instrumento_compraventa | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| cesion | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| escrituracion | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| rescision_venta | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| contrato_alquiler | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| contrato_objeto_locativo | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| modificacion_locativa | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| rescision_finalizacion_alquiler | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| entrega_restitucion_inmueble | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |

### 5.4. Entidades financieras
| Entidad | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| relacion_generadora | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| obligacion_financiera | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| obligacion_obligado | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Alta |
| composicion_obligacion | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| movimiento_financiero | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| aplicacion_financiera | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| movimiento_tesoreria | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| recibo / documento equivalente emitido | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |

### 5.5. Entidades documentales
| Entidad | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| documento_logico | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| documento_version | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |
| archivo_digital | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Media |
| emision_numeracion | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Alta |

### 5.6. Entidades administrativas sincronizables
| Entidad | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| usuario | Sí | Sí | Sí | Sí | Sí | Según caso | Sí | Media |
| usuario_persona | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| usuario_sucursal | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| usuario_rol_seguridad | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| usuario_rol_sucursal | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| denegacion_explicita | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Media |
| valor_parametro | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Baja/Media |
| item_catalogo | Sí | Sí | Sí | Sí | Sí | No habitual | Sí | Baja |

### 5.7. Tablas técnicas de sincronización
| Entidad técnica | UID | VER | TS | OP | SYNC | LOCK | IDEMP | CONFLICTO |
|---|---|---|---|---|---|---|---|---|
| sync_installation / equivalente | Sí | No obligatorio | Sí | Sí | Sí | No | Sí | Media |
| sync_outbox / equivalente | Sí o identificador técnico único | No | Sí | Sí | Sí | No | Sí | Baja |
| sync_inbox / equivalente | Sí o identificador técnico único | No | Sí | Sí | Sí | No | Sí | Baja |
| sync_conflict / equivalente | Sí | Sí | Sí | Sí | Sí | Sí en resolución | Sí | Alta |
| record_lock | Sí o token único | No | Sí | No obligatorio | No distribuible o según diseño | N/A | No | N/A |

### 5.8. Operaciones que requieren lock lógico
| Operación | Lock |
|---|---|
| edición prolongada de venta | Obligatorio |
| edición prolongada de contrato | Obligatorio |
| registración de cobranza | Obligatorio |
| emisión de recibo | Obligatorio |
| anulación de recibo permitida | Obligatorio |
| reformulación financiera | Obligatorio |
| resolución manual de conflicto | Obligatorio |
| ABM simple de parámetro | No obligatorio |
| corrección simple de persona | Según caso |

### 5.9. Operaciones que requieren idempotencia estricta
| Operación | Idempotencia |
|---|---|
| recepción de cambios remotos | Obligatoria |
| aplicación de cambio remoto | Obligatoria |
| reenvío de paquete | Obligatoria |
| reprocesamiento de inbox | Obligatoria |
| cobranza | Obligatoria crítica |
| movimiento financiero | Obligatoria crítica |
| aplicación financiera | Obligatoria crítica |
| tesorería | Obligatoria crítica |
| emisión de recibo | Obligatoria crítica |

## 6. Estructuras técnicas mínimas

### 6.1. `record_lock` o equivalente
Campos mínimos:

- `id_record_lock`
- `tipo_entidad`
- `uid_entidad`
- `id_usuario`
- `id_instalacion_origen`
- `token_lock`
- `motivo_lock`
- `fecha_hora_lock`
- `fecha_hora_expiracion`
- `fecha_hora_ultima_renovacion`
- `estado_lock`

### 6.2. `sync_outbox` o equivalente
Campos mínimos:

- `id_sync_outbox`
- `op_id`
- `uid_entidad`
- `tipo_entidad`
- `tipo_evento`
- `version_registro`
- `payload_json`
- `hash_payload`
- `id_instalacion_origen`
- `fecha_hora_generacion`
- `estado_outbox`
- `reintentos`
- `ultimo_error`

### 6.3. `sync_inbox` o equivalente
Campos mínimos:

- `id_sync_inbox`
- `op_id`
- `id_instalacion_origen`
- `uid_entidad`
- `tipo_entidad`
- `tipo_evento`
- `version_registro`
- `payload_json`
- `hash_payload`
- `fecha_hora_recepcion`
- `fecha_hora_procesamiento`
- `estado_inbox`
- `motivo_rechazo`
- `detalle_resultado`
- `id_conflicto`

### 6.4. `sync_conflict` o equivalente
Campos mínimos:

- `id_sync_conflict`
- `op_id_origen`
- `uid_entidad`
- `tipo_entidad`
- `payload_remoto`
- `snapshot_local`
- `motivo_conflicto`
- `criticidad`
- `estado_conflicto`
- `fecha_hora_deteccion`
- `fecha_hora_resolucion`
- `op_id_resolucion`

### 6.5. `sync_installation` o equivalente
Campos mínimos:

- `id_sync_installation`
- `id_instalacion`
- `uid_instalacion`
- `codigo_nodo_sync`
- `estado_sync`
- `ultima_salida_exitosa_at`
- `ultima_entrada_exitosa_at`
- `habilitada_para_sync`

## 7. Reglas por capa

### 7.1. Impacto directo en servicios de aplicación
**Reglas**

**REQ-SYNC-101**  
Todo servicio de comando DEBE recibir o construir contexto técnico suficiente para:

- usuario
- sucursal
- instalación
- `op_id`
- versión esperada cuando corresponda

**REQ-SYNC-102**  
Todo servicio de comando que modifique una entidad sincronizable DEBE:

1. leer estado actual
2. validar lock si corresponde
3. validar versión esperada si corresponde
4. ejecutar validaciones de negocio
5. persistir cambio
6. actualizar metadatos transversales
7. escribir outbox dentro de la misma transacción
8. devolver resultado técnico explícito

**REQ-SYNC-103**  
Todo servicio que aplique cambios remotos DEBE:

1. registrar entrada en inbox
2. verificar idempotencia por `op_id`
3. determinar si aplica, rechaza o entra en conflicto
4. procesar en transacción
5. dejar estado final técnico

**REQ-SYNC-104**  
Los servicios de aplicación DEBEN mapear explícitamente estos resultados:

- éxito
- error de validación
- error de concurrencia local
- lock activo
- duplicado idempotente
- conflicto de sincronización
- inconsistencia técnica bloqueante

**REQ-SYNC-105**  
Los servicios de aplicación NO DEBEN ocultar conflictos técnicos detrás de mensajes genéricos.

**Consecuencias de diseño**

Cada caso de uso de escritura debería modelarse como un comando explícito.

Ejemplos:

- `CrearVentaCommand`
- `ModificarPersonaCommand`
- `RegistrarCobranzaCommand`
- `EmitirReciboCommand`
- `AplicarOperacionRemotaCommand`
- `ResolverConflictoSyncCommand`

Cada comando debería devolver un resultado tipado y no un simple booleano.

### 7.2. Impacto directo en repositorios
**Reglas**

**REQ-SYNC-106**  
Los repositorios DEBEN persistir y devolver metadatos transversales necesarios para sincronización.

**REQ-SYNC-107**  
Los repositorios de entidades sincronizables DEBEN soportar búsqueda por `uid_global`.

**REQ-SYNC-108**  
Los repositorios DEBEN soportar updates condicionados por `version_registro` cuando la entidad lo requiera.

**REQ-SYNC-109**  
Los repositorios NO DEBEN resolver conflictos distribuidos por cuenta propia.

**REQ-SYNC-110**  
Los repositorios NO DEBEN aplicar merge semántico implícito.

**REQ-SYNC-111**  
Los repositorios de inbox y outbox DEBEN exponer operaciones seguras para:

- alta
- lectura por estado
- cambio de estado
- consulta por `op_id`
- reintento controlado

**REQ-SYNC-112**  
Los repositorios de lock DEBEN exponer operaciones para:

- adquirir lock
- renovar lock
- liberar lock
- forzar liberación
- verificar lock activo

**Consecuencias de diseño**

Se recomienda separar repositorios por responsabilidad:

- repositorios de dominio
- repositorios de infraestructura transversal
- repositorios de sincronización
- repositorios de conflicto
- repositorios de lock

No conviene que un único repositorio “gigante” mezcle lógica de dominio con sincronización.

### 7.3. Impacto directo en endpoints
**Reglas**

**REQ-SYNC-113**  
Los endpoints de comando DEBEN trabajar sobre casos de uso transaccionales y no sobre mutaciones parciales descoordinadas.

**REQ-SYNC-114**  
Los endpoints de escritura DEBEN poder devolver estados diferenciados para:

- validación fallida
- concurrencia
- lock
- duplicado
- conflicto
- error técnico

**REQ-SYNC-115**  
Los endpoints de sincronización DEBEN ser idempotentes por `op_id`.

**REQ-SYNC-116**  
Los endpoints de sincronización NO DEBEN asumir que todo cambio recibido se aplica automáticamente.

**REQ-SYNC-117**  
Los endpoints de sincronización DEBEN permitir al menos estos resultados por operación:

- aplicada
- duplicada
- rechazada
- en conflicto

**REQ-SYNC-118**  
Los endpoints de lock DEBEN existir si la UI requiere edición prolongada o reserva operativa explícita.

**REQ-SYNC-119**  
Los endpoints NO DEBEN exponer el ID local como identidad distribuida principal.

**REQ-SYNC-120**  
Los endpoints DEBERÍAN usar `uid_global` como referencia externa estable para entidades sincronizables.

**Consecuencias de diseño**

Ejemplos de endpoints esperables:

- `POST /ventas`
- `PUT /personas/{uid_global}`
- `POST /cobranzas`
- `POST /recibos`
- `POST /locks`
- `DELETE /locks/{token_lock}`
- `POST /sync/receive`
- `POST /sync/reprocess/{op_id}`
- `POST /sync/conflicts/{id}/resolve`

No es una definición cerrada del contrato HTTP, pero sí del impacto estructural.

### 7.4. Impacto directo en manejo de errores
**REQ-SYNC-121**  
El backend DEBE diferenciar errores de negocio de errores técnicos de sincronización.

**REQ-SYNC-122**  
El backend DEBE diferenciar conflicto local de concurrencia de conflicto distribuido.

**REQ-SYNC-123**  
El backend DEBE registrar diagnósticamente:

- `op_id`
- entidad afectada
- usuario
- instalación
- resultado técnico

**REQ-SYNC-124**  
Los errores técnicos de sync NO DEBEN perder el vínculo con el `op_id`.

## 8. Matriz de operaciones
| Tipo de operación | Transacción | Versionado | Lock | Outbox | Inbox | Idempotencia | Conflicto |
|---|---|---|---|---|---|---|---|
| alta simple sincronizable | Sí | Sí | No habitual | Sí | No | Sí | Baja/según entidad |
| modificación simple sincronizable | Sí | Sí | Según caso | Sí | No | Sí | Según entidad |
| baja lógica sincronizable | Sí | Sí | Según caso | Sí | No | Sí | Según entidad |
| edición prolongada de venta | Sí | Sí | Sí | Sí | No | Sí | Alta |
| registración de cobranza | Sí | Sí | Sí | Sí | No | Sí crítica | Alta |
| emisión de recibo | Sí | Sí | Sí | Sí | No | Sí crítica | Alta |
| recepción de cambio remoto | Sí | Según entidad | No | No | Sí | Sí | Sí |
| reprocesamiento de inbox | Sí | Según entidad | No | No | Sí | Sí | Sí |
| resolución manual de conflicto | Sí | Sí | Sí | Sí si impacta datos | Sí/relación técnica | Sí | Alta |

## 9. Pendientes

### 9.1.
**PENDIENTE-001**  
UUID v4 vs UUID v7 para `uid_global`.

### 9.2.
**PENDIENTE-002**  
`timestamp` vs `timestamptz`.

### 9.3.
**PENDIENTE-003**  
Formato exacto de `op_id`.

### 9.4.
**PENDIENTE-004**  
Merge automático por campo para persona.

### 9.5.
**PENDIENTE-005**  
Política de reactivación tras baja lógica por tipo de entidad.

### 9.6.
**PENDIENTE-006**  
Catálogo final cerrado de estados técnicos de outbox, inbox, lock y conflicto.

## 10. Criterios de aceptación
La especificación se considerará implementada correctamente cuando el backend cumpla simultáneamente con lo siguiente:

**REQ-SYNC-125**  
Toda entidad sincronizable implementa columnas transversales obligatorias.

**REQ-SYNC-126**  
Toda escritura sincronizable genera `op_id`.

**REQ-SYNC-127**  
Toda escritura sincronizable usa transacción y outbox acoplado.

**REQ-SYNC-128**  
Toda aplicación remota usa inbox e idempotencia por `op_id`.

**REQ-SYNC-129**  
Existe mecanismo real de lock lógico donde corresponde.

**REQ-SYNC-130**  
Existe persistencia formal de conflictos.

**REQ-SYNC-131**  
El backend diferencia claramente concurrencia local y sincronización distribuida.

**REQ-SYNC-132**  
Las operaciones financieras críticas son idempotentes y no duplicables por reintento.

## 11. Conclusión operativa
Esta versión lista para desarrollo deja definido que el backend deberá construirse sobre estas bases:

- doble identidad: local + global
- versionado obligatorio
- timestamps transversales
- `op_id` obligatorio
- outbox transaccional
- inbox idempotente
- locks lógicos para exclusividad operativa
- conflictos persistidos y resolubles
- borrado lógico en toda entidad sincronizable
- separación estricta entre concurrencia local y sincronización distribuida

Con esto ya queda en condiciones de pasar al siguiente nivel de diseño técnico: contrato de servicios, diseño de repositorios, endpoints FastAPI y modelo físico final de tablas técnicas.

Puedo seguir con el siguiente documento y armar la traducción directa de esta especificación a diseño técnico de backend, en formato: servicios + repositorios + endpoints + flujo de sincronización paso a paso.
