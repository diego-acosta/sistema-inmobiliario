# ERR-DOC — Errores del dominio Documental

## Objetivo
Definir errores del dominio documental.

## Alcance
Incluye documentos, emisión, numeración, versionado, asociación y anulación.

---

## A. Errores de documentos

### ERR-DOC-001 — Documento no encontrado
- codigo: documento_no_encontrado
- descripcion: No existe el documento solicitado en el contexto informado.
- tipo: funcional
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-002 — Documento inactivo
- codigo: documento_inactivo
- descripcion: El documento existe pero se encuentra inactivo para la operación requerida.
- tipo: funcional
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-003 — Documento duplicado
- codigo: documento_duplicado
- descripcion: Ya existe un documento equivalente que impide registrar otro con la misma identidad funcional.
- tipo: integridad
- aplica_a: documento
- origen: DER
- es_reintento_valido: no

### ERR-DOC-004 — Tipo documental inválido
- codigo: tipo_documental_invalido
- descripcion: El tipo documental informado no es válido o no corresponde para la operación.
- tipo: validacion
- aplica_a: documento, tipo_documental
- origen: DER
- es_reintento_valido: no

### ERR-DOC-005 — Estado de documento inválido
- codigo: estado_documento_invalido
- descripcion: El estado actual del documento no permite ejecutar la acción solicitada.
- tipo: validacion
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de emisión documental

### ERR-DOC-006 — Emisión inválida
- codigo: emision_invalida
- descripcion: La emisión solicitada no cumple las condiciones requeridas por el circuito documental.
- tipo: validacion
- aplica_a: emision_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-007 — Documento no emitido
- codigo: documento_no_emitido
- descripcion: El documento aún no cuenta con una emisión válida para la operación requerida.
- tipo: funcional
- aplica_a: documento, emision_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-008 — Documento ya emitido
- codigo: documento_ya_emitido
- descripcion: El documento ya fue emitido y no admite una nueva emisión directa en el estado actual.
- tipo: validacion
- aplica_a: documento, emision_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-009 — Reemisión inválida
- codigo: reemision_invalida
- descripcion: La reemisión solicitada no es válida para el documento o emisión de referencia.
- tipo: validacion
- aplica_a: documento, emision_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-010 — Inconsistencia de emisión
- codigo: inconsistencia_emision
- descripcion: La emisión documental presenta inconsistencias de estado, contexto o trazabilidad.
- tipo: integridad
- aplica_a: emision_documental
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de numeración

### ERR-DOC-011 — Numeración duplicada
- codigo: numeracion_duplicada
- descripcion: Ya existe una numeración documental equivalente e incompatible con la solicitada.
- tipo: integridad
- aplica_a: numeracion_documental
- origen: DER
- es_reintento_valido: no

### ERR-DOC-012 — Número de documento ya asignado
- codigo: numero_documento_ya_asignado
- descripcion: El número documental ya fue asignado a otro documento o emisión.
- tipo: integridad
- aplica_a: numeracion_documental, documento
- origen: DER
- es_reintento_valido: no

### ERR-DOC-013 — Secuencia inválida
- codigo: secuencia_invalida
- descripcion: La secuencia de numeración no resulta válida para el tipo o contexto documental.
- tipo: validacion
- aplica_a: numeracion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-014 — Inconsistencia de numeración
- codigo: inconsistencia_numeracion
- descripcion: La numeración documental presenta inconsistencias entre serie, contexto o valor asignado.
- tipo: integridad
- aplica_a: numeracion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-015 — Contexto de numeración inválido
- codigo: contexto_numeracion_invalido
- descripcion: El contexto usado para numerar el documento no es válido o no corresponde.
- tipo: validacion
- aplica_a: numeracion_documental
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de versionado

### ERR-DOC-016 — Versión de documento no encontrada
- codigo: version_documento_no_encontrada
- descripcion: No existe la versión documental solicitada.
- tipo: funcional
- aplica_a: version_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-017 — Versión inválida
- codigo: version_invalida
- descripcion: La versión documental informada no es válida para la operación requerida.
- tipo: validacion
- aplica_a: version_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-018 — Versión duplicada
- codigo: version_duplicada
- descripcion: Ya existe una versión documental con la misma identidad o correlación esperada.
- tipo: integridad
- aplica_a: version_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-019 — Conflicto de versión de documento
- codigo: conflicto_version_documento
- descripcion: La operación sobre versiones entra en conflicto con otra mutación o con el estado vigente del documento.
- tipo: concurrencia
- aplica_a: documento, version_documental
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-DOC-020 — Intento de sobrescritura de versión
- codigo: intento_sobrescritura_version
- descripcion: La operación intenta sobrescribir una versión documental ya consolidada.
- tipo: integridad
- aplica_a: version_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-021 — Recuperación de versión inválida
- codigo: recuperacion_version_invalida
- descripcion: No es posible recuperar la versión solicitada en el contexto actual.
- tipo: validacion
- aplica_a: version_documental
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de asociación documental

