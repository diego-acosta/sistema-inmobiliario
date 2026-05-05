# SRV-FIN-019 - Registro de pago por persona V1

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `POST /api/v1/financiero/pagos?id_persona={id}`

---

## Objetivo

Registrar un pago que impacta saldos de obligaciones de una persona, creando los registros persistentes correspondientes.

---

## Input

```json
{
  "monto": 50000.00,
  "fecha_pago": "2026-05-20"
}
```

- `monto` (obligatorio): monto a aplicar; debe ser > 0
- `fecha_pago` (opcional): fecha del pago; también usada como `fecha_corte` para mora; default `date.today()`

Query param:
- `id_persona` (obligatorio): persona pagante

---

## Output

```json
{
  "id_persona": 1,
  "fecha_pago": "2026-05-20",
  "monto_ingresado": 50000.00,
  "monto_aplicado": 45000.00,
  "remanente": 5000.00,
  "obligaciones_pagadas": [
    {
      "id_obligacion_financiera": 10,
      "id_movimiento_financiero": 5,
      "monto_aplicado": 20000.00,
      "estado_resultante": "CANCELADA"
    }
  ]
}
```

- `monto_aplicado`: suma de importes efectivamente aplicados a `saldo_pendiente`
- `remanente`: monto no consumido (incluyendo mora si el monto no alcanzó a cubrir saldo+mora)
- `obligaciones_pagadas`: una entrada por obligación con saldo reducido

---

## Persistencia

Por cada obligación cubierta:

1. `movimiento_financiero` (tipo=PAGO, signo=CREDITO, estado=APLICADO)
2. `aplicacion_financiera` por cada `composicion_obligacion` afectada
3. Trigger de DB actualiza `saldo_pendiente`
4. UPDATE de `estado_obligacion` (→ CANCELADA o PARCIALMENTE_CANCELADA)

Todo en una única transacción. Rollback total si alguna escritura falla.

---

## Idempotencia por op_id

Si el request incluye `X-Op-Id` y ya existe al menos un
`movimiento_financiero` de tipo `PAGO` con `op_id_alta` igual para la persona
indicada, el servicio devuelve el resultado persistido de esa operación y no
crea nuevos movimientos ni nuevas aplicaciones.

Antes de devolver el resultado idempotente, el servicio valida que el payload
minimo coincida con el registrado originalmente en
`movimiento_financiero.observaciones`: `tipo = pago_persona`, `id_persona`,
`monto_ingresado` normalizado a 2 decimales y `fecha_pago` efectiva. Si el
mismo `X-Op-Id` se reutiliza con otro `id_persona`, `monto` o `fecha_pago`,
devuelve `IDEMPOTENCY_PAYLOAD_CONFLICT` con HTTP 409.

El comportamiento mantiene el modelo V1 de un `movimiento_financiero` por
obligación cubierta. Por eso un mismo `op_id` puede agrupar múltiples
movimientos de pago cuando un pago cubre más de una obligación.

Para reconstruir el resultado idempotente, `movimiento_financiero.observaciones`
guarda un resumen técnico de la operación. No representa una imputación ni crea
conceptos financieros adicionales.

Sin `X-Op-Id`, el endpoint mantiene el comportamiento histórico: cada llamada
válida puede registrar un nuevo pago.

---

## Mora / punitorio

Si corresponde mora liquidable al momento del pago, se crea o incrementa una
`composicion_obligacion` `PUNITORIO` dentro de la obligacion base antes de
imputar. No se crea nueva `obligacion_financiera` ni composicion
`INTERES_MORA` para esta liquidacion V1.

La base morable se obtiene desde composiciones activas cuyo
`concepto_financiero.aplica_punitorio = true`. `PUNITORIO` y accesorios no
marcados no integran esa base.

---

## Regla funcional: punitorio por pago

Estado: `IMPLEMENTADO`.

Cuando el pago liquide mora persistida, el cargo debe registrarse como
`PUNITORIO` dentro de la obligacion base. No se debe crear un componente
`INTERES_MORA` separado en V1.

Reglas:

- si `fecha_pago <= fecha_vencimiento + dias_gracia`, no se liquida punitorio
- si `fecha_pago > fecha_vencimiento + dias_gracia`, el calculo corre desde
  `fecha_vencimiento`
- pagos anteriores o iguales a `fecha_vencimiento` no interrumpen el tramo
  moratorio
- pagos posteriores a `fecha_vencimiento` si interrumpen el tramo; el siguiente
  calculo usa como inicio la ultima fecha de pago posterior al vencimiento
- la base es el saldo morable pendiente de la obligacion, definido por
  `concepto_financiero.aplica_punitorio = true`
- no incluye punitorios pendientes ni accesorios no marcados
- no hay hardcode por codigo de concepto para determinar base morable
- el punitorio liquidado se persiste como `composicion_obligacion` `PUNITORIO`
  de la obligacion base
- si el pago no cubre el total liquidado, queda `saldo_componente` pendiente

---

## Diferencias vs POST /api/v1/financiero/imputaciones

| | `imputaciones` | `pagos` |
|---|---|---|
| Alcance | 1 obligación | todas las de la persona |
| Transacción | 1 obligación | múltiples obligaciones |
| Orden | manual | vencidas primero |
| Mora | no incluye | incluye en total_a_cubrir |

---

## Limitaciones V1

- mora no se persiste como `INTERES_MORA`
- no soporta distribución proporcional entre co-obligados
- un único `movimiento_financiero` por obligación (no uno global por pago)

---

## Referencias

- `MODELO-FINANCIERO-FIN` sección 12
- `SRV-FIN-018-simulacion-pago-persona`
- `SRV-FIN-013-generacion-de-mora`
