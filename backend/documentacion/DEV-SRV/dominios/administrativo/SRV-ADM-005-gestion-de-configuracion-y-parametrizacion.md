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

Las claves contractuales se crearán por migraciones versionadas, no por alta/baja dinámica en el primer runtime. Editabilidad, visibilidad y sensibilidad requieren metadata explícita aún no existente. No se expondrán secretos en claro por API, historial, outbox ni logs. También están pendientes la prohibición física de vigencias solapadas y toda la deuda CORE-EF de `valor_parametro`: UID, versión, timestamps, soft delete, metadata de instalación, op IDs, idempotencia, outbox e historial.

Para #425 se usarán sólo definición `parametro_sistema` y valor GLOBAL vigente en `valor_parametro`, con `id_sucursal IS NULL` e `id_instalacion IS NULL`, sin `configuracion_general`, `configuracion_local` ni catálogos. Continúan pendientes patch SQL CORE-EF, seeds de dos claves, constraints 1–31, read, write, versionado, idempotencia, outbox, historial, rollback, query service y tests PostgreSQL.

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
