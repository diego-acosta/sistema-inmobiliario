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
- lectura de vigencia historica por activo para `disponibilidad` y `ocupacion`
- lectura de trazabilidad de integracion comercial por activo basada en `venta`, `venta_objeto_inmobiliario` y `outbox_event`

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
