# AUDITORIA / DISENO TECNICO
## Cuotas refuerzo internas al tramo en Plan Pago V2

- Fecha: 2026-06-02
- Tipo: Documental / tecnico (sin cambios de codigo, SQL ni tests)
- Dominio: comercial (definicion de plan de pago de venta) + financiero (materializacion de obligaciones y composiciones)
- Alcance evaluado: Plan Pago V2 `PLAN_POR_BLOQUES`, con foco en `TRAMO_CUOTAS` y soporte actual de `REFUERZO`.

---

## 0) Contexto y regla funcional objetivo

La definicion UX vigente fija que las cuotas refuerzo forman parte del total de cuotas del tramo. No son cuotas adicionales al tramo.

Regla funcional objetivo:

- Si el usuario define `cantidad_total_cuotas = 24` y `cantidad_refuerzos = 2`, el plan tiene **24 cuotas/obligaciones totales**:
  - 22 cuotas normales;
  - 2 cuotas refuerzo.
- No es `24 cuotas + 2 refuerzos`.
- La cuota refuerzo ocupa una posicion del tramo (`numero_cuota`) y usa el vencimiento de esa posicion.
- El usuario no debe reservar capital manualmente para refuerzos.
- La cuota refuerzo puede materializarse como obligacion separada con el mismo vencimiento de la cuota/mes asociado, pero representa una cuota dentro del total pactado.

Ejemplo objetivo:

```text
TRAMO_CUOTAS
  cantidad_total_cuotas = 24
  cuotas_refuerzo = [
    { numero_cuota = 6, unidades_refuerzo = 2, etiqueta = "Refuerzo cuota 6" },
    { numero_cuota = 18, unidades_refuerzo = 2, etiqueta = "Refuerzo cuota 18" }
  ]

Resultado esperado:
  cantidad_obligaciones_tramo = 24
  cantidad_cuotas_normales = 22
  cantidad_cuotas_refuerzo = 2
```

---

## 1) Clasificacion arquitectonica

### 1.1 Conceptos

- `Plan Pago V2 PLAN_POR_BLOQUES`: **nucleo del dominio comercial** para describir la forma comercial de pago de una venta.
- `TRAMO_CUOTAS`: **nucleo del dominio comercial** dentro del plan; define cantidad de posiciones pactadas, vencimientos y metodo de liquidacion del tramo.
- `cuota_refuerzo interna`: **nucleo del dominio comercial** como especializacion de una posicion del tramo, porque define como se pacta el cronograma comercial.
- `obligacion_financiera` resultante: **nucleo del dominio financiero**; materializa deuda/saldo exigible generada por el plan.
- `id_plan_pago_venta_bloque` y `clave_funcional_origen`: **soporte transversal/trazabilidad** entre el plan comercial y las obligaciones financieras.
- `tipo_bloque = REFUERZO` actual: **compatibilidad heredada / bloque libre vigente**, no debe confundirse con cuota refuerzo interna al tramo sin decision explicita.

### 1.2 Limites de dominio

- Comercial decide la estructura del plan, la cantidad total de cuotas y que posiciones son refuerzo.
- Financiero materializa obligaciones y composiciones sin redefinir la regla comercial de cantidad de cuotas.
- La consulta integral puede proyectar datos financieros generados, pero no debe recalcular la semantica comercial como fuente primaria.
- No corresponde dividir Plan Pago V2 por objeto vendido ni por comprador en este diseno.

---

## 2) Estado actual verificado

### 2.1 `tipo_bloque = REFUERZO` hoy

El soporte actual de `REFUERZO` funciona como **bloque de pago unico** dentro de `PLAN_POR_BLOQUES`:

1. La validacion acepta `REFUERZO` como `tipo_bloque` valido junto con `CONTADO`, `ANTICIPO`, `TRAMO_CUOTAS` y `SALDO`.
2. Al no ser `TRAMO_CUOTAS`, cae en la validacion de pago unico.
3. La validacion de pago unico exige `importe_total_bloque > 0`, precision monetaria de centavos y `fecha_vencimiento` informada.
4. En preview se genera una unica obligacion para ese bloque, con `tipo_item_cronograma = REFUERZO`, `item_numero = 1`, `fecha_vencimiento = bloque.fecha_vencimiento` e `importe_total = bloque.importe_total_bloque`.
5. En SQL, `plan_pago_venta_bloque.tipo_bloque` admite `REFUERZO` y el constraint de pago unico exige importe/fecha para `CONTADO|ANTICIPO|REFUERZO|SALDO`.
6. En SQL, `obligacion_financiera.tipo_item_cronograma` admite `REFUERZO`.

