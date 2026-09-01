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

| Atributo | Semántica | Mutable | Nullable | Versiona Tarea |
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

El orden es BAJA < NORMAL < ALTA < URGENTE y NORMAL es el default conceptual. fecha_objetivo es opcional y representa DATE funcional, no timestamp CORE-EF.

`VENCIDA` no es un estado persistido. Para cada caso de uso relevante, `fecha_corte_local` se captura una sola vez desde un reloj confiable del servidor y se proyecta en la zona IANA `America/Argentina/Buenos_Aires`; no proviene del cliente, instalación ni sesión PostgreSQL. La regla exacta es:

```text
vencida =
  deleted_at ausente
  AND fecha_objetivo no nula
  AND estado IN (PENDIENTE, EN_CURSO)
  AND fecha_objetivo < fecha_corte_local
```

La comparación es DATE estricta. Una Tarea con fecha objetivo igual a la fecha de corte no está vencida durante ese día; terminales y bajas lógicas no están vencidas. Una Tarea reabierta puede volver a estar vencida si su fecha objetivo quedó antes del corte.

## 12. Creador, responsable y actores

El creador humano se toma exclusivamente de Bearer → AuthenticatedPrincipal.id_usuario, conserva FK local y viaja como usuario.uid_global. Es inmutable. La baja o desactivación posterior del usuario no invalida la Tarea ni elimina su identidad histórica.

El responsable es 0..1 y puede asignarse, reasignarse o quitarse mediante administración aplicable mientras el lifecycle lo permita. Su elegibilidad es una invariante continua y se evalúa completa sobre un único `instante_corte_utc` capturado una sola vez por caso de uso desde el reloj confiable del servidor en UTC; ese instante no proviene del cliente, navegador, sucursal ni instalación.

Para una Tarea de sucursal, el responsable sólo es elegible cuando se cumplen simultáneamente:

```text
usuario vigente
= estado_usuario = ACTIVO
  AND usuario.deleted_at IS NULL
  AND usuario.fecha_baja IS NULL

sucursal vigente
= estado_sucursal = ACTIVA
  AND sucursal.deleted_at IS NULL
  AND sucursal.fecha_baja IS NULL

vínculo usuario_sucursal vigente
= usuario_sucursal.deleted_at IS NULL
  AND estado_vinculo = ACTIVO
  AND fecha_desde_utc <= instante_corte_utc
  AND (fecha_hasta_utc IS NULL OR instante_corte_utc < fecha_hasta_utc)
  AND usuario vigente
  AND sucursal vigente

responsable elegible
= vínculo usuario_sucursal vigente
  AND puede_operar = true
  AND autorización efectiva Administrativa suficiente
```

El intervalo de vigencia es `[fecha_desde, fecha_hasta)`, inclusivo al inicio y exclusivo al final. No alcanza con verificar aisladamente `puede_operar`. Para una Tarea global se exige el alcance global operativo vigente equivalente y autorización efectiva Administrativa suficiente; la representación técnica de ese alcance permanece bajo ownership Administrativo. Sin responsable elegible no se ingresa a EN_CURSO ni COMPLETADA.

Las fronteras temporales de elegibilidad preservan el contrato temporal congelado: toda entrada nueva de `fecha_desde`/`fecha_hasta` que deba ser autoritativa llega con offset explícito, se normaliza a UTC y se compara como instante UTC. Si la persistencia futura usa `timestamp without time zone`, sólo puede tratarse como UTC canónico cuando la escritura recibió un offset explícito y normalizó previamente el instante; el timezone de sesión PostgreSQL no es autoridad semántica.

Los valores legacy naïve sin offset no se reinterpretan silenciosamente como UTC ni como ninguna otra zona. Antes de usarlos como frontera autoritativa para visibilidad, elegibilidad, asignación o mutación GOP, su semántica debe resolverse mediante migración/backfill explícito o una regla legacy documentada y validada. Este DEV-ARCH no elige esa estrategia ni supone un timezone histórico.

