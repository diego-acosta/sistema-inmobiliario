# SRV-ADM-004 — Gestión de auditoría

## Objetivo
Gestionar la auditoría del sistema, permitiendo registrar, consolidar y consultar eventos auditables asociados a usuarios, entidades, operaciones y decisiones administrativas, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- registro de eventos auditables
- consolidación de trazas administrativas
- consulta histórica de auditoría
- búsqueda por usuario, entidad, operación o contexto
- vinculación entre evento, actor y entidad afectada

No cubre:
- logging técnico de infraestructura
- monitoreo en tiempo real
- definición de permisos o autorizaciones
- analítica avanzada o BI

## Entidades principales
- auditoria_evento
- auditoria_contexto
- usuario
- entidad_auditada cuando corresponda

## Modos del servicio

### Registro
Permite registrar un evento auditable del sistema.

### Consolidación
Permite vincular o completar contexto de auditoría cuando corresponda.

### Consulta
Permite visualizar eventos de auditoría y su trazabilidad.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id cuando corresponda
- sucursal_id cuando corresponda
- instalacion_id cuando corresponda
- op_id
- timestamp técnico cuando corresponda

### Datos de negocio
- tipo de evento auditable
- entidad afectada
- identificador de la entidad
- usuario actor cuando corresponda
- acción ejecutada
- resultado de la acción
- motivo u observaciones
- contexto adicional cuando corresponda

### Parámetros de consulta
- tipo de evento
- usuario actor
- entidad afectada
- identificador de entidad
- op_id
- resultado
- rango de fechas
- contexto técnico

## Resultado esperado

### Para operaciones write
- identificador de evento de auditoría
- tipo de evento
- entidad afectada cuando corresponda
- usuario actor cuando corresponda
- resultado registrado
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de eventos auditables
- usuario actor
- entidad afectada
- acción ejecutada
- resultado
- contexto técnico
- trazabilidad histórica

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia cuando corresponda
2. validar consistencia mínima del evento
3. cargar entidad o usuario asociado cuando corresponda
4. registrar evento auditable
5. persistir con metadatos transversales
6. registrar outbox cuando corresponda
7. devolver resultado

### Consolidación
1. validar contexto técnico
2. cargar evento existente cuando corresponda
3. validar consistencia del contexto adicional
4. completar o vincular información de auditoría
5. persistir actualización
6. registrar outbox cuando corresponda
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar eventos de auditoría
3. resolver usuario, entidad y contexto asociado
4. devolver vista de lectura

## Validaciones clave
- coherencia del tipo de evento
- consistencia entre usuario, acción y entidad
- validez del contexto técnico asociado
- no duplicidad indebida cuando la política lo restrinja
- integridad de op_id cuando corresponda
- control de versionado si aplica
- idempotencia en registro cuando corresponda

## Efectos transaccionales
- alta o actualización de auditoria_evento
- alta o actualización de auditoria_contexto cuando corresponda
- vinculación con usuario y entidad auditada
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables cuando corresponda

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- usuarios existentes cuando corresponda
- entidades del sistema existentes cuando corresponda
- permisos sobre gestión administrativa

### Hacia abajo
- consulta administrativa consolidada
- cumplimiento interno
- investigación operativa
- trazabilidad transversal del sistema

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-ADMINISTRATIVO]]
- [[CU-ADM]]
- [[RN-ADM]]
- [[ERR-ADM]]
- [[EVT-ADM]]
- [[EST-ADM]]
- [[SRV-ADM-001-gestion-de-usuarios]]
- [[SRV-ADM-002-gestion-de-roles-y-permisos]]
- [[SRV-ADM-003-gestion-de-autorizaciones]]
- DER administrativo

## Pendientes abiertos
- catálogo final de eventos auditables
- nivel mínimo obligatorio de detalle por evento
- criterios de retención histórica
- integración con logging técnico
- políticas de consulta restringida por criticidad
