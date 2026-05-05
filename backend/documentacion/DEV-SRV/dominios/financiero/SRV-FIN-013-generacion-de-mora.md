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
- administracion API de politicas variables de tasa
- administracion API de dias de gracia
- refinanciacion
- reversion especifica de mora

## Decision V1 - Mora dinamica de lectura no persistida

En la version actual, la mora dinamica de lectura no genera obligaciones
financieras accesorias ni composiciones `INTERES_MORA`.

El proceso de mora V1 solo realiza:

- marcado idempotente de obligaciones `EMITIDA -> VENCIDA`
- cálculo dinámico de `mora_calculada` en consultas de deuda y estado de cuenta
- exposición de `dias_atraso` y `tasa_diaria_mora`

La mora calculada por consultas o por `mora/generar` no modifica:

- `importe_total`
- `saldo_pendiente`
- `composicion_obligacion`
- `obligacion_obligado`

Esto no contradice la liquidacion de `PUNITORIO` al registrar pagos:
`PUNITORIO` es un cargo persistido distinto, creado solo por
`POST /api/v1/financiero/pagos` cuando corresponde liquidar mora.

## Limitaciones V1

- `tasa_diaria` y `dias_gracia` se persisten en `parametro_punitorio`, pero no
  existe endpoint administrativo para gestionar esos parametros.
- La resolucion implementada contempla alcance `GLOBAL`, `CONCEPTO` y
  `RELACION_GENERADORA`; si no hay parametro vigente, usa defaults tecnicos.
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

La mora calculada por este proceso no se persiste como deuda ni como
composicion. La persistencia de cargo por mora en pagos pertenece a
`POST /api/v1/financiero/pagos` y se modela como `PUNITORIO`.

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

El `PUNITORIO` liquidado por pago si modifica el estado persistido de la
obligacion mediante `composicion_obligacion` y triggers de saldo, queda trazado
en `liquidacion_punitorio` y puede revertirse solo bajo las reglas de reversion
V1 de pago agrupado.

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

Modulo base: `app/domain/financiero/resolver_mora.py`
Resolucion persistida V1: tabla `parametro_punitorio`, resuelta desde el
repository financiero.

Prioridad de resolución (mayor a menor):

1. **RELACION_GENERADORA** — `parametro_punitorio.id_relacion_generadora`
2. **CONCEPTO** — `parametro_punitorio.id_concepto_financiero`
3. **GLOBAL** — fila vigente sin relacion ni concepto
4. **Default tecnico** — `TASA_DIARIA_MORA_DEFAULT = 0.001`,
   `DIAS_GRACIA_MORA_DEFAULT = 5`

Solo aplican filas con `deleted_at IS NULL`, `estado_parametro = ACTIVO` y
vigencia que cubra la fecha de referencia (`fecha_desde <= fecha_referencia` y
`fecha_hasta IS NULL OR fecha_hasta >= fecha_referencia`).

El seed V1 crea un parametro `GLOBAL` equivalente al default tecnico. El
fallback tecnico permanece para instalaciones sin tabla o sin filas vigentes.

Todos los endpoints de cálculo de mora usan el mismo resolver:
- `GET /api/v1/financiero/deuda`
- `GET /api/v1/financiero/deuda/consolidado`
- `GET /api/v1/financiero/relaciones-generadoras/{id}/estado-cuenta`
- `GET /api/v1/financiero/personas/{id}/estado-cuenta`
- `POST /api/v1/financiero/personas/{id}/simular-pago`
- `POST /api/v1/financiero/pagos`

Los dias de gracia se resuelven como parametro de calculo y no modifican el
estado `VENCIDA`. Solo desplazan el inicio del calculo dinamico de mora.

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
  aplica `dias_gracia` resuelto por `parametro_punitorio` antes de empezar a
  acumular dias de atraso.

Esta separacion es intencional: permite simular escenarios a una fecha pasada o
futura sin alterar los estados persistidos en base de datos.

Ejemplo: una obligacion con `estado_obligacion = 'EMITIDA'` y
`fecha_vencimiento = 2026-04-01` puede mostrar mora calculada si se consulta
con `fecha_corte = 2026-04-10`, aunque `mora/generar` aun no haya corrido.

## Limitaciones / evolucion

- administrar `parametro_punitorio` por API o interfaz operativa
- validar no solapamiento de vigencias activas por alcance antes de exponer
  mantenimiento de parametros
- eventual generacion de cargos de mora si se define V2
- punitorios
- reversion/anulacion especifica de mora
