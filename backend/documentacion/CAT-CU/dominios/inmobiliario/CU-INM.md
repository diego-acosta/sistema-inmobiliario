# CU-INM - Catalogo de casos de uso del dominio inmobiliario

## Objetivo
Mantener un catalogo sincronizado con la implementacion real del dominio y con el DEV-SRV vigente.

## Casos implementados
| ID | Caso de uso | Estado |
| --- | --- | --- |
| CU-INM-001 | Alta de desarrollo | IMPLEMENTADO |
| CU-INM-002 | Modificacion de desarrollo | IMPLEMENTADO |
| CU-INM-003 | Baja logica de desarrollo | IMPLEMENTADO |
| CU-INM-004 | Consulta de desarrollo | IMPLEMENTADO |
| CU-INM-005 | Listado de desarrollos | IMPLEMENTADO |
| CU-INM-006 | Alta de inmueble | IMPLEMENTADO |
| CU-INM-007 | Modificacion de inmueble | IMPLEMENTADO |
| CU-INM-008 | Baja logica de inmueble | IMPLEMENTADO |
| CU-INM-009 | Consulta de inmueble | IMPLEMENTADO |
| CU-INM-010 | Listado de inmuebles | IMPLEMENTADO |
| CU-INM-011 | Asociar inmueble a desarrollo | IMPLEMENTADO |
| CU-INM-012 | Desasociar inmueble de desarrollo | IMPLEMENTADO |
| CU-INM-013 | Alta de unidad funcional | IMPLEMENTADO |
| CU-INM-014 | Modificacion de unidad funcional | IMPLEMENTADO |
| CU-INM-015 | Baja logica de unidad funcional | IMPLEMENTADO |
| CU-INM-016 | Consulta de unidad funcional | IMPLEMENTADO |
| CU-INM-017 | Listado de unidades por inmueble | IMPLEMENTADO |
| CU-INM-018 | Listado global de unidades funcionales | IMPLEMENTADO |
| CU-INM-019 | Alta de edificacion | IMPLEMENTADO |
| CU-INM-020 | Modificacion de edificacion | IMPLEMENTADO |
| CU-INM-021 | Baja logica de edificacion | IMPLEMENTADO |
| CU-INM-022 | Consulta de edificacion | IMPLEMENTADO |
| CU-INM-023 | Listado global de edificaciones | IMPLEMENTADO |
| CU-INM-024 | Listado de edificaciones por padre | IMPLEMENTADO |
| CU-INM-025 | Alta de servicio | IMPLEMENTADO |
| CU-INM-026 | Modificacion de servicio | IMPLEMENTADO |
| CU-INM-027 | Baja logica de servicio | IMPLEMENTADO |
| CU-INM-028 | Consulta de servicio | IMPLEMENTADO |
| CU-INM-029 | Listado de servicios | IMPLEMENTADO |
| CU-INM-030 | Asociar servicio a inmueble | IMPLEMENTADO |
| CU-INM-031 | Listado de servicios por inmueble | IMPLEMENTADO |
| CU-INM-032 | Listado de inmuebles por servicio | IMPLEMENTADO |
| CU-INM-033 | Asociar servicio a unidad funcional | IMPLEMENTADO |
| CU-INM-034 | Listado de servicios por unidad funcional | IMPLEMENTADO |
| CU-INM-035 | Listado de unidades funcionales por servicio | IMPLEMENTADO |

## Casos parciales o futuros
| ID | Caso de uso | Estado | Nota |
| --- | --- | --- | --- |
| CU-INM-036 | Gestion de disponibilidad | PARCIAL | Solo SQL |
| CU-INM-037 | Gestion de ocupacion | PARCIAL | Solo SQL |
| CU-INM-038 | Gestion de identificacion operativa | PARCIAL | Campos embebidos, sin servicio propio |
| CU-INM-039 | Consulta y reporte inmobiliario | PARCIAL | Solo lecturas simples |
| CU-INM-040 | Gestion de identificacion catastral | NO IMPLEMENTADO | Sin soporte tecnico actual |
| CU-INM-041 | Gestion de atributos y documentacion inmobiliaria | NO IMPLEMENTADO | Sin soporte tecnico actual |
| CU-INM-042 | Gestion de mejoras | CONCEPTUAL | No existe `inmueble_mejora` |
| CU-INM-043 | Relacion inmobiliaria vigente | CONCEPTUAL | No existe `relacion_inmobiliaria` |
| CU-INM-044 | Consulta integral de inmueble | CONCEPTUAL | No implementada |
| CU-INM-045 | Gestion de propietario en inmobiliario | FUERA DE ALCANCE | Otro dominio |
| CU-INM-046 | Gestion de instalacion como entidad inmobiliaria | FUERA DE ALCANCE | Ownership operativo |
| CU-INM-047 | Registro de factura de servicio externo | SQL IMPLEMENTADO / API-BACKEND NO IMPLEMENTADOS | Actor: operador. Entrada: datos de factura del proveedor externo. Salida esperada futura: registro interno + evento conceptual pendiente `factura_servicio_registrada`. Existe tabla SQL estructural `factura_servicio`, pero no existe endpoint, schema, service, evento implementado ni consumer financiero; no genera obligacion financiera |
| CU-INM-048 | Disparo de integracion financiera por `factura_servicio` | NO IMPLEMENTADO | La obligacion derivada pertenece a `financiero` mediante `relacion_generadora` |
| CU-INM-049 | Emision de factura de servicio | FUERA DE ALCANCE | El sistema no factura servicios |

## Referencia
- Este catalogo replica el estado vigente de `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/CU-INM.md`.
