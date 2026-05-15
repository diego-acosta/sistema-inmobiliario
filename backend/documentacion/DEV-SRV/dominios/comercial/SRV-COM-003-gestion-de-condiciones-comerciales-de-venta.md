# SRV-COM-003 - Gestion de condiciones comerciales de venta

## Objetivo
Gestionar las condiciones comerciales basicas de la venta hoy materializadas en SQL, permitiendo definir y ajustar `monto_total` y `precio_asignado` por objeto sin invadir financiero, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- definicion basica de condiciones comerciales de venta
- modificacion basica de condiciones comerciales
- consistencia entre `venta` y `venta_objeto_inmobiliario`

No cubre:
- alta de venta
- imputacion financiera
- disponibilidad u ocupacion
- instrumentacion legal de compraventa
- escrituracion
- pagos, caja, recibos o tesoreria
- mora, punitorios, indexacion o intereses

Excepcion implementada V2:
- `GeneratePlanPagoVentaCuotasIgualesSimpleService` genera el cronograma inicial
  `CUOTAS_IGUALES_SIMPLE` como plan comercial V2 y materializa obligaciones
  financieras `PROYECTADA` sin registrar pagos ni ejecutar deuda/mora.

## Estado actual materializado
- el SQL vigente materializa las condiciones comerciales basicas en `venta.monto_total`, `venta.moneda`, columnas minimas de plan financiero y `venta_objeto_inmobiliario.precio_asignado`
- no existe hoy una tabla materializada `venta_condicion_comercial`
- no existe hoy una tabla materializada `esquema_financiamiento`
- existe `venta_plan_cuota` como detalle comercial minimo para `CUOTAS_FIJAS V1`
- por lo tanto, la implementacion actual del servicio debe operar sobre `venta`, `venta_plan_cuota` y su detalle multiobjeto ya persistido
- existe `plan_pago_venta` como cabecera/regla comercial para planes V2
- existe `generacion_cronograma_financiero` como corrida tecnica/idempotente
  del cronograma financiero generado desde planes V2

Con estos datos, los planes financieros derivables formalmente en V1 son:

- `CONTADO`: una obligacion `CAPITAL_VENTA` por `venta.monto_total`, con vencimiento en `venta.fecha_venta`, materializada por financiero al procesar `venta_confirmada`.
- `ANTICIPO_Y_SALDO`: una obligacion `ANTICIPO_VENTA` por `venta.importe_anticipo` y una obligacion `CAPITAL_VENTA` por `venta.importe_saldo`.
- `CUOTAS_FIJAS`: N obligaciones `CAPITAL_VENTA`, una por cada cuota activa de `venta_plan_cuota`, con importe y vencimiento propios.

Saldo extraordinario o cualquier estructura distinta de las anteriores no deben inferirse desde texto libre ni desde campos incompletos. Requieren persistir datos comerciales minimos adicionales.

El plan V2 inicial materializado es:

- `CUOTAS_IGUALES_SIMPLE`: N obligaciones `PROYECTADA` con composicion
  `CAPITAL_VENTA`, una por cada cuota igual calculada desde `plan_pago_venta`,
  sin usar `venta_plan_cuota`.

## Entidades principales
- venta
- venta_objeto_inmobiliario
- venta_plan_cuota
- plan_pago_venta
- generacion_cronograma_financiero

## Modos del servicio

### Definicion
Permite establecer las condiciones comerciales iniciales de una venta en `borrador`.

### Modificacion
Permite actualizar las condiciones comerciales basicas mientras la venta siga en estado compatible.

### Consulta
Permite visualizar `monto_total` y precios por objeto desde la propia `venta`.

### Generacion V2 inicial
Permite generar el plan `CUOTAS_IGUALES_SIMPLE` desde una venta, dejando
persistida la regla comercial y el cronograma financiero proyectado.

## Entradas conceptuales

### Contexto tecnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta
- precio total
- lista completa de objetos de la venta con `precio_asignado`
- plan financiero: `CONTADO`, `ANTICIPO_Y_SALDO` o `CUOTAS_FIJAS`
- cuotas pactadas cuando el plan sea `CUOTAS_FIJAS`
- observaciones comerciales cuando corresponda

