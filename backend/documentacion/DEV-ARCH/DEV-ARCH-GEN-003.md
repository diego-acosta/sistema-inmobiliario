# DEV-ARCH-GEN-003 — Identidad, autorización y contexto central

## 1. Estado, alcance y evidencia

**ARQUITECTURA OBJETIVO — contrato de PR 02; primer slice auth implementado en la rama, validado externamente en 3503ff2, incluida la inicialización limpia y la frontera HTTP UTC (§19).**
Base histórica de PR 02: `transition/central-authority`, commit
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

PR04 cierra D1 en §5 sobre `5bcefa5a6215557eb9644c67deb7c27de2b1e671`,
merge de #544. El evaluador general y el contexto D1 se implementarán en PR05.

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

Login central inserta sucursal e instalación NULL. El principal y `/me` ya no
proyectan esos campos; no se encontraron callers productivos que los requieran.
Se adaptaron schemas y fixtures de consumidores; no se selecciona sucursal al autenticar.

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
de `TimeZone`. Sesiones y bootstrap usan UTC explícito en consultas, defaults y triggers;
sus pruebas PostgreSQL no UTC fueron validadas en el head 3503ff2 (§19).
El cast de autorización GLOBAL permanece pendiente de migración (§16). No convertir timestamps económicos
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

Para un command contextual humano de escritura, antes de ejecutar o devolver replay
(orden completo y reglas de lectura en §5):

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
es rechazo de autorización, sin efectos. §5.3 distingue los flags para reads y
writes; ninguno concede por sí solo un permiso.

**Commands GLOBAL sin contexto operativo:** su contrato puede declarar
`id_sucursal = NULL`, con permiso GLOBAL y sin `usuario_sucursal` ficticio.
No se convierte una operación contextual en GLOBAL por omitir el header.
Si el contrato declara GLOBAL sin contexto, el selector se ignora íntegramente
según §5.4; no cambia el alcance ni habilita roles contextuales. No se impone
sucursal por mera procedencia Sync.
Los writes GLOBAL existentes que hoy requieren contexto conservan su API hasta
su migración. Esto no redefine alcance de parámetros ni resuelve #435.

## 5. D1 cerrada — autorización GLOBAL y CONTEXTUAL (PR04)

**Contrato objetivo aprobado; evaluador completo NO implementado.** Corte de
lectura: `5bcefa5a6215557eb9644c67deb7c27de2b1e671`, merge de #544 en
`transition/central-authority`. PR04 modifica sólo documentación; PR05 materializa
este contrato para actores humanos autenticados por sesión/Bearer. D2 sigue abierta.
No se crea una entidad de seguridad ni una jerarquía de roles nueva.

### 5.1 Evidencia física y runtime antes de decidir

Rutas de repositorios relativas a `backend/app/infrastructure/persistence/repositories/`.
SQL base: `backend/database/schema_inmobiliaria_20260418.sql`; evoluciones relevantes:
`patch_usuario_rol_seguridad_core_ef_20260630.sql` y
`patch_usuario_sucursal_core_ef_20260702.sql`. Se inspeccionaron los patches
vigentes: no se encontró evolución que agregue scope/tiempo a denegaciones ni
un evaluador de `usuario_rol_sucursal` en `backend/app/`.

