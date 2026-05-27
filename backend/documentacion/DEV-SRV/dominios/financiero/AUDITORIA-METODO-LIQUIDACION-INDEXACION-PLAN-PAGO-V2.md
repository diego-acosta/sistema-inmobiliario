# AUDITORIA / DISENO TECNICO
## Metodo de liquidacion `INDEXACION` por bloque/tramo en Plan Pago V2

- Fecha: 2026-05-27
- Tipo: Documental / tecnico (sin cambios de codigo, SQL ni tests)
- Dominio: comercial (regla de plan por bloques) + financiero (materializacion de obligaciones y composiciones)
- Alcance evaluado: Plan Pago V2 `PLAN_POR_BLOQUES`, con foco en bloques `TRAMO_CUOTAS`.

---

## 0) Contexto verificado en implementacion actual

Estado ya vigente en repo:

1. `PLAN_POR_BLOQUES` es el `metodo_plan_pago` usado por el flujo V2 por bloques.
2. `metodo_liquidacion` vive en `plan_pago_venta_bloque` (no a nivel global de plan).
3. `INTERES_DIRECTO` esta implementado para `TRAMO_CUOTAS` en preview/generate y persistencia de bloque.
4. Preview ya expone `total_calculado` (capital base) y `total_con_interes`.

No se relevo implementacion de `INDEXACION` en este flujo; queda como `PENDIENTE / NO IMPLEMENTADO`.

---

## A) Estado actual (auditoria)

### A.1 SQL de plan por bloques y liquidacion actual

Se relevo patch de soporte fisico vigente para bloque:

- `plan_pago_venta_bloque` tiene hoy columnas para `metodo_liquidacion` y parametros de `INTERES_DIRECTO`:
  - `metodo_liquidacion`
  - `tasa_interes_directo_periodica`
  - `cantidad_periodos`
  - `base_calculo_interes`
- Restricciones SQL actuales:
  - `metodo_liquidacion` permitido: `SIN_INTERES` o `INTERES_DIRECTO` (o `NULL`).
  - Si `metodo_liquidacion='INTERES_DIRECTO'`, exige `tipo_bloque='TRAMO_CUOTAS'` y los 3 parametros minimos no nulos.

Conclusion: no existe soporte SQL de `INDEXACION` en bloque actualmente.

### A.2 Backend de Plan Pago V2 por bloques

Se relevo:

- command input de bloque con parametros de `INTERES_DIRECTO` y sin parametros de indexacion;
- preview service que:
  - valida `metodo_liquidacion` de tramo;
  - rechaza cualquier metodo distinto de `INTERES_DIRECTO`;
  - calcula `total_con_interes` cuando aplica interes directo;
- generate service que propaga/guarda parametros actuales de bloque;
- repository V2 que inserta/lee/compatibiliza campos actuales de bloque.

Conclusion: `INDEXACION` no esta soportado en contrato interno command/schema/service/repository.

### A.3 Indices financieros y valores por fecha

Resultado del relevamiento de SQL/backend:

- No se encontro tabla/catalogo operativo llamado `indice_financiero` en schema principal auditado.
- No se encontro tabla historica de valores de indice (por ejemplo, `indice_financiero_valor`, `historico_indice`, etc.) en el alcance auditado.
- No se encontro query/repository de consulta de indice por fecha para Plan Pago V2 por bloques.

Estado: para este alcance, el soporte de indice financiero por fecha queda `NO CONFIRMADO / PENDIENTE`.

### A.4 Conceptos financieros relacionados

Si se identifico en seed/catalogo financiero el concepto:

- `AJUSTE_INDEXACION` (tipo ajuste/debito), reutilizable para modelar diferencia por indexacion en composicion.

Esto permite una estrategia de composicion separada (capital + ajuste) sin redefinir semantica de capital.

---

## B) Modelo conceptual propuesto

Definicion objetivo (sin implementacion en este PR):

```text
PLAN_POR_BLOQUES
  TRAMO_CUOTAS
    metodo_liquidacion = INDEXACION
```

Reglas de modelo:

1. `INDEXACION` se define como **metodo_liquidacion de bloque/tramo**, no como `metodo_plan_pago` global.
2. No requiere endpoint nuevo; se propaga en el endpoint unificado existente de preview/generate V2.
3. Debe convivir con `INTERES_DIRECTO` a nivel de sistema.
4. En un mismo bloque `TRAMO_CUOTAS`, para primera etapa, **no combinar** simultaneamente `INTERES_DIRECTO` + `INDEXACION`.
   - Composiciones mixtas quedan fuera de alcance y `PENDIENTE` de decision futura explicita.

---

## C) Campos minimos requeridos

### C.1 Candidatos funcionales minimos

Para `metodo_liquidacion = INDEXACION`:

- `id_indice_financiero` o `codigo_indice_financiero`
- `fecha_base_indice`
- `valor_base_indice`
- `fecha_aplicacion_indice`
- `valor_aplicado_indice`
- `modo_indexacion`
- `base_calculo_indexacion`
- `periodicidad_actualizacion`
- `politica_valor_no_disponible`
- `tipo_generacion_indexada` (`PROYECTADA` / `DEFINITIVA` / `RECALCULABLE`)
- `conserva_capital_original`
- `genera_ajuste_por_diferencia`

### C.2 Recomendacion de modelado fisico

**Recomendado para etapa 1:** tabla hija `plan_pago_venta_bloque_indexacion` (1:1 opcional por bloque).

Razon:

- evita ensanchar excesivamente `plan_pago_venta_bloque` con columnas que no aplican a otros metodos;
- mantiene compatibilidad y legibilidad de constraints condicionales;
- permite evolucion futura (nuevas politicas, versionado de parametros) sin degradar el nucleo comun del bloque.

Alternativa valida (menos recomendable): agregar todas las columnas directo en `plan_pago_venta_bloque` con checks condicionales por metodo.

---

## D) Decisiones abiertas (pendientes o recomendadas)

1. **Cuotas proyectadas vs capital base + ajuste futuro**
   - Recomendacion etapa 1: capital base + ajuste explicito (ver estrategia E).

2. **Momento de recalculo (vencimiento/pago/job mensual)**
   - `PENDIENTE`.
   - Recomendacion inicial: definir modo unico por release para evitar ambiguedad operativa.

3. **Congelamiento de valor indice al generar obligacion**
   - Recomendacion etapa 1: soportar `tipo_generacion_indexada=DEFINITIVA` con congelamiento explicito del valor aplicado al momento de generar.

4. **Composicion de obligacion indexada**
   - Recomendado: conservar `CAPITAL_VENTA` + agregar `AJUSTE_INDEXACION` (en lugar de reescribir capital).

5. **Base de aplicacion del indice**
   - `PENDIENTE` entre: capital inicial bloque / saldo bloque / cuota base / saldo vivo.
   - Recomendacion inicial: `CAPITAL_INICIAL_BLOQUE` para reducir complejidad.

6. **Preview: ultimo indice disponible vs proyectado**
   - Recomendacion inicial: ultimo indice disponible (modo deterministico y auditable).

7. **Falta de valor de indice para fecha objetivo**
   - Recomendacion inicial: error controlado (no inferir silenciosamente), salvo politica explicita configurada.

8. **Idempotencia cuando cambia valor del indice**
   - Recomendacion: incluir en clave/compatibilidad tecnica los parametros de indexacion y referencia de valor aplicado (fecha/valor/fuente) cuando sea `DEFINITIVA`.

---

## E) Estrategia recomendada para primera implementacion

Se recomienda estrategia **conservadora y compatible**:

1. Mantener `monto_total_plan` y `total_calculado` como capital base.
2. Extender preview con `total_indexado` o `total_con_indexacion` sin romper campos existentes.
3. Para generate, preferir composicion separada por obligacion:
   - `CAPITAL_VENTA` (base)
   - `AJUSTE_INDEXACION` (diferencia)
4. Evitar mutar el capital base historico una vez emitida la obligacion.

Motivo:

- preserva trazabilidad contable y semantica actual de capital;
- minimiza regresiones sobre flujos actuales y sobre `INTERES_DIRECTO`;
- facilita conciliacion, auditoria y eventuales reversas del ajuste.

---

## F) Impacto SQL (para implementacion futura)

### F.1 Hace falta patch SQL

**Si.** Para soportar `INDEXACION` por bloque/tramo en forma robusta hace falta patch SQL.

### F.2 Opcion recomendada

