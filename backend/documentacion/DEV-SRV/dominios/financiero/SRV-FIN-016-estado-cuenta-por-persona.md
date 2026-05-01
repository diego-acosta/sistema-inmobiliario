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

- `saldo_pendiente_total`: suma de `saldo_pendiente` de todas las obligaciones incluidas
- `saldo_vencido`: suma de `saldo_pendiente` donde `fecha_vencimiento < fecha_corte AND saldo_pendiente > 0`
- `saldo_futuro`: suma restante (`saldo_pendiente_total - saldo_vencido`)
- `mora_calculada`: suma de mora dinamica de todas las obligaciones (importes completos)
- `total_con_mora`: `saldo_pendiente_total + mora_calculada`

### Por obligacion

- `id_obligacion_financiera`, `id_relacion_generadora`, `tipo_origen`, `id_origen`
- `periodo_desde`, `periodo_hasta`, `fecha_vencimiento`, `estado_obligacion`
- `importe_total`, `saldo_pendiente`
- `porcentaje_responsabilidad`: porcentaje de responsabilidad de la persona sobre esta obligacion
- `monto_responsabilidad`: `saldo_pendiente * porcentaje_responsabilidad / 100`
- `dias_atraso`, `tasa_diaria_mora`, `mora_calculada`: mora dinamica no persistida
- `total_con_mora`: `(saldo_pendiente + mora_calculada) * porcentaje_responsabilidad / 100`

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

## Reglas de filtros

- todos los filtros activos se combinan con AND
- un filtro no invalida a otro; combinaciones contradictorias producen lista vacía con HTTP 200
- `vencidas=True` aplica `fecha_vencimiento < fecha_corte AND saldo_pendiente > 0`; usa la `fecha_corte` efectiva de la consulta
- `fecha_vencimiento_desde` y `fecha_vencimiento_hasta` son independientes de `vencidas`; se pueden combinar
- rango invertido (`fecha_desde > fecha_hasta`) no es error; produce lista vacía
- no se validan ni rechazan combinaciones mutuamente excluyentes

---

## Alcance V1

- `obligacion_obligado` es la fuente de verdad del obligado. La consulta no infiere obligados desde el contrato ni desde la venta — solo expone lo que está materializado en la tabla.
- No incluye composiciones por obligacion ni aplicaciones financieras (pagos). Solo totales de saldo y mora.
- No incluye paginacion. Devuelve todas las obligaciones aplicables en una sola respuesta.
- `fecha_corte` es configurable vía query param. Si se omite, usa `date.today()`.

---

## Pendientes

- Evaluacion de paginacion si el volumen de obligaciones por persona crece en produccion.

---

## Referencias

- `MODELO-FINANCIERO-FIN` seccion 9
- `SRV-FIN-013-generacion-de-mora`
- `RN-LOC-FIN-003`
