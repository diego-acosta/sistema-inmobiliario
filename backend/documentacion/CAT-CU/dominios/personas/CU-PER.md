# CU-PER — Casos de uso del dominio Personas

## Objetivo
Definir los casos de uso del dominio Personas.

## Alcance
Incluye persona base, documentos identificatorios, domicilios, contactos, relaciones, representación y participación en relaciones del sistema.

---

## A. Gestión de persona base

### CU-PER-001 — Alta de persona
- tipo: write
- objetivo: Registrar una nueva persona base dentro del sistema.
- entidades: persona
- criticidad: alta

### CU-PER-002 — Modificación de persona
- tipo: write
- objetivo: Actualizar datos relevantes de una persona existente.
- entidades: persona
- criticidad: alta

### CU-PER-003 — Baja lógica de persona
- tipo: write
- objetivo: Dar de baja lógica a una persona preservando su trazabilidad histórica.
- entidades: persona
- criticidad: alta

### CU-PER-004 — Reactivación de persona
- tipo: write
- objetivo: Reactivar una persona previamente dada de baja cuando el dominio lo permita.
- entidades: persona
- criticidad: media

## B. Gestión de documentos identificatorios

### CU-PER-005 — Alta de documento identificatorio
- tipo: write
- objetivo: Registrar un documento identificatorio para una persona.
- entidades: persona, persona_documento
- criticidad: alta

### CU-PER-006 — Modificación de documento identificatorio
- tipo: write
- objetivo: Actualizar los datos de un documento identificatorio asociado a una persona.
- entidades: persona, persona_documento
- criticidad: alta

### CU-PER-007 — Baja lógica de documento identificatorio
- tipo: write
- objetivo: Dar de baja lógica a un documento identificatorio manteniendo historial.
- entidades: persona, persona_documento
- criticidad: alta

### CU-PER-008 — Cambio de documento principal
- tipo: write
- objetivo: Definir cuál es el documento identificatorio principal de una persona.
- entidades: persona, persona_documento
- criticidad: alta

## C. Gestión de domicilios

### CU-PER-009 — Alta de domicilio
- tipo: write
- objetivo: Registrar un domicilio asociado a una persona.
- entidades: persona, persona_domicilio
- criticidad: media

### CU-PER-010 — Modificación de domicilio
- tipo: write
- objetivo: Actualizar un domicilio previamente asociado a una persona.
- entidades: persona, persona_domicilio
- criticidad: media

### CU-PER-011 — Baja lógica de domicilio
- tipo: write
- objetivo: Dar de baja lógica a un domicilio preservando trazabilidad histórica.
- entidades: persona, persona_domicilio
- criticidad: media

### CU-PER-012 — Cambio de domicilio principal
- tipo: write
- objetivo: Definir cuál es el domicilio principal de la persona.
- entidades: persona, persona_domicilio
- criticidad: media

## D. Gestión de contactos

### CU-PER-013 — Alta de contacto
- tipo: write
- objetivo: Registrar un contacto asociado a una persona.
- entidades: persona, persona_contacto
- criticidad: media

### CU-PER-014 — Modificación de contacto
- tipo: write
- objetivo: Actualizar un contacto previamente registrado para una persona.
- entidades: persona, persona_contacto
- criticidad: media

### CU-PER-015 — Baja lógica de contacto
- tipo: write
- objetivo: Dar de baja lógica a un contacto manteniendo su trazabilidad histórica.
- entidades: persona, persona_contacto
- criticidad: media

### CU-PER-016 — Cambio de contacto principal
- tipo: write
- objetivo: Definir cuál es el contacto principal de una persona.
- entidades: persona, persona_contacto
- criticidad: media

## E. Gestión de relaciones entre personas

### CU-PER-017 — Alta de relación entre personas
- tipo: write
- objetivo: Registrar una relación entre personas dentro del sistema según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta

### CU-PER-018 — Modificación de relación entre personas
- tipo: write
- objetivo: Actualizar una relación existente entre personas según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta

