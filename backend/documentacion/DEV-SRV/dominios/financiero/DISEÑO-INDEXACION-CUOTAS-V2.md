# DISEÑO — Indexación de cuotas V2

## Estado del documento

- Issue principal: `#338 — [Financiero] Diseño de indexación de cuotas V2`.
- Fuente obligatoria: `#336` y `backend/documentacion/auditorias/AUDIT-336-indexacion-cuotas-v2.md`.
- Tipo: diseño funcional/técnico, exclusivamente documental.
- Dominio dueño del cálculo: financiero.
- Fecha: 2026-07-10.

## Fuentes revisadas

- Issues GitHub: `#338`, `#336`.
- Auditoría principal: `backend/documentacion/auditorias/AUDIT-336-indexacion-cuotas-v2.md`.
- Arquitectura: `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`, dominios personas, comercial, operativo y analítico.
- DEV-SRV Comercial: `MODELO-PLANES-PAGO-VENTA.md`, `MODELO-PLANES-PAGO-VENTA-BLOQUES.md`, `DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`.
- DEV-SRV Financiero: `MODELO-FINANCIERO-FIN.md`, `SRV-FIN-004-gestion-de-indices-financieros.md`, `SRV-FIN-006-cronograma-y-obligaciones.md`, `SRV-FIN-007-simulacion-y-registro-de-pago.md`, `SRV-FIN-008-gestion-de-imputacion-financiera.md`, `SRV-FIN-009-gestion-de-mora-creditos-y-debitos.md`, `SRV-FIN-010-emision-financiera.md`, auditorías de método/fórmula/soporte físico/cronograma/preview/SQL de planes V2.
- DEV-API: `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`, `backend/documentacion/DEV-API/dominios/financiero/DEV-API-FIN-001.md`.
- SQL y DER: `patch_plan_pago_venta_bloque_indexacion_20260528.sql`, `patch_plan_pago_venta_bloques_v2_20260515.sql`, `seed_minimo.sql`, `seed_test_baseline.sql`, `DER-COMERCIAL.md`, `DER-FINANCIERO.md`.
- Backend: routers comercial/financiero; servicios V2 por bloques; `IndexacionCuotaCalculator`; servicios de ajuste/bonificación de indexación, pagos e imputaciones; repositorios `plan_pago_venta_v2_repository.py`, `financiero_repository.py`, `comercial_repository.py`.
- Tests relevados: planes V2, preview/generación por bloques, consulta integral, calculadora de indexación, pagos, ventas completas, imputaciones, estado de cuenta y mora.

## 1. Objetivo y alcance

Este diseño cierra las decisiones necesarias para implementar después la indexación posterior de cuotas V2 mediante corridas formales, preview obligatorio y command CORE-EF. Resuelve la brecha detectada por la auditoría: existe soporte parcial (`AJUSTE_INDEXACION`, índices, configuración por bloque, trazabilidad por obligación y calculadora pura), pero no existe una corrida idempotente, auditable, atómica y coordinada con pagos, imputaciones, mora y recibos.

Alcance de esta V2 inicial:

1. Diseñar SQL futuro de `corrida_indexacion_financiera` y `corrida_indexacion_financiera_detalle`, sin escribir DDL aquí.
2. Diseñar preview de indexación.
3. Diseñar command CORE-EF de aplicación.
4. Diseñar automatización conceptual por publicación de índices.
5. Diseñar integración con alta manual e importación de ventas históricas.
6. Diseñar política de reindexación manual y corrección controlada.

Límites explícitos:

- No se implementa código, SQL, endpoint, schema, seed, frontend, job ni integración real con importadores.
- No se modifica pagos, imputaciones, mora, recibos, caja ni emisión documental.
- No se incluyen cuotas pagadas/parcialmente pagadas, compensaciones, notas de crédito, reimputación automática ni rectificación con recibos emitidos.

Relación de dominios:

| Concepto | Clasificación | Dominio dueño | Decisión |
| --- | --- | --- | --- |
| `plan_pago_venta` | núcleo | comercial | Define la forma de pago pactada; no calcula deuda. |
| `plan_pago_venta_bloque` | núcleo | comercial | Define tramos/bloques; no recibe pagos ni saldos. |
| `plan_pago_venta_bloque_indexacion` | soporte transversal | comercial | Representa la cláusula de indexación pactada en el bloque; Financiero la consume funcionalmente para calcular y aplicar. |
| `generacion_cronograma_financiero` | núcleo | financiero | Materializa el cronograma inicial; no reemplaza la corrida posterior. |
| `obligacion_financiera` | núcleo | financiero | Fuente de verdad de deuda, importe, saldo y estado financiero. |
| `composicion_obligacion` | núcleo/soporte financiero | financiero | Explica capital, interés, ajuste y saldos por componente. |
| `obligacion_financiera_indexacion` | soporte de trazabilidad | financiero | Congela índice aplicado por obligación; no agrupa corridas. |
| `indice_financiero` / `indice_financiero_valor` | núcleo | financiero | Fuente de valores publicados. |
| Corrida de indexación | núcleo | financiero | Orquesta cálculo, aplicación, auditoría, idempotencia y rollback. |

Comercial es dueño semántico de la cláusula de indexación pactada en el bloque. Financiero consume esa configuración y es dueño exclusivo del cálculo, aplicación, deuda y trazabilidad financiera. Comercial no debe duplicar la fórmula financiera: puede solicitar preview/confirmación de una venta o importación, pero el cálculo de fecha base, fecha de corte, índice, coeficiente, ajuste y composición pertenece a Financiero. Financiero debe ser fuente única porque ya posee índices, obligaciones, saldos, composiciones, pagos, imputaciones, mora, trazabilidad e invariantes CORE-EF.

## 2. Glosario

