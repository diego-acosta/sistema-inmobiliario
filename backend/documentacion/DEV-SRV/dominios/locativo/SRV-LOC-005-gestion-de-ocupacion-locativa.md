# SRV-LOC-005 — Gestión de ocupación locativa

## Objetivo
Gestionar la ocupación locativa de inmuebles y unidades funcionales, permitiendo registrar, modificar y consultar el uso efectivo bajo contratos de alquiler, preservando consistencia operativa y trazabilidad.

## Alcance
Este servicio cubre:
- registro de ocupación locativa
- actualización de ocupación
- finalización de ocupación
- consulta de ocupación vigente e histórica
- vinculación entre contrato y objeto locativo
- coordinación con disponibilidad del dominio inmobiliario

No cubre:
- gestión de contratos
- gestión de disponibilidad general del inmueble
- generación de obligaciones financieras
- gestión documental locativa

## Entidades principales
- ocupacion_locativa
- contrato_alquiler
- inmueble
- unidad_funcional

## Modos del servicio

### Registro de ocupación
Permite registrar el inicio de ocupación bajo un contrato.

### Actualización
Permite modificar datos de ocupación vigente.

### Finalización
Permite cerrar una ocupación locativa.

### Consulta
Permite visualizar ocupación vigente e histórica.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato
- identificador de inmueble o unidad funcional
- fecha de inicio de ocupación
- fecha de fin cuando corresponda
- estado de ocupación
- observaciones

### Parámetros de consulta
- identificador de contrato
- identificador de inmueble o unidad funcional
- estado de ocupación
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de ocupación locativa
- contrato asociado
- objeto locativo asociado
- estado resultante
- vigencia
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- ocupación vigente
- historial de ocupaciones
- contrato asociado
- objeto locativo
- vigencias

## Flujo de alto nivel

### Registro de ocupación
1. validar contexto técnico e idempotencia
2. cargar contrato vigente
3. cargar objeto locativo
4. validar elegibilidad para ocupación
5. registrar ocupación locativa
6. coordinar estado con dominio inmobiliario
7. persistir con metadatos transversales
8. registrar outbox
9. devolver resultado

### Actualización
1. validar contexto técnico
2. cargar ocupación existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Finalización
1. validar contexto técnico
2. cargar ocupación vigente
3. validar condiciones de cierre
4. aplicar finalización
5. coordinar liberación operativa cuando corresponda
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Consulta
1. validar parámetros
2. cargar ocupaciones
3. resolver vigencias
4. devolver vista de lectura

## Validaciones clave
- contrato vigente
- objeto locativo existente
- coherencia entre contrato y ocupación
- no superposición indebida de ocupaciones
- consistencia temporal
- coordinación con disponibilidad
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de ocupacion_locativa
- vinculación con contrato_alquiler
- vinculación con inmueble o unidad funcional
- cierre de vigencias anteriores cuando corresponda
- coordinación con estado de disponibilidad
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- contrato de alquiler existente
- inmueble o unidad funcional existente
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- [[SRV-INM-007-gestion-de-estado-disponibilidad-y-ocupacion]]
- dominio financiero
- procesos operativos

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
- [[SRV-INM-007-gestion-de-estado-disponibilidad-y-ocupacion]]
- DER locativo
- DER inmobiliario

## Pendientes abiertos
- catálogo final de estados de ocupación locativa
- reglas de sincronización con disponibilidad
- definición de ocupación parcial o múltiple
- integración con procesos de entrega y restitución
- criterios de control de inconsistencias
