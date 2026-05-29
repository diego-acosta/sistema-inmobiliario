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

La strategy futura debe distinguir explicitamente si esta operando sobre un plan indexado nuevo/prospectivo o sobre una carga historica/backfill de un plan antiguo. Esta distincion evita exigir valores futuros no publicados en planes nuevos, pero permite materializar cuotas antiguas cuando los valores historicos del indice ya existen o fueron cargados previamente.

### F.1 Plan indexado nuevo / prospectivo

Definicion: plan creado hoy para cuotas futuras o aun no determinables por falta de publicacion del indice.

Reglas:

1. Las cuotas futuras nacen como `PROYECTADAS`.
2. No se inventan valores de indice no publicados.
3. La emision/liquidacion definitiva ocurre cuando el indice aplicable este publicado/cargado.
4. Si falta el indice aplicable para una cuota futura, la cuota permanece `PROYECTADA` o pendiente de emision/liquidacion definitiva.
5. Preview puede mostrar calculos solo para cuotas con valores publicados disponibles; para cuotas sin valor aplicable debe informar condicion pendiente/error controlado segun contrato futuro, sin usar valores estimados inventados.
6. Generate prospectivo no debe exigir valores futuros no publicados como condicion para crear la estructura del plan; si la implementacion decide que generate solo materializa obligaciones definitivas, entonces debe bloquear la emision definitiva de las cuotas sin indice y mantenerlas pendientes/proyectadas.

Decision recomendada:

- Separar la creacion/proyeccion del plan de la emision/liquidacion definitiva de cada cuota indexada.
- No cambiar `CAPITAL_VENTA`: la cuota futura conserva el capital base prorrateado y solo suma `AJUSTE_INDEXACION` cuando exista valor aplicado real.

### F.2 Carga historica / backfill de plan antiguo

Definicion: carga controlada de planes indexados antiguos ya existentes fuera del sistema, con cuotas correspondientes a periodos pasados o ya determinables.

Reglas:

1. Se permite cargar planes indexados antiguos.
2. Si los valores historicos del indice ya existen en `indice_financiero_valor` o se cargan previamente, las cuotas pueden emitirse/materializarse de una vez.
3. Las cuotas vencidas o ya determinables pueden quedar `EMITIDAS` o materializadas segun el estado funcional definido para el flujo de importacion, siempre que se cuente con:
   - `valor_base_indice`;
   - `valor_aplicado_indice` por cuota/periodo;
   - `fecha_valor` o periodo aplicado;
   - `id_indice_financiero_valor` cuando corresponda;
   - coeficiente calculado;
   - composicion `CAPITAL_VENTA` + `AJUSTE_INDEXACION`.
4. No se deben inventar valores historicos: si faltan, deben cargarse primero en `indice_financiero_valor` o devolverse error controlado.
5. La carga historica debe congelar los valores aplicados usados para cada cuota materializada.

Decision recomendada:

- Tratar la carga historica como **futuro command/import controlado** si requiere reglas propias de estado inicial, validacion masiva, auditoria de origen o permisos especiales.
- Si se reutiliza generate, el request/command debe declarar explicitamente `modo_operacion` o ampliar `tipo_generacion_indexada` para distinguir al menos:
  - `PROSPECTIVO` / plan nuevo;
  - `HISTORICO_BACKFILL` / carga historica.
- No reutilizar silenciosamente el mismo comportamiento de generate para ambos casos, porque la exigencia de valores publicados y el estado inicial de las cuotas no son equivalentes.

---

## G) Comportamiento esperado de Preview

Clasificacion CORE-EF futura: `PREVIEW_READLIKE`.

Preview futuro debe:

1. Validar configuracion de `INDEXACION` sin persistir efectos.
2. Consultar valores publicados disponibles del indice para las fechas objetivo cuando el modo y la fecha lo requieran.
3. Calcular, para cuotas con valor aplicable disponible:
   - `coeficiente_indexacion`;
   - `capital_indexado`;
   - `ajuste_indexacion`;
   - `total_con_indexacion`.