- **Fecha de venta:** fecha comercial del negocio de compraventa. Puede ser anterior a la fecha de alta en sistema.
- **Fecha de alta en sistema:** timestamp en que se registra la venta/importación en la instalación.
- **Fecha base:** fecha desde la cual se toma el índice base del bloque. En el soporte actual corresponde a `plan_pago_venta_bloque_indexacion.fecha_base_indice` y su `valor_base_indice`.
- **Fecha de corte:** fecha objetivo para decidir hasta qué vencimientos/períodos se calculan con índice publicado. En venta histórica es la fecha funcional de alta/confirmación o la fecha de corte elegida en preview; en reindexación manual es parámetro obligatorio.
- **Fecha de publicación:** fecha en que un `indice_financiero_valor` pasa de alta técnica/no computable a publicado/computable.
- **Período de índice:** unidad temporal representada por `indice_financiero_valor.fecha_valor` o período equivalente vigente en SQL/documentación.
- **Índice base:** valor usado como denominador, congelado en la configuración del bloque.
- **Índice aplicado:** valor publicado seleccionado para la fecha objetivo de la cuota/corte.
- **Coeficiente:** `indice_aplicado / indice_base`, con escala de 8 decimales.
- **Capital base:** componente original `CAPITAL_VENTA` de la obligación; para generación inicial indexada deriva del capital de la cuota calculada desde el bloque.
- **Ajuste:** diferencia no negativa `capital_base * coeficiente - capital_base`, materializable como `AJUSTE_INDEXACION` solo si `>= 0` por las restricciones vigentes de `composicion_obligacion`.
- **Corrida:** unidad auditada de cálculo/aplicación para un `plan_pago_venta + plan_pago_venta_bloque`.
- **Detalle de corrida:** resultado por obligación analizada, elegible o excluida.
- **Obligación elegible:** obligación que puede ser indexada en V2 inicial: `PROYECTADA`, `EMITIDA`, `EXIGIBLE` o `VENCIDA`, sin pagos, imputaciones, recibos congelantes, mora/punitorios incompatibles ni lock incompatible.
- **Obligación excluida:** obligación analizada que no se modifica y registra motivo.
- **Obligación proyectada sin índice:** obligación generada con capital base porque todavía no existe valor publicado aplicable. `PROYECTADA_SIN_INDICE` no es un valor de `estado_obligacion`; es estado de indexación/trazabilidad y convive con un estado financiero real, normalmente `PROYECTADA`.
- **Corrida automática:** corrida propuesta por publicación de índice o job, sin intervención manual en detección.
- **Corrida manual:** corrida solicitada por usuario autorizado.
- **Corrida reemplazante:** corrida que corrige/reemplaza una aplicada anterior, con motivo y vínculo explícito.

## 3. Unidad de operación

Decisión cerrada: la unidad inicial de operación es `plan_pago_venta + plan_pago_venta_bloque`. La obligación es la granularidad de detalle; la publicación de índice puede disparar una detección masiva, pero se agrupa en corridas separadas por plan y bloque.

Justificación:

- El bloque contiene la configuración de indexación (`plan_pago_venta_bloque_indexacion`).
- La obligación contiene el importe/saldo a modificar y referencia opcional al bloque.
- Una corrida por índice global perdería control transaccional fino y elevaría riesgos masivos.
- Una corrida por obligación dificultaría idempotencia y auditoría del tramo completo.

Relación conceptual:

```text
corrida_indexacion_financiera
  ├─ id_plan_pago_venta
  ├─ id_plan_pago_venta_bloque
  ├─ id_plan_pago_venta_bloque_indexacion
  ├─ id_indice_financiero
  ├─ origen_corrida
  └─ N corrida_indexacion_financiera_detalle -> obligacion_financiera
```

La detección por publicación de índice produce grupos candidatos por `(id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero, fecha_corte/período_aplicado)`. Cada grupo genera una propuesta/preview/corrida independiente. Una importación masiva puede tener una corrida lógica de lote, pero financieramente debe persistir corridas por plan+bloque y registrar el lote/fila como metadato de origen.

## 4. Base de cálculo

Decisión cerrada:

- Base de cálculo posterior: componente original `CAPITAL_VENTA` de `composicion_obligacion` por obligación.
- No se reescribe `CAPITAL_VENTA`.
- La diferencia se materializa con `AJUSTE_INDEXACION` solo cuando el importe calculado es `>= 0`; además, el SQL vigente de `composicion_obligacion` exige importes y saldos `>= 0`.
- El cálculo debe persistir snapshot de valores utilizados en cabecera/detalle para reproducibilidad, aunque `CAPITAL_VENTA` siga siendo fuente primaria.

Fórmula vigente a respetar según calculadora/auditorías:

```text
coeficiente_indexacion = valor_aplicado_indice / valor_base_indice
importe_indexado = capital_base * coeficiente_indexacion
ajuste_indexacion = importe_indexado - capital_base
importe_total_vigente_nuevo = capital_base + ajuste_indexacion_valido + otros_componentes_compatibles_no_indexables
```

Reglas:

- `valor_base_indice > 0`; si es cero o nulo, error bloqueante.
- `valor_aplicado_indice` debe ser publicado/computable; si falta, la obligación queda `PROYECTADA_SIN_INDICE` o la confirmación se bloquea según origen.
- `coeficiente_indexacion` se redondea a 8 decimales con criterio `ROUND_HALF_UP`, alineado al helper actual.
- Importes monetarios se redondean a 2 decimales con `ROUND_HALF_UP`.
- Si existe `AJUSTE_INDEXACION` previo, la corrida no acumula ciegamente: calcula el ajuste objetivo desde capital original y reemplaza/actualiza el componente al importe objetivo `>= 0`, registrando ajuste anterior y nuevo.
- Duplicidad: una obligación no puede recibir dos ajustes para el mismo índice/período/corrida efectiva. Si ya existe `obligacion_financiera_indexacion` para el mismo valor aplicado y la misma versión/base, el reintento idéntico es idempotente; si difiere, es conflicto o corrida reemplazante autorizada.
- Diferencias negativas: V2 inicial no permite persistir componentes de indexación por debajo de cero ni asume cambios SQL. Si `valor_aplicado_indice < valor_base_indice` y el cálculo produce diferencia negativa, la corrida no modifica la obligación y devuelve `AJUSTE_NEGATIVO_NO_SOPORTADO`. El tratamiento queda reservado para una evolución futura mediante bonificación de indexación, crédito financiero, ajuste compensatorio, nota de crédito o modificación explícita del modelo físico.
- Múltiples períodos: la corrida aplica el valor correspondiente a cada obligación según fecha objetivo; no encadena coeficientes acumulativos. Siempre recalcula contra índice base y capital original para evitar drift.

## 5. Elegibilidad de obligaciones

Matriz inicial:

| Estado/condición | Decisión V2 inicial | Motivo |
| --- | --- | --- |
| `PROYECTADA` sin pagos/imputaciones | Elegible | No hay efectos financieros externos. |
| `EMITIDA` sin pagos/imputaciones/recibos incompatibles | Elegible | Estado financiero vigente sin aplicaciones. |
| `EXIGIBLE` sin pagos/imputaciones/recibos incompatibles | Elegible | Estado financiero exigible sin aplicaciones. |
| `VENCIDA` sin aplicaciones ni mora incompatible | Elegible con advertencia | La fecha vencida no impide indexar si no hay efectos posteriores. |
| `PARCIALMENTE_CANCELADA` | Fuera de alcance | Requiere regla de saldo aplicado/reimputación. |
| `CANCELADA` | Fuera de alcance | No alterar conciliación, aplicaciones ni recibos. |
| `ANULADA` | Excluida | No se modifica deuda anulada. |
| `REEMPLAZADA` | Excluida | La obligación vigente es otra. |
| `PENDIENTE_AJUSTE` | No elegible automáticamente | Debe resolverse según causa antes de indexar. |
| Refinanciada | Excluida/bloqueante | Requiere flujo de refinanciación. |
| Con punitorios | Excluida | Evita alterar cálculo accesorio. |
| Con recibos/documentos que congelan importe | Excluida | No modificar importes documentados. |
| Con imputaciones/aplicaciones | Excluida | Fuera de alcance inicial. |
| Con ajustes manuales no indexación | Excluida salvo whitelist futura | Evita sobrescribir decisiones manuales. |
| Con bonificaciones de indexación | Excluida en V2 inicial | Requiere política neta ajuste/bonificación. |
| Con índice ya aplicado mismo período | Idempotente o excluida | No reindexar dos veces. |
| Con corrida previa aplicada distinta | Excluida salvo reemplazante autorizada | Trazabilidad y motivo obligatorios. |
| Con lock activo incompatible | Bloqueante | No se aplica la corrida completa. |

`PROYECTADA_SIN_INDICE` no es estado financiero de `obligacion_financiera`; es trazabilidad de indexación asociada a una obligación con estado real, normalmente `PROYECTADA`. Si una corrida contiene al menos una obligación elegible y otras excluidas, el preview puede mostrar ambas. Para aplicar, V2 inicial exige que el payload declare la política: aplicar solo elegibles conocidas o bloquear si existen excluidas. Decisión inicial: para `PUBLICACION_INDICE` y `REINDEXACION_MANUAL`, se permite aplicar elegibles y dejar excluidas reportadas sin efectos; para `ALTA_MANUAL_VENTA_HISTORICA` e `IMPORTACION_VENTA_HISTORICA`, una cuota no calculable por falta de índice bloquea confirmación de esa venta/fila salvo borrador.

## 6. Modelo conceptual de corrida

Sin DDL, la futura cabecera `corrida_indexacion_financiera` debe incluir:

- Identidad: `id_corrida_indexacion_financiera`, `uid_global`, `version_registro`.
- Alcance: `id_plan_pago_venta`, `id_plan_pago_venta_bloque`, `id_plan_pago_venta_bloque_indexacion`, `id_generacion_cronograma_financiero` si aplica.
- Índice: `id_indice_financiero`, `id_indice_financiero_valor_base` si existe, `id_indice_financiero_valor_aplicado`, período/fecha base y aplicado, valores base/aplicado.
- Fechas: `fecha_base`, `fecha_corte`, `fecha_calculo`, `fecha_publicacion_indice` cuando aplique.
- Origen: catálogo `origen_corrida`, datos JSON controlados por origen, referencia técnica/funcional.
- Estado: ciclo definido en sección 7.
- Idempotencia: `hash_corrida`, `op_id`, `payload_hash`, versiones incluidas.
- Contexto CORE-EF: `id_usuario`, `id_sucursal`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, op_ids, timestamps.
- Totales: analizadas, elegibles, excluidas, aplicadas, importes antes/después, ajuste total anterior/nuevo, saldo antes/después.
- Reemplazo/reversión: `id_corrida_anterior`, `id_corrida_reemplazante`, `motivo` obligatorio para corrección/reproceso.
- Auditoría/outbox: estado de evento emitido o referencia a outbox.

Detalle `corrida_indexacion_financiera_detalle`:

- Identidad y FK a corrida.
- `id_obligacion_financiera`, `version_esperada`, `version_resultante`.
- `capital_base`, `id_composicion_capital_venta`.
- Índice base/aplicado: ids, fechas, valores, coeficiente.
- `ajuste_anterior`, `ajuste_nuevo`, diferencia neta, referencia a componente `AJUSTE_INDEXACION` creado/actualizado.
- `importe_anterior`, `importe_nuevo`, `saldo_anterior`, `saldo_nuevo`.
- Elegibilidad: `ELEGIBLE`, `EXCLUIDA`, `BLOQUEANTE`, `RESERVADA_FUTURA`, motivo, error técnico/funcional.
- Snapshots antes/después mínimos de obligación y composiciones.
- Referencia a `obligacion_financiera_indexacion` resultante o trazabilidad equivalente.

Catálogo de origen y datos adicionales:

| Origen | Datos obligatorios |
| --- | --- |
| `IMPORTACION_VENTA_HISTORICA` | id/lote de importación, fila, hash de fila, usuario, venta creada, política parcial. |
| `ALTA_MANUAL_VENTA_HISTORICA` | usuario, venta, fecha de venta, fecha de alta, motivo/observación. |
| `PUBLICACION_INDICE` | id valor publicado, fecha publicación, job/detección, lote de impacto. |
| `REINDEXACION_MANUAL` | usuario autorizado, motivo, fecha de corte, selección de bloque. |
| `CORRECCION_INDICE` | valor anterior/nuevo, corrida anterior, motivo, autorización. |
| `REPROCESO_CONTROLADO` | corrida anterior, causa técnica/funcional, aprobación, op técnica. |

## 7. Estados y transiciones

Estados persistibles V2 inicial:

- `BORRADOR`: corrida creada por importación/alta o preparación, no validada.
- `PREVISUALIZADA`: snapshot calculado y hash emitido.
- `PENDIENTE_APLICACION`: preview persistido listo para command; último estado persistido antes de comenzar la aplicación.
- `APLICADA`: todos los detalles elegibles declarados fueron aplicados atómicamente.
- `FALLIDA`: estado persistido en una transacción técnica separada después de rollback financiero; conserva error, etapa y diagnóstico.
- `ANULADA`: corrida no aplicada descartada.
- `REEMPLAZADA`: corrida aplicada que queda superada por una reemplazante.

Reservados:

- `REVERSADA`: futuro, cuando exista reversión completa.
- `APLICADA_PARCIAL`: no se usa en V2 inicial; se prefiere rollback total. Solo podría existir en futuro para lotes masivos técnicamente particionados, nunca para una misma corrida plan+bloque.
- `APLICANDO`: no es estado persistible en V2 inicial; es un estado operativo en memoria/ejecución indicado por locks lógicos activos.

