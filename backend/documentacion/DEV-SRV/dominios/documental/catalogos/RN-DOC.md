# RN-DOC — Reglas del dominio Documental

## Objetivo
Definir reglas del dominio documental.

## Alcance
Incluye documentos, emisión, numeración, versionado, asociación y anulación.

---

## A. Reglas de documentos

### RN-DOC-001 — Documento como representación
- descripcion: Un documento representa una operación, entidad o hecho del sistema, sin ejecutar por sí mismo la lógica del negocio asociado.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-002 — Documento sin lógica de negocio
- descripcion: El documento no define ni sustituye la lógica de negocio de los dominios funcionales que representa.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-003 — Existencia previa a emisión
- descripcion: Un documento puede existir dentro del sistema sin haber sido emitido formalmente.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-004 — Tipo documental obligatorio
- descripcion: Todo documento debe contar con un tipo documental que defina su naturaleza y tratamiento.
- aplica_a: documento, tipo_documental
- origen_principal: DER

### RN-DOC-005 — Actividad documental
- descripcion: Un documento puede encontrarse activo o inactivo según su estado operativo dentro del dominio documental.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-006 — Multiplicidad de versiones
- descripcion: Un documento puede tener múltiples versiones preservando continuidad documental.
- aplica_a: documento, version_documental
- origen_principal: DEV-SRV

## B. Reglas de emisión documental

### RN-DOC-007 — Emisión como validación de uso
- descripcion: La emisión genera un documento válido para su uso interno o externo según el circuito correspondiente.
- aplica_a: documento, emision_documental
- origen_principal: DEV-SRV

### RN-DOC-008 — Trazabilidad de documento emitido
- descripcion: Todo documento emitido debe ser trazable en cuanto a fecha, contexto y referencia operativa relevante.
- aplica_a: documento, emision_documental
- origen_principal: DEV-SRV

### RN-DOC-009 — Inmutabilidad directa de documento emitido
- descripcion: Un documento emitido no debe modificarse directamente; los cambios posteriores deben canalizarse mediante versionado, reemisión o mecanismo equivalente.
- aplica_a: documento, emision_documental
- origen_principal: DEV-SRV

### RN-DOC-010 — Reemisión sin alteración de original
- descripcion: La reemisión no debe alterar la versión o emisión original ya consolidada.
- aplica_a: documento, emision_documental
- origen_principal: DEV-SRV

### RN-DOC-011 — Emisión dependiente de origen
- descripcion: La emisión documental puede depender de una operación o entidad origen claramente identificable.
- aplica_a: documento, emision_documental
- origen_principal: DEV-SRV

## C. Reglas de numeración

### RN-DOC-012 — Unicidad de numeración por tipo
- descripcion: La numeración documental debe ser única dentro del alcance definido para su tipo documental.
- aplica_a: numeracion_documental, tipo_documental
- origen_principal: DER

### RN-DOC-013 — Prohibición de duplicación numérica
- descripcion: No debe existir duplicación inconsistente de números documentales ya asignados.
- aplica_a: numeracion_documental
- origen_principal: DER

### RN-DOC-014 — Secuencialidad cuando corresponda
- descripcion: La numeración documental puede seguir secuencia ordenada cuando así lo requiera la política aplicable.
- aplica_a: numeracion_documental
- origen_principal: DEV-SRV

### RN-DOC-015 — Numeración contextual
- descripcion: La numeración puede depender de un contexto operativo, como sucursal o serie equivalente, sin perder unicidad dentro de su alcance.
- aplica_a: numeracion_documental
- origen_principal: DEV-SRV

### RN-DOC-016 — No reutilización de numeración
- descripcion: Un número documental asignado no debe reutilizarse para otro documento distinto.
- aplica_a: numeracion_documental
- origen_principal: DEV-SRV

## D. Reglas de versionado

### RN-DOC-017 — Múltiples versiones por documento
- descripcion: Un documento puede generar múltiples versiones a lo largo de su ciclo de vida.
- aplica_a: documento, version_documental
- origen_principal: DEV-SRV

### RN-DOC-018 — Conservación de versiones anteriores
- descripcion: La generación de una nueva versión no elimina ni reemplaza destructivamente las versiones anteriores.
- aplica_a: version_documental
- origen_principal: DEV-SRV

### RN-DOC-019 — Trazabilidad entre versiones
- descripcion: Las versiones documentales deben mantener trazabilidad entre sí y con el documento base.
- aplica_a: documento, version_documental
- origen_principal: DEV-SRV

