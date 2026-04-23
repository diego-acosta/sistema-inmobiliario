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
- generacion de obligaciones financieras
- imputacion financiera
- disponibilidad u ocupacion
- instrumentacion legal de compraventa
- escrituracion

## Estado actual materializado
- el SQL vigente materializa las condiciones comerciales basicas en `venta.monto_total` y `venta_objeto_inmobiliario.precio_asignado`
- no existe hoy una tabla materializada `venta_condicion_comercial`
- no existe hoy una tabla materializada `esquema_financiamiento`
- por lo tanto, la implementacion actual del servicio debe operar sobre `venta` y su detalle multiobjeto ya persistido

## Entidades principales
- venta
- venta_objeto_inmobiliario

## Modos del servicio

### Definicion
Permite establecer las condiciones comerciales iniciales de una venta en `borrador`.

### Modificacion
Permite actualizar las condiciones comerciales basicas mientras la venta siga en estado compatible.

### Consulta
Permite visualizar `monto_total` y precios por objeto desde la propia `venta`.

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
- observaciones comerciales cuando corresponda

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

## Validaciones clave
- venta existente
- venta no eliminada
- venta en estado `borrador`
- lista completa de objetos vigentes, sin faltantes ni extras
- no duplicidad de objetos en request
- `precio_asignado > 0`
- suma exacta de `precio_asignado == monto_total`
- no modificacion indebida en estados no permitidos
- control de versionado
- coherencia multiobjeto persistida

## Efectos transaccionales
- actualizacion de `venta.monto_total`
- actualizacion de `venta_objeto_inmobiliario.precio_asignado` para todos los objetos de la venta
- actualizacion de metadatos transversales
- rollback completo si falla cualquier actualizacion parcial

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
- definicion exacta de esquemas de financiamiento
- reglas de modificacion segun estado de venta
- integracion completa con generacion de obligaciones
- tratamiento de moneda y ajustes
