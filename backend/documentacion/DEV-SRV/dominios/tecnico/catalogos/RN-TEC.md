# RN-TEC — Reglas del dominio Técnico

## Objetivo
Definir las reglas técnicas del dominio Técnico como apoyo a implementación backend y consistencia distribuida.

## Alcance del dominio
Incluye operaciones distribuidas, sincronización, inbox y outbox, idempotencia, reintentos, locks lógicos, concurrencia, conflictos técnicos y consultas de trazabilidad técnica.

---

## A. Reglas de operaciones distribuidas

### RN-TEC-001 — Trazabilidad obligatoria de operación distribuida
- descripcion: toda operación distribuida debe ser trazable durante su ciclo técnico de procesamiento.
- aplica_a: operacion_distribuida
- origen_principal: CORE-EF

### RN-TEC-002 — Identidad operativa consistente
- descripcion: una operación distribuida debe tener identidad operativa consistente cuando participe como unidad identificable de procesamiento.
- aplica_a: operacion_distribuida, op_id
- origen_principal: CORE-EF

### RN-TEC-003 — Cierre técnico con preservación de historial
- descripcion: el cierre técnico de una operación distribuida no debe perder historial de ejecución ni contexto relevante.
- aplica_a: operacion_distribuida
- origen_principal: DEV-SRV

### RN-TEC-004 — Rechazo técnico con trazabilidad
- descripcion: una operación inválida debe poder rechazarse sin perder trazabilidad del motivo ni del contexto técnico.
- aplica_a: operacion_distribuida
- origen_principal: DEV-SRV

## B. Reglas de sincronización

### RN-TEC-005 — Consistencia en sincronización entre instalaciones
- descripcion: la sincronización entre instalaciones debe preservar consistencia del estado compartido y evitar sobrescrituras implícitas.
- aplica_a: sincronizacion
- origen_principal: CORE-EF

### RN-TEC-006 — Recepción sin aplicación automática
- descripcion: la recepción de cambios remotos no implica su aplicación automática y debe mediar validación técnica previa.
- aplica_a: sincronizacion, cambio_remoto, inbox
- origen_principal: CORE-EF

### RN-TEC-007 — Aplicación remota con versionado y conflicto
- descripcion: la aplicación de cambios remotos debe respetar versionado, validación de estado y reglas explícitas de conflicto.
- aplica_a: sincronizacion, cambio_remoto, version_registro
- origen_principal: CORE-EF

### RN-TEC-008 — Reintento controlado de sincronización fallida
- descripcion: una sincronización fallida puede reintentarse solo bajo condiciones controladas que preserven consistencia técnica.
- aplica_a: sincronizacion
- origen_principal: DEV-SRV

### RN-TEC-009 — Confirmación sin ocultamiento de conflicto
- descripcion: la confirmación de sincronización no debe ocultar conflictos, rechazos o inconsistencias detectadas previamente.
- aplica_a: sincronizacion
- origen_principal: DEV-SRV

## C. Reglas de inbox y outbox

### RN-TEC-010 — Registro de cambio distribuible en outbox
- descripcion: todo cambio distribuible debe poder registrarse en outbox cuando el flujo técnico de sincronización lo requiera.
- aplica_a: outbox
- origen_principal: CORE-EF

### RN-TEC-011 — Trazabilidad técnica de inbox y outbox
- descripcion: inbox y outbox deben preservar trazabilidad técnica suficiente de emisión, recepción y procesamiento.
- aplica_a: inbox, outbox
- origen_principal: CORE-EF

### RN-TEC-012 — Orden lógico de procesamiento
- descripcion: el procesamiento de inbox debe respetar orden lógico cuando exista dependencia temporal o causal entre mensajes.
- aplica_a: inbox
- origen_principal: CORE-EF
- observaciones: aplica cuando la consistencia temporal del flujo lo requiere.

### RN-TEC-013 — Conservación del mensaje recibido
- descripcion: el procesamiento técnico no debe perder registro del mensaje recibido ni de su resultado de tratamiento.
- aplica_a: inbox
- origen_principal: DEV-SRV

### RN-TEC-014 — Confirmación con historial útil
- descripcion: la confirmación de procesamiento no debe eliminar historial útil para trazabilidad, auditoría o diagnóstico técnico.
- aplica_a: inbox
- origen_principal: DEV-SRV

## D. Reglas de idempotencia y reintentos

### RN-TEC-015 — Unicidad de op_id
- descripcion: op_id debe ser único en su contexto operativo para identificar una operación distribuida de forma consistente.
- aplica_a: op_id, operacion_distribuida
- origen_principal: CORE-EF

### RN-TEC-016 — Reintento válido por igualdad de contenido
- descripcion: mismo op_id con mismo contenido implica reintento válido y no debe generar un nuevo efecto técnico.
- aplica_a: op_id, operacion_distribuida
- origen_principal: CORE-EF