### CU-PER-019 — Baja lógica de relación entre personas
- tipo: write
- objetivo: Dar de baja lógica a una relación entre personas preservando historial según el modelo vigente.
- entidades: persona, persona_relacion
- criticidad: alta

## F. Gestión de representación y poderes

### CU-PER-020 — Alta de representación o poder
- tipo: write
- objetivo: Registrar una representación o poder vigente entre personas.
- entidades: persona, representacion_poder
- criticidad: alta

### CU-PER-021 — Modificación de representación o poder
- tipo: write
- objetivo: Actualizar una representación o poder previamente registrado.
- entidades: persona, representacion_poder
- criticidad: alta

### CU-PER-022 — Baja lógica de representación o poder
- tipo: write
- objetivo: Dar de baja lógica a una representación o poder manteniendo su trazabilidad.
- entidades: persona, representacion_poder
- criticidad: alta

### CU-PER-023 — Consulta de representación vigente
- tipo: read
- objetivo: Consultar representaciones o poderes vigentes de una persona.
- entidades: persona, representacion_poder
- criticidad: media

## G. Gestión de roles de participación

### CU-PER-024 — Asignación de rol de participación a persona en una relación del sistema
- tipo: write
- objetivo: Asignar a una persona un rol de participación dentro de una relación del sistema.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta

### CU-PER-025 — Modificación de rol de participación
- tipo: write
- objetivo: Actualizar el rol de participación asignado a una persona dentro de una relación del sistema.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta

### CU-PER-026 — Baja lógica de rol de participación
- tipo: write
- objetivo: Dar de baja lógica a un rol de participación asignado a una persona.
- entidades: persona, rol_participacion, relacion_persona_rol
- criticidad: alta

## H. Consultas de persona

### CU-PER-027 — Consulta de persona
- tipo: read
- objetivo: Consultar el detalle base de una persona determinada.
- entidades: persona
- criticidad: media

### CU-PER-028 — Consulta de personas
- tipo: read
- objetivo: Listar y filtrar personas según criterios del dominio.
- entidades: persona
- criticidad: media

### CU-PER-029 — Consulta de ficha integral de persona
- tipo: read
- objetivo: Consultar la ficha integral de una persona con documentos, domicilios, contactos y relaciones asociadas.
- entidades: persona, persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder
- criticidad: media

### CU-PER-030 — Consulta por documento
- tipo: read
- objetivo: Buscar y consultar personas a partir de su documento identificatorio.
- entidades: persona, persona_documento
- criticidad: media

### CU-PER-031 — Consulta por CUIT o CUIL
- tipo: read
- objetivo: Buscar y consultar personas a partir de su CUIT o CUIL.
- entidades: persona, persona_documento
- criticidad: media

### CU-PER-032 — Consulta por nombre o razón social
- tipo: read
- objetivo: Buscar y consultar personas por nombre, apellido o razón social.
- entidades: persona
- criticidad: media

### CU-PER-033 — Consulta de histórico vinculado a persona
- tipo: read
- objetivo: Consultar la evolución histórica de una persona y de sus vínculos relevantes.
- entidades: persona, persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder, relacion_persona_rol
- criticidad: media

---

## Reglas

1. No fusionar persona con usuario.
2. No mezclar persona con cliente, locatario u otras especializaciones funcionales.
3. No mezclar identificación documental con documentación del dominio documental.
4. Mantener trazabilidad histórica en documentos, domicilios, contactos y relaciones.
5. Mantener separación entre persona base y su participación en relaciones del sistema.

---

## Notas

- El dominio Personas define al sujeto de negocio base del sistema.
- Las especializaciones funcionales dependen de persona, pero no la reemplazan.
- La persona puede participar en múltiples relaciones del sistema con distintos roles.
- Este dominio no define permisos ni seguridad técnica.
- Debe mantenerse alineado con comercial, locativo, financiero, documental y administrativo.
