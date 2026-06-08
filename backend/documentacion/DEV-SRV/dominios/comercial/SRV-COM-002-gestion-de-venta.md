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

## Decision vigente: venta real, borrador de wizard y preview

### Venta real

La entidad `venta` representa una operacion comercial confirmada o ya formalmente existente. En el Wizard Venta Completa V3, la `venta` real no se persiste durante la carga del formulario: se crea recien al confirmar y, cuando se crea desde el wizard completo, nace en estado `confirmada`.

Estados principales de `venta` para el flujo Wizard Venta Completa V3:

- `confirmada`;
- `cancelada`;
- `finalizada`.

`borrador` no debe usarse como estado normal de `venta` para guardar progreso del Wizard Venta Completa V3. Si se conserva en contratos o flujos historicos, queda clasificado como compatibilidad heredada o pendiente de revision, no como modelo principal del wizard completo.

### Borrador de Wizard Venta Completa V3

Si el usuario necesita guardar progreso de carga, el concepto debe modelarse como una entidad separada, por ejemplo `borrador_venta_wizard`. Clasificacion: soporte UX/tecnico del flujo comercial; no es nucleo `venta` y no redefine la semantica de la venta real.

Uso conceptual de `borrador_venta_wizard`:

- guardar progreso de carga;
- retomar despues;
- descartar si no se concreta;
- convertirse en `venta` confirmada al finalizar.

Estados sugeridos:

- `en_carga`;
- `descartado`;
- `convertido`;
- `vencido`.

Restricciones:

- `borrador_venta_wizard` no es `venta`;
- no genera obligaciones;
- no genera Plan Pago V2 real;
- no cambia disponibilidad definitiva;
- no genera rescision;
- no debe confundirse con una `venta` `cancelada`.

### Preview previo a confirmacion

Preview Plan Pago V2 no crea `venta`, no genera obligaciones reales y no cambia estados comerciales. Su clasificacion CORE-EF es `PREVIEW_READLIKE`, por lo que no debe forzar headers write.

Para el Wizard Venta Completa V3 antes de confirmar, el endpoint objetivo debe ser sin `id_venta` porque la venta todavia no existe:

```text
POST /api/v1/ventas/plan-pago-v2/preview
```

Estado de implementacion: pendiente/no implementado en el router actual. El endpoint existente con `id_venta` en path pertenece a preview sobre una venta ya persistida y no debe usarse con IDs ficticios para el wizard antes de confirmar.

### Confirmacion de venta completa

Al confirmar una venta completa, el backend debe ejecutar la operacion compuesta correspondiente:

- crear `venta` en estado `confirmada`;
- crear objetos de venta;
- crear compradores;
- crear Plan Pago V2 real;
- generar obligaciones;
- actualizar disponibilidad/estado cuando corresponda.

## Modos del servicio

### Alta
Permite registrar una nueva operacion de venta.

Alcance implementado actual para alta derivada heredada:
- una `venta` puede generarse desde una `reserva_venta` `confirmada`
- en esa conversion heredada la `venta` nace en estado `borrador`
- la `venta` conserva referencia explicita a la reserva origen
- la conversion copia objetos y participaciones vigentes de la reserva
- la conversion no crea `ocupacion`
- la conversion no genera obligaciones financieras ni `relacion_generadora`
- este comportamiento no es el modelo principal del Wizard Venta Completa V3, donde la venta se persiste recien al confirmar y nace `confirmada`

### Integracion financiera V1

La confirmacion comercial emite `venta_confirmada`, pero no crea deuda por si misma.

El dominio financiero consume ese evento y materializa el plan financiero V1 definido en `venta`.

El comportamiento `CONTADO V1` materializa:

- una `relacion_generadora` con `tipo_origen = venta`
- una unica `obligacion_financiera` `CAPITAL_VENTA`
- importe igual a `venta.monto_total`
- `fecha_vencimiento = venta.fecha_venta`
- un `obligacion_obligado` para el comprador canonico `COMPRADOR` al 100%

El comportamiento `ANTICIPO_Y_SALDO V1` materializa una obligacion `ANTICIPO_VENTA` y una obligacion `CAPITAL_VENTA` para el saldo ordinario pactado. Comercial no define todavia cuotas, saldo extraordinario ni calendario financiero avanzado.

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
- revisar flujos historicos que conservan `venta.borrador` para separarlos del Wizard Venta Completa V3
- implementar, si se aprueba, `borrador_venta_wizard` con persistencia y contratos propios
- implementar, si se aprueba, `POST /api/v1/ventas/plan-pago-v2/preview` sin `id_venta` para preview previo a confirmacion
- definicion completa del ciclo de estados de venta fuera del Wizard Venta Completa V3
- reglas de cancelacion y reversion
- relacion exacta entre venta y condiciones comerciales
- integracion avanzada con el dominio financiero para cuotas y saldo extraordinario
- asignacion posterior de importes por objeto en `venta_objeto_inmobiliario`