| Pieza | Existe SQL | Existe runtime | Uso actual / límite | Clasificación |
| --- | --- | --- | --- | --- |
| `usuario` | Sí: identidad y elegibilidad | Sí | Auth central de #544; USUARIO distinto de PERSONA | REUTILIZAR |
| `usuario_sucursal` | Sí: usuario/sucursal, estado, flags, `[desde,hasta)`, deleted_at | Sí, repository y proyección #536 | Habilitación operativa; listados no prueban vigencia actual | REUTILIZAR |
| `usuario_rol_seguridad` | Sí: usuario/rol, desde/hasta, deleted_at y metadata | Sí, CRUD y evaluador GLOBAL | Asignación GLOBAL; writer usa CURRENT_TIMESTAMP, evaluador cast dependiente de TimeZone | MIGRAR_EN_PR05 |
| `usuario_rol_sucursal` | Sí: FKs directas usuario/rol/sucursal, desde/hasta | No evaluador encontrado | No FK a usuario_rol_seguridad; sin estado ni deleted_at | MIGRAR_EN_PR05 |
| `rol_seguridad` | Sí: código único y estado_rol | Sí | Rol ACTIVO; no tiene scope, vigencia ni deleted_at | REUTILIZAR |
| `permiso` | Sí: código único y estado_permiso | Sí | Código contractual exacto; no tiene scope ni deleted_at | REUTILIZAR |
| `rol_seguridad_permiso` | Sí: FKs rol/permiso y UNIQUE de pareja | Sí, evaluador GLOBAL | Asociación; no tiene estado, vigencia ni deleted_at | REUTILIZAR |
| `denegacion_explicita` | Sí: PK, FKs usuario/permiso, motivo | No evaluador encontrado | Sin sucursal, estado, vigencia ni deleted_at; sin UNIQUE de pareja | MIGRAR_EN_PR05 |
| `require_administrative_permission` / servicio / repository | Usa tablas anteriores | Sí | GLOBAL, no deny ni habilitación/contexto; devuelve principal | MIGRAR_EN_PR05 |
| `AuthenticatedPrincipal` / dependency Bearer | sesión/usuario | Sí | Seis campos de identidad, sin sucursal/instalación | REUTILIZAR |
| `X-Sucursal-Id` | NO APLICA: selector HTTP | Sí, parsing CORE-EF | Obligatorio en varios writes legacy incluso GLOBAL | MIGRAR_EN_PR05 |
| `TechnicalContextRepository.resolve_operational_context` | sucursal/usuario_sucursal/instalacion | Sí | UTC, elegibilidad y alcance; exige instalación como argumento | MIGRAR_EN_PR05 |
| `ResolvedLocalCommandContext`, policy y adapters API | Usan tablas existentes | Sí, sin adopción productiva del adapter fuera de su módulo encontrada | Resolver #456, actor técnico incompleto y headers legacy | LEGACY_TRANSICIONAL |
| `LOCAL_INSTALLATION_CODE`, resolver #456 y procedencia de instalación | instalacion/FKs | Sí, fuera de auth #544 | No forman parte de D1; retirar junto con sus callers | RETIRAR_POSTERIORMENTE |
| Actor técnico D2 | No se prescribe modelo | No autenticación técnica completa | No usar principal humano ficticio | NO_APLICA |

`usuario_rol_sucursal` tiene índice de vigencia, no exclusión de intervalos;
los índices parciales GLOBAL y usuario_sucursal sólo excluyen ciertos duplicados
abiertos, no todo solapamiento temporal. La evaluación es existencial: varias
concesiones válidas no multiplican derechos ni son por sí solas error técnico.
La matriz describe archivos reales, no introspección de una DB en ejecución;
no se ejecutaron suites en PR04.

### 5.2 Perfiles y composición única

Cada operación protegida declara en servidor su perfil **GLOBAL** o **CONTEXTUAL**,
su `permission_code` exacto y si es lectura o escritura. El cliente no elige el
perfil. No inferirlo del nombre del permiso ni agregar una columna scope a permiso.
Una operación puede usar varios permisos sólo si su contrato expresa cómo se
combinan; para cada permiso se aplica D1, sin permisos implícitos por rol nominal.

Definiciones: P = principal válido; E = permiso contractual definido y ACTIVO;
G = concesión GLOBAL vigente; C(s) = concesión contextual vigente en sucursal s;
H(s) = habilitación vigente correspondiente a lectura/escritura; D = existe
`denegacion_explicita` para usuario/permiso. La validación del target es adicional.

- **GLOBAL:** P AND E AND G AND NOT D. `id_sucursal = NULL`; no se consulta ni
  exige usuario_sucursal. C(s) nunca sustituye G, aunque se envíe un selector.
- **CONTEXTUAL:** P AND sucursal válida s AND H(s) AND E AND (G OR C(s)) AND NOT D.
  G satisface el permiso contextual, pero no crea H(s) ni acceso a otra sucursal.
- **DENY > ALLOW**: una denegación aplicable bloquea todas las vías de concesión.
  No hay bypass de administrador, permiso por header, herencia entre roles ni
  asignación automática al autenticar.

Se adopta la unión propuesta por el responsable: reutiliza las asignaciones
GLOBAL y las FKs directas contextuales existentes y evita duplicar roles por
sucursal para un usuario GLOBAL ya habilitado. El runtime GLOBAL no resuelve esa
unión todavía; sus tests no son evidencia de implementación D1.

### 5.3 Elegibilidad exacta, temporalidad y denegaciones

Un único instante de autorización por request se obtiene de PostgreSQL mediante
`clock_timestamp() AT TIME ZONE 'UTC'`. Las proyecciones de seguridad se evalúan
coherentemente sobre ese instante y snapshot, sin cachear permisos en la sesión.
La vigencia es `[fecha_desde, fecha_hasta)`: desde inclusivo, hasta exclusivo;
NULL en hasta significa sin fin, intervalo vacío nunca habilita. PR05 alinea el
reloj GLOBAL y sus writers de instantes técnicos con UTC, sin convertir filas
históricas ni fechas económicas. No basta corregir el reader dejando writers en
hora local. El resolver read-only no hace commit ni modifica actividad de sesión.

- Sucursal contextual: existente, `estado_sucursal = ACTIVA`,
  `permite_operacion = true`, `deleted_at IS NULL`, `fecha_baja IS NULL` (§4).