4. Devolver campos de indexacion del bloque.
5. Devolver `total_con_indexacion` a nivel bloque y plan cuando todos los valores requeridos para ese total esten disponibles; si hay cuotas prospectivas sin indice, debe explicitar importes pendientes/no determinables.
6. Idealmente devolver detalle por cuota:
   - `fecha_vencimiento`;
   - `id_indice_financiero_valor` cuando exista valor aplicado;
   - `fecha_valor` publicada usada;
   - `valor_aplicado_indice`;
   - `coeficiente_indexacion`;
   - `capital_cuota`;
   - `ajuste_indexacion_cuota`;
   - `importe_cuota`;
   - estado esperado de determinacion (`PROYECTADA`, pendiente de indice, o determinable/materializable).
7. En carga historica, si falta un valor historico requerido, devolver error controlado (`INDICE_SIN_VALOR_PARA_FECHA`), no usar cero, no usar uno, no proyectar y no inventar valor.
8. En plan nuevo/prospectivo, si falta un valor futuro no publicado, no inventar valor: dejar la cuota como proyectada/pendiente de emision definitiva o devolver condicion controlada segun contrato futuro.

Preview no debe:

- persistir `obligacion_financiera_indexacion`;
- generar obligaciones reales;
- modificar `CAPITAL_VENTA`;
- usar pagos, caja, recibos ni saldos vivos.

---

## H) Comportamiento esperado de Generate futuro

Clasificacion CORE-EF futura: `COMMAND_WRITE_NEGOCIO`.

Generate futuro debe:

1. Dejar de devolver `INDEXACION_GENERATE_NO_IMPLEMENTADO` solo cuando exista strategy implementada y cubierta por tests para el modo operativo soportado.
2. Validar que el indice existe y esta activo.
3. Distinguir explicitamente el modo operativo:
   - plan indexado nuevo/prospectivo;
   - carga historica/backfill de plan antiguo.
4. Para plan prospectivo:
   - no exigir valores futuros no publicados;
   - crear cuotas `PROYECTADAS` o pendientes de emision/liquidacion cuando el indice aplicable todavia no exista;
   - emitir/materializar definitivamente solo las cuotas cuyo valor aplicable ya este publicado/cargado, si el flujo lo permite;
   - no generar `AJUSTE_INDEXACION` definitivo para cuotas sin valor aplicado real.
5. Para carga historica/backfill:
   - exigir todos los valores historicos aplicables a las cuotas que se pretenden emitir/materializar;
   - permitir materializar de una vez cuotas vencidas o ya determinables si existe `indice_financiero_valor` para cada fecha/periodo requerido;
   - devolver error controlado si falta algun valor historico requerido.
6. Validar configuracion `INDEXACION` contra lo persistido o contra el payload idempotente.
7. Congelar los valores aplicados reales en la misma transaccion que genera/emite/materializa obligaciones.
8. Generar obligaciones reales por cuota con `importe_total = CAPITAL_VENTA + AJUSTE_INDEXACION` cuando la cuota este determinada/materializada.
9. Generar composiciones para cuotas determinadas/materializadas:
   - `CAPITAL_VENTA` por el capital base prorrateado;
   - `AJUSTE_INDEXACION` por la diferencia indexada prorrateada.
10. Persistir o reutilizar `plan_pago_venta_bloque_indexacion`.
11. Persistir `obligacion_financiera_indexacion` por obligacion/cuota emitida o materializada, con:
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
   - `tipo_generacion_indexada` o `modo_operacion`.
12. Mantener idempotencia del generate/import: reintentos deben devolver/reutilizar el mismo resultado compatible, no duplicar obligaciones ni cambiar valores aplicados ya congelados.
13. Ejecutar todo en una frontera transaccional unica: plan, bloques, configuracion indexada, obligaciones, composiciones y trazabilidad de indexacion.

Generate no debe:

- persistir parcialmente si falla una cuota;
- recalcular con valores publicados nuevos si ya existe generacion compatible congelada;
- combinar `INDEXACION` con `INTERES_DIRECTO` en el mismo bloque;
- crear pagos, caja, recibos, documental real ni administrativo nuevo;
- inventar valores de indice futuros ni historicos.

Si la carga historica no se resuelve con generate, debe documentarse y nacer como command/import separado con decision CORE-EF propia antes de implementarse.

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

Pero no alcanza para explicar generate/import si cada cuota usa su propia `fecha_vencimiento` o periodo aplicado, porque puede haber varios `valor_aplicado_indice` dentro del mismo bloque.

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

Usar `obligacion_financiera_indexacion` como detalle obligatorio por obligacion/cuota emitida o materializada.

Reglas:

- `plan_pago_venta_bloque_indexacion` guarda la configuracion base del bloque.
- `obligacion_financiera_indexacion` guarda el valor aplicado real por cuota cuando la cuota se emite/materializa.
- En plan prospectivo, `obligacion_financiera_indexacion` se crea cuando exista valor aplicado real y la cuota quede emitida/materializada; no debe crearse con valores inventados.
- En carga historica, `obligacion_financiera_indexacion` puede crearse inmediatamente para cuotas con indice aplicado conocido y validado contra `indice_financiero_valor`.

Esto permite que la primera implementacion use fecha de vencimiento/periodo por cuota y mantenga:

- trazabilidad;
- idempotencia;
- explicabilidad del calculo;
- separacion entre importes (`obligacion_financiera` + `composicion_obligacion`) y parametros tecnicos del indice aplicado.

---

## J) Idempotencia

### J.1 Compatibilidad esperada

Un generate/import indexado es compatible cuando coinciden:

- `op_id` y contexto CORE-EF segun endpoint write existente o command/import futuro;
- modo operativo (`PROSPECTIVO` o `HISTORICO_BACKFILL`) declarado por `modo_operacion` o `tipo_generacion_indexada` equivalente;
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
- valores publicados aplicados congelados para cuotas emitidas/materializadas (`id_indice_financiero_valor`, `fecha_valor`, `valor_indice`).

### J.2 Mismo payload y mismos valores de indice aplicados

Resultado: **compatible**.

- Debe devolver/reutilizar plan, obligaciones, composiciones y trazabilidad ya generadas.
- No debe duplicar obligaciones.

### J.3 Mismo payload pero valores publicados cambiaron despues

Regla recomendada:

- Si no existia generacion/import previo, el flujo usa los valores publicados disponibles y requeridos al momento del primer intento exitoso y los congela para las cuotas emitidas/materializadas.
- Si ya existia generacion/import previo compatible, el flujo no recalcula con valores nuevos: debe devolver lo ya congelado.
- Si el mismo `op_id` intenta producir otro set de valores aplicados, debe tratarse como incompatibilidad/idempotencia conflictiva.

Motivo: la emision/materializacion indexada exige estabilidad del resultado generado y evita que un retry post-error cambie deuda por actualizacion posterior del indice.

### J.4 Carga historica / backfill

Reglas especificas:

- La idempotencia debe incluir los valores aplicados historicos congelados.
- Reintento con mismo payload + mismos valores aplicados = compatible.
- Reintento con valor aplicado distinto para la misma cuota/periodo = conflicto/incompatibilidad.
- Si falta un valor historico requerido, no debe persistirse parcialmente; se devuelve error controlado y se reintenta luego de cargar el valor faltante en `indice_financiero_valor`.

### J.5 Retry post-error

- Si fallo antes de persistir cualquier obligacion, puede reintentar y recalcular/leer los valores publicados disponibles en ese nuevo intento.
- Si fallo luego de persistencia parcial, eso no debe quedar confirmado: la transaccion debe hacer rollback completo.
- Si el primer intento confirmo transaccion, todo retry debe usar lo congelado, no recalcular.

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

Cuando se implemente la strategy o el import/backfill, agregar o ajustar tests sin inventar cobertura:

1. Preview `INDEXACION` con valor exacto de indice por fecha.
2. Preview `INDEXACION` con fallback al ultimo valor publicado anterior.
3. Preview `INDEXACION` sin valor disponible: error controlado `INDICE_SIN_VALOR_PARA_FECHA`.
4. Preview devuelve `total_con_indexacion` y detalle de valor aplicado usado.
5. Generate/import genera obligaciones reales con composiciones `CAPITAL_VENTA` + `AJUSTE_INDEXACION` para cuotas determinadas.
6. Suma de `CAPITAL_VENTA` = capital base del bloque.
7. Suma de `AJUSTE_INDEXACION` = ajuste total esperado segun politica de fecha/valor aplicado.
8. Ultima cuota absorbe redondeo de capital y ajuste por separado.
9. Generate/import persiste `obligacion_financiera_indexacion` por cuota emitida/materializada con valor aplicado congelado.
10. Idempotencia con mismo payload y mismos valores congelados.
11. Mismo payload con configuracion indexada incompatible devuelve `PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE`.
12. Cambio de `valor_base_indice` a ocho decimales se comporta igual que la compatibilidad actual del repository.
13. Carga historica con todos los indices disponibles genera obligaciones `EMITIDAS` o materializadas segun estado definido.
14. Carga historica con falta de indice historico devuelve error controlado y no persiste parcialmente.
15. Plan nuevo/prospectivo con falta de indice futuro deja cuotas `PROYECTADAS` o bloquea solo la emision definitiva segun contrato futuro.
16. No se inventan indices ni valores futuros/historicos.
17. Se persiste `obligacion_financiera_indexacion` por cada cuota historica emitida/materializada.
18. Reintento de carga historica con mismo payload + mismos valores aplicados es compatible.
19. Reintento de carga historica con valor aplicado distinto para la misma cuota/periodo devuelve conflicto/incompatibilidad.
20. No regresion de `INTERES_DIRECTO` en preview/generate.
21. No regresion de planes legacy / sin `metodo_liquidacion`.
22. Generate con `INDEXACION` deja de devolver `INDEXACION_GENERATE_NO_IMPLEMENTADO` solo en tests de la strategy implementada para el modo soportado.
23. CORE-EF de generate/import: headers faltantes/invalidos, rollback ante error, idempotencia y ausencia de persistencia parcial.

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

### M.3 Futuro generate / import historico

- Futuro generate prospectivo: `COMMAND_WRITE_NEGOCIO`.
- Futuro import/backfill historico, si nace separado: `COMMAND_WRITE_NEGOCIO` o `COMMAND_WRITE_TECNICO` segun decision de negocio/operacion, pero debe declararse explicitamente antes de implementarse.
- Debe respetar headers CORE-EF existentes del endpoint write o del command/import que se defina.
- Idempotencia: **APLICA** por `op_id + payload + modo_operacion + valores de indice congelados`.
- Para carga historica, la compatibilidad incluye los valores aplicados historicos por cuota/periodo.
- Outbox: **APLICA solo si el flujo de generate/import existente lo declara para la operacion sincronizable**; no inventar evento sin respaldo.
- Lock logico: **APLICA si el flujo de plan/venta ya bloquea generacion concurrente sobre la venta/plan**; no definir lock nuevo sin soporte.
- Versionado: usar `version_registro`/compatibilidad existente cuando modifique entidades versionadas.
- Rollback/transaccion: plan, bloques, configuracion indexada, obligaciones, composiciones y trazabilidad deben persistir en una unica transaccion atomica, tanto en prospectivo como en carga historica.

---

## N) Decision final recomendada

Para la primera implementacion de la strategy `INDEXACION`:

1. Usar formula `valor_aplicado_indice / valor_base_indice`.
2. Usar `CAPITAL_INICIAL_BLOQUE` como unica base de calculo.
3. Usar `fecha_vencimiento` de cada cuota como fecha objetivo del indice.
4. Usar fallback al ultimo valor `PUBLICADO <= fecha_vencimiento` cuando se requiera valor aplicado real.
5. Distinguir explicitamente plan nuevo/prospectivo vs carga historica/backfill mediante `modo_operacion` o `tipo_generacion_indexada` equivalente.
6. En plan prospectivo, no exigir ni inventar valores futuros no publicados; dejar cuotas `PROYECTADAS` o pendientes de emision/liquidacion definitiva.
7. En carga historica, permitir materializar cuotas antiguas si todos los valores historicos aplicables existen o fueron cargados previamente.
8. Devolver error controlado si falta un valor historico requerido o si se intenta emitir/materializar sin valor aplicado real.
9. Mantener `CAPITAL_VENTA` como capital original prorrateado.
10. Materializar la diferencia en `AJUSTE_INDEXACION`.
11. Persistir detalle por cuota emitida/materializada en `obligacion_financiera_indexacion`.
12. Congelar valores aplicados en generate/import y hacerlos parte de la compatibilidad idempotente.
13. Mantener `INDEXACION_GENERATE_NO_IMPLEMENTADO` hasta que la strategy, persistencia y tests esten completos para el modo operativo soportado.

Esta decision no invade pagos, caja, recibos, mora ni documental real; no modifica `INTERES_DIRECTO`; no cambia `metodo_plan_pago` global; no inventa indices futuros ni historicos; y mantiene `INDEXACION` como `metodo_liquidacion` exclusivo de bloque `TRAMO_CUOTAS` en `PLAN_POR_BLOQUES`.
