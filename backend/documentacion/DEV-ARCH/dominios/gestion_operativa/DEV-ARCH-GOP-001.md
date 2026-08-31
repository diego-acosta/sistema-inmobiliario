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

Existe una diferencia histórica entre el texto de continuidad estricta del freeze y el runtime portable materializado por #510: este último admite saltos de versión con snapshot autosuficiente. Por prevalencia de arquitectura/runtime real y por el contrato de #523, GOP adopta esa convergencia sin modificar el protocolo Técnico ni usar timestamps como autoridad.

## 3. Fuentes y prevalencia

Ante contradicción rige: AGENTS.md; DEV-ARCH vigente; SQL real; runtime real; tests reales; issues/PR vigentes; GOP-FREEZE-001; PROJECT-STATUS; CODEX-WORKFLOW; documentación histórica. Toda contradicción se declara; no se reconcilia silenciosamente.

## 4. Ownership y límites

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

El MVP permite crear y operar Tareas humanas, asignarlas, priorizarlas, fijar fecha objetivo, transicionar su lifecycle, comentar y consultar historial. La creación cumple:

- origen = USUARIO;
- id_usuario_creador derivado de AuthenticatedPrincipal.id_usuario;
- generador_sistema = NULL.

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
| Actor de historial | id_usuario local | usuario.uid_global | Administrativo |
| Autor de comentario | id_usuario local | usuario.uid_global | Administrativo |
| Sucursal | id_sucursal local nullable | sucursal.uid_global nullable | Operativo |
| Instalación | id_instalacion local | instalacion.uid_global | Operativo/Técnico |

Todo uid_global es obligatorio para la entidad sincronizable, único, inmutable, no reutilizable y generado al crearla. op_id identifica la operación y nunca se convierte en identidad de Tarea o Comentario. Ninguna PK local viaja entre instalaciones.

## 9. Snapshot conceptual de Tarea

| Atributo | Semántica | Mutable | Nullable | Versiona Tarea |
| --- | --- | --- | --- | --- |
| origen | USUARIO en MVP; SISTEMA reservado | No | No | No después del alta |
| creador | Autor humano del alta | No | No para USUARIO | No después del alta |
| generador_sistema | Descriptor futuro de generación | No | Sí en USUARIO | No después del alta |
| título | Asunto breve | Sí en estados editables | No | Sí |
| descripción | Detalle funcional | Sí en estados editables | Según freeze | Sí |
| prioridad | BAJA/NORMAL/ALTA/URGENTE | Sí | No; NORMAL por defecto | Sí |
| responsable | Usuario 0..1 | Sí | Sí | Sí |
| fecha_objetivo | Fecha funcional DATE | Sí | Sí | Sí |
| estado | Lifecycle funcional | Sólo transición válida | No | Sí |
| fecha_finalizacion | Resultado de completar | Derivada por lifecycle | Sí | Sí con transición |
| sucursal funcional | Scope; NULL significa global | No en MVP | Sí | No después del alta |
| deleted_at | Baja lógica técnica | Sólo command futuro | Sí | Sí |
| metadata CORE-EF | Identidad, versión y procedencia | Según CORE-EF | Según contrato | Según mutación |

No se congelan nombres físicos, longitudes, tipos SQL ni DTO.

## 10. Lifecycle

Estados únicos: PENDIENTE, EN_CURSO, COMPLETADA y CANCELADA. PENDIENTE es el único inicial.

| Desde | Hacia | Condición |
| --- | --- | --- |
| PENDIENTE | EN_CURSO | Responsable obligatorio |
| PENDIENTE | COMPLETADA | Responsable obligatorio |
| PENDIENTE | CANCELADA | Autorización aplicable |
| EN_CURSO | PENDIENTE | Transición explícita |
| EN_CURSO | COMPLETADA | Responsable obligatorio |
| EN_CURSO | CANCELADA | Autorización aplicable |
| COMPLETADA | PENDIENTE | Reapertura explícita con motivo obligatorio |
| CANCELADA | — | No reabre |

