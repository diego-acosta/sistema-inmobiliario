# DEV-API-INM-001 - Dominio Inmobiliario

## Estado del documento

- version: `1.0`
- estado: `vigente`
- fuente: `backend implementado + documentacion consolidada`
- ultima actualizacion: `2026-04-21`

## Resumen

Este documento define el contrato API vigente del dominio `inmobiliario`, alineado con la implementacion real del backend y consolidado contra SQL, tests y documentacion vigente del proyecto. Su objetivo es evitar ambiguedad entre lo que existe efectivamente en codigo y lo que permanece como referencia historica o capacidad aun no implementada.

El contenido se clasifica en tres niveles contractuales: `vigente` para endpoints realmente implementados, `heredado` para contratos o naming historicos que hoy no coinciden con el backend real, y `pendiente` para capacidades del dominio que aun no existen como API usable.

## 1. Alcance

Este documento define la version Markdown, auditable y versionable del contrato de API del dominio `inmobiliario`, tomando como base el PDF `DEV-API-001 - Dominio Inmobiliario v1.2`, la documentacion `DEV-SRV`, `SYS-MAP-002`, `RN-INM`, `ERR-INM`, el SQL vigente y la implementacion backend actualmente existente.

El objetivo de esta version es separar con claridad:

- contrato vigente: endpoints realmente implementados en backend
- contrato heredado: endpoints o contratos del PDF que no coinciden con la implementacion real
- pendiente: capacidades del dominio que existen como necesidad documental o estructural, pero no tienen circuito backend vigente

Este documento no debe leerse como diseño libre ni como roadmap abierto. El contrato vigente queda definido por router, schema, service, repository, SQL y tests actualmente existentes.

## 2. Fuente de verdad

El contrato vigente de este documento se basa, en orden de prioridad, en:

- backend realmente implementado en `routers`, `schemas`, `services` y `repositories`
- tests vigentes del dominio
- SQL vigente del dominio inmobiliario
- documentacion `DEV-SRV`, `SYS-MAP-002`, `RN-INM` y `ERR-INM`
- PDF `DEV-API-001 - Dominio Inmobiliario v1.2` solo como fuente historica complementaria

Criterio operativo:

- si un endpoint existe en el PDF pero no existe en backend, no forma parte del contrato vigente
- si una seccion existe en `DEV-SRV` pero difiere del router actual, prevalece el router actual
- frontend debe consumir solo el bloque de contrato vigente

## 3. Criterios de diseno

- `inmobiliario` es el dominio dueno del activo inmobiliario y de su estructura operativa base.
- `inmueble` es la raiz operativa vigente del dominio.
- `desarrollo` es opcional para `inmueble`.
- `unidad_funcional` depende siempre de `inmueble`.
- `edificacion` existe hoy como entidad propia y exige padre exclusivo: `id_inmueble` XOR `id_unidad_funcional`.
- `servicio` se documenta como contrato vigente porque existe en SQL, backend y tests, pero su semantica debe leerse como soporte transversal del activo y no como reemplazo de infraestructura fisica.
- `instalacion` no pertenece al nucleo del dominio inmobiliario; su ownership sigue siendo `operativo`.
- el contrato prioriza implementacion real por encima del PDF historico
- los endpoints no implementados no deben aparecer mezclados dentro de bloques vigentes
- cuando el PDF propone naming, payloads o endpoints no implementados, se conservan solo como heredado o pendiente

## 4. Decisiones relevantes del dominio

- `inmueble` es la raiz operativa vigente del dominio.
- `desarrollo` es opcional para `inmueble`.
- `unidad_funcional` depende siempre de `inmueble`.
- `edificacion` exige padre exclusivo entre `id_inmueble` e `id_unidad_funcional`.
- `servicio` usa naming tecnico unico en backend y se expone como `servicios`.
- las asociaciones vigentes son `inmueble_servicio` y `unidad_funcional_servicio`.
- `disponibilidad` tiene contrato API vigente y usa `id_inmueble` o `id_unidad_funcional` como parent exclusivo.
- no se permite editar disponibilidades ya cerradas.
- no se permite usar `PUT` para cerrar una disponibilidad abierta.
- el cierre historico se hace exclusivamente con `PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar`.
- la baja logica de disponibilidad se hace con `deleted_at`.
- `ocupacion` tiene contrato API vigente y usa `id_inmueble` o `id_unidad_funcional` como parent exclusivo.
- no se permite editar ocupaciones ya cerradas.
- no se permite usar `PUT` para cerrar una ocupacion abierta.
- el cierre historico de ocupacion se hace exclusivamente con `PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar`.
- la baja logica de ocupacion se hace con `deleted_at`.
- no existe hoy una API consolidada bajo `/api/v1/inmobiliario/...` para reportes o consultas globales.
- `instalacion` no es entidad del dominio inmobiliario; su ownership sigue siendo `operativo`.
- `infraestructura`, `inmueble_mejora` y `relacion_inmobiliaria` no forman parte del contrato vigente actual.

## 5. Convencion de errores

El backend vigente expone respuestas con el formato general:

```json
{
  "ok": false,
  "error_code": "CODIGO",
  "error_message": "Mensaje",
  "details": {
    "errors": []
  }
}
```

Las respuestas exitosas usan el formato:

```json
{
  "ok": true,
  "data": {}
}
```

Convenciones publicas observables en implementacion y tests:

- `NOT_FOUND` para entidades inexistentes o dadas de baja logica
- `APPLICATION_ERROR` para validaciones funcionales y rechazos de negocio
- `CONCURRENCY_ERROR` para versionado mediante `If-Match-Version`
- `INTERNAL_ERROR` para errores no controlados en router

Marcadores internos observables en `details.errors`:

- `NOT_FOUND_DESARROLLO`
- `NOT_FOUND_INMUEBLE`
- `NOT_FOUND_UNIDAD_FUNCIONAL`
- `NOT_FOUND_EDIFICACION`
- `NOT_FOUND_SERVICIO`
- `DUPLICATE_INMUEBLE_SERVICIO`
- `DUPLICATE_UNIDAD_FUNCIONAL_SERVICIO`
- `EXACTLY_ONE_PARENT_REQUIRED`
- `INVALID_REQUIRED_FIELDS`

Headers transversales observables en operaciones write:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`
- `If-Match-Version` en update, baja y operaciones asociativas versionadas

Observacion:

- El PDF historico tambien menciona `VALIDATION_ERROR`, `IDEMPOTENT_DUPLICATE`, `SYNC_CONFLICT`, `LOCK_ACTIVE` y `TECHNICAL_INCONSISTENCY`, pero esos codigos no constituyen hoy el contrato publico principal observado en routers y tests del dominio.

## 6. Contrato vigente

Este bloque contiene solo endpoints realmente implementados en backend.

### 6.1 Desarrollos

#### `POST /api/v1/desarrollos`
- estado: vigente
- objetivo: alta de desarrollo
- payload vigente: `codigo_desarrollo`, `nombre_desarrollo`, `descripcion`, `estado_desarrollo`, `observaciones`

#### `GET /api/v1/desarrollos/{id_desarrollo}`
- estado: vigente
- objetivo: consulta de detalle de desarrollo

#### `GET /api/v1/desarrollos`
- estado: vigente
- objetivo: listado de desarrollos

#### `PUT /api/v1/desarrollos/{id_desarrollo}`
- estado: vigente
- objetivo: modificacion de desarrollo

#### `PATCH /api/v1/desarrollos/{id_desarrollo}/baja`
- estado: vigente
- objetivo: baja logica de desarrollo

Observaciones de implementacion real:

- la respuesta de alta incluye `id_desarrollo`, `uid_global`, `version_registro` y `estado_desarrollo`
- update y baja requieren `If-Match-Version`

### 6.2 Inmuebles

#### `POST /api/v1/inmuebles`
- estado: vigente
- objetivo: alta de inmueble
- payload vigente: `id_desarrollo`, `codigo_inmueble`, `nombre_inmueble`, `superficie`, `estado_administrativo`, `estado_juridico`, `observaciones`
- observacion: `id_desarrollo` es opcional

#### `GET /api/v1/inmuebles/{id_inmueble}`
- estado: vigente
- objetivo: consulta de detalle de inmueble

#### `GET /api/v1/inmuebles`
- estado: vigente
- objetivo: listado de inmuebles

#### `PUT /api/v1/inmuebles/{id_inmueble}`
- estado: vigente
- objetivo: modificacion de inmueble

#### `PATCH /api/v1/inmuebles/{id_inmueble}/baja`
- estado: vigente
- objetivo: baja logica de inmueble

#### `PATCH /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`
- estado: vigente
- objetivo: asociar inmueble a desarrollo
- payload vigente: `id_desarrollo`

#### `PATCH /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`
- estado: vigente
- objetivo: desasociar inmueble de desarrollo

Observaciones de implementacion real:

- el SQL vigente confirma `id_desarrollo` nullable y `codigo_inmueble` unico
- asociacion, desasociacion, update y baja usan `If-Match-Version`

### 6.3 Unidades funcionales

#### `POST /api/v1/inmuebles/{id_inmueble}/unidades-funcionales`
- estado: vigente
- objetivo: alta de unidad funcional
- payload vigente: `codigo_unidad`, `nombre_unidad`, `superficie`, `estado_administrativo`, `estado_operativo`, `observaciones`

#### `GET /api/v1/inmuebles/{id_inmueble}/unidades-funcionales`
- estado: vigente
- objetivo: listado de unidades funcionales por inmueble

#### `GET /api/v1/unidades-funcionales`
- estado: vigente
- objetivo: listado global de unidades funcionales

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}`
- estado: vigente
- objetivo: consulta de detalle de unidad funcional

#### `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}`
- estado: vigente
- objetivo: modificacion de unidad funcional

#### `PATCH /api/v1/unidades-funcionales/{id_unidad_funcional}/baja`
- estado: vigente
- objetivo: baja logica de unidad funcional

Observaciones de implementacion real:

- la unidad funcional no existe sin `id_inmueble`
- la implementacion real usa `codigo_unidad`, `nombre_unidad`, `estado_administrativo` y `estado_operativo`

### 6.4 Edificaciones

#### `POST /api/v1/edificaciones`
- estado: vigente
- objetivo: alta de edificacion
- payload vigente: `id_inmueble`, `id_unidad_funcional`, `descripcion`, `tipo_edificacion`, `superficie`, `observaciones`

#### `GET /api/v1/edificaciones/{id_edificacion}`
- estado: vigente
- objetivo: consulta de detalle de edificacion

#### `GET /api/v1/edificaciones`
- estado: vigente
- objetivo: listado global de edificaciones

