# SRV-INM-005 - Gestion de servicios e infraestructura

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: SQL `servicio`, `inmueble_servicio`, `unidad_funcional_servicio`, `servicios_router.py`, `inmuebles_router.py`, tests de servicios y asociaciones
- nota: el termino `infraestructura` se conserva solo para referencia historica del documento

## Modelo implementado
- entidad gestionada: `servicio`
- relaciones implementadas:
  - `inmueble_servicio`
  - `unidad_funcional_servicio`
- operaciones disponibles:
  - `POST /api/v1/servicios`
  - `GET /api/v1/servicios/{id_servicio}`
  - `GET /api/v1/servicios`
  - `PUT /api/v1/servicios/{id_servicio}`
  - `PUT /api/v1/servicios/{id_servicio}/baja`
  - `POST /api/v1/inmuebles/{id_inmueble}/servicios`
  - `GET /api/v1/inmuebles/{id_inmueble}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/inmuebles`
  - `POST /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/unidades-funcionales`

## Funcionalidad disponible
- CRUD basico de `servicio`
- asociacion de servicios a inmuebles y unidades funcionales
- control de duplicados activos en aplicacion y, para `inmueble_servicio`, tambien en DB

## Funcionalidad pendiente
- modelar `infraestructura` como entidad propia: `NO IMPLEMENTADO`
- catalogos especializados de cobertura o capacidad del servicio: `CONCEPTUAL`

## Modelo conceptual futuro
- si el negocio necesita distinguir infraestructura fisica de servicio, debe aparecer como modelo nuevo y no como alias de `servicio`

## Fuera de alcance
- `infraestructura` como entidad tecnica transversal
- ownership sobre `instalacion`

## Referencias
- [[SRV-INM-002-gestion-de-inmuebles]]
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
