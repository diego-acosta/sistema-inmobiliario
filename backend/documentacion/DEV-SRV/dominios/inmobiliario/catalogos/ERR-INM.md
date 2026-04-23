# ERR-INM - Errores del dominio inmobiliario

## Objetivo
Documentar el contrato de error que hoy existe en backend y separar los codigos conceptuales no implementados.

## Contrato publico implementado
| Codigo publico | Estado | Uso actual |
| --- | --- | --- |
| `NOT_FOUND` | IMPLEMENTADO | GET de detalle y writes cuando falta la entidad objetivo |
| `APPLICATION_ERROR` | IMPLEMENTADO | Validaciones de negocio y rechazos funcionales |
| `CONCURRENCY_ERROR` | IMPLEMENTADO | Falta o invalidez de `If-Match-Version` y conflictos de version |
| `INTERNAL_ERROR` | IMPLEMENTADO | Excepcion no traducida en router |

## Marcadores internos implementados en `details.errors`
| Codigo interno | Estado | Aplica a | Nota |
| --- | --- | --- | --- |
| `NOT_FOUND_DESARROLLO` | IMPLEMENTADO | `desarrollo`, `inmueble` | Rechazo por desarrollo inexistente |
| `NOT_FOUND_INMUEBLE` | IMPLEMENTADO | `inmueble`, `edificacion`, `inmueble_servicio` | Falta de inmueble referenciado |
| `NOT_FOUND_UNIDAD_FUNCIONAL` | IMPLEMENTADO | `unidad_funcional`, `edificacion`, `unidad_funcional_servicio` | Falta de unidad funcional referenciada |
| `NOT_FOUND_EDIFICACION` | IMPLEMENTADO | `edificacion` | Falta de edificacion en writes |
| `NOT_FOUND_SERVICIO` | IMPLEMENTADO | `servicio`, asociaciones | Falta de servicio referenciado |
| `DUPLICATE_INMUEBLE_SERVICIO` | IMPLEMENTADO | `inmueble_servicio` | Duplicado activo detectado por app y/o DB |
| `DUPLICATE_UNIDAD_FUNCIONAL_SERVICIO` | IMPLEMENTADO | `unidad_funcional_servicio` | Duplicado activo detectado por app |
| `EXACTLY_ONE_PARENT_REQUIRED` | IMPLEMENTADO | `edificacion` | Se exige `id_inmueble` XOR `id_unidad_funcional` |
| `INVALID_REQUIRED_FIELDS` | IMPLEMENTADO | `unidad_funcional` | Campos obligatorios alineados con SQL |
| `X-Instalacion-Id es requerido.` | IMPLEMENTADO | writes versionados o asociativos | Validacion tecnica de contexto |

## Conceptos de error preservados pero no emitidos hoy
| Codigo conceptual | Estado | Nota |
| --- | --- | --- |
| `inmueble_no_encontrado` | CONCEPTUAL | Semantica valida, pero el backend actual responde `NOT_FOUND` |
| `unidad_funcional_no_encontrada` | CONCEPTUAL | Idem |
| `conflicto_concurrencia` | CONCEPTUAL | El backend actual responde `CONCURRENCY_ERROR` |
| `relacion_inmobiliaria_no_encontrada` | NO IMPLEMENTADO | No existe `relacion_inmobiliaria` |
| `infraestructura_no_encontrada` | NO IMPLEMENTADO | No existe entidad `infraestructura` |

## Fuera de alcance
- errores de propietario, cliente o contrato en el dominio inmobiliario
- errores tecnicos profundos de infraestructura transversal

## Notas
- El contrato vigente debe leerse desde routers y tests antes que desde nomenclatura conceptual historica.
