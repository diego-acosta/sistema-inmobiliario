# AUDITORIA / DISENO TECNICO
## Formula de `INDEXACION` en Plan Pago V2 por bloques

- Fecha: 2026-05-29
- Tipo: Documental / tecnico (sin cambios de codigo, SQL ni tests)
- Dominio: financiero (materializacion de obligaciones, composiciones, indices y trazabilidad) + comercial (estructura de plan de venta por bloques)
- Alcance evaluado: Plan Pago V2 `PLAN_POR_BLOQUES`, bloque `TRAMO_CUOTAS`, `metodo_liquidacion = INDEXACION`.
- Restriccion de este PR: **no implementa calculo**, **no modifica SQL**, **no modifica tests**, **no crea endpoint** y **no toca pagos/caja/recibos**.

---

## 0) Clasificacion arquitectonica

| Concepto | Clasificacion | Dominio / ownership | Decision |
| --- | --- | --- | --- |
| Plan de venta por bloques (`PLAN_POR_BLOQUES`) | nucleo del dominio | comercial | Define la estructura comercial del plan de venta y sus bloques. |
| Obligaciones, composiciones y conceptos financieros | nucleo del dominio | financiero | Materializan deuda, capital, ajuste e importes exigibles. |
| Indices financieros y valores publicados | nucleo del dominio financiero | financiero | Fuente financiera para calcular actualizaciones/indexaciones. |
| `plan_pago_venta_bloque_indexacion` | soporte transversal de trazabilidad/configuracion | comercial + financiero, sin mover ownership | Vincula el bloque comercial con parametros financieros de indexacion. |
| `obligacion_financiera_indexacion` | soporte transversal de trazabilidad tecnica | financiero | Congela el indice aplicado por obligacion, sin duplicar importes ni saldos. |
| `AJUSTE_INDEXACION` | nucleo financiero como concepto de composicion/ajuste | financiero | Debe representar la diferencia indexada sin reescribir `CAPITAL_VENTA`. |

La solucion futura no debe redefinir `metodo_plan_pago` global, no debe mezclar dominios, no debe mover logica de pagos/caja/recibos y no debe combinar `INDEXACION` con `INTERES_DIRECTO` en un mismo bloque en esta primera etapa.

---

## A) Estado actual auditado

### A.1 Definido documentalmente

- `AUDITORIA-METODO-LIQUIDACION-INDEXACION-PLAN-PAGO-V2.md` define `INDEXACION` como `metodo_liquidacion` de bloque/tramo, no como `metodo_plan_pago` global.
- La misma auditoria recomienda no combinar `INTERES_DIRECTO` + `INDEXACION` dentro del mismo `TRAMO_CUOTAS` en primera etapa.
- Esa auditoria recomienda conservar `CAPITAL_VENTA` y agregar `AJUSTE_INDEXACION` como composicion separada.
- `AUDITORIA-SOPORTE-FISICO-INDICES-FINANCIEROS.md` define la necesidad de catalogo/historico de indices, query por fecha con fallback `<= fecha_objetivo`, preview deterministico y generate con congelamiento del valor aplicado.
- `SRV-FIN-004-gestion-de-indices-financieros.md` documenta la gestion de indices financieros como responsabilidad del dominio financiero.

Estado: **DEFINIDO DOCUMENTALMENTE** para el modelo conceptual, soporte de indices y direccion tecnica. La formula exacta de calculo y distribucion por cuota queda definida por este documento.

### A.2 Implementado en SQL

- Existe soporte fisico base para `indice_financiero` e `indice_financiero_valor`, con estados, valor positivo, unicidad por indice/fecha activa, FK del valor al indice y triggers CORE-EF.
- Existe soporte fisico para `plan_pago_venta_bloque_indexacion` con:
  - `id_plan_pago_venta_bloque`;
  - `id_indice_financiero`;
  - `fecha_base_indice`;
  - `valor_base_indice`;
  - `modo_indexacion` restringido a `POR_COEFICIENTE`;
  - `base_calculo_indexacion` restringido a `CAPITAL_INICIAL_BLOQUE`;
  - `tipo_generacion_indexada` restringido a `DEFINITIVA`;
  - `politica_valor_no_disponible` restringida a `ERROR_SI_NO_EXISTE`;
  - flags obligatorios `conserva_capital_original = TRUE` y `genera_ajuste_por_diferencia = TRUE`.
- Existe soporte fisico para `obligacion_financiera_indexacion`, con `id_obligacion_financiera`, `id_plan_pago_venta_bloque_indexacion`, `id_indice_financiero`, `id_indice_financiero_valor`, valores base/aplicado, fecha aplicada y coeficiente.
- El constraint de `plan_pago_venta_bloque.metodo_liquidacion` fue ampliado para permitir `INDEXACION`.

