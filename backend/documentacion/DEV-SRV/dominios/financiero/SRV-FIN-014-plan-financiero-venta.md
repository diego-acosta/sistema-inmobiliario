# SRV-FIN-014 - Plan financiero de venta

## Objetivo

Definir como una `venta` confirmada del dominio `comercial` debe transformarse en un plan de obligaciones financieras, sin trasladar ownership comercial al dominio financiero y sin generar obligaciones desde `confirm_venta_service`.

Este documento define la regla V1 implementada para materializar obligaciones
financieras de venta desde condiciones comerciales persistidas.

---

## Diagnostico actual

El flujo comercial implementado actualmente es:

1. Una `reserva_venta` confirmada puede generar una `venta`.
2. La `venta` nace en estado `borrador`.
3. Las condiciones comerciales basicas se definen sobre:
   - `venta.monto_total`
   - `venta_objeto_inmobiliario.precio_asignado`
4. La venta solo puede confirmarse si:
   - `monto_total` existe y es mayor a cero
   - todos los objetos tienen `precio_asignado` mayor a cero
   - la suma de `precio_asignado` coincide exactamente con `monto_total`
5. Al confirmar la venta, comercial emite `venta_confirmada` en `outbox_event`.
6. Financiero crea `relacion_generadora` desde `venta_confirmada` con:
   - `tipo_origen = 'venta'`
   - `id_origen = id_venta`
7. Financiero resuelve un comprador canonico desde `relacion_persona_rol`
   y `rol_participacion` usando `codigo_rol = COMPRADOR`.
8. Si existe exactamente un comprador, financiero materializa
   `obligacion_obligado` para la obligacion `CAPITAL_VENTA`.

La generacion automatica V1 desde venta confirmada materializa una deuda de venta
segun el plan comercial persistido: `CONTADO`, `ANTICIPO_Y_SALDO` o
`CUOTAS_FIJAS`. En todos los casos usa la misma relacion generadora de venta,
composiciones financieras y obligado financiero comprador.

---

## Datos disponibles hoy

### En comercial

Datos disponibles para construir un plan minimo:

- `venta.id_venta`
- `venta.fecha_venta`
- `venta.estado_venta`
- `venta.monto_total`
- `venta.tipo_plan_financiero`
- `venta.moneda`
- `venta.importe_anticipo`
- `venta.fecha_vencimiento_anticipo`
- `venta.importe_saldo`
- `venta.fecha_vencimiento_saldo`
- `venta_plan_cuota` para cuotas fijas pactadas
- `venta.id_reserva_venta`
- `venta_objeto_inmobiliario.id_venta`
- `venta_objeto_inmobiliario.id_inmueble`
- `venta_objeto_inmobiliario.id_unidad_funcional`
- `venta_objeto_inmobiliario.precio_asignado`

Datos validados por el flujo comercial:

- la venta confirmada tiene condiciones comerciales completas
- `monto_total` coincide con la suma de precios asignados
- cada objeto de venta tiene exactamente una referencia inmobiliaria

### En financiero

Datos y capacidades disponibles:

- `relacion_generadora`
- `obligacion_financiera`
- `composicion_obligacion`
- `concepto_financiero`
- creacion manual de obligaciones por `POST /api/v1/financiero/obligaciones`
- composicion de obligaciones por conceptos financieros
- concepto `CAPITAL_VENTA`
- concepto `ANTICIPO_VENTA`
- concepto `SALDO_EXTRAORDINARIO`
- concepto `INTERES_FINANCIERO`
- `obligacion_financiera.moneda` con default SQL `ARS`
- `composicion_obligacion.moneda_componente` con default SQL `ARS`

---

## Datos faltantes

No existen hoy datos implementados suficientes para modelos avanzados de financiacion.

Faltan como datos comerciales persistidos:

- periodicidad
- tasa de interes financiero
- composicion capital/interes por cuota
- fecha de primer vencimiento
- regla de redondeo por cuota
- tabla materializada `venta_condicion_comercial`
- tabla materializada `esquema_financiamiento`

`CUOTAS_FIJAS V1` queda soportado mediante `venta_plan_cuota`: no incluye
interes, indexacion, refinanciacion, cancelacion anticipada ni multiples
compradores.

---

## Decision de cierre V1: CONTADO default

Mientras la venta no tenga una estructura financiera explicita persistida, la materializacion financiera de `venta_confirmada` se define formalmente como plan `CONTADO V1`.

Reglas cerradas:

