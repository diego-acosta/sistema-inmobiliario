# SRV-FIN-015 - Plan financiero locativo

## Objetivo

Materializar el cronograma financiero locativo mensual a partir de la activacion
de un contrato de alquiler, sin trasladar la semantica contractual del dominio
locativo al dominio financiero.

---

## Flujo V2 minimo implementado

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

## Cronograma mensual generado V2 minimo

- `concepto_financiero = CANON_LOCATIVO`
- una `obligacion_financiera` por periodo mensual aplicable
- periodo inicial: desde `contrato_alquiler.fecha_inicio`
- periodo final: hasta `contrato_alquiler.fecha_fin`
- el ultimo periodo se corta en `fecha_fin` cuando no coincide con fin de mes
- `importe_total = condicion_economica_alquiler.monto_base` vigente al inicio
  del periodo
- `fecha_emision = periodo_desde`
- `fecha_vencimiento` deriva de regla locativa cuando exista soporte fisico;
  usa `periodo_desde` como fallback tecnico
- `moneda = condicion_economica_alquiler.moneda` o `ARS` si es `NULL`
- estado inicial: `EMITIDA`
- composicion unica por obligacion con `CANON_LOCATIVO`
- `obligacion_obligado` para el locatario principal del contrato

## Regla RN-LOC-FIN-001

La condicion economica aplicable a un periodo locativo es la vigente en
`periodo_desde`, salvo que exista una regla explicita de prorrateo o division
del periodo.

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

## Obligado financiero locativo V2 minimo

```text
contrato_alquiler
-> relacion_persona_rol tipo_relacion = contrato_alquiler
-> rol_participacion codigo_rol = LOCATARIO_PRINCIPAL
-> obligacion_obligado
```

- El obligado principal del canon locativo es el locatario principal vigente
  del contrato.
- El garante no es obligado principal automatico.
- Si no existe locatario principal, el cronograma no debe generar obligaciones
  completas y debe devolver error funcional explicito.
- `financiero` materializa `obligacion_obligado`, pero no inventa sujetos ni
  roles: consume la asociacion contextual definida por `locativo` sobre
  `relacion_persona_rol`.

---

## Regla de vencimiento V2 minimo

- La fecha de vencimiento debe derivar de una regla locativa.
- Si existe `dia_vencimiento_canon` en contrato o condicion, se usa ese dia
  dentro del mes del periodo, limitado al ultimo dia real del mes.
- Si no existe soporte fisico para `dia_vencimiento_canon`, se mantiene
  `fecha_vencimiento = periodo_desde` como fallback tecnico.
- El fallback no debe interpretarse como regla conceptual definitiva.

---

## Estados minimos de obligacion_financiera

- `EMITIDA`
- `VENCIDA`
- `CANCELADA`
- `ANULADA`
- `REEMPLAZADA`
- `PENDIENTE_AJUSTE`

Alcance actual:

- El cronograma locativo genera obligaciones en `EMITIDA`.
- No se implementa mora en este servicio.
- No se implementa regeneracion ni reemplazo de cronograma.
- `PENDIENTE_AJUSTE` queda reservado para ajustes futuros del cronograma.

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
- No usa periodicidad para dividir periodos; el cronograma implementado es
  mensual.
- No prorratea cambios de condicion dentro del mes.
- No divide un periodo mensual si una condicion cambia a mitad de mes.
- Si dos condiciones economicas aplican al mismo `periodo_desde`, gana la de
  `fecha_desde` mas reciente.
- No normaliza politica de moneda; usa `condicion.moneda` o fallback `ARS`.
- `fecha_vencimiento = periodo_desde` cuando no exista soporte fisico para
  `dia_vencimiento_canon`.
- Existe pipeline automatico interno `outbox_event -> inbox` mediante
  `outbox_to_inbox_worker`, sin HTTP.

---

## Pendientes recomendados

- Prorrateo V2: dividir periodos o prorratear importes cuando una condicion
  cambia dentro del mes.
- Validar o prevenir solapamientos en `condicion_economica_alquiler`.
- Normalizar politica de moneda.
- Persistir `dia_vencimiento_canon` en contrato o condicion si se formaliza la
  regla de vencimiento locativo.
- Definir dias de gracia.
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