Estado: **IMPLEMENTADO EN SQL** para soporte fisico y trazabilidad. **NO IMPLEMENTADO EN SQL**: no hay cambios en este PR y no se agrega nueva estructura.

### A.3 Implementado en backend

- El command/input de Plan Pago V2 por bloques ya transporta campos de indexacion por bloque.
- El preview valida `INDEXACION` como metodo valido solo para `TRAMO_CUOTAS`, valida parametros minimos y normaliza las constantes soportadas (`POR_COEFICIENTE`, `CAPITAL_INICIAL_BLOQUE`, `DEFINITIVA`, `ERROR_SI_NO_EXISTE`).
- El preview actual **no calcula** `total_con_indexacion`, no busca valores publicados y no devuelve detalle de valor aplicado por cuota.
- `IndiceFinancieroRepository.get_valor_publicado_por_codigo_y_fecha(...)` consulta indice activo y valor publicado con fallback deterministico al ultimo `fecha_valor <= fecha_objetivo`.
- `PlanPagoVentaV2Repository` puede insertar/leer/compatibilizar `plan_pago_venta_bloque_indexacion`.
- `GeneratePlanPagoVentaV2PorBloquesService` bloquea cualquier generate con `INDEXACION` devolviendo `INDEXACION_GENERATE_NO_IMPLEMENTADO` antes de persistir obligaciones indexadas.
- El generate actual solo genera composiciones separadas para `INTERES_DIRECTO`; no genera `AJUSTE_INDEXACION` ni registros en `obligacion_financiera_indexacion`.

Estado: **IMPLEMENTADO EN BACKEND** para propagacion, validacion minima, query de indice por fecha, persistencia de configuracion y bloqueo seguro de generate. **NO IMPLEMENTADO EN BACKEND**: strategy real de calculo, preview con valores publicados, composiciones `AJUSTE_INDEXACION` y trazabilidad por obligacion.

### A.4 Cubierto por tests

- Hay tests de `IndiceFinancieroRepository` para:
  - valor exacto por fecha;
  - fallback al ultimo valor anterior;
  - `None` cuando solo hay valores futuros;
  - ignorar estados no computables y entidades soft-deleted/no activas.
- Hay tests de preview de Plan Pago V2 por bloques para aceptar y normalizar `INDEXACION`, y para rechazar configuraciones invalidas.
- Hay tests unificados que verifican que generate con `INDEXACION` devuelve `INDEXACION_GENERATE_NO_IMPLEMENTADO`.
- Hay tests de repository para persistir configuracion de `plan_pago_venta_bloque_indexacion` e incompatibilidad por indice, valor base o fecha base diferente.
- Hay tests de no regresion alrededor de `INTERES_DIRECTO` y de composicion `CAPITAL_VENTA` en flujos existentes.

Estado: **CUBIERTO POR TESTS** para soporte, validaciones y bloqueo. **NO CUBIERTO POR TESTS**: formula real de indexacion, distribucion de ajuste por cuota, redondeo separado capital/ajuste, generate con `AJUSTE_INDEXACION`, y trazabilidad `obligacion_financiera_indexacion` producida por la strategy.

### A.5 No implementado / no confirmado

- Strategy de liquidacion `INDEXACION` para preview/generate: **NO IMPLEMENTADO**.
- Calculo de `coeficiente_indexacion`, `capital_indexado`, `ajuste_indexacion` y `total_con_indexacion`: **NO IMPLEMENTADO**.
- Respuesta de preview con `total_con_indexacion` y valor aplicado usado por cuota/bloque: **NO IMPLEMENTADO**.
- Generate real de obligaciones indexadas con composiciones `CAPITAL_VENTA` + `AJUSTE_INDEXACION`: **NO IMPLEMENTADO**.
- Persistencia generada por la strategy en `obligacion_financiera_indexacion`: **NO IMPLEMENTADO**.
- Politica de actualizacion posterior de valores de indice ya publicados y efectos sobre planes generados: **NO CONFIRMADO**; fuera de alcance de esta primera implementation strategy.

---

## B) Formula recomendada para primera etapa

### B.1 Formula base

Para `metodo_liquidacion = INDEXACION`, `modo_indexacion = POR_COEFICIENTE`:

```text
coeficiente_indexacion = valor_aplicado_indice / valor_base_indice

capital_indexado = capital_base * coeficiente_indexacion

ajuste_indexacion = capital_indexado - capital_base

total_con_indexacion = capital_base + ajuste_indexacion
```

Definiciones obligatorias:

