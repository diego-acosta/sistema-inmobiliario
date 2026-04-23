# SRV-TEC-003 — Gestión de conflictos de sincronización

## Objetivo
Gestionar conflictos derivados de operaciones distribuidas, permitiendo su detección, registro, clasificación, resolución y consulta, preservando consistencia, integridad y trazabilidad técnica.

## Alcance
Este servicio cubre:
- detección de conflictos durante sincronización
- registro de conflictos técnicos
- clasificación por tipo y criticidad
- resolución de conflictos
- consulta de conflictos y su estado
- trazabilidad de decisiones de resolución

No cubre:
- ejecución de sincronización en sí misma
- lógica funcional de negocio
- importación/exportación técnica completa
- auditoría administrativa global

## Entidades principales
- conflicto_sincronizacion
- sincronizacion_operacion
- sincronizacion_recepcion
- entidad_sincronizable cuando corresponda

## Modos del servicio

### Detección
Permite identificar conflictos durante la aplicación de operaciones remotas.

### Registro
Permite persistir un conflicto técnico con toda su información.

### Clasificación
Permite categorizar conflictos por tipo, criticidad y estado.

### Resolución
Permite resolver conflictos mediante decisiones técnicas o manuales.

### Consulta
Permite visualizar conflictos y su trazabilidad.

## Entradas conceptuales

### Contexto técnico (write)
- op_id
- uid_entidad
- tipo_entidad
- instalacion_origen
- instalacion_destino
- version_local
- version_remota
- payload_local cuando corresponda
- payload_remoto cuando corresponda

### Datos de negocio
- tipo de conflicto
- causa detectada
- nivel de criticidad
- estado del conflicto
- acción de resolución
- usuario resolutor cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de conflicto
- tipo de conflicto
- estado
- criticidad
- entidad afectada
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de conflicto
- entidad afectada
- tipo de conflicto
- estado resultante
- acción aplicada
- op_id asociado
- errores estructurados cuando corresponda

### Para consulta
- listado de conflictos
- estado
- tipo
- criticidad
- entidad afectada
- historial de resolución
- trazabilidad técnica

## Flujo de alto nivel

### Detección y registro
1. detectar inconsistencia durante aplicación remota
2. validar que corresponde a conflicto técnico
3. clasificar tipo preliminar de conflicto
4. registrar conflicto con contexto completo
5. persistir información técnica
6. devolver resultado

### Clasificación
1. cargar conflicto registrado
2. validar información técnica disponible
3. asignar tipo definitivo y criticidad
4. actualizar estado
5. persistir cambios
6. devolver resultado

### Resolución
1. validar contexto técnico
2. cargar conflicto existente
3. validar elegibilidad de resolución
4. aplicar estrategia de resolución
5. actualizar estado y resultado
6. persistir cambios
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar conflictos registrados
3. resolver trazabilidad
4. devolver vista de lectura

## Validaciones clave
- consistencia entre versión local y remota
- integridad de payload técnico
- coherencia del tipo de conflicto
- no duplicidad indebida de conflictos
- consistencia de estado de conflicto
- trazabilidad completa por op_id y entidad
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de conflicto_sincronizacion
- vinculación con operaciones distribuidas
- actualización de estado de resolución
- preservación de histórico de decisiones
- mantenimiento de integridad técnica

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- [[CORE-EF-001-infraestructura-transversal]]
- [[SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion]]
- existencia de operaciones remotas procesadas
- contexto técnico válido

### Hacia abajo
- [[SRV-TEC-004-gestion-de-estado-de-sincronizacion-y-jobs-tecnicos]]
- todos los dominios sincronizables

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-TECNICO]]
- [[CU-TEC]]
- [[RN-TEC]]
- [[ERR-TEC]]
- [[EVT-TEC]]
- [[EST-TEC]]
- [[SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion]]
- [[CORE-EF-001-infraestructura-transversal]]

## Pendientes abiertos
- catálogo definitivo de tipos de conflicto
- políticas automáticas vs manuales de resolución
- criterios de priorización por criticidad
- integración con auditoría
- impacto de resolución en estado global del sistema
