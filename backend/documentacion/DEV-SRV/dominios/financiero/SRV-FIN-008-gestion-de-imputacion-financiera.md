# SRV-FIN-008 - Gestion de imputacion financiera

## Objetivo

Aplicar un monto sobre una obligacion financiera, distribuyendolo contra sus composiciones segun prioridad de conceptos, y dejando que la base de datos actualice saldos mediante triggers.

## Estado

- estado: `IMPLEMENTADO PARCIAL`
- endpoint implementado: `POST /api/v1/financiero/imputaciones`
- no modifica SQL
- no recalcula saldo en backend como fuente primaria

## Alcance implementado

Este servicio cubre actualmente:

- imputacion manual de un monto sobre una obligacion
- creacion de `movimiento_financiero`
- creacion de una o mas `aplicacion_financiera`
- distribucion contra composiciones activas con saldo
- uso de `orden_aplicacion`
- actualizacion de estado de obligacion despues de aplicar

No cubre actualmente:

- reversion de imputaciones
- reaplicacion de pagos
- endpoint autonomo de movimientos/pagos
- imputacion distribuida entre varias obligaciones
- estado persistido de aplicacion
- outbox financiero

## Entidades

- `obligacion_financiera`
- `composicion_obligacion`
- `concepto_financiero`
- `movimiento_financiero`
- `aplicacion_financiera`

## Entrada implementada

```json
{
  "id_obligacion_financiera": 10,
  "monto": 5000.00
}
```

Reglas de request:

- `id_obligacion_financiera` debe ser mayor a cero
- `monto` debe ser mayor a cero

## Estados que aceptan imputacion

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `VENCIDA`

Estados que no aceptan imputacion:

- `CANCELADA`
- `ANULADA`
- `REEMPLAZADA`

## Politica de distribucion implementada

La imputacion busca composiciones activas con saldo y las ordena por prioridad legal implementada.

Prioridad:

1. `PUNITORIO`
2. `CARGO_ADMINISTRATIVO`
3. `INTERES_FINANCIERO`
4. `AJUSTE_INDEXACION`
5. `CAPITAL_VENTA`
6. `ANTICIPO_VENTA`
7. `CANON_LOCATIVO`
8. `EXPENSA_TRASLADADA`
9. `SERVICIO_TRASLADADO`
10. `IMPUESTO_TRASLADADO`
11. otros conceptos por `orden_composicion`

`INTERES_MORA` puede existir en catalogos heredados, pero no se usa como
concepto activo de mora persistida en V1.

Si el monto alcanza a mas de una composicion, el backend crea multiples filas en `aplicacion_financiera`.

`orden_aplicacion` se asigna segun el orden real de distribucion.

## Flujo implementado

1. cargar obligacion
2. validar existencia y baja logica
3. validar monto positivo
4. validar estado de obligacion
5. validar que el monto no exceda `saldo_pendiente`
6. cargar composiciones activas con `saldo_componente > 0`
7. ordenar composiciones por prioridad de concepto y `orden_composicion`
8. construir lineas de aplicacion
9. insertar `movimiento_financiero`
10. insertar `aplicacion_financiera`
11. la DB actualiza saldos por triggers
12. el backend actualiza `estado_obligacion` segun saldo resultante

## Actualizacion de saldo y estado

La DB actualiza:

- `composicion_obligacion.saldo_componente`
- `obligacion_financiera.saldo_pendiente`

El backend no recalcula esos saldos.

Luego del insert de aplicaciones, el backend ejecuta:

- `CANCELADA` si `saldo_pendiente = 0`
- `PARCIALMENTE_CANCELADA` si `saldo_pendiente < importe_total`
- no modifica `ANULADA` ni `REEMPLAZADA`

## Resultado implementado

```json
{
  "ok": true,
  "data": {
    "id_obligacion_financiera": 10,
    "id_movimiento_financiero": 30,
    "monto_aplicado": 5000.00,
    "aplicaciones": [
      {
        "id_aplicacion_financiera": 40,
        "id_composicion_obligacion": 20,
        "importe_aplicado": 5000.00,
        "orden_aplicacion": 1
      }
    ]
  }
}
```

## Errores implementados

- `404 NOT_FOUND` si la obligacion no existe
- `400 MONTO_EXCEDE_SALDO` si el monto excede el saldo pendiente
- `400 ESTADO_INVALIDO` si el estado no acepta imputacion
- `400 APPLICATION_ERROR` para validaciones de aplicacion no especificas
- `422` para validaciones Pydantic del request
- `500 INTERNAL_ERROR` para errores no controlados

## Pendientes

- reversion
- reaplicacion
- imputacion multi-obligacion
- idempotencia completa por `X-Op-Id`
- outbox financiero
