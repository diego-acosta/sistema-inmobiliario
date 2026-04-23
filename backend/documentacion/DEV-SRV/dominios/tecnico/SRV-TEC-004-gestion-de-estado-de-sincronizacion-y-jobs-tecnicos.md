# SRV-TEC-004 — Gestión de estado de sincronización y jobs técnicos

## Objetivo
Gestionar el estado técnico de sincronización y la ejecución de jobs técnicos del sistema, permitiendo registrar, ejecutar, reintentar, cancelar y consultar procesos técnicos, preservando consistencia, control operativo y trazabilidad.

## Alcance
Este servicio cubre:
- registro de jobs técnicos
- ejecución de jobs
- reintento de jobs fallidos
- cancelación de jobs cuando corresponda
- consulta de estado de sincronización
- mantenimiento de estado técnico agregado

No cubre:
- ejecución directa de lógica de negocio
- resolución de conflictos
- importación/exportación completa
- backup o restore

## Entidades principales
- job_tecnico
- estado_sincronizacion
- sincronizacion_operacion cuando corresponda
- sincronizacion_recepcion cuando corresponda

## Modos del servicio

### Registro de job
Permite registrar un job técnico a ejecutar.

### Ejecución
Permite ejecutar un job técnico.

### Reintento
Permite reintentar un job fallido.

### Cancelación
Permite cancelar un job cuando corresponda.

### Consulta
Permite visualizar estado de jobs y sincronización.

## Entradas conceptuales

### Contexto técnico (write)
- instalacion_id
- usuario_id cuando corresponda
- op_id cuando corresponda
- tipo_job
- prioridad cuando corresponda

### Datos de negocio
- tipo de job técnico
- parámetros de ejecución
- estado del job
- resultado de ejecución
- número de reintentos
- timestamps de ejecución
- observaciones técnicas

### Parámetros de consulta
- identificador de job
- tipo de job
- estado
- instalación
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de job
- estado del job
- resultado técnico
- número de reintentos
- timestamps
- errores estructurados cuando corresponda

### Para consulta
- listado de jobs técnicos
- estado de ejecución
- historial de ejecuciones
- estado agregado de sincronización
- trazabilidad técnica

## Flujo de alto nivel

### Registro
1. validar contexto técnico
2. validar tipo de job
3. registrar job técnico
4. persistir estado inicial
5. devolver resultado

### Ejecución
1. cargar job registrado
2. validar elegibilidad de ejecución
3. ejecutar lógica técnica asociada
4. actualizar estado del job
5. persistir resultado
6. devolver resultado

### Reintento
1. cargar job fallido
2. validar condiciones de reintento
3. ejecutar nuevamente
4. actualizar estado
5. persistir cambios
6. devolver resultado

### Cancelación
1. cargar job activo
2. validar cancelación
3. actualizar estado
4. persistir cambios
5. devolver resultado

### Consulta
1. validar parámetros
2. cargar jobs y estado de sincronización
3. consolidar información
4. devolver vista de lectura

## Validaciones clave
- consistencia de tipo de job
- coherencia de estados de ejecución
- control de reintentos
- no ejecución duplicada indebida
- integridad de estado técnico agregado
- trazabilidad por instalación y operación

## Efectos transaccionales
- alta o actualización de job_tecnico
- actualización de estado_sincronizacion
- registro de ejecuciones y reintentos
- mantenimiento de trazabilidad técnica

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- [[CORE-EF-001-infraestructura-transversal]]
- [[SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion]]
- [[SRV-TEC-003-gestion-de-conflictos-de-sincronizacion]]
- contexto técnico válido

### Hacia abajo
- [[SRV-TEC-005-gestion-de-importacion-y-exportacion-tecnica]]
- mantenimiento técnico del sistema
- monitoreo técnico

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-TECNICO]]
- [[CU-TEC]]
- [[RN-TEC]]
- [[ERR-TEC]]
- [[EVT-TEC]]
- [[EST-TEC]]
- [[CORE-EF-001-infraestructura-transversal]]

## Pendientes abiertos
- catálogo final de tipos de job
- estrategia de scheduling
- definición de prioridades
- política de reintentos
- integración con monitoreo externo
