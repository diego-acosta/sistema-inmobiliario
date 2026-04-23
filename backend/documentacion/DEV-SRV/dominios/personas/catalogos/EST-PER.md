# EST-PER — Estados del dominio Personas

## Objetivo
Definir los estados relevantes del dominio Personas como apoyo a implementación backend.

## Alcance del dominio
Incluye persona base, identificación, domicilios, contactos, relaciones, representación, roles de participación y estados operativos transversales del dominio.

---

## A. Estados de persona base

### EST-PER-001 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: persona
- descripcion: la persona se encuentra operativa y disponible para las operaciones permitidas del dominio.
- estado_inicial: sí
- estado_final: no

### EST-PER-002 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: persona
- descripcion: la persona permanece registrada pero no se encuentra operativa para determinadas acciones del dominio.
- estado_inicial: no
- estado_final: no

### EST-PER-003 — Dada de baja
- codigo: dada_de_baja
- tipo: entidad
- aplica_a: persona
- descripcion: la persona fue dada de baja lógica y solo conserva trazabilidad e historial.
- estado_inicial: no
- estado_final: sí
- observaciones: se apoya en la lógica de baja y trazabilidad del dominio.

## B. Estados de documentos identificatorios

### EST-PER-004 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: persona_documento
- descripcion: el documento identificatorio se encuentra operativo dentro del dominio.
- estado_inicial: sí
- estado_final: no

### EST-PER-005 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: persona_documento
- descripcion: el documento identificatorio permanece registrado pero no debe utilizarse como activo.
- estado_inicial: no
- estado_final: no

### EST-PER-006 — Principal
- codigo: principal
- tipo: entidad
- aplica_a: persona_documento
- descripcion: el documento está marcado como principal para la persona.
- estado_inicial: no
- estado_final: no
- observaciones: deriva del indicador de principalidad del modelo.

### EST-PER-007 — Secundario
- codigo: secundario
- tipo: entidad
- aplica_a: persona_documento
- descripcion: el documento está asociado a la persona pero no es el principal.
- estado_inicial: sí
- estado_final: no
- observaciones: se define por oposición a la principalidad.

### EST-PER-008 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: persona_documento
- descripcion: el documento fue dado de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## C. Estados de domicilios

### EST-PER-009 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: persona_domicilio
- descripcion: el domicilio se encuentra operativo dentro del dominio.
- estado_inicial: sí
- estado_final: no

### EST-PER-010 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: persona_domicilio
- descripcion: el domicilio permanece registrado pero no debe utilizarse como vigente.
- estado_inicial: no
- estado_final: no

### EST-PER-011 — Principal
- codigo: principal
- tipo: entidad
- aplica_a: persona_domicilio
- descripcion: el domicilio está marcado como principal para la persona.
- estado_inicial: no
- estado_final: no
- observaciones: deriva del indicador de principalidad del modelo.

### EST-PER-012 — Secundario
- codigo: secundario
- tipo: entidad
- aplica_a: persona_domicilio
- descripcion: el domicilio está asociado a la persona pero no es el principal.
- estado_inicial: sí
- estado_final: no
- observaciones: se define por oposición a la principalidad.

### EST-PER-013 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: persona_domicilio
- descripcion: el domicilio fue dado de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## D. Estados de contactos

### EST-PER-014 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: persona_contacto
- descripcion: el contacto se encuentra operativo dentro del dominio.
- estado_inicial: sí
- estado_final: no

### EST-PER-015 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: persona_contacto
- descripcion: el contacto permanece registrado pero no debe utilizarse como vigente.
- estado_inicial: no
- estado_final: no

### EST-PER-016 — Principal
- codigo: principal
- tipo: entidad
- aplica_a: persona_contacto
- descripcion: el contacto está marcado como principal para la persona.
- estado_inicial: no
- estado_final: no
- observaciones: deriva del indicador de principalidad del modelo.

### EST-PER-017 — Secundario
- codigo: secundario
- tipo: entidad
- aplica_a: persona_contacto
- descripcion: el contacto está asociado a la persona pero no es el principal.
- estado_inicial: sí
- estado_final: no
- observaciones: se define por oposición a la principalidad.

### EST-PER-018 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: persona_contacto
- descripcion: el contacto fue dado de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## E. Estados de relaciones entre personas

### EST-PER-019 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: persona_relacion
- descripcion: la relación entre personas se encuentra vigente y operativa.
- estado_inicial: sí
- estado_final: no

