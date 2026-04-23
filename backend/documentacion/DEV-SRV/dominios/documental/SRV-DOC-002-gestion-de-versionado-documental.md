# SRV-DOC-002 — Gestión de versionado documental

## Objetivo
Gestionar versiones documentales asociadas a documentos lógicos, permitiendo registrar, actualizar, invalidar y consultar revisiones sucesivas, preservando consistencia, historización y trazabilidad.

## Alcance
Este servicio cubre:
- generación de nuevas versiones documentales
- actualización de metadatos de versión
- invalidación de versiones
- consulta de versiones vigentes e históricas
- control de secuencia y trazabilidad de versiones

No cubre:
- alta de documento lógico base
- emisión formal de documentos
- asociaciones documentales con entidades
- almacenamiento físico o binario
- lógica específica de negocio por dominio

## Entidades principales
- documento_version
- documento_logico

## Modos del servicio

### Generación
Permite registrar una nueva versión de un documento lógico existente.

### Modificación
Permite actualizar metadatos o estado de una versión.

### Invalidación
Permite dejar sin efecto una versión documental.

### Consulta
Permite visualizar versiones vigentes e históricas de un documento lógico.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de documento lógico
- número o secuencia de versión cuando corresponda
- estado de la versión
- metadatos de versión
- fecha o vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de documento lógico
- número de versión
- estado
- vigencia
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de versión documental
- documento lógico asociado
- número o secuencia de versión
- estado resultante
- vigencia cuando corresponda
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de versiones
- secuencia de versiones
- estado
- vigencia
- trazabilidad histórica

## Flujo de alto nivel

### Generación
1. validar contexto técnico e idempotencia
2. cargar documento lógico existente
3. validar elegibilidad para nueva versión
4. registrar nueva versión documental
5. cerrar o ajustar vigencia anterior cuando corresponda
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar versión existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Invalidación
1. validar contexto técnico
2. cargar versión documental
3. validar anulabilidad
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar versiones documentales
3. resolver secuencia histórica
4. devolver vista de lectura

## Validaciones clave
- documento lógico existente
- consistencia de secuencia de versiones
- no duplicidad indebida de versión activa cuando la política lo restrinja
- coherencia de estado y vigencia
- control de versionado
- idempotencia en generación

## Efectos transaccionales
- alta o actualización de documento_version
- vinculación con documento_logico
- cierre o ajuste de vigencias anteriores cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- documento lógico existente
- contexto técnico válido
- permisos sobre gestión documental

### Hacia abajo
- [[SRV-DOC-003-gestion-de-asociaciones-documentales]]
- [[SRV-DOC-005-gestion-de-emision-y-numeracion-documental]]
- consulta documental consolidada

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
- DER documental

## Pendientes abiertos
- política exacta de numeración de versiones
- definición de versión vigente versus histórica
- criterios de reemplazo e invalidación
- integración con almacenamiento físico
- reglas de edición sobre versiones emitidas
