# DEV-ARCH-ADM-001 — Freeze de configuración administrativa

## 1. Propósito y estado

Este documento congela la fuente de verdad arquitectónica de configuración y parametrización del dominio `administrativo`. Su origen fue un freeze documental; desde entonces, incrementos posteriores pueden materializar decisiones concretas mediante SQL, runtime y tests verificables. El estado vigente de cada capacidad debe leerse según su sección específica y la implementación real del repositorio; las capacidades marcadas como pendientes o no confirmadas permanecen únicamente como contrato o evolución futura.

Antes de este freeze no existía un DEV-ARCH Administrativo en la rama base. El material histórico del DER global describía un diseño más amplio que no coincide con el SQL real; desde este incremento, para configuración prevalecen este freeze, `DEV-ARCH-GEN-001` y la implementación verificable.

## 2. Ownership y clasificación

| Concepto | Clasificación | Decisión |
| --- | --- | --- |
| `parametro_sistema` | núcleo de Administrativo | Definición canónica de cada parámetro. |
| `valor_parametro` | núcleo de Administrativo | Fuente canónica de valores por contexto y vigencia. |
| `tipo_dato_parametro`, `alcance_parametro` | soporte de la definición | Describen tipo y alcance; no son valores. |
| `parametro_opcion` | soporte de la definición | Sólo expresa opciones válidas de un parámetro; no convierte parámetros en catálogos. |
| `historial_parametro` | soporte transversal de trazabilidad | Su estructura actual es incompleta; no prueba auditoría runtime. |
| `configuracion_general` | compatibilidad heredada | No admite nuevas claves ni consumidores; se migrará incrementalmente y su eliminación física queda para una evolución posterior. |
| `configuracion_local` | núcleo de Operativo | Queda fuera de la parametrización administrativa y de #425. |

### Bootstrap canónico de seguridad administrativa (#249 / alcance histórico #260)

Los resets DEV y TEST materializan un único `rol_seguridad` administrativo con
contrato exacto: `codigo_rol = 'ADMINISTRADOR_SISTEMA'`,
`nombre_rol = 'Administrador del sistema'`, descripción
`Rol administrativo global para la gestión y configuración del sistema.` y
`estado_rol = 'ACTIVO'`. El patch versionado falla ante una fila incompatible y
no asigna el rol a usuarios ni crea permisos o relaciones rol-permiso.

Este bootstrap pertenece al núcleo Administrativo y sólo establece el receptor
canónico para permisos futuros. #412 queda implementado por su PR; su
patch podrá resolver exactamente una fila activa por `codigo_rol` sin crearla ni
modificarla. Endpoints, headers, idempotencia HTTP, outbox, locks y versionado
runtime son **NO APLICA** para este incremento SQL; sí aplican transacción,
rollback, preflight e idempotencia SQL fail-fast.

Los parámetros no son catálogos. `catalogo_maestro`/`item_catalogo` conservan su modelo administrativo propio y no participan en la resolución de configuración.

## 3. Modelo canónico

`parametro_sistema` define identidad y referencia físicamente a `alcance_parametro`; `valor_parametro` conserva el valor y posee campos opcionales `id_sucursal` e `id_instalacion`. Esas columnas prueban capacidad física de contexto, pero no congelan por sí solas su semántica de resolución.

Para futuros parámetros contextuales quedan **NO CONFIRMADOS** el catálogo cerrado de alcances, el significado exacto de `alcance_parametro`, la posibilidad de overrides, la precedencia entre niveles, la obligatoriedad de un valor global base y las reglas de contexto y fallback. En particular, no se define una granularidad máxima de override ni una precedencia general.

Las vigencias de un mismo parámetro y contexto no pueden solaparse. El SQL actual sólo comprueba el orden entre `fecha_desde` y `fecha_hasta`; la exclusión de solapamientos permanece pendiente. La inclusividad de `fecha_hasta` está **NO CONFIRMADA**.

