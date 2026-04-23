# SRV-INM-001 - Gestion de desarrollos inmobiliarios

## Estado del servicio
- clasificacion: `IMPLEMENTADO`
- naming canonico: `desarrollo`
- fuente de verdad: SQL `desarrollo`, `desarrollos_router.py`, `test_desarrollos_*`

## Modelo implementado
- entidad nucleo: `desarrollo`
- relacion implementada: `inmueble.id_desarrollo`
- operaciones disponibles:
  - `POST /api/v1/desarrollos`
  - `GET /api/v1/desarrollos/{id_desarrollo}`
  - `GET /api/v1/desarrollos`
  - `PUT /api/v1/desarrollos/{id_desarrollo}`
  - `PUT /api/v1/desarrollos/{id_desarrollo}/baja`

## Funcionalidad disponible
- alta, modificacion, baja logica, detalle y listado de `desarrollo`
- versionado optimista en update y baja
- soporte para asociacion posterior desde `inmueble`

## Funcionalidad pendiente
- reactivacion de `desarrollo`
- filtros avanzados de consulta
- vistas agregadas por ocupacion, disponibilidad o comercializacion

## Modelo conceptual futuro
- `desarrollo_inmobiliario` se conserva solo como etiqueta conceptual de negocio
- cualquier expansion debe seguir usando `desarrollo` como nombre tecnico en SQL, backend y API

## Fuera de alcance
- gestion individual de `inmueble` y `unidad_funcional`
- disponibilidad, ocupacion y atributos catastrales
- ownership sobre `instalacion`, que pertenece a operativo

## Referencias
- [[00-INDICE-INMOBILIARIO]]
- [[CU-INM]]
- [[RN-INM]]
- [[ERR-INM]]
