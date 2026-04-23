# SRV-ADM-005 — Gestión de configuración y parametrización

## Objetivo
Gestionar la configuración y parametrización del sistema, permitiendo definir, modificar, invalidar y consultar parámetros operativos y funcionales, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- alta de parámetros de configuración
- modificación de parámetros
- baja lógica de parámetros
- consulta de configuraciones
- definición de parámetros globales y contextuales

No cubre:
- lógica de negocio específica
- ejecución de reglas funcionales
- gestión de usuarios o permisos
- auditoría en sí misma

## Entidades principales
- configuracion_parametro
- configuracion_contexto

## Modos del servicio

### Alta
Permite registrar un nuevo parámetro de configuración.

### Modificación
Permite actualizar un parámetro existente.

### Baja lógica
Permite invalidar un parámetro.

### Consulta
Permite visualizar parámetros configurados.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id cuando corresponda
- instalacion_id cuando corresponda
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- clave del parámetro
- valor
- tipo de dato
- alcance (global, sucursal, instalación)
- estado
- vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- clave de parámetro
- alcance
- sucursal o instalación cuando corresponda
- estado
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de parámetro
- clave y valor
- alcance aplicado
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de parámetros
- clave
- valor
- alcance
- estado
- vigencia

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos del parámetro
3. registrar configuración
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar parámetro existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar parámetro
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. resolver alcance aplicable
3. cargar configuraciones
4. devolver vista de lectura

## Validaciones clave
- coherencia de tipo de dato
- unicidad de clave por alcance
- consistencia de valores
- no duplicidad indebida
- coherencia de vigencias
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de configuracion_parametro
- vinculación con configuracion_contexto cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión administrativa

### Hacia abajo
- todos los dominios funcionales del sistema
- lógica de negocio configurable
- reportes administrativos

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-ADMINISTRATIVO]]
- [[CU-ADM]]
- [[RN-ADM]]
- [[ERR-ADM]]
- [[EVT-ADM]]
- [[EST-ADM]]
- DER administrativo

## Pendientes abiertos
- catálogo final de parámetros del sistema
- definición de tipos de datos soportados
- reglas de override por alcance
- estrategia de cacheo de configuración
- control de impacto de cambios en caliente