- `capital_base = importe_total_bloque`.
- `valor_base_indice = valor_base_indice` guardado en `plan_pago_venta_bloque_indexacion`.
- `valor_aplicado_indice = valor publicado` obtenido por fecha de aplicacion definida para la cuota/bloque.
- `coeficiente_indexacion` debe ser positivo porque `valor_base_indice > 0` y los valores publicados computables deben tener `valor_indice > 0`.
- No se reescribe `CAPITAL_VENTA`.
- La diferencia debe materializarse como composicion separada `AJUSTE_INDEXACION`.
- Si `valor_aplicado_indice < valor_base_indice`, el resultado matematico produce ajuste negativo. Para primera etapa queda **NO CONFIRMADO** si se permite ajuste negativo; recomendacion segura: validar con negocio antes de generate definitivo y, mientras no este decidido, devolver `INDEXACION_CONFIG_INVALIDA` o error funcional especifico si el ajuste negativo no es aceptado.

### B.2 Redondeo de formula

- Los valores de indice se comparan/guardan a escala de ocho decimales cuando aplique compatibilidad de configuracion.
- Los importes de obligaciones/composiciones deben terminar en dos decimales.
- La division y multiplicacion deben calcularse con `Decimal`, no con flotantes.
- El redondeo de importes debe usar `ROUND_HALF_UP` y/o la regla vigente `ULTIMA_CUOTA` ya usada por Plan Pago V2.
- El coeficiente puede persistirse con escala tecnica de ocho decimales, alineado al soporte SQL actual.

---

## C) Base de calculo

Decision para primera implementacion:

```text
base_calculo_indexacion = CAPITAL_INICIAL_BLOQUE
```

Reglas:

- Usar `importe_total_bloque` como capital inicial del bloque.
- No usar saldo decreciente.
- No usar saldo vivo.
- No usar la cuota base como fuente principal, excepto como prorrateo derivado posterior.
- No mezclar con `INTERES_DIRECTO` en esta etapa.
- No calcular indexacion sobre intereses ni sobre otros ajustes.

Justificacion:

- Coincide con el constraint fisico ya existente para `base_calculo_indexacion`.
- Reduce ambiguedad operativa y evita recalculos sobre pagos, mora, caja o recibos.
- Preserva la semantica de `CAPITAL_VENTA` como capital original y permite explicar la actualizacion mediante `AJUSTE_INDEXACION`.

---

## D) Distribucion por cuota

### D.1 Regla general con un valor aplicado por cuota

Para cada cuota `n` del bloque:

```text
capital_total = importe_total_bloque
valor_aplicado_n = valor publicado usable para fecha_vencimiento_n
coeficiente_n = valor_aplicado_n / valor_base_indice
ajuste_total_n = capital_total * (coeficiente_n - 1)
capital_por_cuota_base = capital_total / cantidad_cuotas
ajuste_por_cuota_n = ajuste_total_n / cantidad_cuotas
importe_cuota_n = capital_por_cuota_n + ajuste_por_cuota_n
```

Interpretacion:

- La indexacion de cada cuota se calcula sobre el capital inicial del bloque y luego se prorratea por cantidad de cuotas.
- Esto no usa saldo vivo ni saldo decreciente: todas las cuotas parten de la misma base de capital del bloque, pero cada una puede tener distinto `valor_aplicado_indice` por su fecha de vencimiento.
- La suma de `CAPITAL_VENTA` de todas las cuotas debe ser exactamente `capital_total`.
- La suma de `AJUSTE_INDEXACION` de todas las cuotas debe explicar la suma de ajustes calculados por cuota.

### D.2 Variante si se decide valor unico por bloque

Si por restriccion de primera implementacion se decide congelar un unico valor aplicado por bloque:

```text
capital_total = importe_total_bloque
ajuste_total = capital_total * (valor_aplicado / valor_base - 1)
capital_por_cuota = capital_total / cantidad_cuotas
ajuste_por_cuota = ajuste_total / cantidad_cuotas
importe_cuota = capital_por_cuota + ajuste_por_cuota
```

Esta variante es mas simple, pero menos fiel si las cuotas tienen vencimientos mensuales y el indice cambia por periodo.

### D.3 Redondeo y ultima cuota

Decision recomendada:

1. Calcular capital y ajuste como componentes separados.
2. Redondear cada componente monetario a dos decimales con `ROUND_HALF_UP`.
3. Aplicar `ULTIMA_CUOTA` absorbiendo diferencias **por separado**:
   - ultima cuota absorbe diferencia de `CAPITAL_VENTA`;
   - ultima cuota absorbe diferencia de `AJUSTE_INDEXACION`.
4. Garantias esperadas:
   - `sum(CAPITAL_VENTA) = capital_total`;
   - `sum(AJUSTE_INDEXACION) = ajuste_total` cuando el bloque usa valor unico;
   - con valor aplicado por cuota, `sum(AJUSTE_INDEXACION) = sum(ajuste_por_cuota_n redondeado con ajuste de ultima cuota por politica definida)`;
   - `sum(obligaciones) = sum(CAPITAL_VENTA) + sum(AJUSTE_INDEXACION)`.

Para evitar ambiguedad con valor aplicado distinto por cuota, la implementacion debe definir la unidad de cierre del redondeo:

- **Recomendado:** cerrar `CAPITAL_VENTA` a nivel bloque y cerrar `AJUSTE_INDEXACION` como suma de importes de ajuste por cuota. Cada cuota conserva su propio valor aplicado trazado.
- No se debe usar una cuota total redondeada para inferir luego capital/ajuste, porque podria romper la conciliacion de composiciones.

---

## E) Fecha de aplicacion del indice

### E.1 Opcion recomendada para primera implementacion

Recomendacion: **cada obligacion/cuota usa su propia `fecha_vencimiento` como `fecha_objetivo` de busqueda del indice**.

Regla:

1. Para cada cuota se calcula su `fecha_vencimiento` con la periodicidad vigente del bloque.
2. Se consulta el valor publicado del indice para esa fecha.
3. Si existe valor exacto para `fecha_valor = fecha_vencimiento`, se usa ese valor.
4. Si no existe exacto, se usa el ultimo valor `PUBLICADO` con `fecha_valor <= fecha_vencimiento`.
5. Si no hay valor utilizable, se devuelve error controlado y no se inventa valor.

Justificacion:

- Alinea la indexacion con el vencimiento real de cada obligacion.
- Reutiliza la politica ya implementada en `IndiceFinancieroRepository`.
- Permite trazabilidad por obligacion y evita que cuotas con vencimientos diferentes compartan artificialmente un valor desactualizado.
- Evita mezclar preview/generate con pagos o saldo vivo.

### E.2 Alternativa no recomendada como regla principal

Usar una unica fecha/valor aplicado por bloque simplifica la idempotencia y la persistencia, pero pierde precision cuando el bloque contiene multiples vencimientos. Solo deberia elegirse si se decide postergar la trazabilidad por obligacion, cosa que actualmente no es necesaria porque ya existe `obligacion_financiera_indexacion`.

---

## F) Modo operativo: plan nuevo vs carga historica

La strategy futura debe usar **un mismo flujo/servicio de generacion indexada** para Plan Pago V2 por bloques. La diferencia entre plan indexado nuevo/prospectivo, carga historica/backfill o plan mixto no debe resolverse creando servicios separados ni reglas divergentes, sino evaluando **cuota por cuota** si existe el valor de indice aplicable.

### F.1 Regla comun por cuota

Para cada cuota de un bloque `TRAMO_CUOTAS` con `metodo_liquidacion = INDEXACION`:

1. Buscar el indice aplicable segun la secuencia/periodo definido para la cuota.
2. Si existe valor publicado aplicable:
   - calcular `coeficiente_indexacion`;
   - calcular `AJUSTE_INDEXACION`;
   - emitir/materializar la obligacion o dejarla en estado emitible segun contrato final;
   - persistir composiciones `CAPITAL_VENTA` + `AJUSTE_INDEXACION`;
   - persistir `obligacion_financiera_indexacion` con valor aplicado real congelado.
3. Si no existe valor publicado aplicable:
   - no inventar valor;
   - dejar la obligacion como `PROYECTADA`;
   - no crear `AJUSTE_INDEXACION` definitivo;
   - no persistir valor aplicado inexistente;
   - no crear `obligacion_financiera_indexacion` definitiva para esa cuota.

### F.2 Plan indexado nuevo / prospectivo

Definicion: plan creado hoy para cuotas futuras o aun no determinables por falta de publicacion del indice.

Reglas:

1. Usa el mismo flujo/servicio de generacion indexada que cualquier otro plan indexado.
2. Normalmente faltaran indices futuros; esas cuotas quedaran `PROYECTADAS`.
3. No se inventan valores de indice no publicados.
4. La emision/liquidacion definitiva de cada cuota ocurre cuando el indice aplicable este publicado/cargado.
5. Si alguna cuota del plan nuevo ya tiene valor publicado aplicable, el mismo flujo puede dejarla emitida/materializada o emitible segun contrato final.

### F.3 Carga historica / backfill de plan antiguo

Definicion: carga controlada de planes indexados antiguos ya existentes fuera del sistema, con cuotas correspondientes a periodos pasados o ya determinables.

Reglas:

1. Usa el mismo flujo/servicio de generacion indexada que el plan prospectivo.
2. Normalmente los valores historicos del indice ya existiran en `indice_financiero_valor` o se cargaran previamente; esas cuotas podran emitirse/materializarse en el mismo flujo.
3. Las cuotas vencidas o ya determinables pueden quedar `EMITIDAS` o materializadas segun el estado funcional definido, siempre que se cuente con:
   - `valor_base_indice`;
   - `valor_aplicado_indice` por cuota/periodo;
   - `fecha_valor` o periodo aplicado;
   - `id_indice_financiero_valor` cuando corresponda;
   - coeficiente calculado;
   - composicion `CAPITAL_VENTA` + `AJUSTE_INDEXACION`.
