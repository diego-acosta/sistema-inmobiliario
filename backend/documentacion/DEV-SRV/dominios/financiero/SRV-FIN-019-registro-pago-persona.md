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
  "uid_pago_grupo": "1b42c6a1-41a3-49f9-94d7-4a472f76922b",
  "codigo_pago_grupo": "PAGO-20260520-1B42C6A1",
  "monto_ingresado": 50000.00,
  "monto_aplicado": 45000.00,
  "remanente": 5000.00,
  "obligaciones_pagadas": [
    {
      "id_obligacion_financiera": 10,
      "id_movimiento_financiero": 5,
      "uid_pago_grupo": "1b42c6a1-41a3-49f9-94d7-4a472f76922b",
      "codigo_pago_grupo": "PAGO-20260520-1B42C6A1",
      "monto_aplicado": 20000.00,
      "estado_resultante": "CANCELADA"
    }
  ]
}
```

- `monto_aplicado`: suma de importes efectivamente aplicados a `saldo_pendiente`
- `remanente`: monto no consumido (incluyendo mora si el monto no alcanzó a cubrir saldo+mora)
- `obligaciones_pagadas`: una entrada por obligación con saldo reducido

El resultado incluye `uid_pago_grupo` y `codigo_pago_grupo` a nivel operación
y en cada obligación pagada. Ambos identifican la operación de pago común que
agrupa los movimientos generados.

---

## Persistencia

Por cada obligación cubierta:

1. `movimiento_financiero` (tipo=PAGO, signo=CREDITO, estado=APLICADO)
2. `aplicacion_financiera` por cada `composicion_obligacion` afectada
3. Trigger de DB actualiza `saldo_pendiente`
4. UPDATE de `estado_obligacion` (→ CANCELADA o PARCIALMENTE_CANCELADA)

Todo en una única transacción. Rollback total si alguna escritura falla.

---

Todos los `movimiento_financiero` creados por el mismo request comparten
`uid_pago_grupo` y `codigo_pago_grupo`. Esto aplica también cuando el pago
afecta una sola obligación. El agrupador no reemplaza al movimiento por
obligación ni cambia las `aplicacion_financiera`.

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

Si la operacion original asociada al `X-Op-Id` ya fue revertida, el reintento
no recrea el pago ni vuelve a liquidar punitorios: devuelve `PAGO_YA_REVERTIDO`
con HTTP 409.

El comportamiento mantiene el modelo V1 de un `movimiento_financiero` por
obligación cubierta. Por eso un mismo `op_id` puede agrupar múltiples
movimientos de pago cuando un pago cubre más de una obligación.

Los movimientos de una misma operación comparten `uid_pago_grupo` y
`codigo_pago_grupo`; un reintento idempotente devuelve esos mismos valores.

Para reconstruir el resultado idempotente, `movimiento_financiero.observaciones`
guarda un resumen técnico de la operación. No representa una imputación ni crea
conceptos financieros adicionales.

Sin `X-Op-Id`, el endpoint mantiene el comportamiento histórico: cada llamada
válida puede registrar un nuevo pago.

---

## Mora / punitorio

Si corresponde mora liquidable al momento del pago, se crea o incrementa una
`composicion_obligacion` `PUNITORIO` dentro de la obligacion base antes de
imputar. `PUNITORIO` es la decision arquitectonica V1 para persistir el cargo
por mora en esta implementacion. No se crea nueva `obligacion_financiera` ni
composicion `INTERES_MORA` separada.

La base morable se obtiene desde composiciones activas cuyo
`concepto_financiero.aplica_punitorio = true`. `PUNITORIO` y accesorios no
marcados no integran esa base.

La tasa diaria y los dias de gracia se resuelven desde `parametro_punitorio`
con prioridad `RELACION_GENERADORA` > `CONCEPTO` > `GLOBAL` > default tecnico.
Solo aplican parametros `ACTIVO`, no eliminados y vigentes para `fecha_pago`.

---

## Regla funcional: punitorio por pago

Estado: `IMPLEMENTADO`.

Cuando el pago liquida mora, el cargo se registra como `PUNITORIO` dentro de la
obligacion base. Esta es la forma persistente implementada en V1; no se usa
`INTERES_MORA` como componente separado.

Cada liquidacion positiva de `PUNITORIO` registra ademas una fila en
`liquidacion_punitorio`. Esta tabla es trazabilidad de la liquidacion, no una
obligacion nueva ni una aplicacion. La fila queda vinculada a la obligacion, a
la composicion `PUNITORIO` afectada y al agrupador de pago
`uid_pago_grupo`/`codigo_pago_grupo`.

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
- la trazabilidad de cada liquidacion positiva se persiste en
  `liquidacion_punitorio` con `estado_liquidacion = ACTIVA`
- un reintento idempotente por `X-Op-Id` no duplica composiciones, movimientos,
  aplicaciones ni liquidaciones de punitorio
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

- el cargo por mora se persiste como `PUNITORIO`; `INTERES_MORA` no se usa como
  componente separado en V1
- no soporta distribución proporcional entre co-obligados
- un único `movimiento_financiero` por obligación (no uno global por pago)

---

El agrupador común no constituye movimiento global; es trazabilidad común sobre
los movimientos por obligación.

## Referencias

- `MODELO-FINANCIERO-FIN` sección 12
- `SRV-FIN-018-simulacion-pago-persona`
- `SRV-FIN-013-generacion-de-mora`

## Consulta de pagos agrupados

Se agregan endpoints de solo lectura:
- `GET /api/v1/financiero/personas/{id_persona}/pagos`
- `GET /api/v1/financiero/pagos/{codigo_pago_grupo}`
- `GET /api/v1/financiero/pagos/{codigo_pago_grupo}/recibo`

Reglas: agrupan por `uid_pago_grupo` + `codigo_pago_grupo`, consideran solo movimientos `PAGO` no eliminados y detalle desde `aplicacion_financiera`.

Cuando todos los movimientos `PAGO` del grupo estan `ANULADO`, la consulta
`GET /api/v1/financiero/pagos/{codigo_pago_grupo}` informa
`estado_pago_grupo = ANULADO`.

### Constancia interna de pago agrupado

`GET /api/v1/financiero/pagos/{codigo_pago_grupo}/recibo` devuelve una vista de
consulta para presentar una constancia interna de pago agrupado. No es un
recibo oficial ni un comprobante fiscal.

Alcance:

- es read-only
- se basa en `movimiento_financiero`, `aplicacion_financiera`,
  `codigo_pago_grupo` y `uid_pago_grupo`
- no crea entidad persistida de recibo o comprobante
- no genera comprobante oficial
- no reserva numeracion fiscal
- no tiene validez fiscal
- no modifica pagos, saldos, movimientos ni aplicaciones
- usa `codigo_pago_grupo` como identificador de consulta
- devuelve `404` si no existen movimientos `PAGO` no eliminados para el codigo

Contenido:

- cabecera: `codigo_pago_grupo`, `uid_pago_grupo`, `fecha_pago`, persona,
  `monto_total`, `monto_aplicado`, `remanente`
- detalle desde `aplicacion_financiera`: movimiento, obligacion, periodo,
  concepto financiero, importe aplicado y estado resultante
- `totales_por_concepto`
- `estado_recibo = BORRADOR/CONSULTA`

El diseño queda preparado para incorporar en una version futura una entidad
formal, por ejemplo `comprobante_pago` o `comprobante_financiero`, con
numeracion, estado fiscal, anulacion, emision PDF e integracion fiscal si
corresponde.

## Reversion V1 de pago agrupado

Endpoint: `POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir`.

Request:

```json
{
  "motivo": "texto obligatorio"
}
```

Alcance:

- revierte siempre la operacion completa identificada por `codigo_pago_grupo`
- no permite revertir aplicaciones sueltas
- no borra fisicamente movimientos
- marca los movimientos `PAGO` del grupo como `ANULADO`
- soft-deletea las `aplicacion_financiera` del grupo para que dejen de contar
  en saldos
- anula las `liquidacion_punitorio` activas asociadas al grupo
- reduce la composicion `PUNITORIO` solamente por el importe liquidado por esas
  liquidaciones anuladas
- no toca liquidaciones ni punitorios de otros pagos
- recalcula saldos mediante los triggers vigentes de aplicacion/composicion
- recalcula `estado_obligacion` despues de restaurar saldos
- registra el motivo de reversion en `observaciones` cuando hay campo
  disponible

Restriccion V1:

- solo se permite revertir pagos sin operaciones posteriores activas sobre las
  obligaciones o composiciones afectadas por el grupo
- se bloquea la reversion si existen movimientos `PAGO`, aplicaciones activas,
  composiciones activas creadas/modificadas o `liquidacion_punitorio` `ACTIVA`
  posteriores al pago agrupado
- el bloqueo incluye operaciones posteriores sin `codigo_pago_grupo`, por
  ejemplo `BONIFICACION_INDEXACION`
- el bloqueo devuelve `PAGO_TIENE_OPERACIONES_POSTERIORES` con HTTP 409
- V1 no recomputa historia de punitorio ni recalcula tramos moratorios
- si el pago ya fue revertido, la repeticion de la reversion conserva el
  comportamiento idempotente y devuelve estado `YA_ANULADO`

Estados resultantes de obligacion:

- `saldo_pendiente = 0` -> `CANCELADA`
- `saldo_pendiente > 0` e `importe_cancelado_acumulado > 0` ->
  `PARCIALMENTE_CANCELADA`
- `saldo_pendiente > 0` e `importe_cancelado_acumulado = 0` -> `VENCIDA` si
  `fecha_vencimiento < CURRENT_DATE`, si no `EMITIDA`

La reversion V1 es operativa/financiera interna. No genera comprobante fiscal,
no reserva numeracion fiscal, no anula comprobantes oficiales y no modifica
cronogramas ni generacion de obligaciones.
