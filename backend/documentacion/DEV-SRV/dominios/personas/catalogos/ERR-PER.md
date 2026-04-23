# ERR-PER — Errores del dominio Personas

## Objetivo
Definir errores funcionales y transversales del dominio Personas como apoyo a implementación backend.

## Alcance del dominio
Incluye persona base, identificación, domicilios, contactos, relaciones, representación, roles de participación y consultas del dominio.

---

## A. Errores de persona base

### ERR-PER-001 — persona_no_encontrada
- codigo: persona_no_encontrada
- descripcion: la persona indicada no existe o no está disponible en el dominio.
- tipo: funcional
- aplica_a: persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-002 — persona_inactiva
- codigo: persona_inactiva
- descripcion: la persona se encuentra inactiva y no admite la operación solicitada.
- tipo: funcional
- aplica_a: persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-003 — persona_duplicada
- codigo: persona_duplicada
- descripcion: ya existe una persona con datos que entran en conflicto con las reglas de unicidad del modelo.
- tipo: integridad
- aplica_a: persona
- origen: SQL
- es_reintento_valido: no
- observaciones: deriva de validaciones concretas del modelo real.

### ERR-PER-004 — estado_persona_invalido
- codigo: estado_persona_invalido
- descripcion: el estado actual de la persona no permite la transición u operación requerida.
- tipo: validacion
- aplica_a: persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-005 — reactivacion_persona_invalida
- codigo: reactivacion_persona_invalida
- descripcion: la persona no puede ser reactivada por inconsistencias con su estado previo o su información asociada.
- tipo: validacion
- aplica_a: persona
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de documentos identificatorios

### ERR-PER-006 — documento_identificatorio_no_encontrado
- codigo: documento_identificatorio_no_encontrado
- descripcion: el documento identificatorio indicado no existe o no pertenece a la persona consultada.
- tipo: funcional
- aplica_a: persona_documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-007 — documento_identificatorio_duplicado
- codigo: documento_identificatorio_duplicado
- descripcion: el documento identificatorio entra en conflicto con una restricción de unicidad del modelo.
- tipo: integridad
- aplica_a: persona_documento
- origen: SQL
- es_reintento_valido: no

### ERR-PER-008 — documento_principal_inexistente
- codigo: documento_principal_inexistente
- descripcion: no se encontró el documento identificado como principal para la persona.
- tipo: funcional
- aplica_a: persona_documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-009 — documento_principal_inconsistente
- codigo: documento_principal_inconsistente
- descripcion: la principalidad documental de la persona presenta una inconsistencia con el modelo.
- tipo: integridad
- aplica_a: persona_documento
- origen: SQL
- es_reintento_valido: no

### ERR-PER-010 — cambio_documento_principal_invalido
- codigo: cambio_documento_principal_invalido
- descripcion: no es válido aplicar el cambio de documento principal en el estado actual de la persona o del documento.
- tipo: validacion
- aplica_a: persona_documento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-011 — documento_identificatorio_inactivo
- codigo: documento_identificatorio_inactivo
- descripcion: el documento identificatorio se encuentra inactivo y no puede utilizarse para la operación solicitada.
- tipo: funcional
- aplica_a: persona_documento
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de domicilios

### ERR-PER-012 — domicilio_no_encontrado
- codigo: domicilio_no_encontrado
- descripcion: el domicilio indicado no existe o no pertenece a la persona consultada.
- tipo: funcional
- aplica_a: persona_domicilio
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-013 — domicilio_duplicado
- codigo: domicilio_duplicado
- descripcion: el domicilio entra en conflicto con reglas de unicidad o duplicación del modelo.
- tipo: integridad
- aplica_a: persona_domicilio
- origen: SQL
- es_reintento_valido: no
- observaciones: aplica cuando el modelo o las validaciones activas lo contemplan.

### ERR-PER-014 — domicilio_principal_inexistente
- codigo: domicilio_principal_inexistente
- descripcion: no se encontró el domicilio marcado como principal para la persona.
- tipo: funcional
- aplica_a: persona_domicilio
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-015 — domicilio_principal_inconsistente
- codigo: domicilio_principal_inconsistente
- descripcion: la principalidad de domicilios presenta una inconsistencia con el modelo o con el estado vigente.
- tipo: integridad
- aplica_a: persona_domicilio
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-016 — cambio_domicilio_principal_invalido
- codigo: cambio_domicilio_principal_invalido
- descripcion: no es válido cambiar el domicilio principal en el contexto actual de la persona.
- tipo: validacion
- aplica_a: persona_domicilio
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-017 — domicilio_inactivo
- codigo: domicilio_inactivo
- descripcion: el domicilio se encuentra inactivo y no puede quedar operativo ni principal.
- tipo: funcional
- aplica_a: persona_domicilio
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de contactos

