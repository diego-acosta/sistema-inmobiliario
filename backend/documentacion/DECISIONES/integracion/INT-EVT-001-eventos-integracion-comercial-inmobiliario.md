# INT-EVT-001 - Eventos integracion comercial-inmobiliario

## 1. Contexto

La decision `INT-DEC-001` establece que la integracion entre `comercial` e `inmobiliario` debe modelarse como:

1. asincronica
2. basada en eventos de negocio
3. unidireccional desde `comercial` hacia `inmobiliario`
4. sin acoplamiento directo entre servicios

Dentro de ese contrato:

1. `comercial` emite eventos de negocio
2. `inmobiliario` consume esos eventos
3. `inmobiliario` decide y ejecuta cualquier cambio sobre `disponibilidad`
4. `comercial` no espera confirmacion sincrona ni resultado operativo para completar sus casos de uso

El presente documento define los eventos de integracion respaldados por el flujo comercial actualmente implementado y por las decisiones ya documentadas.

## 2. Criterio de definicion

Un evento de integracion entre `comercial` e `inmobiliario` solo puede definirse si:

1. representa un hito de negocio del dominio `comercial`
2. esta respaldado por un write real del flujo comercial
3. puede asociarse a objetos inmobiliarios concretos alcanzados por la operacion
4. no invade ownership operativo de `inmobiliario`

No se definen como eventos de integracion:

1. cambios tecnicos de fila
2. actualizaciones internas de metadatos
3. incrementos de `version_registro`
4. eventos de infraestructura

## 3. Eventos candidatos

Los eventos candidatos respaldados por el workspace actual son:

1. `venta_confirmada`
2. `escrituracion_registrada`

Existe ademas un candidato no definido en esta version:

1. evento externo de formalizacion legal o registral

Ese candidato no se formaliza aqui porque no existe contrato write materializado ni payload funcional definido en el backend actual.

## 4. Eventos definidos

### 4.1 `venta_confirmada`

#### Nombre

`venta_confirmada`

#### Cuando se emite

Se asocia al hito en que una `venta` alcanza `estado_venta = confirmada` por `PATCH /api/v1/ventas/{id_venta}/confirmar`.

La condicion de negocio exacta es:

1. `venta` existente y no dada de baja
2. `venta` en estado confirmable segun contrato actual
3. `venta` con condiciones comerciales completas
4. `venta` con objetos validos
5. confirmacion persistida exitosamente

#### Que representa

Representa que la operacion comercial de venta quedo confirmada dentro del dominio `comercial`.

Representa un hito de negocio suficientemente relevante para que `inmobiliario` evalúe si corresponde algun cambio posterior sobre el estado operativo del activo.

#### Que no representa

No representa:

1. cierre final de `venta`
2. cambio automatico de `disponibilidad`
3. cambio automatico de `ocupacion`
4. transferencia de ownership del activo
5. confirmacion de que `inmobiliario` ya proceso el cambio operativo

### 4.2 `escrituracion_registrada`

#### Nombre

`escrituracion_registrada`

#### Cuando se emite

Se asocia al hito en que una `escrituracion` queda registrada por `POST /api/v1/ventas/{id_venta}/escrituraciones`.

La condicion de negocio exacta es:

1. `venta` existente y no dada de baja
2. `venta` en estado comercial compatible con escrituracion segun implementacion vigente
3. sin `rescision_venta` conflictiva
4. sin otra `escrituracion` conflictiva
5. registracion persistida exitosamente

#### Que representa

Representa que la operacion comercial posee un hito documental y juridico de formalizacion registrado dentro de `comercial`.

Representa un evento de negocio posterior o complementario a la `venta`, relevante para que `inmobiliario` evalúe si corresponde un cambio operativo posterior.

#### Que no representa

No representa:

1. finalizacion persistida de `venta`
2. cambio automatico de `estado_venta`
3. cambio automatico de `disponibilidad`
4. cambio automatico de `ocupacion`
5. cierre legal total validado por procesos externos no materializados en el backend actual

## 5. Payload conceptual

