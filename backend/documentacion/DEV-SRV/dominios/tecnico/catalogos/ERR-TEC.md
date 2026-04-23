# ERR-TEC — Errores del dominio Técnico

## Objetivo
Definir errores técnicos y transversales del dominio Técnico como apoyo a implementación backend.

## Alcance del dominio
Incluye operaciones distribuidas, sincronización, inbox y outbox, idempotencia, reintentos, locks lógicos, concurrencia, conflictos técnicos y consultas técnicas.

---

## A. Errores de operaciones distribuidas

### ERR-TEC-001 — operacion_distribuida_no_encontrada
- codigo: operacion_distribuida_no_encontrada
- descripcion: la operación distribuida indicada no existe o no está disponible.
- tipo: tecnico
- aplica_a: operacion_distribuida
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-002 — operacion_distribuida_invalida
- codigo: operacion_distribuida_invalida
- descripcion: la operación distribuida no cumple las validaciones técnicas requeridas.
- tipo: validacion
- aplica_a: operacion_distribuida
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-003 — operacion_distribuida_rechazada
- codigo: operacion_distribuida_rechazada
- descripcion: la operación distribuida fue rechazada por una validación técnica o de consistencia.
- tipo: tecnico
- aplica_a: operacion_distribuida
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-004 — operacion_distribuida_inconsistente
- codigo: operacion_distribuida_inconsistente
- descripcion: la operación distribuida presenta inconsistencias de estado, trazabilidad o contexto técnico.
- tipo: integridad
- aplica_a: operacion_distribuida
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-005 — cierre_tecnico_invalido
- codigo: cierre_tecnico_invalido
- descripcion: no es válido cerrar técnicamente la operación en su estado actual.
- tipo: validacion
- aplica_a: operacion_distribuida
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de sincronización

### ERR-TEC-006 — sincronizacion_no_encontrada
- codigo: sincronizacion_no_encontrada
- descripcion: la sincronización indicada no existe o no está disponible.
- tipo: tecnico
- aplica_a: sincronizacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-007 — sincronizacion_fallida
- codigo: sincronizacion_fallida
- descripcion: la sincronización no pudo completarse bajo las condiciones técnicas actuales.
- tipo: tecnico
- aplica_a: sincronizacion
- origen: DEV-SRV
- es_reintento_valido: sí
- observaciones: el reintento depende de que persistan condiciones válidas de consistencia.

### ERR-TEC-008 — cambio_remoto_invalido
- codigo: cambio_remoto_invalido
- descripcion: el cambio remoto recibido no cumple las validaciones técnicas requeridas.
- tipo: validacion
- aplica_a: cambio_remoto
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-009 — cambio_remoto_inaplicable
- codigo: cambio_remoto_inaplicable
- descripcion: el cambio remoto no puede aplicarse sobre el estado local vigente.
- tipo: integridad
- aplica_a: cambio_remoto
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-010 — confirmacion_sincronizacion_invalida
- codigo: confirmacion_sincronizacion_invalida
- descripcion: la confirmación de sincronización no es válida para el estado técnico actual.
- tipo: validacion
- aplica_a: sincronizacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-011 — sincronizacion_inconsistente
- codigo: sincronizacion_inconsistente
- descripcion: la sincronización presenta inconsistencias de estado, secuencia o trazabilidad técnica.
- tipo: integridad
- aplica_a: sincronizacion
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de inbox y outbox