- se genera una unica obligacion `CAPITAL_VENTA`
- el importe surge de `venta.monto_total`
- `fecha_vencimiento = venta.fecha_venta`
- el obligado financiero es el comprador canonico `COMPRADOR` con `porcentaje_responsabilidad = 100.00`
- no se generan `CUOTA_VENTA` ni `SALDO_EXTRAORDINARIO`

## Decision V1: ANTICIPO_Y_SALDO

Si `venta.tipo_plan_financiero = ANTICIPO_Y_SALDO`, financiero materializa:

- una obligacion `ANTICIPO_VENTA` por `venta.importe_anticipo`, con `fecha_vencimiento = venta.fecha_vencimiento_anticipo`
- una obligacion `CAPITAL_VENTA` por `venta.importe_saldo`, con `fecha_vencimiento = venta.fecha_vencimiento_saldo`
- ambas obligaciones con moneda `venta.moneda`
- ambas obligaciones con obligado `COMPRADOR` al 100%

`importe_anticipo + importe_saldo` debe coincidir con `venta.monto_total`. El saldo ordinario pactado usa `CAPITAL_VENTA`; `SALDO_EXTRAORDINARIO` queda reservado para saldos no ordinarios futuros.

## Decision V1: CUOTAS_FIJAS

Si `venta.tipo_plan_financiero = CUOTAS_FIJAS`, financiero materializa una
obligacion por cada cuota activa de `venta_plan_cuota`:

- cada cuota genera una `obligacion_financiera`
- cada obligacion usa composicion `CAPITAL_VENTA`
- `fecha_vencimiento = venta_plan_cuota.fecha_vencimiento`
- `importe_total = venta_plan_cuota.importe_cuota`
- moneda de la obligacion = `venta_plan_cuota.moneda`
- todas las obligaciones usan obligado `COMPRADOR` al 100%

`CUOTA_VENTA` no se usa en V1 porque no esta formalmente vigente en seeds/base
ni documentado como concepto financiero operativo. Cada cuota representa una
parte del capital ordinario de venta.

La suma de cuotas activas debe coincidir exactamente con `venta.monto_total` y
los numeros de cuota deben ser secuenciales desde 1.

---

## Diseno del plan

`PlanFinancieroVenta` es el contrato conceptual que comercial prepara a partir de condiciones comerciales ya confirmadas y financiero materializa como obligaciones.

Estructura propuesta:

```json
{
  "id_venta": 10,
  "id_relacion_generadora": 25,
  "monto_total": 150000.00,
  "moneda": "ARS",
  "fecha_base": "2026-04-30",
  "obligaciones": [
    {
      "fecha_vencimiento": "2026-04-30",
      "composiciones": [
        {
          "codigo_concepto_financiero": "CAPITAL_VENTA",
          "importe": 150000.00
        }
      ]
    }
  ]
}
```

Campos:

- `id_venta`: identificador de la venta confirmada.
- `id_relacion_generadora`: relacion financiera creada para `tipo_origen = 'venta'`.
- `monto_total`: total comercial de la venta.
- `moneda`: moneda del plan.
- `fecha_base`: fecha comercial usada como referencia del plan.
- `obligaciones`: lista de obligaciones a materializar.
- `fecha_vencimiento`: vencimiento de la obligacion.
- `composiciones`: desglose economico de la obligacion.
- `codigo_concepto_financiero`: concepto financiero existente.
- `importe`: importe definido por el dominio origen.

---

## Caso minimo V1

### Venta contado

Regla:

- Una venta confirmada con `tipo_plan_financiero = CONTADO` genera una unica
  obligacion de capital de venta.

Plan:

- una unica obligacion
- una unica composicion
- concepto financiero: `CAPITAL_VENTA`
- importe: `venta.monto_total`
- moneda: `venta.moneda`
- fecha_base: `venta.fecha_venta`
- fecha_vencimiento: `venta.fecha_venta`

Ejemplo:

```json
{
  "id_venta": 10,
  "id_relacion_generadora": 25,
  "monto_total": 150000.00,
  "moneda": "ARS",
  "fecha_base": "2026-04-30",
  "obligaciones": [
    {
      "fecha_vencimiento": "2026-04-30",
      "composiciones": [
        {
          "codigo_concepto_financiero": "CAPITAL_VENTA",
          "importe": 150000.00
        }
      ]
    }
  ]
}
```

Este caso queda vigente como plan simple y como default tecnico cuando la venta
no explicita otro plan soportado.

---