COMPLETADA y CANCELADA congelan el snapshot, salvo comentarios y la reapertura permitida de COMPLETADA. CANCELADA es estado funcional; deleted_at es baja técnica y nunca son equivalentes.

## 11. Prioridad y fechas

El orden es BAJA < NORMAL < ALTA < URGENTE y NORMAL es el default conceptual. fecha_objetivo es opcional y representa DATE funcional, no timestamp CORE-EF. VENCIDA se deriva cuando la fecha objetivo ya pasó según fecha de servidor en Argentina/Buenos_Aires y la tarea no está terminal; no se persiste como estado.

## 12. Creador, responsable y actores

El creador humano se toma exclusivamente de Bearer → AuthenticatedPrincipal.id_usuario, conserva FK local y viaja como usuario.uid_global. Es inmutable. La baja o desactivación posterior del usuario no invalida la Tarea ni elimina su identidad histórica.

El responsable es 0..1, puede asignarse, reasignarse o quitarse mientras el lifecycle lo permita. Sin responsable no se ingresa a EN_CURSO ni COMPLETADA. Un usuario desactivado sigue siendo resoluble históricamente, aunque su elegibilidad para nuevas asignaciones se evalúa en origen.

Actores de historial y autores de comentario conservan referencia local más identidad portable. El receptor no reevalúa retrospectivamente roles, permisos, asignación ni relaciones humanas que cambiaron después del hecho confirmado.

## 13. Scope de sucursal

Tarea.id_sucursal es scope funcional, nullable e inmutable en el MVP. NULL significa Tarea global, no instalación desconocida ni sucursal implícita. Una sucursal concreta habilita filtrado, visibilidad y autorización por ese scope.

X-Sucursal-Id y X-Instalacion-Id son contexto/procedencia técnica del command. No asignan Tarea.id_sucursal, no autentican personas y no convierten instalación en scope funcional. En sync, la sucursal se referencia por sucursal.uid_global.

## 14. Visibilidad y autorización humana

GOP declara capacidades conceptuales y consume la infraestructura de Administrativo; no crea ACL, roles ni tablas de permisos.

| Capacidad | Regla conceptual |
| --- | --- |
| Consultar | Creador; responsable elegible; consulta por scope; administración por scope |
| Crear | Permiso aplicable al scope global o de sucursal |
| Editar | Administración del scope; responsable elegible cuando el freeze lo permite |
| Asignar/reasignar | Administración del scope |
| Completar | Administración del scope o responsable elegible |
| Cancelar | Administración del scope según freeze |
| Reabrir | Administración del scope; motivo obligatorio |
| Comentar | Actor autorizado en origen, incluidos estados terminales |
| Baja lógica | Capacidad técnica futura, no expuesta en el MVP |

Tener un permiso no implica automáticamente acceso a todas las Tareas. Para una Tarea global se exige capacidad global; para una Tarea de sucursal se evalúa el alcance de esa sucursal, además de los vínculos de creador/responsable previstos. Los códigos definitivos quedan para DEV-SRV/DEV-API y Administrativo.

## 15. Comentarios

ComentarioTarea es append-only en el MVP: no se edita ni se borra funcionalmente; una corrección es otro append. Tiene uid_global propio, único, inmutable y no reutilizable, y version_registro propio que nace en 1 y normalmente permanece en 1.

Agregar comentario:

- no incrementa Tarea.version_registro;
- no requiere If-Match-Version de Tarea;
- conserva Tarea.uid_global, autor portable, op_id y causalidad suficiente;
- produce persistencia, outbox y receipt en una transacción;
- es válido en PENDIENTE, EN_CURSO, COMPLETADA y CANCELADA con autorización;
- no reabre, no completa, no cancela ni altera fecha_finalizacion.

Comentario y baja causalmente concurrentes conservan ambos efectos. Un comentario confirmado antes de la baja converge aunque la baja llegue primero. Un intento causalmente posterior a la baja no es una mutación ordinaria válida. No se crean placeholders ni LWW.

## 16. Historial funcional

HistorialTarea registra cambios funcionales estructurados; no es CORE-EF, auditoría administrativa, outbox, inbox ni operacion_idempotente.

