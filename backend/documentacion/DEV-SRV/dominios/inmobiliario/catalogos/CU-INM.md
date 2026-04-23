# CU-INM - Casos de uso del dominio inmobiliario

## Objetivo
Catalogar los casos de uso del dominio con estado explicito respecto de SQL, backend y tests actuales.

## Modelo implementado
| ID | Caso de uso | Estado | Fuente actual |
| --- | --- | --- | --- |
| CU-INM-001 | Alta de desarrollo | IMPLEMENTADO | `POST /api/v1/desarrollos` |
| CU-INM-002 | Modificacion de desarrollo | IMPLEMENTADO | `PUT /api/v1/desarrollos/{id_desarrollo}` |
| CU-INM-003 | Baja logica de desarrollo | IMPLEMENTADO | `PUT /api/v1/desarrollos/{id_desarrollo}/baja` |
| CU-INM-004 | Consulta de desarrollo | IMPLEMENTADO | `GET /api/v1/desarrollos/{id_desarrollo}` |
| CU-INM-005 | Listado de desarrollos | IMPLEMENTADO | `GET /api/v1/desarrollos` |
| CU-INM-006 | Alta de inmueble | IMPLEMENTADO | `POST /api/v1/inmuebles` |
| CU-INM-007 | Modificacion de inmueble | IMPLEMENTADO | `PUT /api/v1/inmuebles/{id_inmueble}` |
| CU-INM-008 | Baja logica de inmueble | IMPLEMENTADO | `PUT /api/v1/inmuebles/{id_inmueble}/baja` |
| CU-INM-009 | Consulta de inmueble | IMPLEMENTADO | `GET /api/v1/inmuebles/{id_inmueble}` |
| CU-INM-010 | Listado de inmuebles | IMPLEMENTADO | `GET /api/v1/inmuebles` |
| CU-INM-011 | Asociar inmueble a desarrollo | IMPLEMENTADO | `PUT /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo` |
| CU-INM-012 | Desasociar inmueble de desarrollo | IMPLEMENTADO | `PUT /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo` |
| CU-INM-013 | Alta de unidad funcional | IMPLEMENTADO | `POST /api/v1/inmuebles/{id_inmueble}/unidades-funcionales` |
| CU-INM-014 | Modificacion de unidad funcional | IMPLEMENTADO | `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}` |
| CU-INM-015 | Baja logica de unidad funcional | IMPLEMENTADO | `PUT /api/v1/unidades-funcionales/{id_unidad_funcional}/baja` |
| CU-INM-016 | Consulta de unidad funcional | IMPLEMENTADO | `GET /api/v1/unidades-funcionales/{id_unidad_funcional}` |
| CU-INM-017 | Listado de unidades por inmueble | IMPLEMENTADO | `GET /api/v1/inmuebles/{id_inmueble}/unidades-funcionales` |
| CU-INM-018 | Listado global de unidades funcionales | IMPLEMENTADO | `GET /api/v1/unidades-funcionales` |
| CU-INM-019 | Alta de edificacion | IMPLEMENTADO | `POST /api/v1/edificaciones` |
| CU-INM-020 | Modificacion de edificacion | IMPLEMENTADO | `PUT /api/v1/edificaciones/{id_edificacion}` |
| CU-INM-021 | Baja logica de edificacion | IMPLEMENTADO | `PUT /api/v1/edificaciones/{id_edificacion}/baja` |
| CU-INM-022 | Consulta de edificacion | IMPLEMENTADO | `GET /api/v1/edificaciones/{id_edificacion}` |
| CU-INM-023 | Listado global de edificaciones | IMPLEMENTADO | `GET /api/v1/edificaciones` |
| CU-INM-024 | Listado de edificaciones por padre | IMPLEMENTADO | `GET /api/v1/inmuebles/{id_inmueble}/edificaciones`, `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones` |
| CU-INM-025 | Alta de servicio | IMPLEMENTADO | `POST /api/v1/servicios` |
| CU-INM-026 | Modificacion de servicio | IMPLEMENTADO | `PUT /api/v1/servicios/{id_servicio}` |
| CU-INM-027 | Baja logica de servicio | IMPLEMENTADO | `PUT /api/v1/servicios/{id_servicio}/baja` |
| CU-INM-028 | Consulta de servicio | IMPLEMENTADO | `GET /api/v1/servicios/{id_servicio}` |
| CU-INM-029 | Listado de servicios | IMPLEMENTADO | `GET /api/v1/servicios` |
| CU-INM-030 | Asociar servicio a inmueble | IMPLEMENTADO | `POST /api/v1/inmuebles/{id_inmueble}/servicios` |
| CU-INM-031 | Listado de servicios por inmueble | IMPLEMENTADO | `GET /api/v1/inmuebles/{id_inmueble}/servicios` |
| CU-INM-032 | Listado de inmuebles por servicio | IMPLEMENTADO | `GET /api/v1/servicios/{id_servicio}/inmuebles` |
| CU-INM-033 | Asociar servicio a unidad funcional | IMPLEMENTADO | `POST /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios` |
| CU-INM-034 | Listado de servicios por unidad funcional | IMPLEMENTADO | `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios` |
| CU-INM-035 | Listado de unidades funcionales por servicio | IMPLEMENTADO | `GET /api/v1/servicios/{id_servicio}/unidades-funcionales` |
| CU-INM-036 | Gestion de disponibilidad | IMPLEMENTADO | `POST /api/v1/disponibilidades`, `PUT /api/v1/disponibilidades/{id_disponibilidad}`, `PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar`, `PUT /api/v1/disponibilidades/{id_disponibilidad}/baja`, `POST /api/v1/disponibilidades/reemplazar-vigente`, `GET /api/v1/inmuebles/{id_inmueble}/disponibilidades`, `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades` |
| CU-INM-037 | Gestion de ocupacion | IMPLEMENTADO | `POST /api/v1/ocupaciones`, `PUT /api/v1/ocupaciones/{id_ocupacion}`, `PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar`, `PUT /api/v1/ocupaciones/{id_ocupacion}/baja`, `POST /api/v1/ocupaciones/reemplazar-vigente`, `GET /api/v1/inmuebles/{id_inmueble}/ocupaciones`, `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/ocupaciones` |

