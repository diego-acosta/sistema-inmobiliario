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

## Cronograma mensual generado V2 con prorrateo

- `concepto_financiero = CANON_LOCATIVO`
- una `obligacion_financiera` por **segmento** dentro del período mensual;
  si no hay cambio de condición dentro del período, hay un solo segmento (igual que antes)
- periodo inicial: desde `contrato_alquiler.fecha_inicio`
- periodo final: hasta `contrato_alquiler.fecha_fin`
- el ultimo periodo se corta en `fecha_fin` cuando no coincide con fin de mes

### Sin cambio de condición (un segmento)

- `importe_total = condicion_economica_alquiler.monto_base` (monto completo)

### Con cambio de condición dentro del período (prorrateo)

- un nuevo segmento comienza cuando `condicion.fecha_desde` cae estrictamente
  dentro del período mensual (> `periodo_desde` y <= `periodo_hasta`)
- `importe_total = monto_base * dias_segmento / dias_mes` (días reales del mes)
- redondeo a 2 decimales con ROUND_HALF_UP
- residuo: cuando todos los segmentos del período tienen el mismo `monto_base`,
  el último segmento absorbe la diferencia de redondeo para garantizar suma exacta
- `periodo_desde` y `periodo_hasta` del payload reflejan el segmento real,
  no el mes completo
- `fecha_emision` = inicio del mes (`periodo_desde_mes`) para todos los segmentos;
  esto evita violación del constraint `fecha_vencimiento >= fecha_emision`

- `fecha_emision = periodo_desde_mes` (inicio del mes, igual para todos los segmentos del mes)
- `fecha_vencimiento` = día `contrato_alquiler.dia_vencimiento_canon` dentro del
  mes de `periodo_desde`; si ese día no existe en el mes, se usa el último día
  real del mes; si `dia_vencimiento_canon` es NULL, se usa `periodo_desde` como
  fallback técnico (RN-LOC-FIN-003)
- `moneda = condicion_economica_alquiler.moneda` o `ARS` si es `NULL`
- estado inicial: `EMITIDA`
- composicion unica por obligacion con `CANON_LOCATIVO`
- `obligacion_obligado` para el locatario principal del contrato

## Regla RN-LOC-FIN-001 (actualizada con prorrateo)

La condicion economica aplicable a un periodo locativo se resuelve segmento a
segmento cuando hay cambios dentro del período.

Regla de condicion aplicable:

- Para cada segmento se evalua la condicion vigente usando `seg_desde`.
- Vigente significa:
  - `fecha_desde <= seg_desde`
  - `fecha_hasta IS NULL` o `fecha_hasta >= seg_desde`
- Si mas de una condicion aplica al mismo `seg_desde`, se utiliza la de
  `fecha_desde` mas reciente.
- Si no hay condicion aplicable para un segmento, ese segmento se omite.
- Si un período mensual no tiene ningún segmento con condición, el período completo se omite.

Regla de prorrateo (RN-LOC-FIN-005):

- Un cambio de condición dentro del período se detecta cuando `fecha_desde`
  de una condición cae estrictamente después de `periodo_desde` y dentro del período.
- Cada segmento generado usa el `monto_base` de su propia condición.
- `importe = monto_base * dias_segmento / dias_mes` con días reales del mes.

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

## Regla de vencimiento V2 (RN-LOC-FIN-003)

- `contrato_alquiler.dia_vencimiento_canon` determina el día del mes en que
  vence el canon locativo.
- Si el campo está informado, `fecha_vencimiento` se calcula como ese día
  dentro del mes de `periodo_desde`.
- Si el día no existe en el mes (ej: 31 en febrero), se usa el último día real.
- Si el día calculado quedara antes de `periodo_desde`, se usa `periodo_desde`.
- Si `dia_vencimiento_canon` es NULL, se usa `periodo_desde` como fallback
  técnico. El fallback no es una regla conceptual definitiva.
- `dia_vencimiento_canon` pertenece a `contrato_alquiler`, no a
  `condicion_economica_alquiler`.
- No hay días de gracia implementados.
- No hay ajuste por feriados ni días inhábiles.

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
- La base de datos refuerza la idempotencia con indices unicos parciales:
  - `relacion_generadora(tipo_origen, id_origen) WHERE deleted_at IS NULL`
  - `obligacion_financiera(id_relacion_generadora, periodo_desde, periodo_hasta)
    WHERE deleted_at IS NULL`
- El repositorio mantiene la verificacion aplicativa y usa conflicto SQL como
  defensa ante retry o concurrencia.
- El indice unico `(tipo_origen, id_origen) WHERE deleted_at IS NULL` impide
  que existan multiples `relacion_generadora` activas para el mismo origen. Los
  tests que verifican listados o conteo de relaciones deben usar `id_origen`
  distintos para evitar colisiones entre casos de prueba.

---

## Limitaciones actuales

- Solo genera obligaciones por `CANON_LOCATIVO`.
- No genera expensas, servicios, impuestos ni punitorios.
- No usa periodicidad para dividir periodos; el cronograma implementado es
  mensual.
- Prorratea cambios de condición dentro del mes (RN-LOC-FIN-005 — implementado).
- Si dos condiciones economicas aplican al mismo `periodo_desde`, gana la de
  `fecha_desde` mas reciente.
- No normaliza politica de moneda; usa `condicion.moneda` o fallback `ARS`.
- `fecha_vencimiento = periodo_desde` cuando `dia_vencimiento_canon` sea NULL.
- Existe pipeline automatico interno `outbox_event -> inbox` mediante
  `outbox_to_inbox_worker`, sin HTTP.

---

## Pendientes recomendados

- Prorrateo V2: dividir periodos o prorratear importes cuando una condicion
  cambia dentro del mes.
- Validar o prevenir solapamientos en `condicion_economica_alquiler`.
- Normalizar politica de moneda.
- `dia_vencimiento_canon` ya está implementado en `contrato_alquiler`.
- Definir dias de gracia.
- Normalizacion de periodicidad.
- Incorporar conceptos locativos adicionales solo cuando exista definicion
  funcional correspondiente: expensas, servicios, impuestos o punitorios.
- Definicion de ejecucion operativa del worker interno.

---

## Referencias

- `SRV-LOC-001-gestion-de-contratos-de-alquiler`
- `SRV-LOC-002-gestion-de-condiciones-locativas`
- `SRV-FIN-001-gestion-relacion-generadora`
- `SRV-FIN-003-generacion-de-obligaciones`
- `MODELO-FINANCIERO-FIN`
