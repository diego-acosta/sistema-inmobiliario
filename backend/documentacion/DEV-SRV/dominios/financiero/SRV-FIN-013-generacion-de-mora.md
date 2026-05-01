# SRV-FIN-013 - Mora V1 simple

## Objetivo

Marcar obligaciones vencidas y exponer mora diaria calculada dinamicamente,
sin crear obligaciones financieras nuevas por mora.

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `POST /api/v1/financiero/mora/generar`
- no modifica SQL estructural
- no usa `tipo_obligacion`
- no crea `INTERES_MORA` como obligacion

## Alcance

Este servicio cubre:

- seleccion de obligaciones `EMITIDA` vencidas con saldo
- transicion idempotente a `VENCIDA`
- calculo simple de mora diaria en lecturas
- exposicion de `mora_calculada`, `dias_atraso` y `tasa_diaria_mora` en deuda
  consolidada y estado de cuenta

No cubre:

- creacion de obligaciones de mora
- capitalizacion de mora
- punitorios
- politicas variables de tasa
- refinanciacion
- reversion especifica de mora

## Decisión V1 — Mora dinámica no persistida

En la versión actual, la mora no genera obligaciones financieras accesorias ni composiciones `INTERES_MORA`.

El proceso de mora V1 solo realiza:

- marcado idempotente de obligaciones `EMITIDA -> VENCIDA`
- cálculo dinámico de `mora_calculada` en consultas de deuda y estado de cuenta
- exposición de `dias_atraso` y `tasa_diaria_mora`

La mora calculada no modifica:

- `importe_total`
- `saldo_pendiente`
- `composicion_obligacion`
- `obligacion_obligado`

## Pendientes explícitos

- parametrizar `tasa_diaria_mora`
- definir días de gracia
- definir política de mora por contrato, concepto o relación generadora
- definir si habrá Mora V2 persistida
- definir cuándo una mora calculada se liquida formalmente
- definir si una liquidación de mora futura genera:
  - una nueva `obligacion_financiera`
  - una `composicion_obligacion` accesoria
  - o un movimiento/ajuste financiero específico

## Endpoint

`POST /api/v1/financiero/mora/generar`

Request:

```json
{
  "fecha_proceso": "2026-05-01"
}
```

Si `fecha_proceso` no viene, el backend usa la fecha actual.

Response:

```json
{
  "ok": true,
  "data": {
    "fecha_proceso": "2026-05-01",
    "procesadas": 10,
    "marcadas": 10,
    "generadas": 0,
    "tasa_diaria": "0.001"
  }
}
```

`generadas` se mantiene en `0` porque Mora V1 simple no crea obligaciones de
mora.

## Reglas de negocio

Una obligacion pasa a `VENCIDA` si cumple:

- `fecha_vencimiento < fecha_proceso`
- `saldo_pendiente > 0`
- `deleted_at IS NULL`
- `estado_obligacion = 'EMITIDA'`

La transicion es idempotente: una obligacion ya `VENCIDA`, `CANCELADA`,
`ANULADA`, `REEMPLAZADA`, `PENDIENTE_AJUSTE` o en otro estado no vuelve a
modificarse por este proceso.

## Calculo dinamico

La mora no se persiste como deuda ni como composicion.

Formula:

```text
mora_calculada = saldo_pendiente * tasa_diaria * dias_atraso
```

Reglas:

- tasa diaria fija inicial: `0.001`
- `dias_atraso = fecha_actual - fecha_vencimiento` cuando la obligacion esta
  vencida
- si no hay atraso o el saldo es cero, `mora_calculada = 0`
- redondeo a 2 decimales

## Lecturas afectadas

`GET /api/v1/financiero/deuda` agrega por obligacion:

- `dias_atraso`
- `mora_calculada`
- `tasa_diaria_mora`

`GET /api/v1/financiero/relaciones-generadoras/{id}/estado-cuenta` agrega por
obligacion los mismos campos y en resumen:

- `mora_calculada`

El saldo persistido no se modifica por la mora calculada.

## Pendientes

- tasa configurable por parametro formal
- dias de gracia
- politica por tipo de contrato/concepto
- eventual generacion de cargos de mora si se define V2
- punitorios
- reversion/anulacion especifica de mora
