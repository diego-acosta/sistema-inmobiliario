# CU-TEC — Casos de uso del dominio Técnico

## Objetivo
Definir los casos de uso del dominio Técnico orientados a implementación backend.

## Alcance del dominio
Incluye operaciones distribuidas, sincronización, inbox y outbox, idempotencia, locks, concurrencia, conflictos técnicos y consultas de soporte a consistencia distribuida.

## Bloques del dominio
- Operaciones distribuidas
- Sincronización
- Inbox y outbox
- Idempotencia y reintentos
- Locks y concurrencia
- Conflictos técnicos
- Consultas técnicas

---

## A. Operaciones distribuidas

### CU-TEC-001 — Registro de operación distribuida
- servicio_origen: SRV-TEC-001
- tipo: write
- objetivo: Registrar una operación distribuida para su trazabilidad técnica y control de ejecución.
- entidades: operacion_distribuida, op_id
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-002 — Validación de operación distribuida
- servicio_origen: SRV-TEC-001
- tipo: write
- objetivo: Validar una operación distribuida antes de su procesamiento técnico dentro del circuito permitido.
- entidades: operacion_distribuida, op_id
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-003 — Rechazo de operación distribuida inválida
- servicio_origen: SRV-TEC-001
- tipo: write
- objetivo: Rechazar técnicamente una operación distribuida inválida preservando trazabilidad del motivo.
- entidades: operacion_distribuida, op_id
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-004 — Cierre técnico de operación distribuida
- servicio_origen: SRV-TEC-001
- tipo: write
- objetivo: Cerrar técnicamente una operación distribuida al finalizar su circuito de procesamiento.
- entidades: operacion_distribuida
- criticidad: alta
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## B. Sincronización

### CU-TEC-005 — Inicio de sincronización
- servicio_origen: SRV-TEC-002
- tipo: write
- objetivo: Iniciar un proceso de sincronización entre instalaciones dentro del marco técnico definido.
- entidades: sincronizacion
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-006 — Recepción de cambio remoto
- servicio_origen: SRV-TEC-002
- tipo: write
- objetivo: Registrar la recepción de un cambio remoto para su posterior validación y procesamiento.
- entidades: sincronizacion, cambio_remoto, inbox
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-007 — Aplicación de cambio remoto
- servicio_origen: SRV-TEC-002
- tipo: write
- objetivo: Aplicar un cambio remoto válido preservando versionado, trazabilidad e integridad técnica.
- entidades: sincronizacion, cambio_remoto, version_registro
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-008 — Confirmación de sincronización
- servicio_origen: SRV-TEC-002
- tipo: write
- objetivo: Confirmar técnicamente una sincronización completada dentro del circuito permitido.
- entidades: sincronizacion
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-009 — Reintento de sincronización fallida
- servicio_origen: SRV-TEC-002
- tipo: write
- objetivo: Reintentar una sincronización fallida bajo condiciones técnicas controladas.
- entidades: sincronizacion, op_id
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## C. Inbox y outbox

### CU-TEC-010 — Registro en outbox
- servicio_origen: SRV-TEC-003
- tipo: write
- objetivo: Registrar en outbox un evento o cambio distribuible asociado a una operación sincronizable.
- entidades: outbox, op_id
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-TEC-011 — Emisión desde outbox
- servicio_origen: SRV-TEC-003
- tipo: write
- objetivo: Emitir técnicamente un registro pendiente desde outbox dentro del circuito de sincronización.
- entidades: outbox
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-TEC-012 — Registro en inbox
- servicio_origen: SRV-TEC-003
- tipo: write
- objetivo: Registrar en inbox un cambio recibido para su procesamiento técnico controlado.
- entidades: inbox, op_id
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-013 — Procesamiento de inbox
- servicio_origen: SRV-TEC-003
- tipo: write
- objetivo: Procesar un registro de inbox respetando orden lógico, idempotencia y consistencia distribuida.
- entidades: inbox, operacion_distribuida, lock_logico
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-014 — Confirmación de procesamiento técnico
- servicio_origen: SRV-TEC-003
- tipo: write
- objetivo: Confirmar el procesamiento técnico de un registro recibido dentro del circuito de inbox.
- entidades: inbox
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## D. Idempotencia y reintentos

