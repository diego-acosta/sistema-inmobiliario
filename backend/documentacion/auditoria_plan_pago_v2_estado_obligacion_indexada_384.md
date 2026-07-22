# Auditoría #384 — Estado de obligación en cuotas indexadas de Plan Pago V2

## Alcance y conclusión

**Clasificación:** E — combinación correcta, con contrato insuficientemente explícito.

`obligacion_financiera` es núcleo de Financiero. El plan y sus bloques son núcleo
de Comercial; las referencias entre ambos son trazabilidad. Esta auditoría no
modifica deuda, SQL, transiciones, etiquetas ni el endpoint read-only.

Una obligación `PROYECTADA` puede tener indexación materializada. La indexación
describe el cálculo/composición monetaria de la cuota; `estado_obligacion`
describe su ciclo de vida financiero. Por eso `PROYECTADA + CON_INDICE_APLICADO`
es válido tanto para `AL_NACIMIENTO` como para `CORRIDA_POSTERIOR`.

La corrección mínima es documental: el contrato ahora declara las tres
dimensiones separadas y los tests del escenario demo congelan la combinación.

## Evidencia auditada

* SQL: el `CHECK chk_obligacion_estado` enumera `PROYECTADA`, `EMITIDA`,
  `EXIGIBLE`, `PARCIALMENTE_CANCELADA`, `CANCELADA`, `VENCIDA`, `ANULADA`,
  `REEMPLAZADA` y `PENDIENTE_AJUSTE`. No existe una columna de indexación que
  sustituya ese estado. `importe_total` y `saldo_pendiente` se recomponen desde
  la composición activa.
* Generación PPV2: los servicios de generación crean cuotas con
  `estado_obligacion=PROYECTADA`; la generación indexada al nacimiento agrega
  `obligacion_financiera_indexacion` y `AJUSTE_INDEXACION` sin transición de
  estado.
* Corridas V2: la aplicación agrega/reemplaza la composición de ajuste y
  actualiza importes/saldo/versionado. Su elegibilidad admite `PROYECTADA`,
  `EMITIDA`, `EXIGIBLE` y `VENCIDA`, y excluye estados terminales o de pago; no
  ejecuta una transición contractual por indexar.
* Read model: `PlanPagoVentaV2Repository` devuelve directamente
  `o.estado_obligacion`; en cambio calcula exclusivamente campos de
  presentación de indexación. La prioridad es error de la corrida más reciente,
  exclusión, índice materializado, bloque indexado sin índice y, por último,
  `NO_REQUIERE_INDICE`. Conserva una corrida aplicada efectiva aun cuando una
  corrida posterior falle.
* Pago: la persistencia cambia a `PARCIALMENTE_CANCELADA` cuando queda saldo y
  a `CANCELADA` cuando es cero, sin borrar indexación ni composición.
* Frontend: “Estado obligación” usa `estado_obligacion`; “Estado pago” se deriva
  de estado/saldo; “Indexación” usa sólo `estado_indexacion_presentacion` y
  `origen_indexacion`. No se detectó una etiqueta que reescriba “Proyectada”.

## Estados y transiciones verificadas

| Estado | Semántica/verificación actual |
| --- | --- |
| `PROYECTADA` | Cuota planificada materializada por PPV2; puede tener capital e índice aplicado. |
| `EMITIDA` | Deuda emitida; el repositorio de mora la selecciona como origen de `VENCIDA`. |
| `EXIGIBLE` | Valor permitido y elegible para corrida; no se halló en PPV2 un comando que haga `EMITIDA -> EXIGIBLE`. |
| `VENCIDA` | La tarea de mora actualiza `EMITIDA` con vencimiento anterior y saldo positivo. |
| `PARCIALMENTE_CANCELADA` | Pago/imputación con saldo positivo menor al importe. |
| `CANCELADA` | Pago/imputación con saldo cero. |
| `ANULADA` | Anulación financiera; implementada en flujos financieros ajenos a PPV2. |
| `REEMPLAZADA` | Reemplazo financiero; implementado en el repositorio financiero. |
| `PENDIENTE_AJUSTE` | Valor permitido por SQL y excluido de indexación V2; fuera de los escenarios solicitados. |

