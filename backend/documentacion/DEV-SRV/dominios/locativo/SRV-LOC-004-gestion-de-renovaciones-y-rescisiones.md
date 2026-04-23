# SRV-LOC-004 — Gestión de renovaciones y rescisiones

## Objetivo
Gestionar renovaciones y rescisiones de contratos de alquiler, permitiendo extender, reemplazar o finalizar contratos de forma anticipada, preservando consistencia contractual y trazabilidad del ciclo de vida.

## Alcance
Este servicio cubre:
- registro de renovación de contrato
- registro de extensión de vigencia
- registro de rescisión anticipada
- consulta de historial de renovaciones y rescisiones
- vinculación entre contratos sucesivos

No cubre:
- alta de contrato base
- definición detallada de condiciones locativas
- generación de obligaciones financieras
- liquidación de penalidades
- gestión documental completa

## Entidades principales
- contrato_alquiler
- contrato_renovacion
- contrato_rescision

## Modos del servicio

### Renovación
Permite generar una continuidad o reemplazo del contrato.

### Extensión
Permite extender la vigencia del contrato actual.

### Rescisión
Permite finalizar anticipadamente un contrato.

### Consulta
Permite visualizar el historial de ciclo de vida contractual.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato
- tipo de operación (renovación, extensión, rescisión)
- fecha efectiva
- causal de rescisión cuando corresponda
- contrato nuevo cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de contrato
- tipo de operación
- rango de fechas
- estado

## Resultado esperado

### Para operaciones write
- identificador de operación
- contrato afectado
- tipo de operación
- estado resultante del contrato
- vigencia actualizada
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- historial de renovaciones
- historial de rescisiones
- contratos vinculados
- estado actual y evolución

## Flujo de alto nivel

### Renovación
1. validar contexto técnico e idempotencia
2. cargar contrato existente
3. validar elegibilidad para renovación
4. generar nuevo contrato o continuidad
5. vincular contratos
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Extensión
1. validar contexto técnico
2. cargar contrato vigente
3. validar condiciones de extensión
4. actualizar vigencia
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Rescisión
1. validar contexto técnico
2. cargar contrato
3. validar causal y condiciones de rescisión
4. aplicar finalización anticipada
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar historial de operaciones
3. devolver vista de lectura

## Validaciones clave
- contrato existente
- coherencia de fechas
- elegibilidad para renovación o rescisión
- no superposición indebida de contratos
- consistencia de vínculos entre contratos
- control de versionado
- idempotencia en operaciones

## Efectos transaccionales
- actualización de contrato_alquiler
- registro de contrato_renovacion o contrato_rescision
- vinculación entre contratos
- actualización de vigencias
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- contrato existente
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- [[SRV-LOC-002-gestion-de-condiciones-locativas]]
- [[SRV-LOC-005-gestion-de-ocupacion-locativa]]
- dominio financiero (ajustes, liquidaciones)

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

## Pendientes abiertos
- catálogo final de causales de rescisión
- reglas de penalización por rescisión
- definición de renovación automática
- integración completa con dominio financiero
- tratamiento de contratos encadenados