Si el responsable pierde después elegibilidad, permanece referenciado para trazabilidad pero pierde las capacidades derivadas de esa relación. No hay desasignación, reasignación, cancelación ni cambio de estado automático. La gestión posterior requiere una mutación explícita de un actor con administración aplicable.

Actores de historial y autores de comentario conservan referencia local más identidad portable cuando el tipo de hecho exige actor humano. El receptor no reevalúa retrospectivamente roles, permisos, asignación ni relaciones humanas que cambiaron después del hecho confirmado.

## 13. Scope de sucursal

Tarea.id_sucursal es scope funcional, nullable e inmutable en el MVP. NULL significa Tarea global, no instalación desconocida ni sucursal implícita. Una sucursal concreta habilita filtrado, visibilidad y autorización por ese scope.

X-Sucursal-Id y X-Instalacion-Id son contexto/procedencia técnica del command. No asignan Tarea.id_sucursal, no autentican personas y no convierten instalación en scope funcional. En sync, la sucursal funcional se referencia por sucursal.uid_global.

Si la sucursal del scope deja de estar vigente, la Tarea conserva scope, estado, responsable registrado y demás datos; no se convierte a global ni se muta automáticamente. Las capacidades locales dejan de estar vigentes y la gestión residual requiere alcance global administrativo vigente más autorización efectiva de Administrativo.

## 14. Visibilidad y autorización humana

GOP declara habilitaciones funcionales y consume la autorización efectiva de Administrativo; no crea ACL, roles ni tablas de permisos. Toda operación humana protegida requiere simultáneamente la relación funcional que la habilita y autorización efectiva Administrativa. Ninguna de las dos sustituye a la otra.

### 14.1 Bases de visibilidad

Un usuario puede ver una Tarea si, con autorización efectiva correspondiente, cumple al menos una base independiente:

1. es el creador humano;
2. es el responsable registrado y conserva elegibilidad vigente;
3. tiene consulta vigente sobre la sucursal de una Tarea de sucursal;
4. tiene administración vigente sobre esa sucursal;
5. para Tarea global, tiene alcance global de consulta o administración vigente;
6. para Tarea de sucursal cuyo scope dejó de estar vigente, tiene alcance global administrativo vigente.

`puede_administrar` es una base propia de visibilidad pero no implica ni deriva `puede_consultar`. `puede_consultar` por sí solo no habilita mutación.

- **Mis tareas** significa exclusivamente Tareas cuyo responsable registrado es el usuario y cuya elegibilidad sigue vigente.
- **Tareas creadas por mí** es una consulta separada por autoría.
- El creador conserva visibilidad por autoría después de asignación, reasignación o desasignación, aunque no sea responsable ni conserve scope.
- Una Tarea sin responsable sigue visible por creador o por consulta/administración del scope.

### 14.2 Matriz de mutación

| Acción | Creador por esa sola relación | Responsable vigente/elegible | Administración aplicable |
| --- | --- | --- | --- |
| Modificar título o descripción | No | No | Sí |
| Asignar, reasignar o desasignar | No | No | Sí |
| Cambiar prioridad o fecha objetivo | No | No | Sí |
| Cambiar PENDIENTE ↔ EN_CURSO | No | Sí | Sí |
| Completar | No | Sí | Sí, sólo si existe responsable elegible |
| Cancelar | No | No | Sí |
| Reabrir COMPLETADA → PENDIENTE | No | No | Sí |
| Comentar | Sí | Sí | Sí |

La administración aplicable significa: alcance global administrativo para Tarea global; administración vigente sobre la sucursal para Tarea de sucursal vigente; o fallback de alcance global administrativo si la sucursal dejó de estar vigente. En todos los casos se exige además autorización efectiva de Administrativo y se respetan lifecycle, terminalidad y elegibilidad.