#### `GET /api/v1/inmuebles/{id_inmueble}/edificaciones`
- estado: vigente
- objetivo: listado de edificaciones por inmueble

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones`
- estado: vigente
- objetivo: listado de edificaciones por unidad funcional

#### `PUT /api/v1/edificaciones/{id_edificacion}`
- estado: vigente
- objetivo: modificacion de edificacion

#### `PATCH /api/v1/edificaciones/{id_edificacion}/baja`
- estado: vigente
- objetivo: baja logica de edificacion

Regla vigente de contrato:

- debe informarse exactamente uno entre `id_inmueble` e `id_unidad_funcional`

### 6.5 Servicios

#### `POST /api/v1/servicios`
- estado: vigente
- objetivo: alta de servicio
- payload vigente: `codigo_servicio`, `nombre_servicio`, `descripcion`, `estado_servicio`

#### `GET /api/v1/servicios/{id_servicio}`
- estado: vigente
- objetivo: consulta de detalle de servicio

#### `GET /api/v1/servicios`
- estado: vigente
- objetivo: listado de servicios

#### `PUT /api/v1/servicios/{id_servicio}`
- estado: vigente
- objetivo: modificacion de servicio

#### `PATCH /api/v1/servicios/{id_servicio}/baja`
- estado: vigente
- objetivo: baja logica de servicio

Observacion de naming:

- el naming vigente del backend fue verificado contra `servicios_router.py` y se expone como `servicios`

### 6.6 Asociaciones servicio <-> inmueble

#### `POST /api/v1/inmuebles/{id_inmueble}/servicios`
- estado: vigente
- objetivo: asociar servicio a inmueble
- payload vigente: `id_servicio`, `estado`

#### `GET /api/v1/inmuebles/{id_inmueble}/servicios`
- estado: vigente
- objetivo: listar servicios asociados a inmueble

#### `GET /api/v1/servicios/{id_servicio}/inmuebles`
- estado: vigente
- objetivo: listar inmuebles asociados a servicio

Observaciones de implementacion real:

- no existe hoy update de `inmueble_servicio`
- no existe hoy baja de `inmueble_servicio`
- los tests vigentes confirman rechazo por duplicado activo con `APPLICATION_ERROR`
- el naming vigente fue verificado contra `inmuebles_router.py` y `servicios_router.py`

### 6.7 Asociaciones servicio <-> unidad funcional

#### `POST /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
- estado: vigente
- objetivo: asociar servicio a unidad funcional
- payload vigente: `id_servicio`, `estado`

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
- estado: vigente
- objetivo: listar servicios asociados a unidad funcional

#### `GET /api/v1/servicios/{id_servicio}/unidades-funcionales`
- estado: vigente
- objetivo: listar unidades funcionales asociadas a servicio

Observaciones de implementacion real:

- no existe hoy update de `unidad_funcional_servicio`
- no existe hoy baja de `unidad_funcional_servicio`
- los tests vigentes confirman rechazo por duplicado activo con `APPLICATION_ERROR`
- el naming vigente fue verificado contra `inmuebles_router.py` y `servicios_router.py`

### 6.8 Disponibilidad

#### `POST /api/v1/disponibilidades`
- estado: vigente
- objetivo: alta de disponibilidad
- payload vigente: `id_inmueble`, `id_unidad_funcional`, `estado_disponibilidad`, `fecha_desde`, `fecha_hasta`, `motivo`, `observaciones`

