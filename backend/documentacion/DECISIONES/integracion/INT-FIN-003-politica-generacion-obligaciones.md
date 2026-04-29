# INT-FIN-003 - Politica de generacion de obligaciones por tipo de origen

## Estado

- estado: `DEFINIDO`
- impacto: `ALTO`
- bloquea: implementacion de `materializar obligaciones`

---

## 1. Problema

`relacion_generadora` es la raiz formal del circuito financiero, pero no tiene un comportamiento unico de generacion de obligaciones.

La cantidad, periodicidad y composicion de las obligaciones financieras dependen del `tipo_origen` y de las condiciones economicas definidas por el dominio que origina la relacion.

Por lo tanto, no es valido implementar la materializacion de obligaciones como una unica rutina generica que siempre produzca la misma cantidad de obligaciones o el mismo calendario.

`activar relacion_generadora` no genera obligaciones. Activar solo habilita y da vigencia a la relacion formal que puede producir obligaciones durante su vigencia.

---

## 2. Regla general

La `relacion_generadora` identifica y mantiene vigente el vinculo financiero con el dominio origen.

El dominio `financiero` materializa `obligacion_financiera` y `composicion_obligacion` en operaciones separadas de materializacion, segun las condiciones recibidas desde el dominio origen.

Regla de ownership:

- `comercial` define las condiciones economicas de una venta.
- `locativo` define las condiciones economicas de un contrato de alquiler.
- `inmobiliario` aporta el origen operativo de un servicio trasladado mediante `factura_servicio`, cuando exista contrato implementado para ese flujo.
- `financiero` materializa la deuda, conserva el ownership sobre `relacion_generadora`, `obligacion_financiera` y `composicion_obligacion`, y no redefine las condiciones primarias del dominio origen.

Resumen:

```text
dominio origen define condiciones
-> relacion_generadora activa como vinculo formal vigente
-> operacion de materializacion
-> financiero materializa obligaciones segun el plan recibido
```

---

## 3. Politica por tipo de origen

### VENTA

La generacion de obligaciones depende de las condiciones comerciales de la venta:

- venta de contado -> 1 `obligacion_financiera`
- venta financiada -> multiples `obligacion_financiera`, una por cuota o hito exigible
- venta con anticipo y saldo -> combinacion de obligaciones, por ejemplo una obligacion por anticipo y una o mas obligaciones por saldo

`financiero` no decide si la venta es contado, financiada o anticipo/saldo. Esa condicion proviene del dominio `comercial`.

La materializacion puede ocurrir una o varias veces durante la vigencia de la `relacion_generadora`, segun los hitos economicos definidos por `comercial`.

### CONTRATO_ALQUILER

La generacion de obligaciones es periodica.

La periodicidad y el alcance temporal surgen de las condiciones del contrato:

- mensual, cuando el contrato define devengamiento mensual
- por periodo contractual, cuando el contrato define otro esquema de exigibilidad

`financiero` materializa las obligaciones de alquiler segun el periodo, importes y condiciones definidos por `locativo`.

Una `relacion_generadora` activa puede producir obligaciones de alquiler multiples en distintos momentos de su vigencia.

### SERVICIO_TRASLADADO

La politica base es:

- 1 `factura_servicio` -> 1 `obligacion_financiera`

`factura_servicio` actua como origen operativo externo registrado por `inmobiliario`. El sistema no emite esa factura.

La obligacion derivada pertenece al dominio `financiero` y debe generarse desde una `relacion_generadora` valida. La generacion debe ser idempotente por `id_factura_servicio`, de modo que una factura no produzca mas de una obligacion financiera activa.

Esta regla es compatible con la decision conceptual vigente para `SERVICIO_TRASLADADO`: una `relacion_generadora` puede agrupar el servicio asociado a un inmueble o unidad funcional, y cada `factura_servicio` posterior genera una obligacion dentro de esa relacion.

---

## 4. Regla de diseno

`financiero` no define la cantidad de obligaciones.

`financiero` ejecuta la materializacion de obligaciones segun condiciones externas validadas y referenciadas por una `relacion_generadora` activa.

`relacion_generadora` es el vinculo formal vigente entre un origen economico y la deuda financiera que pueda materializarse, pero no reemplaza al dominio origen ni redefine sus condiciones.

La activacion de `relacion_generadora` y la materializacion de obligaciones son operaciones separadas.

---

## 5. Estado

- estado: `DEFINIDO`
- impacto: `ALTO`
- bloquea: implementacion de `materializar obligaciones`

La materializacion de obligaciones no debe implementarse hasta contar con politica por `tipo_origen` y reglas minimas para interpretar el plan recibido desde cada origen.

---

## 6. Implicancias tecnicas

- `activar relacion_generadora` no genera obligaciones.
- La materializacion de obligaciones requiere politica por `tipo_origen`.
- Cada politica debe recibir condiciones, calendario, importes y composicion desde el origen correspondiente.
- Una `relacion_generadora` activa puede producir obligaciones una o muchas veces durante su vigencia.
- La politica definida en este documento es base para futuras politicas configurables.
- Las futuras implementaciones deben mantener idempotencia por origen cuando corresponda, especialmente en `SERVICIO_TRASLADADO` con clave conceptual `id_factura_servicio`.
- Esta decision no modifica SQL, no agrega columnas y no implementa activacion, materializacion de obligaciones ni composiciones.