Las claves contractuales del sistema no tendrán alta ni baja dinámica en el primer incremento runtime: se administrarán mediante migraciones versionadas. La exposición administrativa, la sensibilidad y la editabilidad administrativa ya son metadata física explícita de la definición mediante `exponible_api_administrativa`, `es_sensible` y `editable_administrativamente`, con política restrictiva por defecto. No deben inferirse del código, tipo, nombre, exposición, sensibilidad o valor.

La editabilidad administrativa es independiente de exposición y sensibilidad, nace `false` para toda definición existente o futura y sólo puede habilitarse por migración versionada explícita; no existe endpoint write que la modifique. La autorización real, el cifrado o secret manager y cualquier modelo adicional de visibilidad siguen **NO CONFIRMADOS**.

## 4. Consumo interdominio y secretos

Otros dominios consumirán parámetros mediante un query service interno del dominio Administrativo; no consultarán directamente las tablas. Ese servicio no está implementado todavía.

Un valor sensible nunca puede exponerse en claro por API, historial, outbox ni logs. El mecanismo de cifrado o secret manager, la autorización y la caché están **NO CONFIRMADOS**. Este freeze fija la prohibición de exposición, no afirma que exista hoy una solución runtime para secretos.

## 5. Freeze específico para #425

#425 se implementará exclusivamente sobre:

- `parametro_sistema`, como definición;
- `valor_parametro`, como valor `GLOBAL` vigente;
- `id_sucursal IS NULL` e `id_instalacion IS NULL`;
- sin `configuracion_general`;
- sin `configuracion_local`;
- sin catálogos.

Permanecen pendientes para #425 y sus incrementos de implementación: patch SQL funcional específico; seeds de las dos claves; constraints de rango 1–31; read; write; versionado; idempotencia; outbox; historial; rollback; query service interno y tests PostgreSQL. Esta lista no declara nombres de endpoints ni comportamiento runtime existente.

Quedan **NO CONFIRMADOS** hasta contar con evidencia: códigos/nombres exactos de las claves, defaults, cifrado/secret manager, autorización, caché, inclusividad de `fecha_hasta`, reactivación o reutilización de claves y taxonomía final de eventos.

## 6. Estado CORE-EF físico de `valor_parametro`

#410 implementó preparación física CORE-EF en `valor_parametro`: `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta` y `op_id_ultima_modificacion`. También implementó triggers de insert/update, versionado físico, integridad para definiciones cuyo alcance se resuelve por código `GLOBAL`, garantía concurrente de un único valor global vigente no eliminado, constraints físicas mínimas de vigencia, migración transaccional e integración en resets DEV/TEST.

Siguen pendientes, sin declararlos implementados: idempotencia HTTP, replay, `If-Match-Version` runtime, compare-and-swap en repository, outbox runtime, historial alineado al valor/contexto, autorización, cifrado o secret manager, no solapamiento temporal general, resolución contextual, overrides, precedencia, fallback y la frontera transaccional de commands de #412 y #425.

## 7. Decisión CORE-EF del freeze

- Endpoints: **NO APLICA**; no se agregan ni modifican rutas.
- Clasificación de command/read-like: **NO APLICA**; el incremento es documental.
- Headers, `If-Match-Version`, idempotencia, outbox, lock, versionado, transacción y rollback ejecutables: **NO APLICA** en este incremento.
- Tests CORE-EF y reset PostgreSQL: **NO APLICA**; no se modifica SQL ni runtime.

El `GET /api/v1/administrativo/configuracion/parametros` de #407/PR #414 se preserva como `QUERY_READLIKE`: inventaría definiciones, pero no lee valores ni ejecuta resolución contextual. #408 documenta este freeze y no agrega endpoints.

## 8. Incremento estructural #409

