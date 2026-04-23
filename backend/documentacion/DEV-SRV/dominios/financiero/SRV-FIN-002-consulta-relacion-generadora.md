# SRV-FIN-002 — Consulta de relación generadora

## Objetivo
Devolver una vista integral, consistente y explotable de una relación generadora, incluyendo identidad, estado, origen, obligaciones asociadas, resumen financiero e historial visible.

## Alcance
Este servicio cubre:
- consulta de cabecera de relación generadora
- consulta del estado funcional
- identificación del origen del negocio
- listado o resumen de obligaciones asociadas
- resumen agregado de saldo
- vista operativa del cronograma asociado
- historial funcional visible

No cubre:
- recalcular deuda
- regenerar obligaciones
- aplicar pagos
- cancelar, finalizar o activar la relación
- materializar eventos técnicos

## Entidades principales
- relacion_generadora
- obligacion_financiera

## Subconsultas internas
- obtener_cabecera_relacion_generadora
- obtener_origen_relacion_generadora
- obtener_resumen_financiero_relacion
- obtener_obligaciones_relacion
- obtener_cronograma_relacion
- obtener_historial_visible_relacion

## Entrada conceptual
### Identificación principal
- id_relacion_generadora

### Parámetros opcionales
- incluir_obligaciones
- incluir_composicion
- incluir_historial
- incluir_obligados
- incluir_resumen_saldos
- incluir_cronograma

### Parámetros de lectura
- filtros por estado de obligación
- paginación
- orden cronológico
- corte a fecha cuando corresponda

### Contexto de seguridad
- identidad del usuario consultante
- permisos de lectura financiera
- alcance de visibilidad por sucursal o instalación cuando aplique

## Resultado esperado
- cabecera de la relación generadora
- origen funcional asociado
- resumen financiero agregado
- obligaciones asociadas
- composición por obligación cuando se solicite
- historial visible cuando se solicite

## Flujo de alto nivel
1. validar entrada y permisos de lectura
2. cargar cabecera de la relación
3. resolver origen funcional
4. cargar obligaciones asociadas
5. calcular o exponer resumen visible de saldo
6. incluir composición, cronograma o historial cuando se solicite
7. devolver vista consolidada

## Validaciones clave
- id_relacion_generadora válido
- existencia de la relación
- permisos suficientes para lectura financiera
- coherencia entre parámetros de expansión solicitados

## Restricciones
- es una query pura
- no modifica estado
- no requiere lock
- no requiere versionado
- no requiere op_id
- no escribe outbox

## Dependencias
### Hacia arriba
- relación generadora existente
- origen funcional resoluble
- permisos de lectura financiera

### Hacia abajo
- cronograma y detalle de deuda
- composición de obligaciones
- historial financiero visible

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[SRV-FIN-001-gestion-relacion-generadora]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- [[RN-FIN]]
- [[EST-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- política final de resolución del origen por tipo
- nivel exacto de detalle del historial visible
- estrategia final de resumen de saldo a fecha