4. No se deben inventar valores historicos: si faltan, esas cuotas quedan `PROYECTADAS` o pendientes segun contrato final hasta que el valor se cargue en `indice_financiero_valor`.
5. La carga historica debe congelar los valores aplicados usados para cada cuota emitida/materializada.

### F.4 Plan mixto

Un mismo plan puede contener cuotas con valor publicado aplicable y cuotas sin valor aplicable.

Reglas:

- Las cuotas con indice disponible pueden emitirse/materializarse en el mismo flujo.
- Las cuotas sin indice disponible quedan `PROYECTADAS`.
- La persistencia de `obligacion_financiera_indexacion` y `AJUSTE_INDEXACION` solo corresponde a cuotas con valor aplicado real.
- `modo_operacion` o `tipo_generacion_indexada` pueden servir para auditoria, control del flujo, reporting o permisos, pero no para duplicar servicios ni para crear reglas divergentes entre prospectivo e historico.

---

## G) Comportamiento esperado de Preview

Clasificacion CORE-EF futura: `PREVIEW_READLIKE`.

Preview futuro debe:

1. Validar configuracion de `INDEXACION` sin persistir efectos.
2. Evaluar cuota por cuota si existe valor publicado aplicable para la fecha/periodo objetivo.
3. Para cuotas con valor aplicable disponible, calcular:
   - `coeficiente_indexacion`;
   - `capital_indexado`;
   - `ajuste_indexacion`;
   - `total_con_indexacion`.
4. Para cuotas sin valor aplicable disponible:
   - no inventar valor;
   - marcarlas como `PROYECTADAS`/pendientes de determinacion segun contrato futuro;
   - no devolver `AJUSTE_INDEXACION` definitivo ni valor aplicado inexistente.
5. Devolver campos de indexacion del bloque.
6. Devolver totales diferenciando importes determinados de importes pendientes cuando existan cuotas sin indice.
7. Idealmente devolver detalle por cuota:
   - `fecha_vencimiento`;
   - `id_indice_financiero_valor` cuando exista valor aplicado;
   - `fecha_valor` publicada usada;
   - `valor_aplicado_indice`;
   - `coeficiente_indexacion`;
   - `capital_cuota`;
   - `ajuste_indexacion_cuota`;
   - `importe_cuota`;
   - estado esperado de determinacion (`EMITIBLE`/materializable o `PROYECTADA`).

Preview no debe:

- persistir `obligacion_financiera_indexacion`;
- generar obligaciones reales;
- modificar `CAPITAL_VENTA`;
- usar pagos, caja, recibos ni saldos vivos.

---

## H) Comportamiento esperado de Generate futuro

Clasificacion CORE-EF futura: `COMMAND_WRITE_NEGOCIO`.

Generate indexado futuro debe:

1. Ser un **mismo flujo/servicio** para plan nuevo, carga historica y planes mixtos.
2. Dejar de devolver `INDEXACION_GENERATE_NO_IMPLEMENTADO` solo cuando exista strategy implementada y cubierta por tests para la evaluacion cuota por cuota.
3. Validar que el indice existe y esta activo.
4. Procesar cada cuota del bloque `TRAMO_CUOTAS` con `INDEXACION` de forma independiente respecto de la disponibilidad del indice.
5. No exigir que existan todos los indices futuros para generar el plan.
6. Para cada cuota con valor publicado aplicable:
   - calcular `coeficiente_indexacion`;
   - calcular `AJUSTE_INDEXACION`;
   - emitir/materializar la obligacion o dejarla en estado emitible segun contrato final;
   - generar composiciones `CAPITAL_VENTA` + `AJUSTE_INDEXACION`;
   - persistir `obligacion_financiera_indexacion` con valor aplicado real congelado.
7. Para cada cuota sin valor publicado aplicable:
   - dejar la obligacion como `PROYECTADA`;
   - no generar `AJUSTE_INDEXACION` definitivo;
   - no persistir `obligacion_financiera_indexacion` definitiva;
   - no persistir valor aplicado inexistente.
8. Validar configuracion `INDEXACION` contra lo persistido o contra el payload idempotente.
9. Persistir o reutilizar `plan_pago_venta_bloque_indexacion` como configuracion base del bloque.
10. Mantener rollback transaccional de todo lo que el flujo intente persistir: plan, bloques, obligaciones, composiciones y trazabilidad deben confirmarse o revertirse de forma atomica.

Para cuotas con valor aplicado real, `obligacion_financiera_indexacion` debe guardar:

- `id_obligacion_financiera`;
- `id_plan_pago_venta_bloque_indexacion`;
- `id_indice_financiero`;
- `id_indice_financiero_valor`;
- `fecha_base_indice`;
- `valor_base_indice`;
- `fecha_aplicacion_indice`;
- `fecha_valor` o periodo aplicado cuando el modelo lo exponga;
- `valor_aplicado_indice`;
- `coeficiente_indexacion`;
- `modo_indexacion`;
- `base_calculo_indexacion`;
- `tipo_generacion_indexada` o `modo_operacion` si se incorpora con finalidad de auditoria/control.

