# RN-INM - Reglas del dominio inmobiliario

## Objetivo
Conservar las reglas reales del dominio, diferenciando lo ya enforced por SQL/backend de lo que sigue siendo conceptual.

## Reglas implementadas
| Regla | Estado | Fuente actual |
| --- | --- | --- |
| `inmueble` es el activo raiz del dominio | IMPLEMENTADO | SQL, backend y tests |
| `unidad_funcional` depende siempre de `inmueble` | IMPLEMENTADO | FK y CRUD actual |
| `desarrollo` es opcional para `inmueble` | IMPLEMENTADO | `id_desarrollo` nullable y endpoints de asociacion |
| `edificacion` debe pertenecer a exactamente un padre | IMPLEMENTADO | XOR en SQL y validacion backend |
| `codigo_unidad`, `estado_administrativo` y `estado_operativo` de `unidad_funcional` son obligatorios | IMPLEMENTADO | SQL y validacion backend alineados |
| no puede haber dos asociaciones activas iguales en `inmueble_servicio` | IMPLEMENTADO | backend y DB |
| no puede haber dos asociaciones activas iguales en `unidad_funcional_servicio` | PARCIAL | backend si, DB aun no |
| writes de update y baja usan versionado optimista | IMPLEMENTADO | routers, services y tests |

## Reglas parciales
| Regla | Estado | Nota |
| --- | --- | --- |
| `disponibilidad` y `ocupacion` tienen vigencia y padre exclusivo | IMPLEMENTADO | SQL, routers, services y tests cubren CRUD, cierre, reemplazo de vigencia y lecturas por activo |
| la identificacion operativa se resuelve por codigos embebidos | PARCIAL | existe, pero sin servicio dedicado |

## Modelo conceptual futuro
| Regla | Estado | Nota |
| --- | --- | --- |
| relacion temporal con propietario u otras partes | CONCEPTUAL | no existe `relacion_inmobiliaria` en implementacion real |
| atributos especializados del activo | NO IMPLEMENTADO | sin tablas ni backend |
| identificacion catastral | NO IMPLEMENTADO | sin tablas ni backend |
| mejoras como entidad separada | NO IMPLEMENTADO | sin soporte actual |

## Fuera de alcance
- cliente, propietario, contrato, pago, deuda, caja, instalacion
- cualquier semantica de otro dominio absorbida como nucleo inmobiliario

## Notas
- La documentacion futura debe tomar estas reglas implementadas como base y no como simple intencion conceptual.