### Datos de negocio para `CUOTAS_IGUALES_SIMPLE V2`
- monto total del plan
- moneda
- cantidad de cuotas
- fecha del primer vencimiento
- periodicidad
- regla de redondeo

### Parametros de consulta
- identificador de venta

## Resultado esperado

### Para operaciones write
- venta asociada
- precio total definido
- precios por objeto definidos
- estado resultante
- version resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- condiciones comerciales vigentes leidas desde `venta`
- precio total
- precios por objeto

### Para `CUOTAS_IGUALES_SIMPLE V2`
- `plan_pago_venta` generado
- `generacion_cronograma_financiero` de la corrida
- `id_relacion_generadora`
- obligaciones financieras proyectadas generadas o recuperadas por idempotencia

## Flujo de alto nivel

### Definicion
1. validar contexto tecnico e idempotencia operativa
2. cargar venta existente
3. validar elegibilidad para definir condiciones sobre venta en `borrador`
4. validar que el request cubra el conjunto completo de objetos vigentes
5. validar que la suma de `precio_asignado` coincida con `monto_total`
6. persistir `monto_total` en `venta` y `precio_asignado` en todos los objetos
7. devolver resultado

### Modificacion
1. validar contexto tecnico
2. cargar venta y objetos existentes
3. validar version esperada
4. validar modificabilidad segun estado de venta
5. revalidar completitud y suma del detalle multiobjeto
6. persistir actualizacion transaccional
7. devolver resultado

### Consulta
1. validar parametros
2. cargar venta y su detalle de objetos
3. devolver vista de lectura

### Generacion `CUOTAS_IGUALES_SIMPLE V2`
1. validar request y contexto tecnico
2. cargar venta existente
3. verificar que no exista un plan vivo incompatible
4. persistir o reutilizar `plan_pago_venta` con metodo `CUOTAS_IGUALES_SIMPLE`
5. asegurar `relacion_generadora` de venta
6. persistir o reutilizar `generacion_cronograma_financiero`
7. resolver comprador financiero unico
8. calcular cuotas iguales y vencimientos mensuales
9. generar obligaciones financieras `PROYECTADA` idempotentes por cuota
10. crear composicion `CAPITAL_VENTA` y obligado `COMPRADOR`
11. marcar el plan como `GENERADO`
12. devolver plan, corrida y obligaciones

## Validaciones clave
- venta existente
- venta no eliminada
- venta en estado `borrador`
- lista completa de objetos vigentes, sin faltantes ni extras
- no duplicidad de objetos en request
- `precio_asignado > 0`
- suma exacta de `precio_asignado == monto_total`
- para `CUOTAS_FIJAS`, cuotas obligatorias, secuenciales desde 1, sin duplicados, con importes positivos, fechas obligatorias, moneda consistente y suma exacta de cuotas igual a `monto_total`
- no modificacion indebida en estados no permitidos
- control de versionado
- coherencia multiobjeto persistida

Validaciones de `CUOTAS_IGUALES_SIMPLE V2`:

- venta existente y no eliminada
- `monto_total_plan > 0`
- moneda requerida
- `cantidad_cuotas > 0`
- periodicidad unica soportada: `MENSUAL`
- regla de redondeo unica soportada: `ULTIMA_CUOTA`
- concepto financiero `CAPITAL_VENTA` existente
- comprador financiero unico resoluble
- plan vivo compatible o inexistente

Pendientes documentados:

- `monto_total_plan` y `moneda` no se validan estrictamente todavia contra
  `venta.monto_total` y `venta.moneda`
- `X-Op-Id` invalido se acepta y se ignora como UUID; requiere decision
  transversal de endurecimiento

## Efectos transaccionales
- actualizacion de `venta.monto_total`
- actualizacion de columnas minimas del plan financiero de `venta`
- reemplazo transaccional por soft delete de cuotas activas en `venta_plan_cuota`
- actualizacion de `venta_objeto_inmobiliario.precio_asignado` para todos los objetos de la venta
- actualizacion de metadatos transversales
- rollback completo si falla cualquier actualizacion parcial

