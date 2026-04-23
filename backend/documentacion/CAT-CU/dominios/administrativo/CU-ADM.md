# CU-ADM — Casos de uso del dominio Administrativo

## Objetivo
Definir los casos de uso administrativos del sistema.

## Alcance
Incluye usuarios, roles, permisos, configuración y auditoría.

---

## A. Gestión de usuarios

### CU-ADM-001 — Alta de usuario
- tipo: write
- objetivo: Registrar un nuevo usuario administrativo dentro del sistema.
- entidades: usuario
- criticidad: alta

### CU-ADM-002 — Modificación de usuario
- tipo: write
- objetivo: Actualizar datos relevantes de un usuario existente.
- entidades: usuario
- criticidad: alta

### CU-ADM-003 — Baja lógica de usuario
- tipo: write
- objetivo: Dar de baja lógica a un usuario como baja funcional de mayor nivel, potencialmente irreversible o de largo plazo, preservando su trazabilidad histórica.
- entidades: usuario
- criticidad: alta

### CU-ADM-004 — Activación de usuario
- tipo: write
- objetivo: Habilitar un usuario para uso operativo dentro del sistema.
- entidades: usuario
- criticidad: alta

### CU-ADM-005 — Desactivación de usuario
- tipo: write
- objetivo: Inhabilitar operativamente un usuario de forma reversible, sin implicar eliminación funcional ni pérdida de historial.
- entidades: usuario
- criticidad: alta

### CU-ADM-006 — Consulta de usuario
- tipo: read
- objetivo: Consultar información operativa y de estado de un usuario.
- entidades: usuario
- criticidad: media

### CU-ADM-021 — Consulta de usuarios
- tipo: read
- objetivo: Listar y filtrar usuarios según criterios administrativos.
- entidades: usuario
- criticidad: media

## B. Gestión de roles y permisos

### CU-ADM-007 — Alta de rol
- tipo: write
- objetivo: Registrar un nuevo rol administrativo o de seguridad.
- entidades: rol
- criticidad: alta

### CU-ADM-008 — Modificación de rol
- tipo: write
- objetivo: Actualizar definición o alcance de un rol existente.
- entidades: rol
- criticidad: alta

### CU-ADM-009 — Baja de rol
- tipo: write
- objetivo: Dar de baja un rol preservando trazabilidad de sus asignaciones previas.
- entidades: rol
- criticidad: alta

### CU-ADM-010 — Asignación de rol a usuario
- tipo: write
- objetivo: Vincular un rol a un usuario para habilitar permisos administrativos.
- entidades: usuario, rol, permiso
- criticidad: crítica

### CU-ADM-011 — Remoción de rol
- tipo: write
- objetivo: Quitar un rol previamente asignado a un usuario.
- entidades: usuario, rol
- criticidad: alta

### CU-ADM-012 — Consulta de roles
- tipo: read
- objetivo: Consultar roles disponibles, vigentes o asignados.
- entidades: rol
- criticidad: media

### CU-ADM-013 — Consulta de permisos
- tipo: read
- objetivo: Consultar permisos definidos y su relación con roles administrativos.
- entidades: permiso, rol
- criticidad: media

### CU-ADM-022 — Gestión de permisos
- tipo: write
- objetivo: Crear o modificar permisos administrativos del sistema.
- entidades: permiso
- criticidad: crítica

## C. Configuración del sistema

### CU-ADM-014 — Modificación de parámetros del sistema
- tipo: write
- objetivo: Actualizar parámetros generales o administrativos del sistema.
- entidades: parametro_sistema, configuracion_sistema
- criticidad: crítica

### CU-ADM-015 — Consulta de configuración
- tipo: read
- objetivo: Consultar la configuración general vigente del sistema.
- entidades: configuracion_sistema, parametro_sistema
- criticidad: media

### CU-ADM-016 — Activación o desactivación de funcionalidades
- tipo: write
- objetivo: Habilitar o deshabilitar funcionalidades configurables del sistema.
- entidades: configuracion_sistema, funcionalidad
- criticidad: crítica

## D. Auditoría y trazabilidad

### CU-ADM-017 — Consulta de auditoría de operaciones
- tipo: read
- objetivo: Consultar auditoría administrativa de operaciones relevantes del sistema.
- entidades: evento_auditoria
- criticidad: alta

### CU-ADM-018 — Consulta de historial de cambios
- tipo: read
- objetivo: Consultar el historial de cambios administrativos sobre usuarios, roles, permisos o configuración.
- entidades: evento_auditoria, historial_cambios
- criticidad: alta

### CU-ADM-019 — Consulta por op_id
- tipo: read
- objetivo: Consultar trazabilidad administrativa, técnica y funcional vinculada a una operación identificada por `op_id`.
- entidades: evento_auditoria, op_id
- criticidad: alta

### CU-ADM-020 — Consulta de eventos administrativos
- tipo: read
- objetivo: Consultar eventos administrativos relevantes para control y trazabilidad.
- entidades: evento_auditoria
- criticidad: media

---

## Reglas

1. No duplicar casos.
2. No mezclar con dominios funcionales.
3. Mantener coherencia con CORE-EF.
4. No incluir lógica de negocio.
5. Mantener numeración CU-ADM-XXX.

---

## Notas

- Este dominio es transversal a todo el sistema.
- No ejecuta lógica de negocio, solo la controla.
- Es clave para seguridad y trazabilidad.
