# EVT-INM - Eventos del dominio inmobiliario

## Objetivo
Separar los cambios observables que hoy existen en el sistema de los eventos conceptuales todavia no implementados.

## Estado actual
- no existe hoy una publicacion explicita de eventos de dominio inmobiliario en el backend vigente
- lo implementado son cambios observables sobre persistencia y respuestas API

## Cambios observables implementados
| Evento conceptual | Estado | Evidencia actual |
| --- | --- | --- |
| `desarrollo_creado` | IMPLEMENTADO | alta de `desarrollo` con tests `test_desarrollos_create.py` |
| `desarrollo_modificado` | IMPLEMENTADO | update de `desarrollo` |
| `desarrollo_dado_de_baja` | IMPLEMENTADO | baja logica de `desarrollo` |
| `inmueble_creado` | IMPLEMENTADO | alta de `inmueble` |
| `inmueble_modificado` | IMPLEMENTADO | update de `inmueble` |
| `inmueble_dado_de_baja` | IMPLEMENTADO | baja logica de `inmueble` |
| `inmueble_asociado_a_desarrollo` | IMPLEMENTADO | endpoint de asociacion |
| `inmueble_desasociado_de_desarrollo` | IMPLEMENTADO | endpoint de desasociacion |
| `unidad_funcional_creada` | IMPLEMENTADO | alta de `unidad_funcional` |
| `unidad_funcional_modificada` | IMPLEMENTADO | update de `unidad_funcional` |
| `unidad_funcional_dada_de_baja` | IMPLEMENTADO | baja logica de `unidad_funcional` |
| `edificacion_creada` | IMPLEMENTADO | alta de `edificacion` |
| `edificacion_modificada` | IMPLEMENTADO | update de `edificacion` |
| `edificacion_dada_de_baja` | IMPLEMENTADO | baja logica de `edificacion` |
| `servicio_creado` | IMPLEMENTADO | alta de `servicio` |
| `servicio_modificado` | IMPLEMENTADO | update de `servicio` |
| `servicio_dado_de_baja` | IMPLEMENTADO | baja logica de `servicio` |
| `servicio_asociado_a_inmueble` | IMPLEMENTADO | alta de `inmueble_servicio` |
| `servicio_asociado_a_unidad_funcional` | IMPLEMENTADO | alta de `unidad_funcional_servicio` |

## Eventos conceptuales futuros
| Evento | Estado | Nota |
| --- | --- | --- |
| `disponibilidad_cambiada` | PARCIAL | La tabla existe en SQL, pero no hay backend inmobiliario vigente |
| `ocupacion_registrada` | PARCIAL | La tabla existe en SQL, pero no hay backend inmobiliario vigente |
| `relacion_inmobiliaria_creada` | NO IMPLEMENTADO | No existe la entidad en el sistema actual |
| `infraestructura_registrada` | NO IMPLEMENTADO | No existe la entidad en el sistema actual |
| `inmueble_mejora_registrada` | NO IMPLEMENTADO | No existe la entidad en el sistema actual |

## Fuera de alcance
- eventos tecnicos de infraestructura transversal
- eventos de `instalacion`, `cliente`, `contrato`, `pago` o dominios externos

## Notas
- Cuando exista outbox o contrato de eventos explicito, este catalogo debe migrar de cambios observables a eventos publicados reales.
