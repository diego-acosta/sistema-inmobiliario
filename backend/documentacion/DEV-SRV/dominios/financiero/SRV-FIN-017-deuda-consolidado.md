# SRV-FIN-017 - Estado de deuda consolidado

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `GET /api/v1/financiero/deuda/consolidado`

---

## Objetivo

Vista agregada de deuda global sin filtro de persona, agrupada por `relacion_generadora` y desagregada por `tipo_origen`.

---

## Parametros

### Query (todos opcionales)

- `tipo_origen`: filtra por `relacion_generadora.tipo_origen` (ej: `CONTRATO_ALQUILER`, `VENTA`)
- `fecha_corte`: fecha para cálculo de mora y clasificación vencida/futura; si se omite, usa `date.today()`

---

## Respuesta

### Raíz

- `fecha_corte`: fecha efectiva usada

### Resumen global

- `saldo_pendiente_total`: suma de `saldo_pendiente` de todas las obligaciones incluidas
- `saldo_vencido`: suma de `saldo_pendiente` donde `fecha_vencimiento < fecha_corte`
- `saldo_futuro`: `saldo_pendiente_total - saldo_vencido`
- `mora_calculada`: suma de mora dinámica total
- `total_con_mora`: `saldo_pendiente_total + mora_calculada`

### Por tipo_origen

Mismos campos que el resumen global, más `cantidad_relaciones`.

Cada clave del dict es el `tipo_origen` en mayúsculas (ej: `"CONTRATO_ALQUILER"`).

### Relaciones

Lista de items, uno por `relacion_generadora` con saldo > 0:

- `id_relacion_generadora`, `tipo_origen`, `id_origen`
- `saldo_pendiente`, `saldo_vencido`, `saldo_futuro`
- `mora_calculada`, `total_con_mora`
- `cantidad_obligaciones`

---

## Reglas

- solo incluye obligaciones con `saldo_pendiente > 0`
- excluye `ANULADA` y `REEMPLAZADA`
- mora dinámica: no persiste, no crea `INTERES_MORA`
- `fecha_corte` no modifica estados en DB
- respuesta sin paginación; agrega todas las relaciones en memoria

---

## Diferencia con endpoints existentes

| Endpoint | Alcance |
|---|---|
| `GET /deuda` | listado paginado de obligaciones individuales |
| `GET /estado-cuenta` | por relacion_generadora, con composiciones y aplicaciones |
| `GET /personas/{id}/estado-cuenta` | por persona vía `obligacion_obligado` |
| `GET /deuda/consolidado` | vista global agrupada por relacion_generadora y tipo_origen |

---

## Referencias

- `MODELO-FINANCIERO-FIN` sección 10
- `SRV-FIN-013-generacion-de-mora`
- `SRV-FIN-016-estado-cuenta-por-persona`
