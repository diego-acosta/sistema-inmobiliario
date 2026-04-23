# SRV-ANA-002 — Consulta analítica inmobiliaria

## Objetivo
Proveer una vista analítica consolidada del dominio inmobiliario, permitiendo consultar en forma resumida y agregada el estado de inmuebles, objetos inmobiliarios, unidades funcionales, disponibilidad, ocupación y condiciones relevantes del activo, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta consolidada del inventario inmobiliario
- métricas de disponibilidad y ocupación
- agregación por desarrollo, sucursal, zona o dimensión equivalente
- estados resumidos del activo
- soporte para paneles y reportes inmobiliarios

No incluye:
- alta, modificación o baja de inmuebles
- recalculo de estados write
- redefinición de disponibilidad u ocupación
- lógica contractual, comercial o financiera

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- desarrollo
- inmueble base / terreno según modelo legado
- unidad_funcional
- edificacion
- servicio
- disponibilidad
- ocupacion

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por desarrollo
- filtros por sucursal
- filtros por objeto inmobiliario
- filtros por disponibilidad
- filtros por ocupación
- filtros por estado del activo
- agrupación por dimensión inmobiliaria

## Resultado esperado
- cantidad total de inmuebles / objetos inmobiliarios
- cantidad total de unidades funcionales
- distribución por disponibilidad
- distribución por ocupación
- distribución por desarrollo, sucursal o zona
- indicadores resumidos del inventario inmobiliario
- vistas consolidadas aptas para reporting

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo inmobiliario a consultar
3. obtener información desde fuentes funcionales del dominio inmobiliario
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre disponibilidad y ocupación visibles
- no confusión entre estado actual y estado histórico

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no recalcula estados persistentes

## Dependencias

### Hacia dominios funcionales
- servicios de dominio inmobiliario
- disponibilidad y ocupación como fuentes de verdad del estado operativo
- lectura consolidada del maestro inmobiliario

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad de lectura cuando corresponda

## Reglas de arquitectura aplicadas
- no redefine la lógica del dominio inmobiliario
- no reemplaza la consulta operativa detallada de inmuebles
- consume información estructural ya definida por el dominio inmobiliario
- agrega, resume y consolida para fines analíticos

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- puede alimentar dashboards y reportes inmobiliarios
- no reemplaza consultas analíticas comercial, locativa o financiera

## Pendientes abiertos
- definición exacta de KPIs inmobiliarios mínimos
- definición de métricas estándar de vacancia / disponibilidad
- política de corte temporal para ocupación histórica
- estrategia de vistas materializadas o cache analítico
