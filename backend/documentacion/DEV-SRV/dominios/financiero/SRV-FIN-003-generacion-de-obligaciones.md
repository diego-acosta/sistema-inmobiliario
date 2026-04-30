# SRV-FIN-003 - Generacion de obligaciones

## Objetivo

Crear obligaciones financieras dentro de una `relacion_generadora`, con una o mas composiciones economicas basadas en `concepto_financiero`.

## Estado

- estado: `IMPLEMENTADO PARCIAL`
- endpoint implementado: `POST /api/v1/financiero/obligaciones`
- no modifica SQL
- no usa `tipo_obligacion`

## Alcance implementado

Este servicio cubre actualmente:

- generacion manual de una obligacion financiera
- validacion de existencia de `relacion_generadora`
- validacion de existencia de cada `concepto_financiero`
- creacion atomica de `obligacion_financiera`
- creacion atomica de `composicion_obligacion`
- calculo de `importe_total` como suma de composiciones recibidas
- estado inicial `PROYECTADA`

No cubre actualmente:

- activacion de relacion generadora
- materializacion desde plan externo
- generacion automatica por contrato, venta o factura_servicio
- resolucion de obligado financiero
- outbox financiero
- idempotencia completa por `X-Op-Id`

## Entidades

- `relacion_generadora`
- `obligacion_financiera`
- `composicion_obligacion`
- `concepto_financiero`

## Entrada implementada

```json
{
  "id_relacion_generadora": 1,
  "fecha_vencimiento": "2026-12-31",
  "composiciones": [
    {
      "codigo_concepto_financiero": "CANON_LOCATIVO",
      "importe_componente": 100000.00
    }
  ]
}
```

Reglas de request:

- `id_relacion_generadora` debe ser mayor a cero
- `fecha_vencimiento` es obligatoria
- `composiciones` debe tener al menos un item
- cada `importe_componente` debe ser mayor a cero

## Flujo implementado

1. validar composiciones requeridas
2. validar existencia de `relacion_generadora`
3. validar cada `concepto_financiero` por codigo
4. sumar importes de composiciones
5. construir `obligacion_financiera`
6. construir composiciones con `orden_composicion`
7. insertar obligacion y composiciones en una transaccion
8. devolver obligacion con composiciones

## Reglas de negocio

- Toda obligacion creada por backend pertenece a una `relacion_generadora`.
- Toda obligacion creada por backend tiene al menos una `composicion_obligacion`.
- Toda composicion referencia un `concepto_financiero` existente.
- La naturaleza economica no se guarda en `tipo_obligacion`; se interpreta desde `concepto_financiero`.
- `saldo_pendiente` inicial se persiste igual a `importe_total`.
- `saldo_componente` inicial se persiste igual a `importe_componente`.

## Resultado implementado

```json
{
  "ok": true,
  "data": {
    "id_obligacion_financiera": 10,
    "id_relacion_generadora": 1,
    "fecha_emision": "2026-04-30",
    "fecha_vencimiento": "2026-12-31",
    "importe_total": 100000.00,
    "saldo_pendiente": 100000.00,
    "estado_obligacion": "PROYECTADA",
    "composiciones": [
      {
        "id_composicion_obligacion": 20,
        "orden_composicion": 1,
        "estado_composicion_obligacion": "ACTIVA",
        "importe_componente": 100000.00,
        "saldo_componente": 100000.00,
        "moneda_componente": "ARS",
        "codigo_concepto_financiero": "CANON_LOCATIVO"
      }
    ]
  }
}
```

## Errores implementados

- `404 NOT_FOUND` si la relacion generadora no existe
- `404 NOT_FOUND` si un concepto financiero no existe
- `400 APPLICATION_ERROR` para validaciones de aplicacion no especificas
- `422` para validaciones Pydantic del request
- `500 INTERNAL_ERROR` para errores no controlados

## Pendientes

- duplicidad funcional por periodo/concepto/relacion
- generacion masiva
- materializacion desde plan de origen
- generacion desde `factura_servicio`
- resolucion y persistencia de `obligacion_obligado`
