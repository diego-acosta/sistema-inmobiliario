# SRV-COM-008 - Consulta y reporte comercial

## Objetivo

Proveer la capa de lectura operativa del dominio `comercial`, permitiendo consultar reservas, ventas y trazabilidad comercial asociada sin generar efectos persistentes.

## Alcance

Este servicio cubre hoy:

- detalle de `reserva_venta`
- listado de `reserva_venta`
- listado UI read-only de `venta`
- detalle enriquecido de `venta`
- detalle integral read-only de `venta`
- listado por `venta` de:
  - `instrumento_compraventa`
  - `cesion`
  - `escrituracion`
- lectura del estado de integracion `comercial -> inmobiliario` por `venta`
- lectura del estado financiero asociado a una `venta`, solo si ya existe `relacion_generadora`

No cubre en el `v1` vigente:

- reportes consolidados de actividad comercial
- busqueda avanzada multi-criterio fuera de los filtros ya materializados
- lectura propia de documental comercial
- detalle individual de `instrumento_compraventa`, `cesion` o `escrituracion`
- listados globales de `instrumento_compraventa`, `cesion` o `escrituracion`
- analitica o BI
- generacion de `relacion_generadora`
- generacion de obligaciones financieras
- recalculo de deuda, mora o punitorio
- plan financiero avanzado de venta
- rescision de venta
- cesion real con cambio de comprador

## Entidades principales

- `reserva_venta`
- `venta`
- `venta_objeto_inmobiliario`
- `instrumento_compraventa`
- `cesion`
- `escrituracion`
- `outbox_event` como soporte de observabilidad de integracion

## Modos del servicio

### Consulta operativa

Permite visualizar el estado actual de reservas y ventas ya registradas.

### Trazabilidad comercial

Permite reconstruir procedencia de la venta, objetos alcanzados y registros comerciales asociados.

### Observabilidad de integracion

Permite leer, por `venta`, el estado de los eventos emitidos hacia `inmobiliario` y su efecto contractual esperado.

### Consulta integral de venta

Permite consultar una `venta` con sus datos comerciales, partes, objetos, trazabilidad operativa y estado financiero asociado.

Esta consulta es estrictamente read-only:

- no crea ni modifica `venta`
- no crea ni modifica `relacion_generadora`
- no crea ni modifica `obligacion_financiera`
- no crea compradores ni obligados
- no crea `movimiento_financiero`, `aplicacion_financiera` ni `movimiento_tesoreria`
- no escribe `outbox_event` ni `inbox_event`
- no recalcula deuda
- no ejecuta mora ni punitorio
- no cambia estados

### Listado UI de venta

Permite localizar ventas para abrir la ficha integral, usando filtros operativos y una proyeccion compacta.

Filtros materializados:

- `q`
- `estado_venta`
- `id_persona`
- `rol_codigo`
- `id_inmueble`
- `id_unidad_funcional`
- `tipo_plan_financiero`
- `fecha_venta_desde`
- `fecha_venta_hasta`
- `con_saldo`
- `limit` (0..100; `0` es valido para consultar solo `total` sin items)
- `offset`

La proyeccion incluye compradores, objetos y resumen financiero solo como lectura de hechos persistidos. No genera relacion financiera, no genera obligaciones, no recalcula saldos, no ejecuta mora, no crea pagos y no escribe outbox ni inbox. `con_saldo=false` incluye ventas sin saldo pendiente positivo, tambien cuando no existe relacion generadora persistida. `rol_codigo` puede aplicarse sin `id_persona`. `cantidad_vencidas` usa el estado persistido `VENCIDA` y no calcula mora dinamica.

## Entradas conceptuales

### Parametros de consulta hoy materializados

- identificador de reserva
- filtros basicos de `reserva_venta`:
  - `codigo_reserva`
  - `estado_reserva`
  - `fecha_desde`
  - `fecha_hasta`
  - `vigente`
  - `limit`
  - `offset`
- identificador de venta
- filtros de listado UI de `venta`:
  - `q`
  - `estado_venta`
  - `id_persona`
  - `rol_codigo`
  - `id_inmueble`
  - `id_unidad_funcional`
  - `tipo_plan_financiero`
  - `fecha_venta_desde`
  - `fecha_venta_hasta`
  - `con_saldo`
  - `limit`
  - `offset`
- identificador de venta para detalle integral:
  - `GET /api/v1/ventas/{id_venta}/detalle-integral`
- filtros de `instrumento_compraventa` por venta:
  - `tipo_instrumento`
  - `estado_instrumento`
  - `fecha_desde`
  - `fecha_hasta`
- filtros de `cesion` por venta:
  - `tipo_cesion`
  - `fecha_desde`
  - `fecha_hasta`
- filtros de `escrituracion` por venta:
  - `fecha_desde`
  - `fecha_hasta`
  - `numero_escritura`

## Resultado esperado

- datos de reserva
- datos de venta
- objetos comerciales asociados
- origen de la venta desde `reserva_venta` cuando exista
- instrumentos, cesiones y escrituraciones asociados a una `venta`
- estado de integracion `comercial -> inmobiliario`
- partes comerciales desde `relacion_persona_rol`, `rol_participacion` y `persona`
- condiciones comerciales simples desde `venta.monto_total` y `venta_objeto_inmobiliario.precio_asignado`
- relacion financiera asociada cuando exista `relacion_generadora.tipo_origen = venta`
- obligaciones financieras asociadas a la relacion, con composiciones, conceptos y obligados si existen
- resumen financiero usando saldos persistidos
- resumen de lectura derivado de hechos persistidos

## Flujo de alto nivel

### Consulta

1. validar parametros de entrada
2. resolver la entidad o conjunto objetivo
3. cargar datos persistidos del dominio comercial
4. integrar objetos y relaciones asociadas
5. enriquecer con lecturas actuales de `inmobiliario` cuando corresponda
6. enriquecer con observabilidad de outbox cuando corresponda
7. para detalle integral, leer `relacion_generadora` y obligaciones asociadas solo como datos persistidos
8. devolver la proyeccion de lectura

## Validaciones clave

- consistencia de parametros de consulta
- existencia de la entidad objetivo cuando corresponda
- coherencia entre filtros aplicados
- caracter read-only de toda la operacion

## Efectos transaccionales

- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no registra inbox
- no crea relaciones generadoras ni obligaciones
- no recalcula saldos ni mora
- no requiere idempotencia write

## Errores

- [[ERR-COM]]

## Dependencias

### Hacia arriba

- existencia de informacion comercial registrada
- integridad del dominio comercial

### Hacia abajo

- `inmobiliario` como fuente read-only de `disponibilidad` y `ocupacion`
- `outbox_event` como fuente read-only de observabilidad de integracion

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
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- [[SRV-COM-004-gestion-de-instrumentos-de-compraventa]]
- [[SRV-COM-005-gestion-de-cesiones]]
- [[SRV-COM-006-gestion-de-escrituracion]]
- `DEV-API-COMERCIAL.md`
- DER comercial

## Pendientes abiertos

- definicion de listados globales de `venta`
- definicion de detalles individuales de recursos hijos
- criterios de busqueda avanzada
- limite futuro entre consulta operativa y analitica
- eventual incorporacion de documental comercial en lectura
