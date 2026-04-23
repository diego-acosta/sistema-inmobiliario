# SRV-OPE-006 — Consulta y reporte operativo

## Objetivo
Proveer una capa de lectura consolidada del dominio operativo, permitiendo consultar sucursales, instalaciones, cajas operativas, movimientos y cierres, con trazabilidad completa, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de sucursales
- consulta de instalaciones
- consulta de cajas operativas
- consulta de movimientos de caja
- consulta de cierres de caja
- trazabilidad operativa completa
- búsqueda operativa
- reporte consolidado del dominio operativo

No cubre:
- operaciones de alta, modificación o baja
- gestión de movimientos financieros complejos
- analítica avanzada o BI

## Entidades principales
- sucursal
- instalacion
- caja_operativa
- movimiento_caja
- cierre_caja

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual del dominio operativo.

### Consulta histórica
Permite reconstruir la evolución operativa.

### Búsqueda
Permite localizar información operativa por múltiples criterios.

### Reporte consolidado
Permite obtener una vista integrada del dominio.

## Entradas conceptuales

### Parámetros de consulta
- identificador de sucursal
- identificador de instalación
- identificador de caja
- estado de caja
- tipo de movimiento
- rango de fechas
- usuario responsable
- criterios de búsqueda

## Resultado esperado

- sucursales
- instalaciones
- cajas operativas
- movimientos de caja
- cierres de caja
- estados operativos
- trazabilidad completa
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros
2. resolver entidades objetivo
3. cargar sucursales
4. cargar instalaciones
5. cargar cajas operativas
6. integrar movimientos de caja
7. integrar cierres de caja
8. consolidar vista
9. devolver resultado

## Validaciones clave
- consistencia de parámetros
- coherencia de filtros
- existencia de entidades cuando corresponda
- control de acceso a información

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- existencia de información operativa
- integridad del dominio operativo
- permisos de consulta

### Hacia abajo
- dominio financiero
- dominio administrativo
- reportes externos

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
- [[SRV-OPE-003-gestion-de-caja-operativa]]
- [[SRV-OPE-004-gestion-de-movimientos-de-caja]]
- [[SRV-OPE-005-gestion-de-cierre-de-caja]]
- DER operativo

## Pendientes abiertos
- definición de reportes operativos estándar
- criterios de búsqueda avanzada
- integración con financiero para reportes mixtos
- límites entre operación y analítica
- políticas de acceso a información sensible
