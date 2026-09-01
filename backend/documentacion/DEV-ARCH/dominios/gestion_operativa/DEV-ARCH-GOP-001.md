# DEV-ARCH-GOP-001 — Gestión Operativa: arquitectura del MVP inicial de Tarea

## 0. Metadatos

- **Documento:** DEV-ARCH-GOP-001
- **Dominio:** gestion_operativa
- **Versión:** 1.0
- **Estado:** Propuesto para aprobación
- **Issue:** #523
- **Naturaleza:** Arquitectura formal; no implementa DER, SQL, API ni runtime
- **Baseline auditado:** main en 3a501e299a0fc258fbd5599f3e3d0fdbf5f426f8

## 1. Propósito

Este documento define la arquitectura formal del MVP inicial de Tarea. Convierte en contrato arquitectónico el freeze funcional GOP-FREEZE-001 y las decisiones cerradas por #490, #491, #492, #493 y #507. El primer runtime es exclusivamente humano.

La separación de dominios es obligatoria: gestion_operativa no es operativo. Gestión Operativa gobierna el seguimiento interno; Administrativo gobierna identidad y autorización humanas; Operativo gobierna sucursal e instalación; Técnico/CORE-EF/Sync gobierna infraestructura distribuida.

## 2. Estado y trazabilidad

#489 y #507 están cerrados/completados. #523 permanece abierto y es el owner de este documento. #522 permanece abierto, no bloquea el MVP humano y debe resolverse antes de habilitar automatización u origen SISTEMA.

Fuentes principales: AGENTS.md, DEV-ARCH-GEN-001, DEV-ARCH-ADM-001, DEV-ARCH-OPE-001, CORE-EF-001, GOP-FREEZE-001, #469/#470, #490–#493, #507, #510/PR #521 y #511/PR #512.

El runtime portable de #510 admite saltos de versión para `administrativo.usuario`, pero esa política pertenece a ese aggregate y no constituye una regla transversal. GOP conserva la continuidad estricta congelada para Tarea: una mutación local confirmada avanza exactamente `Vn → Vn+1`, y una recepción remota con gap no adelanta el snapshot hasta resolver la continuidad conforme al contrato Técnico posterior. No se usan timestamps como autoridad ni LWW.

## 3. Fuentes y prevalencia

Ante contradicción rige: AGENTS.md; DEV-ARCH vigente; SQL real; runtime real; tests reales; issues/PR vigentes; GOP-FREEZE-001; PROJECT-STATUS; CODEX-WORKFLOW; documentación histórica. Toda contradicción se declara; no se reconcilia silenciosamente.

## 4. Clasificación semántica, ownership y límites

La taxonomía semántica congelada por `GOP-FREEZE-001` se preserva explícitamente y es independiente de la naturaleza técnica definida después en la sección 6:

| Concepto/capacidad | Clasificación semántica |
| --- | --- |
| Tarea | Núcleo del dominio |
| ComentarioTarea | Núcleo del dominio |
| HistorialTarea | Núcleo del dominio |
| Identidad y autorización provistas por Administrativo | Soporte transversal |
| Metadata, versionado, idempotencia, procedencia técnica, outbox, inbox, sync y demás capacidades CORE-EF/Técnico aplicables | Soporte transversal |
| Antiguos `CU-OPER-*` y cualquier modelo legacy de tareas | Compatibilidad heredada / documentación histórica desalineada; no se adopta como modelo principal de Tareas |

Esta clasificación no sustituye aggregate boundaries ni decisiones de persistencia: `Tarea` sigue siendo aggregate root, `ComentarioTarea` append sincronizable independiente e `HistorialTarea` append funcional estructurado. Ninguna estructura heredada de `operativo` se adopta como contrato vigente de `gestion_operativa`.

| Concepto | Owner | Contrato GOP |
| --- | --- | --- |
| Tarea, ComentarioTarea, HistorialTarea | Gestión Operativa | Define semántica, invariantes y evolución funcional |
| Lifecycle, prioridad, fecha objetivo, asignación | Gestión Operativa | Parte del snapshot o de sus appends |
| Usuario, usuario.uid_global, AuthenticatedPrincipal | Administrativo | GOP referencia y consume |
| Roles, permisos y autorización humana | Administrativo | GOP declara capacidades, no crea IAM |
| Sucursal e instalación | Operativo | GOP referencia identidades portables |
| op_id, operacion_idempotente, outbox e inbox | Técnico / CORE-EF / Sync | GOP reutiliza |
| Retry, PENDING_DEPENDENCY, operation scope, lease y fencing | Técnico / Sync | GOP aporta sólo resultado funcional |
| Transporte | Técnico / Sync | Fuera del dominio GOP |

Quedan preservadas las desigualdades USUARIO ≠ PERSONA, USUARIO ≠ INSTALACION, SUCURSAL ≠ INSTALACION, uid_global ≠ PK local, operacion_idempotente ≠ outbox y outbox ≠ inbox.

## 5. Alcance del MVP

El MVP permite crear y operar Tareas humanas, asignarlas, priorizarlas, fijar fecha objetivo, transicionar su lifecycle, comentar y consultar historial. La creación manual cumple:

- autenticación Bearer resuelta a un AuthenticatedPrincipal vigente;
- origen = USUARIO;
- id_usuario_creador derivado exclusivamente de AuthenticatedPrincipal.id_usuario;
- generador_sistema = NULL;
- si propone una sucursal, requiere administración vigente sobre esa sucursal y autorización efectiva de Administrativo;
- si propone scope global, requiere alcance global administrativo vigente y autorización efectiva de Administrativo.