- H(s): vínculo del mismo usuario/sucursal, `estado_vinculo = ACTIVO`, no eliminado
  y vigente. Para writes se exige `puede_operar = true`; para queries contextuales
  `puede_consultar = true`. Consultar no exige puede_operar, ni operar lo implica.
  `puede_administrar` no sustituye el permiso ni ninguno de esos flags y no se
  convierte en un tercer bypass. No se infiere acceso del tipo de habilitación.
- G: usuario_rol_seguridad del actor, vigente y `deleted_at IS NULL`, unido por
  id_rol_seguridad a rol ACTIVO y por rol_seguridad_permiso al permiso ACTIVO.
- C(s): usuario_rol_sucursal del actor y s, vigente, unido al mismo catálogo de
  roles y permisos activos. No exigir que también exista usuario_rol_seguridad.
  No inventar estado/deleted_at en la asignación contextual.
- E: código case-sensitive, sin normalizar mayúsculas ni escoger primer resultado.
  Permiso existente INACTIVO no concede (403); un código contractual inexistente,
  incluso por borrado físico, es inconsistencia técnica (500). No hay soft delete
  de permiso/rol en el schema actual. Rol inactivo, asignación vencida/eliminada o
  asociación rol-permiso ausente no conceden; otra vía válida puede hacerlo.
- D: cualquier fila existente para usuario + permiso deniega ese permiso en
  GLOBAL y en **todas** las sucursales. No caduca ni tiene scope por sucursal.
  El motivo es explicativo, no predicado. Varias filas coincidentes siguen siendo
  deny, no se elige una ni se inventa unicidad; para levantarlo no debe quedar
  ninguna denegación aplicable. PR04 no diseña un CRUD nuevo de denegaciones.
- Vínculos huérfanos, estructura incompatible, estados desconocidos o duplicidad
  que viola unicidades contractuales son error técnico, no 403 ni allow. Varios
  roles/asignaciones/concesiones coherentes se reducen con EXISTS/OR; no se
  confunden con corrupción. Un solapamiento de habilitaciones válidas satisface
  H si al menos una fila cumple todos sus predicados; no combinar flags de filas
  inactivas/fuera de vigencia. Sólo denegacion_explicita expresa un deny prevalente.

### 5.4 Request, headers, lecturas y recursos

`X-Sucursal-Id` es obligatorio en CONTEXTUAL, incluidos reads contextuales. Usar
parsing común de entero positivo, dentro del rango bigint de la FK; ausencia,
valor inválido, ambiguo o repetido se rechaza con 400 antes de consultar target.
No se toma sucursal de sesión, instalación, predeterminada, primera asignación,
payload o target. Manipular el selector sólo cambia la sucursal a validar.

**GLOBAL ignora X-Sucursal-Id**, incluso si su valor es inválido: no lo parsea,
no lo usa para decidir permisos ni lo copia al contexto/receipt/auditoría; conserva
NULL. Así enviar el header nunca convierte G en C ni C en G. Las rutas de auth
preautenticadas/login, logout y `/me` conservan el contrato #544; no se les añade
un permiso D1 ni un selector.

Un usuario sin sucursales puede autenticarse, usar `/me` y ejecutar operaciones
GLOBAL autorizadas; todas sus operaciones contextuales se deniegan. Con varias
sucursales, cada request elige una: la misma sesión puede atender requests
simultáneos en A y B si ambos pasan D1. La predeterminada sólo es preferencia UI.

Reads protegidos también requieren permiso y deny actuales; no heredan op_id,
CAS ni efectos write. Un listado contextual filtra por s en DB antes de contar,
agrupar o paginar; no trae datos ajenos para filtrarlos después de exponer totales.
Una lectura GLOBAL usa concesión GLOBAL sin sucursal; no convierte automáticamente
un listado contextual en una consulta de todas las sucursales.

El dominio valida por separado la pertenencia funcional del target y de todos
los recursos afectados a s, sin moverlos ni cambiar ownership. Para CREATE valida
el ámbito de creación y las referencias padre; para multi-entidad no basta la
primera raíz. Recursos compartidos siguen su asociación de dominio, no se inventa
una única FK universal. Si no puede acreditarse pertenencia, incluido target
inexistente en esa consulta acotada, el control de scope responde 403 indistinguible,
sin revelar existencia ni devolver receipt. Otras validaciones de negocio sólo
proceden después. Los contratos heredados 404 no cambian en PR04: su adopción
central exige alinear callers y tests antes de declarar el endpoint migrado.

### 5.5 Orden y errores cerrados

Orden: autenticar → validar selector contractual → permiso definido/configuración
coherente → sucursal/habilitación → concesiones y deny actuales → target/scope →
idempotencia (§12) → EXECUTE o REPLAY autorizado. En GLOBAL se omiten sucursal/H.
Una lectura coherente puede agrupar consultas, pero nunca exponer un receipt antes
de esos controles. Configuración incoherente detectada es error técnico aunque
ninguna concesión permitiría continuar; no disfrazarla de falta de privilegios.

