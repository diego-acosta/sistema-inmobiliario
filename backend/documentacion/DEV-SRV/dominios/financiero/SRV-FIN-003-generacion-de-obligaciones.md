# SRV-FIN-003 — Generación de obligaciones

## Objetivo
Materializar deuda financiera a partir de una relación generadora válida, creando obligaciones financieras y sus composiciones según el método y origen aplicable.

## Alcance
Este servicio cubre:
- generación inicial de obligaciones
- generación locativa
- generación por venta financiada
- generación por anticipo
- generación por expensas, servicios e impuestos
- generación por garantía monetaria cuando corresponda
- generación extraordinaria
- liquidación final
- refinanciación
- cancelación anticipada
- regularización
- reemisión

No cubre directamente:
- parametrización financiera general
- mantenimiento de índices
- registro de pago
- imputación de pago
- caja operativa
- emisión documental final

## Agregado principal
- relacion_generadora

## Entidades relacionadas
- obligacion_financiera
- composicion_obligacion

## Casos de uso cubiertos
- generación de obligaciones por activación inicial
- generación de obligaciones locativas
- generación de obligaciones extraordinarias
- liquidación final
- refinanciación
- cancelación anticipada
- regularización
- reemisión

## Reglas
- [[RN-FIN]]

## Entradas conceptuales
### Contexto técnico
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- id_relacion_generadora
- tipo de generación o método financiero aplicable
- período o fecha de corte cuando corresponda
- parámetros de cálculo necesarios
- motivo u observación cuando aplique

## Resultado esperado
- identificador de relación generadora afectada
- cantidad de obligaciones generadas
- cantidad de composiciones generadas
- versión resultante cuando corresponda
- op_id
- resumen de efectos generados
- errores estructurados cuando corresponda

## Flujo de alto nivel
1. validar contexto técnico e idempotencia
2. cargar relación generadora
3. validar existencia, estado y elegibilidad para generar
4. resolver método financiero aplicable
5. determinar conceptos, vencimientos e importes
6. crear obligaciones financieras
7. crear composiciones por concepto
8. persistir de forma atómica
9. registrar outbox
10. devolver resultado

## Validaciones clave
- relación generadora existente
- relación en estado compatible con generación
- origen formal compatible
- parámetros mínimos disponibles
- no duplicidad indebida de emisión o generación
- consistencia entre obligación y composición
- idempotencia en reintentos
- coherencia con refinanciación, regularización o reemisión cuando corresponda

## Efectos transaccionales
- alta de obligacion_financiera
- alta de composicion_obligacion
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias
### Hacia arriba
- relación generadora válida
- parametrización financiera vigente
- índices financieros cuando apliquen
- origen comercial o locativo compatible

### Hacia abajo
- cronograma y consulta de deuda
- pagos e imputación
- emisión financiera
- analítica financiera

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[RN-FIN]]
- [[ERR-FIN]]
- [[EST-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- definición exacta por tipo de obligación y método financiero
- política de reemisión versus regularización
- reglas de duplicidad por período, concepto y relación
- estrategia exacta de corte para generación extraordinaria y liquidación final
