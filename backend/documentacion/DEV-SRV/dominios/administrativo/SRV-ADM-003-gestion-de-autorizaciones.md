# SRV-ADM-003 — Gestión de autorizaciones

## Objetivo
Gestionar autorizaciones del sistema, permitiendo registrar solicitudes, aprobar, rechazar, revocar y consultar decisiones administrativas sobre operaciones sensibles, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- registro de solicitudes de autorización
- aprobación de autorizaciones
- rechazo de autorizaciones
- revocación de autorizaciones
- consulta de autorizaciones y su estado
- vinculación de autorizaciones con usuarios, roles, entidades o contextos

No cubre:
- autenticación técnica
- definición de roles y permisos
- auditoría administrativa global
- configuración general del sistema

## Entidades principales
- autorizacion
- solicitud_autorizacion
- usuario
- rol_administrativo cuando corresponda

## Modos del servicio

### Solicitud
Permite registrar una solicitud de autorización para una operación o contexto.

### Aprobación
Permite aprobar una autorización solicitada.

### Rechazo
Permite rechazar una solicitud de autorización.

### Revocación
Permite dejar sin efecto una autorización previamente concedida.

### Consulta
Permite visualizar autorizaciones, solicitudes y estados.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de autorización
- usuario solicitante
- usuario autorizante cuando corresponda
- rol o contexto aplicable cuando corresponda
- entidad u operación asociada cuando corresponda
- motivo de solicitud
- motivo de aprobación, rechazo o revocación
- estado
- vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de autorización
- usuario solicitante
- usuario autorizante
- tipo de autorización
- estado
- contexto o entidad asociada
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de autorización o solicitud
- usuarios involucrados
- tipo de autorización
- estado resultante
- vigencia cuando corresponda
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de autorizaciones
- solicitudes registradas
- usuarios involucrados
- estado
- vigencia
- contexto o entidad asociada

## Flujo de alto nivel

### Solicitud
1. validar contexto técnico e idempotencia
2. validar requerimiento de autorización
3. cargar usuarios y contexto asociado
4. registrar solicitud de autorización
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Aprobación
1. validar contexto técnico
2. cargar solicitud existente
3. validar elegibilidad del autorizante
4. aplicar aprobación
5. registrar vigencia y efectos cuando corresponda
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Rechazo
1. validar contexto técnico
2. cargar solicitud existente
3. validar elegibilidad del autorizante
4. aplicar rechazo
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Revocación
1. validar contexto técnico
2. cargar autorización vigente
3. validar condiciones de revocación
4. aplicar revocación
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar autorizaciones y solicitudes
3. devolver vista de lectura

## Validaciones clave
- usuario solicitante existente
- usuario autorizante válido cuando corresponda
- coherencia del tipo de autorización
- consistencia del contexto o entidad asociada
- no duplicidad indebida de autorizaciones vigentes cuando la política lo restrinja
- consistencia de vigencias
- control de versionado
- idempotencia en solicitud

## Efectos transaccionales
- alta o actualización de solicitud_autorizacion
- alta o actualización de autorizacion
- vinculación con usuario, rol, entidad o contexto cuando corresponda
- aplicación de borrado lógico o revocación cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- usuarios existentes
- roles y permisos definidos cuando corresponda
- contexto técnico válido
- permisos sobre gestión administrativa

### Hacia abajo
- [[SRV-ADM-004-gestion-de-auditoria]]
- procesos sensibles del sistema
- todos los dominios funcionales que requieran autorización explícita

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
- DER administrativo

## Pendientes abiertos
- catálogo final de tipos de autorización
- reglas de autorización por contexto
- definición de autorizaciones automáticas versus manuales
- políticas de revocación
- integración con workflows de aprobación