| Situación | HTTP objetivo / respuesta |
| --- | --- |
| Bearer requerido ausente/malformado, sesión expirada/revocada/inválida, usuario inelegible | 401 `INVALID_SESSION`, según #544; ningún permiso se evalúa sin principal |
| Selector contextual ausente/inválido/repetido | 400 `LOCAL_COMMAND_HEADER_INVALID` legacy se migra a `CENTRAL_CONTEXT_HEADER_INVALID`; ErrorResponse, header y razón sin datos sensibles |
| Principal válido sin H, sucursal inexistente/inactiva/no operable, sin concesión, deny o target fuera de scope | 403 `autorizacion_insuficiente`, mismo mensaje sanitizado; no revelar cuál control falló |
| Permiso contractual inexistente, configuración/resultado incoherente, corrupción de referencias, fallo de persistencia | 500 `inconsistencia_roles_permisos`, sanitizado; detalles sólo en diagnóstico protegido |

Se reutilizan los mapeos 401/403/500 actuales donde corresponden; el código central
400 es contrato a materializar por PR05, no implementación existente. Login inválido
conserva `INVALID_CREDENTIALS`. Errores de payload/negocio/CAS mantienen sus contratos
una vez superado D1. Un 403 no revoca ni renueva sesión.

### 5.6 Tabla de decisión y adversarios

Salvo indicación: principal/permiso válidos, target del ámbito, sin error técnico.
H representa vínculo vigente y flag requerido; A/B son sucursales diferentes.

| Caso | Sucursal | H | Permiso GLOBAL | Permiso contextual | Deny | Resultado |
| --- | --- | --- | --- | --- | --- | --- |
| GLOBAL con G | NULL | No aplica | Sí | No | No | ALLOW |
| GLOBAL sólo C | NULL | No aplica | No | A | No | 403 |
| CONTEXTUAL con G | A | Sí | Sí | No | No | ALLOW |
| CONTEXTUAL con C(A) | A | Sí | No | A | No | ALLOW |
| CONTEXTUAL sólo C(B) | A | Sí | No | B | No | 403 |
| CONTEXTUAL sin vínculo | A | No | Sí | A | No | 403 |
| Vínculo inactivo/eliminado/futuro/vencido | A | No | Sí | A | No | 403 |
| GLOBAL con deny | NULL | No aplica | Sí | A | Sí | 403 |
| CONTEXTUAL G + deny | A | Sí | Sí | No | Sí | 403 |
| CONTEXTUAL C + deny | A | Sí | No | A | Sí | 403 |
| Usuario sin sucursales, GLOBAL con G | NULL | No aplica | Sí | No | No | ALLOW; login/me también permitidos por #544 |
| Usuario sin sucursales, CONTEXTUAL | A | No | Sí | No | No | 403 |
| Selector requerido ausente | Ausente | — | Sí | A | No | 400 |
| Selector requerido inválido/ambiguo | Inválida | — | Sí | A | No | 400 |
| Target B, actor autorizado A | A | Sí | Sí | A | No | 403 |
| Header manipulado a B sin H(B) | B | No | Sí | A | No | 403 |
| Write con puede_operar=false | A | No | Sí | A | No | 403 |
| Read con puede_consultar=false | A | No | Sí | A | No | 403 |
| Único rol vencido o inactivo | A | Sí | No vigente | No vigente | No | 403 |
| Permiso existente inactivo | A | Sí | No efectiva | No efectiva | No | 403 |
| Permiso borrado físicamente/no definido | A | Sí | — | — | — | 500 |
| Única asociación rol-permiso ausente | A | Sí | No | No | No | 403 |
| Asociación huérfana/inconsistencia física | A | Sí | — | — | — | 500 |
| Sesión válida sin roles | NULL (GLOBAL) | No aplica | No | No | No | 403; /me sigue permitido |
| G y H(A), H(B), requests simultáneos | A / B | Sí / Sí | Sí | No | No | ALLOW independiente por request |
| GLOBAL con selector extra inválido | NULL | No aplica | Sí | No | No | ALLOW; selector ignorado |
| Replay tras perder permiso/H o adquirir deny | A | Según estado actual | No efectiva | No efectiva | Puede existir | 403; sin receipt |

PR05 debe convertir la tabla en pruebas de comportamiento: UTC no dependiente de
TimeZone, límites exactos desde/hasta, roles múltiples con OR, intervalos vacíos,
flags independientes, deny duplicado, selector manipulado, targets ajenos y replay
tras revocación. No eliminar tests legacy para aparentar D1 implementada.

### 5.7 Consumidores y aceptación de PR05

