# DEV-API-FIN-001 - Dominio Financiero

## Estado del documento

- version: `1.2`
- estado: `IMPLEMENTADO PARCIAL / ALINEADO A BACKEND`
- ultima actualizacion: `2026-04-30`
- fuente: backend real + SQL vigente + tests financieros

Este documento describe los endpoints financieros actualmente implementados en backend. No documenta como operable funcionalidad que siga pendiente.

---

## 1. Endpoints implementados

### Relaciones generadoras

- `POST /api/v1/financiero/relaciones-generadoras`
- `GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}`
- `GET /api/v1/financiero/relaciones-generadoras`

### Conceptos financieros

- `GET /api/v1/financiero/conceptos-financieros`

### Obligaciones

- `POST /api/v1/financiero/obligaciones`
- `GET /api/v1/financiero/obligaciones/{id_obligacion_financiera}`

### Imputaciones

- `POST /api/v1/financiero/imputaciones`

### Deuda consolidada

- `GET /api/v1/financiero/deuda`

### Estado de cuenta

- `GET /api/v1/financiero/estado-cuenta`

### Mora

- `POST /api/v1/financiero/mora/generar`

### Inbox de eventos

- `POST /api/v1/financiero/inbox`

---

## 2. Convencion de respuesta

Respuesta exitosa:

```json
{
  "ok": true,
  "data": {}
}
```

Respuesta de error:

```json
{
  "ok": false,
  "error_code": "CODIGO",
  "error_message": "Mensaje",
  "details": {
    "errors": []
  }
}
```

Codigos usados por el backend actual:

- `NOT_FOUND`
- `APPLICATION_ERROR`
- `MONTO_EXCEDE_SALDO`
- `ESTADO_INVALIDO`
- `FECHA_RANGO_INVALIDO`
- `INTERNAL_ERROR`

---

## 3. Relaciones generadoras

### POST /api/v1/financiero/relaciones-generadoras

Crea una relacion generadora.

Request:

```json
{
  "tipo_origen": "CONTRATO_ALQUILER",
  "id_origen": 42,
  "descripcion": "Relacion generadora"
}
```

Valores operativos implementados:

- `VENTA`
- `CONTRATO_ALQUILER`

Response `201`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "descripcion": "Relacion generadora",
    "estado_relacion_generadora": "BORRADOR",
    "fecha_alta": "2026-04-30T10:00:00"
  }
}
```

### GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}

Consulta una relacion generadora por ID.

### GET /api/v1/financiero/relaciones-generadoras

Filtros:

- `tipo_origen`
- `id_origen`
- `vigente`
- `limit`
- `offset`

---

## 4. Conceptos financieros

### GET /api/v1/financiero/conceptos-financieros

Lista conceptos financieros.

Filtros:

- `estado`
- `limit`
- `offset`

Response:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_concepto_financiero": 1,
        "codigo_concepto_financiero": "PUNITORIO",
        "nombre_concepto_financiero": "Punitorio",
        "descripcion_concepto_financiero": "Cargo punitorio por incumplimiento.",
        "tipo_concepto_financiero": "MORA",
        "naturaleza_concepto": "DEBITO",
        "estado_concepto_financiero": "ACTIVO"
      }
    ],
    "total": 1
  }
}
```

---

## 5. Obligaciones

### POST /api/v1/financiero/obligaciones

Crea una obligacion financiera con composiciones.

Request:

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

Reglas:

- `id_relacion_generadora` debe existir
- debe existir al menos una composicion
- cada composicion debe referenciar un `concepto_financiero` existente
- no se usa `tipo_obligacion`
- estado inicial: `PROYECTADA`

Response `201`:

```json
{
  "ok": true,
  "data": {
    "id_obligacion_financiera": 10,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_relacion_generadora": 1,
    "codigo_obligacion_financiera": null,
    "descripcion_operativa": null,
    "fecha_emision": "2026-04-30",
    "fecha_vencimiento": "2026-12-31",
    "periodo_desde": null,
    "periodo_hasta": null,
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

### GET /api/v1/financiero/obligaciones/{id_obligacion_financiera}

Consulta una obligacion con sus composiciones.

---

## 6. Imputaciones

### POST /api/v1/financiero/imputaciones

Imputa un monto a una obligacion financiera.

Request:

```json
{
  "id_obligacion_financiera": 10,
  "monto": 5000.00
}
```

Reglas:

- la obligacion debe existir
- el monto debe ser mayor a cero
- el monto no puede exceder `saldo_pendiente`
- el estado debe aceptar imputacion
- la imputacion se distribuye contra composiciones activas con saldo
- la DB actualiza saldos por triggers
- el backend actualiza estado luego de leer el saldo resultante

Response `201`:

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

---

## 7. Deuda consolidada

### GET /api/v1/financiero/deuda

Consulta obligaciones financieras con sus composiciones. Es read-only.

Filtros:

- `id_relacion_generadora`
- `estado_obligacion`
- `fecha_vencimiento_desde`
- `fecha_vencimiento_hasta`
- `con_saldo`
- `limit`
- `offset`

Reglas:

- lista obligaciones no dadas de baja
- si `con_saldo=true`, solo incluye `saldo_pendiente > 0`
- no recalcula saldos
- muestra composiciones activas asociadas a cada obligacion
- valida que `fecha_vencimiento_hasta >= fecha_vencimiento_desde`

Response:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_obligacion_financiera": 10,
        "id_relacion_generadora": 1,
        "estado_obligacion": "PROYECTADA",
        "fecha_vencimiento": "2026-12-31",
        "importe_total": 100000.00,
        "saldo_pendiente": 100000.00,
        "composiciones": [
          {
            "id_composicion_obligacion": 20,
            "codigo_concepto_financiero": "CANON_LOCATIVO",
            "importe_componente": 100000.00,
            "saldo_componente": 100000.00
          }
        ]
      }
    ],
    "total": 1
  }
}
```

