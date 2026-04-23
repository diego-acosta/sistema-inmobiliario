# SRV-ANA-010 — Consulta de cobranzas

## Objetivo
Proveer una vista analítica consolidada de las cobranzas del sistema, permitiendo analizar montos cobrados, su distribución, su evolución temporal y su composición, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de montos cobrados
- distribución de cobranzas por período
- distribución por sucursal, cliente, contrato o relación
- composición de cobranzas por tipo o concepto
- evolución temporal de cobranzas
- soporte para reporting y dashboards financieros

No incluye:
- registro de pagos
- imputación financiera write
- generación de deuda
- recalculo financiero primario
- modificación de movimientos o aplicaciones

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada, distributiva y temporal
- sin efectos transaccionales

## Entidades involucradas (referencial)
- movimiento_financiero
- aplicacion_financiera
- obligacion_financiera
- relacion_generadora
- cuenta_financiera cuando corresponda
- caja / contexto operativo cuando corresponda por lectura

## Entradas conceptuales
- rango de fechas
- filtros por sucursal
- filtros por cliente / persona / locatario
- filtros por relación generadora
- filtros por contrato o venta
- filtros por tipo de cobranza
- agrupación temporal
- agrupación por dimensión financiera u operativa

## Resultado esperado
- total cobrado
- cobranzas por período
- cobranzas por sucursal
- cobranzas por cliente / persona / locatario
- cobranzas por contrato / relación
- composición de cobranzas por tipo o concepto
- evolución temporal de cobranzas

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar período y universo de análisis
3. obtener pagos y aplicaciones desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por período y dimensiones
6. calcular métricas agregadas de cobranzas
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de fechas
- consistencia entre movimientos, aplicaciones y obligaciones
- no doble conteo de cobranzas
- coherencia entre monto cobrado y distribución aplicada

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica pagos ni aplicaciones

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para pagos, cobranzas y aplicaciones
- lecturas consolidadas del estado de pago
- relaciones entre movimientos y obligaciones

### Hacia infraestructura
- CORE-EF-001 para timestamps, trazabilidad y consistencia temporal

## Reglas de arquitectura aplicadas
- no redefine la lógica de cobranzas
- no recalcula pagos ni aplicaciones como fuente primaria
- consume movimientos y aplicaciones ya definidos
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de flujo financiero
  - consulta de deuda
  - consulta de mora
- se articula con dashboards financieros y análisis operativo de cobros
- no reemplaza consultas operativas de pago o aplicación

## Pendientes abiertos
- definición de métricas estándar de cobranzas
- definición de segmentación clave por canal o criterio operativo
- política de granularidad temporal
- estrategia de optimización (materialización / cache)