Actualmente `require_administrative_permission` protege cuatro rutas administrativas:
GET/POST/PUT `/api/v1/administrativo/configuracion/calendario-comercial`
(`ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR`) y PATCH
`/api/v1/administrativo/configuracion/parametros/{codigo_parametro:path}/valor-global`
(`ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR`). Son alcance funcional GLOBAL;
los writes todavía exigen sucursal/instalación por metadata legacy. El GET no las
exige. PR04 no modifica esas APIs ni el calendario ni la parametrización #435.

`test_administrative_authorization.py` congela expresamente ausencia de joins
contextuales y el cast temporal antiguo; su par PostgreSQL cubre estados,
vigencia GLOBAL, roles múltiples y lectura sin efectos. `test_local_command_context_536*`
cubre habilitación, UTC y dependencia de instalación; `test_administrativo_alcance_operativo.py`
cubre write UTC, flags y predeterminada. Es evidencia parcial, no D1 completa.

PR05 debe materializar contexto humano central, evaluador GLOBAL/contextual/deny,
reloj y writers técnicos UTC afectados, mapeos y regresión de esos consumidores.
El catálogo de permisos existente se reutiliza; no crear permisos directos,
herencia entre roles ni una nueva autenticación. Adoptar cada ruta con su caller,
fingerprint y pertenencia coherentes; una ruta no queda migrada por cambiar sólo
el helper. Nuevos commands/queries contextuales, menús/visibilidad basados en D1
y replay central quedan bloqueados hasta esa evidencia runtime. Los contratos de
cada dominio determinan targets; PR05 no implementa masivamente esos dominios.

El helper actual, contexto local y metadatos transicionales pueden permanecer
hasta adaptar callers, **no para preservar datos**. No se diseñan dual-read,
backfills, traducciones de identidad, conversión histórica ni upgrade in-place.
**Premisa cerrada: no hay datos útiles que preservar.** DEV/TEST se reconstruyen
cuando corresponda con el flujo oficial; baseline/seeds reproducibles no son datos
productivos. Si en un incremento futuro aparecen datos útiles reales, se detiene
esa premisa y se diseña una migración específica en ese momento. D1 queda cerrada
contractualmente; D2 y Gate 2 completo permanecen pendientes.

## 6. INSTALACION y LOCAL_INSTALLATION_CODE

**ARQUITECTURA OBJETIVO: INSTALACION = NO APLICA**, como entidad funcional
ni técnica. No se reinterpreta como actor, dispositivo, estación o deployment
ni se crea sustituto persistido. El funcionamiento final no requiere instalación.

**RUNTIME / MODELO ACTUAL: entidad legacy todavía materializada.** Las
persistencias y relaciones funcionales heredadas que la referencian siguen
válidas transicionalmente; la decisión objetivo no las elimina ni permite
ignorar sus restricciones actuales.

**TRANSICIÓN: migrar reglas y consumidores antes de retirar dependencias.**
Tabla, FKs, casos de uso, estados, eventos, resolvers, headers y procedencia se
retiran progresivamente con la migración del dominio responsable. Su existencia
física temporal no autoriza nuevas dependencias ni devuelve INSTALACION al modelo
objetivo; tampoco justifica conservarla a largo plazo. PR 02 no elimina esas piezas.

### Relaciones funcionales heredadas: retiro coordinado

El objetivo de Caja es la relación directa `SUCURSAL → CAJA_OPERATIVA`, sin
instalación intermedia obligatoria para existir u operar. Caja conserva identidad
propia, apertura, estado, movimientos, cierre, responsable y numeración/reglas
funcionales aplicables; no se fija aquí una nueva cardinalidad.

El SQL actual `backend/database/patch_caja_operativa_base_20260704.sql` ya define
FK directa a sucursal y también `id_instalacion NOT NULL` con FK, además de
`ux_caja_operativa_codigo_activa` por `(id_sucursal, id_instalacion, codigo_caja)`
para filas no eliminadas. Esa dependencia funcional/física sigue vigente hasta
migrar sus reglas; no es sólo metadata de Sync descartable.

**MIGRACIÓN FUNCIONAL PENDIENTE — Operativo:** determinar el ámbito central de
unicidad de `codigo_caja` al retirar instalación; no inferir automáticamente
unicidad por sucursal ni permitir colisiones. Migrar también el contexto heredado
de aperturas/movimientos/cierres y la configuración local por sucursal/instalación,
resolviendo qué reglas permanecen en caja o sucursal antes de retirar sus FKs y
selectores. No elegir aquí cardinalidades ni nuevos valores de configuración.

