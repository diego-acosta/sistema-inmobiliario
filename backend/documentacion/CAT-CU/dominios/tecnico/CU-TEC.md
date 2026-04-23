# CU-TEC — Casos de uso del dominio Técnico

## Objetivo
Definir los casos de uso del dominio Técnico.

## Alcance
Incluye sincronización, trazabilidad técnica, outbox/inbox, idempotencia, locks, conflictos y mantenimiento de consistencia distribuida.

---

## A. Gestión de operaciones distribuidas

### CU-TEC-001 — Registro de operación distribuida
- tipo: write
- objetivo: Registrar una operación distribuida para su trazabilidad técnica y control de ejecución.
- entidades: operacion_distribuida
- criticidad: crítica

### CU-TEC-002 — Validación de operación distribuida
- tipo: write
- objetivo: Validar una operación distribuida antes de su procesamiento técnico dentro del circuito permitido.
- entidades: operacion_distribuida
- criticidad: crítica

### CU-TEC-003 — Rechazo de operación distribuida inválida
- tipo: write
- objetivo: Rechazar técnicamente una operación distribuida inválida preservando trazabilidad del motivo.
- entidades: operacion_distribuida
- criticidad: crítica

### CU-TEC-004 — Cierre técnico de operación distribuida
- tipo: write
- objetivo: Cerrar técnicamente una operación distribuida al finalizar su circuito de procesamiento.
- entidades: operacion_distribuida
- criticidad: alta

## B. Gestión de sincronización

### CU-TEC-005 — Inicio de sincronización
- tipo: write
- objetivo: Iniciar un proceso de sincronización entre instalaciones dentro del marco técnico definido.
- entidades: sincronizacion
- criticidad: crítica

### CU-TEC-006 — Recepción de cambio remoto
- tipo: write
- objetivo: Registrar la recepción de un cambio remoto para su posterior validación y procesamiento.
- entidades: sincronizacion, cambio_remoto
- criticidad: crítica

### CU-TEC-007 — Aplicación de cambio remoto
- tipo: write
- objetivo: Aplicar un cambio remoto válido preservando versionado, trazabilidad e integridad técnica.
- entidades: sincronizacion, cambio_remoto
- criticidad: crítica

### CU-TEC-008 — Confirmación de sincronización
- tipo: write
- objetivo: Confirmar técnicamente una sincronización completada dentro del circuito permitido.
- entidades: sincronizacion
- criticidad: alta

### CU-TEC-009 — Reintento de sincronización fallida
- tipo: write
- objetivo: Reintentar una sincronización fallida bajo condiciones técnicas controladas.
- entidades: sincronizacion
- criticidad: alta

## C. Gestión de inbox y outbox

### CU-TEC-010 — Registro en outbox
- tipo: write
- objetivo: Registrar en outbox un evento o cambio distribuible asociado a una operación sincronizable.
- entidades: outbox
- criticidad: crítica

### CU-TEC-011 — Emisión desde outbox
- tipo: write
- objetivo: Emitir técnicamente un registro pendiente desde outbox dentro del circuito de sincronización.
- entidades: outbox
- criticidad: alta

### CU-TEC-012 — Registro en inbox
- tipo: write
- objetivo: Registrar en inbox un cambio recibido para su procesamiento técnico controlado.
- entidades: inbox
- criticidad: crítica

### CU-TEC-013 — Procesamiento de inbox
- tipo: write
- objetivo: Procesar un registro de inbox respetando orden lógico, idempotencia y consistencia distribuida.
- entidades: inbox
- criticidad: crítica

### CU-TEC-014 — Confirmación de procesamiento técnico
- tipo: write
- objetivo: Confirmar el procesamiento técnico de un registro recibido dentro del circuito de inbox.
- entidades: inbox
- criticidad: alta

## D. Gestión de idempotencia y reintentos

### CU-TEC-015 — Validación de op_id
- tipo: write
- objetivo: Validar un op_id para determinar unicidad, reintento válido o conflicto técnico.
- entidades: operacion_distribuida, op_id
- criticidad: crítica

### CU-TEC-016 — Detección de operación duplicada
- tipo: write
- objetivo: Detectar una operación duplicada dentro de la estrategia técnica de idempotencia.
- entidades: operacion_distribuida, op_id
- criticidad: crítica

### CU-TEC-017 — Reintento técnico controlado
- tipo: write
- objetivo: Ejecutar un reintento técnico controlado de una operación distribuida sin perder consistencia.
- entidades: operacion_distribuida, op_id
- criticidad: alta

### CU-TEC-018 — Rechazo por conflicto de op_id
- tipo: write
- objetivo: Rechazar una operación cuando el op_id presente conflicto técnico con el registro previo.
- entidades: operacion_distribuida, op_id
- criticidad: crítica

## E. Gestión de locks y concurrencia