### ERR-TEC-012 — outbox_no_encontrado
- codigo: outbox_no_encontrado
- descripcion: el registro de outbox indicado no existe o no está disponible.
- tipo: tecnico
- aplica_a: outbox
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-013 — inbox_no_encontrado
- codigo: inbox_no_encontrado
- descripcion: el registro de inbox indicado no existe o no está disponible.
- tipo: tecnico
- aplica_a: inbox
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-014 — registro_outbox_invalido
- codigo: registro_outbox_invalido
- descripcion: no es válido registrar el cambio o evento en outbox bajo el contexto técnico actual.
- tipo: validacion
- aplica_a: outbox
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-015 — registro_inbox_invalido
- codigo: registro_inbox_invalido
- descripcion: no es válido registrar el mensaje recibido en inbox bajo el contexto técnico actual.
- tipo: validacion
- aplica_a: inbox
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-016 — procesamiento_inbox_invalido
- codigo: procesamiento_inbox_invalido
- descripcion: el procesamiento del inbox no es válido por estado, contexto o consistencia técnica.
- tipo: validacion
- aplica_a: inbox
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-017 — orden_logico_invalido
- codigo: orden_logico_invalido
- descripcion: no es válido procesar el mensaje actual porque falta una secuencia previa necesaria para preservar consistencia.
- tipo: integridad
- aplica_a: inbox
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-TEC-018 — emision_outbox_invalida
- codigo: emision_outbox_invalida
- descripcion: no es válida la emisión del registro de outbox en el estado técnico actual.
- tipo: validacion
- aplica_a: outbox
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-TEC-019 — confirmacion_procesamiento_invalida
- codigo: confirmacion_procesamiento_invalida
- descripcion: la confirmación de procesamiento no es válida para el registro técnico indicado.
- tipo: validacion
- aplica_a: inbox
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de idempotencia y reintentos

### ERR-TEC-020 — op_id_invalido
- codigo: op_id_invalido
- descripcion: el op_id informado no cumple las reglas de identidad operativa requeridas.
- tipo: validacion
- aplica_a: op_id
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-021 — op_id_duplicado
- codigo: op_id_duplicado
- descripcion: la operación ya fue registrada con el mismo op_id y mismo contenido.
- tipo: concurrencia
- aplica_a: op_id, operacion_distribuida
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-TEC-022 — op_id_duplicado_con_payload_distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el op_id ya existe asociado a un contenido distinto y genera conflicto técnico.
- tipo: concurrencia
- aplica_a: op_id, operacion_distribuida
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-023 — reintento_invalido
- codigo: reintento_invalido
- descripcion: el reintento no cumple las condiciones técnicas necesarias para ejecutarse de forma consistente.
- tipo: validacion
- aplica_a: operacion_distribuida, sincronizacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-024 — operacion_ya_ejecutada
- codigo: operacion_ya_ejecutada
- descripcion: la operación ya fue ejecutada correctamente y no debe volver a producir efecto técnico.
- tipo: tecnico
- aplica_a: operacion_distribuida, op_id
- origen: CORE-EF
- es_reintento_valido: sí

## E. Errores de locks y concurrencia

### ERR-TEC-025 — lock_logico_activo
- codigo: lock_logico_activo
- descripcion: existe un lock lógico activo incompatible con la operación solicitada.
- tipo: concurrencia
- aplica_a: lock_logico
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-TEC-026 — lock_logico_inexistente
- codigo: lock_logico_inexistente
- descripcion: no existe el lock lógico requerido o referenciado para la operación solicitada.
- tipo: tecnico
- aplica_a: lock_logico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-027 — liberacion_lock_invalida
- codigo: liberacion_lock_invalida
- descripcion: no es válida la liberación del lock lógico en el estado técnico actual.
- tipo: validacion
- aplica_a: lock_logico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-028 — version_esperada_invalida
- codigo: version_esperada_invalida
- descripcion: la versión esperada informada no coincide con la versión vigente del registro.
- tipo: concurrencia
- aplica_a: version_registro
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-029 — conflicto_concurrencia
- codigo: conflicto_concurrencia
- descripcion: se detectó un conflicto de concurrencia incompatible con la operación técnica solicitada.
- tipo: concurrencia
- aplica_a: operacion_distribuida, lock_logico, version_registro
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-TEC-030 — overwrite_no_permitido
- codigo: overwrite_no_permitido
- descripcion: no se permite sobrescribir silenciosamente un estado técnico versionado o concurrente.
- tipo: integridad
- aplica_a: version_registro
- origen: CORE-EF
- es_reintento_valido: no

## F. Errores de conflictos técnicos

