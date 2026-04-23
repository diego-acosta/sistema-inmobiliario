# SRV-ANA-008 — Consulta de deuda

## Objetivo
Proveer una vista analítica consolidada del estado de deuda del sistema, permitiendo analizar deuda total, su distribución y su evolución, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta de deuda total del sistema
- distribución de deuda por dimensiones (sucursal, cliente, contrato, objeto)
- análisis de deuda por estado (vigente, vencida, en mora)
- composición de deuda (capital, intereses, punitorios cuando corresponda)
- soporte para análisis y reporting financiero

No incluye:
- cálculo primario de deuda
- cálculo de intereses
- generación de obligaciones
- modificación de estados financieros
- redefinición de mora o saldo

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada y analítica
- sin efectos transaccionales

## Entidades involucradas (referencial)
- obligacion_financiera
- composicion_obligacion
- obligacion_obligado
- relacion_generadora
- estado_financiero derivado del dominio financiero

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por sucursal
- filtros por cliente / persona
- filtros por relación generadora
- filtros por tipo de obligación
- filtros por estado de deuda
- agrupación por dimensión financiera

## Resultado esperado
- deuda total
- deuda por sucursal
- deuda por cliente
- deuda por contrato o relación
- deuda por estado (vigente, vencida, mora)
- composición de deuda (capital, intereses, punitorios)
- indicadores de distribución y concentración de deuda

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo financiero a analizar
3. obtener estados de deuda desde el dominio financiero
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas de deuda
6. agrupar por dimensiones
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre obligación y estado financiero
- no confusión entre deuda calculada y deuda analizada

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no recalcula lógica financiera primaria

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para:
  - saldo
  - deuda
  - mora
  - composición de obligación
- lecturas consolidadas del estado financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad

## Reglas de arquitectura aplicadas
- no recalcula intereses ni saldo como lógica primaria
- no reconstruye deuda desde movimientos
- consume estado financiero ya definido
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a SRV-ANA-005 como vista financiera detallada
- sirve como base para dashboards de deuda
- se articula con:
  - flujo financiero
  - cobranzas
  - mora

## Pendientes abiertos
- definición de métricas estándar de deuda
- definición de segmentaciones clave (riesgo, antigüedad)
- política de corte temporal para análisis histórico
- estrategia de optimización (materialización / cache)
