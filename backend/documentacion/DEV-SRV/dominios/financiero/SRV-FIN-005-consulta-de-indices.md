# SRV-FIN-005 — Consulta de índices

## Objetivo
Devolver valores actuales e históricos de índices financieros utilizados por el sistema, de forma consistente, explotable y apta para soporte de cálculos, validaciones y análisis.

## Alcance
Este servicio cubre:
- consulta actual de índices financieros
- consulta histórica de índices
- búsqueda por tipo, período o vigencia
- navegación operativa sobre valores publicados

No cubre:
- alta de índices
- modificación de índices
- recalculo de deuda
- generación de obligaciones
- actualización de valores
- emisión de eventos técnicos

## Entidad principal
- indice_financiero

## Subconsultas internas
- obtener_indice_actual
- obtener_historial_indice
- filtrar_indices_por_tipo
- filtrar_indices_por_periodo
- ordenar_series_historicas

## Entrada conceptual
### Parámetros principales
- identificador de índice cuando aplique
- tipo o nombre de índice
- período o rango de fechas
- indicador de consulta actual o histórica

### Parámetros opcionales
- paginación
- orden cronológico
- filtros de vigencia
- corte a fecha cuando corresponda

### Contexto de seguridad
- identidad del usuario consultante
- permisos de lectura financiera

## Resultado esperado
- listado o detalle de índices encontrados
- valor actual cuando corresponda
- serie histórica cuando corresponda
- metadatos visibles de vigencia y período
- resultado vacío o no encontrado cuando corresponda

## Flujo de alto nivel
1. validar entrada y permisos de lectura
2. resolver criterio de búsqueda
3. cargar índice o serie histórica correspondiente
4. ordenar y filtrar resultados cuando corresponda
5. devolver vista de lectura consolidada

## Validaciones clave
- criterio de búsqueda válido
- coherencia entre período y rango solicitado
- permisos suficientes de lectura financiera

## Restricciones
- es una query pura
- no modifica estado
- no requiere lock
- no requiere versionado
- no requiere op_id
- no escribe outbox

## Dependencias
### Hacia arriba
- existencia de índices cargados
- permisos de lectura financiera

### Hacia abajo
- generación de obligaciones
- ajustes de alquiler
- validaciones financieras
- analítica financiera

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-004-gestion-de-indices-financieros]]
- [[RN-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- política exacta de vigencia visible para series superpuestas
- criterio final para exponer valor actual versus último valor publicado
- estrategia de consulta por fecha de aplicación versus fecha de carga