### ERR-TEC-031 — conflicto_tecnico_no_encontrado
- codigo: conflicto_tecnico_no_encontrado
- descripcion: el conflicto técnico indicado no existe o no está disponible.
- tipo: tecnico
- aplica_a: conflicto_tecnico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-032 — conflicto_tecnico_detectado
- codigo: conflicto_tecnico_detectado
- descripcion: se detectó un conflicto técnico que impide continuar el procesamiento automático.
- tipo: tecnico
- aplica_a: conflicto_tecnico
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-033 — conflicto_no_resoluble_automaticamente
- codigo: conflicto_no_resoluble_automaticamente
- descripcion: el conflicto detectado no puede resolverse automáticamente con las políticas vigentes.
- tipo: tecnico
- aplica_a: conflicto_tecnico
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-034 — resolucion_conflicto_invalida
- codigo: resolucion_conflicto_invalida
- descripcion: la resolución aplicada no es válida para el tipo o estado del conflicto técnico.
- tipo: validacion
- aplica_a: conflicto_tecnico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-035 — escalamiento_conflicto_invalido
- codigo: escalamiento_conflicto_invalido
- descripcion: no es válido escalar el conflicto técnico en el estado actual del proceso.
- tipo: validacion
- aplica_a: conflicto_tecnico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-036 — merge_silencioso_no_permitido
- codigo: merge_silencioso_no_permitido
- descripcion: no está permitido resolver el conflicto mediante merge silencioso por defecto.
- tipo: integridad
- aplica_a: conflicto_tecnico
- origen: CORE-EF
- es_reintento_valido: no

## G. Errores de consultas técnicas

### ERR-TEC-037 — criterio_consulta_tecnica_invalido
- codigo: criterio_consulta_tecnica_invalido
- descripcion: los criterios de consulta técnica informados no son válidos.
- tipo: validacion
- aplica_a: consultas tecnicas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-038 — trazabilidad_tecnica_no_disponible
- codigo: trazabilidad_tecnica_no_disponible
- descripcion: no se encuentra disponible la trazabilidad técnica solicitada para el contexto indicado.
- tipo: tecnico
- aplica_a: consultas tecnicas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-039 — historico_tecnico_inconsistente
- codigo: historico_tecnico_inconsistente
- descripcion: el histórico técnico presenta inconsistencias que impiden su reconstrucción confiable.
- tipo: integridad
- aplica_a: consultas tecnicas
- origen: DEV-SRV
- es_reintento_valido: no

## H. Errores transversales del dominio técnico

### ERR-TEC-040 — inconsistencia_tecnica
- codigo: inconsistencia_tecnica
- descripcion: se detectó una inconsistencia técnica interna que impide completar la operación.
- tipo: integridad
- aplica_a: dominio_tecnico
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-TEC-041 — integridad_tecnica_invalida
- codigo: integridad_tecnica_invalida
- descripcion: existe una inconsistencia de integridad entre estructuras técnicas relacionadas.
- tipo: integridad
- aplica_a: dominio_tecnico
- origen: SQL
- es_reintento_valido: no
- observaciones: deriva de persistencia o controles técnicos concretos del modelo real.

### ERR-TEC-042 — recurso_tecnico_bloqueado
- codigo: recurso_tecnico_bloqueado
- descripcion: el recurso técnico requerido se encuentra bloqueado para la operación actual.
- tipo: concurrencia
- aplica_a: dominio_tecnico
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-TEC-043 — secuencia_tecnica_invalida
- codigo: secuencia_tecnica_invalida
- descripcion: el orden técnico de ejecución o procesamiento no es válido para el contexto actual.
- tipo: integridad
- aplica_a: dominio_tecnico
- origen: CORE-EF
- es_reintento_valido: no

### ERR-TEC-044 — estado_tecnico_incompatible
- codigo: estado_tecnico_incompatible
- descripcion: el estado técnico actual no es compatible con la operación solicitada.
- tipo: validacion
- aplica_a: dominio_tecnico
- origen: DEV-SRV
- es_reintento_valido: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Técnico.
- No reemplaza al CAT-CU maestro.
- Los errores aquí listados se usan como apoyo a implementación, validación y manejo consistente de respuestas backend.
- Debe mantenerse alineado con CU-TEC, RN-TEC, CORE-EF-001 y CORE-EF-VALIDACION.
