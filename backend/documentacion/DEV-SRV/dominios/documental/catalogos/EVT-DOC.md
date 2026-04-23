# EVT-DOC — Eventos del dominio Documental

## Objetivo
Definir eventos observables del dominio documental.

## Alcance
Incluye documentos, emisión, numeración, versionado, asociación y anulación.

---

## A. Eventos de documentos

### EVT-DOC-001 — Documento creado
- codigo: documento_creado
- descripcion: Se registró un nuevo documento dentro del dominio documental.
- origen_principal: SRV-DOC-001
- entidad_principal: documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-002 — Documento modificado
- codigo: documento_modificado
- descripcion: Se actualizó información relevante de un documento existente.
- origen_principal: SRV-DOC-001
- entidad_principal: documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-003 — Documento activado
- codigo: documento_activado
- descripcion: El documento fue activado para volver a estar operativo dentro del dominio.
- origen_principal: SRV-DOC-001
- entidad_principal: documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-004 — Documento desactivado
- codigo: documento_desactivado
- descripcion: El documento fue desactivado operativamente.
- origen_principal: SRV-DOC-001
- entidad_principal: documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-005 — Documento dado de baja lógica
- codigo: documento_dado_de_baja_logica
- descripcion: El documento fue marcado con baja lógica, preservando historial y trazabilidad.
- origen_principal: SRV-DOC-006
- entidad_principal: documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de emisión documental

### EVT-DOC-006 — Documento emitido
- codigo: documento_emitido
- descripcion: Se emitió formalmente un documento para su uso interno o externo.
- origen_principal: SRV-DOC-002
- entidad_principal: emision_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-007 — Documento reemitido
- codigo: documento_reemitido
- descripcion: Se generó una nueva emisión sobre un documento ya existente cuando correspondía.
- origen_principal: SRV-DOC-002
- entidad_principal: emision_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-008 — Documento generado desde operación
- codigo: documento_generado_desde_operacion
- descripcion: Se generó un documento a partir de una operación o entidad de referencia del sistema.
- origen_principal: SRV-DOC-002
- entidad_principal: documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí
- observaciones: El hecho de negocio originante pertenece al dominio que disparó la generación, no al documental.

### EVT-DOC-009 — Emisión confirmada
- codigo: emision_confirmada
- descripcion: La emisión documental quedó confirmada con su trazabilidad correspondiente.
- origen_principal: SRV-DOC-002
- entidad_principal: emision_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de numeración

### EVT-DOC-010 — Numeración generada
- codigo: numeracion_generada
- descripcion: Se generó una numeración documental dentro del alcance previsto.
- origen_principal: SRV-DOC-003
- entidad_principal: numeracion_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-011 — Número de documento asignado
- codigo: numero_documento_asignado
- descripcion: Se asignó un número documental a un documento o emisión.
- origen_principal: SRV-DOC-003
- entidad_principal: numeracion_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-012 — Numeración validada
- codigo: numeracion_validada
- descripcion: La numeración documental fue validada conforme a las reglas aplicables.
- origen_principal: SRV-DOC-003
- entidad_principal: numeracion_documental
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-013 — Conflicto de numeración detectado
- codigo: conflicto_numeracion_detectado
- descripcion: Se detectó un conflicto o inconsistencia en la numeración documental.
- origen_principal: SRV-DOC-003
- entidad_principal: numeracion_documental
- tipo_evento: auditoria
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí

## D. Eventos de versionado

### EVT-DOC-014 — Versión de documento creada
- codigo: version_documento_creada
- descripcion: Se creó una nueva versión documental preservando las versiones anteriores.
- origen_principal: SRV-DOC-004
- entidad_principal: version_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-015 — Versión de documento modificada
- codigo: version_documento_modificada
- descripcion: Se ajustó una versión documental dentro del circuito permitido por el dominio.
- origen_principal: SRV-DOC-004
- entidad_principal: version_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-016 — Versión de documento recuperada
- codigo: version_documento_recuperada
- descripcion: Se recuperó una versión anterior de un documento.
- origen_principal: SRV-DOC-004
- entidad_principal: version_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-017 — Versión de documento comparada
- codigo: version_documento_comparada
- descripcion: Se registró una comparación observable entre versiones documentales cuando el flujo lo requiere.
- origen_principal: SRV-DOC-004
- entidad_principal: version_documental
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí
- observaciones: No sustituye consultas; solo aplica si la comparación se registra como hecho observable del proceso documental.

## E. Eventos de asociación documental

### EVT-DOC-018 — Documento asociado a entidad
- codigo: documento_asociado_a_entidad
- descripcion: Se vinculó un documento a una entidad del sistema.
- origen_principal: SRV-DOC-005
- entidad_principal: asociacion_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-019 — Documento desasociado de entidad
- codigo: documento_desasociado_de_entidad
- descripcion: Se removió la asociación documental respecto de una entidad previamente vinculada.
- origen_principal: SRV-DOC-005
- entidad_principal: asociacion_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-020 — Documento asociado a operación
- codigo: documento_asociado_a_operacion
- descripcion: Se vinculó un documento a una operación del sistema.
- origen_principal: SRV-DOC-005
- entidad_principal: asociacion_documental
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-021 — Relación documental creada
- codigo: relacion_documental_creada
- descripcion: Se creó una nueva relación documental observable dentro del sistema.
- origen_principal: SRV-DOC-005
- entidad_principal: asociacion_documental
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## F. Eventos de anulación y baja

### EVT-DOC-022 — Documento anulado
- codigo: documento_anulado
- descripcion: El documento fue anulado conservando su historial y trazabilidad.
- origen_principal: SRV-DOC-006
- entidad_principal: documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-023 — Documento revocado
- codigo: documento_revocado
- descripcion: Se revocó la validez operativa de un documento previamente emitido o habilitado.
- origen_principal: SRV-DOC-006
- entidad_principal: documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-024 — Documento dado de baja
- codigo: documento_dado_de_baja
- descripcion: El documento fue dado de baja dentro del dominio documental.
- origen_principal: SRV-DOC-006
- entidad_principal: documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-DOC-025 — Anulación confirmada
- codigo: anulacion_confirmada
- descripcion: La anulación documental quedó confirmada en forma explícita.
- origen_principal: SRV-DOC-006
- entidad_principal: documento
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad: sí

## G. Notas de compatibilidad transversal

- El dominio documental no ejecuta lógica de negocio.
- Los documentos representan hechos de otros dominios.
- Los eventos documentales pueden derivar de:
  - comercial
  - locativo
  - financiero
- Esos eventos no deben duplicarse como eventos documentales principales.
- Los writes sincronizables usan `op_id` y outbox.

---

## Reglas de normalización

1. No listar consultas como eventos.
2. No duplicar eventos.
3. No usar “éxito” o “error”.
4. Mantener eventos como cambios observables reales.
5. Mantener numeración `EVT-DOC-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio documental.
- Es transversal a todos los dominios.
- No reemplaza eventos de negocio.
- Debe mantenerse alineado con CU-DOC y RN-DOC.
- Es base para trazabilidad documental.
