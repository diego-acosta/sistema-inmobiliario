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

## 2) Campos faltantes para liquidación por bloque (INTERES_DIRECTO)

Para soportar explícitamente `INTERES_DIRECTO` como método de `TRAMO_CUOTAS` dentro de `PLAN_POR_BLOQUES`, y conforme `METODO-PLAN-PAGO-INTERES-DIRECTO.md`, faltan **parámetros mínimos por bloque/tramo**:

1. **Campos en modelo físico de bloque** (propuestos, nullable por compatibilidad):
   - `metodo_liquidacion`
   - `tasa_interes_directo_periodica`
   - `cantidad_periodos`
   - `base_calculo_interes`
2. **Reglas SQL condicionadas por tipo de bloque/método**:
   - Si `tipo_bloque='TRAMO_CUOTAS'` y `metodo_liquidacion='INTERES_DIRECTO'`, exigir/validar `tasa_interes_directo_periodica`, `cantidad_periodos` y `base_calculo_interes`.
   - Para otros métodos (o legado sin método), estos parámetros pueden no aplicar y deben seguir estrategia compatible.
3. **Propagación en capa app (command/schema)**:
   - `PlanPagoVentaBloqueInput` y schemas HTTP de preview/generate para aceptar los cuatro campos.
   - Validaciones condicionadas en preview para exigir mínimos solo cuando método sea `INTERES_DIRECTO`.
4. **Propagación en repository**:
   - Payload de upsert de bloque (`PlanPagoVentaBloqueUpsertPayload`) + SQL de insert/select + comparadores de compatibilidad/idempotencia (`_ensure_plan_pago_venta_bloque_compatible`).
5. **Preview/generación y contrato de salida**:
   - Incluir estos campos en respuesta de bloque (preview y generate) para trazabilidad funcional del tramo.
   - La liquidación de `INTERES_DIRECTO` requiere esos parámetros, aunque otros métodos de liquidación puedan no usarlos.

## 3) ¿Hace falta patch SQL?

**Sí, hace falta patch SQL** para introducir en `plan_pago_venta_bloque` los cuatro campos mínimos de `INTERES_DIRECTO`:
- `metodo_liquidacion`
- `tasa_interes_directo_periodica`
- `cantidad_periodos`
- `base_calculo_interes`

Además del alta de columnas, el patch debe incorporar constraints condicionales por `tipo_bloque`/`metodo_liquidacion` para que los parámetros mínimos sean obligatorios cuando aplique `INTERES_DIRECTO`, sin romper métodos/bloques que no los usan.

Adicionalmente, se recomienda patch complementario de backfill lógico:
- Bloques existentes `TRAMO_CUOTAS` deben conservar compatibilidad (columnas nullable y/o default compatible), evitando ruptura inmediata de contratos legacy.

## 4) Compatibilidad con bloques existentes

Estrategia sugerida (sin romper lo actual):

1. **Fase 1 (compatibilidad)**
   - Agregar columnas nuevas como nullable.
   - No exigir parámetros de `INTERES_DIRECTO` para registros existentes.
   - Mantener comportamiento actual cuando `metodo_liquidacion` sea `NULL` o no `INTERES_DIRECTO` (compatibilidad heredada).

2. **Fase 2 (adopción controlada)**
   - En requests nuevos, permitir y validar `metodo_liquidacion` en `TRAMO_CUOTAS`.
   - Si `metodo_liquidacion=INTERES_DIRECTO`, exigir `tasa_interes_directo_periodica`, `cantidad_periodos`, `base_calculo_interes`.
   - Mantener coexistencia con métodos no `INTERES_DIRECTO` y legacy sin método explícito.

3. **Fase 3 (endurecimiento opcional)**
   - Cuando todo cliente emita método/parámetros explícitos, endurecer constraints para `TRAMO_CUOTAS` nuevos y definir migración de históricos si corresponde.

Principio: **legacy no puede convertirse en modelo principal**, pero tampoco debe romperse mientras no haya migración funcional completa.

## 5) Tests a agregar

### 5.1 Unit/service preview
- `TRAMO_CUOTAS` con `metodo_liquidacion='INTERES_DIRECTO'` y parámetros mínimos completos (`tasa_interes_directo_periodica`, `cantidad_periodos`, `base_calculo_interes`) → acepta contrato y enruta por rama esperada.
- `TRAMO_CUOTAS` con `metodo_liquidacion='INTERES_DIRECTO'` y falta de parámetros mínimos → error de validación.
- `TRAMO_CUOTAS` con método inválido → error de validación.
- `TRAMO_CUOTAS` sin método (compat legacy) → comportamiento actual intacto.

### 5.2 Repository
- Persistencia/lectura de los cuatro campos en `get_or_create_plan_pago_venta_bloque`.
- Compatibilidad `_ensure_plan_pago_venta_bloque_compatible` debe incluir los cuatro campos (detecta conflicto si cambian).

### 5.3 Integración endpoint generate/preview existentes
- Respuesta incluye los cuatro campos por bloque.
- Reintento idempotente con mismo bloque+método+parámetros no falla.
- Mismo `clave_bloque` con distinto método o distinto parámetro mínimo falla con incompatibilidad esperada.

### 5.4 SQL/integración DB
- Constraint de dominio de `metodo_liquidacion` aplicado según `tipo_bloque`.
- Constraint condicional de parámetros mínimos cuando `metodo_liquidacion=INTERES_DIRECTO`.
- Inserciones legacy y métodos no `INTERES_DIRECTO` siguen válidos sin exigir parámetros no aplicables.

## 6) Decisión CORE-EF (AGENTS §14)

Como este alcance es de auditoría técnica para cambios internos de modelo/servicio y **no crea endpoint nuevo**:

- Clasificación endpoint: `NO_CONFIRMADO` (no hay endpoint write nuevo/modificado en este entregable).
- Headers CORE-EF write (`X-Op-Id`, etc.): `NO APLICA` en esta auditoría (sin cambio de contrato HTTP).
- `If-Match-Version`: `NO APLICA` en esta auditoría.
- Idempotencia/outbox/lock/versionado transaccional: **deben documentarse** cuando se implemente efectivamente un write endpoint o se modifique uno existente; en esta auditoría quedan `PENDIENTE`.
- Tests CORE-EF mínimos de write: `NO APLICA` en este entregable porque no se tocó endpoint.

## Estado de implementación respecto al objetivo

- `INTERES_DIRECTO` como `metodo_liquidacion` de `TRAMO_CUOTAS` en `PLAN_POR_BLOQUES`: **pendiente**.
- Requisito previo detectado: **patch SQL obligatorio** + propagación de contrato interno en command/schema/repository/preview/generate/tests para los 4 campos mínimos de INTERES_DIRECTO.