#### `GET /api/v1/inmuebles/{id_inmueble}/disponibilidades`
- estado: vigente
- objetivo: listar disponibilidades por inmueble

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades`
- estado: vigente
- objetivo: listar disponibilidades por unidad funcional

#### `PUT /api/v1/disponibilidades/{id_disponibilidad}`
- estado: vigente
- objetivo: modificacion completa de disponibilidad vigente

#### `PATCH /api/v1/disponibilidades/{id_disponibilidad}/baja`
- estado: vigente
- objetivo: baja logica de disponibilidad

#### `PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar`
- estado: vigente
- objetivo: cierre historico de disponibilidad

#### `POST /api/v1/disponibilidades/reemplazar-vigente`
- estado: vigente
- objetivo: reemplazo transaccional de la disponibilidad vigente de una entidad
- payload vigente: `id_inmueble`, `id_unidad_funcional`, `estado_disponibilidad`, `fecha_desde`, `motivo`, `observaciones`

Descripcion:

- operacion compuesta que reemplaza la disponibilidad vigente de una entidad
- implica cierre de la disponibilidad actualmente abierta
- implica creacion de una nueva disponibilidad

Semantica:

- operacion transaccional y atomica
- si falla cualquier paso, no se aplican cambios
- no deja estados intermedios inconsistentes
- la atomicidad de la operacion esta garantizada por la capa de persistencia mediante una unica transaccion

Reglas:

- debe existir exactamente una disponibilidad vigente previa
- la entidad se define por XOR entre `id_inmueble` e `id_unidad_funcional`
- no se permite ejecutar si no hay disponibilidad vigente
- no se permite ejecutar si hay mas de una disponibilidad vigente
- la nueva disponibilidad debe respetar las reglas temporales vigentes
- no se permiten solapamientos, segun DB

Comportamiento:

- cierra la disponibilidad vigente mediante `fecha_hasta`
- crea una nueva disponibilidad con `fecha_hasta = null`
- mantiene la coherencia temporal del historial
- devuelve la nueva disponibilidad creada

Observaciones de implementacion real:

- debe informarse exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- `fecha_hasta` debe ser `null` o mayor/igual a `fecha_desde`
- no puede existir mas de una disponibilidad abierta simultanea para la misma entidad, segun reglas vigentes de DB
- no se permite editar disponibilidades ya cerradas
- no se permite usar `PUT` para cerrar una disponibilidad abierta
- el cierre historico se hace exclusivamente con `PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar`
- la baja logica se resuelve con `deleted_at`
- update, cierre y baja requieren `If-Match-Version`
- las lecturas excluyen registros con `deleted_at`
- `POST /api/v1/disponibilidades/reemplazar-vigente` no usa `If-Match-Version`; la coherencia se resuelve a nivel transaccional
- `POST /api/v1/disponibilidades/reemplazar-vigente` exige exactamente una disponibilidad vigente previa
- `POST /api/v1/disponibilidades/reemplazar-vigente` cierra el registro abierto y crea uno nuevo dentro de la misma transaccion

Semantica historica del registro:

- la disponibilidad es un registro historico
- disponibilidad = estado potencial de uso
- no debe reinterpretarse como estado editable actual
- el cierre se realiza exclusivamente mediante `PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar`
- `PUT` no puede utilizarse para cerrar ni para modificar registros cerrados
- `POST /api/v1/disponibilidades/reemplazar-vigente` no reescribe el registro anterior: lo cierra y crea uno nuevo

Invariantes del dominio:

- exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- `fecha_hasta >= fecha_desde`
- no puede existir mas de una disponibilidad abierta simultanea para la misma entidad, segun reglas de DB

Limites temporales vigentes:

- las reglas actuales de base de datos consideran como solapamiento los registros que comparten el mismo limite temporal
- por lo tanto, la nueva `fecha_desde` debe ser estrictamente mayor al cierre efectivo de la anterior
- no se permiten limites coincidentes

### 6.9 Ocupacion

#### `POST /api/v1/ocupaciones`
- estado: vigente
- objetivo: alta de ocupacion
- payload vigente: `id_inmueble`, `id_unidad_funcional`, `tipo_ocupacion`, `fecha_desde`, `fecha_hasta`, `descripcion`, `observaciones`

#### `GET /api/v1/inmuebles/{id_inmueble}/ocupaciones`
- estado: vigente
- objetivo: listar ocupaciones por inmueble

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/ocupaciones`
- estado: vigente
- objetivo: listar ocupaciones por unidad funcional

#### `PUT /api/v1/ocupaciones/{id_ocupacion}`
- estado: vigente
- objetivo: modificacion completa de ocupacion vigente

#### `PATCH /api/v1/ocupaciones/{id_ocupacion}/baja`
- estado: vigente
- objetivo: baja logica de ocupacion

#### `PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar`
- estado: vigente
- objetivo: cierre historico de ocupacion

#### `POST /api/v1/ocupaciones/reemplazar-vigente`
- estado: vigente
- objetivo: reemplazo transaccional de la ocupacion vigente de una entidad
- payload vigente: `id_inmueble`, `id_unidad_funcional`, `tipo_ocupacion`, `fecha_desde`, `descripcion`, `observaciones`

Descripcion:

- operacion compuesta que reemplaza la ocupacion vigente de una entidad
- implica cierre de la ocupacion actualmente abierta
- implica creacion de una nueva ocupacion

Semantica:

- operacion transaccional y atomica
- si falla cualquier paso, se realiza rollback completo
- no deja estados intermedios inconsistentes
- la atomicidad de la operacion esta garantizada por la capa de persistencia mediante una unica transaccion

Reglas:

- debe existir exactamente una ocupacion abierta previa aplicable
- la entidad se define por XOR entre `id_inmueble` e `id_unidad_funcional`
- no se permite ejecutar si no hay ocupacion vigente aplicable
- no se permite ejecutar si hay mas de una vigente inconsistente
- la nueva ocupacion debe respetar las reglas temporales vigentes
- no se permiten solapamientos, segun DB

Comportamiento:

- cierra la ocupacion vigente mediante `fecha_hasta`
- crea una nueva ocupacion con `fecha_hasta = null`
- mantiene la coherencia temporal del historial
- devuelve la nueva ocupacion creada

Observaciones de implementacion real:

- debe informarse exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- `fecha_hasta` debe ser `null` o mayor/igual a `fecha_desde`
- no puede existir mas de una ocupacion activa simultanea para la misma entidad y el mismo `tipo_ocupacion`, segun reglas vigentes de DB
- no se permite editar ocupaciones ya cerradas
- no se permite usar `PUT` para cerrar una ocupacion abierta
- el cierre historico se hace exclusivamente con `PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar`
- la baja logica se resuelve con `deleted_at`
- update, cierre y baja requieren `If-Match-Version`
- las lecturas excluyen registros con `deleted_at`
- `POST /api/v1/ocupaciones/reemplazar-vigente` no usa `If-Match-Version`; la coherencia se resuelve a nivel transaccional
- `POST /api/v1/ocupaciones/reemplazar-vigente` exige exactamente una ocupacion abierta aplicable para la entidad y el `tipo_ocupacion` segun la regla vigente de DB
- `POST /api/v1/ocupaciones/reemplazar-vigente` cierra el registro abierto y crea uno nuevo dentro de la misma transaccion
- a diferencia de disponibilidad, en ocupacion la regla de solapamiento depende de entidad + `tipo_ocupacion`
- si se intenta reemplazar con el mismo `tipo_ocupacion` y un limite coincidente, la DB puede rechazarlo como solapamiento
- esa semantica proviene de la base real y el backend la traduce a error publico