### ERR-PER-018 — contacto_no_encontrado
- codigo: contacto_no_encontrado
- descripcion: el contacto indicado no existe o no pertenece a la persona consultada.
- tipo: funcional
- aplica_a: persona_contacto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-019 — contacto_duplicado
- codigo: contacto_duplicado
- descripcion: el contacto entra en conflicto con reglas de unicidad o duplicación del modelo.
- tipo: integridad
- aplica_a: persona_contacto
- origen: SQL
- es_reintento_valido: no
- observaciones: aplica cuando el modelo o las validaciones activas lo contemplan.

### ERR-PER-020 — contacto_principal_inexistente
- codigo: contacto_principal_inexistente
- descripcion: no se encontró el contacto marcado como principal para la persona.
- tipo: funcional
- aplica_a: persona_contacto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-021 — contacto_principal_inconsistente
- codigo: contacto_principal_inconsistente
- descripcion: la principalidad de contactos presenta una inconsistencia con el modelo o con el estado vigente.
- tipo: integridad
- aplica_a: persona_contacto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-022 — cambio_contacto_principal_invalido
- codigo: cambio_contacto_principal_invalido
- descripcion: no es válido cambiar el contacto principal en el contexto actual de la persona.
- tipo: validacion
- aplica_a: persona_contacto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-023 — contacto_inactivo
- codigo: contacto_inactivo
- descripcion: el contacto se encuentra inactivo y no puede quedar operativo ni principal.
- tipo: funcional
- aplica_a: persona_contacto
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de relaciones entre personas

### ERR-PER-024 — relacion_persona_no_encontrada
- codigo: relacion_persona_no_encontrada
- descripcion: la relación entre personas indicada no existe o no está disponible.
- tipo: funcional
- aplica_a: persona_relacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-025 — relacion_persona_duplicada
- codigo: relacion_persona_duplicada
- descripcion: ya existe una relación equivalente en conflicto con la que se intenta registrar.
- tipo: integridad
- aplica_a: persona_relacion
- origen: SQL
- es_reintento_valido: no

### ERR-PER-026 — relacion_persona_inconsistente
- codigo: relacion_persona_inconsistente
- descripcion: la relación presenta inconsistencias entre sus partes, estado o datos de vinculación.
- tipo: integridad
- aplica_a: persona_relacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-027 — tipo_relacion_invalido
- codigo: tipo_relacion_invalido
- descripcion: el tipo de relación informado no es válido para el modelo vigente.
- tipo: validacion
- aplica_a: persona_relacion
- origen: DEV-SRV
- es_reintento_valido: no
- observaciones: aplica cuando el modelo o catálogo asociado lo contempla.

### ERR-PER-028 — baja_relacion_invalida
- codigo: baja_relacion_invalida
- descripcion: no es válida la baja lógica de la relación en el estado o contexto actual.
- tipo: validacion
- aplica_a: persona_relacion
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores de representación y poderes

### ERR-PER-029 — representacion_poder_no_encontrado
- codigo: representacion_poder_no_encontrado
- descripcion: la representación o poder indicado no existe o no está disponible.
- tipo: funcional
- aplica_a: representacion_poder
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-030 — representacion_poder_invalido
- codigo: representacion_poder_invalido
- descripcion: la representación o poder no cumple las validaciones del dominio o del modelo vigente.
- tipo: validacion
- aplica_a: representacion_poder
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-031 — representacion_poder_inactiva
- codigo: representacion_poder_inactiva
- descripcion: la representación o poder se encuentra inactiva y no puede utilizarse como vigente.
- tipo: funcional
- aplica_a: representacion_poder
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-032 — representacion_sin_vigencia
- codigo: representacion_sin_vigencia
- descripcion: la representación o poder no cuenta con vigencia válida para la operación consultada.
- tipo: validacion
- aplica_a: representacion_poder
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-033 — representacion_duplicada
- codigo: representacion_duplicada
- descripcion: ya existe una representación o poder equivalente en conflicto con el nuevo registro.
- tipo: integridad
- aplica_a: representacion_poder
- origen: SQL
- es_reintento_valido: no
- observaciones: aplica cuando el modelo o validaciones concretas lo determinen.

## G. Errores de roles de participación

