# SRV-ANA-004 — Consulta analítica locativa

## Objetivo
Proveer una vista analítica consolidada del dominio locativo, permitiendo consultar en forma resumida y agregada cartera locativa, reservas, contratos, condiciones económicas, ajustes, renovaciones, rescisiones, entregas y restituciones, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta consolidada de actividad locativa
- métricas de cartera locativa y contratos
- agregación por sucursal, desarrollo, objeto locativo o dimensión contractual
- estados resumidos del ciclo locativo
- soporte para paneles y reportes locativos

No incluye:
- alta, modificación o baja de contratos locativos
- gestión write de condiciones económicas
- reajustes write, renovaciones o rescisiones
- recalculo write de estados locativos

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- cartera_locativa
- solicitud_alquiler
- reserva_locativa
- contrato_alquiler
- contrato_objeto_locativo
- condicion_economica_alquiler
- ajuste_alquiler
- modificacion_locativa
- rescision_finalizacion_alquiler
- entrega_restitucion_inmueble

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por sucursal
- filtros por desarrollo
- filtros por contrato
- filtros por estado locativo
- filtros por objeto locativo
- agrupación por dimensión locativa o contractual

## Resultado esperado
- cantidad total de contratos
- cantidad total de reservas locativas
- distribución por estado locativo
- distribución por sucursal, desarrollo u objeto locativo
- indicadores resumidos de cartera locativa
- vistas consolidadas aptas para reporting locativo

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo locativo a consultar
3. obtener información desde fuentes funcionales del dominio locativo
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre contrato, condición económica y estado locativo cuando se proyecten en forma resumida
- no confusión entre estado actual y estado histórico

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no recalcula estados persistentes

## Dependencias

### Hacia dominios funcionales
- servicios de dominio locativo
- lectura consolidada de cartera locativa, reservas y contratos
- maestro inmobiliario como referencia del objeto locativo

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad de lectura cuando corresponda

## Reglas de arquitectura aplicadas
- no redefine la lógica del dominio locativo
- no reemplaza la consulta operativa detallada de contratos o reservas locativas
- consume información estructural ya definida por el dominio locativo
- agrega, resume y consolida para fines analíticos

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- se articula con la analítica inmobiliaria para explotar disponibilidad y ocupación del activo locativo
- puede alimentar dashboards y reportes locativos
- no reemplaza consultas analíticas comerciales ni financieras

## Pendientes abiertos
- definición exacta de KPIs locativos mínimos
- definición de métricas estándar de vacancia, ocupación y renovación
- política de corte temporal para cartera histórica
- estrategia de vistas materializadas o cache analítico