Alta/modificación/baja/consulta, estados y eventos de instalación:
**LEGACY / EN RETIRADA**, no objetivo final. Su retiro de DEV-SRV, catálogos,
API y runtime corresponde al incremento Operativo junto con sus consumidores;
el resolver #456 conserva compatibilidad transicional hasta migrar sus callers.
[El freeze Operativo](dominios/operativo/DEV-ARCH-OPE-001.md) delimita esta
precedencia sobre sus secciones históricas. [Analítico](dominios/analitico/DEV-ARCH-ANA-001.md)
puede leer instalación existente mientras se migra, pero deberá consumir las
fuentes funcionales resultantes sin exigir conservarla. Retirar instalación no
puede romper caja ni lectores antes de adaptar sus dependencias.

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
| `X-Sucursal-Id` | CONDICIONAL: obligatorio en CONTEXTUAL (reads/writes); ignorado en GLOBAL, contexto NULL; §§4–5 |
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
antiguos como nuevos. En esta transición no hay datos útiles a preservar: el
corte usa rebuild oficial DEV/TEST, sin dual-read ni migración de receipts. No
alterar la canonicalización RFC 8785 ni ampliar el ledger en PR04. La autorización
D1 se revalida antes del claim y de exponer replay, incluido target/scope; si el
target ya no permite acreditar autorización, 403 sin receipt. Revalidar seguridad
no significa recalcular estado económico, CAS ni efectos del command completado.

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
composición GLOBAL/contextual se rige por D1 cerrada en §5. Esa decisión explícita
de PR04 reemplaza la apertura anterior, sin ampliar precedencia a otros negocios.

## 16. Matriz de evidencia objetivo vs runtime actual

Rutas relativas al repositorio. Matriz actualizada para el slice auth central;
§19 registra la validación vigente de auth central, inicialización limpia y frontera HTTP UTC.

| Área / evidencia concreta | Runtime actual | Objetivo / pendiente responsable |
| --- | --- | --- |
| `backend/app/application/administrativo/authentication.py`; `backend/app/api/authentication.py` | Login/principal sin resolver instalación ni proyectar sucursal; TTL 8h y logout revocable | Implementado en rama; validado externamente en 3503ff2, incluida la inicialización limpia y la frontera HTTP UTC (§19) |
| `backend/app/infrastructure/persistence/repositories/sesion_usuario_repository.py`; `backend/database/patch_sesion_usuario_runtime_20260807.sql` | Insert central con instalación/sucursal NULL, digest/TTL; patch_auth_central_20260914.sql conserva FK y usa UTC explícito | Patch, triggers y zona no UTC validados en PostgreSQL 18.0 sobre 3503ff2 (§19) |
| `backend/app/config/settings.py`; `backend/app/application/common/local_installation.py`; `backend/app/infrastructure/persistence/repositories/instalacion_repository.py` | Settings permite LOCAL_INSTALLATION_CODE ausente; DATABASE_URL sigue obligatorio; resolver legacy falla explícitamente antes del lookup si falta configuración | Sólo contexto legacy sigue consumiendo el resolver; sin fallback |
| `backend/app/application/administrativo/commands/bootstrap_credential.py`; `backend/database/patch_credencial_usuario_core_ef_20260805.sql` | CLI crea/resetea sin resolver ni campos de instalación en preview/result; procedencia NULL, FKs conservadas | Preserva Argon2id/locks/replay; validado externamente en 3503ff2, incluida la inicialización limpia y la frontera HTTP UTC (§19) |
| `backend/app/application/common/local_command_context.py`, `local_command_headers.py`; `backend/app/api/local_command_context.py` | Sucursal por request; instalación resuelta incluso sin assertion; op_id requerido; adapters sin adopción productiva encontrada fuera del módulo | Técnico: contexto §7 sin instalación, policy idempotencia/CAS; no quitar protecciones legacy en bloque |
| `backend/app/infrastructure/persistence/repositories/technical_context_repository.py` | Reloj UTC, sucursal elegible, vínculo vigente + instalación↔sucursal | Técnico/Administrativo/Operativo: conservar scope, retirar sólo validación instalación |
| `backend/app/infrastructure/persistence/repositories/usuario_sucursal_repository.py`; `backend/database/patch_usuario_sucursal_core_ef_20260702.sql` | Flags, predeterminada e índices; listas no sustituyen proyección temporal #536 | Administrativo: reutilizar asignaciones y UTC; no crear asignación a deployment |
| `backend/app/application/administrativo/authorization.py`; `backend/app/api/administrative_authorization.py`; `backend/app/infrastructure/persistence/repositories/administrative_authorization_repository.py` | Permiso GLOBAL reusable, sin denegación/scope contextual; reloj por cast | Administrativo: UTC, denegaciones y composición de §5 en PR05; no afirmar cobertura transversal |
| `backend/database/schema_inmobiliaria_20260418.sql`, tablas de §5 | usuario_rol_sucursal tiene FKs directas usuario/rol/sucursal; denegación sólo usuario/permiso | D1 cerrada en §5 sobre estas relaciones; implementación PR05, sin columnas ficticias |
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