Semantica historica del registro:

- la ocupacion es un registro historico
- ocupacion = uso efectivo real
- no debe reinterpretarse como estado editable actual
- el cierre se realiza exclusivamente mediante `PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar`
- `PUT` no puede utilizarse para cerrar ni para modificar registros cerrados
- `POST /api/v1/ocupaciones/reemplazar-vigente` no reescribe el registro anterior: lo cierra y crea uno nuevo

Invariantes del dominio:

- exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- `fecha_hasta >= fecha_desde`
- no puede existir mas de una ocupacion activa simultanea para la misma entidad y el mismo `tipo_ocupacion`, segun reglas de DB

Reemplazo de ocupacion vigente:

- estado: vigente
- operacion compuesta
- requiere transaccion
- implica cierre de registro vigente + creacion de nuevo registro

### 6.10 Trazabilidad de integracion comercial por activo

#### `GET /api/v1/inmuebles/{id_inmueble}/trazabilidad-integracion`
- estado: vigente
- objetivo: consultar la trazabilidad de integracion `comercial -> inmobiliario` para un inmueble especifico

#### `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/trazabilidad-integracion`
- estado: vigente
- objetivo: consultar la trazabilidad de integracion `comercial -> inmobiliario` para una unidad funcional especifica

Semantica del read:

- es una operacion `read only`
- no genera writes ni altera `disponibilidad` u `ocupacion`
- expone ventas asociadas al activo segun `venta_objeto_inmobiliario`
- por cada venta asociada expone solo los eventos contractuales hoy materializados: `venta_confirmada` y `escrituracion_registrada`
- `estado` refleja el valor persistido en `outbox_event.status` y se limita a `PENDING`, `PUBLISHED` o `REJECTED`
- `efecto_operativo_aplicado` expresa el efecto local observable/aplicado para el activo consultado:
- `venta_confirmada` -> `disponibilidad = SIN_CAMBIO`, `ocupacion = SIN_CAMBIO`
- `escrituracion_registrada` con `PENDING` -> `disponibilidad = PENDIENTE`, `ocupacion = SIN_CAMBIO`
- `escrituracion_registrada` con `PUBLISHED` -> `disponibilidad = NO_DISPONIBLE`, `ocupacion = SIN_CAMBIO`
- `escrituracion_registrada` con `REJECTED` -> `disponibilidad = NO_APLICADO`, `ocupacion = SIN_CAMBIO`
- si el activo no existe o no tiene ventas asociadas, el backend vigente devuelve `data = []` para mantener el patron de subrecursos listados del dominio

Observacion de limites:

- este contrato no reemplaza el endpoint global pendiente `GET /api/v1/inmobiliario/trazabilidad`
- la lectura no transfiere ownership comercial a `inmobiliario`; solo consume trazabilidad ya persistida en `venta`, `venta_objeto_inmobiliario` y `outbox_event`

### 6.11 Consulta y reporte inmobiliario vigente

Dentro del dominio, la capacidad de consulta hoy vigente se limita a los endpoints GET ya listados en las secciones anteriores.

Estado actual:

- vigente: consultas GET simples y relacionales de desarrollos, inmuebles, unidades funcionales, edificaciones, servicios, asociaciones, disponibilidades y ocupaciones
- no vigente como endpoint propio: una API consolidada bajo `/api/v1/inmobiliario/...`

## 7. Contrato heredado

Este bloque conserva informacion del PDF fuente cuando difiere del backend vigente o cuando hoy no puede asumirse como contrato usable.

### 7.1 Desarrollos heredados

#### `PUT /api/v1/desarrollos/{id_desarrollo}/baja`
- estado: heredado
- fuente: `SRV-INM-001`
- observacion: el backend vigente implementa `PATCH /api/v1/desarrollos/{id_desarrollo}/baja`

### 7.2 Inmuebles heredados

#### `PUT /api/v1/inmuebles/{id_inmueble}/baja`
- estado: heredado
- fuente: `SRV-INM-002`
- observacion: el backend vigente implementa `PATCH /api/v1/inmuebles/{id_inmueble}/baja`

#### `PUT /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`
- estado: heredado
- fuente: `SRV-INM-002`
- observacion: el backend vigente implementa `PATCH /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`

#### `PUT /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`
- estado: heredado
- fuente: `SRV-INM-002`
- observacion: el backend vigente implementa `PATCH /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`

### 7.3 Unidades funcionales heredadas

#### payload historico de alta y modificacion de unidad funcional
- estado: heredado
- fuente: PDF
- campos heredados: `tipo_unidad_funcional`, `identificacion_interna`, `identificacion_externa`, `caracteristicas`, `estado_comercial_locativo`
- observacion: esos campos no existen en schemas ni routers vigentes; el backend actual usa `codigo_unidad`, `nombre_unidad`, `estado_administrativo` y `estado_operativo`

#### `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}/baja`
- estado: heredado
- fuente: `SRV-INM-003`
- observacion: el backend vigente implementa `PATCH /api/v1/unidades-funcionales/{id_unidad_funcional}/baja`

### 7.4 Edificaciones, mejoras e instalaciones heredadas

#### bloque "edificaciones, mejoras e instalaciones"
- estado: heredado
- fuente: PDF y `SRV-INM-004`
- observacion: hoy el contrato implementado confirma solo `edificacion`

