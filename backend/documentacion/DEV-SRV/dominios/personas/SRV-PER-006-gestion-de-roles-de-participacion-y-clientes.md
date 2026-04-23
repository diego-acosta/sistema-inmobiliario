# SRV-PER-006 — Gestión de roles de participación y clientes

## Objetivo
Gestionar asociaciones transversales entre persona y contextos operativos del sistema, permitiendo asignar, modificar, invalidar y consultar roles de participación y proyecciones funcionales heredadas como la condición de cliente, preservando consistencia técnica mínima y trazabilidad.

## Alcance
Este servicio cubre:
- asignación de roles de participación a personas
- modificación de roles
- baja lógica de roles
- gestión de asociaciones persona-contexto mediante `tipo_relacion` + `id_relacion`
- gestión de condición de cliente cuando exista soporte heredado en SQL
- consulta de roles y participación en operaciones

No cubre:
- alta de persona base
- identificación documental
- domicilios y contactos
- relaciones estructurales entre personas
- clasificación general de persona
- definición semántica de comprador, vendedor, locatario, garante u otros roles contextuales
- validaciones de negocio propias de comercial, locativo o financiero
- determinación de elegibilidad funcional por tipo de operación

## Entidades principales
- rol_participacion
- relacion_persona_rol
- cliente_comprador

Observación:
- `rol_participacion` y `relacion_persona_rol` se documentan aquí como soporte transversal de asociación y trazabilidad.
- `cliente_comprador` se mantiene por compatibilidad con el modelo físico heredado, pero no debe interpretarse como identidad base de persona.

## Modos del servicio

### Asignación
Permite asociar una persona con un contexto externo del sistema mediante un rol de participación.

### Modificación
Permite actualizar atributos de la asociación persona-contexto.

### Baja lógica
Permite invalidar una asociación sin eliminarla físicamente.

### Consulta
Permite visualizar asociaciones y participaciones contextuales de personas.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de persona
- identificador de operación o entidad origen mediante `tipo_relacion` + `id_relacion`
- identificador de rol de participación
- semántica contextual del rol cuando corresponda al dominio origen
- condición de cliente cuando corresponda como proyección funcional heredada
- estado del rol
- vigencia cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de persona
- identificador de operación
- tipo de rol
- estado
- condición de cliente

## Resultado esperado

### Para operaciones write
- identificador de rol o relación persona-rol
- persona asociada
- contexto asociado
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de roles de participación
- contexto asociado
- tipo de rol
- estado
- condición de cliente

## Flujo de alto nivel

### Asignación
1. validar contexto técnico e idempotencia
2. cargar persona existente
3. cargar contexto o entidad origen
4. validar consistencia técnica mínima de la asociación
5. registrar asociación de participación
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar rol existente
3. validar versión esperada
4. aplicar cambios
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar rol
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar roles de participación
3. devolver vista de lectura

## Validaciones clave
- persona existente
- contexto o entidad origen existente
- rol válido según catálogo
- no duplicidad indebida de asociación activa cuando la política técnica lo restrinja
- coherencia estructural entre `tipo_relacion`, `id_relacion` y entidad objetivo
- control de versionado
- idempotencia en asignación

Observación:
- este servicio no debe asumir reglas funcionales propias del dominio origen.
- la interpretación de roles como `comprador`, `vendedor`, `locatario` o `garante` pertenece al contexto que usa la asociación, no al núcleo semántico de `personas`.

## Efectos transaccionales
- alta o actualización de rol_participacion
- alta o actualización de relacion_persona_rol
- alta o actualización de cliente_comprador cuando corresponda por compatibilidad heredada
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- persona existente
- contexto o entidad origen válida
- contexto técnico válido
- catálogo de roles definido

### Hacia abajo
- dominios que consumen la asociación contextual, como comercial, locativo o financiero

## Advertencia arquitectónica
- Este modelo introduce acoplamiento entre `personas` y dominios contextuales del sistema.
- Su existencia responde a una decisión pragmática basada en SQL, endpoints e implementación actuales.
- `cliente_comprador` debe leerse como proyección funcional o especialización contextual heredada, no como identidad base de persona.
- El servicio actúa como gestor de asociaciones y trazabilidad, no como validador de negocio externo.
- No debe expandirse con nuevas reglas de `comercial`, `locativo` o `financiero` sin una decisión explícita de arquitectura.

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
- [[SRV-PER-005-gestion-de-relaciones-y-representacion]]
- DER de personas

## Pendientes abiertos
- catálogo final de roles de participación
- reglas de compatibilidad entre roles
- política de cliente único o múltiple
- relación exacta entre cliente y rol
- límite definitivo entre soporte transversal y semántica contextual de otros dominios
