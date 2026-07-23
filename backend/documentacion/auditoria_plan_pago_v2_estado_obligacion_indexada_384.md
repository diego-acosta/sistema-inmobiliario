# Auditoría #384 — Estado de obligación en cuotas indexadas de Plan Pago V2

## Corrección histórica por #389

La conclusión original de esta auditoría era una descripción consistente del
código entonces existente: permitía `PROYECTADA + CON_INDICE_APLICADO`. **Esa
conclusión fue reemplazada por la regla funcional consolidada de #389** y no
debe usarse para interpretar el ciclo de vida PPV2.

`obligacion_financiera` es núcleo de Financiero. El plan y sus bloques son
núcleo de Comercial; su referencia es trazabilidad y no traslada ownership.

## Regla vigente implementada

El criterio central es si el importe definitivo de la obligación quedó
materializado dentro del circuito financiero:

| Escenario PPV2 | Estado inicial o resultante |
| --- | --- |
| Cuota fija/no indexada, anticipo, refuerzo o saldo con importe determinado | `EMITIDA` |
| Cuota indexada con valor y ajuste materializados al nacimiento | `EMITIDA` |
| Cuota indexada sin índice aplicable | `PROYECTADA` + `PROYECTADA_SIN_INDICE` |
| Corrida posterior exitosa sobre `PROYECTADA` | `PROYECTADA -> EMITIDA` |
| Corrida sobre `EMITIDA`, `EXIGIBLE` o `VENCIDA` | Conserva el estado contractual |
| Pago parcial / total | `PARCIALMENTE_CANCELADA` / `CANCELADA` |
| `ANULADA` o `REEMPLAZADA` | Nunca se reactiva |

La combinación estable tras indexar correctamente es
`EMITIDA + CON_INDICE_APLICADO` (o un estado posterior de pago/mora). Una
combinación `PROYECTADA + CON_INDICE_APLICADO` sólo identifica un dato heredado
inconsistente o un instante no comprometido de una transacción.

## Evidencia de implementación

La regla de generación está centralizada en
`financiero.determine_initial_obligation_state`: las tres variantes PPV2 aportan
el hecho `definitive_amount_materialized` antes de crear obligaciones. La
corrida toma locks, actualiza importe, saldo,
composición y trazabilidad, y cambia a `EMITIDA` sólo cuando el estado
persistido es `PROYECTADA`; todo se confirma junto con detalle, corrida y
outbox. Ante un error se hace rollback y la obligación no se emite.

Mora conserva `EMITIDA -> VENCIDA` para saldo vencido y no selecciona
`PROYECTADA`; por eso una cuota histórica indexada disponible puede emitirse y
luego procesarse por la rutina normal de mora, mientras que una sin índice
permanece proyectada. Los pagos y los estados terminales están fuera de la
elegibilidad de la corrida y conservan su política vigente.

## Demo `DEMO-VTA-CUOTAS-PPV2-INDEXADA`

| Bloque | Estado obligación | Estado indexación | Origen |
| --- | --- | --- | --- |
| Índice al nacimiento | `EMITIDA` | `CON_INDICE_APLICADO` | `AL_NACIMIENTO` |
| Proyectada sin índice | `PROYECTADA` | `PROYECTADA_SIN_INDICE` | — |
| Corrida posterior | `EMITIDA` | `CON_INDICE_APLICADO` | `CORRIDA_POSTERIOR` |

La corrección no modifica #374. El read model continúa devolviendo el estado
persistido y el frontend sólo traduce sus dimensiones de presentación.
