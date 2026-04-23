# EVT-TEC — Eventos del dominio Técnico

## Objetivo
Definir los eventos observables del dominio Técnico como apoyo a implementación backend, trazabilidad y operación distribuida.

## Alcance del dominio
Incluye operaciones distribuidas, sincronización, inbox y outbox, idempotencia, reintentos, locks lógicos, concurrencia y conflictos técnicos.

---

## A. Eventos de operaciones distribuidas

### EVT-TEC-001 — Operación distribuida registrada
- codigo: operacion_distribuida_registrada
- descripcion: se registró una operación distribuida dentro del circuito técnico.
- origen_principal: SRV-TEC-001
- entidad_principal: operacion_distribuida
- tipo_evento: tecnico
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí

### EVT-TEC-002 — Operación distribuida validada
- codigo: operacion_distribuida_validada
- descripcion: una operación distribuida fue validada técnicamente para su procesamiento.
- origen_principal: SRV-TEC-001
- entidad_principal: operacion_distribuida
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-003 — Operación distribuida rechazada
- codigo: operacion_distribuida_rechazada
- descripcion: una operación distribuida fue rechazada por validación o consistencia técnica.
- origen_principal: SRV-TEC-001
- entidad_principal: operacion_distribuida
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-004 — Operación distribuida cerrada
- codigo: operacion_distribuida_cerrada
- descripcion: se cerró técnicamente una operación distribuida al finalizar su circuito.
- origen_principal: SRV-TEC-001
- entidad_principal: operacion_distribuida
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

## B. Eventos de sincronización

### EVT-TEC-005 — Sincronización iniciada
- codigo: sincronizacion_iniciada
- descripcion: se inició un proceso de sincronización entre instalaciones.
- origen_principal: SRV-TEC-002
- entidad_principal: sincronizacion
- tipo_evento: tecnico
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-TEC-006 — Cambio remoto recibido
- codigo: cambio_remoto_recibido
- descripcion: se recibió un cambio remoto para validación y procesamiento técnico.
- origen_principal: SRV-TEC-002
- entidad_principal: cambio_remoto
- tipo_evento: tecnico
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-TEC-007 — Cambio remoto aplicado
- codigo: cambio_remoto_aplicado
- descripcion: se aplicó un cambio remoto válido respetando las reglas técnicas vigentes.
- origen_principal: SRV-TEC-002
- entidad_principal: cambio_remoto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-TEC-008 — Sincronización confirmada
- codigo: sincronizacion_confirmada
- descripcion: se confirmó técnicamente una sincronización completada.
- origen_principal: SRV-TEC-002
- entidad_principal: sincronizacion
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-009 — Sincronización reintentada
- codigo: sincronizacion_reintentada
- descripcion: se ejecutó un reintento controlado de una sincronización fallida.
- origen_principal: SRV-TEC-002
- entidad_principal: sincronizacion
- tipo_evento: tecnico
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de inbox y outbox

### EVT-TEC-010 — Outbox registrado
- codigo: outbox_registrado
- descripcion: se registró un cambio o evento distribuible en outbox.
- origen_principal: SRV-TEC-003
- entidad_principal: outbox
- tipo_evento: tecnico
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí

### EVT-TEC-011 — Outbox emitido
- codigo: outbox_emitido
- descripcion: se emitió un registro pendiente desde outbox dentro del circuito técnico.
- origen_principal: SRV-TEC-003
- entidad_principal: outbox
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-TEC-012 — Inbox registrado
- codigo: inbox_registrado
- descripcion: se registró un mensaje recibido en inbox para su procesamiento técnico.
- origen_principal: SRV-TEC-003
- entidad_principal: inbox
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-013 — Inbox procesado
- codigo: inbox_procesado
- descripcion: se procesó un registro de inbox respetando orden lógico e idempotencia.
- origen_principal: SRV-TEC-003
- entidad_principal: inbox
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-014 — Procesamiento técnico confirmado
- codigo: procesamiento_tecnico_confirmado
- descripcion: se confirmó el procesamiento técnico de un mensaje registrado en inbox.
- origen_principal: SRV-TEC-003
- entidad_principal: inbox
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

## D. Eventos de idempotencia y reintentos

