# SRV-FIN-009 — Gestión de mora, créditos y débitos

## Objetivo
Ajustar saldo vivo de la deuda emitida mediante mora, punitorios, rectificaciones por índice y créditos o débitos manuales autorizados, manteniendo coherencia con el circuito financiero existente.

## Alcance
Estado actual:
- La generacion automatica de mora diaria simple esta implementada y documentada en `SRV-FIN-013-generacion-de-mora`.
- Punitorios, rectificacion por indice, creditos manuales, debitos manuales y consulta especifica de ajustes siguen pendientes.

Este servicio cubre:
- cálculo y registro de mora
- generación de punitorios
- rectificación por índice
- registro de créditos manuales autorizados
- registro de débitos manuales autorizados
- consulta de ajustes aplicados sobre la deuda

No cubre:
- generación de obligaciones base
- registro de pago
- imputación financiera
- caja operativa
- emisión documental final

## Entidades principales
- obligacion_financiera
- composicion_obligacion
- movimiento_financiero

## Modos del servicio

### Mora y punitorios
Genera ajustes por incumplimiento temporal o atraso sobre obligaciones exigibles.

### Rectificación por índice
Corrige importes o saldos según actualización de índice cuando la política financiera lo permita.

### Crédito manual
Registra una disminución autorizada del saldo vivo por bonificación, corrección o ajuste favorable.

### Débito manual
Registra un incremento autorizado del saldo vivo por ajuste, cargo complementario o corrección desfavorable.

### Consulta
Permite visualizar los ajustes aplicados sobre la deuda y su trazabilidad visible.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- obligación u obligaciones objetivo
- composición objetivo cuando corresponda
- tipo de ajuste: mora, punitorio, rectificación por índice, crédito o débito
- importe o criterio de cálculo
- fecha de aplicación o fecha de corte
- índice aplicable cuando corresponda
- motivo, fundamento u observación
- autorización cuando corresponda

### Parámetros de consulta
- id_obligacion_financiera
- tipo de ajuste
- rango de fechas
- filtros por estado
- nivel de detalle de composición

## Resultado esperado

### Para operaciones write
- obligación u obligaciones afectadas
- ajuste registrado o aplicado
- composición afectada cuando corresponda
- saldo visible resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- detalle de ajustes aplicados
- tipo de ajuste
- obligación afectada
- composición afectada cuando exista
- impacto visible en saldo

## Flujo de alto nivel

### Mora / punitorios
1. validar contexto técnico e idempotencia
2. cargar obligación objetivo
3. validar exigibilidad y atraso
4. calcular ajuste aplicable
5. registrar impacto sobre obligación y composición cuando corresponda
6. persistir de forma atómica
7. registrar outbox
8. devolver resultado

### Rectificación por índice
1. validar contexto técnico
2. cargar obligación y base de cálculo
3. validar índice aplicable
4. calcular diferencia
5. registrar ajuste
6. persistir y registrar outbox
7. devolver resultado

### Crédito / débito manual
1. validar contexto técnico y autorización
2. cargar obligación objetivo
3. validar procedencia del ajuste
4. registrar impacto manual
5. persistir y registrar outbox
6. devolver resultado

### Consulta
1. validar parámetros de lectura
2. cargar ajustes aplicados
3. relacionar ajuste con obligación y composición
4. devolver vista consolidada

## Validaciones clave
- obligación financiera existente
- estado compatible con ajuste
- no confundir ajuste con pago o imputación
- coherencia entre importe del ajuste y saldo objetivo
- índice existente y válido cuando corresponda
- autorización válida para créditos o débitos manuales
- idempotencia en operaciones write

## Efectos transaccionales
- actualización de obligacion_financiera cuando corresponda
- actualización de composicion_obligacion cuando corresponda
- registro de movimiento_financiero asociado cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias

### Hacia arriba
- deuda emitida previamente
- índices financieros vigentes cuando apliquen
- permisos y autorizaciones para ajustes financieros

### Hacia abajo
- cronograma y lectura de deuda
- emisión financiera
- analítica financiera
- reportes de saldo y ajuste

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-004-gestion-de-indices-financieros]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- [[RN-FIN]]
- [[ERR-FIN]]
- DER financiero

## Pendientes abiertos
- política exacta de cálculo de mora y punitorios
- criterio definitivo de rectificación por índice versus reemisión
- catálogo final de motivos autorizados para créditos y débitos manuales
- estrategia de impacto por obligación completa versus composición específica
- trazabilidad exacta entre ajuste financiero y movimiento financiero asociado