Generate no debe:

- persistir parcialmente si falla una cuota que el flujo intenta guardar;
- recalcular/cambiar valores publicados congelados en cuotas ya emitidas/materializadas;
- combinar `INDEXACION` con `INTERES_DIRECTO` en el mismo bloque;
- crear pagos, caja, recibos, documental real ni administrativo nuevo;
- inventar valores de indice futuros ni historicos;
- duplicar servicios entre plan prospectivo y carga historica/backfill.

---

## I) Persistencia de valor aplicado

### I.1 Analisis

`plan_pago_venta_bloque_indexacion` alcanza para guardar la configuracion base del bloque:

- indice;
- fecha base;
- valor base;
- modo;
- base de calculo;
- politica de no disponibilidad;
- flags de conservar capital y generar ajuste.

Pero no alcanza para explicar cuotas emitidas/materializadas si cada cuota usa su propia `fecha_vencimiento` o periodo aplicado, porque puede haber varios `valor_aplicado_indice` dentro del mismo bloque.

### I.2 Opciones evaluadas

1. Guardar valor aplicado en observaciones/detalle de `composicion_obligacion` si existiera campo apto.
   - Estado: **NO RECOMENDADO**.
   - Motivo: baja trazabilidad, dificil compatibilidad idempotente, semantica tecnica mezclada con texto libre.

2. Agregar o usar tabla de detalle de indexacion por obligacion.
   - Estado: **RECOMENDADO**.
   - Motivo: ya existe soporte fisico `obligacion_financiera_indexacion`, con FK a obligacion, bloque indexado, indice y valor publicado.
   - Permite congelar el valor aplicado por cuota y auditar el coeficiente sin duplicar importes.

3. Congelar una unica fecha/valor aplicado por bloque para evitar detalle por cuota.
   - Estado: **NO RECOMENDADO como primera opcion**.
   - Motivo: simplifica, pero sacrifica exactitud por vencimiento/periodo y desaprovecha la tabla de trazabilidad ya disponible.

### I.3 Decision recomendada

Usar `obligacion_financiera_indexacion` como detalle obligatorio **solo** para obligacion/cuota emitida o materializada con valor aplicado real.

Reglas:

- `plan_pago_venta_bloque_indexacion` guarda la configuracion base del bloque.
- `obligacion_financiera_indexacion` guarda el valor aplicado real por cuota cuando la cuota se emite/materializa.
- Las cuotas `PROYECTADAS` sin indice aplicable no deben tener `obligacion_financiera_indexacion` definitiva.
- Las cuotas historicas con indice aplicado conocido y validado contra `indice_financiero_valor` pueden crear `obligacion_financiera_indexacion` inmediatamente en el mismo flujo.
- Las cuotas de un plan nuevo que ya tengan valor publicado aplicable siguen la misma regla: si se emiten/materializan, persisten trazabilidad; si quedan proyectadas, no persisten valor aplicado inexistente.

Esto permite que la primera implementacion use fecha de vencimiento/periodo por cuota y mantenga:

- trazabilidad;
- idempotencia;
- explicabilidad del calculo;
- separacion entre importes (`obligacion_financiera` + `composicion_obligacion`) y parametros tecnicos del indice aplicado.

---

## J) Idempotencia

### J.1 Compatibilidad esperada

Un generate indexado es compatible cuando coinciden:

- `op_id` y contexto CORE-EF segun endpoint write existente;
- `id_venta`, `tipo_pago`, `monto_total_plan`, `moneda`;
- estructura de bloques y cuotas;
- `metodo_liquidacion = INDEXACION`;
- `id_indice_financiero`;
- `fecha_base_indice`;
- `valor_base_indice` normalizado a ocho decimales;
- `modo_indexacion`;
- `base_calculo_indexacion`;
- `tipo_generacion_indexada`;
- `politica_valor_no_disponible`;
- `conserva_capital_original = TRUE`;
- `genera_ajuste_por_diferencia = TRUE`;
- fechas objetivo/periodos por cuota;
- estado determinado por cuota (`emitida/materializada` o `PROYECTADA`);
- valores publicados aplicados congelados para cuotas emitidas/materializadas (`id_indice_financiero_valor`, `fecha_valor`, `valor_indice`).

`modo_operacion` o `tipo_generacion_indexada` pueden formar parte de auditoria/control si se incorporan, pero no deben cambiar la regla funcional comun ni justificar servicios separados.

### J.2 Mismo payload, mismos estados por cuota y mismos valores aplicados

Resultado: **compatible**.

- Debe devolver/reutilizar plan, obligaciones, composiciones y trazabilidad ya generadas.
- No debe duplicar obligaciones.
- Reintento con mismas cuotas emitidas/proyectadas y mismos valores congelados = compatible.

