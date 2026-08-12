# SRV-ADM-005 — Gestión de configuración y parametrización

## Objetivo
Gestionar la configuración y parametrización del sistema, permitiendo definir, modificar, invalidar y consultar parámetros operativos y funcionales, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- alta de parámetros de configuración
- modificación de parámetros
- baja lógica de parámetros
- consulta de configuraciones
- definición de parámetros globales y contextuales

No cubre:
- lógica de negocio específica
- ejecución de reglas funcionales
- gestión de usuarios o permisos
- auditoría en sí misma

## Entidades principales
- configuracion_parametro
- configuracion_contexto

## Modos del servicio

### Alta
Permite registrar un nuevo parámetro de configuración.

### Modificación
Permite actualizar un parámetro existente.

### Baja lógica
Permite invalidar un parámetro.

### Consulta
Permite visualizar parámetros configurados.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id cuando corresponda
- instalacion_id cuando corresponda
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- clave del parámetro
- valor
- tipo de dato
- alcance (global, sucursal, instalación)
- estado
- vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- clave de parámetro
- alcance
- sucursal o instalación cuando corresponda
- estado
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de parámetro
- clave y valor
- alcance aplicado
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de parámetros
- clave
- valor
- alcance
- estado
- vigencia

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos del parámetro
3. registrar configuración
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar parámetro existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar parámetro
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. resolver alcance aplicable
3. cargar configuraciones
4. devolver vista de lectura

## Validaciones clave
- coherencia de tipo de dato
- unicidad de clave por alcance
- consistencia de valores
- no duplicidad indebida
- coherencia de vigencias
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de configuracion_parametro
- vinculación con configuracion_contexto cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión administrativa

### Hacia abajo
- todos los dominios funcionales del sistema
- lógica de negocio configurable
- reportes administrativos

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-ADMINISTRATIVO]]
- [[CU-ADM]]
- [[RN-ADM]]
- [[ERR-ADM]]
- [[EVT-ADM]]
- [[EST-ADM]]
- DER administrativo

## Pendientes abiertos
- catálogo final de parámetros del sistema
- definición de tipos de datos soportados
- reglas de override por alcance
- estrategia de cacheo de configuración
- control de impacto de cambios en caliente

## Incremento #360 — Consulta read-only de catálogos maestros e ítems

### Estado implementado
- Se implementan consultas puras sobre las tablas reales `catalogo_maestro` e `item_catalogo`.
- `item_catalogo` se expone como subrecurso de `catalogo_maestro`.
- Endpoints implementados:
  - `GET /api/v1/administrativo/catalogos`.
  - `GET /api/v1/administrativo/catalogos/{id_catalogo_maestro}`.
  - `GET /api/v1/administrativo/catalogos/{id_catalogo_maestro}/items`.
- La búsqueda `q` se aplica por código o nombre.
- La paginación devuelve `items`, `total`, `page` y `page_size`.
- `estado_item_catalogo` se filtra de forma literal contra el valor persistido.
- `NULL` en `estado_item_catalogo` se preserva en la respuesta.

### Decisión CORE-EF
- Clasificación: `QUERY_READLIKE`.
- Headers write: `NO APLICA` porque no hay comando sincronizable.
- `If-Match-Version`: `NO APLICA`.
- Idempotencia write: `NO APLICA`.
- Outbox: `NO APLICA`.
- Lock lógico: `NO APLICA`.
- Versionado: `NO APLICA`.
- Transacción write / rollback de negocio: `NO APLICA`.
- Efectos persistentes: ninguno.

### Fuera de alcance vigente
- Writes de catálogos o ítems.
- Migraciones SQL y migración CORE-EF de writes.
- Jerarquías de ítems.
- Historial de catálogos.
- Defaults, orden configurable, vigencias, configuración por sucursal o instalación.
- Migración de enums existentes o redefinición de reglas estructurales de otros dominios.

### NO CONFIRMADO
- Valores válidos formales de `estado_item_catalogo`.
- Semántica funcional de `estado_item_catalogo = NULL`.
- Política futura de activación, baja o desactivación.
- Contrato futuro de jerarquías.
- Uso futuro de `historial_catalogo`.


## Incremento #363 — Estructura SQL CORE-EF de catálogos

