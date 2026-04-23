# SRV-FIN-007 — Simulación y registro de pago

## Objetivo
Permitir previsualizar el impacto de un pago y registrar movimientos financieros que cancelen, reduzcan o afecten deuda emitida, sin confundir esta operación con la caja operativa.

## Alcance
Este servicio cubre:
- simulación de pago
- registro de pago
- registro de pago externo
- registro de egreso financiero
- previsualización de impacto sobre obligaciones y composiciones

No cubre:
- caja operativa física
- arqueo de caja
- imputación detallada y reimputación avanzada
- generación de obligaciones
- emisión documental final

## Entidades principales
- movimiento_financiero
- aplicacion_financiera
- obligacion_financiera
- composicion_obligacion

## Modos del servicio

### Simulación
Modo de lectura que permite proyectar cómo impactaría un pago antes de persistirlo.

### Registro
Modo write que materializa el movimiento financiero y deja preparado o ejecutado el impacto sobre la deuda según la política del dominio.

## Entradas conceptuales
### Contexto técnico para registro
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de obligación, relación o conjunto de deuda objetivo
- importe
- fecha de pago
- medio o canal cuando corresponda
- tipo de operación: pago, pago externo o egreso
- observación o referencia cuando corresponda

### Parámetros de simulación
- deuda objetivo
- importe propuesto
- fecha de simulación
- criterios de aplicación visibles

## Resultado esperado
### Para simulación
- impacto proyectado sobre saldo
- obligaciones alcanzadas
- composición afectada
- remanente o diferencia cuando corresponda

### Para registro
- identificador del movimiento financiero
- importe registrado
- versión resultante cuando corresponda
- op_id
- resumen de efectos generados
- errores estructurados cuando corresponda

## Flujo de alto nivel

### Simulación
1. validar parámetros de lectura
2. cargar deuda objetivo
3. proyectar impacto según criterios visibles
4. devolver simulación sin persistencia

### Registro
1. validar contexto técnico e idempotencia
2. cargar deuda u objetivo financiero
3. validar elegibilidad y consistencia de la operación
4. registrar movimiento financiero
5. dejar preparada o ejecutar aplicación sobre deuda según política vigente
6. persistir de forma atómica
7. registrar outbox
8. devolver resultado

## Validaciones clave
- importe válido
- deuda objetivo existente cuando corresponda
- operación compatible con el estado de la deuda
- no duplicidad indebida en reintentos
- coherencia entre movimiento y aplicación financiera
- separación entre financiero lógico y caja operativa física

## Efectos transaccionales
- alta de movimiento_financiero en modo registro
- alta o actualización de aplicacion_financiera cuando corresponda
- actualización de saldo visible de obligaciones afectadas cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias
### Hacia arriba
- deuda emitida previamente
- cronograma y obligaciones
- permisos para registrar movimiento financiero

### Hacia abajo
- imputación financiera
- emisión financiera
- analítica financiera
- lectura operativa en caja

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[RN-FIN]]
- [[ERR-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- política exacta de aplicación automática versus preparación de aplicación
- reglas de tratamiento de pago parcial, excedente y remanente
- estrategia exacta para pago externo y egreso financiero
- frontera definitiva entre simulación, registro e imputación
