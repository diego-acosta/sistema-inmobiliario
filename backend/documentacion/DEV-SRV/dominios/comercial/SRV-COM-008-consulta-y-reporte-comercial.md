# SRV-COM-008 - Consulta y reporte comercial

## Objetivo

Proveer la capa de lectura operativa del dominio `comercial`, permitiendo consultar reservas, ventas y trazabilidad comercial asociada sin generar efectos persistentes.

## Alcance

Este servicio cubre hoy:

- detalle de `reserva_venta`
- listado de `reserva_venta`
- detalle enriquecido de `venta`
- listado por `venta` de:
  - `instrumento_compraventa`
  - `cesion`
  - `escrituracion`
- lectura del estado de integracion `comercial -> inmobiliario` por `venta`

No cubre en el `v1` vigente:

- reportes consolidados de actividad comercial
- busqueda avanzada multi-criterio fuera de los filtros ya materializados
- lectura propia de documental comercial
- detalle individual de `instrumento_compraventa`, `cesion` o `escrituracion`
- listados globales de `venta`, `instrumento_compraventa`, `cesion` o `escrituracion`
- analitica o BI

## Entidades principales

- `reserva_venta`
- `venta`
- `venta_objeto_inmobiliario`
- `instrumento_compraventa`
- `cesion`
- `escrituracion`
- `outbox_event` como soporte de observabilidad de integracion

## Modos del servicio

### Consulta operativa

Permite visualizar el estado actual de reservas y ventas ya registradas.

### Trazabilidad comercial

Permite reconstruir procedencia de la venta, objetos alcanzados y registros comerciales asociados.

### Observabilidad de integracion

Permite leer, por `venta`, el estado de los eventos emitidos hacia `inmobiliario` y su efecto contractual esperado.

## Entradas conceptuales

### Parametros de consulta hoy materializados

- identificador de reserva
- filtros basicos de `reserva_venta`:
  - `codigo_reserva`
  - `estado_reserva`
  - `fecha_desde`
  - `fecha_hasta`
  - `vigente`
  - `limit`
  - `offset`
- identificador de venta
- filtros de `instrumento_compraventa` por venta:
  - `tipo_instrumento`
  - `estado_instrumento`
  - `fecha_desde`
  - `fecha_hasta`
- filtros de `cesion` por venta:
  - `tipo_cesion`
  - `fecha_desde`
  - `fecha_hasta`
- filtros de `escrituracion` por venta:
  - `fecha_desde`
  - `fecha_hasta`
  - `numero_escritura`

## Resultado esperado

- datos de reserva
- datos de venta
- objetos comerciales asociados
- origen de la venta desde `reserva_venta` cuando exista
- instrumentos, cesiones y escrituraciones asociados a una `venta`
- estado de integracion `comercial -> inmobiliario`
- resumen de lectura derivado de hechos persistidos

## Flujo de alto nivel

### Consulta

1. validar parametros de entrada
2. resolver la entidad o conjunto objetivo
3. cargar datos persistidos del dominio comercial
4. integrar objetos y relaciones asociadas
5. enriquecer con lecturas actuales de `inmobiliario` cuando corresponda
6. enriquecer con observabilidad de outbox cuando corresponda
7. devolver la proyeccion de lectura

## Validaciones clave

- consistencia de parametros de consulta
- existencia de la entidad objetivo cuando corresponda
- coherencia entre filtros aplicados
- caracter read-only de toda la operacion

## Efectos transaccionales

- no genera efectos persistentes
- no modifica estado del sistema
- no registra outbox
- no requiere idempotencia write

## Errores

- [[ERR-COM]]

## Dependencias

### Hacia arriba

- existencia de informacion comercial registrada
- integridad del dominio comercial

### Hacia abajo

- `inmobiliario` como fuente read-only de `disponibilidad` y `ocupacion`
- `outbox_event` como fuente read-only de observabilidad de integracion

## Transversales

- [[CORE-EF-001-infraestructura-transversal]]

## Referencias

- [[00-INDICE-COMERCIAL]]
- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]
- [[SRV-COM-001-gestion-de-reserva-de-venta]]
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- [[SRV-COM-004-gestion-de-instrumentos-de-compraventa]]
- [[SRV-COM-005-gestion-de-cesiones]]
- [[SRV-COM-006-gestion-de-escrituracion]]
- `DEV-API-COMERCIAL.md`
- DER comercial

## Pendientes abiertos

- definicion de listados globales de `venta`
- definicion de detalles individuales de recursos hijos
- criterios de busqueda avanzada
- limite futuro entre consulta operativa y analitica
- eventual incorporacion de documental comercial en lectura