Cada entrada conserva conceptualmente tipo de cambio, actor local y portable, instante, op_id causal, valores anterior/nuevo cuando corresponda y motivo obligatorio de reapertura. Se genera para creación, cambios materiales de contenido, asignación, prioridad, fecha objetivo, estado, completar, cancelar, reabrir y baja lógica futura.

Los comentarios no se duplican como historial. La consulta puede presentar ambos flujos sin fusionar sus persistencias. No se congela PK ni layout SQL.

## 17. CORE-EF

Tarea aplica uid_global, version_registro, created_at, updated_at, deleted_at, id_instalacion_origen, id_instalacion_ultima_modificacion, op_id_alta y op_id_ultima_modificacion. ComentarioTarea aplica identidad, versión y metadata CORE-EF correspondientes a una entidad sincronizable.

Quién actuó se expresa con usuario; dónde se ejecutó se expresa con instalación. La metadata transversal no se duplica como campos funcionales. Tarea nace en versión 1; cada mutación material incrementa exactamente 1; la baja lógica también incrementa versión.

## 18. Versionado y CAS

| Operación | Incrementa Tarea | If-Match-Version | Motivo |
| --- | --- | --- | --- |
| Crear | Nace en 1 | No | No hay versión previa |
| Modificar título/descripción | Sí | Sí | Muta snapshot |
| Asignar/reasignar/desasignar | Sí | Sí | Muta responsable |
| Cambiar prioridad | Sí | Sí | Muta snapshot |
| Cambiar fecha objetivo | Sí | Sí | Muta snapshot |
| Cambiar estado/completar/cancelar | Sí | Sí | Muta lifecycle |
| Reabrir | Sí | Sí | Muta lifecycle y exige motivo |
| Agregar comentario | No | No sobre Tarea | Append independiente |
| Baja lógica futura | Sí | Sí | Mutación técnica sincronizable |

Un command material produce como máximo un incremento aun si cambia varios atributos coherentes. No se congela el mecanismo SQL de CAS.

## 19. Idempotencia

GOP reutiliza public.operacion_idempotente y el contrato #469/#470: claim → EXECUTE, REPLAY o CONFLICT → complete. No crea ledger propio.

Cada command futuro define command_code, target_type, target_uid o target_key, payload material canonicalizable, versión esperada cuando aplica, fingerprint, snapshot durable de replay y completion. El claim ocurre antes del efecto dentro de la misma transacción coordinada. Mismo op_id y envelope compatible devuelve replay sin repetir efecto/outbox; incompatibilidad material produce conflicto.

## 20. Fronteras transaccionales

El application service/orchestrator es owner de commit y rollback. Los repositories no hacen commit ni rollback internos.

Para una mutación exitosa, claim idempotente, efecto funcional, historial aplicable, outbox y receipt durable comparten una única transacción. Para comentario, la unidad es claim + comentario + outbox + receipt. Un fallo previo al commit revierte todos los efectos y permite retry contractual.

## 21. Eventos y outbox

La estrategia preferida es evento por command material con snapshot resultante y descriptor causal. Evita depender de parches parciales para saltos de versión y conserva intención sin adoptar event sourcing.

Se prevén clases conceptuales para creación, modificación, asignación, prioridad, fecha objetivo, transición de estado, reapertura, comentario y baja lógica futura. Los nombres EVT, numeración, schemas y routing quedan para artefactos posteriores. Consultas no generan outbox.

## 22. Payload portable

Puede contener únicamente uid_global, versiones, datos funcionales necesarios, op_id, procedencia portable y causalidad suficiente. Usa Tarea.uid_global, ComentarioTarea.uid_global, usuario.uid_global para creador/responsable/actor/autor, sucursal.uid_global e instalacion.uid_global.

Se prohíben PK locales, Bearer, passwords, credenciales, sesiones, roles, permisos, SQL, DSN y secretos. El payload no confía en timestamps para decidir autoridad.

## 23. Recepción e inbox

Se reutiliza #512:

- Delivery = (event_id, consumer);
- Operation = (consumer, op_id);
- Attempt = attempt_id.

Técnico conserva retained envelope, policy default-deny, claim/reclaim, lease, fencing, retry y operation scope. GOP valida semántica, resuelve referencias, aplica snapshot/append, clasifica conflicto y devuelve resultado funcional tipado. El applicator usa la Session provista y no confirma transacciones por su cuenta.

## 24. PENDING_DEPENDENCY

Una referencia portable requerida, válida y temporalmente ausente produce PENDING_DEPENDENCY. No hay aplicación parcial ni placeholder.

| Referencia | Cuándo puede quedar pendiente |
| --- | --- |
| Creador | usuario.uid_global aún no materializado |
| Responsable | usuario.uid_global no resoluble cuando está presente |
| Actor/autor | identidad humana requerida aún ausente |
| Sucursal | sucursal.uid_global concreta aún ausente |
| Instalación | procedencia portable requerida aún ausente |
| Tarea padre | Comentario llega antes que Tarea |

Payload inválido o referencia permanentemente inválida produce rechazo según contrato Técnico; divergencia material produce conflicto; ausencia temporal por sí sola no produce ninguno.

## 25. Conflicto, replay y obsolescencia

| Entrada remota | Resultado |
| --- | --- |
| Versión inferior | Obsoleta; no revierte estado |
| Misma versión y mismo contenido | Replay/duplicado seguro |
| Misma versión y distinto contenido | Conflicto material |
| Versión superior válida | Aplicar |
| Salto de versión con snapshot autosuficiente | Aplicar si resuelve referencias y satisface invariantes |
| Salto no autosuficiente | No aplicar; clasificar según dependencia/validez |
| deleted_at de versión superior | Aplicar baja sin convertir lifecycle |
| Timestamp más nuevo | Sin autoridad por sí mismo |
| Comentario independiente | Converge por su uid_global, versión y op_id propios |

LWW está prohibido. Los estados terminales no autorizan sobrescrituras inválidas: el snapshot entrante debe ser coherente con lifecycle y causalidad.

## 26. Baja lógica

deleted_at es baja técnica, distinta de CANCELADA. No hay DELETE físico. La baja futura es sincronizable, versionada, idempotente, usa CAS, genera outbox y conserva Tarea, comentarios e historial. No restaura ni cambia el lifecycle. No se expone en el primer MVP y la restauración queda fuera de alcance.

Las queries ordinarias excluyen registros dados de baja salvo vistas técnicas/autorizadas. Una baja recibida no elimina appends válidos anteriores o concurrentes.

## 27. Origen SISTEMA futuro

El modelo debe poder proteger esta invariante:

| origen | creador | generador_sistema |
| --- | --- | --- |
| USUARIO | Obligatorio | NULL |
| SISTEMA | NULL | Obligatorio |

Sólo USUARIO se acepta en el primer runtime. generador_sistema es un descriptor funcional mínimo, no una credencial ni identidad técnica. #522 debe cerrar autenticación/autorización técnica antes de habilitar SISTEMA. No se crean service accounts, API keys, usuario SYSTEM ni Bearer artificial.

## 28. Consultas esperadas

La arquitectura debe soportar lecturas de pendientes, responsable, creador, estado, sucursal, prioridad, fecha objetivo, vencidas derivadas, completadas/canceladas, comentarios e historial. El DER evaluará índices sobre uid_global, filtros de lifecycle y baja, responsable, creador, sucursal, prioridad y fecha objetivo, sin fijar DDL aquí.

## 29. Invariantes para DER y SQL

El DER posterior debe materializar Tarea, ComentarioTarea, HistorialTarea, FKs locales, identidades portables, metadata CORE-EF, constraints de origen/creador/generador, enums cerrados de estado/prioridad, versión positiva, unicidad/inmutabilidad de UID, soft delete y relación comentario–Tarea.

SQL debe proteger invariantes estructurales y referenciales; application layer debe proteger autorización, elegibilidad, lifecycle contextual, causalidad, idempotencia orquestada y composición transaccional. No se congelan nombres de tabla/columna, tipos, triggers ni índices definitivos.

