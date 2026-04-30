# MODELO-FINANCIERO-FIN - Modelo financiero implementado

## Estado del documento

- estado: `IMPLEMENTADO PARCIAL / ALINEADO A BACKEND`
- dominio: `financiero`
- ultima revision: `2026-04-30`
- alcance implementado: `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `concepto_financiero`, `movimiento_financiero`, `aplicacion_financiera`, consulta de deuda consolidada y generacion de mora diaria.
- no modifica SQL
- no define funcionalidad fuera del backend vigente

Este documento describe el modelo financiero real que hoy implementa el backend. El dominio financiero es el dueno semantico de deuda, saldos, imputaciones, estado financiero y mora.

---

## 1. Flujo implementado

```text
relacion_generadora
    -> obligacion_financiera
        -> composicion_obligacion + concepto_financiero
            -> aplicacion_financiera
                -> saldo_pendiente / saldo_componente
                    -> estado_obligacion
                        -> mora diaria si corresponde
```

Flujo operativo:

1. Se crea una `relacion_generadora` desde un origen permitido.
2. Se crea una `obligacion_financiera` asociada a esa relacion.
3. La obligacion se crea con una o mas `composicion_obligacion`.
4. Cada composicion referencia un `concepto_financiero`.
5. Una imputacion crea un `movimiento_financiero` y una o mas `aplicacion_financiera`.
6. La base de datos actualiza saldos por triggers.
7. El backend lee los saldos resultantes y actualiza `estado_obligacion` cuando corresponde.
8. El proceso de mora genera nuevas obligaciones con composicion `INTERES_MORA` para deuda vencida con saldo.

---

## 2. Entidades implementadas

### 2.1 relacion_generadora

Raiz formal del circuito financiero.

Implementado:

- alta por `POST /api/v1/financiero/relaciones-generadoras`
- consulta puntual
- listado paginado con filtros basicos
- validacion de origen para `VENTA` y `CONTRATO_ALQUILER`

No implementado:

- activar
- cancelar
- finalizar
- idempotencia completa por `X-Op-Id`

### 2.2 obligacion_financiera

Representa deuda dentro de una `relacion_generadora`.

Implementado:

- alta manual por `POST /api/v1/financiero/obligaciones`
- consulta puntual con composiciones
- `importe_total`
- `saldo_pendiente`
- `estado_obligacion`
- `fecha_emision`
- `fecha_vencimiento`

Reglas implementadas:

- toda obligacion creada por API requiere `id_relacion_generadora` existente
- toda obligacion creada por API requiere al menos una composicion
- no se usa `tipo_obligacion`
- el estado inicial de alta manual es `PROYECTADA`

### 2.3 composicion_obligacion

Representa el desglose economico de una obligacion.

Implementado:

- alta interna junto con la obligacion
- `id_concepto_financiero`
- `orden_composicion`
- `importe_componente`
- `saldo_componente`
- `estado_composicion_obligacion`

Reglas implementadas:

- cada composicion referencia un `concepto_financiero` existente
- el backend no expone alta autonoma de composiciones
- la naturaleza economica se interpreta desde `concepto_financiero`

### 2.4 concepto_financiero

Catalogo financiero que define la naturaleza economica de una composicion.

Implementado:

- consulta por `GET /api/v1/financiero/conceptos-financieros`
- busqueda interna por codigo para crear obligaciones, imputaciones y mora
- catalogo base con `INTERES_MORA` disponible en seeds actuales

### 2.5 movimiento_financiero y aplicacion_financiera

`movimiento_financiero` representa el movimiento registrado por la imputacion.

`aplicacion_financiera` vincula ese movimiento con obligacion y composicion.

Implementado:

- `POST /api/v1/financiero/imputaciones`
- una imputacion crea un movimiento tipo `PAGO`
- una imputacion puede generar una o varias aplicaciones
- cada aplicacion puede apuntar a una composicion
- `orden_aplicacion` refleja el orden de distribucion aplicado

No implementado:

- endpoint autonomo de pagos
- reversion de imputaciones
- estado persistido de aplicacion

---

## 3. Saldos

Regla real implementada:

- la base de datos actualiza `saldo_pendiente` y `saldo_componente` mediante triggers sobre `aplicacion_financiera`.
- el backend no recalcula saldos como fuente primaria.
- luego de registrar aplicaciones, el backend lee el saldo resultante y actualiza el estado de la obligacion.

Esto aplica a:

- `obligacion_financiera.saldo_pendiente`
- `composicion_obligacion.saldo_componente`

Restriccion:

- no duplicar calculo de saldos en servicios de aplicacion.

---

## 4. Imputacion implementada

Estados que aceptan imputacion:

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `VENCIDA`

Reglas:

- la obligacion debe existir y no estar dada de baja
- el monto debe ser mayor a cero
- el monto no puede exceder `saldo_pendiente`
- deben existir composiciones activas con saldo
- la distribucion se hace por prioridad de concepto y luego por `orden_composicion`

Prioridad implementada:

1. `INTERES_MORA`
2. `PUNITORIO`
3. `CARGO_ADMINISTRATIVO`
4. `INTERES_FINANCIERO`
5. `AJUSTE_INDEXACION`
6. `CAPITAL_VENTA`
7. `ANTICIPO_VENTA`
8. `CANON_LOCATIVO`
9. `EXPENSA_TRASLADADA`
10. `SERVICIO_TRASLADADO`
11. `IMPUESTO_TRASLADADO`
12. otros conceptos por `orden_composicion`

---

## 5. Estado de obligacion

Regla implementada despues de imputar:

- si `saldo_pendiente = 0`, el backend actualiza `estado_obligacion` a `CANCELADA`
- si `saldo_pendiente < importe_total`, el backend actualiza `estado_obligacion` a `PARCIALMENTE_CANCELADA`
- no cambia estados `ANULADA` ni `REEMPLAZADA`

El backend no materializa automaticamente `VENCIDA` por fecha. La mora usa la fecha de vencimiento y el saldo como criterio de seleccion, sin requerir que el estado sea `VENCIDA`.

---

## 6. Mora diaria implementada

Endpoint:

- `POST /api/v1/financiero/mora/generar`

Regla:

- selecciona obligaciones con `fecha_vencimiento < fecha_proceso`
- requiere `saldo_pendiente > 0`
- excluye `ANULADA`, `REEMPLAZADA`, `CANCELADA`
- excluye obligaciones ya generadas por mora automatica
- tasa diaria fija: `0.001`
- importe: `saldo_pendiente * 0.001`
- redondeo a 2 decimales
- si el importe calculado es `<= 0`, no genera obligacion

Efecto:

- crea una nueva `obligacion_financiera`
- usa la misma `id_relacion_generadora` de la obligacion base
- crea una composicion `INTERES_MORA`
- no capitaliza sobre la obligacion base

Limitacion:

- no existe FK fisica desde la obligacion de mora hacia la obligacion base.
- el control de duplicado por obligacion base y fecha usa `obligacion_financiera.observaciones` con una marca `MORA_AUTO`.

---

## 7. Consulta de deuda consolidada

Endpoint:

- `GET /api/v1/financiero/deuda`

Implementado:

- listado de obligaciones con composiciones
- filtros por relacion, estado, vencimiento y saldo
- paginacion `limit` / `offset`

La consulta es read-only y no recalcula saldos.

---

## 8. Estado de cuenta financiero

Descripcion:

Vista consolidada del estado financiero de una relacion generadora.

Incluye:

- obligaciones
- composiciones
- imputaciones mediante `aplicacion_financiera`
- saldos actuales
- estados de obligacion

Reglas:

- es una proyeccion del modelo, no una logica de negocio nueva
- no modifica datos
- usa saldos calculados por la DB
- usa datos persistidos para el resumen
- incluye composiciones y aplicaciones reales asociadas a cada obligacion

Notas:

- `cantidad_vencidas` se calcula contra la fecha actual del sistema.
- No existe aun fecha de referencia configurable para esta vista.

---

## 9. Pendientes reales

- transiciones de `relacion_generadora`
- reversion de imputaciones
- endpoint autonomo de pagos
- endpoint autonomo de composiciones
- fecha de referencia configurable para estado de cuenta
- relacion fisica entre mora y obligacion base
- clave unica SQL para evitar duplicidad de mora por obligacion base y fecha
- idempotencia completa por `X-Op-Id`
- outbox financiero para estos writes
