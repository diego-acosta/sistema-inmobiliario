# EST-ADM — Estados del dominio Administrativo

## Objetivo
Consolidar los estados persistentes y operativos relevantes del dominio administrativo para su uso consistente en validaciones, flujos y control de consistencia.

## Alcance
Este catálogo cubre estados de usuarios, credenciales, sesiones, seguridad y autorización, auditoría administrativa, configuración y parámetros, catálogos maestros y estados operativos transversales aplicados al dominio.

---

## A. Estados de usuarios y acceso

### EST-ADM-001 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: usuario, rol_administrativo, permiso, catalogo_maestro, catalogo_item, configuracion_parametro
- descripcion: la entidad se encuentra habilitada para su uso normal dentro del dominio.
- estado_inicial: sí
- estado_final: no

### EST-ADM-002 — Inactivo
- codigo: inactivo
- tipo: entidad
- aplica_a: usuario, rol_administrativo, permiso, catalogo_maestro, catalogo_item, configuracion_parametro
- descripcion: la entidad existe pero no se encuentra habilitada para uso operativo normal.
- estado_inicial: no
- estado_final: no

### EST-ADM-003 — Bloqueado
- codigo: bloqueado
- tipo: entidad
- aplica_a: usuario, credencial_usuario
- descripcion: la entidad existe pero fue bloqueada y no puede operar o autenticar.
- estado_inicial: no
- estado_final: no

### EST-ADM-004 — Suspendido
- codigo: suspendido
- tipo: entidad
- aplica_a: usuario
- descripcion: el usuario se encuentra temporalmente suspendido cuando la política administrativa lo contempla.
- estado_inicial: no
- estado_final: no
- observaciones: estado aplicable cuando el flujo operativo del dominio lo habilite.

### EST-ADM-005 — Pendiente de activación
- codigo: pendiente_activacion
- tipo: entidad
- aplica_a: usuario, credencial_usuario
- descripcion: la entidad fue creada pero aún no alcanzó estado plenamente operativo.
- estado_inicial: sí
- estado_final: no
- observaciones: se utiliza cuando el alta requiere una activación posterior.

### EST-ADM-006 — Eliminado lógico
- codigo: eliminado_logico
- tipo: entidad
- aplica_a: usuario, rol_administrativo, permiso, configuracion_parametro, catalogo_maestro, catalogo_item
- descripcion: la entidad fue invalidada lógicamente y no debe operar como vigente.
- estado_inicial: no
- estado_final: sí

### EST-ADM-007 — Vigente
- codigo: vigente
- tipo: entidad
- aplica_a: credencial_usuario, usuario_rol, rol_permiso, configuracion_contexto
- descripcion: la entidad o asignación se encuentra dentro de vigencia válida y utilizable.
- estado_inicial: sí
- estado_final: no

### EST-ADM-008 — Vencida
- codigo: vencida
- tipo: entidad
- aplica_a: credencial_usuario, configuracion_contexto
- descripcion: la entidad o valor perdió vigencia temporal.
- estado_inicial: no
- estado_final: sí

### EST-ADM-009 — Revocada
- codigo: revocada
- tipo: entidad
- aplica_a: credencial_usuario, usuario_rol, autorizacion
- descripcion: la entidad o asignación fue revocada y dejó de producir efectos.
- estado_inicial: no
- estado_final: sí

### EST-ADM-010 — Activa
- codigo: activa
- tipo: operativo
- aplica_a: sesion_usuario
- descripcion: la sesión se encuentra abierta y utilizable.
- estado_inicial: sí
- estado_final: no

### EST-ADM-011 — Cerrada
- codigo: cerrada
- tipo: operativo
- aplica_a: sesion_usuario
- descripcion: la sesión fue finalizada y no puede reabrirse.
- estado_inicial: no
- estado_final: sí

### EST-ADM-012 — Expirada
- codigo: expirada
- tipo: operativo
- aplica_a: sesion_usuario
- descripcion: la sesión dejó de ser válida por expiración temporal o política de uso.
- estado_inicial: no
- estado_final: sí

## B. Estados de seguridad, roles y permisos

### EST-ADM-013 — Permitido
- codigo: permitido
- tipo: operativo
- aplica_a: autorizacion
- descripcion: la evaluación de autorización resolvió habilitación efectiva para la operación consultada.
- estado_inicial: no
- estado_final: no

### EST-ADM-014 — Denegado
- codigo: denegado
- tipo: operativo
- aplica_a: autorizacion
- descripcion: la evaluación de autorización resolvió denegación para la operación consultada.
- estado_inicial: no
- estado_final: no

### EST-ADM-015 — Denegado explícito
- codigo: denegado_explicito
- tipo: operativo
- aplica_a: autorizacion
- descripcion: existe una denegación explícita aplicada al contexto evaluado.
- estado_inicial: no
- estado_final: no

## C. Estados de auditoría administrativa

