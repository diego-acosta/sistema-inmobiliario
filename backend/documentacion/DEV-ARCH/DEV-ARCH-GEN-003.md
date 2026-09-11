# DEV-ARCH-GEN-003 — Identidad, autorización y contexto central

## 1. Estado, alcance y evidencia

**ARQUITECTURA OBJETIVO — contrato documental de PR 02; runtime pendiente de migración.**
Base auditada: `transition/central-authority`, commit
`f1c4a4ce62240e08867ce8531fc3579540114d24`, merge de #542 (2026-09-11).
`main` permanece separado en `e51e1f50cc51b39856a43480d3005a34526808d1`.
#533 continúa abierto/Draft y fuera de alcance.

Complementa [GEN-002](DEV-ARCH-GEN-002.md), sin ampliar su precedencia general.
La exclusión de INSTALACION es una decisión explícita de producto de PR 02,
no una reinterpretación como dispositivo, cliente o deployment. Este contrato
no cambia reglas económicas, ownership ni crea entidades o mecanismos de seguridad.
Administrativo conserva usuario, credencial, sesión, permisos y auditoría;
Operativo conserva sucursal y caja; Técnico provee mecanismos transversales.
`USUARIO ≠ PERSONA`; rol de seguridad no equivale a rol de participación.

Las decisiones cerradas siguientes no prueban implementación. §16 distingue
brechas reales; §18 registra decisiones abiertas que bloquean sólo sus consumidores.
La base no contiene datos útiles que deban preservarse, según el responsable;
no se inspeccionó una DB productiva ni se ejecutó un reset.

## 2. Identidad humana y principal

Para commands humanos protegidos: `Authorization: Bearer` → sesión utilizable
validada por servidor → `AuthenticatedPrincipal` → `id_usuario` autenticado.
La identidad nunca procede de metadata enviada por el cliente. `X-Usuario-Id`
no se exige, usa, compara ni parsea como identidad/autorización en el contrato
central. Un usuario objetivo en path/payload es el recurso administrado, no el actor.
Login y fronteras preautenticadas conservan sus contratos específicos.

`AuthenticatedPrincipal` sigue siendo una proyección inmutable de identidad
humana autenticada, no un permiso ni un contexto operativo ya autorizado.
Conserva `id_usuario`, `codigo_usuario`, `login`, UID público `id_sesion`,
`mecanismo_autenticacion = SESION_SERVIDOR` y `autenticado_en`.
`id_usuario` y `usuario.uid_global` no se sustituyen entre sí ni se cambian las PK.

| Campo actual del principal | Clasificación objetivo | Destino |
| --- | --- | --- |
| `id_instalacion_origen_sesion` | RETIRAR | No requerido para crear/resolver sesión ni ejecutar requests; compatibilidad física hasta migración |
| `id_sucursal_operativa` | MIGRAR | El contexto efectivo pertenece al command/request, no a la identidad; retirar su autoridad y después su proyección del principal/API |

Hoy login inserta `id_sucursal_operativa = NULL`; el principal sólo proyecta esa
columna. Su presencia no acredita alcance. El retiro de campos de `/me` debe
coordinarse con schema/callers en otro PR; aquí la respuesta no cambia.

## 3. Autenticación y sesión central

Reutilizar `usuario.login`, `credencial_usuario` y `sesion_usuario` existentes.
Conservar Argon2id v1, bearer opaco de 32 bytes aleatorios y sólo digest SHA-256
persistido, expiración absoluta de ocho horas y sesión revocable server-side.
No introducir JWT, refresh, OAuth, SSO ni otro ledger de sesiones.
La sesión central no depende de instalación ni de una sucursal asignada.

La validación conserva usuario activo/no eliminado/sin baja y sesión ACTIVA,
sin cierre, sin requerimiento de reautenticación y con `expira_en > ahora`.
La identidad del usuario es estable entre requests; permisos y alcance se
consultan actualmente, no se congelan como concesiones al iniciar sesión.
Logout mantiene cierre idempotente: un token bien formado desconocido o ya
finalizado no vuelve a mutar la sesión. No exige `X-Op-Id` ni CAS HTTP.
`/me` continúa siendo read-only, sin renovar TTL, actividad ni conceder permisos.
No se promete un mecanismo de revocación administrativa aún inexistente.

