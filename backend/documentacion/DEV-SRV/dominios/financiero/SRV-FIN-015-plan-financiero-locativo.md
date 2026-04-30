# SRV-FIN-015 - Plan financiero locativo

## Objetivo

Materializar deuda inicial locativa desde la activacion de un contrato de alquiler.

---

## Flujo V1 implementado

```text
contrato_alquiler activado
-> outbox_event contrato_alquiler_activado
-> POST /api/v1/financiero/inbox
-> HandleContratoAlquilerActivadoEventService
-> relacion_generadora tipo_origen = contrato_alquiler
-> obligacion_financiera
-> composicion_obligacion CANON_LOCATIVO
```

El dominio locativo emite el evento. El dominio financiero materializa la
relacion generadora y la obligacion inicial.

---

## Regla de activacion

- No se permite activar `contrato_alquiler` sin `condicion_economica_alquiler`.
- Error funcional: `SIN_CONDICION_ECONOMICA`.
- Justificacion: financiero necesita `monto_base` para materializar deuda.

---

## Obligacion generada V1

- `concepto_financiero = CANON_LOCATIVO`
- `importe_total = condicion_economica_alquiler.monto_base`
- `fecha_emision = contrato_alquiler.fecha_inicio`
- `fecha_vencimiento = contrato_alquiler.fecha_inicio`
- `moneda = condicion_economica_alquiler.moneda` o `ARS` si es `NULL`
- estado inicial: `PROYECTADA`
- una sola obligacion inicial, sin cronograma

---

## Idempotencia

- Si ya existe `relacion_generadora` para `contrato_alquiler`, se reutiliza.
- Si ya existen obligaciones para esa `relacion_generadora`, no se crea otra.
- La unicidad sigue siendo aplicativa; no existe constraint SQL
  `UNIQUE(tipo_origen, id_origen)`.

---

## Limitaciones actuales

- No genera cronograma mensual.
- No usa periodicidad todavia.
- No aplica dias de gracia.
- No resuelve locatario u obligado financiero.
- Si no hay condicion vigente exacta para la fecha de inicio, el handler usa
  fallback a la primera condicion disponible segun la implementacion actual;
  esto debe revisarse.
- Usa `ARS` como fallback tecnico si `condicion_economica_alquiler.moneda` es
  `NULL`.
- No hay pipeline automatico `outbox_event -> inbox`; el inbox existe pero
  requiere invocacion.
- No hay generacion de expensas, servicios ni impuestos trasladados.

---

## Pendientes recomendados

- Generador de cronograma locativo mensual.
- Resolucion de obligado financiero o locatario.
- Normalizacion de periodicidad.
- Definicion de fecha de vencimiento real y dias de gracia.
- Constraint SQL para idempotencia.
- Pipeline automatico `outbox_event -> inbox`.

---

## Referencias

- `SRV-LOC-001-gestion-de-contratos-de-alquiler`
- `SRV-LOC-002-gestion-de-condiciones-locativas`
- `SRV-FIN-001-gestion-relacion-generadora`
- `SRV-FIN-003-generacion-de-obligaciones`
- `MODELO-FINANCIERO-FIN`
