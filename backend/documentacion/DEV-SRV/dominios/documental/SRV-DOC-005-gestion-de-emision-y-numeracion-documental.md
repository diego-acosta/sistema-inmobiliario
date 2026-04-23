# SRV-DOC-005 — Gestión de emisión y numeración documental

## Objetivo
Gestionar la emisión formal de documentos del sistema, permitiendo asignar numeración, registrar salidas documentales, invalidar emisiones y consultar resultados, preservando consistencia, unicidad y trazabilidad.

## Alcance
Este servicio cubre:
- emisión de documentos
- asignación de numeración cuando corresponda
- registro de salida documental
- invalidación de emisiones
- consulta de emisiones
- vinculación entre documento lógico, versión y plantilla

No cubre:
- definición del contenido del documento
- gestión de condiciones de negocio
- versionado documental
- asociaciones documentales
- almacenamiento físico

## Entidades principales
- emision_documental
- numeracion_documental
- documento_logico
- documento_version
- plantilla_documental

## Modos del servicio

### Emisión
Permite generar una salida documental formal.

### Anulación
Permite invalidar una emisión existente.

### Consulta
Permite visualizar emisiones realizadas.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id

### Datos de negocio
- tipo de documento
- identificador de documento lógico o versión
- identificador de plantilla cuando corresponda
- reglas de numeración aplicables
- datos visibles para la emisión
- observaciones

### Parámetros de consulta
- tipo de documento
- numeración
- estado
- rango de fechas
- entidad asociada cuando corresponda

## Resultado esperado

### Para operaciones write
- identificador de emisión
- numeración asignada cuando corresponda
- documento asociado
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de emisiones
- numeración
- tipo de documento
- estado
- entidad asociada
- fechas

## Flujo de alto nivel

### Emisión
1. validar contexto técnico e idempotencia
2. cargar documento lógico y versión
3. validar elegibilidad para emisión
4. resolver plantilla cuando corresponda
5. asignar numeración
6. registrar emisión documental
7. persistir de forma atómica
8. registrar outbox
9. devolver resultado

### Anulación
1. validar contexto técnico
2. cargar emisión existente
3. validar anulabilidad
4. registrar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar emisiones
3. devolver vista de lectura

## Validaciones clave
- documento existente
- versión válida
- consistencia del tipo documental
- reglas de numeración válidas
- no duplicidad indebida de numeración
- anulabilidad según política funcional
- idempotencia en emisión

## Efectos transaccionales
- alta o actualización de emision_documental
- alta o actualización de numeracion_documental
- vinculación con documento_logico y documento_version
- aplicación de borrado lógico cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- documento lógico existente
- versión documental válida
- plantilla cuando corresponda
- contexto técnico válido
- permisos sobre emisión documental

### Hacia abajo
- dominio financiero
- dominio locativo
- dominio comercial
- reportes y auditoría

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
- [[SRV-DOC-004-gestion-de-plantillas-documentales]]
- DER documental

## Pendientes abiertos
- política final de numeración por tipo documental
- definición de secuencias por sucursal o instalación
- criterios de reemisión vs anulación
- integración con firmas digitales
- reglas de bloqueo posterior a emisión
