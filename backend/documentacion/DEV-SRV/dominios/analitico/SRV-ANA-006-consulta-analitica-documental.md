# SRV-ANA-006 — Consulta analítica documental

## Objetivo
Proveer una vista analítica consolidada del dominio documental, permitiendo consultar en forma resumida y agregada documentos, numeración, estados documentales, trazabilidad y actividad documental del sistema, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta consolidada de documentos emitidos
- métricas de numeración documental
- distribución por tipo documental
- estados documentales resumidos
- trazabilidad documental agregada
- soporte para paneles y reportes documentales

No incluye:
- generación de documentos
- asignación de numeración write
- modificación de estados documentales
- validaciones jurídicas o de negocio específicas
- lógica financiera o comercial asociada al documento

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- documento
- tipo_documental
- numeracion_documental
- estado_documental
- historial_documental
- vinculación documental con entidades de otros dominios

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por tipo documental
- filtros por estado documental
- filtros por sucursal
- filtros por entidad vinculada (comercial, locativa, financiera, etc.)
- agrupación por dimensión documental

## Resultado esperado
- cantidad total de documentos
- distribución por tipo documental
- distribución por estado documental
- numeración emitida por período
- indicadores de actividad documental
- vistas consolidadas aptas para reporting documental

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo documental a consultar
3. obtener información desde fuentes funcionales del dominio documental
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre tipo documental y estado
- no confusión entre estado actual y estado histórico

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica estados documentales

## Dependencias

### Hacia dominios funcionales
- servicios del dominio documental
- numeración y estados como fuente de verdad
- relaciones con dominios comercial, locativo y financiero para contexto

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad de lectura cuando corresponda

## Reglas de arquitectura aplicadas
- no redefine la lógica del dominio documental
- no reemplaza la consulta operativa de documentos
- consume información estructural ya definida por el dominio documental
- agrega, resume y consolida para fines analíticos

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- se articula con dominios comercial, locativo y financiero como soporte documental
- puede alimentar dashboards y reportes documentales
- no reemplaza consultas analíticas financieras, comerciales o locativas

## Pendientes abiertos
- definición exacta de KPIs documentales mínimos
- definición de métricas estándar de emisión y estados documentales
- política de corte temporal para trazabilidad histórica
- estrategia de vistas materializadas o cache analítico
