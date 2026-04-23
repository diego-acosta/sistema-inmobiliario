# SRV-ANA-001 — Consulta general del sistema

## Objetivo
Proveer una vista consolidada y transversal del sistema, permitiendo consultar información resumida de múltiples dominios sin generar efectos persistentes.

## Alcance
Incluye:
- visión general del estado del sistema
- métricas resumidas por dominio
- indicadores globales
- soporte base para dashboards

No incluye:
- lógica de negocio
- cálculo financiero primario
- modificaciones de estado
- persistencia de datos

## Naturaleza del servicio
- tipo: query
- alcance: transversal
- granularidad: agregada
- sin efectos transaccionales

## Entidades involucradas (referencial)
- dominio inmobiliario (inmuebles, unidades, disponibilidad, ocupación)
- dominio comercial (ventas, reservas, instrumentos)
- dominio locativo (contratos, reservas, condiciones)
- dominio financiero (obligaciones, pagos, saldos)
- dominio documental (documentos, numeración)
- dominio administrativo (usuarios, sesiones, auditoría)
- dominio técnico (sincronización, operaciones)

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por dominio
- filtros por sucursal
- filtros por tipo de entidad

## Resultado esperado
- métricas globales del sistema
- resúmenes por dominio
- indicadores agregados
- estados consolidados

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar dominios involucrados
3. obtener datos desde fuentes funcionales
4. consolidar información
5. construir vista agregada
6. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal (fecha de corte)
- disponibilidad de datos

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones

## Dependencias

### Hacia dominios funcionales
- SRV-FIN (estado financiero)
- servicios de dominio inmobiliario
- servicios de dominio comercial
- servicios de dominio locativo
- servicios documentales

### Hacia infraestructura
- CORE-EF-001 (timestamps, versionado, trazabilidad)

## Reglas de arquitectura aplicadas
- no recalcula lógica financiera
- no redefine estados de negocio
- consume información existente
- agrega y consolida resultados

## Relación con otros servicios analíticos
Este servicio actúa como punto de entrada general.

Los servicios específicos:
- consulta analítica inmobiliaria
- consulta analítica comercial
- consulta analítica locativa
- consulta analítica financiera
- consultas financieras especializadas

proveen mayor nivel de detalle.

## Pendientes abiertos
- definición de métricas estándar
- definición de KPIs globales
- estrategia de optimización (vistas / cache)
- definición de estructura de respuesta para UI
