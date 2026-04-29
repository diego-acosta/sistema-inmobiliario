# SRV-ANA-011 — Consulta de mora

## Objetivo
Proveer una vista analítica consolidada de la mora del sistema, permitiendo analizar deuda vencida, mora acumulada, distribución de saldos morosos y su evolución temporal, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de mora total
- distribución de deuda vencida
- distribución de saldos morosos por dimensión
- evolución temporal de mora
- identificación resumida de sujetos o relaciones con mora
- soporte para reporting y dashboards financieros

No incluye:
- cálculo primario de mora
- generación de intereses punitorios
- actualización de saldos vencidos
- modificación de obligaciones o aplicaciones
- redefinición de reglas de atraso o punitorio

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada, distributiva y temporal
- sin efectos transaccionales

## Entidades involucradas (referencial)
- obligacion_financiera
- composicion_obligacion
- relacion_generadora
- movimiento_financiero cuando corresponda
- aplicacion_financiera cuando corresponda
- estado_financiero derivado del dominio financiero

## Entradas conceptuales
- fecha de corte
- filtros por sucursal
- filtros por cliente / persona / locatario
- filtros por relación generadora
- filtros por origen de relacion generadora o concepto financiero
- filtros por estado de mora
- agrupación temporal
- agrupación por dimensión financiera

## Resultado esperado
- mora total
- deuda vencida total
- mora por sucursal
- mora por cliente / persona / locatario
- mora por relación / contrato
- evolución temporal de la mora
- indicadores de concentración y distribución de mora

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar período y universo de análisis
3. obtener estados de mora desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por período y dimensiones
6. calcular métricas agregadas de mora
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de fechas
- consistencia entre obligación, vencimiento y estado de mora
- no doble conteo de saldos morosos
- coherencia entre deuda vencida y mora visible

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica obligaciones ni estados morosos

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para:
  - saldos vencidos
  - estado de mora
  - punitorios e intereses visibles cuando corresponda
- lecturas consolidadas del estado financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad

## Reglas de arquitectura aplicadas
- no recalcula mora como lógica financiera primaria
- no redefine reglas de vencimiento o punitorio
- consume estados financieros ya definidos
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de deuda
  - consulta de cobranzas
  - consulta de flujo financiero
- se articula con dashboards financieros y análisis de riesgo
- no reemplaza consultas operativas de obligaciones o ajustes financieros

## Pendientes abiertos
- definición de métricas estándar de mora
- definición de segmentación por antigüedad de atraso
- política de granularidad temporal
- estrategia de optimización (materialización / cache)
