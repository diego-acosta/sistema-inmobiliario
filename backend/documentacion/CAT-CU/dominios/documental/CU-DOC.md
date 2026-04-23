# CU-DOC — Casos de uso del dominio Documental

## Objetivo
Definir los casos de uso documentales del sistema.

## Alcance
Incluye plantillas, generación, emisión y consulta de documentos.

---

## A. Plantillas documentales

### CU-DOC-001 — Alta de plantilla documental
- tipo: write
- objetivo: Registrar una nueva plantilla documental dentro del sistema.
- entidades: plantilla_documental
- criticidad: alta

### CU-DOC-002 — Modificación de plantilla documental
- tipo: write
- objetivo: Actualizar una plantilla documental existente.
- entidades: plantilla_documental
- criticidad: alta

### CU-DOC-003 — Baja de plantilla documental
- tipo: write
- objetivo: Dar de baja una plantilla documental preservando su trazabilidad.
- entidades: plantilla_documental
- criticidad: alta

### CU-DOC-004 — Consulta de plantillas
- tipo: read
- objetivo: Consultar y listar plantillas documentales disponibles o históricas.
- entidades: plantilla_documental
- criticidad: media

## B. Generación de documentos

### CU-DOC-005 — Generación de documento
- tipo: write
- objetivo: Generar un documento a partir de una plantilla y de información proveniente del sistema.
- entidades: documento, plantilla_documental
- criticidad: alta

### CU-DOC-006 — Regeneración de documento
- tipo: write
- objetivo: Regenerar un documento previamente generado manteniendo trazabilidad documental.
- entidades: documento, plantilla_documental
- criticidad: alta

### CU-DOC-007 — Anulación de documento generado
- tipo: write
- objetivo: Anular un documento generado dentro del estado documental permitido, sin alterar indebidamente la trazabilidad documental.
- entidades: documento
- criticidad: alta

## C. Emisión documental

### CU-DOC-008 — Emisión de documento
- tipo: write
- objetivo: Emitir formalmente un documento para su uso interno o externo.
- entidades: documento, emision_documental
- criticidad: crítica

### CU-DOC-009 — Reemisión de documento
- tipo: write
- objetivo: Reemitir un documento dentro del circuito documental preservando trazabilidad de emisiones previas.
- entidades: documento, emision_documental
- criticidad: alta

## D. Estado y control documental

### CU-DOC-010 — Cambio de estado documental
- tipo: write
- objetivo: Actualizar el estado documental de un documento según el flujo permitido.
- entidades: documento, estado_documental
- criticidad: alta

### CU-DOC-011 — Versionado de documento
- tipo: write
- objetivo: Registrar una nueva versión documental preservando historial y trazabilidad.
- entidades: documento, version_documental
- criticidad: alta

## E. Asociación documental

### CU-DOC-015 — Asociación de documento a entidad
- tipo: write
- objetivo: Asociar un documento a una entidad del sistema preservando trazabilidad documental.
- entidades: documento, entidad_documental
- criticidad: alta

### CU-DOC-016 — Reasociación de documento
- tipo: write
- objetivo: Modificar la entidad a la que se encuentra asociado un documento dentro de las reglas del circuito documental.
- entidades: documento, entidad_documental
- criticidad: alta

### CU-DOC-017 — Consulta de asociaciones documentales
- tipo: read
- objetivo: Consultar las asociaciones vigentes e históricas de un documento con entidades del sistema.
- entidades: documento, entidad_documental
- criticidad: media

## F. Consultas documentales

### CU-DOC-018 — Consulta de documento
- tipo: read
- objetivo: Consultar el detalle de un documento determinado.
- entidades: documento
- criticidad: media

### CU-DOC-019 — Consulta de documentos
- tipo: read
- objetivo: Listar y filtrar documentos según criterios documentales.
- entidades: documento
- criticidad: media

### CU-DOC-020 — Consulta de historial documental
- tipo: read
- objetivo: Consultar la evolución histórica de un documento, sus estados y sus versiones.
- entidades: documento, historial_documental, version_documental
- criticidad: media

---

## Reglas

1. No generar contratos ni lógica contractual.
2. No generar obligaciones financieras.
3. No ejecutar lógica de negocio.
4. Solo representar estados del sistema.
5. Mantener independencia de otros dominios.

---

## Notas

- Este dominio representa documentalmente el estado del sistema.
- La generación de un documento no implica su emisión formal.
- La emisión documental constituye un acto posterior dentro del circuito documental.
- No define reglas de negocio.
- No modifica entidades principales.
- Solo refleja y formaliza información de otros dominios.