No se habilita origen SISTEMA, baja lógica pública, alertas, automatización, scheduler, notificaciones ni infraestructura transversal nueva.

## 6. Modelo conceptual

Tarea es el aggregate root y contiene el snapshot funcional versionado. ComentarioTarea es un append sincronizable independiente asociado a Tarea. HistorialTarea es un append estructurado interno, generado atómicamente por commands que mutan Tarea.

| Elemento | Naturaleza | Identidad/versionado |
| --- | --- | --- |
| Tarea | Aggregate root | PK local + uid_global; version_registro del snapshot |
| ComentarioTarea | Append sincronizable independiente | PK local futura + uid_global y version_registro propios |
| HistorialTarea | Append funcional estructurado | Diseño físico diferido al DER |

## 7. Aggregate boundaries

Tarea protege lifecycle, responsable requerido para EN_CURSO/COMPLETADA, terminalidad, prioridad, fecha objetivo, scope de sucursal, creador y coherencia de fecha_finalizacion.

ComentarioTarea no integra el lock optimista del snapshot: dos comentarios válidos pueden coexistir; no incrementan Tarea.version_registro. Es un append independiente porque posee identidad distribuida, versionado CORE-EF, idempotencia y evento propios.

HistorialTarea no es root de mutación pública. Se genera desde el command dueño y no admite command autónomo. Su atomicidad con Tarea preserva la explicación funcional del cambio sin convertir el dominio en event sourcing.

## 8. Identidades

| Concepto | Identidad local | Identidad portable | Owner |
| --- | --- | --- | --- |
| Tarea | id_tarea | Tarea.uid_global | GOP |
| ComentarioTarea | PK local a resolver en DER | ComentarioTarea.uid_global | GOP |
| Creador | id_usuario local | usuario.uid_global | Administrativo |
| Responsable | id_usuario local nullable | usuario.uid_global nullable | Administrativo |
| Actor de historial | id_usuario local cuando exista | usuario.uid_global cuando exista | Administrativo |
| Autor de comentario | id_usuario local | usuario.uid_global | Administrativo |
| Sucursal | id_sucursal local nullable | sucursal.uid_global nullable | Operativo |
| Instalación | id_instalacion local | instalacion.uid_global | Operativo (exclusivo); Técnico sólo consume identidad/contexto para procedencia, validación y sync transversal, sin adquirir ownership ni semántica de instalación |

Todo uid_global es obligatorio para la entidad sincronizable, único, inmutable, no reutilizable y generado al crearla. op_id identifica la operación y nunca se convierte en identidad de Tarea o Comentario. Ninguna PK local viaja entre instalaciones.

## 9. Snapshot conceptual de Tarea

| Atributo | Senántica | Mutable | Nullable | Versiona Tarea |
| --- | --- | --- | --- | --- |
| origen | USUARIO en MVP; SISTEMA reservado | No | No | No después del alta |
| creador | Autor humano del alta | No | No para USUARIO | No después del alta |
| generador_sistema | Descriptor futuro de generación | No | Sí en USUARIO | No después del alta |
| título | Asunto breve obligatorio y con contenido funcional real; nunca cadena vacía | Sí en estados editables | No | Sí |
| descripción | Detalle funcional | Sí en estados editables | Sí; opcional | Sí |
| prioridad | BAJA/NORMAL/ALTA/URGENTE | Sí | No; NORMAL por defecto | Sí |
| responsable | Usuario 0..1 | Sí | Sí | Sí |
| fecha_objetivo | Fecha funcional DATE | Sí | Sí | Sí |
| estado | Lifecycle funcional | Sólo transición válida | No | Sí |
| fecha_finalizacion | Finalización vigente generada por servidor | Derivada por lifecycle | Sí | Sí con transición |
| sucursal funcional | Scope; NULL significa global | No en MVP | Sí | No después del alta |
| deleted_at | Baja lógica técnica | Sólo command futuro | Sí | Sí |
| metadata CORE-EF | Identidad, versión y procedencia | Según CORE-EF | Según contrato | Según mutación |

No se congelan nombres físicos, longitudes, tipos SQL ni DTO.

## 10. Lifecycle

Estados únicos: PENDIENTE, EN_CURSO, COMPLETADA y CANCELADA. PENDIENTE es el único inicial.

| Desde | Hacia | Condición |
| --- | --- | --- |
| PENDIENTE | EN_CURSO | Responsable vigente/elegible obligatorio |
| PENDIENTE | COMPLETADA | Responsable vigente/elegible obligatorio |
| PENDIENTE | CANCELADA | Autorización aplicable |
| EN_CURSO | PENDIENTE | Responsable vigente/elegible o administración aplicable |
| EN_CURSO | COMPLETADA | Responsable vigente/elegible obligatorio |
| EN_CURSO | CANCELADA | Autorización aplicable |
| COMPLETADA | PENDIENTE | Reapertura explícita con motivo obligatorio y postestado válido |
| CANCELADA | — | No reabre |

COMPLETADA y CANCELADA congelan el snapshot, salvo comentarios y la reapertura permitida de COMPLETADA. CANCELADA es estado funcional; deleted_at es baja técnica y nunca son equivalentes.

Completar genera en servidor la `fecha_finalizacion` vigente. Reabrir limpia la `fecha_finalizacion` corriente, conserva la finalización anterior en HistorialTarea y debe dejar un postestado activo válido. Si el responsable registrado sigue elegible puede conservarse; si perdió elegibilidad, la misma operación lógica debe dejar responsable NULL o reemplazarlo por uno elegible. Nunca puede resultar una Tarea activa con responsable inelegible. No existe autoasignación.

## 11. Prioridad y fechas

El orden es BAJA < NORMAL < AL