## Modelo parcial
| ID | Caso de uso | Estado | Nota |
| --- | --- | --- | --- |
| CU-INM-038 | Gestion de identificacion operativa | PARCIAL | Los codigos viven embebidos en las entidades, sin servicio dedicado |
| CU-INM-039 | Consulta y reporte inmobiliario | PARCIAL | Existen lecturas simples; no hay ficha integral ni reportes agregados |

## Modelo conceptual futuro
| ID | Caso de uso | Estado | Nota |
| --- | --- | --- | --- |
| CU-INM-040 | Gestion de identificacion catastral | NO IMPLEMENTADO | Sin soporte actual en SQL ni backend |
| CU-INM-041 | Gestion de atributos y documentacion inmobiliaria | NO IMPLEMENTADO | Sin soporte actual en SQL ni backend |
| CU-INM-042 | Gestion de mejoras | CONCEPTUAL | No existe `inmueble_mejora` en la implementacion real |
| CU-INM-043 | Relacion inmobiliaria vigente | CONCEPTUAL | No existe `relacion_inmobiliaria` hoy en SQL ni backend |
| CU-INM-044 | Consulta integral de inmueble | CONCEPTUAL | El backend no expone esa vista consolidada |

## Fuera de alcance
| ID | Caso de uso | Estado | Nota |
| --- | --- | --- | --- |
| CU-INM-045 | Gestion de propietario en inmobiliario | FUERA DE ALCANCE | Invasiona personas y/o comercial |
| CU-INM-046 | Gestion de instalacion como entidad inmobiliaria | FUERA DE ALCANCE | `instalacion` pertenece a operativo |

## Notas
- El naming canonico del catalogo sigue SQL y backend.
- Los conceptos futuros se conservan, pero no se presentan como funcionalidad disponible.