Conclusion: el `REFUERZO` actual es un hito/bloque libre con importe y fecha propios.

### 2.2 Evidencia de implementacion

- `PlanPagoVentaBloqueInput` no tiene campos para asociar refuerzos a una cuota del tramo (`numero_cuota_asociada`, `unidades_refuerzo`, lista de refuerzos o equivalente).
- `PlanPagoVentaBloqueV2Request` tampoco expone dichos campos en el contrato HTTP de preview/generate.
- `BuildPlanPagoVentaV2PorBloquesPreviewService` calcula cuotas de un `TRAMO_CUOTAS` usando `cantidad_cuotas`, y para bloques no tramo emite una sola obligacion con `fecha_vencimiento` propia.
- `GeneratePlanPagoVentaV2PorBloquesService` persiste `plan_pago_venta.cantidad_cuotas` como suma de `cantidad_cuotas` de bloques `TRAMO_CUOTAS`, sin contar bloques `REFUERZO` libres.
- `PlanPagoVentaV2Repository` persiste bloques y obligaciones con los campos actuales, sin columnas/relaciones para asociacion cuota-refuerzo interna.
- Los tests actuales validan un plan financiado con `REFUERZO` como bloque independiente: el cronograma contiene obligaciones de anticipo, cuotas, refuerzo y saldo, y el refuerzo aparece como obligacion adicional en la secuencia.

### 2.3 Respuesta a preguntas 1, 2 y 3

1. **Como funciona hoy `tipo_bloque = REFUERZO`:** como bloque de pago unico dentro del listado de bloques, con una obligacion resultante propia.
2. **Si el REFUERZO actual es bloque libre con importe y fecha:** si. Requiere `importe_total_bloque` y `fecha_vencimiento` propios.
3. **Si puede representar cuota refuerzo interna al tramo sin cambios:** no. Puede parecer similar en la salida porque usa `tipo_item_cronograma = REFUERZO`, pero no preserva la regla funcional de que el refuerzo reemplaza una posicion dentro de `cantidad_total_cuotas`. Hoy agrega una obligacion extra al cronograma si se combina con un tramo de cuotas.

---

## 3) Brecha funcional actual

### 3.1 Campos faltantes

Para soportar cuotas refuerzo internas al tramo faltan, como minimo:

#### En input/API de tramo

