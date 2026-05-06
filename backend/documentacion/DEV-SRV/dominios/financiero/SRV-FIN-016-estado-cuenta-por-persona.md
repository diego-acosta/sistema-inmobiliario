# SRV-FIN-016 - Estado de cuenta por persona

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `GET /api/v1/financiero/personas/{id_persona}/estado-cuenta`

---

## Objetivo

Exponer el estado financiero consolidado de una persona consultando desde `obligacion_obligado`.

---

## Ruta de consulta

```text
persona
-> obligacion_obligado
-> obligacion_financiera
-> relacion_generadora
```

---

## Parametros

### Path

- `id_persona` (obligatorio): identificador de persona

### Query (todos opcionales)

- `estado`: filtra por `estado_obligacion`
- `tipo_origen`: filtra por `relacion_generadora.tipo_origen`
- `id_origen`: filtra por `relacion_generadora.id_origen`
- `vencidas`: si `true`, solo obligaciones con `fecha_vencimiento < fecha_corte AND saldo_pendiente > 0`
- `fecha_vencimiento_desde`, `fecha_vencimiento_hasta`: rango de vencimiento
- `fecha_corte` (ISO date): fecha de corte para cálculo de mora y días de atraso; si se omite, usa `date.today()`

---

## Respuesta

### Raíz

- `fecha_corte`: fecha efectiva usada en el cálculo (informativa, no modificable desde el response)

### Resumen

- `saldo_total`: alias funcional de `saldo_pendiente_total`
- `saldo_pendiente_total`: suma de `saldo_pendiente` de todas las obligaciones incluidas
- `saldo_vencido`: suma de `saldo_pendiente` donde `fecha_vencimiento < fecha_corte AND saldo_pendiente > 0`
- `saldo_futuro`: suma restante (`saldo_pendiente_total - saldo_vencido`)
- `mora_calculada`: suma de mora dinamica de todas las obligaciones (importes completos)
- `total_con_mora`: `saldo_pendiente_total + mora_calculada`
- `saldo_locativo`: saldo incluido en grupo `LOCATIVO`
- `saldo_venta`: saldo incluido en grupo `VENTA`
- `saldo_trasladados`: saldo incluido en grupo `TRASLADADOS`
- `saldo_otros`: saldo incluido en grupo `OTROS`

### Grupos de deuda

`grupos_deuda` expone la lectura jerarquica principal:

```text
persona
-> grupo funcional
-> relacion_generadora / origen
-> obligaciones
-> composiciones
```

Cada grupo incluye:

- `grupo_origen_deuda`: `LOCATIVO`, `VENTA`, `TRASLADADOS` u `OTROS`
- `saldo_total`: suma de saldos de sus relaciones
- `relaciones`: bloques separados por `id_relacion_generadora`

Cada relacion incluye:

- `id_relacion_generadora`, `tipo_origen`, `id_origen`
- `descripcion_origen`: `relacion_generadora.descripcion` si esta disponible
- `saldo_total`: suma de saldos de sus obligaciones
- `cantidad_obligaciones`
- `obligaciones`

Cada obligacion del bloque incluye:

- `id_obligacion_financiera`, `estado_obligacion`
- `fecha_emision`, `fecha_vencimiento`, `periodo_desde`, `periodo_hasta`
- `saldo_pendiente`
- `composiciones`

Cada composicion incluye:

- `id_composicion_obligacion`
- `codigo_concepto_financiero`
- `importe_componente`
- `saldo_componente`
- `estado_composicion_obligacion`

### Por obligacion

- `id_obligacion_financiera`, `id_relacion_generadora`, `tipo_origen`, `id_origen`
- `fecha_emision`, `periodo_desde`, `periodo_hasta`, `fecha_vencimiento`, `estado_obligacion`
- `importe_total`, `saldo_pendiente`
- `porcentaje_responsabilidad`: porcentaje de responsabilidad de la persona sobre esta obligacion
- `monto_responsabilidad`: `saldo_pendiente * porcentaje_responsabilidad / 100`
- `dias_atraso`, `tasa_diaria_mora`, `mora_calculada`: mora dinamica no persistida
- `total_con_mora`: `(saldo_pendiente + mora_calculada) * porcentaje_responsabilidad / 100`
- `composiciones`: desglose activo de la obligacion

---

## Reglas

- excluye `ANULADA` y `REEMPLAZADA`
- incluye `EMITIDA` y `VENCIDA` por defecto
- mora calculada solo si `saldo_pendiente > 0` y `fecha_vencimiento < fecha_corte`
- `fecha_corte` configurable vía query param; si se omite, usa `date.today()`
- `fecha_corte` no modifica estados persistidos; `VENCIDA` sigue dependiendo del estado real en DB
- mora dinamica: no persiste, no crea `INTERES_MORA`, no crea obligaciones
- uso típico de `fecha_corte`: simulación a fecha futura, auditoría a fecha pasada
- devuelve `404` si la persona no existe
- devuelve resumen en cero y lista vacia si la persona existe pero no tiene obligaciones
- cada `relacion_generadora` se muestra como bloque separado dentro de su grupo funcional

## Reglas de filtros

- todos los filtros activos se combinan con AND
- un filtro no invalida a otro; combinaciones contradictorias producen lista vacía con HTTP 200
- `vencidas=True` aplica `fecha_vencimiento < fecha_corte AND saldo_pendiente > 0`; usa la `fecha_corte` efectiva de la consulta
- `fecha_vencimiento_desde` y `fecha_vencimiento_hasta` son independientes de `vencidas`; se pueden combinar
- rango invertido (`fecha_desde > fecha_hasta`) no es error; produce lista vacía
- no se validan ni rechazan combinaciones mutuamente excluyentes

## Clasificacion V1

- `contrato_alquiler` -> `LOCATIVO`
- `venta`, `reserva_venta`, `plan_venta` -> `VENTA`
- `factura_servicio` -> `TRASLADADOS`
- fallback por conceptos `SERVICIO_TRASLADADO`, `EXPENSA_TRASLADADA` o
  `IMPUESTO_TRASLADADO` -> `TRASLADADOS`
- resto -> `OTROS`

---

## Alcance V1

- `obligacion_obligado` es la fuente de verdad del obligado. La consulta no infiere obligados desde el contrato ni desde la venta — solo expone lo que está materializado en la tabla.
- Incluye composiciones por obligacion. No incluye aplicaciones financieras (pagos) dentro de esta vista por persona.
- No incluye paginacion. Devuelve todas las obligaciones aplicables en una sola respuesta.
- `fecha_corte` es configurable vía query param. Si se omite, usa `date.today()`.
- Mantiene compatibilidad con el arreglo plano `obligaciones`, pero la lectura funcional recomendada es `grupos_deuda`.

---

## Pendientes

- Evaluacion de paginacion si el volumen de obligaciones por persona crece en produccion.

---

## Referencias

- `MODELO-FINANCIERO-FIN` seccion 9
- `SRV-FIN-013-generacion-de-mora`
- `RN-LOC-FIN-003`
