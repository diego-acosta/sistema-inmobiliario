# Auditoría Plan Pago V2 — método_liquidacion por bloque/tramo

Fecha: 2026-05-27

## Alcance auditado
- `plan_pago_venta_bloque` (SQL patch vigente)
- `PlanPagoVentaV2Repository`
- `BuildPlanPagoVentaV2PorBloquesPreviewService`
- `GeneratePlanPagoVentaV2PorBloquesService`
- tests V2 de bloques/preview

## 1) Campos existentes hoy

### 1.1 Tabla `plan_pago_venta_bloque`
Campos funcionales actuales:
- Identidad/auditoría: `id_plan_pago_venta_bloque`, `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Negocio bloque: `id_plan_pago_venta`, `numero_bloque`, `tipo_bloque`, `etiqueta_bloque`, `clave_bloque`.
- Estructura financiera actual: `cantidad_cuotas`, `importe_total_bloque`, `importe_cuota`, `fecha_vencimiento`, `fecha_primer_vencimiento`, `periodicidad`, `regla_redondeo`, `concepto_financiero_codigo`, `observaciones`.

Restricciones relevantes:
- `tipo_bloque` acotado a `CONTADO|ANTICIPO|TRAMO_CUOTAS|REFUERZO|SALDO`.
- Para `TRAMO_CUOTAS` exige `cantidad_cuotas`, `importe_cuota`, `fecha_primer_vencimiento`, `periodicidad`.
- Para pagos únicos (`CONTADO|ANTICIPO|REFUERZO|SALDO`) exige `importe_total_bloque` y `fecha_vencimiento`.

### 1.2 Comando/preview/service/repository
- `PlanPagoVentaBloqueInput` no incluye `metodo_liquidacion`.
- El preview valida `TRAMO_CUOTAS` por dos contratos: legacy (`importe_cuota`) o capital total (`importe_total_bloque`), sin campo explícito de método.
- El generate service persiste bloque con los campos actuales; no persiste método de liquidación.
- El repository inserta/lee/compara compatibilidad de bloques sin `metodo_liquidacion`.

### 1.3 Tests existentes
- Hay tests que consolidan compatibilidad legacy por `importe_cuota`.
- Hay tests de tramo por capital total (ajuste de redondeo última cuota).
- No hay tests que distingan estrategias por un campo `metodo_liquidacion` persistido en bloque.

## 2) Campos faltantes para `metodo_liquidacion` por bloque

Para soportar explícitamente `INTERES_DIRECTO` como método de `TRAMO_CUOTAS` dentro de `PLAN_POR_BLOQUES`, faltan:

1. **Campo en modelo físico de bloque**:
   - `metodo_liquidacion` (sugerido `varchar(40)`), nullable para compatibilidad.
2. **Regla SQL condicionada por tipo de bloque**:
   - Si `tipo_bloque='TRAMO_CUOTAS'`, definir obligatoriedad/control de dominio de `metodo_liquidacion`.
3. **Propagación en capa app**:
   - `PlanPagoVentaBloqueInput`.
   - Payload de upsert de bloque (`PlanPagoVentaBloqueUpsertPayload`) y su persistencia en repository.
   - Comparadores de compatibilidad/idempotencia de bloque existentes.
4. **Contrato de salida**:
   - incluir `metodo_liquidacion` en respuestas de bloque (preview y generate) para trazabilidad funcional.

## 3) ¿Hace falta patch SQL?

**Sí, hace falta patch SQL** para introducir `metodo_liquidacion` en `plan_pago_venta_bloque` y sus constraints, porque hoy no existe columna para persistir ni validar ese dato en el modelo físico.

Adicionalmente, se recomienda patch complementario de backfill lógico:
- Bloques existentes `TRAMO_CUOTAS` sin columna previa deben quedar con semántica legacy (`NO_CONFIRMADO` / nulo permitido transitoriamente) para evitar ruptura de compatibilidad inmediata.

## 4) Compatibilidad con bloques existentes

Estrategia sugerida (sin romper lo actual):

1. **Fase 1 (compatibilidad)**
   - Agregar columna nullable.
   - No exigirla para registros existentes.
   - Mantener cálculo actual cuando `metodo_liquidacion` sea `NULL` (compatibilidad heredada).

2. **Fase 2 (adopción controlada)**
   - En requests nuevos, permitir y validar `metodo_liquidacion` en `TRAMO_CUOTAS`.
   - `INTERES_DIRECTO` se enruta por feature flag/regla de dominio sin eliminar legacy.

3. **Fase 3 (endurecimiento opcional)**
   - Cuando todo cliente emita método explícito, endurecer constraint para `TRAMO_CUOTAS` nuevos (o vía validación de servicio) y definir migración de históricos si corresponde.

Principio: **legacy no puede convertirse en modelo principal**, pero tampoco debe romperse mientras no haya migración funcional completa.

## 5) Tests a agregar

### 5.1 Unit/service preview
- `TRAMO_CUOTAS` con `metodo_liquidacion='INTERES_DIRECTO'` → acepta contrato y enruta por rama esperada (aunque cálculo final aún pendiente si requiere más SQL).
- `TRAMO_CUOTAS` con método inválido → error de validación.
- `TRAMO_CUOTAS` sin método (compat legacy) → comportamiento actual intacto.

### 5.2 Repository
- Persistencia/lectura de `metodo_liquidacion` en `get_or_create_plan_pago_venta_bloque`.
- Compatibilidad `_ensure_plan_pago_venta_bloque_compatible` debe incluir el nuevo campo (detecta conflicto si cambia).

### 5.3 Integración endpoint generate/preview existentes
- Respuesta incluye `metodo_liquidacion` por bloque.
- Reintento idempotente con mismo bloque+método no falla.
- Mismo `clave_bloque` con distinto `metodo_liquidacion` falla con incompatibilidad esperada.

### 5.4 SQL/integración DB
- Constraint de dominio de `metodo_liquidacion` aplicado según `tipo_bloque`.
- Inserciones legacy no tramo siguen válidas sin exigir el campo.

## 6) Decisión CORE-EF (AGENTS §14)

Como este alcance es de auditoría técnica para cambios internos de modelo/servicio y **no crea endpoint nuevo**:

- Clasificación endpoint: `NO_CONFIRMADO` (no hay endpoint write nuevo/modificado en este entregable).
- Headers CORE-EF write (`X-Op-Id`, etc.): `NO APLICA` en esta auditoría (sin cambio de contrato HTTP).
- `If-Match-Version`: `NO APLICA` en esta auditoría.
- Idempotencia/outbox/lock/versionado transaccional: **deben documentarse** cuando se implemente efectivamente un write endpoint o se modifique uno existente; en esta auditoría quedan `PENDIENTE`.
- Tests CORE-EF mínimos de write: `NO APLICA` en este entregable porque no se tocó endpoint.

## Estado de implementación respecto al objetivo

- `INTERES_DIRECTO` como `metodo_liquidacion` de `TRAMO_CUOTAS` en `PLAN_POR_BLOQUES`: **pendiente**.
- Requisito previo detectado: **patch SQL obligatorio** + propagación de contrato interno en comando/repository/services/tests.