Efectos transaccionales de `CUOTAS_IGUALES_SIMPLE V2`:

- upsert de `plan_pago_venta`
- upsert o reutilizacion de `relacion_generadora`
- alta o reutilizacion de `generacion_cronograma_financiero`
- alta idempotente de obligaciones financieras `PROYECTADA`
- alta de composicion `CAPITAL_VENTA`
- alta de obligado `COMPRADOR` al 100%
- no escribe `venta_plan_cuota`
- no registra pagos, recibos, caja ni tesoreria
- no crea aplicaciones financieras
- no ejecuta mora ni recalcula deuda

## Servicio implementado: GeneratePlanPagoVentaCuotasIgualesSimpleService

Ownership:

- comercial gobierna la venta y la regla comercial del plan en
  `plan_pago_venta`
- financiero gobierna la deuda/proyeccion mediante `relacion_generadora`,
  `generacion_cronograma_financiero`, `obligacion_financiera`,
  `composicion_obligacion` y `obligacion_obligado`
- el servicio comercial coordina la generacion inicial, pero no absorbe reglas
  de pagos, saldos, mora, caja ni recibos

Reglas de calculo:

- divide `monto_total_plan` por `cantidad_cuotas`
- redondea cada cuota a centavos con criterio decimal
- aplica `ULTIMA_CUOTA` para absorber la diferencia de redondeo y garantizar
  que la suma de cuotas sea exactamente `monto_total_plan`
- genera vencimientos mensuales desde `fecha_primer_vencimiento`
- si el dia del vencimiento no existe en un mes posterior, usa el ultimo dia de
  ese mes

Reglas de cronograma:

- cada cuota genera una obligacion `PROYECTADA`
- cada obligacion usa `fecha_emision = fecha_vencimiento` en la implementacion
  actual
- cada obligacion tiene `numero_obligacion` secuencial desde 1
- cada obligacion tiene `tipo_item_cronograma = CUOTA`
- cada obligacion tiene `etiqueta_obligacion = Cuota N`
- cada obligacion tiene `clave_funcional_origen =
  PLAN_PAGO_VENTA:{id_plan_pago_venta}:CUOTA:{N}`
- la composicion unica inicial es `CAPITAL_VENTA`
- el obligado inicial es el comprador unico de la venta, con
  `rol_obligado = COMPRADOR` y `porcentaje_responsabilidad = 100.00`

Idempotencia:

- la cabecera `plan_pago_venta` se reutiliza si el plan vivo es compatible
- la corrida tecnica usa `generacion_cronograma_financiero.clave_generacion`
- cada obligacion usa `clave_funcional_origen`
- la unicidad funcional efectiva es por `id_relacion_generadora` y
  `clave_funcional_origen` para obligaciones activas
- repetir el mismo request no debe duplicar obligaciones

Limitaciones V2 iniciales:

- soporta endpoints incrementales para `CUOTAS_IGUALES_SIMPLE` y
  `ANTICIPO_MAS_CUOTAS_IGUALES`
- no soporta todavia planes compuestos por bloques comerciales arbitrarios
- no soporta `CRONOGRAMA_DEFINIDO`
- no soporta indexacion
- no soporta interes financiero
- no soporta sistema frances ni aleman
- no soporta multiples compradores
- no reemplaza obligaciones con pagos o aplicaciones
- no confirma ni rescinde ventas
- no registra pagos ni recibos

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- venta existente y valida
- contexto tecnico valido

### Hacia abajo
- ninguna dependencia write obligatoria en el estado actual de implementacion

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-COM-002-gestion-de-venta]]
- DER comercial

## Pendientes abiertos
- definicion futura de si las condiciones comerciales deben materializarse en una entidad propia
- catalogo final de formas de pago
- reglas de modificacion segun estado de venta
- integracion completa con generacion de obligaciones para metodos distintos de `CUOTAS_IGUALES_SIMPLE V2`
- tratamiento de ajustes, intereses, indexacion, refinanciacion y cancelacion anticipada