El patch incremental `patch_parametrizacion_estructural_20260802.sql` materializa
exclusivamente el tipo `ENTERO` y el alcance `GLOBAL`, resueltos siempre por sus
códigos y sin IDs contractuales. Sus nombres y descripciones son datos
estructurales no editables por API. El patch falla y revierte ante nombres o
descripciones incompatibles, variantes de mayúsculas/minúsculas y los sinónimos
`NUMERO`, `GENERAL` o `LOCAL`; su reejecución compatible no duplica filas.

#409 sólo elimina el bloqueo físico de tipo y alcance previo a #425. No crea
`parametro_sistema`, no crea `valor_parametro`, no define semántica contextual y
no implementa ninguna clave, valor, endpoint ni runtime de #425.

### Decisión CORE-EF

- Naturaleza: datos estructurales SQL.
- Endpoints, commands, headers, `If-Match`, idempotencia HTTP, outbox, locks y
  versionado: **NO APLICA**.
- Transacción, rollback, idempotencia SQL y reset reproducible DEV/TEST: aplican
  y forman parte del patch y de sus tests PostgreSQL.

## 9. Incremento SQL #410 — CORE-EF físico de `valor_parametro`

#410 prepara `valor_parametro` como infraestructura reusable del núcleo Administrativo: UID global, versión, timestamps, soft delete y metadata nullable de procedencia/op IDs. Los triggers fijan versión inicial 1, preservan metadata de alta e incrementan exactamente una vez cada `UPDATE` físico. Las filas heredadas no reciben procedencia ni op IDs inventados.

La integridad incorporada se limita a: contexto nulo para definiciones cuyo alcance se resuelve por código `GLOBAL`; fechas estrictamente ordenadas cuando ambas existen; y como máximo un valor global vigente no eliminado por definición. No se impone semántica a alcances no globales ni se resuelven overrides, precedencia, fallback, vigencias futuras o solapamientos temporales.