### J.3 Cambio de valor aplicado en cuota ya emitida/materializada

Regla recomendada:

- Reintento que intenta cambiar `valor_aplicado_indice`, `id_indice_financiero_valor`, `fecha_valor` o coeficiente de una cuota ya emitida/materializada debe devolver incompatibilidad/conflicto.
- El flujo no debe recalcular con valores nuevos una cuota cuyo valor ya quedo congelado.

### J.4 Cuota previamente proyectada que ahora tiene indice disponible

Decision pendiente antes de implementar:

- Definir si una cuota antes `PROYECTADA` puede emitirse/materializarse por un reintento del mismo generate cuando aparece el indice, o si debe existir un comando posterior de emision/liquidacion de cuotas indexadas pendientes.
- Hasta cerrar esta decision, no declarar idempotencia completa para la transicion `PROYECTADA -> emitida/materializada` en retries tardios.
- Cualquier alternativa debe preservar que no se inventan valores y que `obligacion_financiera_indexacion` se crea solo al congelar un valor real.

### J.5 Retry post-error

- Si fallo antes de persistir cualquier obligacion/composicion/trazabilidad, puede reintentar y reevaluar disponibilidad de indices.
- Si fallo luego de persistencia parcial, eso no debe quedar confirmado: la transaccion debe hacer rollback completo.
- Si el primer intento confirmo transaccion, todo retry debe respetar los estados por cuota y valores congelados ya persistidos.

---

## K) Errores funcionales esperados

Codigos sugeridos para la strategy futura:

| Codigo | Cuando aplica | Estado |
| --- | --- | --- |
| `INDICE_FINANCIERO_NO_ENCONTRADO` | El indice configurado no existe, esta inactivo, anulado, borrador o soft-deleted. | Futuro |
| `INDICE_SIN_VALOR_PARA_FECHA` | No hay valor `PUBLICADO` usable con `fecha_valor <= fecha_objetivo`. | Futuro |
| `INDEXACION_CONFIG_INVALIDA` | Parametros incompletos/incompatibles: valor base no positivo, modo no soportado, base no soportada, flags falsos, combinacion con interes directo, ajuste negativo no permitido si negocio lo define asi. | Futuro |
| `INDEXACION_GENERATE_NO_IMPLEMENTADO` | Bloqueo seguro actual de generate mientras no exista strategy. | Actual, temporal |
| `PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE` | Reintento o persistencia encuentra configuracion indexada existente incompatible. | Actual/futuro |

No se deben devolver errores de headers como `{"detail": "..."}` en endpoints write. Generate futuro debe preservar el `ErrorResponse` estandar y los helpers CORE-EF existentes del endpoint.

---

## L) Tests futuros minimos

Cuando se implemente la strategy de generacion indexada unica, agregar o ajustar tests sin inventar cobertura:

1. Preview `INDEXACION` con valor exacto de indice por fecha.
2. Preview `INDEXACION` con fallback al ultimo valor publicado anterior.
3. Preview `INDEXACION` sin valor disponible marca cuota pendiente/proyectada o devuelve condicion controlada segun contrato, sin inventar valor.
4. Preview devuelve `total_con_indexacion` y detalle de valor aplicado usado solo para cuotas con indice disponible.
5. Generate indexado genera obligaciones/composiciones `CAPITAL_VENTA` + `AJUSTE_INDEXACION` para cuotas con indice disponible.
6. Suma de `CAPITAL_VENTA` = capital base del bloque.
7. Suma de `AJUSTE_INDEXACION` = ajuste total esperado para cuotas determinadas segun politica de fecha/valor aplicado.
8. Ultima cuota absorbe redondeo de capital y ajuste por separado cuando corresponda a cuotas determinadas.
9. Generate indexado persiste `obligacion_financiera_indexacion` por cuota emitida/materializada con valor aplicado congelado.
10. Idempotencia con mismo payload, mismos estados por cuota y mismos valores congelados.
11. Mismo payload con configuracion indexada incompatible devuelve `PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE`.
12. Cambio de `valor_base_indice` a ocho decimales se comporta igual que la compatibilidad actual del repository.
13. Plan nuevo con algunas cuotas sin indice deja esas cuotas `PROYECTADAS`.
14. Carga historica con indices disponibles emite/materializa esas cuotas en el mismo flujo de generacion indexada.
15. Plan mixto emite/materializa cuotas con indice disponible y deja `PROYECTADAS` las restantes.
16. No se inventan indices ni valores futuros/historicos.
17. `obligacion_financiera_indexacion` solo existe para cuotas con indice aplicado real.
18. No hay servicios separados para plan nuevo vs carga historica/backfill.
19. Reintento con mismas cuotas emitidas/proyectadas y mismos valores aplicados es compatible.
20. Reintento que cambia valor aplicado de una cuota ya emitida/materializada devuelve conflicto/incompatibilidad.
21. Test pendiente cuando se cierre la decision `PROYECTADA -> emitida/materializada`: mismo generate reintentado vs comando posterior de emision/liquidacion.
22. No regresion de `INTERES_DIRECTO` en preview/generate.
23. No regresion de planes legacy / sin `metodo_liquidacion`.
24. Generate con `INDEXACION` deja de devolver `INDEXACION_GENERATE_NO_IMPLEMENTADO` solo en tests de la strategy implementada para evaluacion cuota por cuota.
25. CORE-EF de generate: headers faltantes/invalidos, rollback ante error, idempotencia y ausencia de persistencia parcial.

