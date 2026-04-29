# INT-FIN-004 - Contrato de plan de generacion de obligaciones

## Estado

- estado: `DEFINIDO`
- impacto: `ALTO`
- bloquea: implementacion de materializacion de obligaciones

---

## 1. Problema

`financiero` no debe definir la estrategia de generacion de obligaciones.

La estrategia pertenece a los dominios origen, porque ellos conocen las condiciones economicas primarias:

- `comercial` conoce si una venta es de contado, financiada o con anticipo y saldo.
- `locativo` conoce la periodicidad, importes y vigencia contractual del alquiler.
- `inmobiliario` aporta el origen operativo de `factura_servicio` para servicios trasladados, cuando ese flujo exista implementado.

Si `financiero` calculara cuotas, definiera importes o decidiera cantidad de obligaciones por su cuenta, invadiria el ownership semantico del dominio origen.

---

## 2. Solucion

Se define el contrato de entrada:

`PlanGeneracionObligaciones`

El dominio origen construye el plan segun sus condiciones economicas.

`financiero` recibe ese plan en la operacion de materializacion, valida su integridad y materializa las obligaciones financieras persistentes.

`PlanGeneracionObligaciones` no es input de `activar relacion_generadora`. La activacion solo habilita y da vigencia a la `relacion_generadora`; no crea obligaciones.

Resumen:

```text
dominio origen calcula estrategia
-> PlanGeneracionObligaciones
-> operacion materializar-obligaciones
-> financiero valida integridad
-> financiero persiste obligaciones
```

---

## 3. Estructura

Ejemplo de `PlanGeneracionObligaciones`:

```json
{
  "tipo_origen": "VENTA",
  "id_origen": 10,
  "obligaciones": [
    {
      "concepto": "ANTICIPO",
      "importe": 100000,
      "fecha_emision": "...",
      "fecha_vencimiento": "..."
    }
  ]
}
```

Campos base:

- `tipo_origen`: tipo de origen financiero, por ejemplo `VENTA`, `CONTRATO_ALQUILER` o `SERVICIO_TRASLADADO`.
- `id_origen`: identificador del origen en su dominio.
- `obligaciones`: lista de obligaciones a materializar.
- `concepto`: concepto economico definido por el origen o por el catalogo financiero aplicable.
- `importe`: importe de la obligacion ya definido por el origen.
- `fecha_emision`: fecha de emision prevista.
- `fecha_vencimiento`: fecha de exigibilidad o vencimiento.

---

## 4. Reglas

- `financiero` no modifica importes.
- `financiero` no calcula cuotas.
- `financiero` no decide la cantidad de obligaciones.
- `financiero` recibe el plan en la operacion de materializacion, no en la activacion de la relacion generadora.
- `financiero` valida integridad estructural del plan.
- `financiero` valida que el origen referenciado sea compatible con la `relacion_generadora`.
- `financiero` valida que la `relacion_generadora` este activa antes de materializar.
- `financiero` persiste `obligacion_financiera` y `composicion_obligacion` segun el plan.
- El dominio origen es responsable de la coherencia economica del plan.
- Si el plan es invalido o inconsistente, `financiero` debe rechazar la materializacion y no dejar efectos parciales.

---

## 5. Relacion con relacion_generadora

`relacion_generadora` sigue existiendo.

La `relacion_generadora` actua como vinculo formal entre:

- el origen economico externo al dominio financiero
- el plan de obligaciones recibido
- las obligaciones financieras persistidas

El plan no reemplaza a `relacion_generadora`.

El plan describe que obligaciones deben generarse; `relacion_generadora` conserva la trazabilidad, ownership financiero y agrupacion de esas obligaciones.

La `relacion_generadora` debe estar activa para materializar obligaciones, pero su activacion no implica materializarlas.

Una misma `relacion_generadora` activa puede recibir uno o mas planes de generacion durante su vigencia, siempre que cada materializacion sea valida e idempotente respecto de las obligaciones ya persistidas.

---

## 6. Estado

- estado: `DEFINIDO`
- impacto: `ALTO`
- bloquea: implementacion de materializacion de obligaciones

Esta decision es base para una implementacion futura de `materializar obligaciones`. No modifica SQL, backend ni tests.