Es preparación SQL transaccional e idempotente. No existe todavía read de valores (#411), write (#412), runtime ni datos funcionales de #425. No se implementan API, outbox, historial, replay HTTP, CAS ni `If-Match-Version`.

## 10. Incremento #438 — Exposición segura de definiciones administrativas

#438 agrega metadata física mínima a `parametro_sistema` y mantiene separados dos conceptos del núcleo Administrativo: `exponible_api_administrativa` decide si una futura API administrativa puede considerar la definición para lectura de valor, y `es_sensible` clasifica si el valor de la definición no puede exponerse en claro. La política persistida es restrictiva por defecto: `exponible_api_administrativa = false` y `es_sensible = true`; ninguna definición heredada queda exponible automáticamente y cualquier habilitación futura debe realizarse mediante migración versionada explícita, sin inferir por código, nombre, tipo, alcance, descripción o valor.

La constraint `chk_parametro_sistema_exposicion_no_sensible` impide `exponible_api_administrativa AND es_sensible`: una definición sensible no puede quedar marcada como exponible en claro por la API administrativa. #438 no agrega niveles de sensibilidad, enum, catálogo, cifrado, secret manager, redacción parcial ni exposición enmascarada.

#438 no implementa autenticación ni autorización real. Los headers CORE-EF de write no equivalen a autorización, y la metadata física es una política mínima de exposición, no un reemplazo de autenticación. El futuro #411 no debe presentarse como endpoint público y deberá depender de autorización real cuando exista infraestructura verificable.

#438 no implementa el endpoint de #411, no modifica el inventario #407, no agrega commands, no genera outbox, no escribe historial runtime y no toca `valor_parametro`. El futuro #411 sólo podrá devolver un valor cuando `exponible_api_administrativa = true AND es_sensible = false`; para definiciones inexistentes o no exponibles se recomienda responder `404 Not Found` con el error estándar de parámetro no encontrado si el catálogo real lo permite, para no revelar existencia por enumeración. Futuros reads no deben registrar `valor_parametro`, secretos, op IDs, credenciales, payload SQL ni contenido sensible; pueden registrar identificador técnico, código cuando esté permitido, clasificación de error, correlación y stack trace interno.

#441 agrega la metadata física `editable_administrativamente boolean NOT NULL DEFAULT false`, independiente de `exponible_api_administrativa` y `es_sensible`. Ninguna definición queda editable automáticamente y la habilitación futura requiere migración funcional versionada. #412 conserva pendiente la implementación del endpoint write, pero su contrato final ya congela autorización Bearer, helper CORE-EF sin `X-Usuario-Id`, `If-Match-Version`, claim derivado sólo de request con `target_uid = None`, replay/conflict antes de lookup mutable, runtime idempotente #470, row lock `FOR UPDATE` sólo en `EXECUTE`, CAS, outbox y transacción única; historial especializado queda fuera de su alcance. #425 conserva pendientes sus definiciones funcionales, valores, rangos y runtime, y deberá declarar explícitamente su exposición, sensibilidad y editabilidad en su propia migración. #435 no queda resuelto: overrides, precedencia, fallback, contexto, granularidad y vigencia temporal siguen pendientes.

## 10.1 Incremento #441 — Editabilidad administrativa default-deny

#441 agrega a `parametro_sistema` la metadata física `editable_administrativamente boolean NOT NULL DEFAULT false`. La columna expresa únicamente editabilidad administrativa explícita: es independiente de `exponible_api_administrativa` y `es_sensible`, no tiene constraints que la acoplen a exposición o sensibilidad y no se expone por API.

La política es default-deny: toda fila existente y futura queda no editable salvo que una migración funcional versionada posterior la habilite explícitamente. El incremento no infiere editabilidad por código, tipo `ENTERO`, alcance `GLOBAL`, nombre, descripción, exposición, sensibilidad, existencia de valor, dominio ni allowlists. No crea parámetros, valores, endpoints write, outbox, historial, triggers ni índices.

CORE-EF: preparación SQL estructural y contractual. Endpoints, command HTTP, headers write, `If-Match-Version`, idempotencia HTTP, outbox, historial runtime y lock lógico son **NO APLICA**; idempotencia SQL, transacción y rollback son obligatorios y están cubiertos por tests PostgreSQL.

## 11. Incremento #411 — Lectura administrativa individual de valor GLOBAL

#411 agrega únicamente `GET /api/v1/administrativo/configuracion/parametros/{codigo_parametro}/valor-global` como `QUERY_READLIKE` administrativo no público. La ruta selecciona por igualdad exacta y case-sensitive sobre `parametro_sistema.codigo_parametro`; no normaliza, no usa aliases, no usa allowlists y no infiere exposición o sensibilidad por código, tipo, nombre, alcance, descripción o valor.

La exposición exige `exponible_api_administrativa = true` y `es_sensible = false`. Definición inexistente, no exponible o sensible son indistinguibles para el cliente y devuelven el mismo `404 parametro_no_encontrado`, sin metadata interna de seguridad. Una definición existente, exponible y no sensible con alcance distinto de `GLOBAL` devuelve `409 conflicto_parametro`.

La consulta devuelve el valor global marcado vigente y no eliminado (`es_valor_vigente = true`, `deleted_at IS NULL`, `id_sucursal IS NULL`, `id_instalacion IS NULL`). No resuelve valor efectivo, fecha actual, precedencia, fallback, overrides ni contexto. `fecha_desde` y `fecha_hasta` son sólo metadata proyectada. Si no hay valor, responde `SIN_VALOR` con `valor_marcado_vigente = null`; si hay valor, responde `CON_VALOR_MARCADO_VIGENTE` e incluye `id_valor_parametro`, `uid_global` y `version_registro` del valor. En este incremento sólo se tipa `ENTERO` de forma estricta: representación decimal ASCII con signo negativo opcional (`-?[0-9]+`), sin `+`, espacios, decimales, notación científica ni dígitos Unicode. Los tipos no soportados son inconsistencia incluso cuando no existe valor; `SIN_VALOR` sólo aplica a definiciones `ENTERO` válidas.

CORE-EF: headers write, `If-Match-Version`, idempotencia HTTP, outbox, historial, lock lógico, optimistic locking, commits y mutaciones son `NO APLICA` porque la ruta es read-only. #412 queda implementado separadamente por su command; #425 y #435 permanecen pendientes y no quedan implementados por esta lectura.

## 12. Incremento #448 — Contrato SQL inicial de `credencial_usuario`

#448 prepara exclusivamente la tabla histórica `public.credencial_usuario` como núcleo administrativo de seguridad para credenciales tipo `PASSWORD`. La implementación es SQL incremental por `ALTER` directo sobre la tabla existente: conserva columnas históricas, agrega metadata CORE-EF física (`uid_global`, `version_registro`, timestamps, `deleted_at`, procedencia por instalación y op IDs), constraints, FKs a `instalacion`, índices parciales y triggers de insert/update.

No existe runtime de credenciales en este incremento: no hay Argon2id, helper criptográfico, creación automática de credenciales, login, logout, sesiones nuevas, principal autenticado, outbox ni historial runtime. `hash_credencial` es sensible y no debe exponerse por API, logs, eventos genéricos ni documentación con ejemplos reales. Usuarios sin fila compatible en `credencial_usuario` no autentican; hoy no existe endpoint que autentique usuarios.

El contrato físico congela `tipo_credencial = 'PASSWORD'` y `estado_credencial IN ('ACTIVA','REVOCADA')`. `VENCIDA` y `BLOQUEADA` son condiciones derivadas futuras, no estados persistidos. #449 y #450 siguen pendientes; #446 permanece bloqueado hasta que existan primitivas/runtime de credenciales y sesión definidos en sus propios incrementos.

### Decisión CORE-EF

- Naturaleza: preparación SQL estructural sobre tabla histórica.
- Endpoints, commands HTTP, headers write, `If-Match-Version`, idempotencia HTTP, outbox, historial runtime y lock lógico funcional: **NO APLICA**; no se agregan rutas ni runtime.
- Transacción, lock SQL, rollback, idempotencia estructural, versionado físico y resets DEV/TEST: aplican y forman parte del patch y de sus tests PostgreSQL.

## 13. Incremento #449 — Primitivas Argon2id para credenciales

#449 incorpora únicamente una primitiva interna transversal de aplicación para hashing y verificación de secretos de credenciales futuras. La política productiva queda fija como Argon2id v1 con `time_cost=3`, `memory_cost=65536`, `parallelism=2`, `hash_len=32`, `salt_len=16` y `type=argon2id`; el identificador persistible futuro es `argon2id:v1`.

Este incremento no crea ni persiste credenciales, no modifica `credencial_usuario`, no agrega endpoints, no implementa autenticación, login, logout, sesiones, tokens, principal autenticado, outbox ni historial runtime. Cuando un consumidor futuro persista credenciales, `hash_credencial` deberá almacenar el string PHC Argon2id y `algoritmo_hash` deberá almacenar `argon2id:v1`; ese consumidor permanece pendiente y fuera de #449.

La primitiva pertenece a soporte transversal de aplicación para seguridad administrativa. No redefine ownership de `usuario` ni de `credencial_usuario`, no invade dominios funcionales y no crea contratos HTTP. #450 y #446 continúan pendientes.

### Benchmark manual orientativo

En el entorno Codex disponible, la instalación de `argon2-cffi>=25.1.0,<26.0.0` no pudo completarse por bloqueo de red del índice Python (`Tunnel connection failed: 403 Forbidden`), por lo que no se obtuvo una medición ejecutable local de 10 hashes y 10 verificaciones. La política no fue modificada para compensar esa limitación; el benchmark debe ejecutarse en un entorno con la dependencia disponible antes del merge.

## 13. Referencia acotada a identidad local (#456)

`LOCAL_INSTALLATION_CODE` es una variable de deployment y soporte transversal read-only; no es un parámetro administrativo, no amplía `configuracion_general` ni implementa #263. Administrativo podrá consumir la identidad resuelta en incrementos futuros sin adquirir ownership sobre `instalacion` ni seleccionar sucursal.

## 14. Incremento #454 — bootstrap local de credenciales

El bootstrap `init`/`reset` es un command técnico local del núcleo administrativo. Selecciona `usuario` por código exacto, revalida su elegibilidad bajo lock y persiste exclusivamente credenciales `PASSWORD` Argon2id. Resuelve dos veces la identidad canónica de instalación: preflight read-only y transacción autoritativa. El reset conserva y revoca la fila histórica y crea una nueva fila activa/principal en la misma transacción.

Es local y no sincronizable: no hay endpoint HTTP, headers, outbox, eventos, sesiones, tokens, autenticación ni historial runtime. `op_id_alta` brinda replay local simplificado; los locks se adquieren en orden usuario → credenciales por PK. El PHC nunca forma parte de DTOs públicos.

## Incremento #455 — localidad verificable

`credencial_usuario` y `sesion_usuario` son locales por instalación y no sincronizables. La matriz campo por campo y el límite entre tabla histórica de sesiones y runtime inexistente se fijan en `documentacion/SINCRONIZACION/SEGURIDAD-CREDENCIALES-455.md`. La metadata CORE-EF no modifica esta decisión.
# Incremento de seguridad #446

Administrativo es dueño de la autenticación humana mínima mediante `usuario.login`,
`credencial_usuario` y `sesion_usuario`. La sesión es soporte técnico local: bearer
opaco, sólo digest SHA-256 persistido, expiración absoluta de ocho horas y cierre
idempotente. Credenciales, sesiones y tokens no participan de outbox ni sync.
Este incremento no crea principal, autorización, roles efectivos ni sucursal activa;
esas capacidades permanecen pendientes de #447 y posteriores.

# Incremento de seguridad #447 — principal autenticado mínimo

Administrativo construye `AuthenticatedPrincipal` exclusivamente desde un bearer opaco cuya sesión local persiste utilizable y cuyo usuario asociado permanece activo. El UID público proviene de `sesion_usuario.uid_global`; el ID técnico interno de la fila no se expone. La lectura proyecta sólo sesión y usuario, usa `clock_timestamp()`, no bloquea, no escribe, no actualiza actividad ni materializa expiración.

La identidad humana (`Authorization`) permanece separada de la identidad de operación (`X-Op-Id`), el contexto de sucursal (`X-Sucursal-Id`), el contexto técnico (`X-Instalacion-Id`) y la concurrencia (`If-Match-Version`). `X-Usuario-Id` está deprecado como fuente HTTP de identidad, pero continúa en endpoints heredados hasta #461. La sesión y sus secretos son locales/no sincronizables. #447 no agrega roles, permisos ni autorización; #443 y #461 permanecen pendientes. No requiere cambios SQL.

## Incremento de seguridad #443 — autorización administrativa GLOBAL

Administrativo incorpora como soporte reusable y read-only la dependency
`require_administrative_permission(permission_code)`. La identidad proviene únicamente
de `AuthenticatedPrincipal.id_usuario`, resuelta antes por #447; autorización no conoce
`X-Usuario-Id` ni headers CORE-EF. La decisión es default-deny y exige usuario activo,
asignación GLOBAL no eliminada y vigente, rol activo y permiso activo de código exacto.

PostgreSQL es la autoridad de vigencia mediante `clock_timestamp()::timestamp without
time zone`: `fecha_desde` es inclusiva y `fecha_hasta` exclusiva. La evaluación no usa
contexto de sucursal o instalación, no bloquea ni escribe y no produce outbox o sync.
Una falta de concesión es 403 uniforme; un permiso contractual inexistente o una
inconsistencia técnica es 500 sanitizado. La autenticación inválida conserva el 401 de
#447. No hubo cambio SQL. #461, #412 y la autorización contextual #435 siguen pendientes.
