# EST-INM - Estados y campos tipificados del dominio inmobiliario

## Objetivo
Registrar los estados y valores tipificados que hoy existen en el modelo real, separando lo observado de lo todavia conceptual.

## Campos implementados en backend y tests
| Campo | Entidad | Estado | Valores observados | Nota |
| --- | --- | --- | --- | --- |
| `estado_desarrollo` | `desarrollo` | IMPLEMENTADO | `ACTIVO`, `INACTIVO` | Persistido y expuesto por CRUD de desarrollo |
| `estado_administrativo` | `inmueble` | IMPLEMENTADO | `ACTIVO`, `INACTIVO` | Persistido y expuesto por CRUD de inmueble |
| `estado_juridico` | `inmueble` | IMPLEMENTADO | `REGULAR`, `OBSERVADO` | Persistido y expuesto por CRUD de inmueble |
| `estado_administrativo` | `unidad_funcional` | IMPLEMENTADO | `ACTIVA`, `INACTIVA` | Persistido y expuesto por CRUD de unidad funcional |
| `estado_operativo` | `unidad_funcional` | IMPLEMENTADO | `DISPONIBLE` | Campo obligatorio; catalogo completo pendiente |
| `tipo_edificacion` | `edificacion` | IMPLEMENTADO | `CASA`, `LOCAL`, `DEPTO`, `BAULERA` | Observado en backend y tests |
| `estado_servicio` | `servicio` | IMPLEMENTADO | `ACTIVO`, `INACTIVO` | Persistido y expuesto por CRUD de servicio |
| `estado` | `inmueble_servicio` | IMPLEMENTADO | `ACTIVO`, `INACTIVO` | Estado de asociacion |
| `estado` | `unidad_funcional_servicio` | IMPLEMENTADO | `ACTIVO`, `INACTIVO` | Estado de asociacion |

## Campos presentes en SQL con API y tests vigentes
| Campo | Entidad | Estado | Nota |
| --- | --- | --- | --- |
| `estado_disponibilidad` | `disponibilidad` | IMPLEMENTADO | Existe en SQL y backend inmobiliario con CRUD, cierre, reemplazo de vigencia y lecturas por activo |
| `tipo_ocupacion` | `ocupacion` | IMPLEMENTADO | Existe en SQL y backend inmobiliario con CRUD, cierre, reemplazo de vigencia y lecturas por activo |

## Modelo conceptual futuro
| Concepto | Estado | Nota |
| --- | --- | --- |
| Estado propio de `relacion_inmobiliaria` | NO IMPLEMENTADO | No existe la entidad en el sistema actual |
| Estado propio de `infraestructura` | NO IMPLEMENTADO | No existe la entidad en el sistema actual |
| Catalogo formal de `estado_operativo` | CONCEPTUAL | El campo existe, pero no hay catalogo validado aparte |

## Fuera de alcance
- estados de `instalacion`, `cliente`, `contrato` o cualquier entidad de otro dominio

## Notas
- Este documento evita promover como oficiales valores que hoy no estan soportados por SQL, backend y tests.
