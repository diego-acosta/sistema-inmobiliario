# SRV-LOC-003 — Gestión de garantías

## Objetivo
Gestionar garantías asociadas a contratos de alquiler, permitiendo su registro, modificación, validación, baja lógica y consulta, preservando consistencia contractual y trazabilidad.

## Alcance
Este servicio cubre:
- registro de garantías
- modificación de garantías
- validación de garantías
- baja lógica de garantías
- consulta de garantías
- vinculación con contrato y personas

No cubre:
- alta de contratos de alquiler
- ejecución judicial o financiera de garantías
- generación de obligaciones financieras
- documentación locativa general

## Entidades principales
- garantia
- contrato_alquiler
- persona
- documento_logico cuando corresponda

## Modos del servicio

### Registro
Permite registrar una nueva garantía asociada a un contrato.

### Modificación
Permite actualizar datos de una garantía existente.

### Validación
Permite validar o aprobar una garantía según reglas del negocio.

### Baja lógica
Permite invalidar una garantía sin eliminarla físicamente.

### Consulta
Permite visualizar garantías asociadas a contratos.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato
- tipo de garantía (propietaria, seguro, recibo, depósito, etc.)
- personas vinculadas cuando corresponda
- datos de la garantía
- estado de la garantía
- vigencia desde / hasta cuando corresponda
- observaciones

### Parámetros de consulta
- identificador de contrato
- tipo de garantía
- estado
- persona vinculada
- vigencia

## Resultado esperado

### Para operaciones write
- identificador de garantía
- contrato asociado
- tipo de garantía
- estado resultante
- vigencia
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de garantías
- tipo de garantía
- estado
- personas vinculadas
- vigencias

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar contrato existente
3. validar datos de la garantía
4. registrar garantía
5. vincular personas cuando corresponda
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar garantía existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Validación
1. validar contexto técnico
2. cargar garantía
3. evaluar condiciones de validación
4. aplicar cambio de estado
5. persistir actualización
6. registrar outbox
7. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar garantía
3. validar condiciones de baja
4. aplicar baja lógica
5. persistir
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar garantías
3. devolver vista de lectura

## Validaciones clave
- contrato existente
- coherencia del tipo de garantía
- consistencia de datos asociados
- validez de personas vinculadas
- no duplicidad indebida cuando corresponda
- consistencia de vigencias
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de garantia
- vinculación con contrato_alquiler
- vinculación con persona cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- contrato de alquiler existente
- personas existentes cuando corresponda
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- [[SRV-LOC-004-gestion-de-renovaciones-y-rescisiones]]
- dominio financiero
- procesos legales cuando corresponda

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-LOCATIVO]]
- [[CU-LOC]]
- [[RN-LOC]]
- [[ERR-LOC]]
- [[EVT-LOC]]
- [[EST-LOC]]
- [[SRV-LOC-001-gestion-de-contratos-de-alquiler]]
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- DER locativo

## Pendientes abiertos
- catálogo final de tipos de garantías
- reglas de validación por tipo
- criterios de aceptación/rechazo
- integración con scoring o evaluación externa
- tratamiento de garantías múltiples por contrato
