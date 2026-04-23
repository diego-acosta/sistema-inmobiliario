# SRV-ADM-006 — Consulta y reporte administrativo

## Objetivo
Proveer una capa de lectura consolidada del dominio administrativo, permitiendo consultar usuarios, roles, permisos, autorizaciones, auditoría y configuraciones del sistema, con trazabilidad completa, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de usuarios
- consulta de roles y permisos
- consulta de autorizaciones
- consulta de auditoría
- consulta de configuraciones
- trazabilidad administrativa completa
- búsqueda administrativa
- reporte consolidado del dominio

No cubre:
- operaciones de alta, modificación o baja
- autenticación técnica
- ejecución de lógica de autorización
- analítica avanzada o BI

## Entidades principales
- usuario
- rol_administrativo
- permiso
- usuario_rol
- rol_permiso
- autorizacion
- solicitud_autorizacion
- auditoria_evento
- configuracion_parametro

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual del dominio administrativo.

### Consulta histórica
Permite reconstruir la evolución administrativa.

### Búsqueda
Permite localizar información administrativa por múltiples criterios.

### Reporte consolidado
Permite obtener una vista integrada del dominio.

## Entradas conceptuales

### Parámetros de consulta
- identificador de usuario
- identificador de rol
- identificador de permiso
- tipo de autorización
- tipo de evento de auditoría
- clave de configuración
- estado
- rango de fechas
- criterios de búsqueda

## Resultado esperado

- usuarios
- roles
- permisos
- asignaciones
- autorizaciones
- auditoría
- configuraciones
- estados administrativos
- trazabilidad completa
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros
2. resolver entidades objetivo
3. cargar usuarios
4. integrar roles y permisos
5. integrar autorizaciones
6. integrar auditoría
7. integrar configuraciones
8. consolidar vista
9. devolver resultado

## Validaciones clave
- consistencia de parámetros
- coherencia de filtros
- existencia de entidades cuando corresponda
- control de acceso a información sensible

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- existencia de información administrativa
- integridad del dominio administrativo
- permisos de consulta

### Hacia abajo
- todos los dominios funcionales del sistema
- reportes externos
- auditoría y cumplimiento

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-ADMINISTRATIVO]]
- [[CU-ADM]]
- [[RN-ADM]]
- [[ERR-ADM]]
- [[EVT-ADM]]
- [[EST-ADM]]
- [[SRV-ADM-001-gestion-de-usuarios]]
- [[SRV-ADM-002-gestion-de-roles-y-permisos]]
- [[SRV-ADM-003-gestion-de-autorizaciones]]
- [[SRV-ADM-004-gestion-de-auditoria]]
- [[SRV-ADM-005-gestion-de-configuracion-y-parametrizacion]]
- DER administrativo

## Pendientes abiertos
- definición de reportes administrativos estándar
- criterios de búsqueda avanzada
- integración con analítica
- políticas de acceso a información sensible
- límites entre consulta operativa y BI