### CU-TEC-019 — Toma de lock lógico
- tipo: write
- objetivo: Tomar un lock lógico sobre un recurso técnico o agregado afectado para prevenir conflictos incompatibles.
- entidades: lock_logico
- criticidad: crítica

### CU-TEC-020 — Liberación de lock lógico
- tipo: write
- objetivo: Liberar un lock lógico previamente tomado dentro del circuito técnico permitido.
- entidades: lock_logico
- criticidad: alta

### CU-TEC-021 — Rechazo por lock activo
- tipo: write
- objetivo: Rechazar técnicamente una operación cuando exista un lock lógico activo incompatible.
- entidades: lock_logico
- criticidad: alta

### CU-TEC-022 — Validación de versión esperada
- tipo: write
- objetivo: Validar la versión esperada de un registro sincronizable antes de aplicar un cambio técnico.
- entidades: version_registro
- criticidad: crítica

## F. Gestión de conflictos técnicos

### CU-TEC-023 — Detección de conflicto técnico
- tipo: write
- objetivo: Detectar conflictos técnicos de sincronización, concurrencia o idempotencia.
- entidades: conflicto_tecnico
- criticidad: crítica

### CU-TEC-024 — Registro de conflicto de sincronización
- tipo: write
- objetivo: Registrar un conflicto de sincronización preservando su contexto y trazabilidad técnica.
- entidades: conflicto_tecnico, sincronizacion
- criticidad: alta

### CU-TEC-025 — Resolución técnica de conflicto
- tipo: write
- objetivo: Resolver técnicamente un conflicto cuando exista una política explícita y permitida para hacerlo.
- entidades: conflicto_tecnico
- criticidad: alta

### CU-TEC-026 — Escalamiento de conflicto no resoluble automáticamente
- tipo: write
- objetivo: Escalar un conflicto técnico cuando no pueda resolverse de forma automática dentro del circuito definido.
- entidades: conflicto_tecnico
- criticidad: crítica

## G. Consultas técnicas

### CU-TEC-027 — Consulta de operación distribuida
- tipo: read
- objetivo: Consultar el detalle técnico de una operación distribuida determinada.
- entidades: operacion_distribuida
- criticidad: media

### CU-TEC-028 — Consulta de outbox
- tipo: read
- objetivo: Consultar registros de outbox según su estado técnico y criterio de emisión.
- entidades: outbox
- criticidad: media

### CU-TEC-029 — Consulta de inbox
- tipo: read
- objetivo: Consultar registros de inbox y su estado de procesamiento técnico.
- entidades: inbox
- criticidad: media

### CU-TEC-030 — Consulta de locks lógicos
- tipo: read
- objetivo: Consultar locks lógicos vigentes o históricos sobre recursos técnicos.
- entidades: lock_logico
- criticidad: media

### CU-TEC-031 — Consulta de conflictos técnicos
- tipo: read
- objetivo: Consultar conflictos técnicos detectados y su estado de resolución o escalamiento.
- entidades: conflicto_tecnico
- criticidad: media

### CU-TEC-032 — Consulta de trazabilidad técnica
- tipo: read
- objetivo: Consultar la trazabilidad técnica de operaciones distribuidas, sincronizaciones y eventos de soporte.
- entidades: operacion_distribuida, sincronizacion, inbox, outbox
- criticidad: media

### CU-TEC-033 — Consulta de histórico técnico
- tipo: read
- objetivo: Consultar la evolución histórica de operaciones técnicas, conflictos, locks y sincronizaciones.
- entidades: operacion_distribuida, sincronizacion, lock_logico, conflicto_tecnico
- criticidad: media

---

## Reglas

1. No ejecutar lógica funcional de negocio.
2. No redefinir semántica de dominios funcionales.
3. No reemplazar CORE-EF, sino operacionalizarlo.
4. Mantener trazabilidad completa de operaciones distribuidas.
5. Toda lógica técnica debe preservar idempotencia, versionado y consistencia.
6. Los conflictos técnicos no deben resolverse con merge silencioso por defecto.

---

## Notas

- El dominio Técnico soporta la operación distribuida del sistema.
- No define negocio, pero garantiza consistencia de ejecución entre instalaciones.
- Debe mantenerse alineado con CORE-EF y con los dominios funcionales.
- Inbox, outbox, op_id, versionado, locks y conflictos son parte central de este dominio.
- Este dominio no reemplaza seguridad administrativa ni operación funcional.
- Las entidades técnicas mencionadas en este documento (operación distribuida, sincronización, inbox, outbox, lock, conflicto, versión, etc.) representan conceptos del modelo técnico definido en CORE-EF.
- La implementación física concreta de estas estructuras (tablas, colas, logs u otras) puede variar y debe alinearse con la arquitectura real del sistema.
- Este documento no define por sí mismo el modelo físico de persistencia técnica, sino las capacidades necesarias para garantizar consistencia distribuida.
