# SRV-LOC-006 — Gestión de documentación locativa

## Objetivo
Gestionar documentación locativa asociada a contratos de alquiler, permitiendo su registro, modificación, invalidación y consulta, preservando consistencia y trazabilidad documental.

## Alcance
Este servicio cubre:
- registro de documentos locativos
- modificación de documentos
- invalidación de documentos
- consulta de documentación asociada a contratos
- vinculación con contrato, personas y garantías

No cubre:
- generación de contratos de alquiler
- definición de condiciones locativas
- gestión de garantías en sí mismas
- ocupación locativa
- emisión formal de documentos

## Entidades principales
- documento_locativo
- documento_logico
- contrato_alquiler
- persona
- garantia

## Modos del servicio

### Registro
Permite registrar un documento locativo.

### Modificación
Permite actualizar datos de un documento.

### Invalidación
Permite dejar sin efecto un documento.

### Consulta
Permite visualizar documentación locativa.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato
- tipo de documento (contrato firmado, anexo, acta, certificado, etc.)
- datos del documento
- personas asociadas cuando corresponda
- garantías asociadas cuando corresponda
- estado del documento
- fecha del documento
- observaciones

### Parámetros de consulta
- identificador de contrato
- tipo de documento
- estado
- persona asociada
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de documento
- contrato asociado
- tipo de documento
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de documentos
- tipo de documento
- estado
- personas asociadas
- garantías asociadas
- fechas

## Flujo de alto nivel

### Registro
1. validar contexto técnico e idempotencia
2. cargar contrato existente
3. validar datos del documento
4. registrar documento locativo
5. vincular entidades relacionadas
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar documento existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Invalidación
1. validar contexto técnico
2. cargar documento
3. validar anulabilidad
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar documentos locativos
3. devolver vista de lectura

## Validaciones clave
- contrato existente
- coherencia del tipo de documento
- consistencia de datos
- validez de entidades asociadas
- no duplicidad indebida cuando corresponda
- anulabilidad según reglas funcionales
- control de versionado
- idempotencia en registro

## Efectos transaccionales
- alta o actualización de documento_locativo
- alta o actualización de documento_logico cuando corresponda
- vinculación con contrato_alquiler
- vinculación con persona y garantia cuando corresponda
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- contrato de alquiler existente
- personas y garantías cuando corresponda
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- procesos legales
- dominio comercial cuando corresponda
- reportes locativos

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
- [[SRV-LOC-003-gestion-de-garantias]]
- DER locativo
- DER documental

## Pendientes abiertos
- catálogo final de documentos locativos
- reglas de obligatoriedad documental
- política de versiones documentales
- integración con gestión documental global
- criterios de validez documental