- `catalogo_maestro` e `item_catalogo` quedan preparados para futuros comandos sincronizables con `uid_global`, versionado físico, timestamps, baja lógica, metadata de instalación y `op_id`.
- Los triggers genéricos CORE-EF aplican defaults de alta, preservan metadata original y aumentan `version_registro` ante modificaciones materiales, incluida la baja lógica.
- La lectura read-only implementada en #360 excluye explícitamente filas con `deleted_at IS NOT NULL`; no hay cambios de rutas, schemas ni contratos de respuesta.
- La unicidad de códigos se conserva para todas las filas, incluidas las bajas lógicas: no hay evidencia que autorice reutilización ni reactivación de códigos históricos.
- No se agregó `CHECK` para `estado_item_catalogo`: los valores definitivos y la semántica de `NULL` permanecen **NO CONFIRMADOS**. No se agrega estado físico a `catalogo_maestro` por falta de evidencia física vigente.
- No se crearon tablas `_legacy`, tablas espejo, lectura dual ni compatibilidad transitoria. Los datos existentes de las tablas y dependencias inmediatas son descartables y el patch los limpia de manera controlada; queda una única estructura definitiva.
- No hay endpoints write ni outbox runtime en este incremento. El CRUD futuro deberá persistir el cambio de negocio y su evento outbox en la misma transacción. Jerarquías, historial, defaults, vigencias y UI permanecen fuera de alcance.

### Decisión CORE-EF

- Endpoints / clasificación HTTP / headers / `If-Match-Version` / idempotencia HTTP / outbox runtime / lock lógico: **NO APLICA**; el incremento es únicamente SQL/infrastructural.
- Versionado físico y triggers: aplica y queda implementado en ambas tablas.
- Transacción y rollback: el patch usa una transacción; ante error revierte. La reversión posterior requiere restaurar backup previo porque la limpieza de datos es deliberada.

## Incremento #368 — CRUD write de catálogos maestros

### Estado implementado

- Se implementan exclusivamente los comandos de `catalogo_maestro`: alta, modificación y baja lógica. Los writes de `item_catalogo` permanecen pendientes.
- `POST /api/v1/administrativo/catalogos` crea el catálogo con versión inicial `1`, metadata CORE-EF y evento `catalogo_maestro_creado`.
- `PUT /api/v1/administrativo/catalogos/{id_catalogo_maestro}` actualiza código, nombre y descripción mediante `version_registro` esperado y emite `catalogo_maestro_modificado`.
- `PATCH /api/v1/administrativo/catalogos/{id_catalogo_maestro}/baja` persiste `deleted_at`, incrementa la versión y emite `catalogo_maestro_desactivado`.
- La baja repetida devuelve el recurso solo para el replay real del mismo `X-Op-Id`; con otro identificador la fila ya no es operable y responde `404`.

### Decisión CORE-EF

Los tres endpoints se clasifican como `COMMAND_WRITE_NEGOCIO`. Exigen el helper común con `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id` y `X-Instalacion-Id`; update y baja también exigen `If-Match-Version`.

- **Idempotencia:** alta consulta `op_id_alta` y compara el payload completo. Update y baja usan `op_id_ultima_modificacion`; un replay consistente no vuelve a mutar ni a emitir outbox. Un `X-Op-Id` asociado a payload incompatible devuelve `IDEMPOTENT_DUPLICATE`.
- **Versionado:** la base aplica `version_registro = 1` en alta; los cambios condicionales por id y versión delegan el incremento único al trigger CORE-EF.
- **Outbox y transacción:** repository persiste cambio y `outbox_event` antes de un único `commit`; cualquier error, incluido el de outbox o constraint, ejecuta rollback de toda la unidad.
- **Lock lógico:** `NO APLICA`; no existe lock lógico administrativo para esta entidad. El control de incompatibilidad es optimistic locking.
- **Soft delete:** los read models existentes excluyen `deleted_at IS NOT NULL`; la fila y su código único se conservan. No se implementa reactivación ni reutilización de código.

### NO CONFIRMADO / fuera de alcance

Permanecen **NO CONFIRMADOS** la política futura de reactivación, reutilización de códigos, estado persistido de catálogo, jerarquías e historial funcional. No se implementan writes, activación/desactivación, defaults, vigencias ni configuración contextual de ítems.

## Incremento #393 — Estado y ciclo de vida de `item_catalogo`

