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
- generación por `factura_servicio` registrada en inmobiliario, cuando exista origen implementado
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
- concepto_financiero

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
- metodo financiero aplicable, sin codificar `tipo_obligacion` como eje estructural
- período o fecha de corte cuando corresponda
- parámetros de cálculo necesarios
- motivo u observación cuando aplique
- referencia al origen inmobiliario `factura_servicio` cuando corresponda
- composiciones esperadas por `concepto_financiero` cuando el plan recibido ya las detalle

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
5. determinar vencimientos, importes y conceptos financieros
6. crear obligaciones financieras
7. crear composiciones por `concepto_financiero`
8. persistir de forma atómica
9. registrar outbox
10. devolver resultado

## Validaciones clave
- relación generadora existente
- relación en estado compatible con generación
- origen formal compatible
- parámetros mínimos disponibles
- no duplicidad indebida de emisión o generación
- no duplicidad de obligacion activa para la misma `factura_servicio` registrada como origen
- idempotencia de generacion por `factura_servicio` usando clave conceptual `id_factura_servicio`
- consistencia entre obligación y composición
- toda obligacion materializada debe tener una o mas composiciones
- toda composicion debe referenciar exactamente un `concepto_financiero`
- la naturaleza economica debe surgir de `composicion_obligacion` + `concepto_financiero`, no de una columna rigida de tipo de obligacion
- el saldo consolidado de la obligacion debe ser conciliable contra sus composiciones
- cuando exista saldo por componente, `saldo_pendiente` debe igualar la suma de `saldo_componente` de composiciones activas, salvo transicion tecnica documentada
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
- origen inmobiliario por `factura_servicio` cuando exista contrato implementado

### factura_servicio
Cuando el origen sea `factura_servicio`, emitida por proveedor externo y registrada por el dominio inmobiliario, este servicio debe tratarla como origen de generacion de obligacion, no como factura emitida por el sistema.

El importe, vencimiento, obligado, concepto y composicion financiera deben resolverse dentro de `financiero` segun la relacion generadora y la parametrizacion aplicable. El registro inmobiliario no calcula deuda como fuente primaria.

Decision conceptual recomendada para `SERVICIO_TRASLADADO`: 1 servicio asociado a inmueble o unidad funcional usa 1 `relacion_generadora`; esa relacion puede existir antes de la primera `factura_servicio`; cada factura posterior genera 1 `obligacion_financiera` dentro de esa misma relacion. `factura_servicio` existe como tabla SQL estructural, pero esta decision queda `PENDIENTE` / `NO IMPLEMENTADO` a nivel funcional hasta que exista contrato, API/backend, evento y consumer financiero.

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
- [[MODELO-FINANCIERO-FIN]]
- [[RN-FIN]]
- [[ERR-FIN]]
- [[EST-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- definición exacta por metodo financiero y composiciones por `concepto_financiero`
- política de reemisión versus regularización
- reglas de duplicidad por período, concepto y relación
- estrategia exacta de corte para generación extraordinaria y liquidación final
