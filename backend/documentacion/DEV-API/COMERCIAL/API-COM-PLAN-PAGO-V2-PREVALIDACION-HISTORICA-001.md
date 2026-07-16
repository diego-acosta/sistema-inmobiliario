# API-COM-PLAN-PAGO-V2-PREVALIDACION-HISTORICA-001 — Prevalidación histórica de Plan Pago Venta V2

## Propósito

Extiende el preview read-like `POST /api/v1/ventas/plan-pago-v2/preview` para prevalidar una posible venta histórica antes de confirmar la venta o generar deuda.

La operación no crea venta, plan, bloques, cronograma, relaciones generadoras, obligaciones, composiciones, indexaciones, corridas ni eventos outbox.

## Decisión de endpoint

Se extiende la ruta existente `POST /api/v1/ventas/plan-pago-v2/preview` porque ya recibe el Plan Pago Venta V2 por bloques sin una venta persistida y ya resuelve el preview vigente de cuotas e indexación. La prevalidación se activa únicamente cuando el request incluye `fecha_venta` y `fecha_corte`, por lo que los previews normales conservan compatibilidad.

## CORE-EF

- Clasificación: `PREVIEW_READLIKE`.
- `If-Match-Version`: NO APLICA; no modifica entidades versionadas.
- Outbox: NO APLICA; no persiste eventos.
- Fecha de corte: dato de negocio explícito del request; CORE-EF no transporta la fecha operativa de negocio.

## Request

Campos base: los vigentes de `PreviewPlanPagoVentaV2PorBloquesRequest`:

- `tipo_pago`
- `monto_total_plan`
- `moneda`
- `bloques`
- `observaciones`

Campos opcionales que activan la prevalidación histórica:

- `fecha_venta`
- `fecha_corte`

Validaciones específicas:

- `fecha_venta` y `fecha_corte` deben informarse juntas.
- `fecha_venta <= fecha_corte`.
- El request mantiene `extra="forbid"`; no acepta ids de persistencia ni campos generados por backend.
- Bloques, moneda y configuración de indexación se validan con las reglas vigentes del preview V2.

## Historicidad y clasificación temporal

`es_venta_historica = fecha_venta < fecha_corte`.

Las cuotas se clasifican por `fecha_vencimiento` contra la fecha de corte exacta:

- `HISTORICA_EXIGIBLE`: `fecha_vencimiento < fecha_corte`.
- `PERIODO_CORTE`: `fecha_vencimiento == fecha_corte`.
- `FUTURA`: `fecha_vencimiento > fecha_corte`.

El preview vigente selecciona el valor de índice aplicable con `fecha_valor <= fecha_vencimiento`; esta prevalidación no cambia esa política ni usa una fecha mensual alternativa. `fecha_corte` solo clasifica exigibilidad para decidir bloqueos de prevalidación: no participa en la selección del índice, el período del índice, el coeficiente ni el importe de cuota.

## Response

Cuando se informan fechas, `data.prevalidacion_historica` incluye:

- `es_venta_historica`
- `fecha_venta`
- `fecha_corte`
- `puede_confirmar`
- `cantidad_cuotas`
- `cantidad_historicas_exigibles`
- `cantidad_periodo_corte`
- `cantidad_futuras`
- `cantidad_con_indice`
- `cantidad_sin_indice`
- `cantidad_bloqueadas`
- `motivos_bloqueo`
- `cuotas`

Cada cuota informa número de cuota, bloque, vencimiento, clasificación temporal, capital, ajuste, total, moneda, estado de indexación, si bloquea la confirmación, motivo estable e información del índice aplicable.

Estados de preview:

- `CON_INDICE_APLICADO`
- `PROYECTADA_SIN_INDICE`
- `NO_REQUIERE_INDICE`
- `BLOQUEADA`

`PROYECTADA_SIN_INDICE` es solo estado de cálculo/preview y no se agrega a `obligacion_financiera.estado_obligacion`.

## Bloqueos

Una cuota histórica exigible bloquea la futura confirmación si requiere indexación y no puede calcularse un importe final confiable.

Códigos funcionales estables por cuota:

- `VALOR_INDICE_PUBLICADO_INEXISTENTE`
- `FECHA_PUBLICACION_INDICE_INCOMPLETA`
- `INDICE_FINANCIERO_INACTIVO`
- `VALOR_BASE_INDICE_INVALIDO`

Las inconsistencias de configuración de indexación o moneda se mantienen como errores globales del preview normal (`APPLICATION_ERROR`/422 según validación de schema) antes de construir `prevalidacion_historica`; por eso `CONFIGURACION_INDEXACION_INVALIDA` y `MONEDA_NO_COMPATIBLE_INDEXACION` no se documentan como motivos por cuota en este contrato.

Las cuotas futuras sin valor aplicable permanecen `PROYECTADA_SIN_INDICE` y no bloquean automáticamente.

## Ejemplos

### Histórico válido

Request con `fecha_venta=2026-01-10`, `fecha_corte=2026-03-15` y valores publicados aplicables para las cuotas vencidas. Response: `es_venta_historica=true`, `cantidad_historicas_exigibles>0`, `cantidad_bloqueadas=0`, `puede_confirmar=true`.

### Histórico bloqueado

Request histórico con cuota exigible de un bloque indexado sin valor publicado aplicable. Response: `puede_confirmar=false`, cuota `BLOQUEADA`, motivo `VALOR_INDICE_PUBLICADO_INEXISTENTE`.

### Cuotas futuras sin índice

Si no existe valor publicado para una cuota futura, la cuota queda `PROYECTADA_SIN_INDICE` y `bloquea_confirmacion=false`.

### Venta actual

Con `fecha_venta == fecha_corte`, `es_venta_historica=false`; la respuesta mantiene el preview normal y puede incluir `cantidad_historicas_exigibles=0`.

## Reutilización en confirmación real

Desde #358 la misma prevalidación read-like se reutiliza en `POST /api/v1/ventas/directa/confirmar-venta-completa` antes de persistir venta, plan o deuda cuando `fecha_corte` está presente. El componente de aplicación no persiste, no crea corridas, no emite outbox, no toma locks y no modifica versiones; tampoco reemplaza la transacción de confirmación, que sigue siendo la frontera atómica real del caso de uso.

Si una cuota `HISTORICA_EXIGIBLE` de un bloque `INDEXACION` queda bloqueada, la confirmación devuelve error funcional `VENTA_HISTORICA_INDEXACION_NO_RESUELTA` con `cantidad_bloqueadas`, `motivos_bloqueo` y `cuotas_bloqueadas`, y no crea filas parciales ni corridas V2.