`item_catalogo` es núcleo de configuración administrativa; el consumo posterior no traslada a Administrativo las reglas de aceptación de cada dominio. Se congelan los estados físicos `ACTIVO` (inicial) e `INACTIVO`, ambos con `deleted_at IS NULL`. La inactivación conserva fila y código, permite la transición futura `INACTIVO -> ACTIVO` y no equivale a baja lógica. La baja lógica usa sólo `deleted_at IS NOT NULL`, excluye la fila de las consultas normales y no se reactiva en este incremento. La constraint de código sigue aplicando a todas las filas, incluidas bajas, por lo que no hay reutilización.

La estrategia de datos es normalizar `NULL` histórico a `ACTIVO`, cerrar la columna con `DEFAULT`, `NOT NULL` y `CHECK`, y eliminar valores incompatibles porque los datos son descartables. Las consultas read-only continúan listando activos e inactivos sin filtro, filtran literalmente cuando se solicita un estado y excluyen siempre bajas lógicas. No se implementan comandos ni endpoints de ítems; por ello headers, idempotencia HTTP, outbox runtime y lock lógico son **NO APLICA**, mientras el versionado/triggers físicos existentes se preservan.

## Incremento #399 — comandos de `item_catalogo`

Los comandos de alta, modificación, cambio de estado y baja lógica de ítems se implementan como `COMMAND_WRITE_NEGOCIO` con metadata CORE-EF, optimistic locking en mutaciones y outbox transaccional. `ACTIVO` e `INACTIVO` son estados físicos; la baja es exclusivamente `deleted_at` y no admite reactivación. La unicidad SQL `(id_catalogo_maestro, codigo_item_catalogo)` conserva el código ocupado después de la baja. No se implementan jerarquías ni historial funcional.

### Corrección PR #400

El intento con un nuevo `X-Op-Id` de persistir el mismo estado físico es una transición inválida (`INVALID_STATE_TRANSITION`), no un conflicto de idempotencia. La baja repetida sólo hace replay con el mismo identificador de la baja previa; con otro identificador se trata como recurso no operable (`NOT_FOUND`). Los errores técnicos se devuelven sin detalle interno; la transacción conserva rollback conjunto de negocio y outbox.

## Incremento #407 — Inventario de definiciones de parámetros

Se implementa una consulta administrativa read-only del inventario existente. La
fuente física se limita a `parametro_sistema`, unida con
`tipo_dato_parametro` y `alcance_parametro`. El repository no ejecuta writes,
commits, resolución de valores ni lógica de negocio; devuelve una lista vacía
cuando no existen definiciones y ordena por `codigo_parametro`, con el ID como
desempate determinista.

La consulta es `QUERY_READLIKE`: no usa headers CORE-EF write y no aplican
idempotencia, outbox, lock lógico, optimistic locking, versionado ni rollback de
negocio. El primer incremento entrega el listado completo, sin paginación,
búsqueda o filtros.

No constituye configuración funcional completa. Permanecen fuera de alcance
`valor_parametro`, valores efectivos, defaults, overrides, vigencias, secretos,
resolución global/sucursal/instalación, writes, `configuracion_general` y
configuración local operativa. La definición de valores y su fuente de verdad
corresponde al incremento posterior #408.

## Incremento #408 — Freeze canónico de configuración

Este incremento es sólo documental y no agrega endpoints. Sustituye los nombres conceptuales no materializados de las secciones iniciales por el siguiente mapa al SQL real: `parametro_sistema` es la definición canónica; `valor_parametro` es la fuente canónica de valores; `tipo_dato_parametro` y `alcance_parametro` soportan la definición; `parametro_opcion` sólo declara opciones válidas; e `historial_parametro` es soporte de trazabilidad físicamente incompleto.

`valor_parametro` posee físicamente `id_sucursal` e `id_instalacion` opcionales, pero esa evidencia no cierra la semántica contextual. Para futuros parámetros quedan **NO CONFIRMADOS** el catálogo de alcances, el significado exacto de `alcance_parametro`, overrides, precedencia, obligatoriedad de una base global y reglas de contexto/fallback. Los consumidores de otros dominios deberán usar un query service administrativo interno, aún pendiente, y no SQL directo. `configuracion_general` es compatibilidad heredada sin nuevas claves ni consumidores. `configuracion_local` pertenece a Operativo. Los parámetros no son catálogos.