## Casos implementados y futuros

### Anticipo y saldo V1

Datos persistidos en `venta`:

- importe de anticipo
- fecha de vencimiento de anticipo
- importe de saldo
- fecha de vencimiento de saldo
- moneda

Plan implementado:

- obligacion por `ANTICIPO_VENTA`
- obligacion posterior por `CAPITAL_VENTA`

### Cuotas fijas V1

Datos persistidos:

- `venta_plan_cuota.numero_cuota`
- `venta_plan_cuota.importe_cuota`
- `venta_plan_cuota.fecha_vencimiento`
- `venta_plan_cuota.moneda`

Plan implementado:

- N obligaciones
- cada obligacion con composicion `CAPITAL_VENTA`
- sin composicion adicional `INTERES_FINANCIERO`
- sin indexacion ni refinanciacion

### Saldo extraordinario

Requiere datos futuros:

- identificacion del saldo extraordinario
- importe
- causa comercial o financiera
- vencimiento

Plan futuro:

- obligacion con concepto `SALDO_EXTRAORDINARIO`

### Financiacion e interes

Requiere datos futuros:

- tasa
- metodo de calculo
- calendario
- separacion capital/interes

Plan futuro:

- cuotas con composiciones:
  - `CAPITAL_VENTA`
  - `INTERES_FINANCIERO`

Financiero no debe calcular cuotas ni intereses por cuenta propia. Debe validar y persistir el plan recibido.

---

## Reglas de ownership

