# SRV-DOC-006 — Consulta y reporte documental

## Objetivo
Proveer una capa de lectura consolidada del dominio documental, permitiendo consultar documentos lógicos, versiones, asociaciones, plantillas y emisiones, con trazabilidad completa, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de documentos lógicos
- consulta de versiones documentales
- consulta de asociaciones documentales
- consulta de plantillas
- consulta de emisiones y numeración
- trazabilidad documental completa
- búsqueda operativa de documentos
- reporte consolidado del dominio documental

No cubre:
- creación o modificación de documentos
- almacenamiento físico de archivos
- generación de contenido documental
- analítica avanzada o BI

## Entidades principales
- documento_logico
- documento_version
- documento_asociacion
- plantilla_documental
- emision_documental
- numeracion_documental

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual documental.

### Consulta histórica
Permite reconstruir la evolución documental.

### Búsqueda
Permite localizar documentos por múltiples criterios.

### Reporte consolidado
Permite obtener una vista integrada del dominio documental.

## Entradas conceptuales

### Parámetros de consulta
- tipo de documento
- identificador de documento lógico
- número de versión
- tipo de asociación
- entidad asociada
- numeración
- estado
- rango de fechas
- criterios de búsqueda

## Resultado esperado

- documentos lógicos
- versiones documentales
- asociaciones
- plantillas
- emisiones
- numeración
- trazabilidad completa
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros
2. resolver documentos objetivo
3. cargar documentos lógicos
4. integrar versiones
5. integrar asociaciones
6. integrar plantillas
7. integrar emisiones
8. consolidar vista
9. devolver resultado

## Validaciones clave
- consistencia de parámetros
- coherencia de filtros
- existencia de entidades cuando corresponda
- control de acceso a información

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-DOC]]

## Dependencias

### Hacia arriba
- existencia de información documental
- integridad del dominio documental
- permisos de consulta

### Hacia abajo
- dominio financiero
- dominio locativo
- dominio comercial
- reportes externos

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-DOCUMENTAL]]
- [[CU-DOC]]
- [[RN-DOC]]
- [[ERR-DOC]]
- [[EVT-DOC]]
- [[EST-DOC]]
- [[SRV-DOC-001-gestion-de-documentos-logicos]]
- [[SRV-DOC-002-gestion-de-versionado-documental]]
- [[SRV-DOC-003-gestion-de-asociaciones-documentales]]
- [[SRV-DOC-004-gestion-de-plantillas-documentales]]
- [[SRV-DOC-005-gestion-de-emision-y-numeracion-documental]]
- DER documental

## Pendientes abiertos
- definición de vistas estándar documentales
- criterios de búsqueda avanzada
- integración con almacenamiento físico
- políticas de acceso documental
- límites con analítica y BI
