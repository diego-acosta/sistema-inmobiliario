# SRV-FIN-008 — Gestión de imputación financiera

## Objetivo
Aplicar, revertir y reaplicar movimientos financieros sobre deuda emitida, determinando de forma explícita cómo impacta cada pago en obligaciones y sus composiciones.

## Alcance
Este servicio cubre:
- imputación de pagos sobre obligaciones
- distribución de importes sobre composición por concepto
- reversión de imputaciones
- reaplicación de pagos
- consulta de aplicación financiera

No cubre:
- registro de pago (movimiento financiero)
- generación de obligaciones
- recalculo estructural de deuda
- caja operativa
- emisión documental

## Entidades principales
- aplicacion_financiera
- movimiento_financiero
- obligacion_financiera
- composicion_obligacion

## Modos del servicio

### Imputación
Asocia un movimiento financiero a una o más obligaciones y sus composiciones.

### Reversión
Deshace total o parcialmente una imputación previamente registrada.

### Reaplicación
Reasigna un movimiento financiero ya existente a nuevas obligaciones o composiciones.

### Consulta
Permite visualizar cómo se aplicaron los pagos sobre la deuda.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de movimiento financiero
- obligaciones objetivo
- criterios de imputación
- importe a aplicar
- tipo de operación: imputación, reversión o reaplicación
- motivo u observación cuando corresponda

### Parámetros de consulta
- id_movimiento_financiero
- id_obligacion_financiera
- filtros por estado
- nivel de detalle de composición

## Resultado esperado

### Para imputación / reversión / reaplicación
- identificador de la aplicación financiera
- movimiento financiero afectado
- obligaciones impactadas
- composición afectada
- saldo resultante por obligación
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- detalle de aplicación por movimiento
- relación movimiento → obligación
- desglose por composición
- estado de aplicación

## Flujo de alto nivel

### Imputación
1. validar contexto técnico e idempotencia
2. cargar movimiento financiero
3. validar deuda objetivo
4. determinar criterios de distribución
5. aplicar sobre obligaciones y composiciones
6. actualizar saldos
7. persistir de forma atómica
8. registrar outbox
9. devolver resultado

### Reversión
1. validar contexto técnico
2. cargar aplicación existente
3. validar reversibilidad
4. revertir impacto en obligaciones
5. actualizar saldos
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Reaplicación
1. revertir imputación previa
2. recalcular nueva aplicación
3. aplicar sobre nuevas obligaciones
4. persistir cambios atómicos
5. registrar outbox
6. devolver resultado

### Consulta
1. validar parámetros de lectura
2. cargar aplicaciones financieras
3. resolver relaciones con movimientos y obligaciones
4. devolver vista consolidada

## Validaciones clave
- movimiento financiero existente
- coherencia entre importe y deuda objetivo
- no sobreimputación indebida
- consistencia entre aplicación y composición
- reversión solo sobre aplicaciones válidas
- idempotencia en operaciones write

### Politica base de distribucion

Cuando exista desglose por `composicion_obligacion`, la imputacion debe impactar componentes o aplicar la politica documentada de distribucion definida en `MODELO-FINANCIERO-FIN`.

La prioridad conceptual por defecto para pagos globales es: `INTERES_MORA`, `PUNITORIO`, `CARGO_ADMINISTRATIVO`, `INTERES_FINANCIERO`, `AJUSTE_INDEXACION`, capitales/canones/trasladados, y luego otros conceptos de cierre.

Esta politica queda `DEFINIDA CONCEPTUALMENTE / PENDIENTE SQL-BACKEND`.

## Efectos transaccionales
- alta o modificación de aplicacion_financiera
- actualización de saldo en obligacion_financiera
- actualización de composición cuando corresponda
- actualización de metadatos transversales
- registro de outbox

## Errores
- [[ERR-FIN]]

## Dependencias

### Hacia arriba
- movimientos financieros registrados
- deuda emitida (obligaciones)
- permisos de operación financiera

### Hacia abajo
- emisión financiera
- analítica financiera
- reportes de deuda y pagos

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[MODELO-FINANCIERO-FIN]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[RN-FIN]]
- [[ERR-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- implementacion SQL/backend de la politica conceptual de distribucion por defecto definida en `MODELO-FINANCIERO-FIN`
- definicion de variantes futuras de distribucion de pago (FIFO, proporcional, manual, etc.)
- estrategia de imputación automática versus manual
- tratamiento de pagos parciales y excedentes
- trazabilidad exacta de reaplicaciones múltiples
