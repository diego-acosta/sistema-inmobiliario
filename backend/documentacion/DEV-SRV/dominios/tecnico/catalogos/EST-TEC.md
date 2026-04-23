# EST-TEC — Estados del dominio Técnico

## Objetivo
Definir los estados relevantes del dominio Técnico como apoyo a implementación backend, consistencia distribuida y trazabilidad.

## Alcance del dominio
Incluye operaciones distribuidas, sincronización, inbox y outbox, idempotencia, reintentos, locks lógicos, concurrencia, conflictos técnicos y estados operativos transversales.

---

## A. Estados de operaciones distribuidas

### EST-TEC-001 — Registrada
- codigo: registrada
- tipo: entidad
- aplica_a: operacion_distribuida
- descripcion: la operación distribuida fue registrada y quedó disponible para su circuito técnico.
- estado_inicial: sí
- estado_final: no

### EST-TEC-002 — Validada
- codigo: validada
- tipo: entidad
- aplica_a: operacion_distribuida
- descripcion: la operación distribuida superó las validaciones técnicas previas a su procesamiento.
- estado_inicial: no
- estado_final: no

### EST-TEC-003 — Rechazada
- codigo: rechazada
- tipo: entidad
- aplica_a: operacion_distribuida
- descripcion: la operación distribuida fue rechazada por validación o consistencia técnica.
- estado_inicial: no
- estado_final: sí

### EST-TEC-004 — Cerrada
- codigo: cerrada
- tipo: entidad
- aplica_a: operacion_distribuida
- descripcion: la operación distribuida completó su circuito técnico y quedó cerrada.
- estado_inicial: no
- estado_final: sí

## B. Estados de sincronización

### EST-TEC-005 — Iniciada
- codigo: iniciada
- tipo: entidad
- aplica_a: sincronizacion
- descripcion: el proceso de sincronización fue iniciado dentro del circuito técnico.
- estado_inicial: sí
- estado_final: no

### EST-TEC-006 — En proceso
- codigo: en_proceso
- tipo: entidad
- aplica_a: sincronizacion
- descripcion: la sincronización se encuentra en curso con validación o aplicación técnica pendiente.
- estado_inicial: no
- estado_final: no

### EST-TEC-007 — Confirmada
- codigo: confirmada
- tipo: entidad
- aplica_a: sincronizacion
- descripcion: la sincronización fue confirmada técnicamente tras completar su procesamiento previsto.
- estado_inicial: no
- estado_final: sí

### EST-TEC-008 — Fallida
- codigo: fallida
- tipo: entidad
- aplica_a: sincronizacion
- descripcion: la sincronización no pudo completarse bajo las condiciones técnicas actuales.
- estado_inicial: no
- estado_final: no

### EST-TEC-009 — Reintentada
- codigo: reintentada
- tipo: entidad
- aplica_a: sincronizacion
- descripcion: la sincronización fallida ingresó a un nuevo intento técnico controlado.
- estado_inicial: no
- estado_final: no

## C. Estados de inbox y outbox

### EST-TEC-010 — Registrado
- codigo: registrado
- tipo: entidad
- aplica_a: inbox, outbox
- descripcion: el registro técnico fue incorporado al circuito de inbox o outbox.
- estado_inicial: sí
- estado_final: no

### EST-TEC-011 — Pendiente
- codigo: pendiente
- tipo: entidad
- aplica_a: inbox, outbox
- descripcion: el registro técnico permanece pendiente de emisión, procesamiento o confirmación.
- estado_inicial: no
- estado_final: no

### EST-TEC-012 — Procesado
- codigo: procesado
- tipo: entidad
- aplica_a: inbox
- descripcion: el registro de inbox ya fue procesado técnicamente.
- estado_inicial: no
- estado_final: no

### EST-TEC-013 — Emitido
- codigo: emitido
- tipo: entidad
- aplica_a: outbox
- descripcion: el registro de outbox fue emitido dentro del flujo técnico de sincronización.
- estado_inicial: no
- estado_final: no

### EST-TEC-014 — Confirmado
- codigo: confirmado
- tipo: entidad
- aplica_a: inbox, outbox
- descripcion: el procesamiento o emisión del registro técnico fue confirmado.
- estado_inicial: no
- estado_final: sí
- observaciones: aplica según el circuito técnico específico de inbox o outbox.

### EST-TEC-015 — Invalido
- codigo: invalido
- tipo: entidad
- aplica_a: inbox, outbox
- descripcion: el registro técnico no es válido para continuar dentro del circuito previsto.
- estado_inicial: no
- estado_final: sí

## D. Estados de idempotencia y reintentos

### EST-TEC-016 — op_id válido
- codigo: op_id_valido
- tipo: operativo
- aplica_a: op_id
- descripcion: el op_id fue validado como consistente para el contexto operativo analizado.
- estado_inicial: no
- estado_final: no

### EST-TEC-017 — op_id duplicado
- codigo: op_id_duplicado
- tipo: operativo
- aplica_a: op_id
- descripcion: el op_id ya existe asociado al mismo contenido y constituye un reintento válido.
- estado_inicial: no
- estado_final: no