Las claves contractuales se crearán por migraciones versionadas, no por alta/baja dinámica en el primer runtime. Desde #438/#441, exposición administrativa, sensibilidad y editabilidad son metadata física explícita en `parametro_sistema` mediante `exponible_api_administrativa`, `es_sensible` y `editable_administrativamente`, con política restrictiva por defecto y sin inferencias por código, tipo, nombre, exposición, sensibilidad o valor. La editabilidad nace `false`, es independiente de exposición/sensibilidad, no es editable por API y sólo debe habilitarse por migración versionada; la autorización real, el cifrado o secret manager y cualquier modelo adicional de visibilidad siguen **NO CONFIRMADOS**. No se expondrán secretos en claro por API, historial, outbox ni logs. También están pendientes la prohibición física de vigencias solapadas, la idempotencia HTTP, el outbox runtime y el historial alineado al valor/contexto.

Para #425 se usarán sólo definición `parametro_sistema` y valor GLOBAL vigente en `valor_parametro`, con `id_sucursal IS NULL` e `id_instalacion IS NULL`, sin `configuracion_general`, `configuracion_local` ni catálogos. Continúan pendientes patch SQL funcional específico, seeds de dos claves, constraints 1–31, read, write, versionado runtime, idempotencia HTTP, outbox, historial, rollback, query service y tests PostgreSQL.

Son **NO CONFIRMADOS** los códigos/nombres exactos, defaults, cifrado o secret manager, autorización, caché, inclusividad de `fecha_hasta`, reactivación y reutilización de claves y taxonomía final de eventos.

### Decisión CORE-EF

**NO APLICA** para endpoints: #408 no crea ni modifica rutas. No se afirma cumplimiento runtime ni se ejecuta reset PostgreSQL.

## Incremento #409 — Vocabulario estructural mínimo

Se persisten por patch transaccional e idempotente únicamente el tipo `ENTERO`
(`Entero`, “Valor numérico entero sin componente decimal.”) y el alcance
`GLOBAL` (`Global`, “Aplicable sin contexto de sucursal o instalación.”). Ambos
son soporte de la definición administrativa, se consumen por código y no son
editables mediante API. Datos incompatibles, variantes case-insensitive y los
sinónimos `NUMERO`, `GENERAL` o `LOCAL` causan error y rollback.

No se siembran definiciones ni valores funcionales: #409 habilita físicamente el
tipo y alcance que podrá consumir #425, pero no completa ni implementa #425.
Endpoints y CORE-EF HTTP son **NO APLICA**; sí aplican transacción, rollback,
idempotencia SQL y resets reproducibles DEV/TEST.

## Incremento #410 — Preparación SQL CORE-EF de valores

El patch `patch_valor_parametro_core_ef_20260803.sql` migra conservadoramente `valor_parametro`: completa sólo UID, versión 1 y timestamps cuando faltan; mantiene nullable la procedencia y los op IDs heredados; y aborta toda la transacción ante datos o estructura incompatibles. El trigger de actualización incrementa una sola versión por cada `UPDATE` físico, incluido soft delete; los futuros commands deberán evitar updates sin cambio material y replays que vuelvan a mutar.

La garantía contextual consulta `alcance_parametro.codigo_alcance = 'GLOBAL'` y exige contexto nulo sólo para esas definiciones. La unicidad parcial limita a uno los valores globales vigentes no eliminados por definición. La fecha final debe ser posterior a la inicial cuando ambas existen. Esto no implementa resolución por fecha, no solapamiento, overrides, precedencia ni fallback.

### Decisión CORE-EF

- Naturaleza: preparación SQL estructural; endpoints, command HTTP, headers, `If-Match-Version`, idempotencia HTTP, outbox runtime y lock lógico: **NO APLICA**.
- Idempotencia SQL, versionado físico, transacción y rollback: obligatorios y cubiertos por el patch/tests PostgreSQL.
- #411 (read), #412 (write), #425 (claves, valores y runtime), outbox e historial permanecen no implementados.

## Incremento #438 — Metadata de exposición segura

El patch `patch_parametro_sistema_exposicion_segura_20260804.sql` agrega a `parametro_sistema` las columnas `exponible_api_administrativa boolean NOT NULL DEFAULT false` y `es_sensible boolean NOT NULL DEFAULT true`. Exposición y sensibilidad son conceptos separados: una definición sólo será candidata a exposición por una futura API si fue marcada explícitamente como exponible y, además, no es sensible.