El payload conceptual de un evento de integracion `comercial -> inmobiliario` debe contener solo informacion minima de negocio necesaria para que `inmobiliario` identifique la operacion y los objetos alcanzados.

Campos minimos conceptuales:

1. `nombre_evento`
2. `id_venta`
3. `id_reserva_venta` cuando exista relacion de origen y resulte relevante
4. `objetos`
5. `timestamp_del_hito`

El campo `objetos` debe permitir identificar cada activo involucrado mediante:

1. `id_inmueble`, o
2. `id_unidad_funcional`

Datos minimos adicionales potencialmente necesarios para `inmobiliario`:

1. estado comercial resultante de la `venta` cuando aplique
2. identificador del hito juridico cuando aplique, por ejemplo `id_escrituracion`
3. contexto tecnico minimo de trazabilidad cuando exista contrato transversal para ello

Este payload conceptual:

1. no define formato tecnico concreto
2. no define serializacion
3. no define canal de transporte
4. no define mecanismos de entrega o reintento

## 6. Reglas

### 6.1 Regla de negocio

Los eventos de integracion deben representar hitos de negocio del dominio `comercial`.

### 6.2 Regla de no tecnificacion

No deben emitirse eventos de integracion modelados como:

1. insercion de una fila
2. update de un campo tecnico
3. cambio de `version_registro`
4. confirmacion interna de persistencia

### 6.3 Regla de no automatismo

La definicion del evento no implica efecto automatico en `inmobiliario`.

La decision sobre `disponibilidad` sigue siendo responsabilidad de `inmobiliario`.

### 6.4 Regla de no implementacion

Este documento no define normativamente:

1. colas
2. broker
3. handlers
4. protocolos tecnicos de entrega

La implementacion tecnica vigente ya materializa `outbox_event`, publisher tecnico y consumidores locales en `inmobiliario`, pero esos detalles operativos quedan gobernados por `CORE-DEC-OUTBOX-001` e `INT-CONS-001`.

## 7. Eventos no definidos

No se definen aun los siguientes eventos por falta de contrato funcional suficiente en el workspace:

### 7.1 `venta_cerrada`

No se define porque no existe hoy cierre persistido de `venta` ni endpoint write materializado para `finalizada` o equivalente.

### 7.2 `venta_cancelada`

No se define porque no existe hoy cancelacion funcional implementada end-to-end para `venta`.

### 7.3 `venta_en_proceso`

No se define porque no existe hoy transicion write materializada hacia `en_proceso`.

### 7.4 Evento externo de registracion legal

No se define porque no existe en el backend actual un contrato funcional ni una fuente write propia que lo materialice dentro del dominio `comercial`.

## 8. Estado actual

En la version actual del workspace:

1. los eventos `venta_confirmada` y `escrituracion_registrada` quedan definidos a nivel contractual
2. la emision tecnica ya esta materializada mediante `outbox_event` transaccional en los writes de `confirmar venta` y `registrar escrituracion`
3. `venta_confirmada` ya tiene consumidor explicito e idempotente en `inmobiliario`, con efecto `NO_OP` sobre `disponibilidad` y `ocupacion`
4. `escrituracion_registrada` ya tiene consumidor materializado en `inmobiliario`, que reemplaza `RESERVADA -> NO_DISPONIBLE` y cierra inconsistencias permanentes en `REJECTED`
5. la observabilidad tecnica del cierre ya persiste `status`, `published_at`, `processing_reason` y `processing_metadata` en `outbox_event`

## 9. Base de verificacion

Esta decision se basa en:

1. `backend/documentacion/DECISIONES/comercial/COM-DEC-001-cierre-del-ciclo-de-vida-de-venta.md`
2. `backend/documentacion/DECISIONES/integracion/INT-DEC-001-integracion-comercial-inmobiliario.md`
3. `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
4. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-002-gestion-de-venta.md`
5. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-006-gestion-de-escrituracion.md`
6. `backend/app/api/routers/comercial_router.py`
7. `backend/app/application/comercial/services/`
8. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
9. `backend/tests/`
10. `AGENTS.md`
