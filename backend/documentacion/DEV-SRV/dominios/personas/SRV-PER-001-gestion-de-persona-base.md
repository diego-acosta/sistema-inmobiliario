# SRV-PER-001 — Gestión de persona base

## Objetivo
Gestionar la entidad persona como unidad base del sistema, permitiendo su alta, modificación, baja lógica y consulta, garantizando identidad consistente y trazabilidad transversal.

## Alcance
Este servicio cubre:
- alta de persona
- modificación de datos base
- baja lógica de persona
- consulta básica de persona

No cubre:
- documentos identificatorios
- domicilios y contactos
- relaciones entre personas
- representación legal
- clasificación o roles
- validaciones documentales externas

## Entidades principales
- persona

## Modos del servicio

### Alta
Registra una nueva persona en el sistema.

### Modificación
Actualiza datos base de una persona existente.

### Baja lógica
Invalida funcionalmente una persona sin eliminarla físicamente.

### Consulta
Permite visualizar los datos base de una persona.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de persona (física o jurídica)
- nombre o razón social
- estado base de la persona
- observaciones cuando corresponda

### Parámetros de consulta
- identificador de persona
- nombre o razón social
- estado
- criterios básicos de búsqueda

## Resultado esperado

### Para operaciones write
- identificador de persona
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- datos base de la persona
- estado de la persona
- identificador

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos base
3. crear entidad persona
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar persona existente
3. validar versión esperada
4. aplicar cambios
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar persona
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar persona
3. devolver datos base

## Validaciones clave
- consistencia de tipo de persona
- existencia previa en modificación y baja
- control de versionado
- idempotencia en alta
- integridad básica de datos

## Efectos transaccionales
- alta o actualización de persona
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión de personas

### Hacia abajo
- identificación documental (SRV-PER-002)
- domicilios y contactos (SRV-PER-003)
- relaciones y representación (SRV-PER-005)
- dominios que consumen persona

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-PERSONAS]]
- [[CU-PER]]
- [[RN-PER]]
- [[ERR-PER]]
- [[EVT-PER]]
- [[EST-PER]]
- DER de personas

## Pendientes abiertos
- definición completa de atributos base de persona
- normalización de tipo de persona
- política de baja lógica y reactivación
- reglas de unicidad base
