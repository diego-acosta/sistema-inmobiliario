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
- `vencidas`: si `true`, solo obligaciones con `fecha_vencimiento < hoy AND saldo_pendiente > 0`
- `fecha_vencimiento_desde`, `fecha_vencimiento_hasta`: rango de vencimiento

---

## Respuesta

### Resumen

- `saldo_pendiente_total`: suma de `saldo_pendiente` de todas las obligaciones incluidas
- `saldo_vencido`: suma de `saldo_pendiente` donde `fecha_vencimiento < hoy AND saldo_pendiente > 0`
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
- `fecha_corte = date.today()` — no configurable en V1
- mora dinamica: no persiste, no crea `INTERES_MORA`, no crea obligaciones
- devuelve `404` si la persona no existe
- devuelve resumen en cero y lista vacia si la persona existe pero no tiene obligaciones

---

## Limitaciones actuales

- fecha de corte no configurable (siempre `hoy`)
- no incluye composiciones por obligacion (solo totales)
- no incluye aplicaciones financieras (pagos) por obligacion
- no agrega solidaridad ni prorrateo entre obligados de la misma obligacion
- no desagrega mora por concepto

---

## Referencias

- `MODELO-FINANCIERO-FIN` seccion 9
- `SRV-FIN-013-generacion-de-mora`
- `RN-LOC-FIN-003`