#### payload historico de edificacion
- estado: heredado
- fuente: PDF
- campos heredados: `tipo_construccion`, `caracteristicas_constructivas`, `superficie_cubierta`, `superficie_semicubierta`, `superficie_descubierta`, `estado_conservacion`, `mejoras_declaradas`, `observaciones_tecnicas`
- observacion: esos campos no existen en schemas ni routers vigentes

#### `PUT /api/v1/edificaciones/{id_edificacion}/baja`
- estado: heredado
- fuente: `SRV-INM-004`
- observacion: el backend vigente implementa `PATCH /api/v1/edificaciones/{id_edificacion}/baja`

#### regla documental de edificacion "uno o ambos padres"
- estado: heredado
- fuente: PDF
- observacion: SQL y backend vigentes aplican XOR estricto entre `id_inmueble` e `id_unidad_funcional`

### 7.5 Servicios e infraestructura heredados

#### `POST /api/v1/servicios-inmobiliarios`
- estado: heredado
- fuente: PDF
- observacion: el naming vigente del backend es `POST /api/v1/servicios`

#### `GET /api/v1/servicios-inmobiliarios`
- estado: heredado
- fuente: PDF
- observacion: el naming vigente del backend es `GET /api/v1/servicios`

#### `GET /api/v1/servicios-inmobiliarios/{id_servicio}`
- estado: heredado
- fuente: PDF
- observacion: el naming vigente del backend es `GET /api/v1/servicios/{id_servicio}`

#### `PUT /api/v1/servicios-inmobiliarios/{id_servicio}`
- estado: heredado
- fuente: PDF
- observacion: el naming vigente del backend es `PUT /api/v1/servicios/{id_servicio}`

#### `PATCH /api/v1/servicios-inmobiliarios/{id_servicio}/baja`
- estado: heredado
- fuente: PDF
- observacion: el naming vigente del backend es `PATCH /api/v1/servicios/{id_servicio}/baja`

#### `PUT /api/v1/servicios/{id_servicio}/baja`
- estado: heredado
- fuente: `SRV-INM-005`
- observacion: el backend vigente implementa `PATCH /api/v1/servicios/{id_servicio}/baja`

#### `PUT /api/v1/inmuebles/{id_inmueble}/servicios/{id_inmueble_servicio}`
- estado: heredado
- fuente: PDF
- observacion: no existe endpoint implementado para update de `inmueble_servicio`

#### `PATCH /api/v1/inmuebles/{id_inmueble}/servicios/{id_inmueble_servicio}/baja`
- estado: heredado
- fuente: PDF
- observacion: no existe endpoint implementado para baja de `inmueble_servicio`

#### `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios/{id_unidad_funcional_servicio}`
- estado: heredado
- fuente: PDF
- observacion: no existe endpoint implementado para update de `unidad_funcional_servicio`

#### `PATCH /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios/{id_unidad_funcional_servicio}/baja`
- estado: heredado
- fuente: PDF
- observacion: no existe endpoint implementado para baja de `unidad_funcional_servicio`

#### termino `infraestructura`
- estado: heredado
- fuente: PDF y `SRV-INM-005`
- observacion: hoy no existe entidad, router ni schema vigente bajo ese nombre

## 8. Pendiente

Este bloque contiene capacidades del dominio que hoy no existen como contrato backend vigente.

### 8.1 Disponibilidad

Estado actual:

- existe en SQL
- existe en `DEV-SRV`
- existe implementacion backend vigente para alta, consulta, modificacion, cierre, baja logica y reemplazo transaccional de la vigente
- no quedan endpoints pendientes del bloque disponibilidad en el backend actual

### 8.2 Ocupacion

Estado actual:

- existe en SQL
- existe en `DEV-SRV`
- existe implementacion backend vigente para alta, consulta, modificacion, cierre, baja logica y reemplazo transaccional de la vigente
- no quedan endpoints pendientes del bloque ocupacion en el backend actual

### 8.3 Identificacion operativa

Estado actual:

- la identificacion operativa existe hoy solo como campos embebidos: `codigo_desarrollo`, `codigo_inmueble`, `codigo_unidad`, `codigo_servicio`
- no existe servicio independiente

Clasificacion:

- estado: pendiente

### 8.4 Identificacion catastral

Estado actual:

- no hay tablas especificas del nucleo inmobiliario vigente para este bloque
- no hay router, schema, service ni tests

Clasificacion:

- estado: no implementado

### 8.5 Atributos y documentacion inmobiliaria

Estado actual:

- no hay tablas especificas del nucleo inmobiliario vigente para este bloque
- no hay router, schema, service ni tests

Clasificacion:

- estado: no implementado

### 8.6 Consulta y reporte inmobiliario consolidado

Estado actual:

- `SRV-INM-011` esta en estado parcial
- hoy solo existen consultas GET simples y relacionales ya documentadas en el contrato vigente
- no existe ficha integral del activo ni router consolidado de reportes

#### `GET /api/v1/inmobiliario/consulta-operativa`
- estado: pendiente
- observacion: no existe router vigente bajo `/api/v1/inmobiliario/...`

#### `GET /api/v1/inmobiliario/inventario`
- estado: pendiente
- observacion: no existe router vigente bajo `/api/v1/inmobiliario/...`

#### `GET /api/v1/inmobiliario/trazabilidad`
- estado: pendiente
- observacion: no existe router vigente bajo `/api/v1/inmobiliario/...`

