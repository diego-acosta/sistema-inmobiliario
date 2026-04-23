# SRV-INM-006 - Gestion de agrupaciones y relaciones estructurales

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: `inmueble.id_desarrollo`, endpoints de asociacion y desasociacion de desarrollo

## Modelo implementado
- relacion estructural implementada: `desarrollo` -> `inmueble`
- operaciones disponibles:
  - `PUT /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`
  - `PUT /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`

## Funcionalidad disponible
- vinculacion estructural de `inmueble` con `desarrollo`
- cambio versionado de la relacion desde el backend inmobiliario actual

## Funcionalidad pendiente
- `relacion_inmobiliaria`: `NO IMPLEMENTADO`
- agrupaciones complejas entre inmuebles: `CONCEPTUAL`
- relaciones vigentes con terceros: `NO IMPLEMENTADO`

## Modelo conceptual futuro
- el concepto de relacion inmobiliaria puede existir a futuro, pero hoy no tiene soporte en SQL, backend ni tests
- cualquier expansion con `propietario` o equivalentes debe respetar el ownership de personas y comercial

## Fuera de alcance
- `propietario`, `cliente`, `contrato`, `rol_participacion`: `FUERA DE ALCANCE`

## Referencias
- [[SRV-INM-001-gestion-de-desarrollos-inmobiliarios]]
- [[SRV-INM-002-gestion-de-inmuebles]]
