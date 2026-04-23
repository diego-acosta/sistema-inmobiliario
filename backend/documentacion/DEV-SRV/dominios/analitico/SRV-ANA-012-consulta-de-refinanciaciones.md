# SRV-ANA-012 — Consulta de refinanciaciones

## Objetivo
Proveer una vista analítica consolidada de las refinanciaciones del sistema, permitiendo analizar deuda refinanciada, reestructuraciones financieras, obligaciones originales y derivadas, y su evolución temporal, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de refinanciaciones realizadas
- distribución de deuda refinanciada
- identificación de obligaciones originales y derivadas
- evolución temporal de refinanciaciones
- agregación por dimensión financiera
- soporte para reporting y dashboards financieros

No incluye:
- generación de refinanciaciones
- modificación de obligaciones
- reestructuración write de deuda
- recalculo financiero primario
- redefinición de reglas de refinanciación

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada, distributiva y temporal
- sin efectos transaccionales

## Entidades involucradas (referencial)
- relacion_generadora
- obligacion_financiera
- refinanciacion / reformulacion cuando corresponda en el modelo
- movimiento_financiero cuando corresponda
- aplicacion_financiera cuando corresponda
- estado_financiero derivado del dominio financiero

## Entradas conceptuales
- fecha de corte
- filtros por sucursal
- filtros por cliente / persona / locatario
- filtros por relación generadora
- filtros por tipo o estado de refinanciación
- agrupación temporal
- agrupación por dimensión financiera

## Resultado esperado
- monto total refinanciado
- refinanciaciones por período
- refinanciaciones por sucursal
- refinanciaciones por cliente / persona / locatario
- refinanciaciones por relación / contrato
- indicadores de distribución y concentración de refinanciaciones
- vista resumida de obligaciones refinanciadas y derivadas

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar período y universo de análisis
3. obtener refinanciaciones y estados asociados desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por período y dimensiones
6. calcular métricas agregadas de refinanciación
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- coherencia de fechas
- consistencia entre obligación original, obligación derivada y relación generadora
- no doble conteo de deuda refinanciada
- coherencia entre refinanciación y saldo financiero visible

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica obligaciones ni reestructuraciones

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para:
  - refinanciaciones
  - obligaciones refinanciadas
  - relaciones generadoras afectadas
  - saldo refinanciado visible
- lecturas consolidadas del estado financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad

## Reglas de arquitectura aplicadas
- no reconstruye refinanciaciones como lógica financiera primaria
- no redefine la relación entre obligación original y derivada
- consume estados financieros ya definidos
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de deuda
  - consulta de mora
  - consulta de cobranzas
- se articula con dashboards financieros y análisis de reestructuración de cartera
- no reemplaza consultas operativas de obligación o reformulación

## Pendientes abiertos
- definición de métricas estándar de refinanciación
- definición de segmentación por tipo de reestructuración
- política de granularidad temporal
- estrategia de optimización (materialización / cache)
