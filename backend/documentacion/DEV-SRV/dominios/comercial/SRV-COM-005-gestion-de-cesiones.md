# SRV-COM-005 — Gestión de cesiones

## Objetivo
Gestionar la cesión de derechos sobre una operación de venta, permitiendo registrar, modificar, invalidar y consultar transferencias de titularidad o participación, preservando consistencia comercial y trazabilidad.

## Alcance
Este servicio cubre:
- registro de cesión de derechos
- modificación de cesión
- anulación o invalidación de cesión
- consulta de cesiones asociadas a una venta
- actualización de intervinientes en la operación

No cubre:
- creación de nuevas ventas independientes
- generación de condiciones comerciales
- generación directa de obligaciones financieras
- instrumentación legal completa de cesión
- escrituración

## Entidades principales
- cesion
- venta
- persona
- relacion_persona_rol

## Modos del servicio

### Registro
Permite registrar una cesión de derechos entre personas.

### Modificación
Permite actualizar atributos de una cesión cuando corresponda.

### Anulación
Permite invalidar una cesión previamente registrada.

### Consulta
Permite visualizar cesiones asociadas a una venta.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta
- persona cedente
- persona cesionaria
- tipo de cesión
- alcance de la cesión (total o parcial)
- fecha de cesión
- estado de la cesión
- observaciones

### Parámetros de consulta
- identificador de venta
- persona interviniente
- estado de cesión
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de cesión
- venta asociada
- personas involucradas
- estado resultante
- actualización de intervinientes cuando corresponda
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de cesiones
- personas involucradas
- estado de la cesión
- relación con la venta

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar venta existente
3. cargar personas involucradas
4. validar elegibilidad de cesión
5. registrar cesión
6. actualizar roles de participación cuando corresponda
7. persistir con metadatos transversales
8. registrar outbox
9. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar cesión existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Anulación
1. validar contexto técnico
2. cargar cesión
3. validar anulabilidad
4. registrar invalidación
5. revertir efectos cuando corresponda
6. persistir cambios
7. registrar outbox
8. devolver resultado

### Consulta
1. validar parámetros
2. cargar cesiones
3. devolver vista de lectura

## Validaciones clave
- venta existente
- personas existentes
- coherencia entre cedente y titular actual
- validez del alcance de cesión
- no superposición indebida de cesiones activas
- consistencia de estado
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de cesion
- actualización de roles de participación
- actualización de intervinientes de la venta
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- venta existente
- personas existentes
- roles de participación definidos
- contexto técnico válido

### Hacia abajo
- [[SRV-COM-006-gestion-de-escrituracion]]
- dominio financiero cuando corresponda ajuste de obligaciones
- procesos legales asociados a cesión

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- DER comercial

## Pendientes abiertos
- catálogo final de tipos de cesión
- reglas de cesión parcial
- impacto exacto en condiciones comerciales
- integración con dominio financiero
- validaciones legales externas