### ERR-DOC-022 — Asociación documental inválida
- codigo: asociacion_documental_invalida
- descripcion: La asociación documental solicitada no es válida para la entidad o el documento involucrado.
- tipo: validacion
- aplica_a: asociacion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-023 — Entidad asociada no encontrada
- codigo: entidad_asociada_no_encontrada
- descripcion: La entidad que se intenta asociar al documento no existe o no está disponible.
- tipo: funcional
- aplica_a: asociacion_documental, entidad_referenciada
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-024 — Duplicación de asociación
- codigo: duplicacion_asociacion
- descripcion: Ya existe una asociación documental equivalente entre el documento y la entidad referida.
- tipo: integridad
- aplica_a: asociacion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-025 — Inconsistencia de asociación
- codigo: inconsistencia_asociacion
- descripcion: La asociación documental presenta inconsistencias de entidad, vigencia o contexto.
- tipo: integridad
- aplica_a: asociacion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-026 — Desasociación inválida
- codigo: desasociacion_invalida
- descripcion: La desasociación solicitada no corresponde al estado actual de la relación documental.
- tipo: validacion
- aplica_a: asociacion_documental
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores de anulación y baja

### ERR-DOC-027 — Documento anulado
- codigo: documento_anulado
- descripcion: El documento ya se encuentra anulado y no admite la operación solicitada.
- tipo: funcional
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-028 — Documento no anulable
- codigo: documento_no_anulable
- descripcion: El documento no cumple condiciones para ser anulado en el estado actual.
- tipo: validacion
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-029 — Anulación inválida
- codigo: anulacion_invalida
- descripcion: La anulación solicitada no es válida por contexto, estado o trazabilidad insuficiente.
- tipo: validacion
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-030 — Documento dado de baja
- codigo: documento_dado_de_baja
- descripcion: El documento se encuentra dado de baja y no puede reutilizarse operativamente.
- tipo: funcional
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-031 — Revocación inválida
- codigo: revocacion_invalida
- descripcion: La revocación solicitada no es válida para el documento o su estado actual.
- tipo: validacion
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: no

## G. Errores transversales documentales

### ERR-DOC-032 — Versión esperada inválida
- codigo: version_esperada_invalida
- descripcion: La versión esperada no coincide con la versión vigente de la entidad documental.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-033 — Lock lógico activo
- codigo: lock_logico_activo
- descripcion: La entidad documental se encuentra protegida por un lock lógico activo.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-034 — Recurso bloqueado
- codigo: recurso_bloqueado
- descripcion: El recurso documental no puede modificarse por una restricción o bloqueo vigente.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-035 — Op id duplicado
- codigo: op_id_duplicado
- descripcion: La operación documental ya fue registrada con el mismo identificador idempotente.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-036 — Op id duplicado con payload distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: El identificador de operación ya existe pero con un payload distinto al actual.
- tipo: integridad
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: no

### ERR-DOC-037 — Conflicto de concurrencia
- codigo: conflicto_concurrencia
- descripcion: La operación entró en conflicto con otra mutación concurrente sobre la misma entidad documental.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-038 — Inconsistencia de contexto técnico
- codigo: inconsistencia_contexto_tecnico
- descripcion: El contexto técnico informado no es válido o no resulta coherente para procesar la operación.
- tipo: integridad
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: no

### ERR-DOC-039 — Entidad no encontrada
- codigo: entidad_no_encontrada
- descripcion: La entidad objetivo de la operación documental no existe al momento de aplicar el cambio.
- tipo: funcional
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: no

### ERR-DOC-040 — Entidad inactiva
- codigo: entidad_inactiva
- descripcion: La entidad objetivo existe pero se encuentra inactiva para la operación solicitada.
- tipo: funcional
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: no

### ERR-DOC-041 — Error de idempotencia
- codigo: error_idempotencia
- descripcion: No fue posible resolver correctamente la idempotencia de la operación documental.
- tipo: concurrencia
- aplica_a: operaciones_write_documentales
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-DOC-042 — Inconsistencia documental
- codigo: inconsistencia_documental
- descripcion: Se detectó una inconsistencia relevante entre documento, emisión, numeración, versión o asociación.
- tipo: integridad
- aplica_a: documento, emision_documental, numeracion_documental, version_documental, asociacion_documental
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-DOC-043 — Conflicto de estado documental
- codigo: conflicto_estado_documental
- descripcion: El estado documental visible entra en conflicto con la operación solicitada o con otro cambio concurrente.
- tipo: concurrencia
- aplica_a: documento
- origen: DEV-SRV
- es_reintento_valido: sí

---

## Reglas de normalización

1. No duplicar errores.
2. Separar errores funcionales de concurrencia.
3. No incluir errores de otros dominios.
4. No incluir errores técnicos de infraestructura profunda.
5. Consolidar variantes similares.
6. Mantener numeración `ERR-DOC-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio documental.
- Es transversal a todos los dominios.
- Debe mantenerse alineado con CU-DOC y RN-DOC.
- Sirve como base para manejo consistente de errores.
