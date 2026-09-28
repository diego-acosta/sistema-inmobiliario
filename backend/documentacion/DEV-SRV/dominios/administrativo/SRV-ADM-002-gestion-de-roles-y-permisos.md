# SRV-ADM-002 — Gestión de roles y permisos

## Contrato central D1 — PR04

[DEV-ARCH-GEN-003 §5](../../../DEV-ARCH/DEV-ARCH-GEN-003.md#5-d1-cerrada--autorización-global-y-contextual-pr04)
es la fuente única de composición GLOBAL/SUCURSAL, deny, contexto de request y
replay humano. D1 está cerrada contractualmente; runtime general pendiente de
PR05 y D2 abierta. Los nombres conceptuales heredados de este documento no crean
tablas distintas de las inventariadas allí ni habilitan herencia entre roles.

## Objetivo
Gestionar roles y permisos del sistema, permitiendo su definición, modificación, asignación, baja lógica y consulta, preservando consistencia administrativa y trazabilidad.

## Alcance
Este servicio cubre:
- alta de roles
- modificación de roles
- baja lógica de roles
- definición de permisos
- asignación de permisos a roles
- asignación de roles a usuarios
- consulta de roles, permisos y asignaciones

No cubre:
- autenticación técnica
- evaluación en línea de autorización de una operación específica
- auditoría administrativa
- configuración global del sistema

## Prerrequisito de autorización central para grants

El permiso activo `ADMIN.SEGURIDAD.GRANTS.ADMINISTRAR` (`Administrar grants de
seguridad`) es una capacidad D1 `GLOBAL` para asignar y revocar roles de
seguridad de usuarios. Su receptor canónico inicial es el rol activo
`ADMINISTRADOR_SISTEMA`; D1 seguirá autorizando por permiso efectivo y no por el
código del rol.

La materialización no migra los dos endpoints productivos, no agrega
`uid_global` a `usuario_rol_seguridad` y no define todavía su target idempotente
central.

## Entidades principales
- rol_administrativo
- permiso
- rol_permiso
- usuario_rol

## Modos del servicio

### Definición de rol
Permite registrar y modificar roles del sistema.

### Definición de permiso
Permite registrar y modificar permisos disponibles.

### Asignación
Permite asignar permisos a roles y roles a usuarios.

### Baja lógica
Permite invalidar roles, permisos o asignaciones.

### Consulta
Permite visualizar roles, permisos y relaciones de asignación.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de rol cuando corresponda
- identificador de permiso cuando corresponda
- identificador de usuario cuando corresponda
- nombre de rol
- nombre o código de permiso
- alcance o contexto cuando corresponda
- estado
- observaciones

### Parámetros de consulta
- identificador de rol
- identificador de permiso
- identificador de usuario
- estado
- contexto de asignación cuando corresponda

## Resultado esperado

### Para operaciones write
- identificador de rol, permiso o asignación
- estado resultante
- relaciones de asignación actualizadas
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de roles
- listado de permisos
- asignaciones usuario-rol
- asignaciones rol-permiso
- estados y alcances

## Flujo de alto nivel

### Definición de rol o permiso
1. validar contexto técnico e idempotencia
2. validar consistencia de datos
3. registrar o actualizar rol o permiso
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Asignación
1. validar contexto técnico
2. cargar usuario, rol o permiso existente
3. validar elegibilidad de asignación
4. registrar asignación
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar entidad o asignación
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar roles, permisos y asignaciones
3. devolver vista de lectura

## Validaciones clave
- usuario existente cuando corresponda
- rol existente cuando corresponda
- permiso existente cuando corresponda
- no duplicidad indebida de asignaciones
- coherencia de alcance o contexto
- control de versionado
- idempotencia en altas y asignaciones

## Efectos transaccionales
- alta o actualización de rol_administrativo
- alta o actualización de permiso
- alta o actualización de rol_permiso
- alta o actualización de usuario_rol
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- usuarios existentes cuando corresponda
- contexto técnico válido
- permisos sobre gestión administrativa

### Hacia abajo
- [[SRV-ADM-003-gestion-de-autorizaciones]]
- [[SRV-ADM-004-gestion-de-auditoria]]
- todos los dominios funcionales del sistema

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
- DER administrativo

## Pendientes abiertos
- catálogo final de permisos del sistema
- materialización de alcances D1 cerrados en GEN-003 §5 (sin instalación objetivo)
- administración de asignaciones; D1 no incorpora herencia entre roles
- gestión de concesiones por roles y denegaciones existentes; D1 no introduce permisos directos
- relación con autenticación externa
