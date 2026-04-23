# EVT-PER — Eventos del dominio Personas

## Objetivo
Definir los eventos observables del dominio Personas como apoyo a implementación backend.

## Alcance del dominio
Incluye persona base, identificación, domicilios, contactos, relaciones, representación y roles de participación del dominio.

---

## A. Eventos de persona base

### EVT-PER-001 — Persona creada
- codigo: persona_creada
- descripcion: se registró una nueva persona base en el sistema.
- origen_principal: SRV-PER-001
- entidad_principal: persona
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-002 — Persona modificada
- codigo: persona_modificada
- descripcion: se actualizaron datos relevantes de una persona existente.
- origen_principal: SRV-PER-001
- entidad_principal: persona
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-003 — Persona dada de baja lógica
- codigo: persona_dada_de_baja_logica
- descripcion: se aplicó baja lógica sobre una persona preservando su trazabilidad.
- origen_principal: SRV-PER-001
- entidad_principal: persona
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-004 — Persona reactivada
- codigo: persona_reactivada
- descripcion: una persona previamente dada de baja fue reactivada.
- origen_principal: SRV-PER-001
- entidad_principal: persona
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de documentos identificatorios

### EVT-PER-005 — Documento identificatorio agregado
- codigo: documento_identificatorio_agregado
- descripcion: se agregó un documento identificatorio a una persona.
- origen_principal: SRV-PER-002
- entidad_principal: persona_documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-006 — Documento identificatorio modificado
- codigo: documento_identificatorio_modificado
- descripcion: se modificó un documento identificatorio existente.
- origen_principal: SRV-PER-002
- entidad_principal: persona_documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-007 — Documento identificatorio dado de baja lógica
- codigo: documento_identificatorio_dado_de_baja_logica
- descripcion: se aplicó baja lógica a un documento identificatorio.
- origen_principal: SRV-PER-002
- entidad_principal: persona_documento
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-008 — Documento principal cambiado
- codigo: documento_principal_cambiado
- descripcion: cambió el documento principal definido para una persona.
- origen_principal: SRV-PER-002
- entidad_principal: persona_documento
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de domicilios

### EVT-PER-009 — Domicilio agregado
- codigo: domicilio_agregado
- descripcion: se agregó un domicilio a una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_domicilio
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-010 — Domicilio modificado
- codigo: domicilio_modificado
- descripcion: se modificó un domicilio existente de una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_domicilio
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-011 — Domicilio dado de baja lógica
- codigo: domicilio_dado_de_baja_logica
- descripcion: se aplicó baja lógica a un domicilio asociado a una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_domicilio
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-012 — Domicilio principal cambiado
- codigo: domicilio_principal_cambiado
- descripcion: cambió el domicilio principal definido para una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_domicilio
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## D. Eventos de contactos

### EVT-PER-013 — Contacto agregado
- codigo: contacto_agregado
- descripcion: se agregó un contacto a una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_contacto
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-014 — Contacto modificado
- codigo: contacto_modificado
- descripcion: se modificó un contacto existente de una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_contacto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-015 — Contacto dado de baja lógica
- codigo: contacto_dado_de_baja_logica
- descripcion: se aplicó baja lógica a un contacto asociado a una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_contacto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-016 — Contacto principal cambiado
- codigo: contacto_principal_cambiado
- descripcion: cambió el contacto principal definido para una persona.
- origen_principal: SRV-PER-003
- entidad_principal: persona_contacto
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## E. Eventos de relaciones entre personas

### EVT-PER-017 — Relación entre personas creada
- codigo: relacion_persona_creada
- descripcion: se registró una nueva relación entre personas.
- origen_principal: SRV-PER-005
- entidad_principal: persona_relacion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-018 — Relación entre personas modificada
- codigo: relacion_persona_modificada
- descripcion: se modificó una relación entre personas existente.
- origen_principal: SRV-PER-005
- entidad_principal: persona_relacion
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-019 — Relación entre personas dada de baja lógica
- codigo: relacion_persona_dada_de_baja_logica
- descripcion: se aplicó baja lógica a una relación entre personas.
- origen_principal: SRV-PER-005
- entidad_principal: persona_relacion
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## F. Eventos de representación y poderes

### EVT-PER-020 — Representación o poder creada
- codigo: representacion_poder_creada
- descripcion: se registró una nueva representación o poder entre personas.
- origen_principal: SRV-PER-005
- entidad_principal: representacion_poder
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-021 — Representación o poder modificada
- codigo: representacion_poder_modificada
- descripcion: se modificó una representación o poder existente.
- origen_principal: SRV-PER-005
- entidad_principal: representacion_poder
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-022 — Representación o poder dada de baja lógica
- codigo: representacion_poder_dada_de_baja_logica
- descripcion: se aplicó baja lógica a una representación o poder.
- origen_principal: SRV-PER-005
- entidad_principal: representacion_poder
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## G. Eventos de roles de participación

### EVT-PER-023 — Rol de participación asignado
- codigo: rol_participacion_asignado
- descripcion: se asignó un rol de participación a una persona dentro de una relación del sistema.
- origen_principal: SRV-PER-006
- entidad_principal: relacion_persona_rol
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-024 — Rol de participación modificado
- codigo: rol_participacion_modificado
- descripcion: se modificó una asignación de rol de participación existente.
- origen_principal: SRV-PER-006
- entidad_principal: relacion_persona_rol
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-PER-025 — Rol de participación dado de baja lógica
- codigo: rol_participacion_dado_de_baja_logica
- descripcion: se aplicó baja lógica a una asignación de rol de participación.
- origen_principal: SRV-PER-006
- entidad_principal: relacion_persona_rol
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## H. Notas de compatibilidad transversal

- El dominio Personas define sujetos base y vínculos, no especializaciones funcionales.
- Los eventos de Personas pueden ser consumidos por comercial, locativo, financiero o documental.
- Esos consumos no deben duplicar eventos propios del dominio Personas.
- Los writes sincronizables usan op_id y outbox según CORE-EF.

## Notas
- Este catálogo deriva del DEV-SRV del dominio Personas.
- No reemplaza al CAT-CU maestro.
- Los eventos aquí listados se usan como apoyo a implementación, auditoría, historización y trazabilidad backend.
- Debe mantenerse alineado con CU-PER, RN-PER, ERR-PER y con el modelo real de base de datos.
