# MODELO-FINANCIERO-FIN - Modelo formal de obligaciones y conceptos

## Estado del documento

- estado: `DEFINIDO CONCEPTUALMENTE / PARCIALMENTE REPRESENTADO EN SQL`
- dominio: `financiero`
- alcance: `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `concepto_financiero`
- no crea endpoints
- no modifica SQL
- no modifica reglas de pago, imputacion, caja, recibos o movimientos financieros

Este documento define el modelo logico financiero para materializar obligaciones sin codificar rigidamente en la obligacion si se trata de venta, alquiler, servicio, expensa u otro origen operativo.

---

## 1. Modelo logico

```text
relacion_generadora
    1 --- N obligacion_financiera

obligacion_financiera
    1 --- N composicion_obligacion

concepto_financiero
    1 --- N composicion_obligacion
```

Interpretacion:

- `relacion_generadora` es la raiz financiera.
- `obligacion_financiera` representa deuda exigible o proyectada.
- `composicion_obligacion` representa el desglose economico de una obligacion.
- `concepto_financiero` es el catalogo que define el significado financiero de cada componente.

El origen se interpreta desde `relacion_generadora`.

La naturaleza economica se interpreta desde `composicion_obligacion` + `concepto_financiero`.

La obligacion no debe codificar rigidamente `venta`, `alquiler`, `servicio`, `expensa` u otros tipos de negocio como logica central. Esos significados se expresan por:

- `relacion_generadora.tipo_origen` e `id_origen`, para ubicar el origen;
- `concepto_financiero`, para clasificar la naturaleza economica;
- `composicion_obligacion`, para materializar importes por concepto.

---

## 2. Entidades

### 2.1 relacion_generadora

Raiz formal del circuito financiero.

Responsabilidad:

- vincular un origen economico externo con el circuito financiero;
- mantener trazabilidad del origen;
- agrupar obligaciones financieras generadas o proyectadas.

El dominio origen define el hecho, contrato, plan o evento que dispara la deuda. `financiero` administra la relacion generadora y las obligaciones derivadas.

### 2.2 obligacion_financiera

Representa deuda exigible o proyectada dentro de una `relacion_generadora`.

Campos logicos esperados:

| Campo | Estado documental |
|---|---|
| `id_obligacion_financiera` | SQL vigente |
| `id_relacion_generadora` | SQL vigente |
| `codigo_obligacion_financiera` | Conceptual; SQL vigente usa `codigo_obligacion` |
| `descripcion_operativa` | Conceptual |
| `fecha_generacion` | Conceptual |
| `fecha_emision` | SQL vigente |
| `fecha_vencimiento` | SQL vigente |
| `periodo_desde` | Conceptual |
| `periodo_hasta` | Conceptual |
| `fecha_cierre` | Conceptual |
| `importe_total` | Conceptual; SQL vigente usa `importe_original` |
| `saldo_pendiente` | SQL vigente |
| `importe_cancelado_acumulado` | Conceptual |
| `importe_bonificado_acumulado` | Conceptual |
| `importe_anulado_acumulado` | Conceptual |
| `moneda` | Conceptual |
| `estado_obligacion` | SQL vigente |
| `es_exigible` | Conceptual / derivable |
| `es_proyectada` | Conceptual / derivable |
| `es_emitida` | Conceptual / derivable |
| `es_vencida` | Conceptual / derivable |
| `genera_recibo` | Conceptual; no implica emision automatica |
| `afecta_estado_cuenta` | Conceptual |
| `afecta_libre_deuda` | Conceptual |
| `observaciones` | SQL vigente |

Estados conceptuales sugeridos:

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `CANCELADA`
- `VENCIDA`
- `ANULADA`
- `REEMPLAZADA`

Estado fisico actual:

- SQL vigente conserva `estado_obligacion` como texto, pero la documentacion vigente `EST-FIN` solo formaliza `pendiente`, `vencida`, `parcialmente_cancelada` y `cancelada`.
- La incorporacion fisica o contractual de los estados conceptuales restantes queda `PENDIENTE`.

### 2.3 composicion_obligacion

Representa el desglose economico de una `obligacion_financiera`.

Campos logicos esperados:

| Campo | Estado documental |
|---|---|
| `id_composicion_obligacion` | SQL vigente |
| `id_obligacion_financiera` | SQL vigente |
| `id_concepto_financiero` | SQL vigente |
| `orden_composicion` | Conceptual |
| `estado_composicion_obligacion` | Conceptual |
| `importe_componente` | Conceptual; SQL vigente usa `importe` |
| `saldo_componente` | Conceptual |
| `moneda_componente` | Conceptual |
| `detalle_calculo` | Conceptual |
| `observaciones` | SQL vigente |

Si una obligacion combina varios conceptos, debe representarse con varias filas de `composicion_obligacion`.

El saldo de la obligacion debe ser reconstruible o conciliable contra sus componentes. La regla exacta de persistencia de saldos por componente queda `PENDIENTE` porque SQL vigente no posee `saldo_componente`.

Politica de saldo por componente:

- El saldo operativo real debe poder existir a nivel `composicion_obligacion`.
- `composicion_obligacion.saldo_componente` representa el saldo vivo de ese concepto dentro de la obligacion.
- `obligacion_financiera.saldo_pendiente` representa el saldo total consolidado.
- Regla preferida: `obligacion_financiera.saldo_pendiente` debe ser igual a la suma de `saldo_componente` de sus composiciones activas, salvo transicion tecnica documentada.
- SQL vigente no posee `saldo_componente`; por lo tanto, la persistencia fisica queda `PENDIENTE SQL`, pero la regla conceptual queda definida.

### 2.4 concepto_financiero

Catalogo financiero que define el significado de cada componente economico.

Campos logicos esperados:

| Campo | Estado documental |
|---|---|
| `id_concepto_financiero` | SQL vigente |
| `codigo_concepto_financiero` | Conceptual; SQL vigente usa `codigo_concepto` |
| `nombre_concepto_financiero` | Conceptual; SQL vigente usa `nombre_concepto` |
| `descripcion_concepto_financiero` | Conceptual |
| `tipo_concepto_financiero` | Conceptual; SQL vigente usa `tipo_concepto` |
| `naturaleza_concepto` | Conceptual |
| `afecta_capital` | Conceptual |
| `afecta_interes` | Conceptual |
| `afecta_mora` | Conceptual |
| `afecta_impuesto` | Conceptual |
| `afecta_caja` | Conceptual |
| `es_imputable` | Conceptual |
| `permite_saldo` | Conceptual |
| `estado_concepto_financiero` | Conceptual; SQL vigente usa `estado_concepto` |
| `observaciones` | Conceptual |

Catalogo base inicial conceptual:

| Codigo | Uso esperado |
|---|---|
| `CAPITAL_VENTA` | Capital de una cuota o saldo de venta. |
| `ANTICIPO_VENTA` | Anticipo exigible asociado a una venta. |
| `SALDO_EXTRAORDINARIO` | Saldo no periodico o diferencia extraordinaria. |
| `CANON_LOCATIVO` | Canon de alquiler o devengamiento locativo. |
| `EXPENSA_TRASLADADA` | Expensa trasladada al obligado financiero. |
| `SERVICIO_TRASLADADO` | Servicio trasladado desde un origen operativo registrado. |
| `IMPUESTO_TRASLADADO` | Impuesto o tasa trasladada. |
| `INTERES_FINANCIERO` | Interes financiero ordinario. |
| `INTERES_MORA` | Interes por mora. |
| `PUNITORIO` | Punitorio por incumplimiento o mora. |
| `CARGO_ADMINISTRATIVO` | Cargo administrativo financiero. |
| `LIQUIDACION_FINAL` | Concepto de cierre o liquidacion final. |
| `REFINANCIACION` | Concepto asociado a reestructuracion de deuda. |
| `CANCELACION_ANTICIPADA` | Concepto asociado a cancelacion antes del vencimiento natural. |
| `AJUSTE_INDEXACION` | Ajuste por indice o actualizacion. |
| `CREDITO_MANUAL` | Credito manual imputable segun politica financiera. |
| `DEBITO_MANUAL` | Debito manual imputable segun politica financiera. |

Estado fisico actual:

- `concepto_financiero` existe en SQL.
- El catalogo base inicial no esta confirmado como datos seed ni como catalogo SQL cargado.
- Los campos conceptuales que no existen en SQL quedan `PENDIENTE` para una migracion futura.

---

## 3. Reglas estructurales

1. Toda `obligacion_financiera` pertenece a una `relacion_generadora`.
2. Toda `obligacion_financiera` debe tener una o mas composiciones.
3. Toda `composicion_obligacion` debe referenciar exactamente un `concepto_financiero`.
4. La obligacion no debe codificar rigidamente `tipo_obligacion` como logica central.
5. La composicion permite representar cuota de venta, anticipo, saldo extraordinario, alquiler mensual, expensa, servicio, impuesto trasladado, interes, punitorio, cargo administrativo, liquidacion final, refinanciacion y cancelacion anticipada.
6. Si una obligacion combina varios conceptos, debe representarse con varias filas de `composicion_obligacion`.
7. El saldo de la obligacion debe ser reconstruible o conciliable contra sus componentes.
8. El origen se interpreta desde `relacion_generadora`; no desde el concepto.
9. La naturaleza economica se interpreta desde `composicion_obligacion` + `concepto_financiero`; no desde un tipo rigido de obligacion.
10. Un pago no cancela directamente una obligacion. La cancelacion se produce mediante `aplicacion_financiera` / imputacion financiera, conforme a `SRV-FIN-007`, `SRV-FIN-008` y `RN-FIN`.

---

## 4. Politica de saldo e imputacion por componente

### 4.1 Regla de saldo

- El saldo operativo real debe poder existir a nivel `composicion_obligacion`.
- `saldo_componente` representa el saldo vivo de cada concepto dentro de la obligacion.
- `saldo_pendiente` representa el saldo total consolidado de la obligacion.
- Regla preferida: `saldo_pendiente = SUM(saldo_componente)` para composiciones activas.
- La obligacion no puede figurar `CANCELADA` si alguna composicion activa conserva `saldo_componente > 0`.
- Una composicion no puede quedar con saldo negativo salvo nota de credito o credito manual explicitamente modelado.
- Los saldos acumulados de la obligacion deben ser conciliables con `movimiento_financiero` y `aplicacion_financiera`.

Estado fisico:

- `saldo_pendiente` existe en SQL vigente de `obligacion_financiera`.
- `saldo_componente` no existe en SQL vigente de `composicion_obligacion`; queda `PENDIENTE SQL`.
- Mientras no exista `saldo_componente`, la conciliacion por componente debe tratarse como regla conceptual o derivada desde `aplicacion_financiera.id_composicion_obligacion` cuando corresponda.

### 4.2 Regla de imputacion

La imputacion financiera debe aplicarse contra componentes, no solo contra la obligacion global, cuando exista desglose.

Si una imputacion se registra a nivel obligacion, el sistema debe distribuirla hacia componentes con una politica documentada.

Politica de distribucion por defecto para pagos globales:

1. `INTERES_MORA`
2. `PUNITORIO`
3. `CARGO_ADMINISTRATIVO`
4. `INTERES_FINANCIERO`
5. `AJUSTE_INDEXACION`
6. `CAPITAL_VENTA` / `ANTICIPO_VENTA` / `CANON_LOCATIVO` / `EXPENSA_TRASLADADA` / `SERVICIO_TRASLADADO` / `IMPUESTO_TRASLADADO`
7. Otros conceptos de cierre

Esta prioridad queda `DEFINIDA CONCEPTUALMENTE / PENDIENTE SQL-BACKEND` hasta que exista implementacion fisica de saldo por componente y reglas de distribucion automatica.

---

## 5. Ejemplos documentales

### Cuota de venta

Origen:

- `relacion_generadora.tipo_origen = VENTA`

Composicion:

- `CAPITAL_VENTA`
- `INTERES_FINANCIERO`, si corresponde

### Anticipo

Origen:

- `relacion_generadora.tipo_origen = VENTA`

Composicion:

- `ANTICIPO_VENTA`

### Alquiler mensual

Origen:

- `relacion_generadora.tipo_origen = CONTRATO_ALQUILER`

Composicion:

- `CANON_LOCATIVO`

### Servicio trasladado

Origen conceptual pendiente:

- `relacion_generadora.tipo_origen = SERVICIO_TRASLADADO`
- `id_origen` referencia a `factura_servicio` o contrato futuro equivalente

Composicion:

- `SERVICIO_TRASLADADO`

Estado:

- `CONCEPTUAL / NO IMPLEMENTADO` hasta que exista API/backend, evento y consumer financiero.

### Mora

Origen:

- relacion generadora de la deuda base

Composicion:

- `INTERES_MORA`
- `PUNITORIO`

### Liquidacion final

Origen:

- relacion generadora que se liquida

Composicion posible:

- `LIQUIDACION_FINAL`
- `INTERES_MORA`
- `PUNITORIO`
- `CARGO_ADMINISTRATIVO`

---

## 6. Relacion con pagos e imputacion

`movimiento_financiero` registra el pago o movimiento economico.

`aplicacion_financiera` imputa ese movimiento contra una `obligacion_financiera` y, cuando corresponda, contra una `composicion_obligacion`.

Por lo tanto:

- el pago no tiene FK directa obligatoria a `relacion_generadora` ni a `obligacion_financiera` en el SQL vigente;
- la trazabilidad entre pago y deuda se reconstruye por `aplicacion_financiera`;
- la cancelacion total o parcial de la obligacion debe pasar por imputacion financiera;
- la imputacion no modifica la definicion estructural de la obligacion, solo su saldo operativo.
- cuando exista desglose por componente, la imputacion debe afectar `composicion_obligacion` segun `id_composicion_obligacion` o mediante politica documentada de distribucion.

---

## 7. Estados y transiciones de obligacion_financiera

La definicion normativa de estados vive en `EST-FIN`. Este documento fija el criterio estructural que esos estados deben respetar:

- No se puede cancelar una obligacion sin `saldo_pendiente = 0`.
- No se puede cancelar una obligacion si alguna composicion activa tiene `saldo_componente > 0`.
- No se puede emitir una obligacion si su `relacion_generadora` no esta en estado valido para generar o emitir.
- No se puede reemplazar una obligacion sin trazabilidad hacia la obligacion nueva o proceso origen.
- No se puede anular una obligacion con pagos aplicados sin reversion o tratamiento documentado.
- `VENCIDA` puede ser estado materializado o derivado por `fecha_vencimiento + saldo`; la decision fisica queda `PENDIENTE`.
- Cualquier transicion que reduzca saldo requiere `aplicacion_financiera`, anulacion formal o credito documentado.

---

## 8. Contradicciones resueltas por este documento

La documentacion previa incluia una nocion de "tipo de obligacion" como catalogo conceptual. Esa idea no debe usarse como eje estructural ni como columna rigida de `obligacion_financiera`.

A partir de este modelo:

- los codigos economicos deben vivir como `concepto_financiero`;
- las agrupaciones operativas como cuota, anticipo, alquiler o servicio se documentan como ejemplos de composicion;
- el origen pertenece a `relacion_generadora`;
- la obligacion conserva su rol de contenedor de deuda, saldo y estado.

---

## 9. Pendientes

- Migracion SQL futura si se decide materializar los campos logicos faltantes.
- Definicion final de estados de obligacion proyectada, emitida, exigible, anulada y reemplazada.
- Seed o mantenimiento operativo del catalogo `concepto_financiero`.
- Implementacion SQL/backend de `saldo_componente`.
- Implementacion SQL/backend de estados ampliados y transiciones.
- Politica exacta de refinanciacion, cancelacion anticipada y liquidacion final.
