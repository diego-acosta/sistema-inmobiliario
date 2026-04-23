# SRV-COM-004 — Gestión de instrumentos de compraventa

## Objetivo
Gestionar los instrumentos jurídicos de la compraventa, permitiendo generar, modificar, invalidar y consultar documentos formales asociados a una venta, preservando trazabilidad documental y consistencia comercial.

## Alcance
Este servicio cubre:
- generación de instrumentos de compraventa
- modificación de instrumentos
- anulación o invalidación de instrumentos
- consulta de instrumentos asociados a una venta
- vinculación entre venta e instrumento documental

No cubre:
- alta de venta
- definición de condiciones comerciales
- generación de obligaciones financieras
- escrituración final
- almacenamiento documental general
- gestión de plantillas documentales globales

## Entidades principales
- documento_logico
- instrumento_compraventa
- venta

## Modos del servicio

### Generación
Permite crear un instrumento jurídico asociado a una venta.

### Modificación
Permite actualizar datos del instrumento cuando la política lo permita.

### Anulación
Permite invalidar un instrumento previamente generado.

### Consulta
Permite visualizar instrumentos asociados a una venta.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de venta
- tipo de instrumento (boleto, contrato, acuerdo, etc.)
- datos relevantes para el instrumento
- fecha de emisión
- estado del instrumento
- observaciones

### Parámetros de consulta
- identificador de venta
- tipo de instrumento
- estado
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de instrumento
- venta asociada
- tipo de instrumento
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de instrumentos
- tipo de instrumento
- estado
- relación con la venta

## Flujo de alto nivel

### Generación
1. validar contexto técnico e idempotencia
2. cargar venta existente
3. validar elegibilidad de emisión de instrumento
4. construir documento lógico
5. registrar instrumento de compraventa
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar instrumento existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Anulación
1. validar contexto técnico
2. cargar instrumento
3. validar anulabilidad
4. registrar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar instrumentos
3. devolver vista de lectura

## Validaciones clave
- venta existente
- tipo de instrumento válido
- coherencia entre estado de venta e instrumento
- no duplicidad indebida de instrumento activo cuando no corresponda
- anulabilidad según política funcional
- control de versionado
- idempotencia en generación

## Efectos transaccionales
- alta o actualización de documento_logico
- alta o actualización de instrumento_compraventa
- vinculación con venta
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-COM]]

## Dependencias

### Hacia arriba
- venta existente
- condiciones comerciales definidas cuando corresponda
- contexto técnico válido

### Hacia abajo
- [[SRV-COM-006-gestion-de-escrituracion]]
- [[SRV-FIN-010-emision-financiera]]
- procesos documentales y legales

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
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- DER comercial
- DER documental

## Pendientes abiertos
- catálogo final de tipos de instrumentos
- política de modificación y anulación
- integración con plantillas documentales
- definición exacta de numeración documental
- relación formal con escrituración