Ser creador sólo habilita visibilidad y comentario por autoría. El responsable elegible sólo obtiene las capacidades de ejecución indicadas en la matriz. Si pierde elegibilidad, no se desasigna ni cambia el estado automáticamente, pero pierde visibilidad por responsabilidad, comentario por responsabilidad, PENDIENTE ↔ EN_CURSO y completar; puede conservar acceso sólo por otra base independiente válida.

## 15. Comentarios

ComentarioTarea es append-only en el MVP: no se edita ni se borra funcionalmente; una corrección es otro append. Tiene uid_global propio, único, inmutable y no reutilizable, y version_registro propio que nace en 1 y normalmente permanece en 1. Cada comentario conserva obligatoriamente la Tarea a la que pertenece, su autor humano portable, el `texto` funcional y el instante de ocurrencia generado/conservado conforme al contrato temporal aplicable; ninguno de esos datos puede omitirse al derivar DER, DEV-SRV o DEV-API.

Agregar comentario:

- no incrementa Tarea.version_registro;
- no requiere If-Match-Version de Tarea;
- conserva Tarea.uid_global, autor portable, `texto`, instante del comentario, op_id y causalidad suficiente;
- produce persistencia, outbox y receipt en una transacción;
- es válido en PENDIENTE, EN_CURSO, COMPLETADA y CANCELADA cuando alguna relación funcional de la matriz lo habilita y existe autorización efectiva;
- no reabre, no completa, no cancela ni altera fecha_finalizacion.

Comentario y baja causalmente concurrentes conservan ambos efectos. Un comentario confirmado antes de la baja converge aunque la baja llegue primero. Un intento causalmente posterior a la baja no es una mutación ordinaria válida. No se crean placeholders ni LWW.

## 16. Historial funcional

HistorialTarea registra cambios funcionales estructurados; no es CORE-EF, auditoría administrativa, outbox, inbox ni operacion_idempotente.

Cada entrada conserva conceptualmente tipo de cambio, actor local y portable cuando exista, instante, op_id causal, valores anterior/nuevo cuando corresponda y motivo obligatorio de reapertura. Se genera para creación, cambios materiales de contenido, asignación, prioridad, fecha objetivo, estado, completar, cancelar y reabrir. La evidencia de finalizaciones previas se conserva cuando una Tarea se reabre. Para el tipo `REABIERTA`, dado que el MVP de reapertura es exclusivamente humano y requiere administración aplicable, el actor humano es obligatorio junto con el instante y el motivo: la entrada debe conservar actor local y `usuario.uid_global`, `estado_anterior = COMPLETADA`, `estado_nuevo = PENDIENTE`, instante y motivo obligatorio; no puede existir una reapertura funcional sin actor atribuible.

Una eventual baja lógica conserva obligatoriamente versionado, CAS, idempotencia, outbox, sync y trazabilidad CORE-EF, pero una entrada funcional específica de HistorialTarea sólo será obligatoria si un contrato funcional posterior determina que corresponde; no se convierte automáticamente toda mutación técnica en hecho funcional.

Los comentarios no se duplican como historial. La consulta puede presentar ambos flujos sin fusionar sus persistencias. No se congela PK ni layout SQL.

## 17. CORE-EF

Tarea aplica uid_global, version_registro, created_at, updated_at, deleted_at, id_instalacion_origen, id_instalacion_ultima_modificacion, op_id_alta y op_id_ultima_modificacion. ComentarioTarea aplica identidad, versión y metadata CORE-EF correspondientes a una entidad sincronizable.

Quién actuó se expresa con usuario; dónde se ejecutó se expresa con instalación. La metadata transversal no se duplica como campos funcionales. Tarea nace en versión 1. Toda mutación local material confirmada del snapshot avanza exactamente una versión `Vn → Vn+1`; la baja lógica también incrementa exactamente una versión local.