- `comercial` es dueno de la semantica de la venta, sus condiciones comerciales y la estrategia economica pactada.
- `financiero` es dueno de `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, saldos, imputaciones, mora y estados financieros.
- `confirm_venta_service` no debe crear obligaciones.
- `venta_confirmada` habilita la integracion, pero no debe contener toda la logica financiera.
- El plan de obligaciones debe ser construido desde datos comerciales confirmados.
- La materializacion persistente de obligaciones debe ejecutarse en financiero.
- `relacion_generadora` es soporte formal de integracion, no reemplaza la venta.
- `PlanFinancieroVenta` no es una entidad SQL vigente; es contrato de integracion propuesto.

---

## Reglas de generacion

### Cuando se genera el plan

El plan debe generarse despues de que existan estas condiciones:

- venta en estado `confirmada`
- `relacion_generadora` existente para `tipo_origen = 'venta'`
- condiciones comerciales completas en la venta
- inexistencia de obligaciones financieras activas ya materializadas para esa relacion

En V1, el disparador recomendado es el procesamiento financiero posterior a `venta_confirmada`, despues de crear o resolver la `relacion_generadora`.

### Quien lo materializa

La materializacion corresponde al dominio financiero.

Flujo recomendado:

```text
venta_confirmada
-> financiero crea/resuelve relacion_generadora
-> financiero obtiene datos comerciales confirmados necesarios
-> financiero construye o recibe PlanFinancieroVenta V1
-> financiero valida integridad
-> financiero crea obligacion_financiera y composicion_obligacion
```

### Idempotencia

Para V1:

- la clave funcional del plan debe ser `(tipo_origen = 'venta', id_venta, tipo_plan_financiero)`
- antes de materializar, financiero debe verificar si ya existen obligaciones no eliminadas para la `id_relacion_generadora`
- si ya existen obligaciones, no debe crear nuevas obligaciones automaticamente

Limitacion actual:

- no existe constraint SQL especifica que impida duplicar obligaciones por plan de venta
- no existe tabla de ejecucion de plan financiero
- no existe `version_plan` persistida

Por lo tanto, la idempotencia V1 solo puede ser aplicativa salvo cambio SQL futuro.

### Si ya existen obligaciones para la venta

Regla V1:

- si la `relacion_generadora` de la venta ya tiene obligaciones no eliminadas, la materializacion automatica debe tratarse como ya realizada y no duplicar.

No debe:

- reemplazar obligaciones existentes
- recalcular saldos
- ajustar importes
- crear obligaciones adicionales

Cualquier correccion posterior debe modelarse como operacion financiera explicita futura.

---

## Riesgos

- La fecha de emision de obligaciones de venta mantiene el criterio tecnico
  vigente `fecha_emision = fecha_vencimiento`; su semantica queda documentada
  como decision pendiente menor.
- No hay idempotencia SQL para impedir duplicacion de obligaciones por plan.
- No hay tabla de plan financiero materializado.
- La resolucion de obligado financiero de venta V1 solo soporta un comprador
  canonico `COMPRADOR` al 100%.
- Si se generan obligaciones automaticamente sin plan explicito, puede confundirse la responsabilidad comercial con la financiera.
- Si financiero calcula cuotas o intereses, invade ownership comercial.
- Multiples compradores requieren un diseno futuro de porcentajes o
  responsabilidad; V1 bloquea el caso y no inventa reparto.

---

## Propuesta de implementacion por fases

### Fase 1 - V1 implementado

Alcance:

- materializacion financiera para venta `CONTADO`
- materializacion financiera para venta `ANTICIPO_Y_SALDO`
- materializacion financiera para venta `CUOTAS_FIJAS`
- usar `relacion_generadora` existente
- crear obligaciones con composiciones `CAPITAL_VENTA` y `ANTICIPO_VENTA`
  segun el plan comercial vigente
- crear `obligacion_obligado` para el comprador canonico `COMPRADOR`
  con `porcentaje_responsabilidad = 100.00`
- importe y vencimiento derivados de venta o `venta_plan_cuota`
- moneda derivada del plan comercial
- idempotencia aplicativa por existencia de obligacion y obligado para la relacion

No incluye:

- intereses
- indexacion
- refinanciacion
- cancelacion anticipada
- multiples compradores
- porcentajes de responsabilidad
- `cliente_comprador`
- rescision

### Fase 2 - Contrato explicito de plan

Alcance:

- formalizar `PlanFinancieroVenta` como contrato interno o endpoint de materializacion
- agregar validaciones estructurales del plan
- registrar metadata de materializacion si se aprueba cambio SQL futuro

### Fase 3 - Condiciones comerciales avanzadas

Alcance:

- incorporar datos comerciales persistidos para forma de pago
- incorporar anticipo
- incorporar calendario de cuotas
- incorporar moneda comercial
- incorporar reglas de financiacion

### Fase 4 - Idempotencia robusta

Alcance:

- agregar constraints o tabla de control de materializacion
- evitar duplicidad bajo procesamiento concurrente real
- definir clave unica por venta y version de plan

### Fase 5 - Multiples obligados

Alcance:

- resolver multiples compradores cuando exista modelo de porcentajes o
  responsabilidad
- definir solidaridad, participacion o reparto
- persistir varios `obligacion_obligado` solo con regla explicita

---

## Referencias

- `SRV-COM-002-gestion-de-venta`
- `SRV-COM-003-gestion-de-condiciones-comerciales-de-venta`
- `SRV-FIN-003-generacion-de-obligaciones`
- `MODELO-FINANCIERO-FIN`
- `INT-FIN-004-contrato-plan-obligaciones`
- `TIPO-OBLIGACION-FIN`

---

## Ejecucion por eventos

La materializacion del plan financiero de venta se realiza a traves del inbox:

```text
venta_confirmada
-> POST /api/v1/financiero/inbox
-> HandleVentaConfirmadaEventService
-> relacion_generadora + obligacion CAPITAL_VENTA + obligacion_obligado COMPRADOR
```

---

## Consideraciones tecnicas

- La materializacion del plan financiero V1 (venta contado)
  se ejecuta de forma atomica junto con la creacion de la relacion generadora.
- No existe riesgo de inconsistencias intermedias.
- La idempotencia sigue siendo aplicativa.
- Si no existe comprador canonico `COMPRADOR`, se devuelve
  `COMPRADOR_VENTA_NO_RESUELTO` y no se crea relacion ni obligacion.
- Si existen multiples compradores canonicos, se devuelve
  `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` y no se crea relacion ni obligacion.
- Si ya existe obligacion sin obligado y en reproceso existe exactamente un
  comprador canonico, el handler completa `obligacion_obligado` sin duplicar la
  obligacion.

---

## Limitaciones tecnicas actuales

### Pipeline outbox -> inbox

Actualmente:

- los eventos se generan en `outbox_event`
- existe worker interno `outbox_to_inbox_worker`
- el worker invoca `InboxEventDispatcher` directamente, sin HTTP

Limitacion:

- no hay scheduler externo ni cola distribuida
- no hay garantia de exactly-once
- el worker no utiliza locking para ejecucion concurrente

Pendiente:

- definir ejecucion operativa del worker
- evaluar control de concurrencia

Prioridad:

- Media

### Manejo de errores

- errores en handlers no se exponen en HTTP
- no existe persistencia de errores de procesamiento

Pendiente:

- logging estructurado
- tabla de eventos fallidos
