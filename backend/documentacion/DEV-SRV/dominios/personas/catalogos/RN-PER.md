# RN-PER — Reglas del dominio Personas

## Objetivo
Definir reglas de negocio y consistencia del dominio Personas orientadas a implementación backend.

## Alcance del dominio
Incluye persona base, identificación, domicilios, contactos, relaciones, representación, roles de participación y consultas del dominio.

---

## A. Reglas de persona base

### RN-PER-001 — Persona como sujeto base
- descripcion: una persona es el sujeto base del sistema y funciona como referencia común para vínculos y participación funcional.
- aplica_a: persona
- origen_principal: DEV-SRV

### RN-PER-002 — Separación de persona y usuario
- descripcion: una persona no debe fusionarse con usuario administrativo ni sustituir estructuras de seguridad técnica.
- aplica_a: persona
- origen_principal: DEV-SRV

### RN-PER-003 — Baja lógica con trazabilidad
- descripcion: la baja lógica de persona no debe destruir trazabilidad ni historial relevante del dominio.
- aplica_a: persona
- origen_principal: DEV-SRV

### RN-PER-004 — Reactivación consistente
- descripcion: la reactivación de persona debe respetar consistencia con el estado previo y con su información asociada vigente.
- aplica_a: persona
- origen_principal: DEV-SRV

### RN-PER-005 — Consistencia de datos base
- descripcion: los datos base de persona deben mantener unicidad y consistencia conforme al modelo vigente.
- aplica_a: persona
- origen_principal: SQL
- observaciones: la restricción exacta depende del modelo real y sus validaciones de persistencia.

## B. Reglas de documentos identificatorios

### RN-PER-006 — Multiplicidad de documentos
- descripcion: una persona puede tener múltiples documentos identificatorios asociados.
- aplica_a: persona, persona_documento
- origen_principal: DEV-SRV

### RN-PER-007 — Documento principal único
- descripcion: debe poder definirse un documento principal y esa principalidad debe ser única por persona.
- aplica_a: persona_documento
- origen_principal: SQL
- observaciones: el modelo expone indicador de principalidad en persona_documento.

### RN-PER-008 — Baja lógica con historial documental
- descripcion: la baja lógica de un documento identificatorio no debe destruir historial ni trazabilidad.
- aplica_a: persona_documento
- origen_principal: DEV-SRV

### RN-PER-009 — Identificación fuera del dominio documental
- descripcion: la gestión identificatoria de persona pertenece al dominio Personas y no al dominio documental.
- aplica_a: persona_documento
- origen_principal: DEV-SRV

### RN-PER-010 — Unicidad documental según modelo
- descripcion: las validaciones de unicidad documental deben respetar las restricciones y validaciones del modelo real de base de datos.
- aplica_a: persona_documento
- origen_principal: SQL

## C. Reglas de domicilios

### RN-PER-011 — Multiplicidad de domicilios
- descripcion: una persona puede tener múltiples domicilios asociados.
- aplica_a: persona, persona_domicilio
- origen_principal: DEV-SRV

### RN-PER-012 — Domicilio principal único
- descripcion: debe poder definirse un domicilio principal y esa principalidad debe ser única por persona.
- aplica_a: persona_domicilio
- origen_principal: DEV-SRV
- observaciones: SRV-PER-003 explicita criterio y control de principalidad.

### RN-PER-013 — Baja lógica de domicilio con historial
- descripcion: la baja lógica de domicilio debe preservar historial y trazabilidad del vínculo con la persona.
- aplica_a: persona_domicilio
- origen_principal: DEV-SRV

### RN-PER-014 — Inactividad incompatible con principalidad
- descripcion: un domicilio inactivo no debe quedar marcado como principal.
- aplica_a: persona_domicilio
- origen_principal: DEV-SRV

## D. Reglas de contactos

### RN-PER-015 — Multiplicidad de contactos
- descripcion: una persona puede tener múltiples contactos o medios de comunicación asociados.
- aplica_a: persona, persona_contacto
- origen_principal: DEV-SRV

### RN-PER-016 — Contacto principal único
- descripcion: debe poder definirse un contacto principal y esa principalidad debe ser única por persona.
- aplica_a: persona_contacto
- origen_principal: DEV-SRV
- observaciones: SRV-PER-003 explicita criterio y control de principalidad.

### RN-PER-017 — Baja lógica de contacto con historial
- descripcion: la baja lógica de contacto debe preservar historial y trazabilidad.
- aplica_a: persona_contacto
- origen_principal: DEV-SRV

### RN-PER-018 — Inactividad incompatible con principalidad de contacto
- descripcion: un contacto inactivo no debe quedar marcado como principal.
- aplica_a: persona_contacto
- origen_principal: DEV-SRV

