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

La editabilidad administrativa es independiente de exposición y sensibilidad, nace `false` para toda definición existente o futura y sólo puede habilitarse por migración versionada explícita; no existe endpoint write que la modifique. La autorización permission-based ya existe para #412; la autorización del futuro agregado calendario, el cifrado o secret manager y cualquier modelo adicional de visibilidad siguen pendientes o **NO CONFIRMADOS** según su incremento.

## 4. Consumo interdominio y secretos

Otros dominios consumirán parámetros mediante un query service interno del dominio Administrativo; no consultarán directamente las tablas. Ese servicio no está implementado todavía.

Un valor sensible nunca puede exponerse en claro por API, historial, outbox ni logs. El mecanismo de cifrado o secret manager y la caché están **NO CONFIRMADOS**; la autorización existente no resuelve por sí sola secretos ni el futuro agregado calendario. Este freeze fija la prohibición de exposición, no afirma que exista hoy una solución runtime para secretos.

## 5. Freeze específico para #425

**Freeze histórico previo a la recongelación vigente de #425:** el modelo funcional
se describía sólo mediante:

- `parametro_sistema`, como definición;
- `valor_parametro`, como valor `GLOBAL` vigente;
- `id_sucursal IS NULL` e `id_instalacion IS NULL`;
- sin `configuracion_general`;
- sin `configuracion_local`;
- sin catálogos.

Estado vigente recongelado: `parametro_sistema` sigue siendo la fuente canónica de
la definición y `valor_parametro` la fuente canónica de valores y vigencias. La
raíz `configuracion_calendario_comercial` es soporte estructural obligatorio del
agregado para identidad portable, `uid_global`, versión, locking, optimistic
concurrency y procedencia CORE-EF. No almacena ni duplica días, `fecha_desde` o
`fecha_hasta`; esos datos permanecen exclusivamente en `valor_parametro`.

**Freeze histórico previo a #482:** permanecían pendientes el patch SQL funcional,
las dos definiciones, el rango 1–31, read, write, versionado, idempotencia, outbox,
historial, rollback, query service y tests PostgreSQL. #482 supera únicamente los
pendientes estructurales que la sección siguiente declara materializados; los
restantes continúan distribuidos entre #483–#486.

### Incremento estructural #482

#425 queda dividido en incrementos. #482 materializa únicamente las definiciones
`DIA_CIERRE_COMERCIAL` y `DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS` como
`ENTERO`/`GLOBAL`, su rango SQL localizado 1–31, el permiso administrativo y la
tabla raíz física `configuracion_calendario_comercial`. La tabla es núcleo
administrativo de identidad, versión y procedencia técnica; `valor_parametro`
conserva ownership exclusivo de los días y de su vigencia. La cardinalidad física
admite cero o una raíz activa.

La migración valida en reejecución la equivalencia física completa de la raíz
(columnas, identity, defaults, conjunto exacto de PK, UNIQUE, CHECK y FK, e índices) y de sus funciones
y triggers. Un objeto homónimo parcial o incompatible aborta la transacción; no
se reemplaza ni sanea silenciosamente.

Para las funciones contractuales compara el body completo almacenado en `pg_proc`
tras eliminar sólo whitespace, y exige firma sin argumentos, retorno `trigger`,
lenguaje `plpgsql`, configuración y seguridad contractuales. Los triggers se
comparan contra su definición completa, sin admitir eventos, granularidad o
condiciones `WHEN` adicionales, y deben conservar `tgenabled = 'O'`. Un trigger
deshabilitado, `REPLICA` o `ALWAYS` es incompatible y aborta; la migración no lo
reactiva silenciosamente.

Aunque ambas definiciones son exponibles, no sensibles y editables
administrativamente, quedan excluidas contractualmente del PATCH genérico #412.
Su modificación funcional corresponderá exclusivamente al agregado #425 y su
permiso dedicado, para preservar atomicidad y temporalidad; los endpoints del
agregado todavía no existen. El patch también aborta si cualquier valor
preexistente, vigente o histórico, no representa un `ENTERO` ASCII entre 1 y 31.

#482 no crea valores ni fila raíz funcional. No agrega GET, bootstrap,
programación, query service, idempotencia HTTP, outbox, sync o historial
especializado. La primera raíz y los dos primeros valores pertenecen a #484 en
una transacción; #483 es el siguiente incremento y #425 permanece abierto.

Estado vigente: los códigos, nombres, descripciones, tipo `ENTERO`, alcance
`GLOBAL`, rango 1–31 y metadata de ambas claves están **CONFIRMADOS Y
MATERIALIZADOS por #482**: `exponible_api_administrativa = true`,
`es_sensible = false` y `editable_administrativamente = true`. También están
materializados el permiso
`ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR` y la raíz física. Continúan **NO
CONFIRMADOS** el cifrado/secret manager, caché, inclusividad de `fecha_hasta`,
reactivación o reutilización, y la taxonomía final de eventos; #482 no anticipa
esas decisiones.

## 6. Estado CORE-EF físico de `valor_parametro`

