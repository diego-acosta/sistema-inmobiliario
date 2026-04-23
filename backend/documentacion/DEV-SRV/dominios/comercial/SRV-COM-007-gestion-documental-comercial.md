# SRV-COM-007 — Gestión documental comercial

## Objetivo
Gestionar la documentación operativa del dominio comercial, permitiendo registrar, modificar, invalidar y consultar documentos asociados a procesos de venta, preservando trazabilidad y consistencia.

## Alcance
Este servicio cubre:
- registro de documentación comercial
- modificación de documentos
- invalidación de documentos
- consulta de documentación asociada a una venta
- vinculación de documentos con operaciones comerciales

No cubre:
- emisión formal de documentos
- instrumentos jurídicos de compraventa (SRV-COM-004)
- almacenamiento documental general del sistema
- escrituración
- generación de obligaciones financieras

## Entidades principales
- documento_comercial
- documento_logico
- venta

## Modos del servicio

### Registro
Permite registrar un documento comercial asociado a una operación.

### Modificación
Permite actualizar datos de un documento existente.

### Invalidación
Permite dejar sin efecto un documento.

### Consulta
Permite visualizar documentación comercial asociada a una venta.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta
- tipo de documento comercial
- datos del documento
- estado del documento
- fecha de registro
- observaciones

### Parámetros de consulta
- identificador de venta
- tipo de documento
- estado
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de documento
- venta asociada
- tipo de documento
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de documentos comerciales
- tipo de documento
- estado
- relación con la venta

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar venta existente
3. validar elegibilidad de registro documental
4. registrar documento comercial
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

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
2. cargar documentos comerciales
3. devolver vista de lectura

## Validaciones clave
- venta existente
- tipo de documento válido
- coherencia con el proceso comercial
- no duplicidad indebida cuando la política lo restrinja
- anulabilidad según reglas funcionales
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de documento_comercial
- alta o actualización de documento_logico cuando corresponda
- vinculación con venta
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- venta existente
- contexto técnico válido
- catálogo de tipos documentales

### Hacia abajo
- procesos comerciales internos
- integración con sistemas documentales externos
- consulta comercial consolidada

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-COM-004-gestion-de-instrumentos-de-compraventa]]
- DER comercial
- DER documental

## Pendientes abiertos
- catálogo final de documentos comerciales
- política de almacenamiento documental
- reglas de modificación e invalidación
- integración con gestión documental global
- definición de metadatos estándar
