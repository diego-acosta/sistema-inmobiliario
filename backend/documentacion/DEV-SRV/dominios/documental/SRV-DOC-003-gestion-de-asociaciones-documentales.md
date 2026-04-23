# SRV-DOC-003 — Gestión de asociaciones documentales

## Objetivo
Gestionar asociaciones entre documentos y entidades del sistema, permitiendo su registro, modificación, baja lógica y consulta, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- registro de asociaciones documentales
- modificación de asociaciones
- baja lógica de asociaciones
- consulta de asociaciones
- vinculación de documentos con entidades del sistema

No cubre:
- gestión del contenido del documento
- versionado documental
- emisión documental
- lógica específica de negocio de cada dominio

## Entidades principales
- documento_asociacion
- documento_logico
- documento_version cuando corresponda

## Modos del servicio

### Registro
Permite asociar un documento a una entidad del sistema.

### Modificación
Permite actualizar una asociación existente.

### Baja lógica
Permite invalidar una asociación.

### Consulta
Permite visualizar asociaciones documentales.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de documento lógico o versión
- tipo de entidad asociada
- identificador de la entidad
- tipo de asociación
- estado
- vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de documento
- tipo de entidad
- identificador de entidad
- tipo de asociación
- estado

## Resultado esperado

### Para operaciones write
- identificador de asociación
- documento asociado
- entidad asociada
- tipo de asociación
- estado resultante
- vigencia cuando corresponda
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de asociaciones
- documento asociado
- entidad vinculada
- tipo de asociación
- estado
- vigencia

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar documento existente
3. validar entidad destino
4. validar consistencia de la asociación
5. registrar asociación documental
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar asociación existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar asociación
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar asociaciones
3. devolver vista de lectura

## Validaciones clave
- documento existente
- entidad destino existente
- coherencia del tipo de asociación
- no duplicidad indebida cuando corresponda
- consistencia de vigencias
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de documento_asociacion
- vinculación con documento_logico o documento_version
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- documento lógico o versión existente
- entidad del sistema existente
- contexto técnico válido
- permisos sobre gestión documental

### Hacia abajo
- consultas documentales
- trazabilidad de operaciones
- reportes del sistema

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-DOCUMENTAL]]
- [[CU-DOC]]
- [[RN-DOC]]
- [[ERR-DOC]]
- [[EVT-DOC]]
- [[EST-DOC]]
- [[SRV-DOC-001-gestion-de-documentos-logicos]]
- [[SRV-DOC-002-gestion-de-versionado-documental]]
- DER documental

## Pendientes abiertos
- catálogo final de tipos de asociación
- reglas de cardinalidad por tipo de entidad
- definición de asociaciones múltiples
- criterios de validez temporal
- integración con auditoría documental