Transiciones permitidas:

```text
BORRADOR -> PREVISUALIZADA -> PENDIENTE_APLICACION -> APLICADA
BORRADOR/PREVISUALIZADA/PENDIENTE_APLICACION -> ANULADA
PENDIENTE_APLICACION -> FALLIDA (solo luego de rollback financiero y en transacción técnica separada)
APLICADA -> REEMPLAZADA (solo por corrección/reproceso autorizado)
APLICADA -> REVERSADA (futuro)
```

Prohibido: persistir `APLICANDO`; `FALLIDA -> APLICADA` sin nueva corrida/reintento idempotente controlado; aplicar sin preview válido; reemplazar sin motivo. El lock lógico, no un estado persistido, indica ejecución en curso.

## 8. Preview

Contrato conceptual del preview:

- Clasificación: `PREVIEW_READLIKE` si es efímero; `COMMAND_WRITE_TECNICO` si persiste una corrida `PREVISUALIZADA`.
- Entrada: plan, bloque, índice, fecha base, fecha de corte, origen, parámetros de venta/importación si aplica, modo `efimero` o `persistir_preview`.
- Salida: plan, bloque, índice, origen, fecha base/corte, obligaciones elegibles/excluidas, motivo, capital base, índices, coeficiente, ajuste anterior/nuevo, importe/saldo anterior/nuevo, versiones esperadas, hash reproducible, advertencias y errores bloqueantes.

Decisión: admitir ambos modos.

1. Preview efímero para consultas rápidas y wizard: no crea corrida, no requiere headers write, devuelve hash.
2. Preview persistido como `PREVISUALIZADA/PENDIENTE_APLICACION` para aplicación posterior, importación masiva o automatización: crea cabecera/detalle sin modificar obligaciones y sí requiere contexto CORE-EF si persiste.

Invalidación del preview: cualquier cambio en obligación, composición, pago, imputación, índice/valor, configuración de bloque, fecha de corte, conjunto de obligaciones o versiones rompe el hash. El command debe recomputar/verificar `hash_corrida` y versiones; si no coincide, error `PREVIEW_VENCIDO` o `HASH_NO_COINCIDENTE`.

## 9. Aplicación

Command conceptual de aplicación:

- Clasificación: `COMMAND_WRITE_NEGOCIO` sincronizable.
- Headers: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; `If-Match-Version` sobre la corrida persistida o aggregate versionado equivalente.
- Entrada: `id_corrida_indexacion_financiera` o payload completo + `preview_hash`, plan, bloque, índice, fecha de corte, versiones esperadas de obligaciones, política de exclusiones, motivo si reproceso/corrección.
- Validaciones: idempotencia, corrida no aplicada/reemplazada, hash vigente, versiones, elegibilidad, índice publicado, locks, ausencia de pagos/imputaciones/recibos/mora incompatibles.
- Lock: plan+bloque y obligaciones elegibles, adquirido antes de modificar y liberado al commit/rollback.
- Transacción: una sola frontera financiera para la corrida plan+bloque. Ante cualquier fallo de aplicación, rollback total; luego se persiste `FALLIDA` en una transacción técnica separada con error, etapa y diagnóstico.
- Modificaciones futuras conceptuales: crear/actualizar componente `AJUSTE_INDEXACION` con importe `>= 0`; actualizar el importe vigente de la obligación (`importe_total` conceptual o campo físico equivalente definido por el issue SQL/API posterior); actualizar `saldo_pendiente`; crear/actualizar trazabilidad `obligacion_financiera_indexacion`; incrementar `version_registro`; registrar detalle/snapshots; outbox/auditoría.

Regla de saldo:

- Si no existen pagos ni aplicaciones, `saldo_pendiente` acompaña el importe vigente nuevo calculado.
- Si existen efectos previos, queda fuera de alcance inicial y se bloquea.
- Nunca generar saldo negativo.
- Nunca borrar aplicaciones existentes.

Idempotencia del command: mismo `op_id` + mismo hash + mismo plan/bloque/índice/fecha/versiones devuelve resultado anterior con `200`. Mismo `op_id` con payload distinto devuelve `IDEMPOTENT_PAYLOAD_CONFLICT` con `409`.

## 10. Automatización por publicación de índice

Proceso completo:

1. Alta técnica de `indice_financiero_valor`: registra valor, aún no necesariamente computable.
2. Publicación del valor: cambia estado a publicado/computable y emite evento técnico/financiero.
3. Detección de impacto: job identifica bloques `INDEXACION` con ese índice y obligaciones con estado financiero real elegible (`PROYECTADA`, `EMITIDA`, `EXIGIBLE` o `VENCIDA`) y/o trazabilidad `PROYECTADA_SIN_INDICE` que pasan a ser calculables.
4. Agrupamiento por `plan_pago_venta + plan_pago_venta_bloque`.
5. Creación de propuestas/previews persistidos; no modificar obligaciones en esta transacción masiva.
6. Validación de elegibilidad y errores por grupo.
7. Aplicación separada: requiere confirmación o job configurado.
8. Reporte por corrida y lote.
9. Reintentos idempotentes por lote/job/op_id.
10. Fallos: una corrida fallida no afecta otras; dentro de cada corrida hay rollback total.
11. Auditoría: vínculo con valor publicado, job, usuario/instalación técnica.

Decisión inicial: la publicación detecta y prepara; la aplicación efectiva queda separada y controlada. Aplicación automática solo si se configura explícitamente por índice/bloque/plan, con límites de lote, auditoría y posibilidad de revisión. No acoplar reindexación masiva a la transacción que publica el índice.

Índices fuera de orden o correcciones: la detección debe comparar período/fecha de valor y corridas ya aplicadas. Si un valor retroactivo afecta obligaciones ya indexadas, no reindexa automáticamente; genera impacto `CORRECCION_INDICE` o `REPROCESO_CONTROLADO`.

## 11. Integración con ventas históricas

Regla única: todo canal (alta manual, Excel, migración, reproceso) debe invocar un componente financiero conceptual, por ejemplo `ResolverIndexacionVentaHistoricaService`, que resuelve fecha base, fecha de corte, búsqueda de índice, coeficiente, ajuste, composición y errores. Comercial no implementa fórmula.

### Venta nueva del día