#### `GET /api/v1/inmobiliario/reportes`
- estado: pendiente
- observacion: no existe router vigente bajo `/api/v1/inmobiliario/...`

### 8.7 factura_servicio

Estado actual:

- `factura_servicio` es una entidad conceptual pendiente para registrar facturas externas de servicios
- no existe endpoint inmobiliario vigente para registrar `factura_servicio`
- no existe payload documentado para factura emitida por proveedor externo
- no existe evento publicado documentado para disparar generacion de obligacion financiera desde ese origen
- el sistema no emite facturas de servicio

Clasificacion:

- estado: no implementado
- ownership del registro origen: pendiente en inmobiliario, vinculado a `servicio` y al activo alcanzado
- ownership de la obligacion derivada: `financiero`
- contrato requerido: origen compatible para `relacion_generadora` antes de exponer API

## 9. Reglas visibles del contrato

- `inmueble` es la raiz operativa del dominio.
- `desarrollo` es opcional para `inmueble`.
- `unidad_funcional` no existe sin `inmueble`.
- `edificacion` exige exactamente un padre entre `id_inmueble` e `id_unidad_funcional`.
- las operaciones write del dominio usan contexto tecnico por headers transversales
- update, baja y acciones asociativas versionadas usan `If-Match-Version`
- las respuestas exitosas incluyen `ok: true` y un bloque `data`
- las respuestas de error incluyen `ok: false`, `error_code`, `error_message` y `details`
- `instalacion` no es entidad del dominio inmobiliario; solo aparece como metadata tecnica y como concepto propio del dominio `operativo`
- `servicio` se implementa como catalogo reutilizable asociado a inmuebles y unidades funcionales
- `factura_servicio` no tiene endpoint vigente y no debe confundirse con facturacion propia del sistema
- las consultas del dominio no generan efectos persistentes
- `disponibilidad` forma parte del contrato API implementado para alta, consulta, modificacion, cierre y baja logica
- `ocupacion` forma parte del contrato API implementado para alta, consulta, modificacion, cierre y baja logica

## 10. Notas de compatibilidad y decisiones pendientes

### 10.1 Criterio de lectura para frontend

Para consumo frontend:

- usar solo la seccion `6. Contrato vigente`
- tratar la seccion `7. Contrato heredado` como referencia historica, no como capacidad disponible
- tratar la seccion `8. Pendiente` como capacidad no disponible hoy

### 10.2 Validacion contra implementacion real

El contrato marcado aqui como vigente fue contrastado con:

- routers del dominio
- schemas del dominio
- SQL vigente
- `DEV-SRV`
- `RN-INM`
- `ERR-INM`
- tests de create, update, baja, asociacion y consulta del dominio

### 10.3 Evidencia de tests revisada

La evidencia vigente confirma:

- altas, detalles, listados, updates y bajas de desarrollos, inmuebles, unidades funcionales, edificaciones y servicios
- asociacion y desasociacion de inmueble a desarrollo
- asociacion y consulta de servicios por inmueble y por unidad funcional
- manejo de `NOT_FOUND`, `APPLICATION_ERROR` y `CONCURRENCY_ERROR`

## Resumen de endpoints