### CU-TEC-015 — Validación de op_id
- servicio_origen: SRV-TEC-004
- tipo: write
- objetivo: Validar un op_id para determinar unicidad, reintento válido o conflicto técnico.
- entidades: op_id, operacion_distribuida
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-016 — Detección de operación duplicada
- servicio_origen: SRV-TEC-004
- tipo: write
- objetivo: Detectar una operación duplicada dentro de la estrategia técnica de idempotencia.
- entidades: op_id, operacion_distribuida
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-017 — Reintento técnico controlado
- servicio_origen: SRV-TEC-004
- tipo: write
- objetivo: Ejecutar un reintento técnico controlado de una operación distribuida sin perder consistencia.
- entidades: operacion_distribuida, op_id
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-018 — Rechazo por conflicto de op_id
- servicio_origen: SRV-TEC-004
- tipo: write
- objetivo: Rechazar una operación cuando el op_id presente conflicto técnico con el registro previo.
- entidades: op_id, operacion_distribuida
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## E. Locks y concurrencia

### CU-TEC-019 — Toma de lock lógico
- servicio_origen: SRV-TEC-005
- tipo: write
- objetivo: Tomar un lock lógico sobre un recurso técnico o agregado afectado para prevenir conflictos incompatibles.
- entidades: lock_logico
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-020 — Liberación de lock lógico
- servicio_origen: SRV-TEC-005
- tipo: write
- objetivo: Liberar un lock lógico previamente tomado dentro del circuito técnico permitido.
- entidades: lock_logico
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-021 — Rechazo por lock activo
- servicio_origen: SRV-TEC-005
- tipo: write
- objetivo: Rechazar técnicamente una operación cuando exista un lock lógico activo incompatible.
- entidades: lock_logico, operacion_distribuida
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-022 — Validación de versión esperada
- servicio_origen: SRV-TEC-005
- tipo: write
- objetivo: Validar la versión esperada de un registro sincronizable antes de aplicar un cambio técnico.
- entidades: version_registro, operacion_distribuida
- criticidad: crítica
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## F. Conflictos técnicos

### CU-TEC-023 — Detección de conflicto técnico
- servicio_origen: SRV-TEC-006
- tipo: write
- objetivo: Detectar conflictos técnicos de sincronización, concurrencia o idempotencia.
- entidades: conflicto_tecnico, operacion_distribuida
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-024 — Registro de conflicto de sincronización
- servicio_origen: SRV-TEC-006
- tipo: write
- objetivo: Registrar un conflicto de sincronización preservando su contexto y trazabilidad técnica.
- entidades: conflicto_tecnico, sincronizacion
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-025 — Resolución técnica de conflicto
- servicio_origen: SRV-TEC-006
- tipo: write
- objetivo: Resolver técnicamente un conflicto cuando exista una política explícita y permitida para hacerlo.
- entidades: conflicto_tecnico, version_registro
- criticidad: alta
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-TEC-026 — Escalamiento de conflicto no resoluble automáticamente
- servicio_origen: SRV-TEC-006
- tipo: write
- objetivo: Escalar un conflicto técnico cuando no pueda resolverse de forma automática dentro del circuito definido.
- entidades: conflicto_tecnico
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: sí

## G. Consultas técnicas

### CU-TEC-027 — Consulta de operación distribuida
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar el detalle técnico de una operación distribuida determinada.
- entidades: operacion_distribuida
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-028 — Consulta de outbox
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar registros de outbox según su estado técnico y criterio de emisión.
- entidades: outbox
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-029 — Consulta de inbox
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar registros de inbox y su estado de procesamiento técnico.
- entidades: inbox
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-030 — Consulta de locks lógicos
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar locks lógicos vigentes o históricos sobre recursos técnicos.
- entidades: lock_logico
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-031 — Consulta de conflictos técnicos
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar conflictos técnicos detectados y su estado de resolución o escalamiento.
- entidades: conflicto_tecnico
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-032 — Consulta de trazabilidad técnica
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar la trazabilidad técnica de operaciones distribuidas, sincronizaciones y eventos de soporte.
- entidades: operacion_distribuida, sincronizacion, inbox, outbox
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-TEC-033 — Consulta de histórico técnico
- servicio_origen: SRV-TEC-007
- tipo: read
- objetivo: Consultar la evolución histórica de operaciones técnicas, conflictos, locks y sincronizaciones.
- entidades: operacion_distribuida, sincronizacion, lock_logico, conflicto_tecnico
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Técnico.
- No reemplaza al CAT-CU maestro.
- Se utiliza como apoyo a implementación backend.
- Debe alinearse con CORE-EF-001, CORE-EF-VALIDACION y con la arquitectura distribuida real del sistema.
