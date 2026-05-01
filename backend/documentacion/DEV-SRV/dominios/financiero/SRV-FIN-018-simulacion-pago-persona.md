# SRV-FIN-018 - Simulación de pago por persona

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `POST /api/v1/financiero/personas/{id_persona}/simular-pago`

---

## Objetivo

Calcular cómo se distribuiría un monto sobre la deuda de una persona sin registrar movimiento financiero ni modificar saldos.

Útil para: pre-liquidación, pantalla de pago, estimación de cancelación de deuda.

---

## Input

```json
{
  "monto": 50000.00,
  "fecha_corte": "2026-05-20"
}
```

- `monto` (obligatorio): monto a simular; debe ser > 0
- `fecha_corte` (opcional): fecha para mora y clasificación vencida/futura; default `date.today()`

---

## Output

```json
{
  "id_persona": 1,
  "fecha_corte": "2026-05-20",
  "monto_ingresado": 50000.00,
  "monto_aplicado": 45500.00,
  "remanente": 4500.00,
  "total_deuda_considerada": 45500.00,
  "detalle": [...]
}
```

### Por obligación en detalle

- `id_obligacion_financiera`
- `saldo_pendiente`: saldo real en DB
- `mora_calculada`: mora dinámica al corte
- `total_a_cubrir`: `(saldo_pendiente + mora_calculada) * porcentaje_responsabilidad / 100`
- `monto_aplicado`: porción del monto que cubre esta obligación
- `saldo_restante_simulado`: `total_a_cubrir - monto_aplicado`

---

## Orden de aplicación

1. Obligaciones con `fecha_vencimiento < fecha_corte` (vencidas), por `fecha_vencimiento ASC`
2. Luego obligaciones futuras o sin vencimiento, por `fecha_vencimiento ASC NULLS LAST`

---

## Reglas

- solo incluye obligaciones con `saldo_pendiente > 0`
- excluye `ANULADA` y `REEMPLAZADA`
- mora dinámica incluida en `total_a_cubrir`; no persiste
- el monto se aplica secuencialmente hasta agotarse
- si el monto supera la deuda total: `remanente = monto - total_deuda`
- no crea `movimiento_financiero`, `aplicacion_financiera` ni `INTERES_MORA`
- no modifica ningún estado ni saldo en DB
- devuelve `404` si la persona no existe
- devuelve `422` si `monto <= 0` (validación Pydantic)

---

## Limitaciones V1

- no desagrega la aplicación entre capital y mora
- no considera política de prelación entre conceptos financieros
- no aplica solidaridad entre co-obligados de la misma obligación
- un solo pago simulado; no admite plan de cuotas

---

## Referencias

- `MODELO-FINANCIERO-FIN` sección 11
- `SRV-FIN-013-generacion-de-mora`
- `SRV-FIN-016-estado-cuenta-por-persona`
