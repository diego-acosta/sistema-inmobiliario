# SRV-LOC-007 — Consulta y reporte locativo

## Objetivo
Proveer una capa de lectura consolidada del dominio locativo, permitiendo consultar contratos de alquiler, condiciones locativas, garantías, renovaciones, ocupación y documentación asociada, con trazabilidad funcional, sin generar efectos persistentes.

## Alcance
Este servicio cubre:
- consulta de contratos de alquiler
- consulta de condiciones locativas
- consulta de garantías
- consulta de renovaciones y rescisiones
- consulta de ocupación locativa
- consulta de documentación locativa
- búsqueda operativa de contratos
- reporte consolidado del dominio locativo

No cubre:
- alta o modificación de contratos
- gestión de condiciones locativas
- gestión de garantías
- gestión de ocupación
- analítica avanzada o BI

## Entidades principales
- contrato_alquiler
- condicion_locativa
- esquema_actualizacion_locativa
- garantia
- contrato_renovacion
- contrato_rescision
- ocupacion_locativa
- documento_locativo
- documento_logico
- persona
- inmueble
- unidad_funcional

## Modos del servicio

### Consulta operativa
Permite visualizar el estado actual del dominio locativo.

### Consulta histórica
Permite reconstruir información histórica contractual.

### Búsqueda
Permite localizar contratos por múltiples criterios.

### Reporte consolidado
Permite obtener una vista integrada del dominio.

## Entradas conceptuales

### Parámetros de consulta
- identificador de contrato
- persona interviniente
- objeto locativo
- estado contractual
- tipo de garantía
- estado de ocupación
- rango de fechas
- criterios de búsqueda y agrupación

## Resultado esperado

- datos de contratos
- condiciones locativas
- garantías asociadas
- historial de renovaciones y rescisiones
- ocupación locativa
- documentación
- personas intervinientes
- objetos locativos
- trazabilidad completa
- vistas agregadas cuando corresponda

## Flujo de alto nivel

### Consulta
1. validar parámetros de entrada
2. resolver contratos objetivo
3. cargar contratos
4. integrar condiciones locativas
5. integrar garantías
6. integrar renovaciones y rescisiones
7. integrar ocupación locativa
8. integrar documentación
9. integrar personas y objetos locativos
10. consolidar vista de salida
11. devolver resultado

## Validaciones clave
- consistencia de parámetros de consulta
- coherencia entre filtros
- existencia de entidades cuando corresponda
- control de acceso a información sensible

## Efectos transaccionales
- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- existencia de información locativa registrada
- integridad del dominio locativo
- permisos de consulta

### Hacia abajo
- dominio inmobiliario
- dominio financiero
- dominio comercial
- exportaciones y reportes externos

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
- [[SRV-LOC-002-gestion-de-condiciones-locativas]]
- [[SRV-LOC-003-gestion-de-garantias]]
- [[SRV-LOC-004-gestion-de-renovaciones-y-rescisiones]]
- [[SRV-LOC-005-gestion-de-ocupacion-locativa]]
- [[SRV-LOC-006-gestion-de-documentacion-locativa]]
- [[SRV-INM-007-gestion-de-estado-disponibilidad-y-ocupacion]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- DER locativo
- DER inmobiliario
- DER financiero

## Pendientes abiertos
- definición de vistas estándar locativas
- criterios de búsqueda avanzada
- límites entre consulta operativa y analítica
- definición de reportes estándar
- políticas de acceso a información sensible
