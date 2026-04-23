# SRV-ANA-003 — Consulta analítica comercial

## Objetivo
Proveer una vista analítica consolidada del dominio comercial, permitiendo consultar en forma resumida y agregada ventas, reservas, operaciones comerciales, instrumentos y estados de avance, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta consolidada de actividad comercial
- métricas de reservas y ventas
- agregación por sucursal, desarrollo, objeto inmobiliario o dimensión comercial
- estados resumidos de pipeline comercial
- soporte para paneles y reportes comerciales

No incluye:
- alta, modificación o baja de operaciones comerciales
- lógica jurídica o contractual detallada
- generación de obligaciones financieras
- recalculo write de estados comerciales

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- reserva_venta
- venta
- venta_objeto_inmobiliario
- instrumento_compraventa
- instrumento_objeto_inmobiliario
- cesion
- escrituracion
- rescision_venta

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por sucursal
- filtros por desarrollo
- filtros por operación comercial
- filtros por estado comercial
- filtros por objeto inmobiliario
- agrupación por dimensión comercial

## Resultado esperado
- cantidad total de reservas
- cantidad total de ventas
- distribución por estado comercial
- distribución por sucursal, desarrollo u objeto
- indicadores resumidos de pipeline comercial
- vistas consolidadas aptas para reporting comercial

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo comercial a consultar
3. obtener información desde fuentes funcionales del dominio comercial
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre reserva, venta e instrumento cuando se proyecten en forma resumida
- no confusión entre estado actual y estado histórico

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no recalcula estados persistentes

## Dependencias

### Hacia dominios funcionales
- servicios de dominio comercial
- lectura consolidada de reservas, ventas e instrumentos
- maestro inmobiliario como referencia del objeto comercializado

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad de lectura cuando corresponda

## Reglas de arquitectura aplicadas
- no redefine la lógica del dominio comercial
- no reemplaza la consulta operativa detallada de ventas o reservas
- consume información estructural ya definida por el dominio comercial
- agrega, resume y consolida para fines analíticos

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- se articula con la analítica inmobiliaria para explotar activos comercializados
- puede alimentar dashboards y reportes comerciales
- no reemplaza consultas analíticas locativas ni financieras

## Pendientes abiertos
- definición exacta de KPIs comerciales mínimos
- definición de métricas estándar de conversión reserva → venta
- política de corte temporal para pipeline histórico
- estrategia de vistas materializadas o cache analítico