1. **Primer slice runtime: autenticación/sesión y bootstrap sin instalación.**
   Implementado en rama; validado externamente en 3503ff2, incluida la inicialización limpia y la frontera HTTP UTC (§19).
   Partir de transición tras integrar este contrato. Alcance Administrativo +
   settings/SQL estrictamente necesarios: mantener bearer/Argon2id/revocación/TTL,
   desacoplar login, credenciales y principal; alinear `/me`, DEV-API y sus callers.
   El esquema debe permitir ese camino sin fila de instalación. El cambio de
   Settings no puede romper consumidores legacy todavía activos: aislar su
   validación explícita hasta retirarlos. No habilitar commands contextuales aún.
2. **D1 cerrada contractualmente por PR04** en §5; evaluador todavía pendiente.
   #544 ya fue mergeado a transición en `5bcefa5a6215557eb9644c67deb7c27de2b1e671`.
3. **PR05:** materializar contexto humano y autorización D1 conforme §5.7;
   alinear callers/replay y procedencia por vertical coherente. Reutilizar las
   invariantes del ledger sin migrar datos; DEV/TEST usan rebuild limpio.
4. Adopción por dominios/Flet, contratos API y retiro físico incremental de
   instalación y Sync tras inventario de consumidores. D2 precede automatización.

Aceptación del paso 1: login, `/me`, expiración y logout sin LOCAL_INSTALLATION_CODE
ni instalación; usuarios/credenciales inválidos siguen fallando; ningún secreto
expuesto; pruebas UTC en PostgreSQL no UTC; logout repetido sin mutación adicional;
compatibilidad de callers explícita; SQL/reset limpio reproducible. Suites focales
autenticación/credenciales/principal y regresión afectada, sin afirmar migración
de permisos o contexto de negocio. Nuevos endpoints/DTO innecesarios no forman
parte de ese incremento. Estos criterios no autorizan implementarlo en PR 02.

## 18. Decisiones y límites de cierre

**D1 CERRADA por PR04:** política única en §5. Su implementación general permanece
pendiente de PR05; no se declara cerrada por la existencia del helper GLOBAL.
La decisión abierta restante es D2:

| ID | DECISIÓN ABIERTA | Alternativas e impacto | Bloquea |
| --- | --- | --- | --- |
| D2 | Autenticación/autorización concreta de jobs e integraciones | Proceso interno con autoridad delimitada vs credencial técnica verificada para frontera externa; cambia ciclo de secretos, revocación y facultades. Resolver por contrato de actor, sin usuario humano ficticio ni nueva instalación | Automatización/commands técnicos protegidos |

INSTALACION, ausencia de sustituto persistido, selección por request, TTL/sesión,
misión de op_id/CAS y reglas de replay anteriores **no son decisiones abiertas**.
Los detalles de aplicación por agregado requieren inventario en su PR, respetando
estas matrices y sus reglas económicas; no habilitan volver a exigir Sync.
D1 contractual cerrada no equivale a contexto/evaluador implementados. D2 abierta,
la materialización de PR05 y la adopción restante impiden declarar Gate 2 de
GEN-002 satisfecho; no se habilitan actores técnicos con el principal humano.

## 19. Primer incremento runtime central — evidencia y límite

