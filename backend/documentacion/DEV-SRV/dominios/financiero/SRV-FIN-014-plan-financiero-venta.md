# SRV-FIN-014 - Plan financiero de venta

## Objetivo

Definir como una `venta` confirmada del dominio `comercial` debe transformarse en un plan de obligaciones financieras, sin trasladar ownership comercial al dominio financiero y sin generar obligaciones desde `confirm_venta_service`.

Este documento es una propuesta de diseno. No modifica SQL, backend ni tests.

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

La generacion automatica de obligaciones desde venta no esta implementada.

---

## Datos disponibles hoy

### En comercial

Datos disponibles para construir un plan minimo:

- `venta.id_venta`
- `venta.fecha_venta`
- `venta.estado_venta`
- `venta.monto_total`
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

- forma de pago de la venta
- moneda comercial explicita de la venta
- anticipo pactado
- saldo a financiar
- cantidad de cuotas
- calendario de vencimientos
- periodicidad
- tasa de interes financiero
- composicion capital/interes por cuota
- fecha de primer vencimiento
- regla de redondeo por cuota
- tabla materializada `venta_condicion_comercial`
- tabla materializada `esquema_financiamiento`

Por lo tanto, cualquier plan distinto de venta contado debe considerarse futuro o pendiente.

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
- `moneda`: moneda del plan. En V1 debe ser `ARS` por default tecnico actual, porque venta no persiste moneda.
- `fecha_base`: fecha usada para emitir o vencer la obligacion. En V1 debe derivarse de `venta.fecha_venta`.
- `obligaciones`: lista de obligaciones a materializar.
- `fecha_vencimiento`: vencimiento de la obligacion.
- `composiciones`: desglose economico de la obligacion.
- `codigo_concepto_financiero`: concepto financiero existente.
- `importe`: importe definido por el dominio origen.

---

## Caso minimo V1

### Venta contado

Regla:

- Una venta confirmada se interpreta como venta contado si no existe informacion implementada de anticipo, cuotas o financiacion.

Plan:

- una unica obligacion
- una unica composicion
- concepto financiero: `CAPITAL_VENTA`
- importe: `venta.monto_total`
- moneda: `ARS`
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

Este caso es el unico implementable hoy sin inventar datos comerciales no persistidos.

---

## Casos futuros

### Anticipo

Requiere datos futuros:

- importe de anticipo
- fecha de vencimiento de anticipo
- regla de saldo restante

Plan futuro:

- obligacion por `ANTICIPO_VENTA`
- una o mas obligaciones posteriores por `CAPITAL_VENTA` o `SALDO_EXTRAORDINARIO`

### Cuotas

Requiere datos futuros:

- cantidad de cuotas
- periodicidad
- fechas de vencimiento
- importe por cuota
- regla de redondeo

Plan futuro:

- N obligaciones
- cada obligacion con composicion `CAPITAL_VENTA`
- si corresponde, composicion adicional `INTERES_FINANCIERO`

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

- la clave funcional del plan debe ser `(tipo_origen = 'venta', id_venta, version_plan = 'V1_CONTADO')`
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

- La venta no persiste moneda; V1 debe asumir `ARS` por default tecnico financiero.
- La venta no persiste forma de pago; V1 interpreta todo como contado.
- No hay datos de vencimiento; V1 usa `venta.fecha_venta`.
- No hay idempotencia SQL para impedir duplicacion de obligaciones por plan.
- No hay tabla de plan financiero materializado.
- No hay resolucion de obligado financiero implementada para obligaciones de venta.
- Si se generan obligaciones automaticamente sin plan explicito, puede confundirse la responsabilidad comercial con la financiera.
- Si financiero calcula cuotas o intereses, invade ownership comercial.

---

## Propuesta de implementacion por fases

### Fase 1 - V1 contado

Alcance:

- implementar materializacion financiera para venta contado
- usar `relacion_generadora` existente
- crear una obligacion con una composicion `CAPITAL_VENTA`
- importe igual a `venta.monto_total`
- moneda `ARS`
- fecha de vencimiento igual a `venta.fecha_venta`
- idempotencia aplicativa por existencia de obligaciones para la relacion

No incluye:

- anticipo
- cuotas
- intereses
- moneda comercial configurable
- obligado financiero
- cambios SQL

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

### Fase 5 - Obligado financiero

Alcance:

- resolver comprador u obligado financiero desde participaciones comerciales
- persistir `obligacion_obligado` cuando el modelo este definido

---

## Referencias

- `SRV-COM-002-gestion-de-venta`
- `SRV-COM-003-gestion-de-condiciones-comerciales-de-venta`
- `SRV-FIN-003-generacion-de-obligaciones`
- `MODELO-FINANCIERO-FIN`
- `INT-FIN-004-contrato-plan-obligaciones`
- `TIPO-OBLIGACION-FIN`

---

## Consideraciones tecnicas

- La materializacion del plan financiero V1 (venta contado)
  se ejecuta de forma atomica junto con la creacion de la relacion generadora.
- No existe riesgo de inconsistencias intermedias.
- La idempotencia sigue siendo aplicativa.