Las clasificaciones CORE-EF congeladas para las operaciones estudiadas del MVP son:

| Operación conceptual | Clasificación CORE-EF | Sincronización |
| --- | --- | --- |
| Crear o mutar snapshot de Tarea | COMMAND_WRITE_NEGOCIO | SINCRONIZABLE |
| Agregar ComentarioTarea | COMMAND_WRITE_NEGOCIO | SINCRONIZABLE |
| Baja lógica futura | COMMAND_WRITE_TECNICO | SINCRONIZABLE |
| Consultas | QUERY_READLIKE | No generan outbox |

Crear o mutar snapshot comprende creación, contenido, asignación/reasignación/desasignación, prioridad, fecha objetivo, transiciones de estado, completar, cancelar y reabrir. La baja lógica futura conserva su naturaleza técnica y permanece fuera del primer MVP público.

Para las operaciones estudiadas del MVP se congela `lock lógico = NO APLICA`. Esta decisión no elimina ni debilita CAS, `If-Match-Version`, `version_registro`, idempotencia, transacción ni el fencing de infraestructura Técnica cuando corresponda: el control optimista del snapshot continúa siendo obligatorio según este documento. No se introduce un mecanismo de locking adicional.

## 18. Versionado y CAS

| Operación | Incrementa Tarea | If-Match-Version | Motivo |
| --- | --- | --- | --- |
| Crear | Nace en 1 | No | No hay versión previa |
| Modificar título/descripción | Sí, +1 local | Sí | Muta snapshot |
| Asignar/reasignar/desasignar | Sí, +1 local | Sí | Muta responsable |
| Cambiar prioridad | Sí, +1 local | Sí | Muta snapshot |
| Cambiar fecha objetivo | Sí, +1 local | Sí | Muta snapshot |
| Cambiar estado/completar/cancelar | Sí, +1 local | Sí | Muta lifecycle |
| Reabrir | Sí, +1 local | Sí | Muta lifecycle y exige motivo |
| Agregar comentario | No | No sobre Tarea | Append independiente |
| Baja lógica futura | Sí, +1 local | Sí | Mutación técnica sincronizable |

Un command local material produce como máximo un incremento aun si cambia varios atributos coherentes. No se congela el mecanismo SQL de CAS.

La recepción remota no redefine esta regla. Si el receptor conserva Tarea en Vn, sólo Vn+1 es candidato inmediato a mutar el snapshot. Un evento con versión `> Vn+1` presenta un gap de continuidad y no adelanta el snapshot. La clasificación, reentrega o reconciliación técnica concreta del gap queda para DEV-SRV/Técnico posterior; GOP no lo convierte automáticamente en PENDING_DEPENDENCY, REJECTED ni CONFLICTO.

## 19. Idempotencia

GOP reutiliza public.operacion_idempotente y el contrato #469/#470: claim → EXECUTE, REPLAY o CONFLICT → complete. No crea ledger propio.

Cada command futuro define command_code, target_type, target_uid o target_key, payload material canonicalizable, versión esperada cuando aplica, fingerprint, snapshot durable de replay y completion. El claim ocurre después del parseo/normalización suficientes para construir el fingerprint y antes del efecto material, dentro de la misma transacción coordinada. El orden exacto respecto de autorización y lecturas mutables se definirá en DEV-SRV preservando el contrato #470 y replay durable. Mismo op_id y envelope compatible devuelve replay sin repetir efecto/outbox; incompatibilidad material produce conflicto.

La futura creación con `origen = SISTEMA` exige además una garantía funcional distinta de la idempotencia técnica por `op_id`: el mismo hecho fuente no puede crear una segunda Tarea funcional equivalente aunque sea reprocesado con un `op_id` nuevo. La identidad o clave material del hecho fuente se definirá en artefactos posteriores; este contrato no crea un ledger GOP paralelo ni congela columnas, hashes o índices.

## 20. Fronteras transaccionales