La autoridad temporal es PostgreSQL en UTC; comparar instantes independientes
de `TimeZone`. Los casts actuales de sesiones/autorización GLOBAL requieren
migración y pruebas con zona no UTC (§16). No convertir timestamps económicos
ni fechas operativas mediante esta regla.

Flet debe conservar el bearer, consultar `/me`, manejar expiración/401 y logout,
y enviar contexto explícito. Un 403 no equivale a sesión inválida. No se envían
passwords/tokens a logs, outbox, Sync ni auditoría; mantener `no-store` y errores
sanitizados. La sesión y credencial pasan de locales por instalación a centrales
no replicables; la prohibición de distribuir secretos permanece.

## 4. Sucursal efectiva: un único modelo por request

Se conserva la selección explícita `X-Sucursal-Id` del resolver actual para
commands con contexto operativo. La sesión no selecciona ni fija sucursal.
Cambiar de sucursal cambia el contexto del siguiente request, no el bearer ni
la sesión; dos requests concurrentes pueden usar sucursales diferentes autorizadas.
No hay fallback servidor a instalación, primera fila, ID fijo, sesión o predeterminada.

`usuario_sucursal.es_sucursal_predeterminada` puede orientar la selección inicial
del cliente; éste debe enviar el selector. Una predeterminada inexistente,
inactiva o no autorizada no habilita nada. Con múltiples sucursales se selecciona
explícitamente; sin sucursales se puede autenticar, pero no operar bajo una sucursal.

Para un command operativo humano, antes de ejecutar o devolver replay:

1. Validar principal y sintaxis del selector.
2. Validar sucursal existente, ACTIVA, `permite_operacion = true`, sin baja ni
   `deleted_at`, conforme a la proyección existente de #536.
3. Validar `usuario_sucursal` del actor: ACTIVO, `puede_operar = true`, no eliminado,
   `fecha_desde <= ahora` y `fecha_hasta IS NULL OR ahora < fecha_hasta`, en UTC.
   Intervalo vacío no habilita; no usar el reader de listas como prueba de vigencia.
4. Evaluar permiso y denegación aplicables (§5). `puede_operar` no concede permisos.
5. Comprobar que el target y las entidades afectadas pertenecen al alcance funcional
   del command. El selector no mueve recursos ni suplanta su sucursal persistida.

Ausencia/invalidez del selector requerido es error de contrato; alcance insuficiente
es rechazo de autorización, sin efectos. No inferir permisos desde los flags
`puede_consultar` o `puede_administrar`; sus consumidores mantienen sus contratos.

**Commands GLOBAL sin contexto operativo:** su contrato puede declarar
`id_sucursal = NULL`, con permiso GLOBAL y sin `usuario_sucursal` ficticio.
No se convierte una operación contextual en GLOBAL por omitir el header.
Si el contrato declara GLOBAL sin contexto, un selector no cambia ese alcance
ni puede habilitar roles locales. La migración específica declara el tratamiento
HTTP de headers no aplicables y no impone sucursal por mera procedencia Sync.
Los writes GLOBAL existentes que hoy requieren contexto conservan su API hasta
su migración. Esto no redefine alcance de parámetros ni resuelve #435.

## 5. Autorización y límites de la evidencia

Identidad, habilitación operativa y permisos son controles separados y acumulativos
cuando el command exige sucursal. Default-deny: no hay rol mágico, autoasignación,
permiso por header, ni permiso implícito por conocer un `op_id`.
Conservar permisos por código contractual exacto y roles/permisos activos.
Una denegación explícita aplicable prevalece sobre una concesión; errores de
resolución no se degradan a permiso concedido. Conservar 401 para sesión inválida,
403 sanitizado para falta de autorización y fallo técnico sanitizado ante
permiso contractual inexistente/inconsistencia, según helpers actuales.