#410 implementó preparación física CORE-EF en `valor_parametro`: `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta` y `op_id_ultima_modificacion`. También implementó triggers de insert/update, versionado físico, integridad para definiciones cuyo alcance se resuelve por código `GLOBAL`, garantía concurrente de un único valor global vigente no eliminado, constraints físicas mínimas de vigencia, migración transaccional e integración en resets DEV/TEST.

Para el agregado calendario siguen pendientes, sin declararlos implementados:
idempotencia HTTP, replay, `If-Match-Version` runtime, compare-and-swap en
repository, outbox runtime, historial alineado al valor/contexto, no solapamiento
temporal, resolución, locks y frontera transaccional de los futuros commands. La
autorización de #412 ya existe, pero no sustituye el runtime pendiente de #425.

## 7. Decisión CORE-EF del freeze

- Endpoints: **NO APLICA**; no se agregan ni modifican rutas.
- Clasificación de command/read-like: **NO APLICA**; el incremento es documental.
- Headers, `If-Match-Version`, idempotencia, outbox, lock, versionado, transacción y rollback ejecutables: **NO APLICA** en este incremento.
- Tests CORE-EF y reset PostgreSQL: **NO APLICA**; no se modifica SQL ni runtime.

El `GET /api/v1/administrativo/configuracion/parametros` de #407/PR #414 se preserva como `QUERY_READLIKE`: lista definiciones, pero no lee valores ni ejecuta resolución contextual. #408 documenta este freeze y no agrega endpoints.

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

**Estado histórico al cierre de #410:** era preparación SQL transaccional e
idempotente; todavía no existían #411, #412 ni datos funcionales de #425. Estado
vigente: #411/#412 están implementados y #482 materializa las definiciones, rango
y raíz física del calendario, pero no sus valores ni runtime agregado.

## 10. Incremento #438 — Exposición segura de definiciones administrativas

#438 agrega metadata física mínima a `parametro_sistema` y mantiene separados dos conceptos del núcleo Administrativo: `exponible_api_administrativa` decide si una futura API administrativa puede considerar la definición para lectura de valor, y `es_sensible` clasifica si el valor de la definición no puede exponerse en claro. La política persistida es restrictiva por defecto: `exponible_api_administrativa = false` y `es_sensible = true`; ninguna definición heredada queda exponible automáticamente y cualquier habilitación futura debe realizarse mediante migración versionada explícita, sin inferir por código, nombre, tipo, alcance, descripción o valor.

La constraint `chk_parametro_sistema_exposicion_no_sensible` impide `exponible_api_administrativa AND es_sensible`: una definición sensible no puede quedar marcada como exponible en claro por la API administrativa. #438 no agrega niveles de sensibilidad, enum, catálogo, cifrado, secret manager, redacción parcial ni exposición enmascarada.

#438 no implementa autenticación ni autorización real. Los headers CORE-EF de write no equivalen a autorización, y la metadata física es una política mínima de exposición, no un reemplazo de autenticación. El futuro #411 no debe presentarse como endpoint público y deberá depender de autorización real cuando exista infraestructura verificable.

#438 no implementa el endpoint de #411, no modifica el inventario #407, no agrega commands, no genera outbox, no escribe historial runtime y no toca `valor_parametro`. El futuro #411 sólo podrá devolver un valor cuando `exponible_api_administrativa = true AND es_sensible = false`; para definiciones inexistentes o no exponibles se recomienda responder `404 Not Found` con el error estándar de parámetro no encontrado si el catálogo real lo permite, para no revelar existencia por enumeración. Futuros reads no deben registrar `valor_parametro`, secretos, op IDs, credenciales, payload SQL ni contenido sensible; pueden registrar identificador técnico, código cuando esté permitido, clasificación de error, correlación y stack trace interno.

#441 agrega la metadata física `editable_administrativamente boolean NOT NULL DEFAULT false`, independiente de `exponible_api_administrativa` y `es_sensible`. Ninguna definición queda editable automáticamente y la habilitación futura requiere migración funcional versionada. **Estado histórico al cierre de #441, superado en parte por #482:** #412 conservaba pendiente la implementación del endpoint write y #425 sus definiciones, rangos y runtime. Estado vigente: #412 está implementado; #482 habilita explícitamente la editabilidad de las dos definiciones y materializa su rango, mientras valores funcionales y runtime agregado siguen pendientes. #435 no queda resuelto: overrides, precedencia, fallback, contexto, granularidad y vigencia temporal siguen pendientes.

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
#447. No hubo cambio SQL. Estado al cierre de este incremento: #461, #412 y la autorización contextual #435 seguían pendientes. El estado vigente posterior a PR #478 se documenta en la sección siguiente.

## 15. Estado vigente post-PR #478 — cierre documental #413

Administrativo posee la configuración global: `parametro_sistema` define y `valor_parametro` conserva valores; `configuracion_general` es compatibilidad heredada sin nuevas claves ni consumidores y `configuracion_local` pertenece a Operativo. Los parámetros administrativos no son catálogos maestros. Para el mínimo materializado, los únicos contratos de tipo y alcance son `ENTERO` y `GLOBAL`, como soporte estructural y no como parámetros funcionales.

