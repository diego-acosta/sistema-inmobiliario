# SRV-DOC-004 — Gestión de plantillas documentales

## Objetivo
Gestionar plantillas documentales del sistema, permitiendo su creación, modificación, invalidación y consulta, preservando consistencia y trazabilidad de los formatos documentales.

## Alcance
Este servicio cubre:
- creación de plantillas documentales
- modificación de plantillas
- invalidación de plantillas
- consulta de plantillas
- definición de estructuras y formatos documentales

No cubre:
- generación de documentos finales
- versionado documental
- asociación directa con entidades del negocio
- almacenamiento físico de documentos
- lógica específica de cada dominio

## Entidades principales
- plantilla_documental

## Modos del servicio

### Creación
Permite registrar una nueva plantilla documental.

### Modificación
Permite actualizar una plantilla existente.

### Invalidación
Permite dejar sin efecto una plantilla.

### Consulta
Permite visualizar plantillas documentales.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo de documento
- nombre de plantilla
- estructura o contenido base
- formato
- estado
- observaciones

### Parámetros de consulta
- tipo de documento
- estado
- nombre
- formato

## Resultado esperado

### Para operaciones write
- identificador de plantilla
- tipo de documento
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de plantillas
- tipo de documento
- nombre
- formato
- estado

## Flujo de alto nivel

### Creación
1. validar contexto técnico e idempotencia
2. validar datos de la plantilla
3. registrar plantilla documental
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar plantilla existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Invalidación
1. validar contexto técnico
2. cargar plantilla
3. validar anulabilidad
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar plantillas
3. devolver vista de lectura

## Validaciones clave
- consistencia del tipo documental
- coherencia del formato
- no duplicidad indebida cuando corresponda
- control de versionado
- idempotencia en creación

## Efectos transaccionales
- alta o actualización de plantilla_documental
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión documental

### Hacia abajo
- [[SRV-DOC-005-gestion-de-emision-y-numeracion-documental]]
- procesos de generación documental
- reportes del sistema

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-DOCUMENTAL]]
- [[CU-DOC]]
- [[RN-DOC]]
- [[ERR-DOC]]
- [[EVT-DOC]]
- [[EST-DOC]]
- DER documental

## Pendientes abiertos
- catálogo final de tipos de plantillas
- definición de formatos soportados
- integración con motores de renderizado
- reglas de versionado de plantillas
- criterios de selección de plantilla por contexto