## E. Reglas de relaciones entre personas

### RN-PER-019 — Relación conforme al modelo vigente
- descripcion: una relación entre personas debe respetar el modelo vigente y sus datos de vinculación permitidos.
- aplica_a: persona_relacion
- origen_principal: DEV-SRV

### RN-PER-020 — Baja lógica de relación con trazabilidad
- descripcion: la baja lógica de relación debe preservar historial y trazabilidad entre las partes vinculadas.
- aplica_a: persona_relacion
- origen_principal: DEV-SRV

### RN-PER-021 — No duplicación indebida de relaciones
- descripcion: las relaciones entre personas no deben duplicarse indebidamente según las reglas del modelo y su contexto de vínculo.
- aplica_a: persona_relacion
- origen_principal: SQL

### RN-PER-022 — Consistencia entre partes vinculadas
- descripcion: la modificación de relación debe respetar consistencia entre persona origen, persona destino y el tipo de relación definido.
- aplica_a: persona_relacion
- origen_principal: DEV-SRV

## F. Reglas de representación y poderes

### RN-PER-023 — Representación según modelo vigente
- descripcion: una representación o poder vincula personas según el modelo vigente del dominio.
- aplica_a: representacion_poder
- origen_principal: DEV-SRV

### RN-PER-024 — Vigencia consultable
- descripcion: la vigencia de la representación debe ser consultable para determinar su validez funcional.
- aplica_a: representacion_poder
- origen_principal: DEV-SRV

### RN-PER-025 — Baja lógica con trazabilidad de representación
- descripcion: la baja lógica de representación debe preservar trazabilidad e historial de la relación representativa.
- aplica_a: representacion_poder
- origen_principal: DEV-SRV

### RN-PER-026 — No asumir representación activa sin respaldo
- descripcion: no debe asumirse representación activa sin respaldo vigente en la información del modelo.
- aplica_a: representacion_poder
- origen_principal: DEV-SRV

## G. Reglas de roles de participación

### RN-PER-027 — Participación funcional de la persona
- descripcion: una persona puede asumir roles de participación dentro de relaciones del sistema.
- aplica_a: rol_participacion, relacion_persona_rol
- origen_principal: DEV-SRV

### RN-PER-028 — El rol no reemplaza la persona base
- descripcion: el rol de participación complementa a la persona base y no la reemplaza como sujeto del dominio.
- aplica_a: rol_participacion, relacion_persona_rol
- origen_principal: DEV-SRV

### RN-PER-029 — Baja lógica de rol con historial
- descripcion: la baja lógica del rol o de su asignación debe preservar historial y trazabilidad relacional.
- aplica_a: rol_participacion, relacion_persona_rol
- origen_principal: DEV-SRV

### RN-PER-030 — Consistencia del contexto relacional
- descripcion: la modificación del rol debe respetar el contexto relacional definido por el modelo y la relación persona-rol vigente.
- aplica_a: relacion_persona_rol
- origen_principal: SQL

## H. Reglas de consultas de persona

### RN-PER-031 — Consultas sin persistencia
- descripcion: las consultas del dominio Personas no generan efectos persistentes.
- aplica_a: consultas de persona
- origen_principal: DEV-SRV

### RN-PER-032 — Ficha integral sin redefinir reglas
- descripcion: la ficha integral debe consolidar información del dominio sin redefinir reglas ni semántica de las entidades consultadas.
- aplica_a: consultas de persona
- origen_principal: DEV-SRV

### RN-PER-033 — Consulta por documento sobre persona_documento
- descripcion: la consulta por documento debe apoyarse en persona_documento como fuente identificatoria asociada a persona.
- aplica_a: persona_documento
- origen_principal: SQL

### RN-PER-034 — Consulta por CUIT o CUIL según modelo real
- descripcion: la consulta por CUIT o CUIL debe apoyarse en persona como estructura del modelo que almacena dicho dato.
- aplica_a: persona
- origen_principal: SQL
- observaciones: cuit_cuil reside en persona según el modelo real de base de datos.

### RN-PER-035 — Trazabilidad temporal en consultas históricas
- descripcion: las consultas históricas deben respetar trazabilidad temporal y estado lógico de la información consultada.
- aplica_a: consultas de persona
- origen_principal: DEV-SRV

## Notas
- Este catálogo deriva del DEV-SRV del dominio Personas.
- No reemplaza al CAT-CU maestro.
- Las reglas aquí listadas se usan como apoyo a implementación y validación backend.
- Debe mantenerse alineado con SRV-PER del dominio y con el modelo real de base de datos.
