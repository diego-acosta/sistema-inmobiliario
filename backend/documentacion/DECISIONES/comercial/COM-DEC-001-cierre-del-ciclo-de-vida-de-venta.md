# COM-DEC-001 - Cierre del ciclo de vida de venta

## 1. Contexto

El flujo comercial write actualmente materializado en `backend` es:

1. `reserva_venta` en `borrador`
2. `POST /api/v1/reservas-venta/{id_reserva_venta}/activar` -> `activa`
3. `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar` -> `confirmada`
4. `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta` -> crea `venta` en `borrador` y finaliza la reserva origen
5. `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales` -> completa `monto_total` y `precio_asignado`
6. `PATCH /api/v1/ventas/{id_venta}/confirmar` -> `venta.estado_venta = confirmada`
7. `POST /api/v1/ventas/{id_venta}/instrumentos-compraventa` -> registra `instrumento_compraventa`
8. `POST /api/v1/ventas/{id_venta}/cesiones` -> registra `cesion`
9. `POST /api/v1/ventas/{id_venta}/escrituraciones` -> registra `escrituracion`

La `venta` puede originarse:

1. a partir de una `reserva_venta` previa en estado `confirmada`
2. sin `reserva_venta` previa, siempre que exista un contrato write especifico que la registre

Este flujo surge de:

- `DEV-API-COMERCIAL.md`
- `SRV-COM-002-gestion-de-venta.md`
- `SRV-COM-004-gestion-de-instrumentos-de-compraventa.md`
- `SRV-COM-005-gestion-de-cesiones.md`
- `SRV-COM-006-gestion-de-escrituracion.md`
- `RN-COM.md`
- routers, services, repositories y tests existentes en `backend`

## 2. Problema

No existe una definicion formal, persistida e implementada para el cierre de `venta`.

El workspace documenta estados de referencia para `venta`, incluyendo `cancelada`, `en_proceso` y `finalizada`, pero no existe hoy en el backend un endpoint write especifico que:

1. materialice esas transiciones
2. defina su relacion obligatoria con `instrumento_compraventa`, `cesion` o `escrituracion`
3. establezca efectos operativos definitivos sobre `disponibilidad`
4. establezca efectos sobre `ocupacion`

En consecuencia, el flujo real llega hasta `venta confirmada` con registraciones posteriores de soporte comercial y juridico, pero sin cierre persistido de la `venta`.

## 3. Principios

### 3.1 Separacion de dominio

El dominio `comercial` no es owner de `disponibilidad` ni de `ocupacion`.

Toda mutacion sobre `disponibilidad` debe surgir de una integracion explicita con `inmobiliario` o de contratos ya implementados y respaldados por la documentacion.

`ocupacion` no debe ser creada, cerrada ni reinterpretada localmente desde `comercial` salvo contrato expreso.

### 3.2 Fuente de verdad implementada

La definicion vigente del ciclo de vida de `venta` debe surgir de la interseccion entre:

1. documentacion del workspace
2. SQL materializado
3. codigo backend existente
4. tests efectivos

Si un estado o efecto esta documentado pero no tiene soporte persistente ni endpoint write materializado, no forma parte del comportamiento implementado de la version actual.

### 3.3 No inferencia de cierre

La sola existencia de `instrumento_compraventa`, `cesion` o `escrituracion` no autoriza a inferir automaticamente una mutacion de `estado_venta` si esa transicion no esta definida y testeada en el backend.

## 4. Decisiones

### 4.1 La escrituracion no finaliza automaticamente la venta

`POST /api/v1/ventas/{id_venta}/escrituraciones` registra una `escrituracion` asociada a una `venta`, pero no ejecuta cierre automatico de `venta`.

No se persiste cambio a `estado_venta` durante el alta de `escrituracion`.

La `escrituracion` se considera dentro del dominio `comercial` como un evento documental y juridico de formalizacion posterior o complementaria a la `venta`.

La `escrituracion` no constituye por si sola un evento operativo que modifique el estado del activo inmobiliario.

### 4.2 `estado_venta` permanece en `confirmada`

Una vez confirmada la `venta`, las altas posteriores de:

- `instrumento_compraventa`
- `cesion`
- `escrituracion`

no modifican `venta.estado_venta`.

El estado persistido de la `venta` permanece en `confirmada` mientras no exista un contrato write especifico que defina otra transicion.

### 4.3 No se implementan estados `finalizada`, `cancelada` ni `en_proceso`