### RN-DOC-020 — No sobrescritura de versión
- descripcion: Una versión documental consolidada no debe sobrescribirse como si fuera la misma versión previa.
- aplica_a: version_documental
- origen_principal: DEV-SRV

### RN-DOC-021 — Recuperación de versiones anteriores
- descripcion: Debe existir posibilidad de recuperar o consultar versiones anteriores cuando el flujo documental lo permita.
- aplica_a: version_documental
- origen_principal: DEV-SRV

## E. Reglas de asociación documental

### RN-DOC-022 — Asociación múltiple permitida
- descripcion: Un documento puede asociarse a múltiples entidades del sistema cuando el contexto funcional lo requiera.
- aplica_a: documento, asociacion_documental
- origen_principal: DEV-SRV

### RN-DOC-023 — Asociación sin modificación de entidad base
- descripcion: La asociación documental no modifica por sí misma la entidad base a la que se vincula.
- aplica_a: documento, asociacion_documental
- origen_principal: DEV-SRV

### RN-DOC-024 — Asociación con operaciones funcionales
- descripcion: Un documento puede asociarse a operaciones comerciales, locativas u otras, sin absorber su lógica de negocio.
- aplica_a: documento, asociacion_documental
- origen_principal: DEV-SRV

### RN-DOC-025 — Trazabilidad de asociación
- descripcion: Toda asociación documental debe conservar trazabilidad respecto de entidad, contexto y vigencia cuando corresponda.
- aplica_a: asociacion_documental
- origen_principal: DEV-SRV

### RN-DOC-026 — Desasociación sin eliminación
- descripcion: La desasociación documental no elimina el documento ni su historial.
- aplica_a: documento, asociacion_documental
- origen_principal: DEV-SRV

## F. Reglas de anulación y baja

### RN-DOC-027 — Documento anulable
- descripcion: Un documento puede ser anulado según las reglas del circuito documental aplicable.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-028 — Anulación sin eliminación
- descripcion: La anulación no elimina físicamente el documento ni su trazabilidad histórica.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-029 — Historial de documento anulado
- descripcion: Un documento anulado debe conservar historial de estados, emisiones y versiones relevantes.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-030 — No reutilización de documento dado de baja
- descripcion: Un documento dado de baja no debe reutilizarse como si fuera un documento nuevo o vigente.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-031 — Trazabilidad de revocación
- descripcion: La revocación documental debe quedar registrada con trazabilidad suficiente para reconstruir el cambio.
- aplica_a: documento
- origen_principal: DEV-SRV

## G. Reglas transversales documentales

### RN-DOC-032 — Sin lógica financiera
- descripcion: El dominio documental no ejecuta lógica financiera ni redefine efectos económicos.
- aplica_a: dominio_documental
- origen_principal: DEV-SRV

### RN-DOC-033 — Sin lógica comercial
- descripcion: El dominio documental no ejecuta lógica comercial ni decide operaciones de venta o reserva.
- aplica_a: dominio_documental
- origen_principal: DEV-SRV

### RN-DOC-034 — Sin lógica locativa
- descripcion: El dominio documental no ejecuta lógica locativa ni define contratos o condiciones de alquiler.
- aplica_a: dominio_documental
- origen_principal: DEV-SRV

### RN-DOC-035 — Documento como representación de hechos
- descripcion: Los documentos representan hechos o decisiones del sistema, pero no los ejecutan ni sustituyen.
- aplica_a: documento
- origen_principal: DEV-SRV

### RN-DOC-036 — Requisitos transversales de write sincronizable
- descripcion: Toda operación write sincronizable del dominio debe respetar versionado, op_id y outbox cuando corresponda.
- aplica_a: operaciones_write_documentales
- origen_principal: DEV-SRV
- observaciones: Regla aplicada en alineación con la infraestructura transversal del sistema.

### RN-DOC-037 — Separación entre estados documentales y de negocio
- descripcion: Los estados documentales no deben confundirse con estados de negocio de los dominios funcionales a los que refieren.
- aplica_a: documento, estado_documental
- origen_principal: DEV-SRV

---

## Reglas de normalización

1. No duplicar reglas.
2. Consolidar variantes similares.
3. Separar claramente documento de operación.
4. No incluir reglas técnicas profundas.
5. Mantener numeración RN-DOC-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio documental.
- Es transversal a todos los dominios.
- No reemplaza lógica de negocio.
- Debe mantenerse alineado con CU-DOC.
