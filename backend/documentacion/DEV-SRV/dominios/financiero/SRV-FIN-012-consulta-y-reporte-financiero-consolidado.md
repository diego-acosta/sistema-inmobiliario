# SRV-FIN-012 — Consulta y reporte financiero consolidado

## Objetivo
Proveer una capa de lectura consolidada del dominio financiero, permitiendo consultar deuda, pagos, imputaciones, mora, tesorería y emisiones con trazabilidad completa y consistencia funcional, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de estado financiero consolidado
- consulta de deuda y obligaciones
- consulta de pagos y movimientos financieros
- consulta de imputaciones
- consulta de mora, créditos y débitos
- consulta de tesorería y saldos
- consulta de emisiones financieras
- reportes financieros operativos
- trazabilidad completa de operaciones financieras

No cubre:
- generación de obligaciones
- registro de pagos
- imputación financiera
- modificación de estados financieros
- lógica analítica avanzada o BI

## Entidades principales
- relacion_generadora
- obligacion_financiera
- composicion_obligacion
- movimiento_financiero
- aplicacion_financiera
- movimiento_tesoreria
- cuenta_financiera
- documento_logico

## Modos del servicio

### Consulta operativa
Permite visualizar el estado financiero actual de una entidad o conjunto de entidades.

### Consulta histórica
Permite reconstruir la evolución financiera a lo largo del tiempo.

### Reporte consolidado
Permite obtener vistas agregadas del estado financiero, agrupadas por criterios funcionales.

### Trazabilidad
Permite seguir la relación entre deuda, pago, imputación, mora, emisión y tesorería.

## Entradas conceptuales

### Parámetros de consulta
- identificador de relación generadora
- identificador de entidad origen (venta, contrato, etc.)
- identificador de persona o cliente
- rango de fechas
- tipo de operación financiera
- estado financiero
- sucursal o instalación cuando corresponda
- criterios de agrupación o consolidación

## Resultado esperado

- estado financiero consolidado
- detalle de obligaciones
- movimientos financieros asociados
- imputaciones aplicadas
- estado de mora o ajustes
- movimientos de tesorería relacionados
- emisiones financieras asociadas
- trazabilidad completa entre entidades
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros de entrada
2. resolver entidad o contexto financiero
3. cargar deuda, pagos, imputaciones y movimientos asociados
4. integrar información de tesorería cuando corresponda
5. integrar emisiones financieras
6. consolidar estado financiero
7. construir vista de salida
8. devolver resultado

## Validaciones clave
- consistencia de parámetros de consulta
- existencia de entidad o contexto financiero
- coherencia entre filtros aplicados
- control de acceso a información financiera

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-FIN]]

## Dependencias

### Hacia arriba
- existencia de información financiera registrada
- integridad del dominio financiero
- permisos de consulta financiera

### Hacia abajo
- capa de reportes operativos
- análisis financiero externo
- exportaciones de datos financieros

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- [[SRV-FIN-009-gestion-de-mora-creditos-y-debitos]]
- [[SRV-FIN-010-emision-financiera]]
- [[SRV-FIN-011-gestion-de-caja-financiera-y-garantias-monetarias]]
- [[RN-FIN]]
- [[ERR-FIN]]
- DER financiero

## Pendientes abiertos
- definición final de vistas estándar de reporte financiero
- criterios de agregación por defecto
- política de snapshots o reconstrucción histórica
- nivel de detalle por perfil de usuario
- límites entre consulta operativa y analítica avanzada