### EST-ADM-016 — Registrado
- codigo: registrado
- tipo: entidad
- aplica_a: evento_auditoria
- descripcion: el evento de auditoría fue persistido correctamente y forma parte de la trazabilidad administrativa.
- estado_inicial: sí
- estado_final: no
- observaciones: el evento auditado es inmutable y no posee un ciclo de edición ordinario.

### EST-ADM-017 — Procesado
- codigo: procesado
- tipo: operativo
- aplica_a: evento_auditoria
- descripcion: el evento auditado fue tomado por un flujo técnico o de consolidación cuando corresponda.
- estado_inicial: no
- estado_final: sí
- observaciones: no implica edición del evento, solo avance de tratamiento técnico asociado.

## D. Estados de configuración y parámetros

### EST-ADM-018 — Reemplazado
- codigo: reemplazado
- tipo: entidad
- aplica_a: configuracion_contexto
- descripcion: el valor dejó de ser el vigente porque fue sustituido por otro en una nueva vigencia.
- estado_inicial: no
- estado_final: sí

## E. Estados de catálogos maestros

### EST-ADM-019 — Válida
- codigo: valida
- tipo: entidad
- aplica_a: jerarquia_catalogo
- descripcion: la relación jerárquica del catálogo cumple con las reglas de integridad definidas.
- estado_inicial: sí
- estado_final: no

### EST-ADM-020 — Inválida
- codigo: invalida
- tipo: entidad
- aplica_a: jerarquia_catalogo
- descripcion: la relación jerárquica del catálogo presenta inconsistencia o incumplimiento de integridad.
- estado_inicial: no
- estado_final: no

### EST-ADM-021 — Habilitado
- codigo: habilitado
- tipo: operativo
- aplica_a: disponibilidad_catalogo_sucursal, catalogo_item
- descripcion: el ítem o catálogo se encuentra habilitado en el contexto operativo correspondiente.
- estado_inicial: sí
- estado_final: no
- observaciones: aplica especialmente a disponibilidad contextual por sucursal.

### EST-ADM-022 — Deshabilitado
- codigo: deshabilitado
- tipo: operativo
- aplica_a: disponibilidad_catalogo_sucursal, catalogo_item
- descripcion: el ítem o catálogo no se encuentra habilitado en el contexto operativo correspondiente.
- estado_inicial: no
- estado_final: no
- observaciones: aplica especialmente a disponibilidad contextual por sucursal.

## F. Estados operativos transversales

### EST-ADM-023 — Éxito
- codigo: exito
- tipo: operativo
- aplica_a: procesos administrativos, operaciones write, evaluaciones
- descripcion: la operación o proceso finalizó correctamente.
- estado_inicial: no
- estado_final: sí

### EST-ADM-024 — Error
- codigo: error
- tipo: operativo
- aplica_a: procesos administrativos, operaciones write, evaluaciones
- descripcion: la operación o proceso finalizó con error y sin resultado válido.
- estado_inicial: no
- estado_final: sí

### EST-ADM-025 — Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: procesos administrativos, operaciones write sincronizables
- descripcion: la operación no pudo completarse por conflicto funcional o técnico.
- estado_inicial: no
- estado_final: sí

### EST-ADM-026 — Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: autorizacion, evaluaciones administrativas, operaciones write
- descripcion: la operación fue rechazada por validación o política del dominio.
- estado_inicial: no
- estado_final: sí

### EST-ADM-027 — Bloqueado por lock
- codigo: bloqueado_por_lock
- tipo: operativo
- aplica_a: operaciones write sensibles del dominio administrativo
- descripcion: la operación no pudo avanzar por lock lógico activo.
- estado_inicial: no
- estado_final: sí

### EST-ADM-028 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: procesos administrativos, verificaciones de integridad
- descripcion: se detectó inconsistencia en el estado o contexto del proceso evaluado.
- estado_inicial: no
- estado_final: no

### EST-ADM-029 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: control de versionado administrativo
- descripcion: la versión esperada coincide con la versión vigente al momento de validar.
- estado_inicial: no
- estado_final: no

### EST-ADM-030 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: control de versionado administrativo
- descripcion: la versión esperada no coincide con la versión vigente.
- estado_inicial: no
- estado_final: sí

### EST-ADM-031 — Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: control de idempotencia administrativa
- descripcion: la operación ya fue ejecutada válidamente con el identificador técnico informado.
- estado_inicial: no
- estado_final: no

### EST-ADM-032 — Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: control de idempotencia administrativa
- descripcion: se detectó repetición de una operación ya registrada con el mismo contenido.
- estado_inicial: no
- estado_final: sí

### EST-ADM-033 — Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: control de idempotencia administrativa
- descripcion: se detectó reutilización de op_id con diferencias incompatibles respecto de la operación original.
- estado_inicial: no
- estado_final: sí

---

## Notas
- Este catálogo deriva del DEV-SRV y del DER administrativo.
- No define lógica de negocio, solo estados posibles.
- Debe mantenerse alineado con RN-ADM y EVT-ADM.
- Sirve como base para validaciones, flujos y control de consistencia.