- Fecha base: la configurada en `plan_pago_venta_bloque_indexacion` al generar el bloque.
- Si todavía no corresponde valor posterior o no existe índice publicado para la fecha objetivo, la cuota se genera con `CAPITAL_VENTA`, sin `AJUSTE_INDEXACION`, y trazabilidad/estado de indexación `PROYECTADA_SIN_INDICE`.
- `AJUSTE_INDEXACION` se materializa solo cuando existe índice aplicado publicado y una generación/corrida válida.
- La obligación no calculable mantiene un estado financiero real vigente, normalmente `PROYECTADA`, más estado de indexación `PROYECTADA_SIN_INDICE` en trazabilidad/consulta.

### Alta manual de venta histórica

- Detección: `fecha_venta < fecha_alta_sistema` o fecha comercial anterior al día operativo de registración.
- Fecha base: la del bloque/índice pactado; si no existe, error de configuración.
- Fecha de corte: por defecto fecha de alta/confirmación; puede ser parámetro si el flujo lo habilita.
- Se consultan índices históricos publicados hasta la fecha objetivo de cada cuota/corte.
- Decisión: generar obligaciones directamente con capital y `AJUSTE_INDEXACION` cuando el índice esté disponible; evitar crear obligaciones desactualizadas para corregirlas inmediatamente.
- Si faltan índices: se permite guardar borrador comercial/preview, pero se bloquea confirmación definitiva de la venta/fila si alguna cuota vencida o calculable histórica no tiene índice requerido. Para cuotas futuras sin índice, puede generarse `PROYECTADA_SIN_INDICE`.
- El usuario debe ver cuotas calculadas, cuotas proyectadas sin índice y errores bloqueantes.

### Importación de ventas históricas

- Usa el mismo componente financiero que alta manual.
- El preview de importación muestra importe base, ajuste e importe final por cuota/fila.
- Prevalidación: disponibilidad de índices, configuración de bloque, unicidad/idempotencia de fila, consistencia de personas/venta.
- Fila bloqueada: si faltan índices para cuotas históricas exigibles o hay inconsistencias.
- Parcialidad: una importación puede confirmar filas válidas y dejar inválidas rechazadas solo si cada fila tiene `op_id/hash` y reporte; nunca confirmar una fila con cuotas incorrectamente indexadas.
- Agrupamiento financiero: corridas por plan+bloque; el lote de importación se registra como origen. No una corrida global única que mezcle planes/bloques.
- Idempotencia: `id_lote_importacion + row_number/clave negocio + hash_fila + plan + bloque + hash_financiero`.

## 12. Corrección de índices

Política conceptual:

| Caso | Decisión |
| --- | --- |
| Valor corregido antes de publicarse/usarse | Se puede modificar con versionado y auditoría técnica. |
| Valor corregido después de generar preview no aplicado | Invalida preview/corrida pendiente. |
| Valor corregido después de generar obligaciones sin pagos | Requiere `CORRECCION_INDICE` con corrida reemplazante; si la nueva diferencia queda por debajo de cero, bloquea con `AJUSTE_NEGATIVO_NO_SOPORTADO`. |
| Valor corregido después de corrida aplicada | No editar destructivamente; crear nueva versión de valor o marca de corrección y corrida reemplazante/compensatoria. Si exige disminuir la deuda, V2 inicial no persiste componente menor a cero y deriva a evolución futura. |
| Valor corregido después de pagos/recibos | Fuera de alcance inicial; requiere issue avanzado de compensación/reversión. |
| Valor cargado retroactivamente/fuera de orden | Detecta impactos y propone corridas; no aplica automáticamente sobre ya aplicadas. |

La solución preserva identificación del valor usado originalmente (`id_indice_financiero_valor`), snapshots de corrida, vínculo `corrida_anterior`/`corrida_reemplazante` y motivo obligatorio. Reversión completa queda reservada; la V2 inicial modela campos para no impedirla.

## 13. Concurrencia y locks

Incompatibilidades durante aplicación:

- pagos, imputaciones, reversión de imputaciones;
- generación/liquidación de mora y punitorios;
- ajustes manuales y bonificaciones;
- refinanciaciones, regeneraciones o reemplazos de obligaciones;
- emisión de recibos/documentos;
- indexaciones concurrentes del mismo plan+bloque/obligaciones;
- importaciones paralelas sobre la misma venta/plan;
- publicación simultánea del mismo índice cuando intente preparar la misma corrida.

Lock lógico:

- Granularidad primaria: recurso `INDEXACION_PLAN_BLOQUE:{id_plan_pago_venta}:{id_plan_pago_venta_bloque}`.
- Granularidad secundaria: cada `OBLIGACION_FINANCIERA:{id}` elegible.
- Orden: adquirir primero plan+bloque, luego obligaciones ordenadas por id ascendente, luego componentes/trazabilidad si aplica.
- Momento: después de `PENDIENTE_APLICACION` y antes de validar versiones finales; `APLICANDO` solo puede existir como estado operativo no persistido.
- Liberación: commit/rollback; expiración configurable; renovación para lotes largos.
- Si una obligación no puede bloquearse: no se aplica la corrida; rollback total de la transacción financiera y persistencia posterior de `FALLIDA` con error `LOCK_ACTIVE` en transacción técnica separada.

## 14. Idempotencia

Clave mínima común:

```text
op_id + origen + id_plan_pago_venta + id_plan_pago_venta_bloque + id_indice_financiero + fecha_corte/período + hash_corrida + conjunto_obligaciones + versiones_obligaciones
```

Extensiones por origen:

- Importación: agregar `id_lote_importacion`, fila/clave externa y hash de fila.
- Alta histórica: agregar id venta/clave temporal y fecha de venta/alta.
- Publicación de índice: agregar `id_indice_financiero_valor` y lote/job de impacto.
- Reindexación manual: agregar usuario/motivo y fecha de corte.
- Corrección: agregar corrida anterior y valor corregido.
- Reintento técnico: mismo op_id/payload retorna mismo resultado; payload distinto es conflicto.

Diferenciación:

- Reintento idéntico: seguro, devuelve corrida/resultado existente.
- Nueva corrida válida: nuevo op_id y cambio legítimo de período/valor/versiones/motivo.
- Conflicto: mismo alcance con datos/versiones cambiadas sin reemplazo autorizado.
- Corrida reemplazante: requiere origen `CORRECCION_INDICE` o `REPROCESO_CONTROLADO` y motivo.

## 15. CORE-EF

Decisión CORE-EF:

| Operación conceptual | Clasificación | CORE-EF |
| --- | --- | --- |
| Preview efímero | `PREVIEW_READLIKE` | No exige headers write; debe devolver errores estándar. |
| Preview persistido/corrida previsualizada | `COMMAND_WRITE_TECNICO` | Exige headers CORE-EF porque persiste corrida. |
| Aplicación | `COMMAND_WRITE_NEGOCIO` | Exige headers, `If-Match-Version`, idempotencia, lock, outbox, rollback. |
| Job por publicación | `COMMAND_WRITE_TECNICO` + commands negocio por corrida | Contexto técnico y op_id/lote; aplicación separada. |
| Corrección/reversión futura | `COMMAND_WRITE_NEGOCIO` | Criticidad alta, motivo, reemplazo/reversión. |

Entidades financieras críticas deben tener `uid_global`, `version_registro`, op_ids, instalación/sucursal/usuario, trazabilidad de alta/modificación, optimistic locking y outbox en la misma transacción que el negocio. No se permite `{"detail":"..."}` para errores CORE-EF; usar envelope estándar/ErrorResponse.

## 16. API conceptual

No se crean endpoints en este PR; todos los endpoints y campos mencionados son diseño futuro hasta que un issue posterior implemente SQL/API. Contratos futuros propuestos, bajo `/api/v1`, kebab-case y separación read/write:

- `POST /api/v1/financiero/indexacion-cuotas-v2/preview`: preview efímero o persistido según flag. Read-like si no persiste.
- `POST /api/v1/financiero/indexacion-cuotas-v2/corridas/{id_corrida}/aplicar`: command write con headers CORE-EF e `If-Match-Version`.
- `GET /api/v1/financiero/indexacion-cuotas-v2/corridas/{id_corrida}`: consulta cabecera.
- `GET /api/v1/financiero/indexacion-cuotas-v2/corridas/{id_corrida}/detalles`: consulta detalle.
- `GET /api/v1/financiero/indexacion-cuotas-v2/corridas`: listado por plan, bloque, índice, estado, origen.
- `POST /api/v1/financiero/indexacion-cuotas-v2/corridas/{id_corrida}/reversar`: futura reversión, fuera de alcance inicial.
- `GET /api/v1/financiero/indices/{id_indice_financiero}/impacto-indexacion-cuotas-v2`: consulta de impacto.
- `GET /api/v1/financiero/indexacion-cuotas-v2/obligaciones-pendientes`: obligaciones `PROYECTADA_SIN_INDICE` o pendientes de corrida.

Respuesta exitosa: envelope `{ "ok": true, "data": ... }`. Error: `{ "ok": false, "error_code": "...", "error_message": "...", "details": ... }`.

## 17. Errores

| Error | HTTP conceptual | Uso |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Parámetros inválidos. |
| `NOT_FOUND` | 404 | Plan, bloque, índice, corrida u obligación inexistente. |
| `CONCURRENCY_ERROR` | 409 | Versión modificada / optimistic lock. |
| `LOCK_ACTIVE` | 409 | Recurso bloqueado. |
| `IDEMPOTENT_DUPLICATE` | 200 | Reintento idéntico exitoso: devuelve resultado previo. |
| `IDEMPOTENT_PAYLOAD_CONFLICT` | 409 | Mismo `op_id` con payload distinto. |
| `SYNC_CONFLICT` | 409 | Conflicto distribuido/op_id. |
| `TECHNICAL_INCONSISTENCY` | 409 | Datos incompatibles detectados antes de aplicar; fallas inesperadas quedan como error interno estándar fuera del contrato funcional. |
| `INDICE_FALTANTE` | 422 | No hay valor para fecha requerida. |
| `INDICE_NO_PUBLICADO` | 422 | Valor existe pero no computable. |
| `FECHA_BASE_INVALIDA` | 422 | Base nula/posterior/inconsistente. |
| `FECHA_CORTE_INVALIDA` | 422 | Corte fuera de rango. |
| `OBLIGACION_NO_ELEGIBLE` | 422 | Estado/condición no permitida. |
| `PREVIEW_VENCIDO` | 409 | Cambió información desde preview. |
| `HASH_NO_COINCIDENTE` | 409 | Hash de aplicación difiere. |
| `VERSION_MODIFICADA` | 409 | Versión esperada no coincide. |
| `CORRIDA_YA_APLICADA` | 409 | Aplicación repetida no idempotente; el reintento idéntico se resuelve con `IDEMPOTENT_DUPLICATE` 200. |
| `CORRIDA_REEMPLAZADA` | 409 | No operar corrida superada. |
| `AJUSTE_INDEXACION_DUPLICADO` | 409 | Componente duplicado no idempotente. |
| `AJUSTE_NEGATIVO_NO_SOPORTADO` | 422 | El cálculo produce diferencia menor a cero y V2 inicial no puede persistir componentes de indexación por debajo de cero. |
| `CONFIG_INDEXACION_INCOMPLETA` | 422 | Falta configuración de bloque. |
| `VALOR_INDICE_AMBIGUO` | 409 | Más de un valor aplicable. |
| `IMPORTACION_PARCIALMENTE_INVALIDA` | 200 | Request procesado con resultado detallado por fila y filas válidas/rechazadas. |
| `IMPORTACION_COMPLETAMENTE_INVALIDA` | 422 | Ninguna fila puede procesarse por errores de validación. |

## 18. Casos de borde

- Índice base igual a cero: bloqueante.
- Falta índice base: bloqueante de configuración.
- Falta índice aplicado: `PROYECTADA_SIN_INDICE` para futuro; bloqueante para cuotas históricas exigibles.
- Valor fuera de orden: detectar impacto, no aplicar automáticamente sobre corridas aplicadas.
- Venta histórica anterior al primer valor disponible: bloquear confirmación salvo borrador.
- Múltiples índices válidos para una fecha: `VALOR_INDICE_AMBIGUO`.
- Redondeos: coeficiente 8 decimales, dinero 2 decimales, snapshot de residuos si aplica.
- Ajuste negativo: bloqueante con `AJUSTE_NEGATIVO_NO_SOPORTADO`; no se modifica la obligación y el tratamiento queda fuera de alcance inicial.
- Obligación con ajuste previo: recalcular objetivo, no acumular.
- Importación parcialmente válida: confirmar solo filas válidas con idempotencia por fila; inválidas no persisten venta definitiva.
- Publicación duplicada: idempotente si mismo valor/hash; conflicto si difiere.
- Dos instalaciones publicando mismo índice: resolver por unicidad/versionado y conflictos CORE-EF.
- Cuota vencida sin pagos: elegible con advertencia si no hay mora persistida.
- Obligación con mora calculada: excluida/bloqueante.
- Venta con varios bloques indexados: una corrida por bloque.
- Distintos índices por bloque: corridas separadas por índice/bloque.
- Periodicidad distinta índice/cuota: seleccionar último publicado `<= fecha_objetivo`, según query vigente; si la política futura cambia, debe versionarse.
- Múltiples valores publicados el mismo día: debe impedirse o marcar ambigüedad.
- Fecha de venta posterior a fecha base configurada: validar coherencia; no usar índice base posterior sin decisión explícita.
- Corrección de índice luego de corrida: corrida reemplazante/correctiva.
- Corrida creada no aplicada: puede anularse o invalidarse.
- Reintento tras timeout: idempotencia por op_id/hash.
- Pérdida de lock: rollback financiero total, liberación/expiración de locks y persistencia técnica posterior de `FALLIDA`.
- Obligación modificada entre preview y command: `PREVIEW_VENCIDO`/`CONCURRENCY_ERROR`.
- Publicación masiva de varios índices: detección por lotes; aplicación separada.

