# SRV-COM-006 — Gestión de escrituración

## Objetivo
Gestionar el proceso de escrituración de una venta, permitiendo registrar, actualizar y consultar el estado del cierre jurídico de la operación, preservando trazabilidad y consistencia del proceso.

## Alcance
Este servicio cubre:
- inicio del proceso de escrituración
- registro de estados del proceso
- actualización de hitos de escrituración
- registro de fechas relevantes (firma, entrega, etc.)
- consulta del estado de escrituración
- vinculación entre venta y cierre jurídico

No cubre:
- ejecución material de la escritura ante escribanía
- generación de documentos notariales
- gestión documental general
- definición de condiciones comerciales
- generación de obligaciones financieras

## Entidades principales
- escrituracion
- venta
- documento_logico cuando corresponda

## Modos del servicio

### Inicio
Permite iniciar el proceso de escrituración para una venta.

### Actualización de estado
Permite registrar avances o cambios en el proceso.

### Registro de hitos
Permite registrar eventos relevantes del proceso de escrituración.

### Consulta
Permite visualizar el estado del proceso de escrituración.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta
- estado de escrituración
- fecha de inicio
- fecha estimada
- fecha efectiva cuando corresponda
- escribanía o entidad interviniente cuando corresponda
- hitos del proceso
- observaciones

### Parámetros de consulta
- identificador de venta
- estado de escrituración
- rango de fechas
- entidad interviniente

## Resultado esperado

### Para operaciones write
- identificador de proceso de escrituración
- venta asociada
- estado resultante
- fechas registradas
- hitos asociados
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- estado de escrituración
- fechas relevantes
- hitos del proceso
- relación con la venta

## Flujo de alto nivel

### Inicio
1. validar contexto técnico e idempotencia
2. cargar venta existente
3. validar elegibilidad para escrituración
4. registrar proceso de escrituración
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Actualización de estado
1. validar contexto técnico
2. cargar proceso de escrituración
3. validar versión esperada
4. validar transición de estado
5. aplicar cambio de estado
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Registro de hitos
1. validar contexto técnico
2. cargar proceso
3. registrar hito relevante
4. persistir cambios
5. registrar outbox
6. devolver resultado

### Consulta
1. validar parámetros
2. cargar proceso de escrituración
3. devolver vista de lectura

## Validaciones clave
- venta existente
- elegibilidad de venta para escrituración
- coherencia de estados y transiciones
- consistencia de fechas
- no duplicidad indebida de proceso activo
- control de versionado
- idempotencia en inicio

## Efectos transaccionales
- alta o actualización de escrituracion
- vinculación con venta
- registro de hitos del proceso
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- venta existente
- instrumentos de compraventa definidos cuando corresponda
- contexto técnico válido

### Hacia abajo
- dominio financiero (cierre de operación)
- procesos legales externos
- integración con sistemas notariales cuando corresponda

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

## Pendientes abiertos
- catálogo final de estados de escrituración
- integración con escribanías externas
- definición de hitos estándar del proceso
- reglas de elegibilidad para inicio de escrituración
- tratamiento de excepciones en el proceso legal