Aunque `DEV-API` documenta transiciones de referencia para `venta`, en la version actual del backend no existe implementacion write materializada para:

- `confirmada -> en_proceso`
- `confirmada -> finalizada`
- `borrador -> cancelada`
- `activa -> cancelada`
- `confirmada -> cancelada`
- `en_proceso -> finalizada`

Por lo tanto, esos estados no forman parte del ciclo write efectivo de `venta` en esta version.

### 4.4 `comercial` no modifica `disponibilidad`

En el ciclo post-generacion de `venta`:

- `definir-condiciones-comerciales` no modifica `disponibilidad`
- `confirmar venta` no modifica `disponibilidad` en la implementacion actual
- `instrumento_compraventa` no modifica `disponibilidad`
- `cesion` no modifica `disponibilidad`
- `escrituracion` no modifica `disponibilidad`

La unica `disponibilidad` operativa vigente que subsiste en el flujo actual es la `RESERVADA` proveniente de la `reserva_venta` confirmada cuando la `venta` nace desde reserva.

El ultimo estado operativo conocido del activo dentro del flujo comercial permanece como `RESERVADA`.

Ni la `venta` ni la `escrituracion` modifican ese estado en la version actual.

### 4.5 No existe cancelacion funcional de `venta` en esta version

No existe hoy un endpoint write implementado que materialice cancelacion funcional de `venta`.

La documentacion incluye referencias a:

- `PATCH /api/v1/ventas/{id_venta}/baja`
- estados `cancelada` y `finalizada`

pero el backend actual no expone una cancelacion funcional implementada y validada end-to-end para `venta`.

## 5. Definicion logica no persistida

Para esta version, se adopta la siguiente definicion logica de cierre:

`venta cerrada = venta confirmada + escrituracion registrada`

Esta definicion:

1. es semantica
2. no implica cambio persistido de `estado_venta`
3. no implica cambio automatico de `disponibilidad`
4. no implica cambio automatico de `ocupacion`
5. no reemplaza la necesidad futura de un cierre real de `venta`

Se utiliza solo como criterio de interpretacion funcional del flujo comercial actual.

## 6. Pendientes

### 6.1 Cierre real de `venta`

Debe definirse un contrato write explicito para cierre de `venta`, incluyendo:

1. precondiciones
2. transicion de estado persistida
3. relacion con `escrituracion`
4. politicas de rollback
5. cobertura de tests

### 6.2 Integracion con `inmobiliario`

Debe definirse si el cierre real de `venta`:

1. reemplaza la `disponibilidad` `RESERVADA`
2. la cierra
3. la transfiere a otro estado operativo
4. delega completamente la resolucion a un contrato externo de `inmobiliario`

### 6.3 Politica de disponibilidad post-venta

Debe definirse formalmente la politica posterior a una `venta` cerrada:

1. si el objeto deja de estar `RESERVADA`
2. si pasa a un nuevo estado operativo
3. si requiere soporte adicional no materializado hoy en SQL
4. si la politica depende de escrituracion, entrega, cierre financiero u otro hito

## 7. Alcance de la version actual

La version actual del dominio `comercial`:

1. implementa el flujo `reserva -> venta -> condiciones -> confirmacion -> instrumento -> cesion -> escrituracion`
2. preserva la separacion semantica entre `comercial` e `inmobiliario`
3. no realiza cierre persistido de `venta`
4. no implementa estados write efectivos `cancelada`, `en_proceso` ni `finalizada` para `venta`
5. no ejecuta politica definitiva de `disponibilidad` post-venta
6. no modifica `ocupacion`

## 8. Base de verificacion

Esta decision se basa en:

1. `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
2. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-002-gestion-de-venta.md`
3. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-004-gestion-de-instrumentos-de-compraventa.md`
4. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-005-gestion-de-cesiones.md`
5. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-006-gestion-de-escrituracion.md`
6. `backend/documentacion/DEV-SRV/dominios/comercial/catalogos/RN-COM.md`
7. `backend/app/api/routers/comercial_router.py`
8. `backend/app/application/comercial/services/`
9. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
10. `backend/tests/`
11. `AGENTS.md`

## 9. Modelo resultante

El dominio `comercial` queda modelado en la version actual como una capa de registro, validacion y trazabilidad de eventos de negocio sobre la operacion comercial.

Ese modelo no asume responsabilidad sobre el estado fisico ni sobre el estado operativo del activo inmobiliario.
