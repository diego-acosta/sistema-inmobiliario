# CU-DOC — Casos de uso del dominio Documental

## Objetivo
Definir los casos de uso del dominio documental.

## Alcance
Incluye gestión de documentos, emisión, numeración, versiones y asociación con entidades del sistema.

---

## A. Gestión de documentos

### CU-DOC-001 — Alta de documento
- servicio_origen: SRV-DOC-001
- tipo: write
- objetivo: Registrar un documento dentro del dominio documental.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-002 — Modificación de documento
- servicio_origen: SRV-DOC-001
- tipo: write
- objetivo: Actualizar metadatos o contenido administrado de un documento existente.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-003 — Baja lógica de documento
- servicio_origen: SRV-DOC-006
- tipo: write
- objetivo: Desactivar un documento sin perder su trazabilidad histórica.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-004 — Activación de documento
- servicio_origen: SRV-DOC-001
- tipo: write
- objetivo: Reactivar un documento cuando su estado operativo lo permita.
- entidades: documento
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-005 — Consulta de documento
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Obtener la vista operativa o detallada de un documento.
- entidades: documento
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Emisión documental

### CU-DOC-006 — Emisión de documento
- servicio_origen: SRV-DOC-002
- tipo: write
- objetivo: Emitir formalmente un documento dentro del circuito documental.
- entidades: documento, emision_documental
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-007 — Reemisión de documento
- servicio_origen: SRV-DOC-002
- tipo: write
- objetivo: Generar una nueva emisión documental sobre un documento ya existente cuando corresponda.
- entidades: documento, emision_documental
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-008 — Generación de documento desde operación
- servicio_origen: SRV-DOC-002
- tipo: write
- objetivo: Crear o materializar un documento a partir de una operación de otro dominio.
- entidades: documento, operacion_referenciada
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-009 — Confirmación de emisión
- servicio_origen: SRV-DOC-002
- tipo: write
- objetivo: Confirmar la emisión documental y su estado operativo resultante.
- entidades: documento, emision_documental
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-010 — Consulta de emisión
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Consultar datos operativos e históricos de la emisión de un documento.
- entidades: documento, emision_documental
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Numeración documental

### CU-DOC-011 — Generación de numeración documental
- servicio_origen: SRV-DOC-003
- tipo: write
- objetivo: Generar una secuencia o numeración válida para documentos emitibles.
- entidades: numeracion_documental
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-012 — Asignación de número de documento
- servicio_origen: SRV-DOC-003
- tipo: write
- objetivo: Asignar un número documental concreto a un documento o emisión.
- entidades: documento, numeracion_documental
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-013 — Validación de numeración
- servicio_origen: SRV-DOC-003
- tipo: write
- objetivo: Verificar consistencia y validez de una numeración antes de su consolidación.
- entidades: numeracion_documental
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-014 — Consulta de numeración
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Consultar numeraciones documentales emitidas, disponibles o históricas.
- entidades: numeracion_documental
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Versionado de documentos

### CU-DOC-015 — Generación de nueva versión
- servicio_origen: SRV-DOC-004
- tipo: write
- objetivo: Crear una nueva versión documental preservando historial previo.
- entidades: documento, version_documental
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-016 — Consulta de versiones
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Obtener el historial de versiones de un documento.
- entidades: documento, version_documental
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-DOC-017 — Recuperación de versión anterior
- servicio_origen: SRV-DOC-004
- tipo: write
- objetivo: Recuperar una versión anterior de un documento dentro del marco permitido por el dominio.
- entidades: documento, version_documental
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-018 — Comparación de versiones
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Comparar dos o más versiones de un documento para análisis y trazabilidad.
- entidades: documento, version_documental
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Asociación documental

### CU-DOC-019 — Asociación de documento a entidad
- servicio_origen: SRV-DOC-005
- tipo: write
- objetivo: Vincular un documento con una entidad del sistema.
- entidades: documento, asociacion_documental, entidad_referenciada
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-020 — Desasociación de documento
- servicio_origen: SRV-DOC-005
- tipo: write
- objetivo: Remover la asociación documental respecto de una entidad o referencia previa.
- entidades: documento, asociacion_documental, entidad_referenciada
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-021 — Asociación de documento a operación
- servicio_origen: SRV-DOC-005
- tipo: write
- objetivo: Vincular un documento a una operación concreta del sistema.
- entidades: documento, asociacion_documental, operacion_referenciada
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-022 — Consulta de asociaciones
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Consultar asociaciones documentales vigentes o históricas.
- entidades: documento, asociacion_documental
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## F. Anulación y baja documental

### CU-DOC-023 — Anulación de documento
- servicio_origen: SRV-DOC-006
- tipo: write
- objetivo: Anular un documento dentro de las reglas del circuito documental.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-024 — Baja lógica de documento
- servicio_origen: SRV-DOC-006
- tipo: write
- objetivo: Marcar un documento con baja lógica sin eliminar su persistencia ni trazabilidad.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-025 — Revocación de documento
- servicio_origen: SRV-DOC-006
- tipo: write
- objetivo: Revocar la validez operativa de un documento previamente emitido o habilitado.
- entidades: documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-DOC-026 — Consulta de estado documental
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Consultar el estado documental actual de un documento y su trazabilidad relevante.
- entidades: documento, estado_documental
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## G. Consultas documentales

### CU-DOC-027 — Consulta operativa documental
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Proveer una vista operativa resumida del dominio documental.
- entidades: documento, estado_documental, numeracion_documental
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-DOC-028 — Consulta integral de documento
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Obtener una vista consolidada del documento con emisión, numeración, versiones y asociaciones.
- entidades: documento, emision_documental, numeracion_documental, version_documental, asociacion_documental
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-DOC-029 — Consulta de documentos por entidad
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Consultar documentos vinculados a una entidad determinada del sistema.
- entidades: documento, asociacion_documental, entidad_referenciada
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-DOC-030 — Reporte documental consolidado
- servicio_origen: SRV-DOC-007
- tipo: read
- objetivo: Emitir una vista consolidada de documentos, estados, numeración y asociaciones.
- entidades: documento, estado_documental, numeracion_documental, asociacion_documental
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

---

## Reglas de normalización

1. No duplicar casos.
2. No mezclar estados con acciones.
3. No mezclar lógica documental con lógica de negocio.
4. Consolidar variantes similares.
5. Mantener numeración CU-DOC-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio documental.
- No define lógica de negocio, solo representación documental.
- Es transversal a todos los dominios.
- Debe mantenerse alineado con DER.
