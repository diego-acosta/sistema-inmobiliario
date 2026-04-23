# SRV-LOC-002 — Gestión de condiciones locativas

## Objetivo
Gestionar las condiciones locativas asociadas a contratos de alquiler, permitiendo definir, modificar, cerrar vigencias y consultar configuraciones económicas y funcionales del contrato, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- definición de condiciones locativas
- modificación de condiciones locativas
- cierre o reemplazo de vigencia
- consulta de condiciones vigentes e históricas
- configuración de canon, moneda y periodicidad
- configuración de esquema de actualización cuando corresponda

No cubre:
- alta de contrato de alquiler
- gestión específica de garantías
- generación de obligaciones financieras
- pagos, imputación o mora
- gestión documental locativa

## Entidades principales
- condicion_locativa
- contrato_alquiler
- esquema_actualizacion_locativa

## Modos del servicio

### Definición
Permite registrar una nueva condición locativa para un contrato.

### Modificación
Permite actualizar una condición locativa según reglas de vigencia.

### Cierre de vigencia
Permite cerrar una condición vigente y, cuando corresponda, reemplazarla por otra.

### Consulta
Permite visualizar condiciones locativas vigentes e históricas.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato
- canon locativo
- moneda
- periodicidad
- fecha desde
- fecha hasta cuando corresponda
- esquema de actualización cuando corresponda
- estado de la condición
- observaciones

### Parámetros de consulta
- identificador de contrato
- estado
- vigencia
- moneda
- periodicidad

## Resultado esperado

### Para operaciones write
- identificador de condición locativa
- contrato asociado
- canon y moneda definidos
- vigencia resultante
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- condiciones locativas vigentes
- historial de condiciones
- canon locativo
- moneda
- periodicidad
- esquema de actualización cuando corresponda

## Flujo de alto nivel

### Definición
1. validar contexto técnico e idempotencia
2. cargar contrato existente
3. validar elegibilidad para registrar condición
4. registrar condición locativa
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar condición existente
3. validar versión esperada
4. validar modificabilidad según estado contractual y vigencia
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Cierre de vigencia
1. validar contexto técnico
2. cargar condición vigente
3. validar consistencia temporal
4. cerrar vigencia actual
5. registrar nueva condición cuando corresponda
6. persistir cambios de forma atómica
7. registrar outbox
8. devolver resultado

### Consulta
1. validar parámetros
2. cargar condiciones locativas
3. resolver vigencias e historial
4. devolver vista de lectura

## Validaciones clave
- contrato existente
- coherencia entre canon, moneda y periodicidad
- no superposición indebida de vigencias
- consistencia temporal de fechas
- modificabilidad según estado contractual
- control de versionado
- idempotencia en definición

## Efectos transaccionales
- alta o actualización de condicion_locativa
- cierre de vigencias anteriores cuando corresponda
- vinculación con contrato_alquiler
- configuración de esquema_actualizacion_locativa cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- contrato de alquiler existente
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- [[SRV-LOC-003-gestion-de-garantias]]
- [[SRV-LOC-004-gestion-de-renovaciones-y-rescisiones]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- [[SRV-FIN-004-gestion-de-indices-financieros]]

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-LOCATIVO]]
- [[CU-LOC]]
- [[RN-LOC]]
- [[ERR-LOC]]
- [[EVT-LOC]]
- [[EST-LOC]]
- [[SRV-LOC-001-gestion-de-contratos-de-alquiler]]
- DER locativo
- DER financiero

## Pendientes abiertos
- catálogo final de periodicidades locativas
- definición exacta de esquemas de actualización
- reglas de reemplazo de condiciones vigentes
- integración completa con generación de obligaciones
- política de historización visible