El application service/orchestrator es owner de commit y rollback. Los repositories no hacen commit ni rollback internos.

Para una mutación exitosa, claim idempotente, efecto funcional, historial aplicable, outbox y receipt durable comparten una única transacción. Para comentario, la unidad es claim + comentario + outbox + receipt. Un fallo previo al commit revierte todos los efectos y permite retry contractual.

## 21. Eventos y outbox

La arquitectura requiere que toda mutación sincronizable emita outbox transaccional suficiente para reproducir el efecto remoto y preservar la causalidad funcional. Como estrategia preferida para el MVP, cada command material puede emitir un evento que transporte el snapshot resultante de esa versión junto con el descriptor causal necesario; DEV-SRV definirá la granularidad, nombres, schemas y routing concretos.

La continuidad estricta de Tarea significa que un snapshot posterior no sustituye una operación intermedia no entregada. El transporte/retry debe preservar la posibilidad de entregar cada mutación necesaria en orden lógico suficiente para que el receptor avance `Vn → Vn+1`. Esto no adopta event sourcing y no autoriza reconstruir historial inventando diferencias entre snapshots.

Consultas no generan outbox. Los nombres EVT, numeración, payload físico y routing quedan para artefactos posteriores.

## 22. Payload portable

El contrato funcional distribuido puede contener únicamente identidades portables, versiones, datos funcionales necesarios, op_id, causalidad y procedencia que el envelope Técnico requiera. Usa Tarea.uid_global, ComentarioTarea.uid_global, usuario.uid_global para referencias humanas requeridas y sucursal.uid_global cuando existe scope funcional concreto.

La procedencia de instalación pertenece al envelope/contrato Técnico y no se declara como referencia funcional GOP universal. Cuando el contrato Técnico la transporte, usa la identidad portable correspondiente sin transferir ownership a GOP.

Se prohíben PK locales, Bearer, passwords, credenciales, sesiones, roles, permisos, SQL, DSN y secretos. El payload no confía en timestamps para decidir autoridad.

## 23. Recepción e inbox

Se reutiliza #512:

- Delivery = (event_id, consumer);
- Operation = (consumer, op_id);
- Attempt = attempt_id.

Técnico conserva retained envelope, policy default-deny, claim/reclaim, lease, fencing, retry y operation scope. GOP valida semántica funcional, resuelve las referencias funcionales requeridas por esa operación, verifica continuidad de versión y aplica snapshot/append cuando corresponda. El applicator usa la Session provista y no confirma transacciones por su cuenta.

Para Tarea, si el snapshot local está en Vn y llega una mutación de Vn+1, puede evaluarse su aplicación. Si llega `> Vn+1`, existe gap de continuidad y el snapshot no avanza. Ese gap no se clasifica por sí solo como dependencia portable, rechazo ni conflicto; el mecanismo técnico de espera/reordenamiento/reentrega se define posteriormente sin rediseñar #512.

## 24. PENDING_DEPENDENCY

PENDING_DEPENDENCY sólo aplica cuando una referencia **funcional portable**, válida, declarada requerida por la operación y temporalmente ausente impide aplicar el efecto. No hay aplicación parcial ni placeholder.

| Categoría | Referencia | Resultado ante ausencia temporal válida |
| --- | --- | --- |
| Funcional requerida | Creador cuando la operación lo requiere | PENDING_DEPENDENCY |
| Funcional requerida | Responsable cuando viene presente y es requerido por el snapshot | PENDING_DEPENDENCY |
| Funcional requerida | Autor de comentario | PENDING_DEPENDENCY |
| Funcional requerida | Sucursal funcional concreta | PENDING_DEPENDENCY |
| Funcional requerida | Tarea padre de ComentarioTarea | PENDING_DEPENDENCY |
| Funcional requerida en REABIERTA | Actor humano de historial | PENDING_DEPENDENCY si la referencia portable requerida del actor todavía no se resuelve; REABIERTA no admite actor ausente |
| Funcional condicional | Actor de historial en otros hechos | Sólo si ese tipo de hecho exige actor humano y la operación requiere materializarlo |
| Funcional opcional | responsable = NULL o sucursal = NULL | No genera dependencia |
| Procedencia técnica | instalación/envelope técnico | La clasifica Técnico según su contrato; no es PENDING_DEPENDENCY GOP por defecto |

