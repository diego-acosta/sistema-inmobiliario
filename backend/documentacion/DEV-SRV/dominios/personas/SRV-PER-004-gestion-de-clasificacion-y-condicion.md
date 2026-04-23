# SRV-PER-004 — Gestión de clasificación y condición

## Objetivo
Gestionar clasificaciones y condiciones auxiliares o heredadas asociadas a la persona dentro del sistema, permitiendo asignar, modificar, invalidar y consultar categorías generales cuando correspondan, preservando consistencia técnica mínima y trazabilidad.

## Alcance
Este servicio cubre:
- asignación de clasificación a persona
- modificación de clasificación
- baja lógica de clasificación
- consulta de clasificaciones asociadas a persona
- gestión de condiciones auxiliares de la persona cuando existan como soporte transversal o heredado

No cubre:
- alta de persona base
- identificación documental
- domicilios y contactos
- relaciones entre personas
- representación legal
- participación en operaciones específicas
- definición semántica de categorías funcionales propias de comercial, locativo o financiero
- determinación de elegibilidad de una persona como cliente, proveedor, titular, garante u otra condición contextual

## Entidades principales
- persona_clasificacion

Observación:
- `persona_clasificacion` se documenta aquí como soporte auxiliar o heredado del dominio.
- Las clasificaciones funcionales contextuales no deben interpretarse como identidad base de la persona.

## Modos del servicio

### Asignación
Permite asignar una clasificación a una persona.

### Modificación
Permite actualizar atributos o vigencias de la clasificación registrada.

### Baja lógica
Permite invalidar una clasificación sin eliminarla físicamente.

### Consulta
Permite visualizar las clasificaciones asociadas a una persona.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de persona
- tipo de clasificación general o auxiliar
- clasificación funcional heredada cuando corresponda
- estado de la clasificación
- vigencia desde / hasta cuando corresponda
- observaciones

Observación:
- categorías como `cliente`, `proveedor`, `titular`, `garante` u otras equivalentes no deben leerse aquí como esencia funcional del sujeto, sino como categorías heredadas o sujetas a revisión arquitectónica.

### Parámetros de consulta
- identificador de persona
- tipo de clasificación
- estado
- vigencia

## Resultado esperado

### Para operaciones write
- identificador de clasificación
- persona asociada
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de clasificaciones
- estado de cada clasificación
- vigencia visible cuando corresponda

## Flujo de alto nivel

### Asignación
1. validar contexto técnico e idempotencia
2. cargar persona existente
3. validar clasificación aplicable según catálogo disponible
4. registrar clasificación
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar clasificación existente
3. validar versión esperada
4. aplicar cambios
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar clasificación
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar clasificaciones
3. devolver vista de lectura

## Validaciones clave
- persona existente
- clasificación válida según catálogo
- no duplicidad indebida de clasificación activa cuando la política lo restrinja
- consistencia de vigencia
- control de versionado
- idempotencia en asignación

Observación:
- este servicio solo debe validar consistencia técnica y documental mínima de la clasificación registrada.
- no debe asumir reglas de negocio externas que definan si una persona es funcionalmente cliente, proveedor, titular o garante en otro dominio.

## Efectos transaccionales
- alta o actualización de persona_clasificacion
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- persona existente
- contexto técnico válido
- catálogo de clasificaciones definido

### Hacia abajo
- dominios que puedan consumir clasificaciones auxiliares o heredadas, cuando corresponda

## Advertencia arquitectónica
- Las clasificaciones funcionales pueden responder semánticamente a otros dominios del sistema.
- Su permanencia aquí responde a herencia documental o a soporte transversal auxiliar.
- Este servicio no debe consolidar como identidad base de persona categorías como `cliente`, `proveedor`, `titular`, `garante` u otras equivalentes.
- No debe expandirse con nuevas clasificaciones funcionales sin una decisión arquitectónica explícita.

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
- DER de personas

## Pendientes abiertos
- catálogo final de clasificaciones de persona
- política de exclusividad o coexistencia de clasificaciones
- definición exacta de vigencias
- reglas de transición entre estados de clasificación
- límite definitivo entre clasificación auxiliar en `personas` y semántica funcional de otros dominios
