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