### EST-TEC-018 — op_id en conflicto
- codigo: op_id_en_conflicto
- tipo: operativo
- aplica_a: op_id
- descripcion: el op_id ya existe asociado a contenido distinto y genera conflicto técnico.
- estado_inicial: no
- estado_final: yes

### EST-TEC-019 — Reintento válido
- codigo: reintento_valido
- tipo: operativo
- aplica_a: operacion_distribuida, sincronizacion
- descripcion: el reintento cumple las condiciones técnicas para ejecutarse sin duplicar efectos incompatibles.
- estado_inicial: no
- estado_final: no

### EST-TEC-020 — Reintento inválido
- codigo: reintento_invalido
- tipo: operativo
- aplica_a: operacion_distribuida, sincronizacion
- descripcion: el reintento no cumple las condiciones técnicas requeridas para preservar consistencia.
- estado_inicial: no
- estado_final: sí

### EST-TEC-021 — Operación ya ejecutada
- codigo: operacion_ya_ejecutada
- tipo: operativo
- aplica_a: operacion_distribuida
- descripcion: la operación ya produjo el efecto técnico esperado y no debe reejecutarse.
- estado_inicial: no
- estado_final: sí

## E. Estados de locks y concurrencia

### EST-TEC-022 — Lock activo
- codigo: lock_activo
- tipo: entidad
- aplica_a: lock_logico
- descripcion: existe un lock lógico vigente sobre el recurso o agregado afectado.
- estado_inicial: sí
- estado_final: no

### EST-TEC-023 — Lock liberado
- codigo: lock_liberado
- tipo: entidad
- aplica_a: lock_logico
- descripcion: el lock lógico fue liberado dentro del circuito técnico permitido.
- estado_inicial: no
- estado_final: sí

### EST-TEC-024 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: version_registro
- descripcion: la versión esperada coincide con la versión vigente del registro técnico evaluado.
- estado_inicial: no
- estado_final: no

### EST-TEC-025 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: version_registro
- descripcion: la versión esperada no coincide con la versión vigente y bloquea el cambio sensible.
- estado_inicial: no
- estado_final: sí

### EST-TEC-026 — Concurrencia en conflicto
- codigo: concurrencia_en_conflicto
- tipo: operativo
- aplica_a: lock_logico, version_registro
- descripcion: se detectó una condición de concurrencia incompatible con la operación en curso.
- estado_inicial: no
- estado_final: sí

## F. Estados de conflictos técnicos

### EST-TEC-027 — Detectado
- codigo: detectado
- tipo: entidad
- aplica_a: conflicto_tecnico
- descripcion: el conflicto técnico fue identificado dentro del circuito de procesamiento.
- estado_inicial: sí
- estado_final: no

### EST-TEC-028 — Registrado
- codigo: registrado
- tipo: entidad
- aplica_a: conflicto_tecnico
- descripcion: el conflicto técnico fue registrado con contexto suficiente para trazabilidad.
- estado_inicial: no
- estado_final: no

### EST-TEC-029 — Resuelto
- codigo: resuelto
- tipo: entidad
- aplica_a: conflicto_tecnico
- descripcion: el conflicto técnico fue resuelto bajo una política explícita permitida.
- estado_inicial: no
- estado_final: sí

### EST-TEC-030 — Escalado
- codigo: escalado
- tipo: entidad
- aplica_a: conflicto_tecnico
- descripcion: el conflicto técnico fue derivado a una instancia superior de resolución.
- estado_inicial: no
- estado_final: sí

### EST-TEC-031 — No resoluble
- codigo: no_resoluble
- tipo: entidad
- aplica_a: conflicto_tecnico
- descripcion: el conflicto técnico no puede resolverse automáticamente con las políticas vigentes.
- estado_inicial: no
- estado_final: sí

## G. Estados operativos transversales del dominio técnico

### EST-TEC-032 — Exito
- codigo: exito
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: la operación técnica finalizó conforme al resultado esperado.
- estado_inicial: no
- estado_final: sí

### EST-TEC-033 — Error
- codigo: error
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: la operación técnica finalizó con una condición de error.
- estado_inicial: no
- estado_final: sí

### EST-TEC-034 — Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: el proceso técnico no puede continuar por una condición de bloqueo activa.
- estado_inicial: no
- estado_final: no

### EST-TEC-035 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: se detectó una inconsistencia técnica que impide asumir coherencia del estado actual.
- estado_inicial: no
- estado_final: no

### EST-TEC-036 — Incompatible
- codigo: incompatible
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: el estado o contexto técnico actual es incompatible con la acción solicitada.
- estado_inicial: no
- estado_final: no

### EST-TEC-037 — Pendiente de revisión
- codigo: pendiente_de_revision
- tipo: operativo
- aplica_a: dominio_tecnico
- descripcion: el estado técnico requiere revisión o intervención posterior para continuar el circuito.
- estado_inicial: no
- estado_final: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Técnico.
- No reemplaza al CAT-CU maestro.
- Los estados aquí listados se usan como apoyo a implementación, validación y consistencia del dominio backend.
- Debe mantenerse alineado con CU-TEC, RN-TEC, ERR-TEC, EVT-TEC, CORE-EF-001 y CORE-EF-VALIDACION.
