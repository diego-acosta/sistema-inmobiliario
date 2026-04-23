# SRV-TEC-001 — Aplicación transversal de CORE-EF en commands

## Objetivo
Aplicar de forma transversal los requisitos técnicos de CORE-EF sobre los commands de negocio del sistema, permitiendo ejecutar operaciones de escritura con contexto técnico consistente, control de versión, lock lógico cuando corresponda, idempotencia y persistencia coordinada de outbox, preservando integridad y trazabilidad.

## Alcance
Este servicio cubre:
- aplicación de contexto técnico mínimo a commands
- validación de versión esperada cuando corresponda
- validación y uso de lock lógico cuando corresponda
- aplicación de op_id como identidad de operación
- registro coordinado de outbox en la misma transacción
- control de idempotencia técnica en operaciones de escritura
- consulta del estado técnico de ejecución cuando corresponda

No cubre:
- lógica funcional específica de cada dominio
- sincronización remota completa
- resolución de conflictos de sincronización
- importación y exportación técnica
- backup, restore o integridad técnica profunda

## Entidades principales
- record_lock
- sync_outbox
- entidad_sincronizable cuando corresponda
- contexto_command_tecnico

## Modos del servicio

### Aplicación técnica de command
Permite ejecutar un command de negocio bajo reglas técnicas transversales consistentes.

### Validación de contexto
Permite validar precondiciones técnicas mínimas antes de ejecutar una mutación.

### Consulta técnica
Permite visualizar el resultado técnico asociado a una ejecución cuando corresponda.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id cuando corresponda
- instalacion_id
- op_id
- version_esperada cuando corresponda
- token_lock cuando corresponda
- tipo_entidad y uid_entidad cuando corresponda

### Datos de negocio
- command funcional a ejecutar
- entidad objetivo
- payload de cambio
- criticidad operativa cuando corresponda

### Parámetros de consulta
- op_id
- uid_entidad
- tipo_entidad
- resultado técnico
- rango de fechas cuando corresponda

## Resultado esperado

### Para operaciones write
- resultado funcional del command
- op_id aplicado
- versión resultante cuando corresponda
- estado técnico explícito
- registro de outbox cuando corresponda
- errores estructurados cuando corresponda

### Para consulta
- estado técnico de ejecución
- entidad afectada
- op_id
- resultado técnico
- trazabilidad mínima asociada

## Flujo de alto nivel

### Aplicación técnica de command
1. validar contexto técnico mínimo
2. cargar entidad objetivo cuando corresponda
3. validar lock lógico si aplica
4. validar versión esperada si aplica
5. validar idempotencia por op_id cuando corresponda
6. ejecutar validaciones funcionales del command
7. persistir cambio de negocio
8. actualizar metadatos transversales
9. registrar outbox en la misma transacción cuando corresponda
10. devolver resultado técnico explícito

### Consulta técnica
1. validar parámetros
2. cargar trazabilidad técnica disponible
3. devolver vista de lectura

## Validaciones clave
- existencia y consistencia de op_id
- presencia de contexto técnico requerido
- validez de versión esperada cuando aplique
- validez de lock lógico cuando aplique
- no sobrescritura silenciosa por conflicto de versión
- idempotencia técnica en operaciones repetidas
- acoplamiento transaccional entre cambio de negocio y outbox

## Efectos transaccionales
- actualización de metadatos transversales de entidades sincronizables
- validación y consumo de lock cuando corresponda
- persistencia de sync_outbox cuando corresponda
- registro técnico consistente con op_id
- reversión completa ante falla técnica o funcional bloqueante

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- [[CORE-EF-001-infraestructura-transversal]]
- existencia de commands de negocio consumidores
- contexto técnico válido
- permisos técnicos y funcionales cuando corresponda

### Hacia abajo
- [[SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion]]
- [[SRV-TEC-003-gestion-de-conflictos-de-sincronizacion]]
- todos los dominios command del sistema

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
- definición exacta del resultado técnico estándar de command
- criterio uniforme para obligatoriedad de lock por caso de uso
- formalización del contexto técnico común reutilizable
- política final de commands no sincronizables
- integración exacta con auditoría técnica y administrativa
