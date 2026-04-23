# SRV-FIN-011 — Gestión de caja financiera y garantías monetarias

## Objetivo
Administrar la tesorería financiera del sistema y las garantías monetarias asociadas, registrando cuentas financieras, movimientos de tesorería, conciliaciones, depósitos, afectaciones, liberaciones, devoluciones y ejecuciones cuando corresponda, preservando trazabilidad financiera y separación respecto de la deuda lógica y de la caja operativa.

## Alcance
Este servicio cubre:
- gestión de cuentas financieras
- registro de movimientos de tesorería
- depósitos de dinero
- devoluciones de dinero
- registro y administración de garantías monetarias
- afectación de garantías
- liberación de garantías
- ejecución de garantías
- conciliación financiera o bancaria
- consulta de cuentas, movimientos, saldos y conciliaciones

No cubre:
- generación de obligaciones
- cronograma de deuda
- registro de pago lógico
- imputación financiera
- mora, créditos y débitos de deuda
- caja operativa física
- almacenamiento documental general

## Entidades principales
- cuenta_financiera
- movimiento_tesoreria
- conciliacion_bancaria
- detalle_conciliacion

## Modos del servicio

### Gestión de cuentas
Administra el alta, actualización, activación, desactivación y consulta de cuentas financieras utilizadas por la tesorería financiera.

### Movimiento de tesorería
Registra ingresos, egresos, ajustes, depósitos, devoluciones y reversiones sobre dinero real administrado por cuentas financieras.

### Gestión de garantías monetarias
Registra depósitos en garantía, su afectación, liberación, devolución parcial o total y eventual ejecución conforme a la política funcional.

### Conciliación
Permite registrar procesos de conciliación financiera, asociar movimientos y detectar diferencias o pendientes.

### Consulta
Permite visualizar cuentas, movimientos, saldos, garantías y conciliaciones con su trazabilidad visible.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de cuenta financiera
- tipo de movimiento de tesorería
- importe y moneda
- fecha operativa
- concepto o motivo
- referencia externa o interna cuando corresponda
- identificador de garantía monetaria cuando corresponda
- operación, contrato o relación financiera asociada cuando corresponda
- datos de conciliación o referencia bancaria cuando corresponda
- observaciones

### Parámetros de consulta
- cuenta financiera
- tipo de movimiento
- rango de fechas
- estado de conciliación
- estado de garantía
- referencia externa
- sucursal o instalación cuando corresponda

## Resultado esperado

### Para operaciones write
- identificador de cuenta, movimiento, garantía o conciliación generada o actualizada
- estado resultante
- saldo visible cuando corresponda
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado o detalle de cuentas financieras
- movimientos registrados
- saldos visibles
- estado de garantías monetarias
- estado y detalle de conciliaciones

## Flujo de alto nivel

### Gestión de cuentas
1. validar contexto técnico e idempotencia
2. cargar o preparar cuenta financiera
3. validar consistencia funcional
4. persistir alta o actualización
5. registrar metadatos transversales
6. registrar outbox cuando corresponda
7. devolver resultado

### Movimiento de tesorería
1. validar contexto técnico e idempotencia
2. cargar cuenta financiera y contexto origen
3. validar elegibilidad del movimiento
4. registrar ingreso, egreso, ajuste, depósito o devolución
5. actualizar saldo o estado visible cuando corresponda
6. persistir de forma atómica
7. registrar outbox
8. devolver resultado

### Gestión de garantías monetarias
1. validar contexto técnico
2. cargar garantía o contexto origen
3. validar disponibilidad, afectabilidad, liberación, devolución o ejecución
4. registrar operación correspondiente
5. actualizar estado visible de la garantía
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Conciliación
1. validar contexto técnico
2. cargar cuenta y movimientos a conciliar
3. registrar cabecera de conciliación
4. vincular detalles conciliados
5. detectar diferencias o pendientes
6. persistir resultado
7. registrar outbox cuando corresponda
8. devolver resultado

### Consulta
1. validar parámetros de lectura
2. cargar cuentas, movimientos, garantías o conciliaciones solicitadas
3. resolver trazabilidad visible
4. devolver vista consolidada

## Validaciones clave
- cuenta financiera existente y habilitada cuando corresponda
- movimiento permitido para el estado actual de la cuenta
- importe válido y consistente
- no duplicidad indebida de registración por reintento
- garantía existente y en estado compatible con la operación solicitada
- no devolución por encima del monto disponible
- no liberación o ejecución incompatible con el estado vigente
- conciliación consistente entre cabecera y detalle
- no modificación indebida de movimientos ya conciliados cuando la política lo restrinja
- idempotencia en operaciones write

## Efectos transaccionales
- alta o actualización de cuenta_financiera cuando corresponda
- alta de movimiento_tesoreria
- alta o actualización de conciliacion_bancaria
- alta o actualización de detalle_conciliacion
- actualización de saldos y estados visibles cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias

### Hacia arriba
- permisos sobre tesorería financiera
- cuenta financiera habilitada cuando corresponda
- operación, relación o garantía existente cuando la registración dependa de una entidad previa
- reglas funcionales sobre devolución, liberación y ejecución

### Hacia abajo
- lectura financiera consolidada
- auditoría y trazabilidad financiera
- conciliación y control operativo
- proyección hacia caja operativa sin fusionarse con ella

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- [[SRV-FIN-009-gestion-de-mora-creditos-y-debitos]]
- [[RN-FIN]]
- [[ERR-FIN]]
- DER financiero

## Pendientes abiertos
- política exacta de identificación funcional de garantías monetarias
- criterio final de afectación entre garantía disponible, afectada, liberada, devuelta y ejecutada
- catálogo final de tipos de movimiento de tesorería
- definición exacta de restricciones sobre reversión de movimientos conciliados
- relación final entre tesorería financiera, garantía monetaria y caja operativa
