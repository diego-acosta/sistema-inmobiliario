# SRV-FIN-010 — Emisión financiera

## Objetivo
Emitir salidas formales del circuito financiero, tales como recibos, comprobantes, libres deuda, certificaciones y estados de cuenta, preservando trazabilidad documental y numeración formal cuando corresponda.

## Alcance
Este servicio cubre:
- emisión de recibos
- emisión de comprobantes financieros
- emisión de libre deuda
- emisión de certificaciones
- emisión de estados de cuenta
- anulación documental cuando corresponda
- consulta de emisiones realizadas

No cubre:
- generación de obligaciones
- registro de pago
- imputación financiera
- almacenamiento documental general
- definición de plantillas documentales generales

## Entidades principales
- movimiento_financiero
- documento_logico
- emision_numeracion

## Modos del servicio

### Emisión
Genera una salida formal asociada a una operación financiera o a un estado financiero consultable.

### Anulación
Invalida una emisión previa cuando la política documental y financiera lo permita.

### Consulta
Permite visualizar emisiones realizadas, su trazabilidad y numeración visible.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de emisión: recibo, comprobante, libre deuda, certificación o estado de cuenta
- entidad u operación financiera origen
- identificador de movimiento financiero cuando corresponda
- identificador de deuda o cuenta cuando corresponda
- motivo u observación
- datos visibles requeridos por la emisión

### Parámetros de consulta
- tipo de emisión
- identificador de entidad origen
- rango de fechas
- estado de emisión
- numeración cuando corresponda

## Resultado esperado

### Para emisión / anulación
- identificador de documento lógico o emisión generada
- numeración asignada cuando corresponda
- entidad financiera asociada
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado o detalle de emisiones realizadas
- tipo de emisión
- numeración visible
- entidad de origen
- estado visible de la emisión

## Flujo de alto nivel

### Emisión
1. validar contexto técnico e idempotencia
2. cargar entidad financiera origen
3. validar elegibilidad para emitir
4. construir salida formal
5. registrar documento lógico y numeración cuando corresponda
6. persistir de forma atómica
7. registrar outbox
8. devolver resultado

### Anulación
1. validar contexto técnico
2. cargar emisión existente
3. validar anulabilidad
4. registrar anulación o invalidez formal
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros de lectura
2. cargar emisiones solicitadas
3. resolver trazabilidad con la entidad financiera origen
4. devolver vista consolidada

## Validaciones clave
- entidad financiera origen existente
- operación o deuda elegible para emisión
- no duplicidad indebida de emisión cuando no corresponda
- numeración válida cuando aplique
- anulabilidad conforme a política funcional
- idempotencia en operaciones write

## Efectos transaccionales
- alta o actualización de documento_logico cuando corresponda
- alta o actualización de emision_numeracion cuando corresponda
- vinculación con la entidad financiera origen
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias

### Hacia arriba
- deuda, movimiento o estado financiero existente
- permisos de emisión financiera
- reglas formales de numeración cuando apliquen

### Hacia abajo
- consulta documental
- analítica financiera
- trazabilidad de operaciones emitidas

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- [[RN-FIN]]
- [[ERR-FIN]]
- DER financiero

## Pendientes abiertos
- política exacta de numeración por tipo de emisión
- criterio final para reemisión versus anulación
- catálogo final de tipos de emisión financiera
- definición exacta de elegibilidad para libre deuda y certificaciones
- relación final entre emisión financiera y documental general
