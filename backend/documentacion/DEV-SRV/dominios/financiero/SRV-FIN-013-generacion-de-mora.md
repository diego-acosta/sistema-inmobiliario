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
- politicas variables de dias de gracia
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

- persistir/administrar `tasa_diaria_mora` por parametro formal
- parametrizar `dias_gracia_mora`
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

- `dias_atraso = max(0, fecha_corte - (fecha_vencimiento + dias_gracia))`
- si no hay atraso o el saldo es cero, `mora_calculada = 0`
- redondeo a 2 decimales

Los parámetros `tasa_diaria` y `dias_gracia` se resuelven mediante el
`resolver_mora_params` (ver sección "Resolver de parámetros de mora").

## Regla funcional para punitorio persistido por pago

Estado: `IMPLEMENTADO` en `POST /api/v1/financiero/pagos`.

Al registrar pagos, cuando corresponde liquidacion persistida de mora, la mora
liquidada se representa como `PUNITORIO`. En V1 no debe usarse un
componente `INTERES_MORA` separado para este caso.

Reglas de calculo:

- si `fecha_pago <= fecha_vencimiento + dias_gracia`, `punitorio = 0`
- si `fecha_pago > fecha_vencimiento + dias_gracia`, el punitorio se calcula
  desde `fecha_vencimiento`, no desde `fecha_vencimiento + dias_gracia`
- pagos realizados antes o en `fecha_vencimiento` no cortan el tramo de
  punitorio
- pagos posteriores al vencimiento si cortan el tramo: el siguiente punitorio
  se calcula desde la ultima `fecha_pago` posterior al vencimiento
- la base de calculo es el saldo morable pendiente, compuesto por
  composiciones cuyo `concepto_financiero.aplica_punitorio = true`
- no incluye `PUNITORIO` pendiente ni accesorios no marcados
- la condicion morable se define por atributo de catalogo, no por hardcodes de
  codigo de concepto
- el punitorio liquidado persiste como `composicion_obligacion`
  `PUNITORIO` dentro de la obligacion base
- si el pago no cubre el punitorio completo, queda `saldo_componente`
  pendiente en la composicion `PUNITORIO`

## Resolver de parámetros de mora

Módulo: `app/domain/financiero/resolver_mora.py`

Prioridad de resolución (mayor a menor):

1. **Regla por origen** — clave `"<TIPO_ORIGEN>:<id_origen>"` (ej. `"CONTRATO_ALQUILER:42"`)
2. **Regla por concepto** — clave `"<codigo_concepto>"` (ej. `"CANON_LOCATIVO"`)
3. **Default global** — `TASA_DIARIA_MORA_DEFAULT = 0.001`, `DIAS_GRACIA_MORA_DEFAULT = 5`

V1: no existen reglas en DB. El resolver siempre retorna el default global.

La interfaz acepta `reglas: dict[str, ResolucionMora]` para inyectar overrides
en tests o en futuras extensiones sin cambiar el contrato.

Todos los endpoints de cálculo de mora usan el mismo resolver:
- `GET /api/v1/financiero/deuda`
- `GET /api/v1/financiero/deuda/consolidado`
- `GET /api/v1/financiero/relaciones-generadoras/{id}/estado-cuenta`
- `GET /api/v1/financiero/personas/{id}/estado-cuenta`
- `POST /api/v1/financiero/personas/{id}/simular-pago`
- `POST /api/v1/financiero/pagos`

Los dias de gracia no se persisten ni modifican el estado `VENCIDA`. Solo
desplazan el inicio del calculo dinamico de mora.

## Lecturas afectadas

`GET /api/v1/financiero/deuda` agrega por obligacion:

- `dias_atraso`
- `mora_calculada`
- `tasa_diaria_mora`

`GET /api/v1/financiero/relaciones-generadoras/{id}/estado-cuenta` agrega por
obligacion los mismos campos y en resumen:

- `mora_calculada`

El saldo persistido no se modifica por la mora calculada.

## Desacople entre estado persistido y cálculo financiero

En Mora V1, fecha real y `fecha_corte` cumplen roles distintos y no deben
confundirse:

- El **estado de la obligacion** (`EMITIDA → VENCIDA`) se determina usando la
  fecha real del sistema. Solo `POST /api/v1/financiero/mora/generar` modifica
  ese estado, y lo hace contra `date.today()` en el momento de ejecucion.

- El **calculo de mora** (`dias_atraso`, `mora_calculada`) usa `fecha_corte`
  cuando se provee en la consulta. Si se omite, usa `date.today()`. El calculo
  aplica `dias_gracia_mora = 5` antes de empezar a acumular dias de atraso.

Esta separacion es intencional: permite simular escenarios a una fecha pasada o
futura sin alterar los estados persistidos en base de datos.

Ejemplo: una obligacion con `estado_obligacion = 'EMITIDA'` y
`fecha_vencimiento = 2026-04-01` puede mostrar mora calculada si se consulta
con `fecha_corte = 2026-04-10`, aunque `mora/generar` aun no haya corrido.

## Pendientes

- tasa y dias_gracia configurables por DB (tabla de reglas de mora) → hoy en `parametros_mora.py`
- cargar reglas del resolver desde DB cuando exista tabla persistida
- eventual generacion de cargos de mora si se define V2
- punitorios
- reversion/anulacion especifica de mora
