# SRV-PER-003 — Gestión de domicilios y contactos

## Objetivo
Gestionar domicilios y medios de contacto asociados a la persona, permitiendo registrar, modificar, invalidar y consultar información de localización y comunicación, preservando consistencia y trazabilidad.

## Alcance
Este servicio cubre:
- alta de domicilios
- modificación de domicilios
- baja lógica de domicilios
- alta de medios de contacto (teléfono, email u otros)
- modificación de medios de contacto
- baja lógica de medios de contacto
- consulta de domicilios y contactos asociados a persona

No cubre:
- alta de persona base
- identificación documental
- relaciones entre personas
- representación legal
- clasificación funcional de persona

## Entidades principales
- persona_domicilio
- persona_contacto

## Modos del servicio

### Gestión de domicilios
Permite administrar múltiples domicilios asociados a una persona.

### Gestión de contactos
Permite administrar múltiples medios de contacto asociados a una persona.

### Consulta
Permite visualizar domicilios y contactos de una persona.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio

#### Domicilios
- identificador de persona
- tipo de domicilio
- dirección completa
- localidad
- provincia
- país
- estado del domicilio
- indicador de domicilio principal cuando corresponda
- observaciones

#### Contactos
- identificador de persona
- tipo de contacto (teléfono, email, etc.)
- valor del contacto
- estado del contacto
- indicador de contacto principal cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de persona
- tipo de domicilio o contacto
- estado
- criterio de principalidad

## Resultado esperado

### Para operaciones write
- identificador de domicilio o contacto
- persona asociada
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de domicilios
- listado de contactos
- indicadores de principalidad
- estado de cada registro

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. cargar persona existente
3. validar consistencia de datos
4. registrar domicilio o contacto
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar registro existente
3. validar versión esperada
4. aplicar cambios
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar registro
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar domicilios y contactos
3. devolver vista de lectura

## Validaciones clave
- persona existente
- consistencia de estructura de domicilio
- formato válido de contacto
- control de duplicidad cuando la política lo requiera
- control de principalidad única cuando corresponda
- control de versionado
- idempotencia en altas

## Efectos transaccionales
- alta o actualización de persona_domicilio
- alta o actualización de persona_contacto
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- persona existente
- contexto técnico válido
- permisos sobre gestión de datos de contacto

### Hacia abajo
- notificaciones
- comunicación con clientes
- procesos comerciales y contractuales

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
- DER de personas

## Pendientes abiertos
- catálogo final de tipos de domicilio
- catálogo final de tipos de contacto
- política de principalidad
- validaciones de formato por tipo de contacto
- integración futura con servicios de validación externa