`PROYECTADA -> EMITIDA` y `EMITIDA -> EXIGIBLE` son transiciones conceptuales
documentadas por el modelo, pero **NO CONFIRMADAS como comando PPV2** en la
implementación auditada. Una fecha de vencimiento no emite ni vuelve exigible una
cuota: sólo la rutina de mora verificada realiza `EMITIDA -> VENCIDA`.

## Matriz semántica

| Estado obligación | Estado indexación | Origen | Pago | Presentación esperada | ¿Válida? |
| --- | --- | --- | --- | --- | --- |
| `PROYECTADA` | `PROYECTADA_SIN_INDICE` | — | Pendiente | Proyectada / Proyectada sin índice | Sí |
| `PROYECTADA` | `CON_INDICE_APLICADO` | `AL_NACIMIENTO` | Pendiente | Proyectada / Indexada al nacimiento | Sí |
| `PROYECTADA` | `CON_INDICE_APLICADO` | `CORRIDA_POSTERIOR` | Pendiente | Proyectada / Ajustada por corrida | Sí |
| `EMITIDA` | `CON_INDICE_APLICADO` | `AL_NACIMIENTO` | Pendiente | Emitida / Indexada al nacimiento | Sí |
| `EXIGIBLE` | `CON_INDICE_APLICADO` | `CORRIDA_POSTERIOR` | Pendiente | Exigible / Ajustada por corrida | Sí |
| `PARCIALMENTE_CANCELADA` | `CON_INDICE_APLICADO` | Cualquiera | Parcial | Parcialmente cancelada / Parcial | Sí |
| `CANCELADA` | `CON_INDICE_APLICADO` | Cualquiera | Pagada | Cancelada / Pagada | Sí |
| `ANULADA` | Cualquiera | Cualquiera | Anulada | Anulada; indexación sólo trazabilidad | Sí |
| `REEMPLAZADA` | Cualquiera | Cualquiera | Reemplazada | Reemplazada; indexación sólo trazabilidad | Sí |
| Cualquiera | `CON_ERROR` | `CORRIDA_POSTERIOR` | Cualquiera | Estado contractual intacto / Con error | Sí |
| Cualquiera | `EXCLUIDA` | `CORRIDA_POSTERIOR` | Cualquiera | Estado contractual intacto / Excluida | Sí |

## Diagnóstico del demo `DEMO-VTA-CUOTAS-PPV2-INDEXADA`

| Cuota/bloque | Estado obligación | Estado indexación | Origen | Capital | Ajuste | Vigente/saldo | Corrida | Diagnóstico |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Índice al nacimiento | `PROYECTADA` | `CON_INDICE_APLICADO` | `AL_NACIMIENTO` | > 0 | > 0 | materializado | ninguna aplicada | Válida: índice y ajuste nacen con la cuota. |
| Proyectada sin índice | `PROYECTADA` | `PROYECTADA_SIN_INDICE` | — | > 0 | 0 | capital | ninguna | Válida: bloque indexable sin valor aplicado. |
| Corrida posterior | `PROYECTADA` | `CON_INDICE_APLICADO` | `CORRIDA_POSTERIOR` | > 0 | > 0 | materializado | una `APLICADA` vigente | Válida: corrida no emite la cuota. |

El fixture además conserva una corrida `PENDIENTE_APLICACION` y una `FALLIDA`;
la segunda es informativa y no sustituye la referencia aplicada efectiva.

## Decisión de contrato y CORE-EF

`GET /api/v1/ventas/{id_venta}/plan-pago-v2` es `QUERY_READLIKE`: no escribe,
no requiere headers write, no tiene idempotencia, outbox, lock ni versionado de
comando (**NO APLICA**). Se preserva el payload. `estado_obligacion` es
persistido/contractual; `estado_pago` es derivado por la UI desde estado y
saldo; `estado_indexacion_presentacion` y `origen_indexacion` son derivados de
presentación. No se modificaron #374, SQL, frontend ni transiciones.