Payload inválido o referencia permanentemente inválida se clasifica conforme al contrato Técnico/funcional correspondiente; divergencia material real produce conflicto. Un gap de `version_registro` no es PENDING_DEPENDENCY: pertenece a continuidad de versión.

## 25. Conflicto, replay y obsolescencia

Tarea conserva criticidad de sincronización **MEDIA**. Esa clasificación prohíbe auto-merge genérico, resolución automática campo por campo y LWW: toda divergencia material que las reglas explícitas no puedan resolver de forma segura debe persistirse como conflicto con trazabilidad. Una resolución que modifique datos requiere una nueva operación trazable con nuevo `op_id`; la criticidad no transfiere ownership funcional a Técnico.

La convergencia de Tarea usa continuidad estricta de snapshot; la de ComentarioTarea permanece independiente.

| Entrada remota de Tarea | Resultado arquitectónico |
| --- | --- |
| Creación válida sobre UID inexistente | Aplicar versión inicial según contrato |
| Versión exactamente local + 1 | Candidata a aplicar si resuelve referencias y satisface invariantes |
| Versión > local + 1 | Gap de continuidad; no aplicar inmediatamente ni avanzar snapshot |
| Versión inferior a la local | No revierte estado; evaluar idempotencia/obsolescencia según operación ya conocida |
| Misma versión y mismo contenido, mismo op_id/envelope compatible | Replay/duplicado seguro de la misma operación; no repetir efecto |
| Misma versión y mismo contenido, op_id distinto | Operación distinta pero materialmente convergente: no es replay ni duplicado, no cambia el snapshot y conserva separadamente la trazabilidad de ambas operaciones |
| Misma versión y distinto contenido | Conflicto material |
| deleted_at en la versión siguiente válida | Aplicar baja sin convertir lifecycle |
| Timestamp más nuevo | Sin autoridad por sí mismo |

Un gap no se resuelve por timestamp ni LWW y no inventa automáticamente una clasificación inbox nueva. DEV-SRV/Técnico definirá cómo esperar/reordenar/reentregar la operación faltante manteniendo #512. La continuidad garantiza que HistorialTarea derivado de las mutaciones aplicadas no pierda silenciosamente operaciones intermedias por adelantar sólo el snapshot.

ComentarioTarea converge por su uid_global, versión y op_id propios. Su aplicación no exige que la Tarea tenga la misma versión actual que tenía al comentar, pero sí la existencia/resolución causal mínima congelada por #493 y las reglas frente a baja lógica.

## 26. Baja lógica

deleted_at es baja técnica, distinta de CANCELADA. No hay DELETE físico. La baja futura es sincronizable, versionada, idempotente, usa CAS, genera outbox y conserva Tarea, comentarios e historial existentes. No restaura ni cambia el lifecycle. No se expone en el primer MVP y la restauración queda fuera de alcance.

Las queries ordinarias excluyen registros dados de baja salvo vistas técnicas/autorizadas. Una baja recibida no elimina appends válidos anteriores o concurrentes. Una entrada funcional específica de HistorialTarea por la baja sólo será obligatoria si un contrato posterior determina que corresponde.

## 27. Origen SISTEMA futuro

El modelo debe poder proteger esta invariante:

| origen | creador | generador_sistema |
| --- | --- | --- |
| USUARIO | Obligatorio | NULL |
| SISTEMA | NULL | Obligatorio |