## 30. Derivaciones hacia DEV-SRV y DEV-API

DEV-SRV definirá commands conceptuales para crear, modificar, asignar/reasignar/desasignar, cambiar prioridad/fecha, transicionar/completar/cancelar/reabrir, comentar y baja lógica futura. Definirá códigos de idempotencia, fingerprints, errores, repositories sin commit y eventos conceptuales.

DEV-API definirá operaciones HTTP sin congelarlas aquí. Auth humana será Bearer → AuthenticatedPrincipal. Los writes sincronizables usarán X-Op-Id, X-Sucursal-Id y X-Instalacion-Id conforme al helper CORE-EF. Las mutaciones de snapshot usarán If-Match-Version; creación y comentario no. X-Usuario-Id está prohibido como identidad GOP.

## 31. Estrategia de tests

| Área | Caso | Nivel |
| --- | --- | --- |
| Dominio | Invariantes, lifecycle, prioridad, vencida, origen | Unitario |
| Autorización | Creador/responsable/scope y default-deny | Unitario/API |
| Persistencia | UID, FKs, constraints, CAS, soft delete | PostgreSQL |
| Atomicidad | Efecto + historial + outbox + receipt; rollback | PostgreSQL |
| Idempotencia | Execute/replay/conflict y canonicalización | PostgreSQL/API |
| API | Bearer, headers, If-Match, errores y replay | API |
| Sync | Payload sin PK, order, saltos, conflicto, replay | Sync |
| Dependencias | Usuario/sucursal/Tarea ausentes y retry | Sync |
| Comentarios | Append concurrente, terminales, baja y causalidad | Unitario/PostgreSQL/Sync |
| Baja | Versión, propagación, conservación de appends | PostgreSQL/Sync |

## 32. Fuera de alcance

DER, SQL, migrations, tablas, routers, schemas, services, repositories, frontend, alertas, automatización, scheduler, notificaciones, auth técnica, #522, service accounts, API keys, usuario SYSTEM, workflow/BPM, DSL, EAV, plugins, IAM GOP, event sourcing, CQRS, ledger GOP y sync paralelo.

## 33. Decisiones congeladas

1. Tarea es aggregate root del snapshot.
2. ComentarioTarea es append sincronizable independiente.
3. HistorialTarea es append interno atómico.
4. Identidad portable usa uid_global; PK local no viaja.
5. Lifecycle y prioridad son cerrados.
6. Sucursal es scope nullable e inmutable; NULL es global.
7. Creador es inmutable; responsable es 0..1.
8. Comentario no versiona Tarea ni usa su CAS.
9. Toda mutación material del snapshot incrementa una versión y usa CAS.
10. Idempotencia, outbox/inbox y retry son transversales.
11. Evento por command material lleva snapshot resultante y causalidad.
12. Convergencia se basa en versión/contenido, nunca LWW.
13. deleted_at no es CANCELADA.
14. MVP sólo admite origen USUARIO.
15. No existen gaps funcionales bloqueantes para DER posterior.

## 34. Pendientes no bloqueantes

Quedan para DER/DEV-SRV/DEV-API: nombres físicos, tipos y longitudes, código definitivo de commands/eventos/permisos, endpoints y DTO, representación física de causalidad, índices finales y clasificación terminal exacta del intento de comentario causalmente posterior a baja.

Quedan fuera y bajo #522: credencial, principal y autorización de actores técnicos. Alertas, scheduler, restauración y automatización requieren incrementos propios.

## 35. Criterio de cierre

DEV-ARCH-GOP queda listo cuando revisión humana confirme: alineación con GOP-FREEZE-001; ownership sin invasiones; Tarea/Comentario/Historial separados; lifecycle y scope completos; CORE-EF, CAS e idempotencia reutilizados; protocolo #512 preservado; origen SISTEMA no habilitado; y ausencia de SQL/API/runtime prematuros.

Este documento satisface el alcance arquitectónico de #523 y habilita, después de aprobación/merge, la preparación separada del DER. No implementa el dominio ni cierra #522.