---

## M) Decision CORE-EF

### M.1 PR actual

- Naturaleza: **PR documental / tecnico**.
- Endpoint write nuevo o modificado: **NO APLICA**.
- Clasificacion CORE-EF del PR: **NO APLICA endpoint write**.
- Headers CORE-EF: **NO APLICA** porque no se modifica endpoint.
- Idempotencia: **NO APLICA** al PR documental.
- Outbox: **NO APLICA**.
- Lock logico: **NO APLICA**.
- Versionado: **NO APLICA**.
- Rollback/transaccion: **NO APLICA**.
- Tests obligatorios de endpoint write: **NO APLICA**; este PR no cambia comportamiento.

### M.2 Futuro preview

- Clasificacion: `PREVIEW_READLIKE`.
- Headers write CORE-EF: **NO APLICA** por ser read-like sin persistencia.
- Debe ser deterministico con valores publicados disponibles y devolver error controlado si falta valor.

### M.3 Futuro generate indexado unico

- Clasificacion: `COMMAND_WRITE_NEGOCIO`.
- Debe existir un mismo flujo/servicio de generacion indexada para plan nuevo, carga historica/backfill y planes mixtos.
- `modo_operacion` o `tipo_generacion_indexada`, si se incorporan, sirven para auditoria/control, no para duplicar servicios ni crear reglas divergentes.
- Debe respetar headers CORE-EF existentes del endpoint write.
- Idempotencia: **APLICA** por `op_id + payload + estados por cuota + valores de indice congelados`.
- Para cuotas emitidas/materializadas, la compatibilidad incluye los valores aplicados por cuota/periodo.
- Outbox: **APLICA solo si el flujo de generate existente lo declara para la operacion sincronizable**; no inventar evento sin respaldo.
- Lock logico: **APLICA si el flujo de plan/venta ya bloquea generacion concurrente sobre la venta/plan**; no definir lock nuevo sin soporte.
- Versionado: usar `version_registro`/compatibilidad existente cuando modifique entidades versionadas.
- Rollback/transaccion: plan, bloques, configuracion indexada, obligaciones, composiciones y trazabilidad que el flujo intente persistir deben confirmarse o revertirse de forma atomica.

---

## N) Decision final recomendada

Para la primera implementacion de la strategy `INDEXACION`:

1. Usar formula `valor_aplicado_indice / valor_base_indice`.
2. Usar `CAPITAL_INICIAL_BLOQUE` como unica base de calculo.
3. Usar `fecha_vencimiento` de cada cuota como fecha objetivo del indice.
4. Usar fallback al ultimo valor `PUBLICADO <= fecha_vencimiento` cuando se requiera valor aplicado real.
5. Implementar un mismo flujo/servicio de generacion indexada para plan nuevo, carga historica/backfill y plan mixto.
6. Evaluar cuota por cuota la disponibilidad del indice aplicable.
7. Emitir/materializar solo cuotas con valor publicado aplicable y congelar ese valor.
8. Dejar `PROYECTADAS` las cuotas sin valor publicado aplicable.
9. No crear `AJUSTE_INDEXACION` definitivo ni `obligacion_financiera_indexacion` para cuotas proyectadas sin indice.
10. Mantener `CAPITAL_VENTA` como capital original prorrateado.
11. Materializar la diferencia en `AJUSTE_INDEXACION` solo para cuotas con indice aplicado real.
12. Congelar valores aplicados en generate y hacerlos parte de la compatibilidad idempotente por cuota.
13. Cerrar antes de implementar si una cuota antes `PROYECTADA` puede emitirse por retry del mismo generate o requiere comando posterior de emision/liquidacion.
14. Mantener `INDEXACION_GENERATE_NO_IMPLEMENTADO` hasta que la strategy, persistencia y tests esten completos para evaluacion cuota por cuota.

Esta decision no invade pagos, caja, recibos, mora ni documental real; no modifica `INTERES_DIRECTO`; no cambia `metodo_plan_pago` global; no inventa indices futuros ni historicos; no duplica servicios por prospectivo/historico; y mantiene `INDEXACION` como `metodo_liquidacion` exclusivo de bloque `TRAMO_CUOTAS` en `PLAN_POR_BLOQUES`.
