# SRV-COM-002 - Gestion de venta

## Objetivo
Gestionar la operacion de venta como entidad comercial central, permitiendo registrar, modificar, cancelar, consultar y administrar su estado, preservando consistencia comercial y trazabilidad.

## Alcance
Este servicio cubre:
- alta de venta
- modificacion de venta
- cancelacion de venta
- gestion de estados de venta
- consulta de venta
- vinculacion de personas y objetos inmobiliarios
- integracion con reserva cuando corresponda

No cubre:
- definicion detallada de condiciones comerciales
- generacion de obligaciones financieras
- instrumentacion juridica de compraventa
- escrituracion
- gestion documental avanzada

## Entidades principales
- venta
- venta_objeto_inmobiliario
- reserva_venta
- persona

## Modos del servicio

### Alta
Permite registrar una nueva operacion de venta.

Alcance implementado actual para alta derivada:
- una `venta` puede generarse desde una `reserva_venta` `confirmada`
- en esa conversion la `venta` nace en estado `borrador`
- la `venta` conserva referencia explicita a la reserva origen
- la conversion copia objetos y participaciones vigentes de la reserva
- la conversion no crea `ocupacion`
- la conversion no genera obligaciones financieras ni `relacion_generadora`

### Modificacion
Permite actualizar datos comerciales de la venta.

### Cancelacion
Permite invalidar una venta segun condiciones funcionales.

### Gestion de estado
Permite avanzar o retroceder el estado de la venta segun reglas del proceso.

### Consulta
Permite visualizar la informacion y estado de la venta.

## Entradas conceptuales

### Contexto tecnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta cuando corresponda
- personas intervinientes (comprador, vendedor u otros)
- objetos inmobiliarios involucrados
- referencia a reserva cuando corresponda
- fecha de operacion
- estado de venta
- observaciones comerciales

### Parametros de consulta
- identificador de venta
- persona interviniente
- objeto inmobiliario
- estado de venta
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de venta
- estado resultante
- personas vinculadas
- objetos inmobiliarios asociados
- referencia a reserva cuando corresponda
- version resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- datos de venta
- estado de venta
- personas intervinientes
- objetos inmobiliarios
- trazabilidad con reserva cuando exista

## Flujo de alto nivel

### Alta
1. validar contexto tecnico e idempotencia
2. cargar personas y objetos
3. validar elegibilidad de venta
4. registrar venta
5. vincular con reserva si corresponde y finalizar la reserva origen si la venta se genero desde una `reserva_venta` `confirmada`
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificacion
1. validar contexto tecnico
2. cargar venta existente
3. validar version esperada
4. validar modificabilidad segun estado
5. aplicar cambios
6. persistir actualizacion
7. registrar outbox
8. devolver resultado

### Cancelacion
1. validar contexto tecnico
2. cargar venta
3. validar cancelabilidad
4. aplicar cancelacion
5. ajustar efectos operativos cuando corresponda
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Gestion de estado
1. validar contexto tecnico
2. cargar venta
3. validar transicion de estado
4. aplicar cambio de estado
5. persistir actualizacion
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parametros
2. cargar venta o conjunto de ventas
3. resolver relaciones con personas y objetos
4. devolver vista de lectura

## Validaciones clave
- personas intervinientes existentes
- objeto inmobiliario valido y disponible
- coherencia entre venta y reserva cuando exista
- consistencia de estado y transiciones
- no duplicidad indebida de venta activa sobre el mismo objeto cuando la politica lo restrinja
- no doble conversion de una misma `reserva_venta`
- consistencia del bloqueo operativo cuando la venta proviene de una reserva `confirmada`
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualizacion de venta
- vinculacion con objetos inmobiliarios
- vinculacion con personas intervinientes
- actualizacion de estado de reserva cuando corresponda
- preservacion del bloqueo de `disponibilidad` ya generado por una `reserva_venta` `confirmada` cuando la venta nace desde esa reserva
- actualizacion de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- personas existentes
- objeto inmobiliario existente
- disponibilidad compatible
- contexto tecnico valido
- permisos comerciales

### Hacia abajo
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- [[SRV-COM-004-gestion-de-instrumentos-de-compraventa]]
- [[SRV-COM-006-gestion-de-escrituracion]]
- dominio financiero para generacion posterior de obligaciones

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-COM-001-gestion-de-reserva-de-venta]]
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- DER comercial
- DER inmobiliario

## Pendientes abiertos
- definicion completa del ciclo de estados de venta
- reglas de cancelacion y reversion
- relacion exacta entre venta y condiciones comerciales
- integracion exacta con el dominio financiero
- asignacion posterior de importes por objeto en `venta_objeto_inmobiliario`
