# SRV-ANA-014 — Consulta de cancelaciones anticipadas

## Objetivo
Proveer una vista analítica consolidada de las cancelaciones anticipadas del sistema, permitiendo analizar obligaciones canceladas antes de su vencimiento, distribución de pagos asociados, impacto financiero y evolución temporal, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de cancelaciones anticipadas
- identificación de obligaciones canceladas antes del vencimiento
- distribución de montos asociados a cancelación anticipada
- análisis por sucursal, sujeto, relación o contrato
- evolución temporal de cancelaciones anticipadas
- soporte para reporting y dashboards financieros específicos

No incluye:
- registro de pagos
- imputación financiera write
- generación de bonificaciones o ajustes write
- recalculo financiero primario
- redefinición de reglas de cancelación anticipada
- reemplazo de cobranzas generales o deuda general

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada, distributiva y temporal
- sin efectos transaccionales

## Entidades involucradas (referencial)
- movimiento_financiero
- aplicacion_financiera
- obligacion_financiera
- composicion_obligacion cuando corresponda
- relacion_generadora
- estado_financiero derivado del dominio financiero

## Entradas conceptuales
- fecha de corte o rango de fechas
- filtros por sucursal
- filtros por cliente / persona / locatario
- filtros por relación generadora
- filtros por contrato o venta
- filtros por origen de relacion generadora o concepto financiero
- agrupación temporal
- agrupación por dimensión financiera

## Resultado esperado
- monto total de cancelaciones anticipadas
- cancelaciones anticipadas por período
- cancelaciones anticipadas por sucursal
- cancelaciones anticipadas por cliente / persona / locatario
- cancelaciones anticipadas por relación / contrato
- distribución por obligación o concepto cuando corresponda
- indicadores de concentración e impacto financiero

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar período y universo de análisis
3. obtener eventos de cancelación anticipada desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por período y dimensiones
6. calcular métricas agregadas de cancelación anticipada
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de fechas
- consistencia entre fecha de cancelación y fecha de vencimiento
- consistencia entre movimiento, aplicación y obligación cancelada
- no doble conteo de cancelaciones anticipadas
- coherencia entre cancelación anticipada y estado financiero visible

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica pagos, aplicaciones ni obligaciones

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para:
  - pagos y aplicaciones
  - obligaciones canceladas
  - condiciones de cancelación anticipada
  - impacto financiero visible
- lecturas consolidadas del estado financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, trazabilidad y consistencia temporal

## Reglas de arquitectura aplicadas
- no redefine la lógica de cancelación anticipada
- no recalcula pagos ni aplicaciones como lógica financiera primaria
- consume estados y relaciones ya definidos
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de cobranzas
  - consulta de deuda
  - consulta de saldos a fecha
- se articula con dashboards financieros y análisis específicos de comportamiento de pago
- no reemplaza consultas generales de cobranzas ni deuda

## Pendientes abiertos
- definición de métricas estándar de cancelación anticipada
- definición de segmentación por origen financiero, concepto financiero y sujeto
- política de granularidad temporal
- estrategia de optimización (materialización / cache)