| Entidad real | Misión / evidencia | Contrato central |
| --- | --- | --- |
| `usuario_sucursal` | Habilitación operativa con flags/vigencia; #536 la consulta | Validación §4, independiente de permisos |
| `usuario_rol_seguridad` | Asignación GLOBAL con vigencia y baja lógica; helper #443 | Conservar filtro vigente `[desde,hasta)` y usuario elegible |
| `rol_seguridad`, `permiso`, `rol_seguridad_permiso` | Roles, permisos y vínculos físicos usados por #443 | Reutilizar; no crear sinónimos `rol_administrativo`/`rol_permiso` de docs antiguas |
| `usuario_rol_sucursal` | SQL: usuario, rol, sucursal, desde/hasta; sin evaluador runtime hallado | Asignación contextual existente, sin inventar FK a `usuario_rol_seguridad`; composición pendiente D1 |
| `denegacion_explicita` | SQL: usuario, permiso, motivo; sin sucursal, vigencia ni evaluador hallado | Denegación aplicable prevalente; no inventar columnas ni revocación temporal |

`require_administrative_permission` sólo resuelve GLOBAL hoy; no evalúa
`usuario_rol_sucursal`, `usuario_sucursal` ni `denegacion_explicita`.
La combinación exacta GLOBAL/contextual no queda autorizada por la mera existencia
de tablas. **DECISIÓN ABIERTA D1** en §18: bloquea habilitar autorización contextual
completa, no el retiro de instalación de login/sesión. No presentar el helper
GLOBAL actual como implementación de la política completa anterior.

## 6. INSTALACION y LOCAL_INSTALLATION_CODE

**INSTALACION en arquitectura objetivo: NO APLICA.** No es actor, dispositivo,
estación ni identidad persistida del deployment. El sistema central debe funcionar
sin una instalación activa en request, sesión, command, CAS, auditoría, idempotencia
ni persistencia de negocio. No se crea sustituto persistido.

