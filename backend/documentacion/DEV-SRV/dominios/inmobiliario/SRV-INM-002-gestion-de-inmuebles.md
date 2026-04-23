# SRV-INM-002 - Gestion de inmuebles

## Estado del servicio
- clasificacion: `IMPLEMENTADO`
- naming canonico: `inmueble`
- fuente de verdad: SQL `inmueble`, `inmuebles_router.py`, `test_inmuebles_*`

## Modelo implementado
- entidad nucleo: `inmueble`
- relacion opcional implementada: `id_desarrollo`
- operaciones disponibles:
  - `POST /api/v1/inmuebles`
  - `GET /api/v1/inmuebles/{id_inmueble}`
  - `GET /api/v1/inmuebles`
  - `PUT /api/v1/inmuebles/{id_inmueble}`
  - `PUT /api/v1/inmuebles/{id_inmueble}/baja`
  - `PUT /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`
  - `PUT /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`

## Funcionalidad disponible
- alta, modificacion, baja logica, detalle y listado de `inmueble`
- asociacion y desasociacion de `desarrollo`
- versionado optimista en update y baja

## Funcionalidad pendiente
- reactivacion de `inmueble`
- filtros avanzados de consulta
- ficha integral del activo

## Modelo conceptual futuro
- el inmueble sigue siendo el activo raiz del dominio
- la documentacion futura debe seguir usando `inmueble` como nombre tecnico
- `desarrollo_inmobiliario` queda reservado a lenguaje funcional, no a naming de implementacion

## Fuera de alcance
- operaciones comerciales, contratos, pagos o cliente
- gestion directa de `instalacion`

## Referencias
- [[SRV-INM-001-gestion-de-desarrollos-inmobiliarios]]
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
- [[SRV-INM-011-consulta-y-reporte-inmobiliario]]
