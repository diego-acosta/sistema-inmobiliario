# Dominio inmobiliario

## Objetivo
Alinear la documentacion del dominio inmobiliario con la implementacion real de SQL, backend y tests, sin perder el modelo conceptual ya definido.

## Fuente de verdad actual
- SQL real: `desarrollo`, `inmueble`, `unidad_funcional`, `edificacion`, `disponibilidad`, `ocupacion`, `inmueble_servicio`, `unidad_funcional_servicio`, `inmueble_sucursal`
- Backend implementado: `desarrollos_router.py`, `inmuebles_router.py`, `edificaciones_router.py`, `servicios_router.py`
- Cobertura vigente: `backend/tests/test_desarrollos_*`, `test_inmuebles_*`, `test_unidades_funcionales_*`, `test_edificaciones_*`, `test_servicios_*`, `test_inmueble_servicios_*`, `test_unidad_funcional_servicios_*`, `test_disponibilidades_*`, `test_ocupaciones_*`, `test_activo_trazabilidad_integracion_get.py`, `test_inmobiliario_*consumer.py`

## Leyenda de estado
- `IMPLEMENTADO`: existe en SQL y en backend con tests vigentes
- `PARCIAL`: existe en una o dos capas, pero no como circuito completo
- `NO IMPLEMENTADO`: no existe hoy en SQL ni en backend
- `CONCEPTUAL`: modelo valido a futuro, sin implementacion actual
- `FUERA DE ALCANCE`: invade otro dominio o no tiene ownership inmobiliario vigente

## Modelo implementado
| Elemento | Estado | Clasificacion | Nota |
| --- | --- | --- | --- |
| `desarrollo` | IMPLEMENTADO | nucleo | Nombre canonico real del backend y SQL |
| `inmueble` | IMPLEMENTADO | nucleo | Activo raiz del dominio |
| `unidad_funcional` | IMPLEMENTADO | nucleo | Depende de `inmueble` |
| `edificacion` | IMPLEMENTADO | nucleo | Con XOR entre `id_inmueble` e `id_unidad_funcional` |
| `servicio` | IMPLEMENTADO | soporte transversal | Se gestiona en backend y se asocia al activo inmobiliario |
| `inmueble_servicio` | IMPLEMENTADO | soporte transversal | Ya tiene unicidad activa en DB y validacion en backend |
| `unidad_funcional_servicio` | IMPLEMENTADO | soporte transversal | Validado en backend |
| `disponibilidad` | IMPLEMENTADO | nucleo | Tiene CRUD, cierre, reemplazo de vigencia y lecturas por activo |
| `ocupacion` | IMPLEMENTADO | nucleo | Tiene CRUD, cierre, reemplazo de vigencia y lecturas por activo |
| `inmueble_sucursal` | PARCIAL | soporte transversal | Existe en SQL, sin servicio inmobiliario expuesto |

## Naming canonico
- Usar `desarrollo`, no `desarrollo_inmobiliario`
- Usar `disponibilidad`, no `disponibilidad_inmobiliaria`
- Usar `edificacion`, no `inmueble_edificacion`
- `infraestructura`, `relacion_inmobiliaria` e `inmueble_mejora` se preservan solo como conceptos futuros; no son nombres tecnicos vigentes

## Servicios DEV-SRV
- [[SRV-INM-001-gestion-de-desarrollos-inmobiliarios]]: `IMPLEMENTADO`
- [[SRV-INM-002-gestion-de-inmuebles]]: `IMPLEMENTADO`
- [[SRV-INM-003-gestion-de-unidades-funcionales]]: `IMPLEMENTADO`
- [[SRV-INM-004-gestion-de-edificaciones-mejoras-e-instalaciones]]: `PARCIAL`
- [[SRV-INM-005-gestion-de-servicios-e-infraestructura]]: `PARCIAL`
- [[SRV-INM-006-gestion-de-agrupaciones-y-relaciones-estructurales]]: `PARCIAL`
- [[SRV-INM-007-gestion-de-estado-disponibilidad-y-ocupacion]]: `IMPLEMENTADO`
- [[SRV-INM-008-gestion-de-identificacion-operativa]]: `PARCIAL`
- [[SRV-INM-009-gestion-de-identificacion-catastral]]: `NO IMPLEMENTADO`
- [[SRV-INM-010-gestion-de-atributos-y-documentacion-inmobiliaria]]: `NO IMPLEMENTADO`
- [[SRV-INM-011-consulta-y-reporte-inmobiliario]]: `PARCIAL`

## Catalogos del dominio
- [[CU-INM]]
- [[RN-INM]]
- [[ERR-INM]]
- [[EVT-INM]]
- [[EST-INM]]

## Notas de alineacion
- `instalacion` aparece hoy como metadata tecnica (`id_instalacion_origen`, `id_instalacion_ultima_modificacion`) y no como entidad de dominio inmobiliario.
- Los conceptos futuros se conservan, pero quedan marcados explicitamente para no inducir a error sobre funcionalidad disponible.
