# INT-CONS-001 - Comportamiento inmobiliario ante eventos de comercial

## 1. Contexto actual

### 1.1 Contrato interdominio vigente

La decision `INT-DEC-001` ya fijo que la integracion `comercial -> inmobiliario` es:

1. asincronica
2. basada en eventos de negocio
3. unidireccional desde `comercial`
4. sin mutacion directa de `disponibilidad` ni `ocupacion` por parte de `comercial`

La decision `INT-EVT-001` ya fijo los dos eventos de negocio contractuales a analizar:

1. `venta_confirmada`
2. `escrituracion_registrada`

La decision `COM-DEC-001` ya fijo que en la version actual:

1. `venta` no se cierra de forma persistida al confirmarse
2. la definicion logica no persistida de cierre es `venta confirmada + escrituracion registrada`
3. `comercial` no modifica por si mismo `disponibilidad`
4. `comercial` no modifica por si mismo `ocupacion`

### 1.2 Estado real de implementacion

El backend actual ya materializa:

1. persistencia transaccional de `venta_confirmada` en `outbox_event`
2. persistencia transaccional de `escrituracion_registrada` en `outbox_event`
3. rollback completo del evento si falla la transaccion de negocio
4. consumidor interdominio materializado en `inmobiliario` para `escrituracion_registrada`
5. publicacion del evento como `PUBLISHED` solo cuando la mutacion operativa local finaliza sin error
6. persistencia de razon estructurada y metadata tecnica minima cuando el evento cierra en `PUBLISHED` o `REJECTED`
7. failpoints de testing transaccional sin DDL global para las pruebas de rollback del flujo `comercial -> inmobiliario`

Esto surge de:

1. `confirm_venta_service` + `comercial_repository.confirm_venta(...)`
2. `create_escrituracion_service` + `comercial_repository.create_escrituracion(...)`
3. `test_outbox_events.py`
4. `tests/sql_failpoints.py`
5. `CORE-DEC-OUTBOX-001`

### 1.2.1 Regla de failpoints para este flujo

Los tests de integracion de este circuito no deben usar `CREATE TRIGGER` como mecanismo de falla inducida cuando corren dentro del fixture transaccional compartido.

Razon tecnica:

1. `CREATE TRIGGER` sobre `venta` o `escrituracion` retiene locks DDL hasta el cierre de la transaccion externa del fixture
2. esos locks pueden cruzarse con el consumo local de `escrituracion_registrada` o con la persistencia de `outbox_event`
3. el resultado observable es bloqueo prolongado o deadlock intermitente en suites paralelas

Por eso, los tests de rollback y outbox de este flujo deben usar `tests/sql_failpoints.py`, que inyecta la excepcion sobre la conexion del test sin mutar catalogo ni crear triggers temporales.

### 1.3 Estado real del dominio inmobiliario

En implementacion real, `inmobiliario` ya dispone de circuito backend, SQL y tests para:

1. alta de `disponibilidad`
2. cierre de `disponibilidad`
3. reemplazo transaccional de `disponibilidad` vigente
4. alta de `ocupacion`
5. cierre de `ocupacion`
6. reemplazo transaccional de `ocupacion` vigente

Semanticamente:

1. `disponibilidad` es nucleo del dominio `inmobiliario` y representa estado potencial de uso
2. `ocupacion` es nucleo del dominio `inmobiliario` y representa uso efectivo real
3. `outbox_event` y el payload de integracion son soporte transversal y no trasladan ownership semantico

### 1.4 Estado observado hoy en codigo y tests

El flujo write hoy verificado es:

1. `reserva_venta confirmada` reemplaza `DISPONIBLE -> RESERVADA`
2. `generar venta` preserva el bloqueo `RESERVADA`
3. `confirmar venta` no modifica `disponibilidad`
4. `registrar escrituracion` no modifica `disponibilidad`
5. el consumidor de `escrituracion_registrada` reemplaza `RESERVADA -> NO_DISPONIBLE`
6. ni `confirmar venta` ni `registrar escrituracion` crean `ocupacion`
7. el consumidor de `escrituracion_registrada` tampoco crea ni cierra `ocupacion`

Por lo tanto, el ultimo estado operativo observable inmediatamente despues del write de `escrituracion` sigue siendo el que exista en `inmobiliario` hasta que el evento pendiente sea consumido; una vez procesado `escrituracion_registrada`, el estado operativo abierto esperado pasa a ser `NO_DISPONIBLE`.

## 2. Eventos a analizar

### 2.1 `venta_confirmada`