La definición aplica default-deny mediante `exponible_api_administrativa DEFAULT false`, `es_sensible DEFAULT true` y `editable_administrativamente DEFAULT false`. Exposición, sensibilidad y editabilidad son metadata distintas; la editabilidad es independiente de las otras dos y tampoco equivale a autorización. Exposición y sensibilidad están relacionadas por la restricción de seguridad que impide exponer una definición sensible: `exponible_api_administrativa = true` requiere `es_sensible = false`, por lo que la combinación `true`/`true` es inválida. Ninguna de estas propiedades se infiere del código, tipo o alcance. Una fila GLOBAL marcada vigente cumple `id_sucursal IS NULL`, `id_instalacion IS NULL`, `es_valor_vigente = true` y `deleted_at IS NULL`, conserva `uid_global`, `version_registro`, timestamps, procedencia técnica y op IDs, y existe a lo sumo una por definición. No representa resolución temporal/contextual, override ni fallback.

#407 (`QUERY_READLIKE`) lista definiciones en orden estable sin valores ni metadata interna y sin headers write. #411 (`QUERY_READLIKE`) consulta por selector exacto/case-sensitive sólo definiciones exponibles y no sensibles; oculta inexistente/no exponible/sensible con 404 indistinguible, rechaza no-GLOBAL con 409 y devuelve `SIN_VALOR` o `CON_VALOR_MARCADO_VIGENTE`, raw/tipado `ENTERO`, UID, versión y timestamps con `Cache-Control: no-store`. Es una ruta administrativa no pública por intención contractual y con política material de exposición, pero el runtime actual no depende de Bearer ni permiso; corregir esa deuda corresponde a #461 o follow-up explícito.

PR #478 implementó #412 como `COMMAND_WRITE_NEGOCIO` update-only en la ruta FastAPI con `{codigo_parametro:path}`. Usa Bearer, `get_authenticated_principal` y exclusivamente `AuthenticatedPrincipal.id_usuario`; no requiere, parsea, compara ni usa `X-Usuario-Id`. Exige `X-Op-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version`; antes del claim sólo valida estructura, valida contexto DB sólo para `EXECUTE` y un `REPLAY` no revalida contexto mutable. La condición runtime es permission-based: el principal debe recibir el permiso global activo `ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR` (“Modificar valor global de parámetro”, “Permite modificar un valor GLOBAL administrativo existente y elegible.”) mediante cualquier rol activo aplicable. El rol canónico `ADMINISTRADOR_SISTEMA` proviene del prerequisito separado y #412 crea/valida su vínculo con ese permiso, pero su código no es una condición exclusiva de autorización; no existe rol `ADMIN` mágico ni autoasignación.

#412 es el primer consumidor productivo de #470: `canonical_payload_hash`, `claim_operation` y `complete_operation` operan sobre `public.operacion_idempotente` con `EXECUTE`, `REPLAY` y conflictos `COMMAND`, `TARGET`, `PAYLOAD`. El replay devuelve el snapshot durable sin consultar estado mutable, actualizar, emitir outbox ni incrementar versión; Administrativo no mantiene un ledger paralelo. En `EXECUTE` bloquea el target con `SELECT ... FOR UPDATE`, valida la versión bajo lock y responde 412 `CONCURRENCY_ERROR` ante mismatch. La igualdad tipada (`"015" == 15`, `"-0" == 0`, `"000" == 0`) produce 200 y receipt durable sin UPDATE, timestamp, versión ni outbox. El cambio material usa CAS por `id_valor_parametro + version_registro`, no por versión aislada.

Una única Session/transacción ejecuta claim → contexto → lock → no-op/CAS → outbox material → completion → commit exterior. El rollback revierte valor, versión, timestamps, procedencia, outbox y receipt; sin receipt durable, el retry vuelve a `EXECUTE`. El cambio material registra EVT-ADM-060 `valor_parametro_modificado`, aggregate `valor_parametro`, aggregate_id local, estado `PENDING` y envelope `{metadata,data}`; la identidad portable es `data.uid_global`, metadata contiene `uid_instalacion_origen` y hash SHA-256 lowercase de RFC 8785. `occurred_at` parte de UTC aware y se almacena naive UTC. No-op y replay emiten cero eventos.

El seed `PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO` es técnico controlado: `ENTERO`, `GLOBAL`, exponible, no sensible, editable y valor inicial técnico `"15"` para reproducibilidad DEV/TEST y soporte del primer command. No es configuración funcional, default de sistema, parámetro comercial, #425 ni valor de negocio.

**Estado histórico al cierre de #413:** fuera de ese incremento permanecían #425,
#435, #461 y #265. Estado vigente post-#482: #425 continúa abierto, pero sus dos
definiciones, rango, permiso y raíz física ya están materializados; valores y fila
raíz funcionales, runtime agregado, eventos, sync e historial especializado siguen
fuera de #482. #435, #461, #265, secretos, CRUD genérico, UI, consumers remotos,
reconciliación y eliminación física de `configuracion_general` no cambian aquí.
