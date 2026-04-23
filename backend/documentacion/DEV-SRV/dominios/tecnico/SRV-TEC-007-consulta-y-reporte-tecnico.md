# SRV-TEC-007 — Consulta y reporte técnico

## Objetivo
Proveer una capa de lectura consolidada del dominio técnico, permitiendo consultar sincronización, operaciones distribuidas, conflictos, jobs técnicos, importación/exportación y respaldo, con trazabilidad completa, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de operaciones distribuidas
- consulta de sincronización
- consulta de conflictos
- consulta de jobs técnicos
- consulta de importación/exportación
- consulta de respaldo y recuperación
- trazabilidad técnica completa
- diagnóstico técnico del sistema

No cubre:
- ejecución de procesos técnicos
- modificación de estado del sistema
- monitoreo en tiempo real externo
- analítica avanzada o BI

## Entidades principales
- sync_outbox
- sync_inbox
- sincronizacion_operacion
- sincronizacion_recepcion
- conflicto_sincronizacion
- job_tecnico
- lote_tecnico
- respaldo_tecnico

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual del sistema técnico.

### Consulta histórica
Permite reconstruir la evolución técnica.

### Búsqueda
Permite localizar eventos técnicos por múltiples criterios.

### Reporte consolidado
Permite obtener una vista integrada del estado técnico.

## Entradas conceptuales

### Parámetros de consulta
- op_id
- uid_entidad
- tipo_entidad
- instalación
- estado técnico
- tipo de operación
- tipo de conflicto
- tipo de job
- tipo de lote
- rango de fechas
- criterios de búsqueda

## Resultado esperado

- operaciones distribuidas
- estados de sincronización
- conflictos
- jobs técnicos
- importaciones/exportaciones
- respaldos y recuperaciones
- estados técnicos
- trazabilidad completa
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros
2. resolver entidades objetivo
3. cargar operaciones distribuidas
4. integrar sincronización
5. integrar conflictos
6. integrar jobs técnicos
7. integrar importación/exportación
8. integrar respaldo y recuperación
9. consolidar vista
10. devolver resultado

## Validaciones clave
- consistencia de parámetros
- coherencia de filtros
- existencia de información técnica
- control de acceso a información técnica sensible

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- existencia de información técnica
- integridad del dominio técnico
- permisos de consulta

### Hacia abajo
- monitoreo del sistema
- diagnóstico operativo
- soporte técnico
- auditoría técnica

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-TECNICO]]
- [[CU-TEC]]
- [[RN-TEC]]
- [[ERR-TEC]]
- [[EVT-TEC]]
- [[EST-TEC]]
- [[SRV-TEC-001-aplicacion-transversal-de-core-ef-en-commands]]
- [[SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion]]
- [[SRV-TEC-003-gestion-de-conflictos-de-sincronizacion]]
- [[SRV-TEC-004-gestion-de-estado-de-sincronizacion-y-jobs-tecnicos]]
- [[SRV-TEC-005-gestion-de-importacion-y-exportacion-tecnica]]
- [[SRV-TEC-006-gestion-de-respaldo-recuperacion-e-integridad-tecnica]]
- [[CORE-EF-001-infraestructura-transversal]]

## Pendientes abiertos
- definición de reportes técnicos estándar
- criterios de diagnóstico automático
- integración con monitoreo externo
- límites entre consulta técnica y observabilidad
- políticas de acceso a información técnica crítica