`venta_confirmada` representa que una `venta` alcanzo `estado_venta = confirmada`.

El payload hoy persistido en outbox contiene como minimo:

1. `id_venta`
2. `id_reserva_venta`
3. `estado_venta = confirmada`
4. `objetos[]` con `id_inmueble` o `id_unidad_funcional`

Este evento representa confirmacion comercial.

No representa por si solo:

1. cierre persistido de `venta`
2. cierre juridico total
3. mutacion automatica de `ocupacion`
4. mutacion operativa ya aplicada por `inmobiliario`

### 2.2 `escrituracion_registrada`

`escrituracion_registrada` representa que una `escrituracion` quedo registrada para una `venta` ya compatible con ese hito.

El payload hoy persistido en outbox contiene como minimo:

1. `id_venta`
2. `id_escrituracion`
3. `fecha_escrituracion`
4. `numero_escritura`
5. `objetos[]` con `id_inmueble` o `id_unidad_funcional`

Este evento representa formalizacion juridico-documental posterior a la confirmacion comercial.

No representa por si solo:

1. toma de posesion fisica
2. alta de ocupante efectivo
3. cierre financiero
4. regularizacion registral externa fuera del backend

## 3. Comportamiento esperado de inmobiliario ante cada evento

### 3.1 Decision para `venta_confirmada`

Ante `venta_confirmada`, `inmobiliario` debe:

1. consumir el evento de forma idempotente
2. validar que cada objeto referido exista y sea identificable
3. no modificar `disponibilidad`
4. no modificar `ocupacion`

Efecto esperado:

1. si el objeto viene del flujo hoy implementado con reserva previa, la `disponibilidad` vigente debe permanecer en `RESERVADA`
2. si no existe una `RESERVADA` coherente, `inmobiliario` no debe sintetizar un nuevo estado operativo a partir de inferencia
3. cualquier desalineacion debe quedar como inconsistencia pendiente de reproceso o revision, sin write compensatorio automatico

Fundamento:

1. `COM-DEC-001` fija que la venta no queda cerrada de forma persistida al confirmarse
2. la definicion logica de cierre exige ademas `escrituracion registrada`
3. los tests actuales verifican preservacion de `RESERVADA` despues de `confirmar venta`
4. el flujo publico hoy implementado de venta nace desde `reserva_venta confirmada`, no desde un alta write publica directa de `venta`

### 3.2 Decision para `escrituracion_registrada`

Ante `escrituracion_registrada`, `inmobiliario` debe:

1. consumir el evento de forma idempotente
2. tratarlo como disparador de cierre operativo de `disponibilidad`
3. reemplazar la `disponibilidad` vigente `RESERVADA` de cada objeto por una nueva `disponibilidad` en estado `NO_DISPONIBLE`
4. ejecutar ese reemplazo con semantica historica: cerrar registro vigente + crear nuevo registro
5. hacerlo dentro de una misma unidad transaccional local por evento, para no dejar cierre parcial entre objetos de una misma venta
6. no modificar `ocupacion`

Precondiciones del reemplazo:

1. debe existir exactamente una `disponibilidad` vigente por objeto
2. esa `disponibilidad` vigente debe estar en `RESERVADA`
3. si no se cumple esa precondicion, no debe inventarse ni forzarse una mutacion alternativa
4. si la inconsistencia es permanente para el payload recibido, el evento no debe quedar en `PENDING`; debe cerrarse en un estado terminal equivalente a rechazo operacional

Efecto esperado:

1. `RESERVADA` deja de ser el ultimo estado operativo abierto del objeto
2. el objeto queda historizado como `NO_DISPONIBLE`
3. el cambio se apoya en un estado ya observado en SQL, codigo y tests, sin introducir catalogos nuevos

Fundamento:

1. `COM-DEC-001` fija que la combinacion `venta confirmada + escrituracion registrada` es el cierre logico actual
2. `INT-DEC-001` reconoce `escrituracion` como hito valido de integracion con `inmobiliario`
3. `DEV-API-COMERCIAL` fija que cualquier ajuste posterior de `disponibilidad` por escrituracion debe resolverse por integracion con `inmobiliario`
4. `NO_DISPONIBLE` ya existe como estado operativo observado y no requiere inventar una semantica nueva como `VENDIDA`

## 4. Que no debe hacer todavia

`inmobiliario` no debe todavia:

1. crear `ocupacion` a partir de `venta_confirmada`
2. crear `ocupacion` a partir de `escrituracion_registrada`
3. cerrar `ocupacion` vigente por inferencia
4. liberar a `DISPONIBLE` un objeto vendido o escriturado
5. crear estados nuevos de `disponibilidad` no respaldados hoy por SQL, codigo o tests
6. inferir efectos operativos a partir de `instrumento_compraventa` o `cesion`
7. mutar tablas de `comercial`
8. reemplazar el contrato asincronico por llamadas sincronas de `comercial` hacia `inmobiliario`
9. asumir cobertura para ventas directas sin reserva si ese flujo write no esta materializado como contrato publico vigente

## 5. Si disponibilidad cambia o no

| Evento | Cambio de disponibilidad | Decision |
| --- | --- | --- |
| `venta_confirmada` | No | Se preserva la `RESERVADA` vigente cuando existe; si no existe estado coherente, se marca inconsistencia sin mutacion automatica |
| `escrituracion_registrada` | Si | Se reemplaza `RESERVADA -> NO_DISPONIBLE` por cada objeto, usando el patron historico y transaccional de `inmobiliario`; si la precondicion permanente falla, el evento debe cerrarse en estado terminal `REJECTED` |

## 6. Si ocupacion cambia o no

| Evento | Cambio de ocupacion | Decision |
| --- | --- | --- |
| `venta_confirmada` | No | La confirmacion comercial no equivale a uso efectivo real |
| `escrituracion_registrada` | No | La escrituracion no informa toma de posesion ni tipo de ocupacion efectiva |

Razon de fondo:

1. `ocupacion` representa uso efectivo y no simple hito comercial o juridico
2. el payload actual no informa ocupante, fecha de posesion ni tipo de ocupacion
3. `DEV-API-COMERCIAL` fija expresamente que ni la confirmacion de venta ni la escrituracion modifican por si solas `ocupacion`

## 7. Pendientes abiertos

1. definir una estrategia de idempotencia mas fuerte que el criterio operativo actual de `ALREADY_APPLIED`, por ejemplo con registro explicito por `event_type + aggregate_id`
2. definir reporte, consulta y remediacion operativa a partir de la razon estructurada y metadata tecnica ya persistidas en `outbox_event`
3. definir los metadatos de trazabilidad definitivos que `inmobiliario` conservara al generar `NO_DISPONIBLE`
4. aclarar documentalmente el tratamiento de ventas futuras sin reserva previa si ese flujo write llega a exponerse publicamente
5. definir un evento posterior especifico para toma de posesion si en el futuro se quisiera mutar `ocupacion`

## 8. Base de verificacion

Esta decision se apoya en:

1. `backend/documentacion/DECISIONES/comercial/COM-DEC-001-cierre-del-ciclo-de-vida-de-venta.md`
2. `backend/documentacion/DECISIONES/integracion/INT-DEC-001-integracion-comercial-inmobiliario.md`
3. `backend/documentacion/DECISIONES/integracion/INT-EVT-001-eventos-integracion-comercial-inmobiliario.md`
4. `backend/documentacion/DECISIONES/infraestructura/CORE-DEC-OUTBOX-001-transactional-outbox.md`
5. `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
6. `backend/documentacion/DEV-API/dominios/inmobiliario/DEV-API-INM-001.md`
7. `backend/app/application/comercial/services/confirm_venta_service.py`
8. `backend/app/application/comercial/services/create_escrituracion_service.py`
9. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
10. `backend/app/infrastructure/persistence/repositories/outbox_repository.py`
11. `backend/tests/test_ventas_confirm.py`
12. `backend/tests/test_escrituraciones_create.py`
13. `backend/tests/test_outbox_events.py`
14. `backend/tests/test_disponibilidades_reemplazar_vigente.py`
15. `backend/tests/test_ocupaciones_reemplazar_vigente.py`
16. `AGENTS.md`

## 9. Contradicciones documentales detectadas

Se detectaron contradicciones no bloqueantes que deben leerse a favor de la implementacion real:

1. `SRV-INM-007` afirma que `disponibilidad` y `ocupacion` no tienen routers, services ni tests inmobiliarios vigentes, pero el backend actual si los tiene
2. `RN-INM` y `EST-INM` siguen marcando `disponibilidad` y `ocupacion` como `PARCIAL` por falta de backend, pero `DEV-API-INM-001`, el codigo y los tests muestran contrato vigente real
3. `INT-EVT-001` conserva la idea historica de ausencia de consumidor; hoy ya existe outbox transaccional persistido y un consumidor materializado en `inmobiliario` para `escrituracion_registrada`
