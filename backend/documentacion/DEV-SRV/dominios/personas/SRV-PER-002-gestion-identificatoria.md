# SRV-PER-002 — Gestión identificatoria

## Objetivo
Gestionar la identificación documental asociada a la persona, permitiendo registrar, modificar, invalidar y consultar documentos identificatorios, preservando consistencia funcional y trazabilidad.

## Alcance
Este servicio cubre:
- alta de documento identificatorio
- modificación de datos identificatorios
- baja lógica de identificación
- consulta de identificaciones asociadas a persona
- control funcional de vigencia identificatoria cuando corresponda

No cubre:
- alta de persona base
- domicilios y contactos
- relaciones entre personas
- representación legal
- clasificación funcional de persona
- validaciones externas contra organismos

## Entidades principales
- persona_documento

## Modos del servicio

### Alta
Registra una identificación documental para una persona existente.

### Modificación
Actualiza datos de una identificación registrada.

### Baja lógica
Invalida funcionalmente una identificación sin eliminarla físicamente.

### Consulta
Permite visualizar identificaciones asociadas a una persona.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de persona
- tipo de documento
- número de documento
- país o jurisdicción cuando corresponda
- vigencia desde / hasta cuando corresponda
- estado identificatorio
- observaciones

### Parámetros de consulta
- identificador de persona
- tipo de documento
- número de documento
- estado
- criterios de vigencia

## Resultado esperado

### Para operaciones write
- identificador de documento de persona
- persona asociada
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado o detalle de identificaciones
- estado identificatorio
- vigencia visible cuando corresponda

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. cargar persona existente
3. validar consistencia identificatoria
4. registrar identificación
5. persistir con metadatos transversales
6. registrar outbox
7. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar identificación existente
3. validar versión esperada
4. aplicar cambios permitidos
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar identificación
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar identificaciones solicitadas
3. devolver vista de lectura

## Validaciones clave
- persona existente
- tipo documental válido
- consistencia entre tipo y número
- no duplicidad indebida de documento activo cuando la política lo restrinja
- control de vigencia cuando corresponda
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de persona_documento
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- persona existente y válida
- contexto técnico válido
- permisos sobre gestión identificatoria

### Hacia abajo
- consulta integral de personas
- procesos que requieren validación documental básica
- dominios que consumen identidad documental

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
- DER de personas

## Pendientes abiertos
- catálogo final de tipos documentales
- política de unicidad por tipo y número
- manejo exacto de vigencias y documentos históricos
- validaciones externas futuras por organismo o jurisdicción
