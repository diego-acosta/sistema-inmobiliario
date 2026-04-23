# EST-DOC — Estados del dominio Documental

## Objetivo
Definir los estados del dominio documental.

## Alcance
Incluye documentos, emisión, numeración, versionado, asociación y anulación.

---

## A. Estados de documentos

### EST-DOC-001 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: documento
- descripcion: El documento se encuentra habilitado para su uso dentro del circuito documental.
- estado_inicial: sí
- estado_final: no

### EST-DOC-002 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: documento
- descripcion: El documento existe pero no se encuentra habilitado operativamente.
- estado_inicial: no
- estado_final: no

### EST-DOC-003 — Emitido
- codigo: emitido
- tipo: entidad
- aplica_a: documento
- descripcion: El documento ya cuenta con una emisión documental válida.
- estado_inicial: no
- estado_final: no

### EST-DOC-004 — No emitido
- codigo: no_emitido
- tipo: entidad
- aplica_a: documento
- descripcion: El documento aún no fue emitido formalmente.
- estado_inicial: sí
- estado_final: no

### EST-DOC-005 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: documento
- descripcion: El documento fue dado de baja lógica y no debe reutilizarse operativamente.
- estado_inicial: no
- estado_final: sí

## B. Estados de emisión

### EST-DOC-006 — Pendiente de emisión
- codigo: pendiente_emision
- tipo: entidad
- aplica_a: emision_documental
- descripcion: La emisión documental fue iniciada pero aún no se consolidó.
- estado_inicial: sí
- estado_final: no

### EST-DOC-007 — Emitido
- codigo: emitido
- tipo: entidad
- aplica_a: emision_documental
- descripcion: La emisión documental quedó registrada como válida.
- estado_inicial: no
- estado_final: no

### EST-DOC-008 — Reemitido
- codigo: reemitido
- tipo: entidad
- aplica_a: emision_documental
- descripcion: El documento cuenta con una reemisión posterior respecto de una emisión previa.
- estado_inicial: no
- estado_final: no

### EST-DOC-009 — Confirmado
- codigo: confirmado
- tipo: entidad
- aplica_a: emision_documental
- descripcion: La emisión documental fue confirmada en forma explícita dentro del circuito.
- estado_inicial: no
- estado_final: sí

## C. Estados de numeración

### EST-DOC-010 — Pendiente de numeración
- codigo: pendiente_numeracion
- tipo: entidad
- aplica_a: numeracion_documental
- descripcion: El documento o emisión aún no tiene número asignado.
- estado_inicial: sí
- estado_final: no

### EST-DOC-011 — Numerado
- codigo: numerado
- tipo: entidad
- aplica_a: numeracion_documental
- descripcion: La numeración documental ya fue asignada.
- estado_inicial: no
- estado_final: no

### EST-DOC-012 — Validado
- codigo: validado
- tipo: entidad
- aplica_a: numeracion_documental
- descripcion: La numeración asignada fue validada conforme a las reglas del dominio.
- estado_inicial: no
- estado_final: no

### EST-DOC-013 — Rechazado
- codigo: rechazado
- tipo: entidad
- aplica_a: numeracion_documental
- descripcion: La numeración propuesta o asignada fue rechazada por inconsistencia o invalidez.
- estado_inicial: no
- estado_final: sí

## D. Estados de versionado

### EST-DOC-014 — Vigente
- codigo: vigente
- tipo: entidad
- aplica_a: version_documental
- descripcion: La versión documental es la versión actualmente aplicable o visible.
- estado_inicial: sí
- estado_final: no

### EST-DOC-015 — Histórico
- codigo: historico
- tipo: entidad
- aplica_a: version_documental
- descripcion: La versión documental quedó preservada como antecedente histórico.
- estado_inicial: no
- estado_final: no

### EST-DOC-016 — Reemplazado
- codigo: reemplazado
- tipo: entidad
- aplica_a: version_documental
- descripcion: La versión documental dejó de ser vigente por haber sido sustituida por otra posterior.
- estado_inicial: no
- estado_final: sí

## E. Estados de asociación documental

### EST-DOC-017 — Asociado
- codigo: asociado
- tipo: entidad
- aplica_a: asociacion_documental
- descripcion: El documento mantiene una asociación activa con una entidad u operación del sistema.
- estado_inicial: sí
- estado_final: no

### EST-DOC-018 — Desasociado
- codigo: desasociado
- tipo: entidad
- aplica_a: asociacion_documental
- descripcion: La asociación documental fue removida y ya no se encuentra vigente.
- estado_inicial: no
- estado_final: sí

## F. Estados de anulación y baja

### EST-DOC-019 — Anulado
- codigo: anulado
- tipo: entidad
- aplica_a: documento
- descripcion: El documento fue anulado manteniendo su historial documental.
- estado_inicial: no
- estado_final: sí

### EST-DOC-020 — Revocado
- codigo: revocado
- tipo: entidad
- aplica_a: documento
- descripcion: La validez operativa del documento fue revocada.
- estado_inicial: no
- estado_final: sí

### EST-DOC-021 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: documento
- descripcion: El documento fue dado de baja lógica y retirado del uso operativo.
- estado_inicial: no
- estado_final: sí

## G. Estados operativos transversales

### EST-DOC-022 — Éxito
- codigo: exito
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación documental se ejecutó correctamente.
- estado_inicial: no
- estado_final: sí

### EST-DOC-023 — Error
- codigo: error
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación documental finalizó con error bloqueante.
- estado_inicial: no
- estado_final: sí

### EST-DOC-024 — Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación encontró una colisión funcional o técnica que impide su cierre normal.
- estado_inicial: no
- estado_final: sí

### EST-DOC-025 — Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación fue rechazada por validación o por regla del dominio.
- estado_inicial: no
- estado_final: sí

### EST-DOC-026 — Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación no puede continuar por lock o restricción equivalente.
- estado_inicial: no
- estado_final: sí

### EST-DOC-027 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: ejecucion_servicio_documental
- descripcion: La operación detectó inconsistencias entre contexto, entidad y estado esperado.
- estado_inicial: no
- estado_final: sí

### EST-DOC-028 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: control_versionado_documental
- descripcion: La versión esperada coincide con la versión vigente.
- estado_inicial: no
- estado_final: sí

### EST-DOC-029 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: control_versionado_documental
- descripcion: La versión esperada no coincide con la versión vigente.
- estado_inicial: no
- estado_final: sí

### EST-DOC-030 — Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: control_idempotencia_documental
- descripcion: La operación fue ejecutada y registrada válidamente.
- estado_inicial: no
- estado_final: sí

### EST-DOC-031 — Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: control_idempotencia_documental
- descripcion: La operación ya había sido registrada con el mismo identificador operativo.
- estado_inicial: no
- estado_final: sí

### EST-DOC-032 — Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: control_idempotencia_documental
- descripcion: La operación repite identificador pero con diferencias incompatibles respecto de la ejecución previa.
- estado_inicial: no
- estado_final: sí

---

## Reglas de normalización

1. No duplicar estados.
2. Consolidar estados comunes.
3. No mezclar estados con eventos.
4. Mantener estados reutilizables.
5. Mantener numeración `EST-DOC-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV y del DER documental.
- Es transversal a todos los dominios.
- No define lógica, solo estados posibles.
- Debe mantenerse alineado con RN-DOC.
- Sirve como base para validaciones y flujos.
