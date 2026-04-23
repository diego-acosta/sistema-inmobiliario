# SRV-INM-007 - Gestion de estado, disponibilidad y ocupacion

## Estado del servicio
- clasificacion: `IMPLEMENTADO`
- fuente de verdad: SQL `disponibilidad` y `ocupacion`, routers, services y tests inmobiliarios vigentes
- backend actual: CRUD, cierre, reemplazo de vigencia y lecturas por activo ya materializados

## Modelo implementado
- campos de estado implementados en entidades activas:
  - `desarrollo.estado_desarrollo`
  - `inmueble.estado_administrativo`
  - `inmueble.estado_juridico`
  - `unidad_funcional.estado_administrativo`
  - `unidad_funcional.estado_operativo`
  - `servicio.estado_servicio`
- tablas persistidas sin API vigente:
  - ninguna para este servicio
- tablas y subrecursos con API vigente:
  - `disponibilidad`
  - `ocupacion`

## Funcionalidad disponible
- lectura y mutacion de estados embebidos en `desarrollo`, `inmueble`, `unidad_funcional` y `servicio`
- alta, modificacion, baja logica y cierre de `disponibilidad`
- reemplazo transaccional de `disponibilidad` vigente
- alta, modificacion, baja logica y cierre de `ocupacion`
- reemplazo transaccional de `ocupacion` vigente
- listados de `disponibilidad` y `ocupacion` por `inmueble` y por `unidad_funcional`

## Funcionalidad pendiente
- reportes o consultas consolidadas de vigencia cross-activo: `PARCIAL`
- lectura consolidada de trazabilidad funcional completa entre disponibilidad, ocupacion e integracion: `PARCIAL`

## Modelo conceptual futuro
- `disponibilidad` y `ocupacion` siguen siendo conceptos validos del dominio
- cualquier extension futura debe apoyarse en los endpoints, services y tests ya materializados

## Fuera de alcance
- ocupacion locativa, contratos y reservas comerciales

## Referencias
- [[EST-INM]]
- [[RN-INM]]
