# CIERRE-MODULO-FINANCIERO-LOCATIVO

## Estado

- dominio: `financiero`
- alcance: financiero locativo V1
- estado: `CERRADO V1`
- fecha de cierre técnico: 2026-05-05

Este documento consolida el cierre funcional y técnico del módulo financiero
locativo V1. No redefine reglas: resume lo implementado y remite a
`MODELO-FINANCIERO-FIN`, `SRV-FIN-015`, `SRV-FIN-019`, `SRV-FIN-013` y
`RN-FIN` como fuente normativa detallada.

---

## 1. Alcance Cerrado V1

Queda cerrado para V1:

- cronograma locativo
- prorrateo parcial por días reales del mes
- regeneración de cronograma locativo
- reemplazo de obligaciones, con vínculo directo 1 a 1 cuando corresponde
- pagos agrupados por `uid_pago_grupo` y `codigo_pago_grupo`
- recibo/constancia interna de pago agrupado
- punitorio persistido como `composicion_obligacion`
- trazabilidad de `liquidacion_punitorio`
- reversión segura V1 de pago agrupado
- indexación corregida por aumento o reducción
- `parametro_punitorio` para resolver tasa y días de gracia

---

## 2. Endpoints Implementados

Endpoints relevantes del cierre:

- `POST /api/v1/financiero/pagos?id_persona={id_persona}`
- `POST /api/v1/financiero/personas/{id_persona}/simular-pago`
- `GET /api/v1/financiero/pagos`
- `GET /api/v1/financiero/pagos/{codigo_pago_grupo}`
- `GET /api/v1/financiero/pagos/{codigo_pago_grupo}/recibo`
- `POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir`
- `POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/ajuste-indexacion`
- `POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/bonificacion-indexacion`
- `POST /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/regenerar-cronograma`

---

## 3. Reglas Funcionales Principales

- Si una obligación no tiene pagos ni aplicaciones activas, la regeneración
  puede reemplazarla según la regla vigente de cronograma.
- Si una obligación con pagos recibe una corrección de índice con aumento, V1
  no reemplaza la obligación: agrega `AJUSTE_INDEXACION` como composición
  positiva dentro de la obligación base.
- Si una obligación con pagos recibe una corrección de índice con reducción, V1
  no crea composición negativa: registra `BONIFICACION_INDEXACION` mediante
  movimiento financiero y aplicaciones contra saldos vivos.
- `PUNITORIO` es la composición persistida de mora en V1. `INTERES_MORA` no se
  usa como concepto activo de mora persistida.
- La mora dinámica de lectura puede mostrarse en simulación o consultas; el
  `PUNITORIO` liquidado se persiste solo cuando corresponde por pago.
- La reversión V1 opera por pago agrupado completo y bloquea operaciones
  posteriores activas sobre obligaciones, composiciones, aplicaciones,
  movimientos o liquidaciones afectadas.
- El parámetro punitorio se resuelve por prioridad; permite definir tasa y días
  de gracia para la liquidación.

---

## 4. Patches SQL Relevantes

En bases existentes deben considerarse, como mínimo, estos patches recientes:

- `patch_dia_vencimiento_canon_20260501.sql`
- `patch_idempotencia_cronograma_locativo_20260501.sql`
- `patch_composicion_refresca_saldo_obligacion_20260504.sql`
- `patch_aplicacion_validacion_ignora_soft_deleted_20260505.sql`
- `patch_concepto_financiero_aplica_punitorio_20260505.sql`
- `patch_liquidacion_punitorio_20260505.sql`
- `patch_movimiento_financiero_pago_grupo_20260505.sql`
- `patch_parametro_punitorio_20260505.sql`

La aplicación concreta depende del estado de cada base. Los patches son la
referencia de compatibilidad para instalaciones que ya tenían schema previo.

---

## 5. Tests De Cierre

Al cierre del módulo, la suite completa pasó con:

```powershell
python -m pytest -q
```

Resultado:

```text
909 passed
```

---

## 6. Pendientes Futuros No Bloqueantes

- CRUD de `parametro_punitorio`
- no solapamiento formal de parámetros punitorios
- saldo a favor formal
- estado de cuenta más expresivo
- comprobante oficial/fiscal
- reversión histórica con recomputación
- tabla para vínculo 1:N de reemplazos si se requiere

---

## 7. Decisiones Explícitas

- No se implementa comprobante fiscal en V1.
- No se implementa composición negativa.
- No se implementa reversión parcial.
- No se implementa recomputación histórica.
- No se usa `INTERES_MORA` como concepto activo en V1.