Sólo USUARIO se acepta en el primer runtime. generador_sistema es un descriptor funcional mínimo, no una credencial ni identidad técnica. #522 debe cerrar autenticación/autorización técnica antes de habilitar SISTEMA. No se crean service accounts, API keys, usuario SYSTEM ni Bearer artificial.

Cuando `origen = SISTEMA` se habilite en un incremento futuro, deberá preservarse simultáneamente `op_id → idempotencia técnica` y `hecho fuente → idempotencia funcional`: reprocesar el mismo hecho fuente con otro `op_id` no puede crear una Tarea funcional duplicada. La clave exacta del hecho fuente permanece diferida y no se diseña en este MVP.

## 28. Consultas esperadas

La arquitectura debe soportar lecturas de pendientes, responsable, creador, estado, sucursal, prioridad, fecha objetivo, vencidas derivadas, completadas/canceladas, comentarios e historial. El DER evaluará índices sobre uid_global, filtros de lifecycle y baja, responsable, creador, sucursal, prioridad y fecha objetivo, sin fijar DDL aquí.

## 29. Invariantes para DER y SQL

El DER posterior debe materializar Tarea, ComentarioTarea, HistorialTarea, FKs locales, identidades portables, metadata CORE-EF e invariantes estructurales de origen/creador/generador, título obligatorio y no vacío, estados, prioridad, versión positiva, unicidad/inmutabilidad de UID, soft delete y relación comentario–Tarea.

SQL y application layer deberán preservar que `título` no sea nullable ni cadena vacía y conserve contenido funcional real en creación y modificación, con la representación concreta que determine el DER. SQL deberá proteger las demás invariantes estructurales y referenciales; application layer protegerá autorización, elegibilidad, lifecycle contextual, causalidad, continuidad remota, idempotencia orquestada y composición transaccional. No se congelan nombres de tabla/columna, tipos SQL, longitudes, enums físicos, CHECK, triggers ni índices definitivos.

## 30. Derivaciones hacia DEV-SRV y DEV-API

DEV-SRV definirá commands conceptuales para crear, modificar, asignar/reasignar/desasignar, cambiar prioridad/fecha, transicionar/completar/cancelar/reabrir, comentar y baja lógica futura. Definirá códigos de idempotencia, fingerprints, errores, granularidad/eventos, repositories sin commit y la clasificación/mecanismo técnico de gaps de continuidad sin convertirlos automáticamente en PENDING_DEPENDENCY.

DEV-API definirá operaciones HTTP sin congelarlas aquí. Auth humana será Bearer → AuthenticatedPrincipal. Los writes sincronizables usarán X-Op-Id, X-Sucursal-Id y X-Instalacion-Id conforme al helper CORE-EF. Las mutaciones de snapshot usarán If-Match-Version; creación y comentario no. X-Usuario-Id está prohibido como identidad GOP.

## 31. Estrategia de tests

| Área | Caso | Nivel |
| --- | --- | --- |
| Dominio | Invariantes, lifecycle, prioridad, vencida, origen | Unitario |
| Reapertura | fecha_finalizacion y responsable elegible/NULL/reemplazo | Unitario/PostgreSQL |
| Autorización | Creador/responsable/scope, pérdida de elegibilidad y fallback | Unitario/API |
| Persistencia | UID, FKs, constraints, CAS, soft delete | PostgreSQL |
| Atomicidad | Efecto + historial + outbox + receipt; rollback | PostgreSQL |
| Idempotencia | Execute/replay/conflict y canonicalización | PostgreSQL/API |
| API | Bearer, headers, If-Match, errores y replay | API |
| Sync | Payload sin PK, continuidad Vn→Vn+1, gap, conflicto y replay | Sync |
| Dependencias | Referencia funcional requerida ausente vs procedencia Técnica | Sync |
| Comentarios | Append concurrente, terminales, baja y causalidad | Unitario/PostgreSQL/Sync |
| Baja | Versión, propagación, conservación de appends | PostgreSQL/Sync |