Una lista opcional en `TRAMO_CUOTAS`, por ejemplo:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "cantidad_total_cuotas": 24,
  "importe_total_bloque": 24000000.00,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "cuotas_refuerzo": [
    {
      "numero_cuota": 6,
      "unidades_refuerzo": 2,
      "etiqueta": "Refuerzo cuota 6"
    },
    {
      "numero_cuota": 18,
      "unidades_refuerzo": 2,
      "etiqueta": "Refuerzo cuota 18"
    }
  ]
}
```

Nombres equivalentes aceptables para diseno futuro:

- `cantidad_total_cuotas` o mantener `cantidad_cuotas` con semantica explicita de total de posiciones.
- `cuotas_refuerzo[].numero_cuota` o `numero_cuota_asociada`.
- `cuotas_refuerzo[].unidades_refuerzo` o `cantidad_unidades`.
- `cuotas_refuerzo[].etiqueta` opcional.

#### En preview/cronograma

- `tipo_item_cronograma = REFUERZO` para distinguir el item generado.
- `numero_cuota_asociada` o equivalente para trazabilidad funcional.
- `unidades_refuerzo` / `cantidad_unidades` si se requiere explicar el peso relativo de la cuota refuerzo.
- `fecha_vencimiento` derivada de `fecha_primer_vencimiento + (numero_cuota - 1)` periodos.
- Orden deterministico del cronograma por fecha y por posicion del tramo.

#### En persistencia

Hoy no hay soporte fisico confirmado para guardar lista de cuotas refuerzo por tramo ni para guardar `numero_cuota_asociada` en la obligacion. Si se exige trazabilidad persistida robusta, hace falta SQL.

Opciones futuras:

1. Tabla hija de bloque, recomendada para modelo normalizado:
   - `plan_pago_venta_bloque_refuerzo`
   - `id_plan_pago_venta_bloque`
   - `numero_cuota`
   - `unidades_refuerzo` / `cantidad_unidades`
   - `etiqueta`
   - metadatos CORE-EF/versionado si aplica al write.
2. Columnas adicionales en `obligacion_financiera` para trazabilidad de posicion (`numero_cuota_asociada`, `tipo_item_cronograma` ya existe). Esta opcion mezcla mas detalle comercial en financiero; debe justificarse como trazabilidad, no ownership.
3. JSON estructurado en bloque. No recomendado como primera opcion si se requieren constraints de duplicados/rangos y auditoria fuerte.

---

## 4) Diseno de calculo objetivo

### 4.1 Cantidades

Para cada `TRAMO_CUOTAS`:

```text
cantidad_total_cuotas = cantidad_cuotas informada en el tramo
cantidad_refuerzos = count(cuotas_refuerzo)
cantidad_cuotas_normales = cantidad_total_cuotas - cantidad_refuerzos
```

Validaciones:

- `cantidad_total_cuotas > 0`.
- Cada `numero_cuota` debe estar entre `1` y `cantidad_total_cuotas`.
- No puede haber dos refuerzos para el mismo `numero_cuota` en el mismo tramo, salvo decision futura explicita de acumulacion (no recomendada en primera etapa).
- `cantidad_refuerzos <= cantidad_total_cuotas`.
- `unidades_refuerzo > 0` si se usa para ponderar importes.
- `cuotas_refuerzo` solo aplica a `TRAMO_CUOTAS`.

Errores propuestos:

- `CUOTA_REFUERZO_NUMERO_INVALIDO`
- `CUOTA_REFUERZO_DUPLICADA`
- `CUOTA_REFUERZO_EXCEDE_CANTIDAD_CUOTAS`
- `CANTIDAD_REFUERZOS_EXCEDE_CUOTAS`
- `CUOTA_REFUERZO_NO_COMPATIBLE_CON_TIPO_BLOQUE`

### 4.2 Valor de cuota y unidades

El usuario no debe reservar capital manualmente para refuerzos. Por lo tanto, el calculo debe derivar el valor de todas las posiciones desde el capital total del tramo y la cantidad de unidades.

Modelo recomendado cuando se usa `unidades_refuerzo`:

```text
unidades_normales = cantidad_cuotas_normales * 1
unidades_refuerzo_total = sum(cuotas_refuerzo.unidades_refuerzo)
unidades_totales = unidades_normales + unidades_refuerzo_total
valor_unidad = importe_total_bloque / unidades_totales

importe_cuota_normal = valor_unidad
importe_cuota_refuerzo = valor_unidad * unidades_refuerzo
```

Ejemplo:

```text
importe_total_bloque = 24.000.000
cantidad_total_cuotas = 24
refuerzos = cuota 6 con 2 unidades, cuota 18 con 2 unidades

