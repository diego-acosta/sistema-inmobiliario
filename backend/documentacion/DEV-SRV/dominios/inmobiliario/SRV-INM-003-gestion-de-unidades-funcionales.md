# SRV-INM-003 - Gestion de unidades funcionales

## Estado del servicio
- clasificacion: `IMPLEMENTADO`
- naming canonico: `unidad_funcional`
- fuente de verdad: SQL `unidad_funcional`, `inmuebles_router.py`, `test_unidades_funcionales_*`

## Modelo implementado
- entidad nucleo: `unidad_funcional`
- dependencia estructural: toda `unidad_funcional` pertenece a un `inmueble`
- operaciones disponibles:
  - `POST /api/v1/inmuebles/{id_inmueble}/unidades-funcionales`
  - `GET /api/v1/inmuebles/{id_inmueble}/unidades-funcionales`
  - `GET /api/v1/unidades-funcionales`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}`
  - `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}`
  - `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}/baja`

## Funcionalidad disponible
- alta, modificacion, baja logica, detalle y listados de `unidad_funcional`
- alineacion explicita con SQL para `codigo_unidad`, `estado_administrativo` y `estado_operativo`
- versionado optimista en update y baja

## Funcionalidad pendiente
- reactivacion de `unidad_funcional`
- filtros avanzados por estado
- consultas consolidadas con disponibilidad u ocupacion

## Modelo conceptual futuro
- la unidad funcional mantiene autonomia descriptiva, pero no reemplaza al inmueble raiz
- cualquier expansion debe preservar la dependencia obligatoria con `inmueble`

## Fuera de alcance
- relacion inmobiliaria con propietario u otros actores
- logica comercial o financiera

## Referencias
- [[SRV-INM-002-gestion-de-inmuebles]]
- [[SRV-INM-005-gestion-de-servicios-e-infraestructura]]
- [[SRV-INM-011-consulta-y-reporte-inmobiliario]]
