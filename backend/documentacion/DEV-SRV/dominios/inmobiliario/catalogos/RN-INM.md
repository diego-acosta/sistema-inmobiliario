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
| registro de `factura_servicio` | IMPLEMENTADO V1 | API/backend registra y consulta facturas externas de proveedor sin generar relacion generadora ni obligacion financiera; el periodo puede ser nulo como dato operativo/documental |
| duplicidad de `factura_servicio` | IMPLEMENTADO V1 | se rechaza duplicado activo por proveedor + numero de factura |
| asociacion de `factura_servicio` a objeto inmobiliario | IMPLEMENTADO V1 | toda factura debe asociarse por XOR a `id_inmueble` o `id_unidad_funcional`, con servicio activo asociado al objeto |
| asignacion de responsable de servicio trasladado | IMPLEMENTADO V1 | `asignacion_servicio_responsable` define persona, servicio, inmueble/UF, vigencia y porcentaje para resolver futuros obligados de `SERVICIO_TRASLADADO`; no materializa obligaciones financieras |

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
| integracion de `factura_servicio` con financiero | IMPLEMENTADO V1 | la obligacion derivada pertenece a `financiero`; cada factura usa `relacion_generadora.tipo_origen = FACTURA_SERVICIO` e `id_origen = id_factura_servicio`, con obligacion `SERVICIO_TRASLADADO`; existe endpoint explicito de materializacion financiera, no evento/consumer automatico; si falta periodo completo, financiero devuelve `PERIODO_FACTURA_REQUERIDO` sin crear filas financieras |
| importe de `factura_servicio` | CONCEPTUAL | el sistema no calcula importes de servicios; el importe proviene del proveedor externo y se registra como dato recibido |
| resolucion de obligado por `factura_servicio` | IMPLEMENTADO V1 | la fuente inmobiliaria `asignacion_servicio_responsable` esta implementada y la materializacion financiera crea `obligacion_obligado` con `RESPONSABLE_SERVICIO` |
| pago externo informado de `factura_servicio` | IMPLEMENTADO V1 | pertenece a `financiero`; registra `PAGO_EXTERNO_INFORMADO` contra `SERVICIO_TRASLADADO` materializado solo en escenario `DIRECTO_RESPONSABLE`, entendido en V1 como responsabilidad 100% de una persona que paga directamente al proveedor; no crea caja, tesoreria ni recibo interno. Si la obligacion no tiene exactamente un obligado activo al 100%, financiero devuelve `PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO` |
| recupero de `factura_servicio` compartida o porcentual | DISENO V1 DOCUMENTADO / NO IMPLEMENTADO | en escenario `EMPRESA_PAGA_Y_RECUPERA`, la empresa/inmobiliaria paga al proveedor y luego se genera una obligacion de recupero a los responsables por su parte. No debe interpretarse `porcentaje_responsabilidad` como pago directo proporcional al proveedor, ni registrarse `PAGO_EXTERNO_INFORMADO` por cada persona. Financiero recomienda `SERVICIO_RECUPERADO` como concepto V1 para servicios comunes recuperados |

## Fuera de alcance
- cliente, propietario, contrato, pago, deuda, caja, instalacion
- cualquier semantica de otro dominio absorbida como nucleo inmobiliario
- emision de facturas de servicio por el sistema
- calculo, saldo, pago, imputacion, mora, ajuste o reversion financiera
- emision automatica/event-driven de obligaciones por `factura_servicio`
- implementacion del recupero `EMPRESA_PAGA_Y_RECUPERA` desde una factura de
  servicio pagada por la empresa, incluyendo egreso proveedor, liquidacion de
  recupero, reglas de reparto y generacion de obligacion financiera

## Notas
- La documentacion futura debe tomar estas reglas implementadas como base y no como simple intencion conceptual.
