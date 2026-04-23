# SRV-PER-005 — Gestión de relaciones y representación

## Objetivo
Gestionar relaciones y vínculos de representación entre personas, permitiendo registrar, modificar, invalidar y consultar asociaciones funcionales o legales, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- alta de relación entre personas
- modificación de relación
- baja lógica de relación
- gestión de representación legal o funcional
- consulta de relaciones asociadas a una persona

No cubre:
- alta de persona base
- identificación documental
- domicilios y contactos
- clasificación funcional
- participación en operaciones específicas

## Entidades principales
- persona_relacion
- representacion_poder

## Modos del servicio

### Alta
Permite registrar una relación entre dos personas.

### Modificación
Permite actualizar atributos de la relación o representación.

### Baja lógica
Permite invalidar una relación sin eliminarla físicamente.

### Consulta
Permite visualizar relaciones y representaciones asociadas a una persona.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de persona origen
- identificador de persona destino
- tipo de relación (familiar, comercial, legal, etc.)
- tipo de representación cuando corresponda
- alcance de la representación
- vigencia desde / hasta cuando corresponda
- estado de la relación
- observaciones

### Parámetros de consulta
- identificador de persona
- tipo de relación
- tipo de representación
- estado
- vigencia

## Resultado esperado

### Para operaciones write
- identificador de relación
- personas asociadas
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de relaciones
- tipo de relación
- tipo de representación
- vigencia
- estado

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. cargar personas involucradas
3. validar consistencia de relación
4. registrar relación o representación
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar relación existente
3. validar versión esperada
4. aplicar cambios
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar relación
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar relaciones
3. devolver vista de lectura

## Validaciones clave
- existencia de ambas personas
- coherencia del tipo de relación
- validez del tipo de representación
- no duplicidad indebida de relación activa cuando la política lo restrinja
- consistencia de vigencia
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de persona_relacion
- alta o actualización de representacion_poder cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- personas existentes
- contexto técnico válido
- catálogo de tipos de relación

### Hacia abajo
- lógica contractual
- lógica comercial
- validación de representación en operaciones

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-PERSONAS]]
- [[CU-PER]]
- [[RN-PER]]
- [[ERR-PER]]
- [[EVT-PER]]
- [[EST-PER]]
- [[SRV-PER-001-gestion-de-persona-base]]
- [[SRV-PER-002-gestion-identificatoria]]
- [[SRV-PER-003-gestion-de-domicilios-y-contactos]]
- [[SRV-PER-004-gestion-de-clasificacion-y-condicion]]
- DER de personas

## Pendientes abiertos
- catálogo final de tipos de relación
- catálogo de tipos de representación
- reglas de exclusividad o coexistencia de relaciones
- definición exacta del alcance de poderes
- integración futura con validación documental de poderes