---

## 8. Estado de cuenta

### GET /api/v1/financiero/estado-cuenta

Devuelve el estado de cuenta financiero consolidado de una relacion generadora.

Query params:

- `id_relacion_generadora` int, obligatorio
- `incluir_canceladas` bool, opcional, default `false`
- `fecha_desde` date, opcional
- `fecha_hasta` date, opcional

Response:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "resumen": {
      "importe_total": 100000.00,
      "saldo_pendiente": 60000.00,
      "importe_cancelado": 40000.00,
      "cantidad_obligaciones": 1,
      "cantidad_vencidas": 0
    },
    "obligaciones": [
      {
        "id_obligacion_financiera": 10,
        "estado_obligacion": "PARCIALMENTE_CANCELADA",
        "fecha_emision": "2026-04-30",
        "fecha_vencimiento": "2026-12-31",
        "importe_total": 100000.00,
        "saldo_pendiente": 60000.00,
        "composiciones": [],
        "aplicaciones": []
      }
    ]
  }
}
```

Reglas:

- no recalcula saldos en backend
- usa datos persistidos en DB
- excluye `CANCELADA`, `ANULADA`, `REEMPLAZADA` por default
- `incluir_canceladas=true` permite verlas
- filtra por `fecha_vencimiento` si se envian fechas
- incluye composiciones reales
- incluye aplicaciones reales
- endpoint read-only

Notas:

- `importe_cancelado` se obtiene de campo persistido; no es una suma dinamica en backend.
- `cantidad_vencidas` usa la fecha actual del sistema.

---

## 9. Mora

### POST /api/v1/financiero/mora/generar

Genera obligaciones de mora diaria para obligaciones vencidas con saldo pendiente.

Request:

```json
{
  "fecha_proceso": "2026-05-01"
}
```

`fecha_proceso` es opcional. Si no se informa, el backend usa la fecha actual.

Response:

```json
{
  "ok": true,
  "data": {
    "fecha_proceso": "2026-05-01",
    "procesadas": 10,
    "generadas": 7
  }
}
```

Reglas implementadas:

- selecciona obligaciones con `fecha_vencimiento < fecha_proceso`
- requiere `saldo_pendiente > 0`
- requiere `deleted_at IS NULL`
- excluye estados `ANULADA`, `REEMPLAZADA`, `CANCELADA`
- excluye obligaciones generadas por mora automatica
- no crea `INTERES_MORA`
- no crea nueva obligacion por mora
- el punitorio persistido V1 se liquida solo al registrar pago y usa
  `PUNITORIO` como `composicion_obligacion` de la obligacion base

Limitacion:

- no existe FK SQL entre obligacion de mora y obligacion base
- no existe constraint unica SQL para obligacion base + fecha de proceso

---

## 10. Inbox de eventos

### POST /api/v1/financiero/inbox

Procesa eventos externos soportados por el dominio financiero.

Request:

```json
{
  "event_type": "contrato_alquiler_activado",
  "payload": {
    "id_contrato_alquiler": 42
  }
}
```

Eventos soportados:

- `venta_confirmada`
  - payload: `{"id_venta": int}`
- `contrato_alquiler_activado`
  - payload: `{"id_contrato_alquiler": int}`

Response:

- `204 No Content`

Notas:

- procesamiento sincronico
- el endpoint existe para invocacion HTTP manual
- el worker interno `outbox_to_inbox_worker` no utiliza este endpoint
- el procesamiento automatico usa `InboxEventDispatcher` directo, sin HTTP
- no hay confirmacion de exito del handler en la respuesta HTTP

---

## 11. Funcionalidad no implementada

Sigue pendiente:

- activar/cancelar/finalizar `relacion_generadora`
- materializacion de obligaciones desde plan externo
- endpoint autonomo de pagos
- reversion de imputaciones
- obligados financieros
- generacion desde `factura_servicio`
- resolucion de obligado financiero
- outbox financiero en estos writes
- idempotencia completa por `X-Op-Id`