Crear tabla hija `plan_pago_venta_bloque_indexacion` con FK unica a `plan_pago_venta_bloque`.

Minimo sugerido:

- FK: `id_plan_pago_venta_bloque` (`UNIQUE`, `NOT NULL`, `ON DELETE` segun politica vigente).
- Identificacion indice: `id_indice_financiero` o `codigo_indice_financiero`.
- Parametros base/aplicacion: fechas/valores base y aplicados.
- Politicas: modo/base/periodicidad/politica faltante/tipo generacion.
- Flags: `conserva_capital_original`, `genera_ajuste_por_diferencia`.

### F.3 Constraints sugeridos

- check de enum cerrados para modo/base/politica/tipo_generacion;
- check de coherencia fecha/valor (`fecha_*` con `valor_*` correspondientes);
- check de no negativos para valores monetarios/indices;
- check de exclusividad semantica por bloque:
  - si bloque `metodo_liquidacion='INDEXACION'` => debe existir fila hija;
  - si no es `INDEXACION` => no debe existir fila hija.

### F.4 Indices sugeridos

- indice por `id_plan_pago_venta_bloque` (unique);
- indice por `codigo_indice_financiero`/`id_indice_financiero`;
- indice compuesto por fechas de aplicacion si se consulta por periodo.

### F.5 Compatibilidad legacy

- mantener `metodo_liquidacion` nullable y sin exigir indexacion a bloques existentes;
- no alterar semantica de planes legacy ni de bloques no indexados;
- no cambiar `metodo_plan_pago` global.

---

## G) Impacto API/app (propagacion futura)

Sin endpoint nuevo, se requiere extender flujo existente:

1. **Request schema**: campos de indexacion en bloque `TRAMO_CUOTAS`.
2. **Response schema**: exponer parametros de indexacion y total indexado en preview.
3. **Command**: agregar campos de indexacion al input de bloque.
4. **Preview service**: validaciones + calculo `total_indexado/total_con_indexacion`.
5. **Generate service**: propagacion a repository + composicion financiera esperada.
6. **Repository**: persistencia/lectura/compatibilidad idempotente de datos indexacion.
7. **Tests**: cobertura dedicada sin romper escenarios actuales.

---

## H) Tests futuros requeridos (implementacion posterior)

Minimo:

1. preview legacy no cambia.
2. generate legacy no cambia.
3. `INDEXACION` sin indice => `VALIDATION_ERROR`.
4. indice inexistente => `VALIDATION_ERROR` o `NOT_FOUND` segun contrato final.
5. falta valor de indice para fecha => error controlado.
6. preview calcula `total_indexado`/`total_con_indexacion`.
7. generate persiste parametros de indexacion.
8. generate genera composiciones esperadas (`CAPITAL_VENTA` + `AJUSTE_INDEXACION`) si aplica.
9. idempotencia: mismo payload + mismo valor indice => reutiliza/consistente.
10. incompatibilidad si cambia indice/campos indexacion para misma clave funcional.
11. no regresion de `INTERES_DIRECTO`.

---

## I) Decision CORE-EF

- PR actual (documental): **NO APLICA endpoint write**.
- Futuro endpoint preview (mismo recurso existente): **PREVIEW_READLIKE**.
- Futuro endpoint generate (mismo recurso existente): **COMMAND_WRITE_NEGOCIO**.
- La implementacion futura debe cumplir checklist CORE-EF de AGENTS.md seccion 14 (headers, idempotencia, versionado, rollback, outbox si aplica, y tests minimos de contrato write).

---

## Roadmap propuesto

1. Definir decision funcional cerrada (seccion D) y contrato de errores.
2. Diseñar patch SQL (tabla hija recomendada) + constraints/indices.
3. Propagar schema/command/preview/generate/repository.
4. Incorporar tests de no regresion + nuevos casos INDEXACION.
5. Documentar DEV-API/DEV-SRV con contrato final y ejemplos.

---

## Estado final de esta auditoria

- `INDEXACION` en Plan Pago V2 por bloques: **PENDIENTE DE IMPLEMENTACION**.
- Recomendacion tecnica para primera etapa: **capital base + composicion de ajuste separada (`AJUSTE_INDEXACION`)**, sin cambiar `metodo_plan_pago` global ni crear endpoint nuevo.
