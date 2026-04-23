# INT-DEC-001 - Integracion comercial-inmobiliario

## 1. Contexto

El dominio `comercial` registra y valida eventos de negocio sobre operaciones de compraventa.

En la version actual del backend, ese registro incluye:

1. `reserva_venta`
2. `venta`
3. `instrumento_compraventa`
4. `cesion`
5. `escrituracion`

El dominio `inmobiliario` gobierna el estado operativo de los activos, incluyendo:

1. `disponibilidad`
2. `ocupacion`

La integracion vigente entre ambos dominios es parcial y especifica:

1. `comercial` consulta `disponibilidad` y `ocupacion` para validar elegibilidad
2. `comercial` reemplaza `disponibilidad` solo en operaciones de `reserva_venta` ya explicitamente documentadas e implementadas
3. cuando una `venta` nace desde una `reserva_venta` `confirmada`, la `disponibilidad` del activo queda en `RESERVADA`
4. esa `disponibilidad` `RESERVADA` no se modifica automaticamente en el flujo posterior de `venta`

La decision `COM-DEC-001` establece que el ciclo actual de `venta` queda modelado como registro de eventos comerciales y juridicos, sin cierre persistido de `venta` ni politica final de disponibilidad post-venta.

## 2. Problema

No esta definido en el workspace cuando debe cambiar la `disponibilidad` del activo despues de:

1. `confirmacion` de `venta`
2. `escrituracion`
3. otro hito posterior de cierre

Tampoco existe hoy un contrato formal entre `comercial` e `inmobiliario` que establezca:

1. evento disparador
2. responsable de decidir el nuevo estado operativo
3. forma de integracion
4. garantias de consistencia interdominio

Como resultado, el ultimo estado operativo conocido del activo dentro del flujo comercial permanece en `RESERVADA` cuando la `venta` proviene de una `reserva_venta` `confirmada`.

## 3. Principios

### 3.1 Ownership

`inmobiliario` es el owner de `disponibilidad`.

`inmobiliario` es el owner de `ocupacion`.

### 3.2 Restriccion de mutacion

`comercial` no debe modificar `disponibilidad` directamente fuera de los contratos write ya implementados y documentados para `reserva_venta`.

`comercial` no debe crear, cerrar ni reinterpretar `ocupacion`.

### 3.3 Integracion explicita

Cualquier cambio de `disponibilidad` posterior a una `venta` debe ejecutarse mediante integracion explicita entre dominios.

No se admite inferencia implicita basada solo en la existencia de `venta`, `instrumento_compraventa`, `cesion` o `escrituracion`.

### 3.4 Fuente de verdad

El contrato de integracion debe surgir de:

1. ownership arquitectonico
2. contratos API documentados
3. servicios de dominio documentados
4. SQL materializado
5. codigo y tests existentes

Si un disparador o estado final no esta definido en esas fuentes, debe quedar explicitamente como no definido.

## 4. Tipo de integracion

La integracion entre `comercial` e `inmobiliario` se define arquitectonicamente como asincronica.

La integracion se basa en eventos de dominio.

La integracion no implica acoplamiento directo entre servicios de ambos dominios.

Dentro de este contrato, `comercial` emite eventos y `inmobiliario` los consume.

Los eventos de integracion deben entenderse como eventos de negocio y no como eventos tecnicos.

Esos eventos representan hitos del dominio comercial, por ejemplo:

1. `venta` confirmada
2. `escrituracion` registrada

Los eventos de integracion no deben modelarse como simples cambios de fila ni como señales tecnicas de persistencia.

El dominio `comercial` no depende de la ejecucion ni del resultado del dominio `inmobiliario` para completar sus casos de uso propios.

La integracion es unidireccional: `comercial -> inmobiliario`.

`comercial` no espera respuesta sincrona ni confirmacion operativa de `inmobiliario` para completar sus operaciones write.

No existe garantia de consistencia inmediata entre `comercial` e `inmobiliario`.

El estado del activo inmobiliario puede reflejar cambios con demora respecto de los eventos comerciales emitidos.

## 5. Eventos potencialmente disparadores

Los siguientes eventos pueden analizarse como posibles disparadores de cambios en `disponibilidad`, pero el workspace actual no los fija como automatismos obligatorios:

### 5.1 Confirmacion de venta

`DEV-API` de `confirmar venta` indica que el backend puede requerir cierre o reemplazo de `disponibilidad` vigente en `inmobiliario` para los objetos alcanzados.

Esa posibilidad existe a nivel documental, pero no esta materializada en la implementacion actual.

### 5.2 Escrituracion

`DEV-API` de `escrituracion` indica que cualquier ajuste de `disponibilidad` posterior a la escrituracion debe resolverse por integracion con `inmobiliario`.

Esto reconoce a `escrituracion` como posible hito de integracion, pero no define politica automatica ni estado resultante.

