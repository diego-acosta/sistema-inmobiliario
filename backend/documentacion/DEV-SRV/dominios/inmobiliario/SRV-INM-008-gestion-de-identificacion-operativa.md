# SRV-INM-008 - Gestion de identificacion operativa

## Estado del servicio
- clasificacion: `PARCIAL`
- backend actual: no existe como servicio independiente

## Modelo implementado
- la identificacion operativa vive hoy como campos embebidos:
  - `codigo_desarrollo`
  - `codigo_inmueble`
  - `codigo_unidad`
  - `codigo_servicio`
- soporte transversal tecnico registrado en SQL:
  - `id_instalacion_origen`
  - `id_instalacion_ultima_modificacion`
  - `op_id_alta`
  - `op_id_ultima_modificacion`

## Funcionalidad disponible
- alta y actualizacion de codigos dentro de los CRUD reales del dominio
- trazabilidad tecnica de write mediante metadata transversal

## Funcionalidad pendiente
- catalogo formal de identificadores operativos: `NO IMPLEMENTADO`
- validaciones avanzadas de normalizacion de codigos: `CONCEPTUAL`

## Modelo conceptual futuro
- puede existir un servicio dedicado de identificacion operativa si se separan reglas hoy embebidas en cada entidad

## Fuera de alcance
- `instalacion` como entidad de negocio inmobiliaria: `FUERA DE ALCANCE`

## Referencias
- [[SRV-INM-001-gestion-de-desarrollos-inmobiliarios]]
- [[SRV-INM-002-gestion-de-inmuebles]]
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