**Runtime/SQL actual: COMPATIBILIDAD_TRANSICIONAL** mientras tenga consumidores.
La entidad, FKs, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`,
headers, resolvers, tests y validación instalación↔sucursal se retiran
incrementalmente después de migrar callers; PR 02 no elimina ninguno.

Nuevas funcionalidades centrales no pueden exigir `X-Instalacion-Id`,
`LOCAL_INSTALLATION_CODE`, resolver instalación, validar sucursal por pertenencia
a instalación, usarla para actor/autorización/ownership/idempotencia ni crear
nuevas dependencias funcionales. Una FK de compatibilidad técnica imprescindible
requiere justificación, consumidores y plan de retiro; no la convierte en núcleo.
No añadir una instalación artificial para hacer funcionar el modelo central.

`LOCAL_INSTALLATION_CODE`: **TRANSICIONAL → RETIRAR** de settings, bootstrap,
login y contexto tras migrar sus consumidores. §16 registra rutas concretas.
El fallo cerrado actual del resolver sigue rigiendo callers legacy; no se elimina
el control sin adaptar su escritura/SQL en el PR responsable.

## 7. Contexto canónico de command central

Reemplazo conceptual de `ResolvedLocalCommandContext`, no nueva entidad persistida
ni implementación de DTO en este PR. Lo resuelve el servidor, sin commits internos.

| Campo | Fuente | Obligación / validación | Uso |
| --- | --- | --- | --- |
| Actor humano o técnico | Sesión validada / mecanismo técnico futuro | Exactamente un tipo; no confiar en header de actor | Autorización y trazabilidad |
| `principal`, `id_usuario` si humano | `AuthenticatedPrincipal` del servidor | Obligatorios para humano protegido; nunca usuario ficticio técnico | Identidad estable |
| `id_sucursal` efectiva | Selector del request validado por servidor | Obligatoria en command operativo; NULL sólo en contrato GLOBAL sin contexto | Alcance y evidencia, no autenticación |
| `op_id` | `X-Op-Id` UUID del intento lógico | Según §9; estable en retries | Deduplicación durable |
| `if_match_version` | `If-Match-Version` entero positivo del snapshot cliente | Según §10, validado contra raíz correcta | CAS, no autorización |

Target/payload siguen siendo datos del command, validados por su dominio.
No se trasladan reglas de negocio al DTO de contexto. Los permisos son una decisión
actual del servidor, no una colección confiada desde cliente/sesión.
No incluir instalación, UID de instalación ni deployment por herencia.

## 8. Política objetivo de headers

| Header | Clasificación / misión |
| --- | --- |
| `Authorization: Bearer` | OBLIGATORIO en commands humanos protegidos; login tiene contrato propio |
| `X-Usuario-Id` | RETIRAR del contrato central; ninguna identidad/autorización; sólo callers legacy hasta migración |
| `X-Sucursal-Id` | CONDICIONAL: selección explícita obligatoria si el command tiene contexto operativo; §4 |
| `X-Instalacion-Id` | NO APLICA al contrato nuevo; COMPATIBILIDAD_TRANSICIONAL |
| `X-Op-Id` | CONDICIONAL por seguridad de comando, no universal; §9 |
| `If-Match-Version` | CONDICIONAL por concurrencia de entidad/agregado; §10 |

Reutilizar parsing común, errores tipados y `ErrorResponse`; no duplicar parsers
por dominio. Requests sin necesidad de write no heredan headers write.
No quitar headers ejecutables por cambiar esta tabla documental.

## 9. Auditoría de X-Op-Id

Misión central retenida: identificar un comando lógico reintentable y obtener
replay durable sin duplicar efectos. Correlación y auditoría pueden referenciarlo,
pero no justifican exigir idempotencia a toda operación; un identificador de log
no prueba deduplicación. Para simple correlación no imponer `X-Op-Id` público.

| Tipo de command | Riesgo de duplicado material | Idempotencia durable | `X-Op-Id` objetivo |
| --- | --- | --- | --- |
| CREATE simple | Duplica entidad si no hay clave estable/constraint equivalente | Obligatoria si un retry puede crear segundo efecto; no necesaria si contrato ya deduplica y recupera resultado inequívoco | CONDICIONAL; obligatorio al usar ledger |
| UPDATE versionado | CAS evita segunda actualización, pero no recupera respuesta perdida ni side effects por sí solo | Obligatoria si necesita replay de resultado o efectos adicionales; no universal para edición simple con CAS | CONDICIONAL |
| Transición de estado | Puede duplicar efectos, notificaciones o ejecución; depende del lifecycle | Obligatoria ante efecto material repetible; justificar excepción si transición es intrínsecamente idempotente | CONDICIONAL |
| Pago/cobro | Alto: duplicación económica | OBLIGATORIA | OBLIGATORIO |
| Emisión | Alto: doble documento/obligación/efecto | OBLIGATORIA | OBLIGATORIO |
| Orquestador multi-entidad | Alto: efecto compuesto y respuesta incierta | OBLIGATORIA, una operación exterior | OBLIGATORIO |
| Append-only | Puede duplicar comentario, entrada o movimiento | Obligatoria cuando cada append tiene significado material; excepción sólo con deduplicación equivalente probada | CONDICIONAL |

Todo command declara clasificación y justificación antes de implementarse.
En operaciones con ledger, el cliente genera el UUID antes de enviar y conserva
op_id, target, payload, sucursal y versión esperada ante timeout. Otra intención
requiere nuevo op_id. Correlación por request puede variar sin alterar la operación.
No eliminar idempotencia existente por la etiqueta CREATE/UPDATE ni por retirar Sync.
Logout conserva su idempotencia propia por sesión sin exigir ledger/X-Op-Id.

## 10. Auditoría de If-Match-Version

Misión: evitar lost updates, ediciones sobre snapshots stale y transiciones
incompatibles entre usuarios de una DB central. No depende de réplicas.

| Tipo de command | Modifica existente | Riesgo de lost update | `If-Match-Version` |
| --- | --- | --- | --- |
| CREATE raíz nueva | No | No | NO APLICA; unicidad/constraints siguen necesarios |
| UPDATE editable versionado | Sí | Alto/medio | OBLIGATORIO para reemplazar/modificar snapshot observado |
| Cambio de estado sobre raíz versionada | Sí | Estado obsoleto | OBLIGATORIO si parte del snapshot; excepción sólo con transición atómica equivalente y contrato explícito |
| Append-only independiente | No modifica snapshot padre normalmente | Bajo en padre | NO APLICA al padre; CONDICIONAL si el caso modifica/depende de su snapshot |
| Pago | Según agregado y efectos | Concurrencia sobre saldo/imputación | Según raíces afectadas; CAS cuando modifica snapshot versionado, más invariantes económicas/locks |
| Orquestador | Varias raíces posibles | Alto | Según raíces afectadas; un escalar no representa versiones distintas |

Crear hijo que muta raíz existente no es excepción CREATE de raíz nueva.
Un append puede no usar CAS del padre sin perder validación del lifecycle,
constraints o transacción. Ejemplo contractual existente: comentario de Tarea
no incrementa versión de Tarea; historial interno no adquiere versión artificial.
Para múltiples raíces, explicitar precondición de cada una en el contrato de
dominio; no reutilizar una versión para targets diferentes ni inventar aquí un DTO.

La comparación debe ser atómica por identidad + versión (CAS SQL/lock equivalente),
no sólo comparar en memoria antes de un UPDATE ciego. Conservar mismatch tipado
(412 `CONCURRENCY_ERROR` en el patrón #412) y rollback. Un replay autorizado de
una operación ya completada devuelve receipt; no reejecuta CAS sobre estado actual.

## 11. Auditoría de version_registro

| Tipo de entidad/agregado | Clasificación | Justificación |
| --- | --- | --- |
| Raíz mutable editable o lifecycle concurrente | CONSERVAR | Token monotónico CAS entre usuarios centrales; identidad + versión |
| Hijos que forman un snapshot de raíz | CONDICIONAL | Usar frontera de versión congelada por el dominio; no sumar versiones duplicadas |
| Append inmutable / historial interno | CONDICIONAL | No necesita CAS por mera existencia; respetar excepciones existentes |
| Sesión/credencial existente | CONSERVAR como metadata física útil | Hoy triggers versionan; no implica exigir If-Match al login/logout |
| Versionado exclusivamente para convergencia Sync | RETIRAR como obligación objetivo | Conservar físicamente hasta retirar consumidores; revisar si también sostiene CAS |

No eliminar columnas ni convertir `uid_global` en PK. No derivar versión de reloj
ni hacer LWW. Cada writer material preserva identidad y versión coherente sin
dobles incrementos trigger/service. Replay y no-op contractual no incrementan
versiones: #412 ya distingue igualdad tipada de UPDATE físico.

## 12. Composición con idempotencia y replay

Reutilizar `operacion_idempotente`, `canonical_payload_hash`, `claim_operation`
y `complete_operation` (#469/#470), sin rediseñar físicamente el ledger aquí.
Conservar unicidad global de op_id, exclusión transaccional, orden de conflicto
COMMAND → TARGET → PAYLOAD, snapshot durable y atomicidad efecto/receipt.
Instalación no es identidad ni parte del contexto material del comando objetivo.

Para el contrato central, la equivalencia comprende command, target estable,
payload normalizado, versión esperada cuando aplica, actor estable y sucursal
efectiva (incluido NULL contractual GLOBAL). Incluir actor/sucursal en el envelope
semántico canonicalizado del caller; no confiar en metadata del receipt que el
claim actual no compara. No incluir bearer, UID de sesión, reloj de retry ni
versión actual del target: otra sesión válida del mismo usuario puede reintentar.
Cambiar actor o sucursal no permite reutilizar el receipt de la intención anterior.

Orden objetivo:

1. Autenticar y validar estructura/contexto; revalidar alcance y permisos actuales,
   incluida denegación aplicable y autorización sobre target antes de exponer receipt.
2. Construir identidad/fingerprint canónicos y reclamar la operación en la misma
   transacción. No exponer snapshots ajenos ni usar op_id como credencial.
3. REPLAY compatible y autorizado: devolver snapshot persistido sin nueva mutación,
   outbox, incremento de versión o validación de negocio que reejecute la operación.
   CONFLICT: rechazo tipado sin efecto; EXECUTE: validar estado, CAS e invariantes.
4. Persistir efectos y completion en una única transacción del caso de uso;
   publicar durablemente si el contrato lo requiere. Error/rollback sin completion
   permite retry EXECUTE; no convertir fallo técnico en receipt exitoso.

Autorización actual no equivale a recalcular resultado histórico: puede requerir
lecturas de seguridad sobre el target, nunca rehacer saldo, emisión o CAS en replay.
Sin autorización comprobable, no devolver snapshot. No prometer cancelación
retroactiva de un command ya autorizado/en ejecución por revocación posterior;
las fronteras transaccionales deben ser explícitas y probadas en su PR runtime.

**Discrepancia declarada:** #412 hoy hashea código, valor tipado y versión,
no actor/sucursal, y valida contexto sólo después de EXECUTE. Su router sí usa
Bearer/permiso GLOBAL. El helper #470 no revalida autorización por sí mismo.
Migrar router/caller/fingerprint/receipt coordinadamente; no reinterpretar receipts
antiguos como nuevos. Dado el bootstrap limpio permitido, el PR de corte puede
invalidar datos técnicos de desarrollo con justificación; si se retienen receipts,
debe aislar su contrato por command/versionado y probar compatibilidad. No alterar
silenciosamente la canonicalización RFC 8785 ni romper consumidores legacy.

## 13. Actores técnicos e identidad del backend

Actor técnico ≠ usuario humano ficticio. `AuthenticatedPrincipal` sólo representa
humanos. Headers técnicos no autentican; `LocalCommandActor.TECHNICAL` actual
omite usuario/scope humano, pero no implementa autenticación técnica.
No habilitar endpoints/jobs privilegiados basándose únicamente en esa policy.

No se identificó necesidad de entidad persistida de deployment para los commands
humanos auditados: la dependencia de instalación es legado, no autenticación.
Logs de proceso/host/versión son observabilidad, no permisos ni ownership.
Los efectos internos conservan actor causal cuando exista sin fingir una sesión.
El mecanismo y las facultades de jobs/integraciones quedan en D2; no se crean
API keys, OAuth, service tokens ni sustituto de INSTALACION.

## 14. Procedencia y auditoría central

Mínimo contractual: tipo/identidad de actor, sucursal efectiva o NULL justificado,
op_id cuando aplique, instante UTC, entidad/operación y resultado. Separar
correlación de intento, operación lógica y resultado de negocio; replay no es
segunda ejecución. Nunca registrar credenciales, bearer, hashes sensibles ni
payloads secretos. Respetar los contratos de auditoría y privacidad existentes.

`id_instalacion_origen` e `id_instalacion_ultima_modificacion` dejan de ser
metadata obligatoria objetivo; las FKs/columnas que persisten son transicionales.
No reemplazarlas automáticamente por otra entidad. El subsistema de auditoría
uniforme no se declara implementado por este contrato; su persistencia y cobertura
se migran por dominio, preservando evidencia funcional y atomicidad aplicables.

## 15. Compatibilidad documental

[Administrativo](dominios/administrativo/DEV-ARCH-ADM-001.md) y
[Operativo](dominios/operativo/DEV-ARCH-OPE-001.md) conservan ownership y contratos
funcionales. Sus apartados históricos sobre sesión local, instalación/sucursal,
headers universales y replay describen runtime/compatibilidad; no son nuevas
obligaciones centrales. Igual tratamiento para GEN-001 §10, RN-ADM-011/012/031,
SRV-TEC-001, CORE-EF y DEV-API aún no migrados, según GEN-002 §9.
La selección request y la exclusión de instalación quedan cerradas aquí; la
precedencia no permite inventar la composición de roles que D1 deja abierta.

## 16. Matriz de evidencia objetivo vs runtime actual

Rutas relativas al repositorio. Lectura estática de SQL/código/tests; ninguna suite
funcional ejecutada en este PR. Una prueba existente no se reporta como PASS.

| Área / evidencia concreta | Runtime actual | Objetivo / pendiente responsable |
| --- | --- | --- |
| `backend/app/application/administrativo/authentication.py`; `backend/app/api/authentication.py` | Login resuelve instalación; principal desde sesión/usuario; TTL 8h y logout revocable | Administrativo: conservar seguridad, retirar dependencia de instalación y proyecciones legacy |
| `backend/app/infrastructure/persistence/repositories/sesion_usuario_repository.py`; `backend/database/patch_sesion_usuario_runtime_20260807.sql` | Insert con instalación, sucursal NULL, digest/TTL, triggers de versión; reloj por cast sin UTC explícito | Administrativo/SQL: login y `/me` sin instalación, UTC independiente de TimeZone; conservar revocación |
| `backend/app/config/settings.py`; `backend/app/application/common/local_installation.py`; `backend/app/infrastructure/persistence/repositories/instalacion_repository.py` | Settings exige LOCAL_INSTALLATION_CODE (también consumido al iniciar `backend/app/main.py` y `backend/app/config/database.py`); lookup exacto, elegibilidad/fallo cerrado | Técnico/Operativo: TRANSICIONAL → RETIRAR al migrar callers; no fallback artificial |
| `backend/app/application/administrativo/commands/bootstrap_credential.py`; `backend/database/patch_credencial_usuario_core_ef_20260805.sql` | CLI crea/resetea con resolver y FKs de procedencia | Administrativo: bootstrap seguro sin instalación, preservar Argon2id/locks/credencial revocada |
| `backend/app/application/common/local_command_context.py`, `local_command_headers.py`; `backend/app/api/local_command_context.py` | Sucursal por request; instalación resuelta incluso sin assertion; op_id requerido; adapters sin adopción productiva encontrada fuera del módulo | Técnico: contexto §7 sin instalación, policy idempotencia/CAS; no quitar protecciones legacy en bloque |
| `backend/app/infrastructure/persistence/repositories/technical_context_repository.py` | Reloj UTC, sucursal elegible, vínculo vigente + instalación↔sucursal | Técnico/Administrativo/Operativo: conservar scope, retirar sólo validación instalación |
| `backend/app/infrastructure/persistence/repositories/usuario_sucursal_repository.py`; `backend/database/patch_usuario_sucursal_core_ef_20260702.sql` | Flags, predeterminada e índices; listas no sustituyen proyección temporal #536 | Administrativo: reutilizar asignaciones y UTC; no crear asignación a deployment |
| `backend/app/application/administrativo/authorization.py`; `backend/app/api/administrative_authorization.py`; `backend/app/infrastructure/persistence/repositories/administrative_authorization_repository.py` | Permiso GLOBAL reusable, sin denegación/scope contextual; reloj por cast | Administrativo: UTC, denegaciones y composición tras D1; no afirmar cobertura transversal |
| `backend/database/schema_inmobiliaria_20260418.sql`, tablas de §5 | usuario_rol_sucursal tiene FKs directas usuario/rol/sucursal; denegación sólo usuario/permiso | D1 debe respetar SQL real; DER histórico con otra estructura no es evidencia de runtime |
| `backend/app/api/core_ef_headers.py`; routers `administrativo_router.py`, `operativo_router.py`, `comercial_router.py`, `financiero_router.py`, `locativo_router.py` | Perfiles legacy/authenticated/technical, instalación extendida y seguridad parcial | Cada dominio: migrar API/servicio/callers juntos, no usar headers como seguridad |
| `backend/app/application/common/idempotency.py`; `backend/app/infrastructure/persistence/repositories/operacion_idempotente_repository.py`; `backend/database/patch_operacion_idempotente_20260810.sql` | Claim no recibe actor/scope; completion exige instalación; FK/trigger de pertenencia y UNIQUE(op_id) | Técnico: adaptar contrato del caller y metadata SQL, conservar ledger único, exclusión y receipt/efecto atómicos |
| `backend/app/application/administrativo/services/actualizar_valor_parametro_global_service.py`; `backend/app/infrastructure/persistence/repositories/valor_parametro_global_command_repository.py` | #412 tiene CAS real y no-op; replay sin contexto mutable | Migración focal Administrativo de §12; no cambiar replay antes de alinear contrato/callers |
| `backend/app/application/integration/outbox_to_inbox_worker.py`; `backend/app/application/financiero/services/inbox_event_dispatcher.py` | Consumers de efectos locales además de Sync | Preservar efectos/guardrail #455; no retirar infraestructura por eliminar instalación del objetivo |

### Evidencia de tests y frontera de regresión futura

Inspección focal y suites relacionadas identificadas en `backend/tests/`;
no equivale a auditoría completa de cada suite ni a ejecución:

- `test_authenticated_principal.py`, `test_authentication_service.py`,
  `test_session_tokens.py`, `test_administrativo_login_api.py`: identidad desde
  sesión, rechazos, digest, TTL, logout repetido y sanitización; adaptar proyecciones.
- `test_administrative_authorization.py`, `test_administrative_authorization_postgres.py`:
  GLOBAL/default-deny; las aserciones excluyen scope contextual, no prueban D1.
- `test_local_command_context_536.py`, `test_local_command_context_536_api.py`,
  `test_local_command_context_536_postgres.py`: humano/técnico, policy, instalación,
  elegibilidad, vigencia y UTC; separar garantías útiles de compatibilidad.
- `test_administrativo_alcance_operativo.py`: normalización UTC de offsets,
  vigencias, replay y predeterminada; no reemplazar por tests sólo sintácticos.
- `test_local_installation_settings.py`, `test_local_installation_resolver.py`,
  `test_local_installation_postgres.py`, `test_admin_credentials_bootstrap.py`:
  inventario de consumidores para retiro, no requisitos de nuevos commands.
- `test_core_ef_headers.py`: contratos actuales de headers; adaptar por perfil.
- `test_operacion_idempotente_469_sql.py`, `test_operacion_idempotente_470_unit.py`,
  `test_operacion_idempotente_470_canonicalization.py`,
  `test_operacion_idempotente_470_postgres.py`,
  `test_operacion_idempotente_470_concurrency.py`: ledger, fingerprint,
  conflictos, simultaneidad, rollback y retry; preservar invariantes útiles.
- `test_administrativo_valor_global_412_concurrency.py`: dos escritores con
  versión compartida y CAS; es concurrencia central útil, no sólo Sync.

## 17. Orden de migración y criterios del siguiente PR

1. **Siguiente PR runtime: autenticación/sesión y bootstrap sin instalación.**
   Partir de transición tras integrar este contrato. Alcance Administrativo +
   settings/SQL estrictamente necesarios: mantener bearer/Argon2id/revocación/TTL,
   desacoplar login, credenciales y principal; alinear `/me`, DEV-API y sus callers.
   El esquema debe permitir ese camino sin fila de instalación. El cambio de
   Settings no puede romper consumidores legacy todavía activos: aislar su
   validación explícita hasta retirarlos. No habilitar commands contextuales aún.
2. Cerrar **D1** documentalmente antes de implementar evaluador contextual;
   puede avanzar en paralelo conceptual con el paso 1, evitando archivos compartidos.
3. Contexto central y autorización; luego composición ledger/callers y SQL
   de procedencia. Migrar por vertical coherente, preservando receipt y efectos.
4. Adopción por dominios/Flet, contratos API y retiro físico incremental de
   instalación y Sync tras inventario de consumidores. D2 precede automatización.

Aceptación del paso 1: login, `/me`, expiración y logout sin LOCAL_INSTALLATION_CODE
ni instalación; usuarios/credenciales inválidos siguen fallando; ningún secreto
expuesto; pruebas UTC en PostgreSQL no UTC; logout repetido sin mutación adicional;
compatibilidad de callers explícita; SQL/reset limpio reproducible. Suites focales
autenticación/credenciales/principal y regresión afectada, sin afirmar migración
de permisos o contexto de negocio. Nuevos endpoints/DTO innecesarios no forman
parte de ese incremento. Estos criterios no autorizan implementarlo en PR 02.

## 18. Decisiones abiertas y límites de cierre

| ID | DECISIÓN ABIERTA | Alternativas e impacto | Bloquea |
| --- | --- | --- | --- |
| D1 | Composición de concesiones GLOBAL y por sucursal para un permiso contextual | Unión de concesiones GLOBAL/local vigente vs exigencia de asignación local (o restricción explícita del rol GLOBAL). Cambia derechos efectivos; el helper actual sólo cubre GLOBAL y SRV-ADM-002 deja alcances/herencia pendientes. No elegir automáticamente. Congelar también aplicabilidad de denegaciones: la tabla actual sólo expresa usuario/permiso global; una variante por sucursal exigiría otro incremento explícito | Evaluador y adopción contextual completa; no login/sesión central ni principio deny prevalente |
| D2 | Autenticación/autorización concreta de jobs e integraciones | Proceso interno con autoridad delimitada vs credencial técnica verificada para frontera externa; cambia ciclo de secretos, revocación y facultades. Resolver por contrato de actor, sin usuario humano ficticio ni nueva instalación | Automatización/commands técnicos protegidos |

INSTALACION, ausencia de sustituto persistido, selección por request, TTL/sesión,
misión de op_id/CAS y reglas de replay anteriores **no son decisiones abiertas**.
Los detalles de aplicación por agregado requieren inventario en su PR, respetando
estas matrices y sus reglas económicas; no habilitan volver a exigir Sync.
Mientras D1 siga abierta, no declarar identidad/contexto completo del backend
ni Gate 2 de GEN-002 satisfecho. Este PR cierra las decisiones respaldadas y
hace explícito el límite, conforme a la prohibición de diseñar seguridad libremente.