### RN-TEC-017 — Conflicto por op_id con contenido distinto
- descripcion: mismo op_id con distinto contenido implica conflicto y no debe tratarse como reintento válido.
- aplica_a: op_id, operacion_distribuida
- origen_principal: CORE-EF

### RN-TEC-018 — No duplicación de efecto técnico
- descripcion: no debe duplicarse el efecto técnico de una operación válida ya registrada o aplicada correctamente.
- aplica_a: operacion_distribuida, op_id
- origen_principal: CORE-EF

### RN-TEC-019 — Reintento con preservación de consistencia
- descripcion: un reintento técnico debe preservar consistencia del estado técnico y respetar la estrategia de idempotencia definida.
- aplica_a: operacion_distribuida, sincronizacion
- origen_principal: DEV-SRV

## E. Reglas de locks y concurrencia

### RN-TEC-020 — Lock lógico solo cuando corresponde
- descripcion: el lock lógico debe aplicarse solo cuando el proceso lo requiera para impedir concurrencia incompatible.
- aplica_a: lock_logico
- origen_principal: CORE-EF

### RN-TEC-021 — Prevención de concurrencia incompatible
- descripcion: el lock debe impedir modificaciones o procesamientos concurrentes incompatibles sobre la entidad, agregado o recurso afectado.
- aplica_a: lock_logico
- origen_principal: CORE-EF

### RN-TEC-022 — Liberación consistente del lock
- descripcion: la liberación del lock debe preservar consistencia del recurso y del circuito técnico asociado.
- aplica_a: lock_logico
- origen_principal: DEV-SRV

### RN-TEC-023 — Validación previa de versión
- descripcion: la validación de versión debe preceder cambios sensibles sobre registros versionados o sincronizables.
- aplica_a: version_registro
- origen_principal: CORE-EF

### RN-TEC-024 — Prohibición de overwrite silencioso
- descripcion: no debe haber overwrite silencioso en procesos versionados o bajo concurrencia relevante.
- aplica_a: version_registro, operacion_distribuida
- origen_principal: CORE-EF

## F. Reglas de conflictos técnicos

### RN-TEC-025 — Detección explícita de conflictos
- descripcion: los conflictos técnicos deben detectarse explícitamente y no inferirse de forma implícita o silenciosa.
- aplica_a: conflicto_tecnico
- origen_principal: CORE-EF

### RN-TEC-026 — Prohibición de merge silencioso
- descripcion: no debe aplicarse merge silencioso por defecto ante conflictos de sincronización, concurrencia o idempotencia.
- aplica_a: conflicto_tecnico
- origen_principal: CORE-EF

### RN-TEC-027 — Resolución solo con política explícita
- descripcion: un conflicto puede resolverse solo si existe una política técnica explícita y permitida para ese caso.
- aplica_a: conflicto_tecnico
- origen_principal: CORE-EF

### RN-TEC-028 — Escalamiento de conflicto no resoluble
- descripcion: un conflicto no resoluble automáticamente debe escalarse sin ocultar su impacto técnico.
- aplica_a: conflicto_tecnico
- origen_principal: DEV-SRV

### RN-TEC-029 — Registro suficiente del contexto de conflicto
- descripcion: el registro del conflicto debe conservar contexto técnico suficiente para análisis, auditoría y resolución.
- aplica_a: conflicto_tecnico
- origen_principal: DEV-SRV

## G. Reglas de consultas técnicas

### RN-TEC-030 — Consultas sin efectos persistentes
- descripcion: las consultas técnicas no generan efectos persistentes ni alteran el estado técnico del sistema.
- aplica_a: consultas tecnicas
- origen_principal: CORE-EF

### RN-TEC-031 — Trazabilidad técnica consultable
- descripcion: la trazabilidad técnica debe poder consultarse sobre operaciones distribuidas, sincronizaciones, locks y conflictos.
- aplica_a: consultas tecnicas
- origen_principal: DEV-SRV

### RN-TEC-032 — Conservación de secuencia útil en histórico técnico
- descripcion: el histórico técnico debe conservar la secuencia útil de eventos y estados para reconstrucción operativa.
- aplica_a: consultas tecnicas
- origen_principal: DEV-SRV

### RN-TEC-033 — Consultas sin alteración de ejecución
- descripcion: las consultas técnicas no deben alterar sincronización, procesamiento, locks ni ejecución distribuida.
- aplica_a: consultas tecnicas
- origen_principal: CORE-EF

## Notas
- Este catálogo deriva del DEV-SRV del dominio Técnico.
- No reemplaza al CAT-CU maestro.
- Las reglas aquí listadas se usan como apoyo a implementación y validación backend.
- Debe mantenerse alineado con CORE-EF-001, CORE-EF-VALIDACION y con la arquitectura distribuida real del sistema.