cantidad_cuotas_normales = 22
unidades_totales = 22 + 2 + 2 = 26
valor_unidad = 24.000.000 / 26
```

Esto evita que el usuario cree un bloque `REFUERZO` adicional y reste manualmente capital al tramo.

Si la primera implementacion no quiere ponderar por unidades, se podria aceptar solo `numero_cuota` y tratar la cuota refuerzo como una posicion de igual importe que una cuota normal. Sin embargo, como el requerimiento menciona `unidades_refuerzo`, la estrategia por unidades es la mas consistente.

### 4.3 Vencimientos

Para periodicidad mensual vigente:

```text
fecha_vencimiento(numero_cuota) = add_months(fecha_primer_vencimiento, numero_cuota - 1)
```

Reglas:

- Una cuota refuerzo en `numero_cuota = 6` vence en la misma fecha que la posicion 6 del tramo.
- Si se materializa como obligacion separada, debe conservar el mismo vencimiento de la posicion asociada.
- No se debe pedir `fecha_vencimiento` manual para cada refuerzo interno, porque eso permitiria romper la asociacion con la cuota/mes.

### 4.4 Orden del cronograma

Orden recomendado dentro de un tramo:

1. Ordenar por `numero_cuota` ascendente.
2. Para cada posicion:
   - si la posicion es normal: generar un item `CUOTA`.
   - si la posicion es refuerzo: generar un item `REFUERZO`.
3. Si por decision futura se materializan dos obligaciones en el mismo vencimiento para una posicion refuerzo (una normal y una refuerzo separada), entonces esa decision debe aclarar que ambas siguen representando una unica posicion del total y debe agregarse un campo de agrupacion/posicion. Para primera etapa, se recomienda reemplazo 1:1: una posicion refuerzo genera un item `REFUERZO`, no un `CUOTA + REFUERZO`.

---

## 5) Convivencia con metodos de liquidacion

### 5.1 `SIN_INTERES`

- Aplica la formula base por unidades.
- Cada posicion normal genera capital `CAPITAL_VENTA`.
- Cada posicion refuerzo genera capital `CAPITAL_VENTA` con `tipo_item_cronograma = REFUERZO`.
- Total de items del tramo: `cantidad_total_cuotas`.

### 5.2 `INTERES_DIRECTO`

`INTERES_DIRECTO` hoy se calcula a nivel de `TRAMO_CUOTAS` sobre `importe_total_bloque`, tasa y periodos. Para cuotas refuerzo internas:

- El interes total del bloque debe calcularse igual que hoy sobre el capital inicial del bloque.
- La distribucion de capital + interes debe respetar las unidades de cada posicion.
- Una posicion refuerzo debe recibir su proporcion de capital e interes segun `unidades_refuerzo`.
- Las composiciones esperadas siguen siendo `CAPITAL_VENTA` + `INTERES_FINANCIERO`.
- No debe convertirse `REFUERZO` en bloque separado, porque eso dejaria al refuerzo fuera del metodo de liquidacion del tramo.

### 5.3 `INDEXACION`

`INDEXACION` actualmente opera como `metodo_liquidacion` de `TRAMO_CUOTAS`, con calculo por cuota y composicion de ajuste cuando hay indice aplicable.

Para cuotas refuerzo internas:

- La fecha objetivo de indice de una cuota refuerzo debe ser el vencimiento derivado de su `numero_cuota`.
- El capital base de la posicion refuerzo debe ser el importe derivado por unidades.
- La composicion esperada debe conservar capital original y ajuste por diferencia (`CAPITAL_VENTA` + `AJUSTE_INDEXACION`) cuando aplique.
- Deben existir tests de no regresion para que refuerzos internos no rompan calculo por indice ni conteos proyectados/con indice.

### 5.4 No combinaciones no definidas

- No habilitar simultaneamente `INTERES_DIRECTO` + `INDEXACION` en el mismo tramo salvo decision tecnica futura expresa.
- No permitir cuotas refuerzo internas sobre `ANTICIPO`, `CONTADO`, `REFUERZO` libre ni `SALDO`.

---

## 6) Materializacion financiera

### 6.1 Obligacion normal

Para una posicion normal:

```text
tipo_item_cronograma = CUOTA
item_numero = numero_cuota
fecha_vencimiento = fecha derivada
importe_total = importe calculado de posicion normal
concepto base = CAPITAL_VENTA
```

### 6.2 Obligacion refuerzo interna

Para una posicion refuerzo:

```text
tipo_item_cronograma = REFUERZO
item_numero = numero_cuota
numero_cuota_asociada = numero_cuota (si existe campo futuro)
fecha_vencimiento = misma fecha que la posicion del tramo
importe_total = importe calculado por unidades_refuerzo
concepto base = CAPITAL_VENTA
```

### 6.3 Total de obligaciones

Para la regla objetivo de reemplazo 1:1:

```text
cantidad_obligaciones_del_tramo = cantidad_total_cuotas
```

No se debe generar:

```text
cantidad_total_cuotas + cantidad_refuerzos
```

### 6.4 Clave funcional

La clave funcional actual de generate usa bloque, tipo de item y `item_numero`. Para refuerzos internos se recomienda mantener idempotencia deterministica incorporando la posicion del tramo:

```text
PLAN_PAGO_VENTA:{id_plan_pago_venta}:BLOQUE:{numero_bloque}:REFUERZO:{numero_cuota}
```

Si se permite mas de un refuerzo por posicion, seria necesario otro ordinal; pero esa alternativa queda descartada para primera etapa por la validacion `CUOTA_REFUERZO_DUPLICADA`.

---

## 7) Impacto por componente

### 7.1 Preview

Impactos esperados:

- Extender `PlanPagoVentaBloqueInput` y schema HTTP para `cuotas_refuerzo` dentro de `TRAMO_CUOTAS`.
- Validar rango, duplicados, cantidad y compatibilidad de tipo de bloque.
- Cambiar el builder de importes del tramo para distribuir por unidades.
- Cambiar `_build_obligaciones` para emitir `CUOTA` o `REFUERZO` por posicion, manteniendo `len(obligaciones_tramo) = cantidad_total_cuotas`.
- Exponer en respuesta preview campos suficientes para distinguir:
  - cuota normal;
  - cuota refuerzo;
  - `numero_cuota` / `numero_cuota_asociada`;
  - `unidades_refuerzo`.
- Mantener `total_calculado` como capital base del plan y `total_con_interes`/`total_con_indexacion` segun metodo.

### 7.2 Generate

Impactos esperados:

- Persistir la definicion de refuerzos por tramo antes de crear obligaciones, si se decide trazabilidad fisica.
- Usar el preview enriquecido como fuente para crear obligaciones.
- Garantizar que `plan_pago_venta.cantidad_cuotas` siga representando `cantidad_total_cuotas` de tramos, no `cuotas normales + extras`.
- Mantener idempotencia por `clave_funcional_origen`.
- Persistir composiciones con la misma regla de `SIN_INTERES`, `INTERES_DIRECTO` o `INDEXACION` del tramo.

### 7.3 Consulta integral

Impactos esperados:

- La consulta integral ya expone `tipo_item_cronograma`, bloques, obligaciones, composiciones, obligados e indexacion.
- Para distinguir cuotas normales/refuerzo de forma completa, debe exponer o derivar con evidencia:
  - `tipo_item_cronograma = REFUERZO`;
  - `item_numero` como posicion del tramo;
  - `numero_cuota_asociada` si se agrega fisicamente;
  - `unidades_refuerzo` si se persiste.
- El resumen deberia permitir verificar:
  - obligaciones totales del tramo;
  - cantidad de cuotas normales;
  - cantidad de refuerzos;
  - total capital/interes/indexacion.

---

## 8) SQL requerido

### 8.1 Sin SQL no alcanza para implementacion completa

Para una implementacion robusta y auditable de cuotas refuerzo internas **si hace falta SQL**, porque hoy no existe soporte fisico confirmado para:

- lista de refuerzos asociada a un `TRAMO_CUOTAS`;
- numero de cuota asociado;
- unidades/cantidad de refuerzo;
- constraints de rango/duplicados;
- trazabilidad persistida hacia consulta integral.

### 8.2 SQL minimo recomendado

Crear tabla hija de bloque:

```text
plan_pago_venta_bloque_refuerzo
  id_plan_pago_venta_bloque_refuerzo
  id_plan_pago_venta_bloque
  numero_cuota
  unidades_refuerzo
  etiqueta
  observaciones
  metadatos sync/versionado/baja logica
