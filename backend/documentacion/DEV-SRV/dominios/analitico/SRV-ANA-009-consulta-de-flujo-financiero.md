# SRV-ANA-009 — Consulta de flujo financiero

## Objetivo
Proveer una vista analítica consolidada del flujo financiero del sistema, permitiendo analizar ingresos, egresos, comportamiento temporal del flujo de dinero y su distribución, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de ingresos
- análisis de egresos
- flujo neto
- distribución de movimientos por período
- evolución temporal del flujo financiero
- soporte para reporting y dashboards financieros

No incluye:
- registro de movimientos
- ejecución de pagos
- imputación financiera
- generación de obligaciones
- recalculo financiero primario

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada y temporal
- sin efectos transaccionales

## Entidades involucradas (referencial)
- movimiento_financiero
- aplicacion_financiera
- cuenta_financiera
- movimiento_tesoreria
- relacion_generadora como contexto

## Entradas conceptuales
- rango de fechas (obligatorio en la mayoría de los casos)
- filtros por sucursal
- filtros por cuenta financiera
- filtros por tipo de movimiento
- filtros por relación generadora
- agrupación temporal (día, mes, año)
- agrupación por dimensión financiera

## Resultado esperado
- total de ingresos
- total de egresos
- flujo neto
- flujo por período
- distribución por sucursal
- distribución por cuenta o tipo de movimiento
- evolución del flujo en el tiempo

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar período de análisis
3. obtener movimientos financieros desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por período y dimensiones
6. calcular métricas agregadas (ingresos, egresos, neto)
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de fechas
- consistencia entre movimientos y aplicaciones
- no doble conteo de flujo
- coherencia entre ingreso, egreso y neto

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica movimientos financieros

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para movimientos y aplicaciones
- lecturas consolidadas del flujo financiero
- estados de cuentas financieras

### Hacia infraestructura
- CORE-EF-001 para timestamps, trazabilidad y consistencia temporal

## Reglas de arquitectura aplicadas
- no redefine lógica de movimiento financiero
- no reconstruye flujo desde operaciones básicas como fuente primaria
- consume movimientos ya registrados
- agrega y analiza el flujo
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de deuda (estado)
  - consulta de cobranzas (ingresos aplicados)
- se articula con análisis temporal y dashboards financieros
- no reemplaza consultas operativas financieras

## Pendientes abiertos
- definición de métricas estándar de flujo
- definición de segmentación de ingresos y egresos
- política de granularidad temporal
- estrategia de optimización (materialización / cache)
