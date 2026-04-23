# CORE-DEC-OUTBOX-001 - Transactional Outbox

## 1. Contexto

El sistema necesita emitir eventos de dominio de forma confiable a partir de operaciones write ya persistidas.

Esa necesidad aparece especialmente en integraciones asincronicas entre dominios, donde:

1. el write de negocio ocurre en una transaccion local sobre base de datos
2. la publicacion del evento ocurre fuera de esa transaccion
3. existe riesgo de inconsistencia entre el resultado del write y la emision del evento

El problema operativo a resolver es el siguiente:

1. si la operacion de negocio hace `commit` y el evento no queda persistido, se pierde capacidad de integracion
2. si el evento se publica por fuera del write y luego la transaccion hace `rollback`, se expone un evento sin estado de negocio valido

## 2. Patron adoptado

El patron adoptado es `Transactional Outbox`.

La solucion consiste en insertar el evento en una tabla local `outbox_event` dentro de la misma transaccion que confirma la operacion de negocio.

La publicacion del evento se delega a un proceso posterior e independiente del write de negocio.

## 3. Definicion de la tabla `outbox_event`

La tabla `outbox_event` queda materializada en SQL con los siguientes campos principales:

1. `id`
2. `event_type`
3. `aggregate_type`
4. `aggregate_id`
5. `payload`
6. `occurred_at`
7. `published_at`
8. `status`
9. `processing_reason`
10. `processing_metadata`

### 3.1 Proposito de cada campo

`id`

Identificador interno del evento en la tabla outbox.

`event_type`

Nombre funcional del evento emitido, por ejemplo `venta_confirmada` o `escrituracion_registrada`.

`aggregate_type`

Tipo de agregado o entidad de negocio a la que pertenece el evento, por ejemplo `venta`.

`aggregate_id`

Identificador de la entidad de negocio asociada al evento.

`payload`

Carga util del evento en `jsonb`, con informacion minima necesaria para consumidores posteriores.

`occurred_at`

Fecha y hora del hito de negocio que origino el evento.

`published_at`

Fecha y hora en que el evento fue marcado como publicado por el proceso publisher.

`status`

Estado actual del evento dentro del outbox.

`processing_reason`

Razon estructurada en `jsonb` para cierres tecnicos `PUBLISHED` o `REJECTED`.

Debe conservar al menos un `code` de lectura estable y puede agregar categoria o detalle corto.

`processing_metadata`

Metadata tecnica minima en `jsonb` sobre el procesamiento final del evento.

Debe conservar como minimo identificacion del procesador, modo de procesamiento y marca temporal tecnica del cierre.

## 4. Estados del evento

Los estados implementados actualmente son:

### 4.1 `PENDING`

Evento pendiente de publicacion.

Es el estado inicial al insertar una fila en `outbox_event`.

### 4.2 `PUBLISHED`

Evento marcado como publicado correctamente por el publisher.

Al cerrarse en este estado debe persistirse tambien `processing_reason` y `processing_metadata`.

### 4.3 `REJECTED`

Evento cerrado en estado terminal por un consumidor cuando detecta una inconsistencia permanente del payload o de sus precondiciones de negocio.

En este estado:

1. el evento ya no debe volver a consultarse como `PENDING`
2. no implica publicacion correcta
3. no debe usarse para errores tecnicos transitorios
4. debe persistir una razon estructurada y metadata tecnica minima de procesamiento

En la implementacion actual, `REJECTED` se utiliza para el consumo local de `escrituracion_registrada` cuando `inmobiliario` detecta una inconsistencia permanente, por ejemplo ausencia de una `RESERVADA` vigente coherente.

## 5. Regla fundamental

La regla fundamental del patron es:

1. el evento se inserta en la misma transaccion que la operacion de negocio
2. si la transaccion hace `rollback`, no queda evento persistido
3. si la transaccion hace `commit`, el evento queda garantizado en `outbox_event`

En la implementacion actual esta regla se aplica en:

1. `confirm_venta_service` / `confirm_venta`
2. `create_escrituracion_service` / `create_escrituracion`

En ambos casos, la insercion del evento ocurre antes del `commit` y dentro del mismo repository que persiste la operacion de negocio.

## 6. Publisher

El publisher es un proceso externo al write de negocio.

Su responsabilidad es:

1. leer eventos `PENDING`
2. publicarlos
3. marcarlos como `PUBLISHED`

En la implementacion actual, el publisher esta materializado en `backend/scripts/outbox_publisher.py`.

Ese script:

1. abre una sesion de base
2. consulta eventos `PENDING` con `get_pending_events(...)`
3. simula la publicacion mediante `print`
4. marca cada evento como publicado con `mark_as_published(...)`, persistiendo razon estructurada y metadata minima del publisher
5. confirma los cambios con `commit`

El publisher no debe depender del consumidor. Si existe un evento resuelto por un consumidor local especifico, el publisher puede excluirlo explicitamente de su circuito sin importar ni ejecutar esa logica de consumo.

El publisher no forma parte de la transaccion de negocio original.

## 7. Idempotencia

La implementacion actual no garantiza entrega unica.

La responsabilidad de manejar idempotencia queda del lado del consumidor.

El sistema permite reintentos de publicacion porque:

1. los eventos permanecen persistidos hasta ser marcados como `PUBLISHED`
2. la publicacion se ejecuta fuera de la transaccion de negocio
3. no existe garantia de exactly-once delivery en el alcance actual

## 8. Alcance

La implementacion actual del patron garantiza:

1. persistencia confiable del evento junto con el write de negocio
2. no perdida del evento cuando la transaccion de negocio confirma correctamente
3. ausencia de evento cuando la transaccion de negocio hace `rollback`

La implementacion actual no define:

1. infraestructura de mensajeria
2. broker distribuido
3. colas
4. topicos
5. entrega distribuida
6. retries distribuidos
7. ordering global entre procesos

Por lo tanto, el alcance real del patron en esta version es la persistencia transaccional confiable del evento y su posterior publicacion por un proceso desacoplado.

## 9. Regla de testing transaccional

Los tests que validan rollback de writes sincronizables y ausencia de persistencia en `outbox_event` deben respetar una restriccion tecnica adicional.

Si el test corre sobre el fixture transaccional de `backend/tests/conftest.py`, no debe inyectar fallas con `CREATE TRIGGER` ni con otro DDL sobre tablas compartidas.

Motivo:

1. el fixture mantiene una transaccion externa real abierta durante todo el test
2. el `commit` del test libera savepoints, no la transaccion externa
3. en PostgreSQL, `CREATE TRIGGER` y `DROP TRIGGER` retienen locks como `ShareRowExclusiveLock` hasta el fin de esa transaccion
4. esos locks pueden bloquear o deadlockear suites paralelas sobre `venta`, `escrituracion` u otras tablas del flujo

Por lo tanto, para failpoints de SQL en tests transaccionales debe usarse `backend/tests/sql_failpoints.py`, que instala listeners locales a la conexion del test y evita introducir DDL global en la base.

Este patron aplica especialmente a los tests que verifican:

1. rollback de `confirm_venta`
2. rollback de `create_escrituracion`
3. ausencia de evento en `outbox_event` cuando falla la transaccion de negocio

## 10. Base de verificacion

Esta decision se basa en:

1. `backend/app/infrastructure/persistence/repositories/outbox_repository.py`
2. `backend/app/application/comercial/services/confirm_venta_service.py`
3. `backend/app/application/comercial/services/create_escrituracion_service.py`
4. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
5. `backend/scripts/outbox_publisher.py`
6. `backend/database/schema_inmobiliaria_20260418.sql`
7. `backend/tests/conftest.py`
8. `backend/tests/sql_failpoints.py`
9. `backend/tests/test_outbox_events.py`
10. `AGENTS.md`
