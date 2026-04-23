# SRV-OPE-003 — Gestión de caja operativa

## Objetivo
Gestionar la caja operativa del sistema, permitiendo su apertura, control de estado, cierre y consulta, preservando consistencia operativa y trazabilidad de las operaciones.

## Alcance
Este servicio cubre:
- apertura de caja
- cambio de estado de caja
- cierre de caja
- consulta de estado de caja
- vinculación con instalación y usuario

No cubre:
- registro de movimientos financieros
- imputación financiera
- conciliación contable
- gestión de obligaciones o pagos

## Entidades principales
- caja_operativa
- instalacion
- sucursal
- usuario

## Modos del servicio

### Apertura
Permite iniciar una nueva caja operativa.

### Cambio de estado
Permite actualizar el estado de la caja (activa, suspendida, etc.).

### Cierre
Permite cerrar la caja operativa.

### Consulta
Permite visualizar estado y datos de la caja.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de instalación
- usuario responsable
- estado inicial
- fecha de apertura
- fecha de cierre cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de caja
- instalación
- estado
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de caja
- instalación asociada
- estado resultante
- vigencia
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- caja operativa
- estado
- instalación
- usuario responsable
- fechas de apertura y cierre

## Flujo de alto nivel

### Apertura
1. validar contexto técnico e idempotencia
2. validar existencia de instalación
3. validar que no exista caja activa cuando corresponda
4. registrar apertura de caja
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Cambio de estado
1. validar contexto técnico
2. cargar caja existente
3. validar versión esperada
4. validar transición de estado
5. aplicar cambio
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Cierre
1. validar contexto técnico
2. cargar caja activa
3. validar condiciones de cierre
4. registrar cierre
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar cajas operativas
3. devolver vista de lectura

## Validaciones clave
- instalación existente
- no existencia de múltiples cajas activas por instalación cuando no corresponda
- coherencia de estados
- consistencia temporal (apertura/cierre)
- control de versionado
- idempotencia en apertura

## Efectos transaccionales
- alta o actualización de caja_operativa
- vinculación con instalación y usuario
- actualización de estado y vigencias
- aplicación de borrado lógico cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- instalación existente
- sucursal válida
- usuario válido
- contexto técnico válido
- permisos sobre caja operativa

### Hacia abajo
- [[SRV-OPE-004-gestion-de-movimientos-de-caja]]
- dominio financiero
- reportes operativos

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-OPERATIVO]]
- [[CU-OPE]]
- [[RN-OPE]]
- [[ERR-OPE]]
- [[EVT-OPE]]
- [[EST-OPE]]
- [[SRV-OPE-001-gestion-de-sucursales]]
- [[SRV-OPE-002-gestion-de-instalaciones]]
- DER operativo

## Pendientes abiertos
- catálogo final de estados de caja
- reglas de apertura por usuario/instalación
- condiciones obligatorias de cierre
- integración con arqueo de caja
- políticas de control concurrente