### ERR-PER-034 — rol_participacion_no_encontrado
- codigo: rol_participacion_no_encontrado
- descripcion: el rol de participación indicado no existe o no está disponible.
- tipo: funcional
- aplica_a: rol_participacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-035 — rol_participacion_invalido
- codigo: rol_participacion_invalido
- descripcion: el rol de participación no es válido para el contexto relacional indicado.
- tipo: validacion
- aplica_a: rol_participacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-036 — relacion_persona_rol_no_encontrada
- codigo: relacion_persona_rol_no_encontrada
- descripcion: la asignación de rol de participación indicada no existe o no está disponible.
- tipo: funcional
- aplica_a: relacion_persona_rol
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-037 — asignacion_rol_duplicada
- codigo: asignacion_rol_duplicada
- descripcion: ya existe una asignación equivalente de rol de participación para la relación indicada.
- tipo: integridad
- aplica_a: relacion_persona_rol
- origen: SQL
- es_reintento_valido: no

### ERR-PER-038 — contexto_relacional_inconsistente
- codigo: contexto_relacional_inconsistente
- descripcion: la asignación o modificación del rol no es consistente con la relación o la persona asociada.
- tipo: integridad
- aplica_a: relacion_persona_rol
- origen: DEV-SRV
- es_reintento_valido: no

## H. Errores de consultas de persona

### ERR-PER-039 — criterio_consulta_invalido
- codigo: criterio_consulta_invalido
- descripcion: los criterios de consulta informados no son válidos para el dominio.
- tipo: validacion
- aplica_a: consultas de persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-040 — persona_no_localizable
- codigo: persona_no_localizable
- descripcion: no fue posible localizar una persona con los criterios provistos.
- tipo: funcional
- aplica_a: consultas de persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-041 — ficha_integral_inconsistente
- codigo: ficha_integral_inconsistente
- descripcion: la información consolidada de la ficha integral presenta inconsistencias entre sus fuentes del dominio.
- tipo: integridad
- aplica_a: consultas de persona
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-042 — consulta_historica_invalida
- codigo: consulta_historica_invalida
- descripcion: la consulta histórica solicitada no cumple las condiciones de trazabilidad temporal del dominio.
- tipo: validacion
- aplica_a: consultas de persona
- origen: DEV-SRV
- es_reintento_valido: no

## I. Errores transversales del dominio

### ERR-PER-043 — version_esperada_invalida
- codigo: version_esperada_invalida
- descripcion: la versión esperada informada no coincide con la versión vigente del registro.
- tipo: concurrencia
- aplica_a: persona, persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder, relacion_persona_rol
- origen: CORE-EF
- es_reintento_valido: no

### ERR-PER-044 — lock_logico_activo
- codigo: lock_logico_activo
- descripcion: existe un lock lógico activo que impide la operación solicitada cuando el proceso lo requiere.
- tipo: concurrencia
- aplica_a: dominio_personas
- origen: CORE-EF
- es_reintento_valido: sí
- observaciones: aplica cuando exista política explícita de lock para el proceso involucrado.

### ERR-PER-045 — op_id_duplicado
- codigo: op_id_duplicado
- descripcion: la operación ya fue registrada con el mismo op_id y mismo contenido.
- tipo: concurrencia
- aplica_a: dominio_personas
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-PER-046 — op_id_duplicado_con_payload_distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el op_id ya existe asociado a un payload distinto y genera conflicto técnico.
- tipo: concurrencia
- aplica_a: dominio_personas
- origen: CORE-EF
- es_reintento_valido: no

### ERR-PER-047 — conflicto_concurrencia
- codigo: conflicto_concurrencia
- descripcion: se detectó un conflicto de concurrencia incompatible con la operación solicitada.
- tipo: concurrencia
- aplica_a: dominio_personas
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-PER-048 — entidad_inactiva
- codigo: entidad_inactiva
- descripcion: la entidad del dominio se encuentra inactiva y no admite la operación requerida.
- tipo: funcional
- aplica_a: persona_documento, persona_domicilio, persona_contacto, persona_relacion, representacion_poder, rol_participacion, relacion_persona_rol
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-PER-049 — integridad_relacional_invalida
- codigo: integridad_relacional_invalida
- descripcion: existe una inconsistencia de integridad entre entidades relacionadas del dominio Personas.
- tipo: integridad
- aplica_a: persona_relacion, representacion_poder, relacion_persona_rol
- origen: SQL
- es_reintento_valido: no

### ERR-PER-050 — inconsistencia_dominio_personas
- codigo: inconsistencia_dominio_personas
- descripcion: se detectó una inconsistencia interna del dominio Personas que impide completar la operación.
- tipo: integridad
- aplica_a: dominio_personas
- origen: DEV-SRV
- es_reintento_valido: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Personas.
- No reemplaza al CAT-CU maestro.
- Los errores aquí listados se usan como apoyo a implementación, validación y manejo consistente de respuestas backend.
- Debe mantenerse alineado con CU-PER, RN-PER y con el modelo real de base de datos.
