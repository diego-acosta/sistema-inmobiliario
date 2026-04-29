# SRV-FIN-006 — Cronograma y obligaciones

## Objetivo
Devolver una vista operativa y consolidada de la deuda emitida, incluyendo cronograma, detalle de obligaciones, composición por concepto y estado visible de cada obligación.

## Alcance
Este servicio cubre:
- consulta de cronograma financiero
- consulta de obligaciones emitidas
- detalle de obligación
- consulta de composición por concepto
- consulta de estado visible de cada obligación
- navegación por vencimiento, emisión, saldo, origen financiero y concepto financiero

No cubre:
- generación de obligaciones
- recalculo de deuda
- registro de pagos
- imputación de pagos
- cancelación o finalización de la relación generadora
- emisión de eventos técnicos

## Entidades principales
- obligacion_financiera
- composicion_obligacion
- obligacion_obligado

## Subconsultas internas
- obtener_cronograma_por_relacion
- obtener_detalle_obligacion
- obtener_composicion_obligacion
- obtener_obligados_por_obligacion
- resumir_estado_deuda
- filtrar_obligaciones_por_estado

## Entrada conceptual
### Parámetros principales
- id_relacion_generadora cuando la lectura sea por relación
- id_obligacion_financiera cuando la lectura sea puntual
- tipo de consulta: cronograma, detalle, composición o resumen

### Parámetros opcionales
- incluir_composicion
- incluir_obligados
- incluir_resumen
- filtros por estado
- filtros por origen financiero
- filtros por concepto financiero
- filtros por vencimiento
- filtros por saldo
- paginación
- orden cronológico
- corte a fecha cuando corresponda

### Contexto de seguridad
- identidad del usuario consultante
- permisos de lectura financiera

## Resultado esperado
- cronograma de obligaciones
- detalle de obligaciones seleccionadas
- composición por concepto cuando se solicite
- obligados asociados cuando se solicite
- resumen visible de saldo, vencido, exigible y cancelado cuando corresponda

## Flujo de alto nivel
1. validar entrada y permisos de lectura
2. resolver el criterio de consulta
3. cargar obligaciones afectadas
4. cargar composición y obligados cuando se solicite
5. ordenar, filtrar y resumir información
6. devolver vista consolidada de lectura

## Validaciones clave
- criterio de búsqueda válido
- existencia de relación generadora u obligación consultada
- coherencia entre filtros solicitados
- permisos suficientes de lectura financiera

## Restricciones
- es una query pura
- no modifica estado
- no requiere lock
- no requiere versionado
- no requiere op_id
- no escribe outbox

## Dependencias
### Hacia arriba
- relación generadora existente cuando aplique
- obligaciones previamente emitidas
- permisos de lectura financiera

### Hacia abajo
- pagos e imputación
- emisión financiera
- analítica financiera
- consulta integral de relación generadora

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-002-consulta-relacion-generadora]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- [[RN-FIN]]
- [[EST-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- soporte fisico de saldo por componente (`saldo_componente`) pendiente de SQL/backend
- criterio final de saldo visible a fecha
- nivel exacto de detalle del estado de obligación expuesto en lectura
- política de agrupación del cronograma por período, vencimiento o emisión
