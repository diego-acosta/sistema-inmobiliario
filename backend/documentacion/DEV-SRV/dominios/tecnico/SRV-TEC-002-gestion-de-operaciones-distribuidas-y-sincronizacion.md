# SRV-TEC-002 — Gestión de operaciones distribuidas y sincronización

## Objetivo
Gestionar operaciones distribuidas y sincronización entre instalaciones, permitiendo preparar, emitir, recibir, aplicar y consultar cambios sincronizables de forma controlada, preservando consistencia técnica, idempotencia y trazabilidad.

## Alcance
Este servicio cubre:
- preparación de operaciones distribuibles
- emisión de cambios locales sincronizables
- recepción de cambios remotos
- aplicación controlada de operaciones remotas
- clasificación de resultados de sincronización
- consulta de estado y trazabilidad de sincronización

No cubre:
- lógica funcional de commands de negocio
- resolución manual o avanzada de conflictos
- importación/exportación técnica por lotes complejos
- respaldo, recuperación o integridad técnica profunda

## Entidades principales
- sync_outbox
- sync_inbox
- sincronizacion_operacion
- sincronizacion_recepcion
- entidad_sincronizable cuando corresponda

## Modos del servicio

### Preparación y emisión
Permite tomar operaciones locales sincronizables y dejarlas listas para envío o marcarlas como emitidas.

### Recepción
Permite registrar la llegada de una operación remota.

### Aplicación controlada
Permite procesar una operación remota y clasificar su resultado técnico.

### Consulta técnica
Permite visualizar estado de operaciones distribuidas y su trazabilidad.

## Entradas conceptuales

### Contexto técnico (write)
- instalacion_id_origen
- instalacion_id_destino cuando corresponda
- op_id
- uid_entidad
- tipo_entidad
- version_registro
- payload técnico
- hash de payload cuando corresponda
- timestamp técnico cuando corresponda

### Datos de negocio
- tipo_evento distribuido
- operación sincronizable origen
- estado técnico esperado
- relación con entidad afectada
- observaciones técnicas

### Parámetros de consulta
- op_id
- uid_entidad
- tipo_entidad
- instalación origen
- instalación destino
- estado técnico
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de operación distribuida o recepción
- op_id procesado
- estado técnico resultante
- clasificación de resultado (aplicada, duplicada, rechazada, conflicto, etc.)
- entidad afectada cuando corresponda
- errores estructurados cuando corresponda

### Para consulta
- operaciones distribuidas emitidas
- recepciones registradas
- estado técnico de sincronización
- trazabilidad por entidad y op_id
- resultados de aplicación

## Flujo de alto nivel

### Preparación y emisión
1. validar contexto técnico de operación distribuible
2. cargar registro técnico local cuando corresponda
3. validar elegibilidad de emisión
4. preparar operación para sincronización
5. registrar o actualizar estado de outbox
6. persistir cambios técnicos
7. devolver resultado

### Recepción
1. validar contexto técnico de recepción
2. verificar estructura mínima de la operación remota
3. registrar recepción técnica
4. persistir entrada en inbox o estructura equivalente
5. devolver resultado

### Aplicación controlada
1. cargar operación remota recibida
2. verificar idempotencia por op_id
3. clasificar si aplica, duplica, rechaza o entra en conflicto
4. aplicar cambio remoto cuando corresponda
5. actualizar estado técnico final
6. persistir resultado en transacción controlada
7. devolver resultado

### Consulta técnica
1. validar parámetros
2. cargar operaciones y recepciones técnicas
3. resolver trazabilidad por op_id y entidad
4. devolver vista de lectura

## Validaciones clave
- presencia y validez de op_id
- consistencia de uid_entidad y tipo_entidad
- idempotencia de recepción y aplicación
- coherencia de version_registro cuando corresponda
- integridad mínima del payload técnico
- no reprocesamiento indebido de operaciones ya aplicadas
- clasificación explícita de duplicado, rechazo o conflicto

## Efectos transaccionales
- alta o actualización de sync_outbox
- alta o actualización de sync_inbox
- registro de sincronizacion_operacion y sincronizacion_recepcion cuando corresponda
- actualización de estados técnicos de emisión y recepción
- aplicación de cambios remotos cuando corresponda
- trazabilidad consistente por op_id y entidad

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- [[CORE-EF-001-infraestructura-transversal]]
- existencia de operaciones sincronizables generadas por commands de negocio
- contexto técnico válido
- instalaciones técnicas válidas cuando corresponda

### Hacia abajo
- [[SRV-TEC-003-gestion-de-conflictos-de-sincronizacion]]
- [[SRV-TEC-004-gestion-de-estado-de-sincronizacion-y-jobs-tecnicos]]
- todos los dominios sincronizables del sistema

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
- [[CORE-EF-001-infraestructura-transversal]]

## Pendientes abiertos
- definición exacta de estados técnicos de operación distribuida
- criterio final de segmentación por destino o alcance
- relación formal entre paquete técnico y operación individual
- política de reintentos de emisión y reprocesamiento
- estrategia exacta de payload técnico portable