La política default-deny queda persistida: las definiciones heredadas no se habilitan automáticamente, quedan sensibles por defecto y no se clasifican por código, tipo, alcance, nombre, descripción ni valor. La constraint `chk_parametro_sistema_exposicion_no_sensible` prohíbe marcar en simultáneo una definición como exponible y sensible. La metadata no es editable por API, no se expone en el inventario #407 y sólo debe cambiar mediante migraciones versionadas.

#438 no implementa autenticación, autorización, endpoint de #411, commands, outbox, historial runtime, CRUD genérico ni logging de reads de valores. Los headers CORE-EF de write no representan autorización. El futuro read administrativo de #411 deberá estar sujeto a una dependencia de autorización real cuando exista y sólo podrá devolver valores si `exponible_api_administrativa = true AND es_sensible = false`; ante definición inexistente o no exponible se recomienda `404 Not Found` para evitar filtración por enumeración. Los futuros logs de lectura de valores no deben registrar valores, secretos, op IDs, credenciales, payload SQL ni contenido sensible.

#441 materializa la editabilidad administrativa default-deny, pero #412 mantiene pendientes writes, autorización, idempotencia/replay, outbox e historial. #425 mantiene pendientes claves, valores y rangos funcionales, que deberán declarar explícitamente su editabilidad en su propia migración. #435 mantiene pendientes overrides, precedencia, fallback y resolución contextual.

## Incremento #441 — Metadata de editabilidad administrativa

El patch `patch_parametro_sistema_editabilidad_administrativa_20260805.sql` agrega `editable_administrativamente boolean NOT NULL DEFAULT false` a `parametro_sistema`. La columna no crea definiciones ni valores funcionales y no modifica `valor_parametro`.

Editabilidad, exposición y sensibilidad quedan separadas: no existe constraint física `editable => exponible` ni `editable => no sensible`. La reejecución del patch sólo acepta la estructura compatible exacta y aborta ante tipo incompatible, columna nullable, default distinto o ausente, o filas nulas; no sanea silenciosamente ni habilita definiciones por código, tipo, alcance, nombre, descripción, exposición, sensibilidad o existencia de valor.

No existe endpoint write para modificar esta metadata. El contrato final de #412
ya congela autorización, `If-Match-Version`, idempotencia/replay, CAS y outbox, pero
su implementación continúa pendiente; historial especializado queda fuera de su
alcance. #425 y #435 siguen pendientes.

## Incremento #411 — Consulta de valor administrativo GLOBAL marcado vigente

El query service administrativo `ObtenerParametroGlobalQueryService` implementa sólo la lectura individual `GET /api/v1/administrativo/configuracion/parametros/{codigo_parametro}/valor-global`. El código se resuelve por igualdad exacta y case-sensitive contra `parametro_sistema.codigo_parametro`, sin `UPPER`, `LOWER`, `ILIKE`, trimming, aliases, allowlists ni IDs hardcodeados.

La política de exposición se evalúa antes del alcance: inexistente, no exponible y sensible se ocultan con el mismo `404 parametro_no_encontrado`. Si la definición existe, es exponible y no sensible, pero `alcance_parametro.codigo_alcance` no es `GLOBAL`, se responde `409 conflicto_parametro`. No se revelan `exponible_api_administrativa`, `es_sensible` ni clasificación interna.

El valor consultado es exclusivamente el marcado vigente global no eliminado (`es_valor_vigente = true`, `deleted_at IS NULL`, `id_sucursal IS NULL`, `id_instalacion IS NULL`). No es valor efectivo ni configuración resuelta: no se evalúan reloj, `fecha_desde`, `fecha_hasta`, precedencia, fallback ni contexto. Sin valor válido se devuelve `SIN_VALOR` y `valor_marcado_vigente = null`. Con valor se devuelve `CON_VALOR_MARCADO_VIGENTE`, `valor_raw`, `valor_tipado`, `uid_global`, `version_registro` y timestamps del valor. En #411 sólo `ENTERO` está soportado y se convierte de forma estricta como decimal ASCII con signo negativo opcional (`-?[0-9]+`); se rechazan `+`, espacios, decimales, notación científica y dígitos Unicode. Los tipos no soportados producen `500 inconsistencia_parametro` aun sin valor; `SIN_VALOR` sólo aplica a definiciones `ENTERO` válidas. No se aplican rangos funcionales de #425.

