# SRV-COM-001 - Gestion de reserva de venta

## Objetivo
Gestionar la reserva de venta como instancia comercial previa a la formalizacion de la operacion, permitiendo registrar, modificar, cancelar, consultar y convertir reservas, preservando consistencia comercial y trazabilidad.

## Alcance
Este servicio cubre:
- alta de reserva de venta
- modificacion de reserva
- cancelacion de reserva
- vencimiento de reserva
- consulta de reserva
- conversion de reserva a venta
- vinculacion de personas y objetos inmobiliarios reservados
- control comercial basico de estado de reserva

No cubre:
- alta de venta definitiva
- definicion completa de condiciones comerciales de venta
- instrumentacion juridica de compraventa
- escrituracion
- generacion de deuda financiera
- documental comercial integral

## Entidades principales
- reserva_venta
- venta
- venta_objeto_inmobiliario
- disponibilidad
- persona

## Modos del servicio

### Alta
Permite registrar una nueva reserva de venta sobre uno o mas objetos inmobiliarios.

### Modificacion
Permite actualizar datos comerciales de una reserva vigente.

### Cancelacion
Permite invalidar o dejar sin efecto una reserva existente.

Alcance implementado actual:
- admite cancelacion funcional desde `borrador`, `activa` y `confirmada`
- `borrador -> cancelada` y `activa -> cancelada` no generan efectos operativos adicionales
- `confirmada -> cancelada` libera la disponibilidad previamente bloqueada
- la cancelacion no crea `ocupacion`
- la cancelacion no genera ni modifica `venta`
- nota de diseno pendiente: hoy la liberacion de una reserva `confirmada` se implementa materializando `RESERVADA -> DISPONIBLE`; queda pendiente cerrar si a futuro debe asumirse siempre `DISPONIBLE` o si corresponde restaurar o recalcular la disponibilidad efectiva del objeto.

### Vencimiento
Permite cerrar una reserva vigente por vencimiento funcional.

Alcance implementado actual:
- admite vencimiento funcional desde `activa` y `confirmada`
- `activa -> vencida` no genera efectos operativos adicionales
- `confirmada -> vencida` libera la disponibilidad previamente bloqueada
- el vencimiento no crea `ocupacion`
- el vencimiento no genera ni modifica `venta`
- nota de diseno pendiente: mientras no exista una politica mas rica de recomposicion de disponibilidad, la liberacion desde `confirmada -> vencida` sigue materializando `DISPONIBLE`.

### Conversion
Permite transformar una reserva valida en una operacion de venta.

Alcance implementado actual:
- la conversion aplica solo a `reserva_venta` en estado `confirmada`
- la conversion genera una `venta` inicial en estado `borrador`
- la conversion finaliza la reserva origen en estado `finalizada`
- la conversion preserva trazabilidad por `venta.id_reserva_venta`
- la conversion replica el detalle multiobjeto y las participaciones vigentes de la reserva hacia la venta
- la conversion no crea `ocupacion`
- la conversion no dispara logica financiera

### Consulta
Permite visualizar el estado y trazabilidad comercial de la reserva.

## Entradas conceptuales

### Contexto tecnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de reserva cuando corresponda
- persona o personas intervinientes
- objeto u objetos inmobiliarios reservados
- fecha de reserva
- estado de reserva
- vigencia o vencimiento cuando corresponda
- importe o sena cuando corresponda
- observaciones comerciales
- motivo de cancelacion cuando corresponda

### Parametros de consulta
- identificador de reserva
- persona interviniente
- objeto inmobiliario
- estado
- rango de fechas
- vigencia

## Resultado esperado

### Para operaciones write
- identificador de reserva
- estado resultante
- personas y objetos vinculados
- operacion de venta generada cuando corresponda
- version resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- datos de reserva
- estado comercial
- personas vinculadas
- objetos reservados
- trazabilidad hacia venta cuando exista

## Flujo de alto nivel

### Alta
1. validar contexto tecnico e idempotencia
2. cargar personas y objetos involucrados
3. validar disponibilidad comercial y elegibilidad de reserva
4. registrar reserva
5. actualizar estado operativo vinculado cuando corresponda
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificacion
1. validar contexto tecnico
2. cargar reserva existente
3. validar version esperada
4. validar modificabilidad segun estado
5. aplicar cambios
6. persistir actualizacion
7. registrar outbox
8. devolver resultado

### Cancelacion
1. validar contexto tecnico
2. cargar reserva existente
3. validar cancelabilidad
4. aplicar cancelacion
5. liberar disponibilidad bloqueada cuando la reserva estaba `confirmada`
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Vencimiento
1. validar contexto tecnico
2. cargar reserva existente
3. validar vencibilidad
4. aplicar vencimiento
5. liberar disponibilidad bloqueada cuando la reserva estaba `confirmada`
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Conversion
1. validar contexto tecnico
2. cargar reserva `confirmada`
3. validar elegibilidad para conversion, bloqueo operativo y coherencia multiobjeto
4. generar `venta` en estado `borrador`
5. materializar `venta_objeto_inmobiliario` y participaciones asociadas
6. finalizar reserva origen y vincular trazabilidad reserva -> venta
7. registrar outbox
8. devolver resultado

### Consulta
1. validar parametros
2. cargar reserva o conjunto de reservas
3. resolver personas, objetos y estado
4. devolver vista de lectura

## Validaciones clave
- personas intervinientes existentes
- objeto inmobiliario existente y reservable
- no superposicion indebida de reserva activa segun politica funcional
- consistencia de estado y vigencia
- modificabilidad y cancelabilidad segun estado
- elegibilidad para conversion a venta
- consistencia del bloqueo `RESERVADA` generado por una reserva `confirmada`
- no doble conversion de la misma reserva
- control de versionado
- idempotencia en operaciones write

## Efectos transaccionales
- alta o actualizacion de reserva_venta
- vinculacion con personas y objetos inmobiliarios
- actualizacion de disponibilidad operativa cuando corresponda
- generacion de venta cuando la reserva se convierte
- finalizacion atomica de la reserva origen cuando se concreta la conversion
- actualizacion de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- personas existentes
- objeto inmobiliario existente
- disponibilidad comercial compatible
- contexto tecnico valido
- permisos sobre gestion comercial

### Hacia abajo
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- [[SRV-COM-008-consulta-y-reporte-comercial]]
- dominio financiero cuando exista conversion con impacto posterior

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-PER-001-gestion-de-persona-base]]
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- DER comercial
- DER inmobiliario

## Pendientes abiertos
- tratamiento funcional de sena o anticipo asociado a reserva
- reglas de conversion parcial o multiple a venta
- definicion posterior de condiciones comerciales por objeto en la venta derivada
