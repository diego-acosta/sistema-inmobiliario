# SRV-OPE-005 — Gestión de cierre de caja

## Objetivo
Gestionar el cierre de caja operativa, permitiendo consolidar movimientos, registrar resultados de cierre y finalizar la vigencia de la caja, preservando consistencia operativa y trazabilidad.

## Alcance
Este servicio cubre:
- ejecución de cierre de caja
- consolidación de movimientos
- registro de totales y diferencias
- registro de observaciones de cierre
- consulta de cierres de caja

No cubre:
- apertura de caja
- registro de movimientos de caja
- conciliación contable formal
- imputación financiera

## Entidades principales
- cierre_caja
- caja_operativa
- movimiento_caja

## Modos del servicio

### Cierre
Permite ejecutar el cierre de una caja operativa.

### Consulta
Permite visualizar cierres de caja.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- caja_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de caja
- totales calculados
- totales declarados cuando corresponda
- diferencias detectadas
- observaciones
- fecha de cierre

### Parámetros de consulta
- identificador de caja
- rango de fechas
- estado de cierre

## Resultado esperado

### Para operaciones write
- identificador de cierre
- caja asociada
- totales registrados
- diferencias
- estado resultante de la caja
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- cierres de caja
- totales
- diferencias
- fechas
- observaciones

## Flujo de alto nivel

### Cierre
1. validar contexto técnico e idempotencia
2. cargar caja operativa activa
3. validar condiciones de cierre
4. consolidar movimientos de caja
5. calcular totales
6. registrar cierre de caja
7. actualizar estado de caja a cerrada
8. persistir cambios de forma atómica
9. registrar outbox
10. devolver resultado

### Consulta
1. validar parámetros
2. cargar cierres de caja
3. devolver vista de lectura

## Validaciones clave
- caja operativa activa
- existencia de movimientos
- consistencia de totales
- coherencia de diferencias
- no cierre duplicado
- control de versionado
- idempotencia en cierre

## Efectos transaccionales
- alta de cierre_caja
- actualización de caja_operativa (estado cerrado)
- consolidación de movimiento_caja
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- caja operativa activa
- movimientos de caja existentes
- contexto técnico válido
- permisos sobre cierre de caja

### Hacia abajo
- reportes operativos
- dominio financiero
- auditoría administrativa

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
- [[SRV-OPE-004-gestion-de-movimientos-de-caja]]
- DER operativo

## Pendientes abiertos
- reglas de tolerancia de diferencias
- integración con arqueo físico
- políticas de reapertura de caja
- control de cierre por usuario
- validaciones adicionales previas al cierre
