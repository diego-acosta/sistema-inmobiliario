# SRV-INM-004 - Gestion de edificaciones, mejoras e instalaciones

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: SQL `edificacion`, `edificaciones_router.py`, `test_edificaciones_*`
- nota: el nombre historico del archivo se conserva por trazabilidad

## Modelo implementado
- entidad implementada: `edificacion`
- regla estructural implementada: XOR entre `id_inmueble` e `id_unidad_funcional`
- operaciones disponibles:
  - `POST /api/v1/edificaciones`
  - `GET /api/v1/edificaciones/{id_edificacion}`
  - `GET /api/v1/edificaciones`
  - `PUT /api/v1/edificaciones/{id_edificacion}`
  - `PUT /api/v1/edificaciones/{id_edificacion}/baja`
  - `GET /api/v1/inmuebles/{id_inmueble}/edificaciones`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones`

## Funcionalidad disponible
- alta, modificacion, baja logica, detalle y listados de `edificacion`
- asociacion a `inmueble` o `unidad_funcional`, nunca a ambos a la vez

## Funcionalidad pendiente
- `inmueble_mejora`: `NO IMPLEMENTADO`
- catalogacion separada de mejoras: `CONCEPTUAL`

## Modelo conceptual futuro
- el concepto de mejora puede evolucionar como especializacion propia si aparece en SQL, backend y tests
- la documentacion futura debe usar `edificacion` como nombre tecnico vigente

## Fuera de alcance
- `instalacion` como entidad de negocio del dominio inmobiliario: `FUERA DE ALCANCE`
- el ownership de `instalacion` pertenece al dominio operativo segun `DEV-ARCH-OPE-001`

## Referencias
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
- [[SRV-INM-011-consulta-y-reporte-inmobiliario]]