## 19. Decisiones fuera de alcance

Quedan para versiones futuras:

- Cuotas pagadas y parcialmente pagadas.
- Reapertura de obligaciones.
- Compensaciones, notas de crédito o saldo a favor.
- Bonificación de indexación, crédito financiero, ajuste compensatorio o modificación física para tratar diferencias negativas.
- Reversión completa implementada.
- Rectificación posterior con recibos emitidos.
- Ajuste sobre saldo aplicado.
- Reimputación automática.
- Modificación de mora ya calculada.
- Reindexación con refinanciaciones activas.
- Aplicación automática masiva sin confirmación/configuración.
- Cambios en importadores reales, frontend o contratos API implementados.

## 20. Roadmap posterior

1. **SQL base de corridas**
   - Objetivo: crear cabecera/detalle, estados, constraints e índices.
   - Dependencias: este diseño.
   - Alcance: DDL, versionado, FK, unicidad/idempotencia.
   - Fuera de alcance: endpoints y aplicación.
   - Resultado: soporte persistente auditable.

2. **Preview de indexación**
   - Objetivo: calcular elegibilidad/importes/hash sin modificar obligaciones.
   - Dependencias: SQL si se persiste; calculadora pura.
   - Alcance: servicio financiero y contrato conceptual implementado.
   - Fuera de alcance: command de aplicación.
   - Resultado: preview reproducible.

3. **Aplicación CORE-EF**
   - Objetivo: command write atómico para aplicar corridas.
   - Dependencias: SQL y preview.
   - Alcance: headers, idempotencia, locks, versiones, outbox, tests.
   - Fuera de alcance: pagadas/parciales.
   - Resultado: obligaciones elegibles indexadas con trazabilidad.

4. **Procesamiento por publicación de índice**
   - Objetivo: detectar impactos y preparar corridas por lote.
   - Dependencias: SQL/preview.
   - Alcance: job o evento, propuestas, reportes.
   - Fuera de alcance: aplicación automática irrestricta.
   - Resultado: publicación desacoplada de aplicación.

5. **Integración con alta histórica**
   - Objetivo: usar componente financiero al registrar ventas históricas.
   - Dependencias: preview/cálculo financiero.
   - Alcance: validaciones y generación directa correcta.
   - Fuera de alcance: importación masiva.
   - Resultado: venta histórica manual sin cuotas desactualizadas.

6. **Integración con importador**
   - Objetivo: preview/confirmación por fila con indexación.
   - Dependencias: alta histórica y preview.
   - Alcance: lote, filas, idempotencia, reporte.
   - Fuera de alcance: UI avanzada no acordada.
   - Resultado: importaciones históricas seguras.

7. **Frontend**
   - Objetivo: visualizar preview, corridas, exclusiones y estados.
   - Dependencias: API implementada.
   - Alcance: pantallas y mensajes.
   - Fuera de alcance: reglas financieras.
   - Resultado: operación controlada por usuario.

8. **Reversión y corrección avanzada**
   - Objetivo: soportar pagadas/parciales, recibos, compensaciones y reversión.
   - Dependencias: aplicación estable y auditoría de corridas.
   - Alcance: modelos correctivos, notas/compensaciones, reimputación si se decide.
   - Fuera de alcance: V2 inicial.
   - Resultado: política completa para escenarios posteriores.

## 16. Implementación física SQL base (#340)

El issue `#340` materializa la infraestructura SQL inicial mediante `backend/database/patch_corridas_indexacion_cuotas_v2_20260710.sql`.

Tablas físicas creadas:

- `corrida_indexacion_financiera`: cabecera de corrida para una única combinación `plan_pago_venta + plan_pago_venta_bloque`.
- `corrida_indexacion_financiera_detalle`: detalle por `obligacion_financiera` analizada, incluyendo elegibles y excluidas.

Estados persistibles de cabecera implementados por `CHECK`:

- `BORRADOR`
- `PREVISUALIZADA`
- `PENDIENTE_APLICACION`
- `APLICADA`
- `FALLIDA`
- `ANULADA`
- `REEMPLAZADA`

No se persisten `APLICANDO`, `APLICADA_PARCIAL` ni `REVERSADA` en esta etapa.

Orígenes implementados por `CHECK`:

- `IMPORTACION_VENTA_HISTORICA`
- `ALTA_MANUAL_VENTA_HISTORICA`
- `PUBLICACION_INDICE`
- `REINDEXACION_MANUAL`
- `CORRECCION_INDICE`
- `REPROCESO_CONTROLADO`

Elegibilidad de detalle implementada por `CHECK`:

- `ELEGIBLE`
- `EXCLUIDA`
- `BLOQUEANTE`
- `RESERVADA_FUTURA`

Columnas principales de cabecera:

- CORE-EF: `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Alcance: `id_plan_pago_venta`, `id_plan_pago_venta_bloque`, `id_plan_pago_venta_bloque_indexacion`, `id_generacion_cronograma_financiero`.
- Índice: `id_indice_financiero`, `id_indice_financiero_valor_base`, `id_indice_financiero_valor_aplicado`, `periodo_base`, `periodo_aplicado`, `fecha_corte`, `fecha_calculo`, `fecha_publicacion_indice`.
- Idempotencia/auditoría: `op_id`, `hash_corrida`, `payload_hash`, snapshots JSONB, usuario, sucursal, referencias de lote/importación/job, motivo, observaciones y error controlado.
- Totales: cantidades analizadas/elegibles/excluidas/aplicadas e importes, ajustes y saldos anteriores/nuevos.
- Reemplazo: `id_corrida_anterior`, `id_corrida_reemplazante` con FKs autorreferenciales y `CHECK` anti-autorreferencia simple.

Columnas principales de detalle:

- CORE-EF equivalente a cabecera.
- Relaciones: `id_corrida_indexacion_financiera`, `id_obligacion_financiera`, componentes opcionales de capital/ajuste e `id_obligacion_financiera_indexacion`.
- Versionado: `version_esperada`, `version_resultante`.
- Cálculo: `capital_base`, valores de índice, coeficiente, ajuste anterior/nuevo, diferencia neta, importes y saldos anteriores/nuevos.
- Elegibilidad y auditoría controlada: estado, motivo, código de error, detalle, advertencias JSONB y snapshots antes/después.

Constraints e integridad relevantes:

- FKs `ON DELETE RESTRICT` hacia plan, bloque, configuración de indexación, generación de cronograma, índice, valores de índice, obligación, composiciones y trazabilidad de indexación.
- FKs compuestas para validar que el bloque pertenece al plan, que la configuración pertenece al bloque, que la generación opcional pertenece al plan y que los valores base/aplicado pertenecen al índice informado.
- Unicidad de detalle por `(id_corrida_indexacion_financiera, id_obligacion_financiera)`.
- Checks de cantidades/importes no negativos, versiones positivas, fechas coherentes, `fecha_aplicacion` solo en `APLICADA`, errores solo en `FALLIDA` y motivo para excluidas.

Índices principales:

- CORE-EF por UID, versión, timestamps y op_ids.
- Cabecera por plan, bloque, plan+bloque, índice, valor aplicado, estado, origen, fecha de corte, hash, corrida anterior/reemplazante.
- Parciales para pendientes de aplicación y corridas activas.
- Detalle por obligación, corrida+obligación, elegibilidad, código de error y parcial de elegibles.

Decisión de idempotencia física:

- La unicidad funcional activa usa `(id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero, id_indice_financiero_valor_aplicado, fecha_corte, origen_corrida, hash_corrida)`.
- La restricción parcial excluye `deleted_at IS NOT NULL`, `ANULADA` y `REEMPLAZADA` para permitir corridas correctivas, reemplazantes o reprocesos controlados con otro origen, período/valor aplicado, fecha de corte o hash.
- `payload_hash` queda persistido como soporte de diagnóstico/idempotencia de API futura, sin formar parte de la clave única para no duplicar el hash funcional cerrado de la corrida.

Desviaciones respecto del diseño conceptual:

- Se usa `periodo_base` / `periodo_aplicado` en lugar de columnas separadas de valor base/aplicado en cabecera porque los valores normalizados quedan referenciados por `indice_financiero_valor` y el detalle conserva los valores numéricos auditables usados en cada obligación.
- `id_generacion_cronograma_financiero` queda opcional y validado contra el plan cuando se informe, porque el esquema real permite la relación por `id_plan_pago_venta` pero no todos los orígenes de corrida nacen necesariamente desde una generación nueva.

### Ajustes de integridad posteriores a revisión del PR #350

La revisión del PR `#350` reforzó la implementación física sin cambiar el alcance funcional cerrado:

- Se agregó la clave candidata `uq_ifv_id_indice_pair` en `indice_financiero_valor (id_indice_financiero_valor, id_indice_financiero)` para respaldar las FKs compuestas de valor base y valor aplicado contra el índice informado por la corrida.
- Se agregó la clave candidata `uq_ppvbi_id_bloque_indice_pair` en `plan_pago_venta_bloque_indexacion (id_plan_pago_venta_bloque_indexacion, id_plan_pago_venta_bloque, id_indice_financiero)` y la FK compuesta `fk_cif_bloque_indexacion_mismo_bloque_indice`, de modo que una corrida no pueda usar una configuración comercial de indexación de otro bloque o de otro índice.
- Se agregó la clave candidata `uq_composicion_obligacion_id_obligacion_pair` en `composicion_obligacion (id_composicion_obligacion, id_obligacion_financiera)` y las FKs compuestas `fk_cifd_composicion_capital_obligacion` y `fk_cifd_composicion_ajuste_obligacion`, para impedir que el detalle apunte a composiciones de otra obligación.
- Se agregó la clave candidata `uq_ofi_id_obligacion_pair` en `obligacion_financiera_indexacion (id_obligacion_financiera_indexacion, id_obligacion_financiera)` y la FK compuesta `fk_cifd_obligacion_indexacion_obligacion`, para impedir trazabilidad cruzada entre obligaciones.
- Se incorporó el trigger estructural `trg_biu_cifd_validar_composiciones`, respaldado por `trg_cifd_validar_composiciones()`, que valida que `id_composicion_capital_venta` use el concepto `CAPITAL_VENTA` y que `id_composicion_ajuste_indexacion` use `AJUSTE_INDEXACION`, siempre dentro de la misma obligación del detalle.

Índices revisados:

- Se eliminaron los índices simples adicionales sobre `uid_global` de las dos tablas nuevas porque ya existe una constraint `UNIQUE` sobre cada UID.
- Se eliminó el índice parcial `idx_cifd_elegibles` porque la unicidad `(id_corrida_indexacion_financiera, id_obligacion_financiera)` ya cubre el acceso principal corrida+obligación; se mantienen índices por elegibilidad y por obligación para consultas futuras no redundantes.

Pruebas incorporadas/reforzadas:

- Aplicación idempotente del patch.
- Inserción válida de cabecera y detalle con defaults CORE-EF.
- Rechazo de bloque de otro plan, configuración con otro índice, generación de otro plan y valores de índice ajenos.
- Rechazo de composiciones cruzadas o con concepto incorrecto.
- Rechazo de trazabilidad de indexación perteneciente a otra obligación.
- Estados, orígenes, idempotencia activa, corrida correctiva, detalle duplicado, importes/versiones inválidas, exclusión sin motivo y reemplazos.

Se mantiene la decisión de que `diferencia_neta` pueda ser negativa como diferencia matemática/auditable, mientras `ajuste_nuevo`, importes y saldos siguen restringidos a valores no negativos.

### Alineación de nombres físicos de `concepto_financiero`

La validación estructural de composiciones queda alineada con los nombres físicos usados por el esquema de ejecución de tests para `concepto_financiero`: `codigo_concepto`, `nombre_concepto`, `tipo_concepto` y `estado_concepto`. El trigger `trg_cifd_validar_composiciones()` valida contra `cf.codigo_concepto` para `CAPITAL_VENTA` y `AJUSTE_INDEXACION`, manteniendo la misma semántica sin calcular ni modificar composiciones u obligaciones.