### EVT-TEC-015 — op_id validado
- codigo: op_id_validado
- descripcion: se validó un op_id dentro del control técnico de idempotencia.
- origen_principal: SRV-TEC-004
- entidad_principal: op_id
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-016 — Operación duplicada detectada
- codigo: operacion_duplicada_detectada
- descripcion: se detectó una operación duplicada dentro de la estrategia técnica de idempotencia.
- origen_principal: SRV-TEC-004
- entidad_principal: operacion_distribuida
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-017 — Reintento técnico ejecutado
- codigo: reintento_tecnico_ejecutado
- descripcion: se ejecutó un reintento técnico controlado sobre una operación distribuida.
- origen_principal: SRV-TEC-004
- entidad_principal: operacion_distribuida
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-018 — Conflicto de op_id detectado
- codigo: conflicto_op_id_detectado
- descripcion: se detectó un conflicto por reutilización incompatible de op_id.
- origen_principal: SRV-TEC-004
- entidad_principal: op_id
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

## E. Eventos de locks y concurrencia

### EVT-TEC-019 — Lock lógico tomado
- codigo: lock_logico_tomado
- descripcion: se tomó un lock lógico sobre un recurso técnico o agregado afectado.
- origen_principal: SRV-TEC-005
- entidad_principal: lock_logico
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-020 — Lock lógico liberado
- codigo: lock_logico_liberado
- descripcion: se liberó un lock lógico previamente tomado.
- origen_principal: SRV-TEC-005
- entidad_principal: lock_logico
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-021 — Operación rechazada por lock
- codigo: operacion_rechazada_por_lock
- descripcion: una operación fue rechazada por la existencia de un lock lógico activo incompatible.
- origen_principal: SRV-TEC-005
- entidad_principal: lock_logico
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-022 — Versión esperada validada
- codigo: version_esperada_validada
- descripcion: se validó la versión esperada de un registro antes de aplicar un cambio técnico.
- origen_principal: SRV-TEC-005
- entidad_principal: version_registro
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-023 — Conflicto de concurrencia detectado
- codigo: conflicto_concurrencia_detectado
- descripcion: se detectó un conflicto de concurrencia incompatible con la operación técnica en curso.
- origen_principal: SRV-TEC-005
- entidad_principal: lock_logico
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí
- observaciones: puede involucrar también versionado u otros controles de concurrencia del dominio técnico.

## F. Eventos de conflictos técnicos

### EVT-TEC-024 — Conflicto técnico detectado
- codigo: conflicto_tecnico_detectado
- descripcion: se detectó un conflicto técnico de sincronización, concurrencia o idempotencia.
- origen_principal: SRV-TEC-006
- entidad_principal: conflicto_tecnico
- tipo_evento: tecnico
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-025 — Conflicto de sincronización registrado
- codigo: conflicto_sincronizacion_registrado
- descripcion: se registró un conflicto de sincronización con su contexto técnico asociado.
- origen_principal: SRV-TEC-006
- entidad_principal: conflicto_tecnico
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-026 — Conflicto técnico resuelto
- codigo: conflicto_tecnico_resuelto
- descripcion: se resolvió un conflicto técnico bajo una política explícita permitida.
- origen_principal: SRV-TEC-006
- entidad_principal: conflicto_tecnico
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad: sí

### EVT-TEC-027 — Conflicto técnico escalado
- codigo: conflicto_tecnico_escalado
- descripcion: se escaló un conflicto técnico no resoluble automáticamente.
- origen_principal: SRV-TEC-006
- entidad_principal: conflicto_tecnico
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí

## G. Notas de compatibilidad transversal

- El dominio Técnico soporta operaciones distribuidas y no reemplaza dominios funcionales.
- Los eventos técnicos pueden ser consumidos por monitoreo, auditoría o infraestructura de soporte.
- Los writes sincronizables del dominio técnico deben respetar op_id, versionado y trazabilidad según CORE-EF.
- Los eventos técnicos no sustituyen eventos funcionales de negocio.

## Notas
- Este catálogo deriva del DEV-SRV del dominio Técnico.
- No reemplaza al CAT-CU maestro.
- Los eventos aquí listados se usan como apoyo a implementación, auditoría, historización y trazabilidad backend.
- Debe mantenerse alineado con CU-TEC, RN-TEC, ERR-TEC, CORE-EF-001 y CORE-EF-VALIDACION.