CORE-EF: clasificación `QUERY_READLIKE`; headers write, `If-Match-Version`, idempotencia HTTP, outbox, historial, lock lógico, optimistic locking, commits y mutaciones son `NO APLICA`. La ruta puede enviar `Cache-Control: no-store` de forma localizada. Autorización completa, writes #412, claves/calendario #425 y contexto/overrides #435 siguen pendientes.

## Incremento #412 — contrato de servicio congelado (implementación pendiente)

#469 y #470 están completados; #412 es su primer consumidor productivo. El flujo
lógico congelado es autenticación, autorización, parsing de headers CORE-EF,
validación referencial/coherencia sucursal-instalación, existencia/elegibilidad
estable, existencia del target update-only,
`canonical_payload_hash`, `claim_operation`, `REPLAY | CONFLICT | EXECUTE`, CAS,
outbox, `complete_operation` y commit exterior. La validación estructural del body
puede intercalarse con dependencies según FastAPI.

El helper CORE-EF autenticado reusable comparte la `Session` del request. Exige UUID
válido para `X-Op-Id`, enteros positivos para `X-Sucursal-Id` y
`X-Instalacion-Id`, y entero `>= 1` para `If-Match-Version`; después verifica la
existencia de ambas referencias y que la instalación pertenezca a la sucursal. Sólo
entonces entrega el contexto técnico al command. Todo contexto inválido falla antes
de canonicalización/claim y de cualquier write; las FKs del ledger son defensa
física final, no el mecanismo normal de validación pública.

Esta coherencia no compara los headers con sucursal o instalación del principal y
no congela autorización contextual, overrides ni #435. El router futuro no repite
consultas o parsing manual.

`OperationCompletion.id_usuario` procede de `AuthenticatedPrincipal.id_usuario`;
`X-Usuario-Id` se ignora. Claim, CAS, outbox y
complete comparten una sola `Session` y transacción exterior. El runtime #470 y el
repository funcional no hacen commit/rollback ni commits parciales. Cualquier fallo
revierte conjuntamente CAS, evento y receipt; sólo después del commit se emite el
éxito.

Outbox **APLICA** porque `valor_parametro` es sincronizable por la política CORE-EF
y EVT-ADM-060 ya tipifica su modificación. Se inserta en la misma transacción:
`event_type = valor_parametro_modificado`, `aggregate_type = valor_parametro` y
`aggregate_id = valor_parametro.id_valor_parametro`. El payload allowlisted exacto
es `uid_global`, `codigo_parametro`, `valor_anterior`, `valor_nuevo`,
`version_anterior`, `version_registro` y `op_id`. Los IDs numéricos locales de
usuario, sucursal e instalación no forman parte del payload distribuido ni se
inventan identidades globales inexistentes. Actor y contexto continúan disponibles
como provenance local en `operacion_idempotente`, metadata técnica del command y,
si el modelo ofrece columnas propias, en el registro local de outbox. La policy
default-deny y el guard de
datos sensibles se mantienen; una definición sensible nunca es elegible. No se
crean consumers remotos ni reconciliación en #412.

El lock lógico persistido **NO APLICA**: la exclusión del receipt usa el advisory
transaccional de #470 por `op_id`, mientras la concurrencia del valor se resuelve por
CAS de `version_registro`. No se agrega un advisory propio del command.

La implementación deberá agregar un patch/seed versionado, transaccional e
idempotente con: permiso `ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR` (nombre
`Modificar valor global de parámetro`, descripción `Permite modificar un valor
GLOBAL administrativo existente y elegible.`, estado `ACTIVO`); y la definición técnica controlada
`PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO`, `ENTERO`, `GLOBAL`, exponible, no sensible y
editable, con exactamente un valor GLOBAL vigente existente. #412 no inventa ni
presupone un `codigo_rol`: la asignación debe resolver un receptor administrativo
canónico realmente sembrado y contractual. Si el reset aún no ofrece uno apropiado,
el incremento/seed administrativo dueño del rol debe resolver esa dependencia antes
de asignar el permiso; el patch #412 no crea silenciosamente un rol ad hoc. Tampoco
se apropia de defaults funcionales de #425.

`historial_parametro` especializado y #265 quedan fuera de alcance. También quedan
fuera CRUD genérico, UPSERT, creación, #425, #435, migración de #400, UI, consumers
remotos, reconciliación, migración masiva heredada y cleanup global de
`X-Usuario-Id`. #412 es el primer write administrativo autenticado sin ese header y
un incremento de #461; cerrarlo no cerrará #461 ni #402.
