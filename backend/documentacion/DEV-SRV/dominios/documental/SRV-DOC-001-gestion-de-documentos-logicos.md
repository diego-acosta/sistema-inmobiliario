# SRV-DOC-001 — Gestión de documentos lógicos

## Objetivo
Gestionar documentos lógicos del sistema como representación abstracta de documentos, permitiendo su alta, modificación, invalidación y consulta, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- alta de documento lógico
- modificación de metadatos
- invalidación de documento
- consulta de documentos lógicos
- centralización de metadatos documentales

No cubre:
- almacenamiento de archivos físicos
- versionado documental detallado
- emisión formal de documentos
- lógica específica de documentos por dominio

## Entidades principales
- documento_logico

## Modos del servicio

### Alta
Permite registrar un nuevo documento lógico.

### Modificación
Permite actualizar metadatos del documento.

### Invalidación
Permite dejar sin efecto un documento lógico.

### Consulta
Permite visualizar documentos lógicos.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de documento
- nombre o identificador
- estado
- metadatos generales
- observaciones

### Parámetros de consulta
- tipo de documento
- estado
- identificador
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de documento lógico
- tipo de documento
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de documentos
- tipo
- estado
- metadatos

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos del documento
3. registrar documento lógico
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar documento existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Invalidación
1. validar contexto técnico
2. cargar documento
3. validar anulabilidad
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar documentos
3. devolver vista de lectura

## Validaciones clave
- consistencia de tipo documental
- coherencia de estado
- no duplicidad indebida cuando corresponda
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de documento_logico
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión documental

### Hacia abajo
- [[SRV-DOC-002-gestion-de-versionado-documental]]
- [[SRV-DOC-003-gestion-de-asociaciones-documentales]]
- [[SRV-DOC-005-gestion-de-emision-y-numeracion-documental]]

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-DOCUMENTAL]]
- [[CU-DOC]]
- [[RN-DOC]]
- [[ERR-DOC]]
- [[EVT-DOC]]
- [[EST-DOC]]
- DER documental

## Pendientes abiertos
- catálogo final de tipos documentales
- definición de metadatos estándar
- relación con almacenamiento físico
- criterios de unicidad documental
- políticas de invalidación
