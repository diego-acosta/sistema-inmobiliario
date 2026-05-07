# DEV-API-FIN-001 - Dominio Financiero

## Estado del documento

- version: `1.3`
- estado: `IMPLEMENTADO PARCIAL / ALINEADO A BACKEND`
- ultima actualizacion: `2026-05-07`
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

### EMPRESA_PAGA_Y_RECUPERA

- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `PATCH /api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular`
- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`
- `GET /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`
- `PATCH /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}/anular`

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

## 9. EMPRESA_PAGA_Y_RECUPERA

Circuito para facturas de servicio donde la empresa paga al proveedor y luego
recupera total o parcialmente el importe contra personas responsables. No usa
`PAGO_EXTERNO_INFORMADO`, `SERVICIO_TRASLADADO` ni `EXPENSA_TRASLADADA`.

Side effects generales:

- el egreso proveedor crea `movimiento_tesoreria`;
- `liquidacion_recupero` crea deuda `SERVICIO_RECUPERADO`;
- la anulacion de `liquidacion_recupero` no toca tesoreria;
- `PAGO_EXTERNO_INFORMADO` no participa en `EMPRESA_PAGA_Y_RECUPERA`.

### POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor

Objetivo: registrar el pago real de la empresa al proveedor de una
`factura_servicio`.

Request:

```json
{
  "id_cuenta_financiera_origen": 1,
  "fecha_pago": "2026-05-20",
  "importe_pagado": 25000.00,
  "medio_pago": "TRANSFERENCIA",
  "referencia_comprobante": "TRX-001",
  "observaciones": "Pago a proveedor"
}
```

Response `201` resumida:

```json
{
  "ok": true,
  "data": {
    "resultado": "REGISTRADO",
    "id_egreso_proveedor_factura_servicio": 1,
    "id_factura_servicio": 10,
    "id_movimiento_tesoreria": 50,
    "estado_egreso": "REGISTRADO",
    "impacta_tesoreria": true,
    "crea_movimiento_financiero": false,
    "crea_obligacion_financiera": false
  }
}
```

Errores funcionales principales:

- `FACTURA_SERVICIO_NOT_FOUND`
- `FACTURA_SERVICIO_ANULADA`
- `CUENTA_FINANCIERA_NOT_FOUND`
- `CUENTA_FINANCIERA_INACTIVA`
- `IMPORTE_INVALIDO`
- `EGRESO_SUPERA_IMPORTE_FACTURA`
- `IDEMPOTENCY_PAYLOAD_CONFLICT`

Reglas:

- crea `movimiento_tesoreria` con tipo
  `EGRESO_PROVEEDOR_FACTURA_SERVICIO`;
- crea `egreso_proveedor_factura_servicio`;
- no crea `movimiento_financiero`;
- no crea `obligacion_financiera`;
- no crea recibo interno ni `PAGO_EXTERNO_INFORMADO`;
- admite idempotencia por `X-Op-Id`.

### GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor

Objetivo: consultar egresos proveedor de una factura y el estado derivado del
pago al proveedor.

Response resumida:

```json
{
  "ok": true,
  "data": {
    "id_factura_servicio": 10,
    "importe_total_factura": 25000.00,
    "total_egresado": 25000.00,
    "saldo_pendiente_pago_proveedor": 0.00,
    "estado_pago_proveedor": "PAGADA",
    "egresos": [
      {
        "id_egreso_proveedor_factura_servicio": 1,
        "id_movimiento_tesoreria": 50,
        "fecha_pago": "2026-05-20",
        "importe_pagado": 25000.00,
        "estado_egreso": "REGISTRADO"
      }
    ]
  }
}
```

Errores funcionales principales:

- `FACTURA_SERVICIO_NOT_FOUND`

Reglas:

- endpoint read-only;
- estados derivados: `SIN_PAGO`, `PAGO_PARCIAL`, `PAGADA`,
  `SOBREPAGADA`;
- solo egresos `REGISTRADO` y no eliminados suman al total egresado;
- no modifica `factura_servicio`.

### PATCH /api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular

Objetivo: anular un egreso proveedor registrado por error.

Request:

```json
{
  "motivo": "Egreso cargado por error"
}
```

Response resumida:

```json
{
  "ok": true,
  "data": {
    "resultado": "ANULADO",
    "id_egreso_proveedor_factura_servicio": 1,
    "id_movimiento_tesoreria": 50,
    "estado_egreso": "ANULADO",
    "estado_movimiento_tesoreria": "ANULADO",
    "ya_anulado": false,
    "motivo": "Egreso cargado por error"
  }
}
```

Errores funcionales principales:

- `EGRESO_PROVEEDOR_NOT_FOUND`
- `MOTIVO_REQUERIDO`
- `EGRESO_PROVEEDOR_CON_LIQUIDACION_RECUPERO`

Reglas:

- marca `egreso_proveedor_factura_servicio.estado_egreso = ANULADO`;
- marca `movimiento_tesoreria.estado = ANULADO`;
- no borra fisicamente;
- es idempotente si ya estaba anulado (`YA_ANULADO`);
- bloquea si el egreso esta usado por una `liquidacion_recupero` activa.

### POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero

Objetivo: generar deuda recuperable contra personas responsables a partir de
egresos proveedor registrados y disponibles.

Request:

```json
{
  "fecha_liquidacion": "2026-05-25",
  "fecha_vencimiento": "2026-06-10",
  "importe_total_recuperar": 20000.00,
  "responsables": [
    {
      "id_persona": 1,
      "porcentaje_responsabilidad": 100.00
    }
  ],
  "observaciones": "Recupero parcial"
}
```

Response `201` resumida:

```json
{
  "ok": true,
  "data": {
    "resultado": "EMITIDA",
    "id_liquidacion_recupero": 1,
    "codigo_liquidacion_recupero": "REC-20260525-ABC12345",
    "id_relacion_generadora": 10,
    "id_obligacion_financiera": 20,
    "estado_liquidacion": "EMITIDA",
    "importe_total_egresado_base": 25000.00,
    "importe_total_recuperar": 20000.00,
    "importe_absorbido_empresa": 5000.00,
    "crea_movimiento_tesoreria": false,
    "crea_pago_externo_informado": false
  }
}
```

Errores funcionales principales:

- `FACTURA_SERVICIO_NOT_FOUND`
- `FACTURA_SERVICIO_ANULADA`
- `RESPONSABLE_PERSONA_NOT_FOUND`
- `RESPONSABLES_REQUERIDOS`
- `RESPONSABLES_DUPLICADOS`
- `RESPONSABLES_PORCENTAJE_INVALIDO`
- `RESPONSABLES_SUMA_DISTINTA_100`
- `EGRESO_PROVEEDOR_REQUERIDO`
- `SIN_MONTO_EGRESADO_DISPONIBLE`
- `IMPORTE_RECUPERO_SUPERA_EGRESADO`
- `CONCEPTO_SERVICIO_RECUPERADO_NO_EXISTE`
- `IDEMPOTENCY_PAYLOAD_CONFLICT`

Reglas:

- requiere egresos proveedor `REGISTRADO`, no eliminados y no usados por otra
  liquidacion activa;
- crea `liquidacion_recupero`;
- crea vinculos `liquidacion_recupero_factura`,
  `liquidacion_recupero_egreso` y `liquidacion_recupero_responsable`;
- crea `relacion_generadora` de origen `LIQUIDACION_RECUPERO`;
- crea `obligacion_financiera` `EMITIDA`;
- crea composicion `SERVICIO_RECUPERADO`;
- crea `obligacion_obligado` con rol `RESPONSABLE_RECUPERO`;
- no crea `movimiento_tesoreria`;
- no crea `PAGO_EXTERNO_INFORMADO`;
- el cobro posterior usa el flujo normal de pago por persona.

### GET /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}

Objetivo: consultar el detalle formal de una `liquidacion_recupero`.

Response resumida:

```json
{
  "ok": true,
  "data": {
    "id_liquidacion_recupero": 1,
    "codigo_liquidacion_recupero": "REC-20260525-ABC12345",
    "estado_liquidacion": "EMITIDA",
    "id_relacion_generadora": 10,
    "id_obligacion_financiera": 20,
    "facturas": [],
    "egresos": [],
    "responsables": [],
    "obligacion": {
      "id_obligacion_financiera": 20,
      "estado_obligacion": "EMITIDA",
      "saldo_pendiente": 20000.00,
      "composiciones": [
        {
          "codigo_concepto_financiero": "SERVICIO_RECUPERADO",
          "importe_componente": 20000.00,
          "saldo_componente": 20000.00
        }
      ],
      "obligados": []
    }
  }
}
```

Errores funcionales principales:

- `LIQUIDACION_RECUPERO_NOT_FOUND`

Reglas:

- endpoint read-only;
- no crea movimientos;
- no modifica saldos;
- expone factura, egreso activo, responsables, relacion y obligacion asociada.

### GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero

Objetivo: listar liquidaciones de recupero asociadas a una
`factura_servicio`.

Response resumida:

```json
{
  "ok": true,
  "data": {
    "id_factura_servicio": 10,
    "items": [
      {
        "id_liquidacion_recupero": 1,
        "codigo_liquidacion_recupero": "REC-20260525-ABC12345",
        "estado_liquidacion": "EMITIDA",
        "fecha_liquidacion": "2026-05-25",
        "fecha_vencimiento": "2026-06-10",
        "importe_total_recuperar": 20000.00,
        "importe_absorbido_empresa": 5000.00,
        "id_obligacion_financiera": 20,
        "saldo_pendiente": 20000.00,
        "cantidad_responsables": 1
      }
    ],
    "total": 1
  }
}
```

Errores funcionales principales:

- `FACTURA_SERVICIO_NOT_FOUND`

Reglas:

- endpoint read-only;
- incluye liquidaciones activas y anuladas no eliminadas;
- no modifica saldos ni crea movimientos.

### PATCH /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}/anular

Objetivo: anular en forma conservadora una liquidacion de recupero sin
operaciones financieras activas.

Request:

```json
{
  "motivo": "Liquidacion cargada por error"
}
```

Response resumida:

```json
{
  "ok": true,
  "data": {
    "resultado": "ANULADA",
    "id_liquidacion_recupero": 1,
    "estado_liquidacion": "ANULADA",
    "id_relacion_generadora": 10,
    "estado_relacion_generadora": "CANCELADA",
    "id_obligacion_financiera": 20,
    "estado_obligacion": "ANULADA",
    "egresos_liberados": 1,
    "ya_anulada": false,
    "motivo": "Liquidacion cargada por error"
  }
}
```

Errores funcionales principales:

- `LIQUIDACION_RECUPERO_NOT_FOUND`
- `MOTIVO_REQUERIDO`
- `LIQUIDACION_RECUPERO_TIENE_OPERACIONES`

Reglas:

- si ya estaba anulada, devuelve `YA_ANULADA`;
- bloquea si existen aplicaciones financieras activas, movimientos
  financieros activos asociados a esas aplicaciones, punitorios activos u
  operaciones/composiciones posteriores;
- marca `liquidacion_recupero.estado_liquidacion = ANULADA`;
- marca `obligacion_financiera.estado_obligacion = ANULADA`;
- marca composiciones asociadas como `ANULADA`;
- marca `relacion_generadora.estado_relacion_generadora = CANCELADA`;
- libera egresos con `liquidacion_recupero_egreso = ANULADO` y `deleted_at`;
- no toca `movimiento_tesoreria`;
- no toca `egreso_proveedor_factura_servicio`;
- no toca `factura_servicio`;
- no revierte pagos normales.

---

## 10. Mora

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

## 11. Inbox de eventos

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

## 12. Funcionalidad no implementada

Sigue pendiente:

- activar/cancelar/finalizar `relacion_generadora`
- materializacion de obligaciones desde plan externo
- reversion de imputaciones
- generacion automatica desde evento `factura_servicio_registrada`
- resolucion general de obligado financiero fuera de los flujos V1
  implementados
- outbox financiero en estos writes
- idempotencia completa por `X-Op-Id` en todos los writes del dominio

### IMPUESTO_TRASLADADO V1

Estado: `DISENO V1 DOCUMENTADO / NO IMPLEMENTADO`.

El diseno V1 queda documentado en
`backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-021-impuestos-trasladados.md`.

Reglas de contrato futuro:

- crear entidad propia `comprobante_impuesto`;
- no usar `factura_servicio` para impuestos;
- no crear `IMPUESTO_RECUPERADO` en V1;
- usar `IMPUESTO_TRASLADADO` para deuda fiscal trasladada;
- mantener `IMPUESTO_TRASLADADO.aplica_punitorio = false` salvo decision
  posterior;
- `comprobante_impuesto` no genera deuda automaticamente;
- la modalidad define el flujo habilitado.

Modalidades futuras:

- `EMPRESA_ASUME`: registra egreso de tesoreria y no genera obligacion al
  responsable.
- `DIRECTO_RESPONSABLE`: puede materializar obligacion `IMPUESTO_TRASLADADO`;
  el pago informado es externo, no caja/tesoreria, y requiere unico responsable
  100%.
- `EMPRESA_PAGA_Y_RECUPERA`: registra egreso de tesoreria, luego liquida
  recupero como obligacion `IMPUESTO_TRASLADADO` y el responsable paga a la
  empresa por flujo normal.

Endpoints futuros a definir, no implementados:

- `POST /api/v1/financiero/comprobantes-impuesto`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}`
- `GET /api/v1/financiero/comprobantes-impuesto`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/materializar`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/pago-externo`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `PATCH /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion}/anular`
