# SRV-OPE-002 — Gestión de instalaciones

## Objetivo
Gestionar instalaciones del sistema como unidad técnica real vinculada a una sucursal, permitiendo su alta, modificación, baja lógica y consulta, preservando consistencia operativa y trazabilidad técnica.

## Alcance
Este servicio cubre:
- alta de instalaciones
- modificación de instalaciones
- baja lógica de instalaciones
- consulta de instalaciones
- vinculación con sucursal
- definición de datos técnicos básicos

No cubre:
- gestión de sucursales
- gestión de usuarios
- gestión de caja operativa
- configuración de sincronización avanzada

## Entidades principales
- instalacion
- sucursal

## Modos del servicio

### Alta
Permite registrar una nueva instalación.

### Modificación
Permite actualizar datos de una instalación.

### Baja lógica
Permite invalidar una instalación.

### Consulta
Permite visualizar instalaciones y su relación con sucursal.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- instalacion_id_origen cuando corresponda
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador interno de instalación
- sucursal asociada
- nombre o descripción
- datos técnicos básicos
- estado
- observaciones

### Parámetros de consulta
- identificador de instalación
- sucursal asociada
- estado
- nombre o identificador interno

## Resultado esperado

### Para operaciones write
- identificador de instalación
- sucursal asociada
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de instalaciones
- sucursal asociada
- estado
- datos técnicos básicos

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. cargar sucursal existente
3. validar datos de instalación
4. registrar instalación
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar instalación existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar instalación
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar instalaciones
3. resolver sucursal asociada
4. devolver vista de lectura

## Validaciones clave
- sucursal existente
- consistencia de datos técnicos
- unicidad de identificador cuando corresponda
- no duplicidad indebida
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de instalacion
- vinculación con sucursal
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-OPE]]

## Dependencias

### Hacia arriba
- sucursal existente
- contexto técnico válido
- permisos sobre gestión operativa

### Hacia abajo
- [[SRV-OPE-003-gestion-de-caja-operativa]]
- trazabilidad técnica
- sincronización entre instalaciones
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
- DER operativo

## Pendientes abiertos
- catálogo final de tipos de instalación
- reglas de unicidad por sucursal
- atributos técnicos mínimos obligatorios
- relación exacta con sincronización técnica
- políticas de activación/inactivación
