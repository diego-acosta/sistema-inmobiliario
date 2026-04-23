# SRV-PER-007 — Consulta y reporte de personas

## Objetivo
Proveer una capa de lectura consolidada del dominio Personas y Partes Intervinientes, permitiendo consultar identidad base, documentación, domicilios, contactos, clasificaciones, relaciones, representación y roles de participación con trazabilidad funcional, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de persona base
- consulta de identificaciones documentales
- consulta de domicilios y contactos
- consulta de clasificaciones y condiciones
- consulta de relaciones entre personas
- consulta de representación
- consulta de roles de participación y condición de cliente
- búsqueda operativa de personas
- reporte consolidado de personas

No cubre:
- alta o modificación de persona
- registración de documentos
- modificación de domicilios o contactos
- asignación de clasificaciones
- alta o modificación de relaciones
- asignación de roles de participación
- analítica avanzada o BI

## Entidades principales
- persona
- persona_documento
- persona_domicilio
- persona_contacto
- persona_clasificacion
- persona_relacion
- representacion_poder
- rol_participacion
- relacion_persona_rol
- cliente_comprador

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual de una persona y sus datos asociados.

### Consulta histórica
Permite reconstruir información histórica o vigencias cuando corresponda.

### Búsqueda
Permite localizar personas por criterios básicos o combinados.

### Reporte consolidado
Permite obtener una vista integrada de la persona y su participación funcional en el sistema.

## Entradas conceptuales

### Parámetros de consulta
- identificador de persona
- nombre o razón social
- tipo de persona
- tipo y número de documento
- estado
- clasificación
- condición funcional
- tipo de relación
- tipo de rol de participación
- rango de vigencia cuando corresponda
- criterios de búsqueda y agrupación

## Resultado esperado

- datos base de persona
- identificaciones documentales asociadas
- domicilios y contactos asociados
- clasificaciones y condiciones visibles
- relaciones y representaciones asociadas
- roles de participación y condición de cliente
- trazabilidad funcional consolidada
- listados o vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros de entrada
2. resolver persona o conjunto de personas objetivo
3. cargar datos base
4. integrar documentación, domicilios y contactos
5. integrar clasificaciones, relaciones y representación
6. integrar roles de participación y condición de cliente
7. consolidar vista de salida
8. devolver resultado

## Validaciones clave
- consistencia de parámetros de consulta
- existencia de persona cuando corresponda
- coherencia entre filtros aplicados
- control de acceso a información sensible según política funcional

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-PER]]

## Dependencias

### Hacia arriba
- existencia de información de personas registrada
- integridad del dominio personas
- permisos de consulta

### Hacia abajo
- reportes operativos
- dominios comercial, locativo y financiero
- exportaciones o vistas de lectura externas

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
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- DER de personas

## Pendientes abiertos
- definición final de vistas estándar de consulta de personas
- criterios de búsqueda avanzados
- política de exposición de datos sensibles
- nivel exacto de historización visible en reportes
- límites entre consulta operativa y analítica avanzada