### EST-PER-020 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: persona_relacion
- descripcion: la relación permanece registrada pero no debe tratarse como vigente.
- estado_inicial: no
- estado_final: no

### EST-PER-021 — Dada de baja
- codigo: dada_de_baja
- tipo: entidad
- aplica_a: persona_relacion
- descripcion: la relación fue dada de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## F. Estados de representación y poderes

### EST-PER-022 — Vigente
- codigo: vigente
- tipo: entidad
- aplica_a: representacion_poder
- descripcion: la representación o poder se encuentra vigente para su uso funcional.
- estado_inicial: sí
- estado_final: no

### EST-PER-023 — No vigente
- codigo: no_vigente
- tipo: entidad
- aplica_a: representacion_poder
- descripcion: la representación o poder existe pero no cuenta con vigencia aplicable.
- estado_inicial: no
- estado_final: no

### EST-PER-024 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: representacion_poder
- descripcion: la representación o poder no se encuentra operativa dentro del dominio.
- estado_inicial: no
- estado_final: no
- observaciones: el modelo expone estado_representacion.

### EST-PER-025 — Dada de baja
- codigo: dada_de_baja
- tipo: entidad
- aplica_a: representacion_poder
- descripcion: la representación o poder fue dada de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## G. Estados de roles de participación

### EST-PER-026 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: rol_participacion
- descripcion: el rol de participación se encuentra vigente y disponible para asignación o uso.
- estado_inicial: sí
- estado_final: no

### EST-PER-027 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: rol_participacion
- descripcion: el rol de participación existe pero no se encuentra operativo.
- estado_inicial: no
- estado_final: no
- observaciones: el modelo expone estado_rol.

### EST-PER-028 — Dado de baja
- codigo: dado_de_baja
- tipo: entidad
- aplica_a: relacion_persona_rol
- descripcion: la asignación de rol de participación fue dada de baja lógica y solo conserva historial.
- estado_inicial: no
- estado_final: sí

## H. Estados operativos transversales del dominio

### EST-PER-029 — Éxito
- codigo: exito
- tipo: operativo
- aplica_a: operaciones del dominio
- descripcion: la operación del dominio se ejecutó correctamente.
- estado_inicial: no
- estado_final: sí

### EST-PER-030 — Error
- codigo: error
- tipo: operativo
- aplica_a: operaciones del dominio
- descripcion: la operación del dominio finalizó con error.
- estado_inicial: no
- estado_final: sí

### EST-PER-031 — Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: operaciones sincronizables
- descripcion: la operación encontró un conflicto de negocio o concurrencia incompatible.
- estado_inicial: no
- estado_final: sí

### EST-PER-032 — Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: operaciones del dominio
- descripcion: la operación fue rechazada por validación o regla del dominio.
- estado_inicial: no
- estado_final: sí

### EST-PER-033 — Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: operaciones del dominio
- descripcion: la operación quedó impedida por una condición de bloqueo aplicable.
- estado_inicial: no
- estado_final: no

### EST-PER-034 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: operaciones y lecturas del dominio
- descripcion: la operación o la información relevada presenta una inconsistencia interna del dominio.
- estado_inicial: no
- estado_final: no

### EST-PER-035 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: operaciones sincronizables
- descripcion: la versión esperada coincide con la versión vigente del registro.
- estado_inicial: no
- estado_final: no

### EST-PER-036 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: operaciones sincronizables
- descripcion: la versión esperada no coincide con la versión vigente del registro.
- estado_inicial: no
- estado_final: sí

### EST-PER-037 — Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: idempotencia de operaciones
- descripcion: la operación ya fue ejecutada válidamente para el op_id informado.
- estado_inicial: no
- estado_final: sí
- observaciones: corresponde al tratamiento idempotente de reintentos válidos.

### EST-PER-038 — Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: idempotencia de operaciones
- descripcion: se detectó una repetición de operación con el mismo op_id y mismo contenido.
- estado_inicial: no
- estado_final: sí

### EST-PER-039 — Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: idempotencia de operaciones
- descripcion: se detectó un op_id repetido con contenido distinto y conflicto técnico asociado.
- estado_inicial: no
- estado_final: sí

## Notas
- Este catálogo deriva del DEV-SRV del dominio Personas.
- No reemplaza al CAT-CU maestro.
- Los estados aquí listados se usan como apoyo a implementación, validación y consistencia del dominio backend.
- Debe mantenerse alineado con CU-PER, RN-PER, ERR-PER, EVT-PER y con el modelo real de base de datos.
