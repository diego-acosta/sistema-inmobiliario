# SRV-ANA-013 — Consulta de saldos a fecha

## Objetivo
Proveer una vista analítica consolidada de saldos financieros a fecha, permitiendo analizar saldos correctos al corte para obligaciones, relaciones, sujetos y universos agregados, sin generar efectos persistentes.

## Alcance
Incluye:
- análisis de saldos financieros a fecha
- distribución de saldos al corte por dimensión
- comparación de saldos entre fechas cuando corresponda
- agregación por sucursal, relación, sujeto, origen financiero o concepto financiero
- soporte para reporting y dashboards temporales

No incluye:
- recalculo financiero primario write
- generación de obligaciones
- modificación de saldos persistidos
- reparación de inconsistencias históricas
- redefinición de reglas de saldo o imputación

## Naturaleza del servicio
- tipo: query
- alcance: analítica financiera especializada
- granularidad: agregada, temporal y comparativa
- sin efectos transaccionales

## Entidades involucradas (referencial)
- obligacion_financiera
- composicion_obligacion
- obligacion_obligado
- relacion_generadora
- movimiento_financiero cuando corresponda
- aplicacion_financiera cuando corresponda
- estado_financiero a fecha derivado del dominio financiero

## Entradas conceptuales
- fecha de corte (obligatoria)
- fecha de comparación cuando corresponda
- filtros por sucursal
- filtros por cliente / persona / locatario
- filtros por relación generadora
- filtros por origen financiero, concepto financiero o estado de obligación
- agrupación por dimensión financiera

## Resultado esperado
- saldo total a fecha
- saldos a fecha por sucursal
- saldos a fecha por cliente / persona / locatario
- saldos a fecha por relación / contrato
- composición de saldo a fecha cuando corresponda
- comparación entre saldos de distintas fechas
- indicadores de distribución y concentración de saldos al corte

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar fecha de corte y universo de análisis
3. obtener saldos a fecha desde el dominio financiero
4. aplicar filtros y segmentaciones
5. agrupar por dimensiones
6. calcular métricas agregadas al corte
7. construir vista analítica
8. devolver resultado

## Validaciones clave
- presencia y validez de la fecha de corte
- coherencia entre fecha de corte y filtros
- consistencia entre obligación, movimiento, aplicación y saldo visible al corte
- no doble conteo de saldos
- coherencia entre saldo actual y saldo histórico cuando exista comparación

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica saldos persistidos
- no repara inconsistencias por efecto lateral

## Dependencias

### Hacia dominio financiero
- SRV-FIN como fuente de verdad para:
  - saldo actual
  - saldo a fecha
  - composición del saldo
  - relaciones entre obligación, movimientos y aplicaciones
- lecturas o read models temporales derivados del dominio financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, trazabilidad temporal y consistencia de lectura al corte

## Reglas de arquitectura aplicadas
- no reconstruye saldos como lógica financiera primaria
- no redefine reglas de imputación o saldo
- consume semántica de saldo a fecha ya definida por SRV-FIN
- agrega y analiza la información
- no reemplaza SRV-FIN

## Relación con otros servicios analíticos
- complementa a:
  - consulta de deuda
  - consulta de mora
  - consulta de refinanciaciones
- se articula con análisis históricos y comparativos
- no reemplaza consultas operativas de saldo por entidad individual

## Pendientes abiertos
- definición de métricas estándar de saldo a fecha
- definición de comparación entre cortes temporales
- política de reconstrucción histórica completa vs aproximación permitida
- estrategia de optimización (materialización / cache temporal)
