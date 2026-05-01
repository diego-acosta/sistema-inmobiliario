# SRV-FIN-015 - Plan financiero locativo

## Objetivo

Materializar el cronograma financiero locativo mensual a partir de la activacion
de un contrato de alquiler, sin trasladar la semantica contractual del dominio
locativo al dominio financiero.

---

## Flujo V1 implementado

```text
contrato_alquiler activado
-> outbox_event contrato_alquiler_activado
-> POST /api/v1/financiero/inbox
-> HandleContratoAlquilerActivadoEventService
-> relacion_generadora tipo_origen = contrato_alquiler
-> obligaciones_financieras mensuales
-> composicion_obligacion CANON_LOCATIVO por periodo
```

El dominio locativo emite el evento. El dominio financiero materializa la
relacion generadora y las obligaciones mensuales del canon locativo cuando
existe al menos una condicion economica aplicable.

---

## Regla de activacion

- La activacion de `contrato_alquiler` no se bloquea por ausencia de
  `condicion_economica_alquiler`.
- Si el contrato se activa sin condiciones economicas aplicables, financiero no
  genera obligaciones.
- Si ningun periodo mensual tiene condicion aplicable, no se crea
  `relacion_generadora`.
- La condicion economica pertenece al dominio locativo; financiero la consume
  como dato fuente para materializar obligaciones.

---

## Cronograma mensual generado V1

- `concepto_financiero = CANON_LOCATIVO`
- una `obligacion_financiera` por periodo mensual aplicable
- periodo inicial: desde `contrato_alquiler.fecha_inicio`
- periodo final: hasta `contrato_alquiler.fecha_fin`
- el ultimo periodo se corta en `fecha_fin` cuando no coincide con fin de mes
- `importe_total = condicion_economica_alquiler.monto_base` vigente al inicio
  del periodo
- `fecha_emision = periodo_desde`
- `fecha_vencimiento = periodo_desde`
- `moneda = condicion_economica_alquiler.moneda` o `ARS` si es `NULL`
- estado inicial: `EMITIDA`
- composicion unica por obligacion con `CANON_LOCATIVO`

Regla de condicion aplicable:

- Para cada periodo mensual se evalua la condicion vigente usando
  `periodo_desde`.
- Vigente significa:
  - `fecha_desde <= periodo_desde`
  - `fecha_hasta IS NULL` o `fecha_hasta >= periodo_desde`
- Si mas de una condicion aplica al mismo `periodo_desde`, se utiliza la de
  `fecha_desde` mas reciente.
- Si no hay condicion aplicable para un periodo, ese periodo se omite.

---

## Idempotencia

- Si ya existe `relacion_generadora` para `contrato_alquiler`, se reutiliza.
- Si ya existen obligaciones para esa `relacion_generadora`, no se crea otra.
- Si no hay ningun periodo con condicion aplicable, no se crea
  `relacion_generadora`.
- La unicidad sigue siendo aplicativa; no existe constraint SQL
  `UNIQUE(tipo_origen, id_origen)`.

---

## Limitaciones actuales

- Solo genera obligaciones por `CANON_LOCATIVO`.
- No genera expensas, servicios, impuestos ni punitorios.
- No resuelve locatario u obligado financiero.
- No usa periodicidad para dividir periodos; el cronograma implementado es
  mensual.
- No prorratea cambios de condicion dentro del mes.
- No divide un periodo mensual si una condicion cambia a mitad de mes.
- Si dos condiciones economicas aplican al mismo `periodo_desde`, gana la de
  `fecha_desde` mas reciente.
- No normaliza politica de moneda; usa `condicion.moneda` o fallback `ARS`.
- `fecha_vencimiento = periodo_desde`.
- Existe pipeline automatico interno `outbox_event -> inbox` mediante
  `outbox_to_inbox_worker`, sin HTTP.

---

## Pendientes recomendados

- Prorrateo V2: dividir periodos o prorratear importes cuando una condicion
  cambia dentro del mes.
- Validar o prevenir solapamientos en `condicion_economica_alquiler`.
- Normalizar politica de moneda.
- Definir regla real de vencimiento y dia de gracia.
- Resolucion de obligado financiero o locatario.
- Normalizacion de periodicidad.
- Incorporar conceptos locativos adicionales solo cuando exista definicion
  funcional correspondiente: expensas, servicios, impuestos o punitorios.
- Constraint SQL para idempotencia.
- Definicion de ejecucion operativa del worker interno.

---

## Referencias

- `SRV-LOC-001-gestion-de-contratos-de-alquiler`
- `SRV-LOC-002-gestion-de-condiciones-locativas`
- `SRV-FIN-001-gestion-relacion-generadora`
- `SRV-FIN-003-generacion-de-obligaciones`
- `MODELO-FINANCIERO-FIN`
