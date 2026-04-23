# CU-PER — Casos de uso del dominio Personas

## Objetivo
Definir los casos de uso del dominio Personas orientados a implementación backend.

## Alcance del dominio
Incluye persona base, identificación, domicilios, contactos, relaciones, representación y consultas integrales de persona.

## Bloques del dominio
- Persona base
- Documentos identificatorios
- Domicilios
- Contactos
- Relaciones entre personas
- Representación y poderes
- Roles de participación
- Consultas de persona

---

## A. Persona base

### CU-PER-001 — Alta de persona
- servicio_origen: SRV-PER-001
- tipo: write
- objetivo: registrar una nueva persona base dentro del sistema.
- entidades: persona
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-002 — Modificación de persona
- servicio_origen: SRV-PER-001
- tipo: write
- objetivo: actualizar datos relevantes de una persona existente.
- entidades: persona
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-003 — Baja lógica de persona
- servicio_origen: SRV-PER-001
- tipo: write
- objetivo: dar de baja lógica a una persona preservando su trazabilidad histórica.
- entidades: persona
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-004 — Reactivación de persona
- servicio_origen: SRV-PER-001
- tipo: write
- objetivo: reactivar una persona previamente dada de baja cuando el dominio lo permita.
- entidades: persona
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## B. Documentos identificatorios

### CU-PER-005 — Alta de documento identificatorio
- servicio_origen: SRV-PER-002
- tipo: write
- objetivo: registrar un documento identificatorio para una persona.
- entidades: persona, persona_documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-006 — Modificación de documento identificatorio
- servicio_origen: SRV-PER-002
- tipo: write
- objetivo: actualizar los datos de un documento identificatorio asociado a una persona.
- entidades: persona, persona_documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-007 — Baja lógica de documento identificatorio
- servicio_origen: SRV-PER-002
- tipo: write
- objetivo: dar de baja lógica a un documento identificatorio manteniendo historial.
- entidades: persona, persona_documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-008 — Cambio de documento principal
- servicio_origen: SRV-PER-002
- tipo: write
- objetivo: definir cuál es el documento identificatorio principal de una persona.
- entidades: persona, persona_documento
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## C. Domicilios

### CU-PER-009 — Alta de domicilio
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: registrar un domicilio asociado a una persona.
- entidades: persona, persona_domicilio
- criticidad: media
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-010 — Modificación de domicilio
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: actualizar un domicilio previamente asociado a una persona.
- entidades: persona, persona_domicilio
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-011 — Baja lógica de domicilio
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: dar de baja lógica a un domicilio preservando trazabilidad histórica.
- entidades: persona, persona_domicilio
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-012 — Cambio de domicilio principal
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: definir cuál es el domicilio principal de la persona.
- entidades: persona, persona_domicilio
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## D. Contactos

### CU-PER-013 — Alta de contacto
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: registrar un contacto asociado a una persona.
- entidades: persona, persona_contacto
- criticidad: media
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-014 — Modificación de contacto
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: actualizar un contacto previamente registrado para una persona.
- entidades: persona, persona_contacto
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-015 — Baja lógica de contacto
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: dar de baja lógica a un contacto manteniendo su trazabilidad histórica.
- entidades: persona, persona_contacto
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-016 — Cambio de contacto principal
- servicio_origen: SRV-PER-003
- tipo: write
- objetivo: definir cuál es el contacto principal de una persona.
- entidades: persona, persona_contacto
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## E. Relaciones entre personas

### CU-PER-017 — Alta de relación entre personas
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: registrar una relación entre personas dentro del sistema según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-018 — Modificación de relación entre personas
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: actualizar una relación existente entre personas según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-019 — Baja lógica de relación entre personas
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: dar de baja lógica a una relación entre personas preservando historial según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## F. Representación y poderes

### CU-PER-020 — Alta de representación o poder
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: registrar una representación o poder vigente entre personas.
- entidades: persona, representacion_poder
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-021 — Modificación de representación o poder
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: actualizar una representación o poder previamente registrado.
- entidades: persona, representacion_poder
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-022 — Baja lógica de representación o poder
- servicio_origen: SRV-PER-005
- tipo: write
- objetivo: dar de baja lógica a una representación o poder manteniendo su trazabilidad.
- entidades: persona, representacion_poder
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-023 — Consulta de representación vigente
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: consultar representaciones o poderes vigentes de una persona.
- entidades: persona, representacion_poder
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## G. Roles de participación

### CU-PER-024 — Asignación de rol de participación a persona en una relación del sistema
- servicio_origen: SRV-PER-006
- tipo: write
- objetivo: asignar a una persona un rol de participación dentro de una relación del sistema.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-025 — Modificación de rol de participación
- servicio_origen: SRV-PER-006
- tipo: write
- objetivo: actualizar el rol de participación asignado a una persona dentro de una relación del sistema.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-PER-026 — Baja lógica de rol de participación
- servicio_origen: SRV-PER-006
- tipo: write
- objetivo: dar de baja lógica a un rol de participación asignado a una persona.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## H. Consultas de persona

### CU-PER-027 — Consulta de persona
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: consultar el detalle base de una persona determinada.
- entidades: persona
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-028 — Consulta de personas
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: listar y filtrar personas según criterios del dominio.
- entidades: persona
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-029 — Consulta de ficha integral de persona
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: consultar la ficha integral de una persona con documentos, domicilios, contactos y relaciones asociadas.
- entidades: persona, persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-030 — Consulta por documento
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: buscar y consultar personas a partir de su documento identificatorio.
- entidades: persona, persona_documento
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-031 — Consulta por CUIT o CUIL
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: buscar y consultar personas a partir de su CUIT o CUIL.
- entidades: persona
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-032 — Consulta por nombre o razón social
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: buscar y consultar personas por nombre, apellido o razón social.
- entidades: persona
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-PER-033 — Consulta de histórico vinculado a persona
- servicio_origen: SRV-PER-007
- tipo: read
- objetivo: consultar la evolución histórica de una persona y de sus vínculos relevantes.
- entidades: persona, persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder, relacion_persona_rol
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Personas.
- No reemplaza al CAT-CU maestro.
- Los casos aquí listados se usan como apoyo a implementación y trazabilidad de servicios.
- Debe mantenerse alineado con SRV-PER del dominio y con el modelo real de base de datos.
