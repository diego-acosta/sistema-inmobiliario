# SRV-OPE-004 — Gestión de movimientos de caja

## Objetivo
Gestionar movimientos de caja operativa, permitiendo registrar ingresos, egresos, anulación y consulta de movimientos, preservando consistencia operativa y trazabilidad financiera.

## Alcance
Este servicio cubre:
- registro de ingresos
- registro de egresos
- anulación de movimientos
- consulta de movimientos de caja
- vinculación con operaciones financieras

No cubre:
- apertura o cierre de caja
- imputación financiera
- generación de obligaciones
- conciliación contable

## Entidades principales
- movimiento_caja
- caja_operativa
- movimiento_financiero cuando corresponda

## Modos del servicio

### Registro
Permite registrar un movimiento de caja.

### Anulación
Permite invalidar un movimiento registrado.

### Consulta
Permite visualizar movimientos de caja.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- caja_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de movimiento (ingreso / egreso)
- monto
- medio de pago cuando corresponda
- referencia a operación financiera
- fecha del movimiento
- observaciones

### Parámetros de consulta
- identificador de caja
- tipo de movimiento
- rango de fechas
- estado
- medio de pago

## Resultado esperado

### Para operaciones write
- identificador de movimiento
- caja asociada
- tipo de movimiento
- monto
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de movimientos
- tipo de movimiento
- monto
- estado
- medio de pago
- fechas

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar caja operativa activa
3. validar consistencia del movimiento
4. registrar movimiento de caja
5. generar o vincular movimiento financiero cuando corresponda
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Anulación
1. validar contexto técnico
2. cargar movimiento existente
3. validar anulabilidad
4. aplicar anulación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar movimientos de caja
3. devolver vista de lectura

## Validaciones clave
- caja operativa activa
- coherencia de tipo de movimiento
- consistencia de montos
- validez de medio de pago
- no duplicidad indebida
- anulabilidad según reglas funcionales
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de movimiento_caja
- vinculación con caja_operativa
- vinculación con movimiento_financiero cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- caja operativa activa
- contexto técnico válido
- permisos sobre caja operativa

### Hacia abajo
- [[SRV-OPE-005-gestion-de-cierre-de-caja]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- dominio financiero

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-OPERATIVO]]
- [[CU-OPE]]
- [[RN-OPE]]
- [[ERR-OPE]]
- [[EVT-OPE]]
- [[EST-OPE]]
- [[SRV-OPE-003-gestion-de-caja-operativa]]
- DER operativo
- DER financiero

## Pendientes abiertos
- catálogo final de medios de pago
- reglas de integración con financiero
- políticas de anulación
- control de duplicidad por op_id
- integración con arqueo de caja
