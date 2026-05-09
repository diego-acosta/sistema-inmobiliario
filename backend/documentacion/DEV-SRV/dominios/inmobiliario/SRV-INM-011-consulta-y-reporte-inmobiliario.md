# SRV-INM-011 - Consulta y reporte inmobiliario

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: endpoints GET de `desarrollo`, `inmueble`, `unidad_funcional`, `edificacion`, `servicio`, subrecursos de `disponibilidad` y `ocupacion`, y lecturas de trazabilidad de integracion por activo

## Modelo implementado
- consultas disponibles:
  - `GET /api/v1/desarrollos`
  - `GET /api/v1/desarrollos/{id_desarrollo}`
  - `GET /api/v1/inmuebles`
  - `GET /api/v1/inmuebles/{id_inmueble}`
  - `GET /api/v1/inmuebles/{id_inmueble}/unidades-funcionales`
  - `GET /api/v1/unidades-funcionales`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}`
  - `GET /api/v1/inmuebles/{id_inmueble}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/inmuebles`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/unidades-funcionales`
  - `GET /api/v1/edificaciones`
  - `GET /api/v1/edificaciones/{id_edificacion}`
  - `GET /api/v1/inmuebles/{id_inmueble}/edificaciones`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones`
  - `GET /api/v1/servicios`
  - `GET /api/v1/servicios/{id_servicio}`
  - `GET /api/v1/inmuebles/{id_inmueble}/disponibilidades`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades`
  - `GET /api/v1/inmuebles/{id_inmueble}/ocupaciones`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/ocupaciones`
  - `GET /api/v1/inmuebles/{id_inmueble}/trazabilidad-integracion`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/trazabilidad-integracion`

## Funcionalidad disponible
- consultas operativas simples y relacionales del modelo ya implementado
- filtros basicos por identificador o por padre inmediato
- listados UI read-only de `GET /api/v1/inmuebles` y `GET /api/v1/unidades-funcionales` con paginacion obligatoria (`limit`, `offset`), `total`, `items` y `data` compatible
- filtros UI vigentes para inmuebles: `q`, `estado_administrativo`, `estado_juridico`, `id_desarrollo`, `disponibilidad_actual`, `ocupacion_actual`, `id_servicio`, `limit`, `offset`
- filtros UI vigentes para unidades funcionales: `q`, `id_inmueble`, `estado_administrativo`, `estado_operativo`, `disponibilidad_actual`, `ocupacion_actual`, `id_servicio`, `limit`, `offset`
- lectura consolidada read-only de disponibilidad y ocupacion abierta del mismo activo consultado
- lectura de vigencia historica por activo para `disponibilidad` y `ocupacion`
- lectura de trazabilidad de integracion comercial por activo basada en `venta`, `venta_objeto_inmobiliario` y `outbox_event`

## Reglas UI vigentes
- `GET /api/v1/inmuebles` no modifica disponibilidad, ocupacion ni vigencias.
- `GET /api/v1/unidades-funcionales` no modifica disponibilidad, ocupacion ni vigencias.
- la disponibilidad actual de inmueble se obtiene solo de `disponibilidad.id_inmueble` con `id_unidad_funcional IS NULL`, `fecha_hasta IS NULL` y `deleted_at IS NULL`.
- la disponibilidad actual de unidad funcional se obtiene solo de `disponibilidad.id_unidad_funcional` con `id_inmueble IS NULL`, `fecha_hasta IS NULL` y `deleted_at IS NULL`.
- la ocupacion actual de inmueble se obtiene solo de `ocupacion.id_inmueble` con `id_unidad_funcional IS NULL`, `fecha_hasta IS NULL` y `deleted_at IS NULL`.
- la ocupacion actual de unidad funcional se obtiene solo de `ocupacion.id_unidad_funcional` con `id_inmueble IS NULL`, `fecha_hasta IS NULL` y `deleted_at IS NULL`.
- si no hay registro abierto, `disponibilidad_actual` u `ocupacion_actual` se devuelve `null`.
- si hay exactamente un registro abierto, se devuelve ese registro como actual.
- si hay mas de un registro abierto, el actual se devuelve `null` y el indicador `*_ambigua` se devuelve `true`.
- los filtros por `disponibilidad_actual` y `ocupacion_actual` aplican solo cuando existe un unico registro abierto no ambiguo.
- no se consultan ni modifican dominios comercial, locativo o financiero para resolver estos listados.

## Funcionalidad pendiente
- ficha integral de `inmueble`: `NO IMPLEMENTADO`
- reportes consolidados cross-activo con `disponibilidad` u `ocupacion`: `NO IMPLEMENTADO`
- analitica agregada del dominio: `CONCEPTUAL`

## Modelo conceptual futuro
- `desarrollo_inmobiliario`, `infraestructura`, `inmueble_mejora` y `relacion_inmobiliaria` no deben aparecer como entidades implementadas en reportes actuales
- si se suman reportes avanzados, el naming debe seguir el modelo tecnico vigente

## Fuera de alcance
- reportes analiticos read-only propietarios de otro dominio
- consultas comerciales, financieras o locativas

## Referencias
- [[SRV-INM-001-gestion-de-desarrollos-inmobiliarios]]
- [[SRV-INM-002-gestion-de-inmuebles]]
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
- [[SRV-INM-004-gestion-de-edificaciones-mejoras-e-instalaciones]]
- [[SRV-INM-005-gestion-de-servicios-e-infraestructura]]