| Metodo | Endpoint | Estado | Observacion breve |
| --- | --- | --- | --- |
| `POST` | `/api/v1/desarrollos` | vigente | Alta de desarrollo |
| `GET` | `/api/v1/desarrollos/{id_desarrollo}` | vigente | Detalle de desarrollo |
| `GET` | `/api/v1/desarrollos` | vigente | Listado de desarrollos |
| `PUT` | `/api/v1/desarrollos/{id_desarrollo}` | vigente | Modificacion de desarrollo |
| `PATCH` | `/api/v1/desarrollos/{id_desarrollo}/baja` | vigente | Baja logica de desarrollo |
| `POST` | `/api/v1/inmuebles` | vigente | Alta de inmueble |
| `GET` | `/api/v1/inmuebles/{id_inmueble}` | vigente | Detalle de inmueble |
| `GET` | `/api/v1/inmuebles` | vigente | Listado de inmuebles |
| `PUT` | `/api/v1/inmuebles/{id_inmueble}` | vigente | Modificacion de inmueble |
| `PATCH` | `/api/v1/inmuebles/{id_inmueble}/baja` | vigente | Baja logica de inmueble |
| `PATCH` | `/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo` | vigente | Asociacion a desarrollo |
| `PATCH` | `/api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo` | vigente | Desasociacion de desarrollo |
| `POST` | `/api/v1/inmuebles/{id_inmueble}/unidades-funcionales` | vigente | Alta de unidad funcional |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/unidades-funcionales` | vigente | Listado por inmueble |
| `GET` | `/api/v1/unidades-funcionales` | vigente | Listado global de unidades funcionales |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}` | vigente | Detalle de unidad funcional |
| `PUT` | `/api/v1/unidades-funcionales/{id_unidad_funcional}` | vigente | Modificacion de unidad funcional |
| `PATCH` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/baja` | vigente | Baja logica de unidad funcional |
| `POST` | `/api/v1/edificaciones` | vigente | Alta de edificacion |
| `GET` | `/api/v1/edificaciones/{id_edificacion}` | vigente | Detalle de edificacion |
| `GET` | `/api/v1/edificaciones` | vigente | Listado global de edificaciones |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/edificaciones` | vigente | Listado por inmueble |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones` | vigente | Listado por unidad funcional |
| `PUT` | `/api/v1/edificaciones/{id_edificacion}` | vigente | Modificacion de edificacion |
| `PATCH` | `/api/v1/edificaciones/{id_edificacion}/baja` | vigente | Baja logica de edificacion |
| `POST` | `/api/v1/servicios` | vigente | Alta de servicio |
| `GET` | `/api/v1/servicios/{id_servicio}` | vigente | Detalle de servicio |
| `GET` | `/api/v1/servicios` | vigente | Listado de servicios |
| `PUT` | `/api/v1/servicios/{id_servicio}` | vigente | Modificacion de servicio |
| `PATCH` | `/api/v1/servicios/{id_servicio}/baja` | vigente | Baja logica de servicio |
| `POST` | `/api/v1/inmuebles/{id_inmueble}/servicios` | vigente | Asociacion servicio <-> inmueble |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/servicios` | vigente | Servicios asociados a inmueble |
| `GET` | `/api/v1/servicios/{id_servicio}/inmuebles` | vigente | Inmuebles asociados a servicio |
| `POST` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios` | vigente | Asociacion servicio <-> unidad funcional |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios` | vigente | Servicios asociados a unidad funcional |
| `GET` | `/api/v1/servicios/{id_servicio}/unidades-funcionales` | vigente | Unidades funcionales asociadas a servicio |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/trazabilidad-integracion` | vigente | Trazabilidad de integracion comercial por inmueble |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/trazabilidad-integracion` | vigente | Trazabilidad de integracion comercial por unidad funcional |
| `PUT` | `/api/v1/desarrollos/{id_desarrollo}/baja` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/inmuebles/{id_inmueble}/baja` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/baja` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/edificaciones/{id_edificacion}/baja` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `POST` | `/api/v1/servicios-inmobiliarios` | heredado | Naming historico; backend usa `/servicios` |
| `GET` | `/api/v1/servicios-inmobiliarios` | heredado | Naming historico; backend usa `/servicios` |
| `GET` | `/api/v1/servicios-inmobiliarios/{id_servicio}` | heredado | Naming historico; backend usa `/servicios/{id_servicio}` |
| `PUT` | `/api/v1/servicios-inmobiliarios/{id_servicio}` | heredado | Naming historico; backend usa `/servicios/{id_servicio}` |
| `PATCH` | `/api/v1/servicios-inmobiliarios/{id_servicio}/baja` | heredado | Naming historico; backend usa `/servicios/{id_servicio}/baja` |
| `PUT` | `/api/v1/servicios/{id_servicio}/baja` | heredado | `DEV-SRV` historico; backend usa `PATCH` |
| `PUT` | `/api/v1/inmuebles/{id_inmueble}/servicios/{id_inmueble_servicio}` | heredado | El PDF lo propone, no existe en backend |
| `PATCH` | `/api/v1/inmuebles/{id_inmueble}/servicios/{id_inmueble_servicio}/baja` | heredado | El PDF lo propone, no existe en backend |
| `PUT` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios/{id_unidad_funcional_servicio}` | heredado | El PDF lo propone, no existe en backend |
| `PATCH` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios/{id_unidad_funcional_servicio}/baja` | heredado | El PDF lo propone, no existe en backend |
| `POST` | `/api/v1/disponibilidades` | vigente | Alta de disponibilidad |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/disponibilidades` | vigente | Listado de disponibilidades por inmueble |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades` | vigente | Listado de disponibilidades por unidad funcional |
| `PUT` | `/api/v1/disponibilidades/{id_disponibilidad}` | vigente | Modificacion de disponibilidad abierta |
| `PATCH` | `/api/v1/disponibilidades/{id_disponibilidad}/baja` | vigente | Baja logica por `deleted_at` |
| `PATCH` | `/api/v1/disponibilidades/{id_disponibilidad}/cerrar` | vigente | Cierre historico exclusivo del registro |
| `POST` | `/api/v1/disponibilidades/reemplazar-vigente` | vigente | Reemplazo transaccional de la disponibilidad vigente |
| `POST` | `/api/v1/ocupaciones` | vigente | Alta de ocupacion |
| `GET` | `/api/v1/inmuebles/{id_inmueble}/ocupaciones` | vigente | Listado de ocupaciones por inmueble |
| `GET` | `/api/v1/unidades-funcionales/{id_unidad_funcional}/ocupaciones` | vigente | Listado de ocupaciones por unidad funcional |
| `PUT` | `/api/v1/ocupaciones/{id_ocupacion}` | vigente | Modificacion de ocupacion abierta |
| `PATCH` | `/api/v1/ocupaciones/{id_ocupacion}/baja` | vigente | Baja logica por `deleted_at` |
| `PATCH` | `/api/v1/ocupaciones/{id_ocupacion}/cerrar` | vigente | Cierre historico exclusivo del registro |
| `POST` | `/api/v1/ocupaciones/reemplazar-vigente` | vigente | Reemplazo transaccional de la ocupacion vigente |
| `GET` | `/api/v1/inmobiliario/consulta-operativa` | pendiente | Reporte no implementado en backend |
| `GET` | `/api/v1/inmobiliario/inventario` | pendiente | Reporte no implementado en backend |
| `GET` | `/api/v1/inmobiliario/trazabilidad` | pendiente | Reporte no implementado en backend |
| `GET` | `/api/v1/inmobiliario/reportes` | pendiente | Reporte no implementado en backend |