## 32. Fuera de alcance

DER, SQL, migrations, tablas, routers, schemas, services, repositories, frontend, alertas, automatización, scheduler, notificaciones, auth técnica, #522, service accounts, API keys, usuario SYSTEM, workflow/BPM, DSL, EAV, plugins, IAM GOP, event sourcing, CQRS, ledger GOP y sync paralelo.

## 33. Decisiones congeladas

1. Tarea es aggregate root del snapshot.
2. ComentarioTarea es append sincronizable independiente.
3. HistorialTarea es append interno atómico para mutaciones funcionales que lo requieren.
4. Identidad portable usa uid_global; PK local no viaja.
5. Lifecycle y prioridad son cerrados.
6. Sucursal es scope nullable e inmutable; NULL es global.
7. Creador es inmutable; responsable es 0..1 y su elegibilidad es continua.
8. Comentario no versiona Tarea ni usa su CAS.
9. Toda mutación local material del snapshot avanza exactamente `Vn → Vn+1` y usa CAS.
10. Una recepción de Tarea con gap `> Vn+1` no adelanta el snapshot; su mecanismo técnico se difiere sin clasificarla automáticamente como PENDING_DEPENDENCY, rechazo o conflicto.
11. Idempotencia, outbox/inbox y retry son transversales.
12. Los eventos deben transportar información suficiente para aplicar cada mutación sincronizable; la granularidad concreta queda para DEV-SRV y un snapshot posterior no sustituye una operación intermedia faltante.
13. Convergencia se basa en versión/contenido y continuidad, nunca LWW.
14. PENDING_DEPENDENCY sólo cubre referencias funcionales portables requeridas y temporalmente ausentes; procedencia Técnica conserva ownership Técnico.
15. deleted_at no es CANCELADA y la baja técnica no obliga por sí sola a crear HistorialTarea funcional.
16. MVP sólo admite origen USUARIO.
17. ComentarioTarea conserva Tarea, autor, texto e instante funcional.
18. Las fronteras temporales de elegibilidad exigen offset explícito, normalización UTC y tratamiento explícito de legacy naïve antes de ser autoritativas.
19. La futura generación SISTEMA combina idempotencia técnica por op_id con idempotencia funcional por hecho fuente.
20. Tarea tiene criticidad de sincronización MEDIA; no admite auto-merge genérico, field-by-field ni LWW.
21. Toda reapertura `REABIERTA` conserva obligatoriamente actor humano local+portable, instante y motivo.
22. Misma versión y contenido con `op_id` distinto es una operación materialmente convergente distinta: no replay/duplicado y conserva ambas trazas.
23. No existen gaps funcionales bloqueantes para DER posterior.

## 34. Pendientes no bloqueantes

Quedan para DER/DEV-SRV/DEV-API: nombres físicos, tipos y longitudes, código definitivo de commands/eventos/permisos, endpoints y DTO, representación física de causalidad, índices finales, mecanismo/clasificación técnica de gaps de continuidad y clasificación terminal exacta del intento de comentario causalmente posterior a baja.

Quedan fuera y bajo #522: credencial, principal y autorización de actores técnicos. Alertas, scheduler, restauración y automatización requieren incrementos propios.

## 35. Criterio de cierre

DEV-ARCH-GOP queda listo cuando revisión humana confirme: alineación con GOP-FREEZE-001; ownership sin invasiones; Tarea/Comentario/Historial separados; lifecycle, elegibilidad y scope completos; CORE-EF, CAS e idempotencia reutilizados; continuidad remota sin pérdida silenciosa de historial; protocolo #512 preservado; origen SISTEMA no habilitado; y ausencia de SQL/API/runtime prematuros.

Este documento satisface el alcance arquitectónico de #523 y habilita, después de aprobación/merge, la preparación separada del DER. No implementa el dominio ni cierra #522.
