# SRV-OPE-001 — Gestión de sucursales

## Objetivo
Gestionar sucursales del sistema, permitiendo su alta, modificación, baja lógica y consulta, preservando consistencia organizativa y trazabilidad.

## Alcance
Este servicio cubre:
- alta de sucursales
- modificación de sucursales
- baja lógica de sucursales
- consulta de sucursales
- definición de datos organizativos

No cubre:
- gestión de usuarios
- gestión de instalaciones
- gestión de caja operativa
- configuración de permisos

## Entidades principales
- sucursal

## Modos del servicio

### Alta
Permite registrar una nueva sucursal.

### Modificación
Permite actualizar datos de una sucursal.

### Baja lógica
Permite invalidar una sucursal.

### Consulta
Permite visualizar sucursales.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- nombre de sucursal
- identificador interno
- datos de ubicación
- estado
- observaciones

### Parámetros de consulta
- identificador de sucursal
- estado
- nombre

## Resultado esperado

### Para operaciones write
- identificador de sucursal
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de sucursales
- nombre
- estado
- datos organizativos

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos de sucursal
3. registrar sucursal
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar sucursal existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar sucursal
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar sucursales
3. devolver vista de lectura

## Validaciones clave
- consistencia de datos organizativos
- unicidad de identificador cuando corresponda
- no duplicidad indebida
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de sucursal
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión operativa

### Hacia abajo
- [[SRV-OPE-002-gestion-de-instalaciones]]
- [[SRV-OPE-003-gestion-de-caja-operativa]]
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
- DER operativo

## Pendientes abiertos
- catálogo final de tipos de sucursal
- reglas de unicidad organizativa
- relación con instalaciones
- integración con estructura administrativa
- políticas de activación/inactivación