### 5.3 Evento externo

`SRV-COM-006` admite dependencias con procesos legales externos y registracion de outbox en operaciones sincronizables.

Por lo tanto, un evento externo de formalizacion juridica o registral puede ser un disparador plausible a futuro, pero no existe hoy un contrato implementado que lo materialice.

## 6. Decisiones vigentes

### 6.1 No existe cambio automatico de disponibilidad post-venta

En la version actual del workspace no se define ningun cambio automatico de `disponibilidad` disparado por:

1. `confirmacion` de `venta`
2. `instrumento_compraventa`
3. `cesion`
4. `escrituracion`

### 6.2 Los unicos efectos write vigentes sobre disponibilidad son los de reserva

Los efectos implementados y respaldados hoy sobre `disponibilidad` son:

1. `confirmacion` de `reserva_venta` -> reemplazo a `RESERVADA`
2. `cancelacion` de `reserva_venta` confirmada -> reemplazo a `DISPONIBLE`
3. `vencimiento` de `reserva_venta` confirmada -> reemplazo a `DISPONIBLE`

Fuera de esos contratos, no existe write vigente que altere automaticamente `disponibilidad`.

### 6.3 Los disparadores futuros quedan abiertos

Los eventos que pueden potencialmente disparar una integracion futura con `inmobiliario` son:

1. `confirmacion` de `venta`
2. `escrituracion`
3. evento externo de formalizacion legal o registral

El workspace actual no decide cual de ellos debe ser el disparador definitivo ni si debe existir mas de uno.

## 7. Modelo de integracion

### 7.1 Naturaleza del contrato

La integracion entre `comercial` e `inmobiliario` para resolver `disponibilidad` post-venta debe considerarse un contrato interdominio explicito.

Ese contrato no forma parte del ownership local de `comercial`.

### 7.2 Modalidad del contrato

La documentacion de servicios write de `comercial` referencia:

1. `outbox`
2. operaciones sincronizables
3. `CORE-EF`

Ese marco resulta compatible con una integracion asincronica y event-driven entre dominios.

### 7.3 Estado de implementacion

Aunque el contrato arquitectonico se define como asincronico y event-driven, el workspace actual no implementa todavia un mecanismo interdominio materializado para cambiar `disponibilidad` post-venta.

Por lo tanto:

1. no se define implementacion sincrona vigente
2. no se define implementacion asincronica vigente
3. solo se define la necesidad de una integracion explicita futura

## 8. Estado actual

En la implementacion actual:

1. la `disponibilidad` permanece en `RESERVADA` cuando la `venta` proviene de una `reserva_venta` previamente `confirmada`
2. no existe automatismo de liberacion, cierre o reemplazo de `disponibilidad` por `confirmacion` de `venta`
3. no existe automatismo de liberacion, cierre o reemplazo de `disponibilidad` por `escrituracion`
4. `comercial` sigue validando contra `disponibilidad` y `ocupacion`, pero no asume ownership operativo sobre esos recursos

La permanencia en `RESERVADA` no debe interpretarse como estado final del activo.

Ese estado permanece asi hasta que un proceso externo, definido por `inmobiliario` o por una integracion posterior, determine su actualizacion.

## 9. Pendientes

### 9.1 Estado final del activo

Debe definirse el estado operativo final del activo luego del cierre real de la operacion.

Eso incluye determinar si el activo debe quedar:

1. `RESERVADA`
2. `NO_DISPONIBLE`
3. en un nuevo estado operativo no materializado hoy
4. en un estado recalculado por `inmobiliario`

### 9.2 Integracion con escrituracion

Debe definirse si `escrituracion` es:

1. un hito meramente documental
2. el disparador formal de cambio operativo
3. una condicion necesaria pero no suficiente
4. un evento que requiere validacion adicional externa

### 9.3 Intervencion de otros dominios

Debe definirse si el cierre operativo final requiere coordinacion adicional con:

1. `financiero`
2. procesos legales externos
3. otros dominios o soportes transversales

## 10. Responsabilidad de cada dominio

### 10.1 Comercial

`comercial`:

1. emite eventos de negocio
2. valida consistencia comercial
3. registra hitos comerciales y juridicos de la operacion

### 10.2 Inmobiliario

`inmobiliario`:

1. decide cambios sobre `disponibilidad`
2. ejecuta cambios sobre `disponibilidad`
3. gobierna el estado operativo del activo

## 11. Base de verificacion

Esta decision se basa en:

1. `backend/documentacion/DECISIONES/comercial/COM-DEC-001-cierre-del-ciclo-de-vida-de-venta.md`
2. `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
3. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-002-gestion-de-venta.md`
4. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-006-gestion-de-escrituracion.md`
5. `backend/documentacion/DEV-SRV/dominios/comercial/catalogos/RN-COM.md`
6. `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`
7. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
8. `backend/tests/`
9. `AGENTS.md`