Evidencia histórica de PR03 (#544), integrado en transición por
`5bcefa5a6215557eb9644c67deb7c27de2b1e671`. Base de aquel incremento:
merge #543 `3a32b8d80d267e3b20a19045156059bda2339d83`.
Clasificación de dependencias auditadas:

| Dependencia / consumers directos | Clasificación | Resultado |
| --- | --- | --- |
| Settings, imports main/database, auth service/router/dependency/schema `/me` | MIGRAR_EN_ESTE_PR | Configuración opcional; autenticación sólo sesión/usuario |
| SesionUsuarioRepository, sesión SQL, triggers/relojes | MIGRAR_EN_ESTE_PR | Instalación nullable con FK; tiempos físicos UTC explícitos |
| BootstrapCredentialCommand, CLI, CredencialUsuarioRepository | MIGRAR_EN_ESTE_PR | Sin resolver/DTO instalación; procedencia nullable existente, op_id/locks conservados |
| Tests de auth/bootstrap/principal y fixtures consumidores | MIGRAR_EN_ESTE_PR | Contrato central y matriz PostgreSQL no UTC agregados |
| local_installation, local_command_context y adapters | LEGACY_PRESERVAR | Sin config el resolver falla cerrado; contexto no migrado |
| Caja, instalación física, Sync, ledger general, permisos contextuales/Flet | FUERA_DE_ALCANCE | Sin cambio de implementación; D1/D2 abiertas en aquel corte; cierre contractual D1 en §5 |

El patch incremental conserva tabla INSTALACION, FKs nullable y constraints de
credenciales/sesiones; sólo sesión pierde NOT NULL en su origen. Credenciales
ya admitían NULL y no requieren cambio de nullability. Defaults y cuatro triggers
conservan UID/versionado/procedencia legacy, cambiando la representación temporal
a UTC. Reaplicar patches históricos aislados no es el procedimiento de despliegue:
resets aplican la cadena ordenada y la reejecución del patch central es idempotente.

**Validación vigente confirmada por el responsable sobre
`3503ff284df0de8817456911f7655786db706ade` — Windows / PostgreSQL 18.0.**
Incluye el cambio runtime de motivo de revocación a `RESET_ADMINISTRATIVO` y
el cierre de semántica residual local/central de auth.

- Sin DB: **83 passed, 2 warnings**.
- Primera focal PostgreSQL: **50 passed, 1 failed, 1 warning**. El único fallo fue
  `test_concurrent_reset_reset_are_legitimate_serial_rotations`.
- Revalidación aislada posterior del caso concurrente: **10/10 PASS** consecutivos.
- Grupo PostgreSQL ampliado relacionado: **106 passed, 1 warning**, incluido ese caso.
- `python -m compileall -q backend/app backend/tests` y `git diff --check`: **PASS**;
  working tree limpio según la validación reportada.

El fallo concurrente inicial se conserva como evidencia: **fallo transitorio no
reproducido**, no bug confirmado ni una ejecución siempre verde. El warning de
PostgreSQL es `StarletteDeprecationWarning` por httpx/starlette.testclient, no fallo
funcional. Estos resultados fueron aportados por el responsable; no se repitieron
en este ajuste documental. UTC, TTL 8h y schema permanecen intactos.

**Evidencia histórica del fix HTTP UTC, previa al cambio final de semántica local/reset:**
`2d1ff2f227babd36040c6b0a767465304e7e2d72` — Windows / PostgreSQL 18.0:
48 focales y 106 PostgreSQL relacionados passed, 1 warning por suite.
Verificó JSON real con offset UTC explícito en `expires_at` y `autenticado_en`,
con persistencia UTC-naive y TTL 8h intactos. API/helper aislado: 3 PASS;
unitarios: 42 PASS; ejecución conjunta: 45 passed, 2 warnings;
compileall/diff --check PASS y working tree clean en ese head anterior.

**Evidencia histórica previa al fix HTTP UTC:**
Validación externa confirmada por el responsable sobre
`c70ea181d58c0eb2bb2a9bdb8b7d83e6a416f844` — Windows / PostgreSQL 18.0.
Reset oficial DEV/TEST **PASS**: DEV con baseline técnico, seed e índices financieros
demo; TEST con baseline técnico. Suite focal **29 passed, 1 warning**;
grupo PostgreSQL de siete archivos **104 passed, 1 warning**;
unitarios con `--noconftest` **149 passed, 1 warning**;
`python -m compileall -q backend/app backend/tests` y `git diff --check` **PASS**;
`git status`: **working tree clean** en el head validado.
La ejecución confirma inicialización con auth vacío, marker `AUTH_CENTRAL_EMPTY_INIT_V1`,
rechazo atómico sin cambios parciales ante auth legacy sin marker, reejecución
preservadora con datos centrales, UTC, FKs, constraints, versionado y comparación
contractual cross-platform. Es evidencia local aportada, no una ejecución en Work.

**Evidencia histórica (heads anteriores):** `c872425e` registró 97 casos PostgreSQL
PASS y `75bb43ce` registró 99. Las limitaciones de conexión de Work pertenecen a
esas etapas; no constituyen un bloqueo vigente tras la validación local vigente de `3503ff2`.

La transición DEV/TEST usa reset destructivo y rebuild limpio; no soporta
migración in-place de credenciales ni sesiones legacy. Antes de cualquier cambio
material, bajo lock y tras el preflight, el patch exige ambas tablas auth vacías
si falta el marker exacto `AUTH_CENTRAL_EMPTY_INIT_V1: credencial_usuario y sesion_usuario vacias al inicializar.`
Ese COMMENT de `sesion_usuario` certifica inicialización central con auth vacío;
no debe escribirse manualmente y el antiguo marker de cutover no lo sustituye.
Con el marker presente, la reejecución conserva filas, versiones y timestamps.
Sin él y con cualquier fila auth, aborta atómicamente e indica usar rebuild oficial.
No convierte instantes, cierra sesiones ni rota credenciales históricas.
La protección de rebuild limpio sigue validada en el head vigente `3503ff2`.
Si aparecen datos útiles antes del corte, detener el rebuild y definir migración
específica; esta política no se extrapola a futuras bases productivas.
Después de PR04: PR05 materializa D1/contexto humano; D2 antes de actores técnicos.

Recuperación antes de usar el slice: revertir código junto con su patch aplicado
sobre una DB de desarrollo reconstruida por la cadena anterior. No restaurar
NOT NULL mientras existan sesiones centrales NULL: usar reconstrucción limpia
permitida por la premisa de datos sin utilidad, nunca instalación ficticia. Si
aparecen datos útiles, reevaluar recuperación antes de resetear. No distribuir
credenciales ni sesiones como mecanismo de rollback.