```

Constraints esperados:

- FK a `plan_pago_venta_bloque`.
- `numero_cuota > 0`.
- `unidades_refuerzo > 0`.
- Unico activo por `(id_plan_pago_venta_bloque, numero_cuota)`.
- Constraint o validacion app que asegure que el bloque padre sea `TRAMO_CUOTAS`.
- Validacion app/SQL diferida de `numero_cuota <= cantidad_cuotas` del bloque.

Opcional segun necesidad de consulta:

- Agregar `numero_cuota_asociada` a `obligacion_financiera` o una tabla de trazabilidad de item de cronograma. Si se agrega al financiero, debe documentarse como trazabilidad de origen comercial, no como ownership financiero de la regla.

---

## 9) Tests futuros requeridos

### 9.1 Preview

- Preview de `TRAMO_CUOTAS` con 24 cuotas y 2 refuerzos devuelve 24 obligaciones totales.
- Cuotas normales = 22.
- Cuotas refuerzo = 2.
- Refuerzo en cuota 6 tiene vencimiento de cuota 6.
- Refuerzo en cuota 18 tiene vencimiento de cuota 18.
- Los refuerzos no aumentan cantidad total.
- El capital total del tramo se distribuye sin exigir capital reservado manualmente.
- Error `CUOTA_REFUERZO_NUMERO_INVALIDO` para `numero_cuota <= 0`.
- Error `CUOTA_REFUERZO_EXCEDE_CANTIDAD_CUOTAS` para `numero_cuota > cantidad_total_cuotas`.
- Error `CUOTA_REFUERZO_DUPLICADA` para dos refuerzos en la misma posicion.
- Error `CANTIDAD_REFUERZOS_EXCEDE_CUOTAS` cuando la lista supera posiciones disponibles.
- Error `CUOTA_REFUERZO_NO_COMPATIBLE_CON_TIPO_BLOQUE` si se informa en bloque no `TRAMO_CUOTAS`.

### 9.2 Generate

- Generate persiste bloque, refuerzos internos y obligaciones correctas.
- `plan_pago_venta.cantidad_cuotas` permanece en 24 para el caso 24/2.
- Las obligaciones generadas para el tramo son 24, no 26.
- Las claves funcionales son deterministicas e idempotentes.
- Reintento con mismo payload no duplica obligaciones/refuerzos.
- Reintento con mismo plan y refuerzos incompatibles falla con error de incompatibilidad.

### 9.3 Consulta integral

- Consulta integral distingue `CUOTA` vs `REFUERZO`.
- Consulta integral muestra posicion asociada y unidades del refuerzo cuando exista soporte fisico.
- Resumen integral conserva total de obligaciones esperado y totales financieros.

### 9.4 No regresion de metodos

- No regresion de `SIN_INTERES` sin refuerzos.
- No regresion de `INTERES_DIRECTO` sin refuerzos.
- `INTERES_DIRECTO` con refuerzos distribuye capital/interes por unidades y mantiene total del tramo.
- No regresion de `INDEXACION` sin refuerzos.
- `INDEXACION` con refuerzos usa vencimiento asociado para indice y mantiene composiciones `CAPITAL_VENTA`/`AJUSTE_INDEXACION`.

### 9.5 SQL/schema

- Tests de columnas/constraints de la tabla hija futura.
- Tests de constraint unico por `(id_plan_pago_venta_bloque, numero_cuota)` activo.
- Tests de rechazo de refuerzo asociado a bloque no `TRAMO_CUOTAS`.

---

## 10) Decision CORE-EF del PR documental

Este PR no agrega ni modifica endpoints write. Por lo tanto:

- Clasificacion del PR: documental / tecnico.
- Clasificacion de endpoint: `NO APLICA` (no se modifica endpoint).
- Headers CORE-EF: `NO APLICA` (no hay endpoint write nuevo/modificado).
- Idempotencia: `NO APLICA` para este PR; para implementacion futura de generate, debe preservarse por `clave_funcional_origen` y definicion persistida de refuerzos.
- Outbox: `NO APLICA` en este PR; implementacion futura debe evaluar si el generate sincronizable emite eventos.
- Lock logico: `NO APLICA` en este PR; implementacion futura debe evaluar bloqueo del plan/venta durante generacion.
- Versionado: `NO APLICA` en este PR; implementacion futura con tabla hija debe nacer con metadatos/versionado compatibles con el resto del modelo.
- Rollback/transaccion: `NO APLICA` en este PR; implementacion futura debe persistir plan, bloque, refuerzos, obligaciones y composiciones en una frontera transaccional.
- Tests CORE-EF: `NO APLICA` en este PR por no tocar codigo, SQL ni endpoints.

---

## 11) Conclusiones

1. El `REFUERZO` actual esta implementado como bloque libre de pago unico con importe y fecha propios.
2. Ese modelo actual no representa cuotas refuerzo internas al tramo, porque agrega obligaciones extras al cronograma cuando convive con `TRAMO_CUOTAS`.
3. Para cumplir la regla UX/funcional, la cuota refuerzo debe modelarse dentro de `TRAMO_CUOTAS` como posicion del total (`numero_cuota`) y no como bloque paralelo.
4. El total de obligaciones del tramo debe seguir siendo `cantidad_total_cuotas`.
5. Se requiere extender input/API, preview, generate, persistencia y consulta integral.
6. Para soporte completo y auditable, hace falta SQL futuro, preferentemente una tabla hija `plan_pago_venta_bloque_refuerzo`.
7. La convivencia con `SIN_INTERES`, `INTERES_DIRECTO` e `INDEXACION` debe resolverse por metodo de liquidacion del mismo tramo, no por bloques refuerzo externos.
8. No se debe dividir Plan Pago V2 por objeto ni por comprador para resolver este caso.
