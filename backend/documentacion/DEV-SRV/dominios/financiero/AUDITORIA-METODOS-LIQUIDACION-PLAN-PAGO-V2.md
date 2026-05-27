# AUDITORIA-METODOS-LIQUIDACION-PLAN-PAGO-V2

## 1. Resumen ejecutivo

- Esta auditoría confirma que en Plan Pago V2 hoy hay implementación efectiva de: **precio fijo/contado** (vía bloque `CONTADO` en método por bloques), **cuotas iguales simples sin interés** y **anticipo + cuotas iguales simples**.
- El método **plan por bloques** (`PLAN_POR_BLOQUES`) está operativo con generación y preview; soporta tipos de bloque `CONTADO`, `ANTICIPO`, `TRAMO_CUOTAS`, `REFUERZO`, `SALDO`, pero no todos están materializados con la misma profundidad funcional en endpoints dedicados.
- No se encontró implementación de cálculo para **interés directo**, **indexación por índice** (CAC/IPC/UVA dentro de Plan Pago V2), **anticipo + cuotas indexadas**, **cuotas escalonadas por tasa o tramo no simple**, ni **combinaciones por bloques con motor de estrategia explícito por método financiero**.
- Existen endpoints financieros de **ajuste/bonificación de indexación sobre obligación existente**, pero eso no equivale a método de liquidación de Plan Pago V2 al alta del cronograma.

## 2. Estado actual de Plan Pago V2

- Dominio principal: **comercial** para definición/alta del plan y bloques; materialización de deuda en **financiero** (`obligacion_financiera`, `composicion_obligacion`) vía repositorio V2.
- El flujo V2 vigente: validar command -> construir preview (bloques/obligaciones) -> persistir `plan_pago_venta` + `plan_pago_venta_bloque` + `generacion_cronograma_financiero` + obligaciones/composiciones/obligados.
- `plan_pago_venta` es cabecera comercial (no deuda); la deuda exigible vive en `obligacion_financiera`.

## 3. Inventario de endpoints

### 3.1 Endpoints Plan Pago V2 (comercial)

1. `POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview`
   - Handler: `preview_plan_pago_venta_v2_por_bloques`.
   - Naturaleza: `PREVIEW_READLIKE` (sin persistencia de plan/obligaciones).
2. `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar`
   - Handler: `generate_plan_pago_venta_v2_por_bloques`.
   - Naturaleza: write de negocio sincronizable (headers CORE-EF requeridos).
3. `POST /api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`
   - Handler: `generate_plan_pago_venta_cuotas_iguales_simple`.
   - Naturaleza: write de negocio sincronizable.
4. `POST /api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales`
   - Handler: `generate_plan_pago_venta_anticipo_mas_cuotas_iguales`.
   - Naturaleza: write de negocio sincronizable.

### 3.2 Endpoints financiero relacionados (impacto, no método de alta Plan V2)

- Existen endpoints de ajuste/bonificación por indexación en obligaciones financieras ya emitidas, pero no constituyen alta de método de liquidación Plan Pago V2.

## 4. Inventario de servicios/commands

- `BuildPlanPagoVentaV2PorBloquesPreviewService`: valida bloques y arma obligaciones simuladas (contado/anticipo/tramo/refuerzo/saldo).
- `GeneratePlanPagoVentaV2PorBloquesService`: persiste plan por bloques y materializa obligaciones.
- `GeneratePlanPagoVentaCuotasIgualesSimpleService`: método dedicado `CUOTAS_IGUALES_SIMPLE`.
- `GeneratePlanPagoVentaAnticipoMasCuotasIgualesService`: método dedicado `ANTICIPO_MAS_CUOTAS_IGUALES`.
- Repositorio común: `PlanPagoVentaV2Repository` para persistencia de plan, bloques, generación cronograma y obligaciones.

## 5. Inventario de tablas

- `plan_pago_venta`: cabecera/regla comercial del plan, con `metodo_plan_pago`, monto, periodicidad, anticipo, etc.
- `plan_pago_venta_bloque`: estructura comercial por bloque (`CONTADO`, `ANTICIPO`, `TRAMO_CUOTAS`, `REFUERZO`, `SALDO`).
- `generacion_cronograma_financiero`: corrida técnica/idempotente de generación.
- `obligacion_financiera`: deuda materializada, con trazabilidad a plan/generación/bloque.
- `composicion_obligacion`: componentes monetarios de cada obligación.

## 6. Inventario de tests

Cobertura principal identificada:
- `test_plan_pago_venta_v2_bloques_unificado.py`
- `test_plan_pago_venta_v2_bloques_preview.py`
- `test_plan_pago_venta_v2_cuotas_iguales.py`
- `test_plan_pago_venta_v2_anticipo_mas_cuotas.py`
- `test_schema_cronograma_v2.py`
- `test_ventas_detalle_integral.py` (integración consumo de plan V2)

No se encontró suite específica para métodos de interés directo/indexación como método de alta de Plan V2.

## 7. Matriz de métodos de liquidación

| Método | Estado | Evidencia resumida |
|---|---|---|
| precio fijo / contado | **IMPLEMENTADO** | Vía `PLAN_POR_BLOQUES` + bloque `CONTADO` validado en preview y generación. |
| anticipo + saldo | **PARCIAL** | Soportado por bloques `ANTICIPO` + `SALDO` en motor por bloques; endpoint dedicado existente es anticipo + cuotas iguales (no saldo único dedicado). |
| cuotas iguales simples sin interés | **IMPLEMENTADO** | Servicio y endpoint dedicados `CUOTAS_IGUALES_SIMPLE`. |
| interés directo | **NO IMPLEMENTADO** | Sin método, endpoint, command ni cálculo de tasa/interés en Plan V2. |
| indexación por índice | **NO IMPLEMENTADO** | Sin método de alta V2 por índice; solo ajustes financieros posteriores sobre obligaciones. |
| anticipo + cuotas indexadas | **NO IMPLEMENTADO** | No hay cálculo/indexador en generación V2. |
| cuotas escalonadas | **PARCIAL** | Bloques múltiples permiten estructurar tramos; no hay método formal con semántica de escalonamiento/tasa. |
| saldo extraordinario / refuerzos | **PARCIAL** | Tipo bloque `REFUERZO` y `SALDO` permitido en preview/tabla; falta endpoint/método formal y cobertura amplia de negocio. |
| combinaciones por bloques | **PARCIAL** | `PLAN_POR_BLOQUES` ya combina bloques; falta catálogo formal de estrategias y reglas avanzadas (interés/indexación). |

## 8. Brechas por método

1. **Interés directo**
   - Falta contrato API (payload tasa/base/período/regla redondeo interés).
   - Falta servicio de cálculo y trazabilidad de componentes (capital vs interés) en `composicion_obligacion`.
   - Falta método permitido en `plan_pago_venta.metodo_plan_pago` y tests.

2. **Indexación por índice (CAC/IPC/UVA)**
   - Falta modelado de índice fuente, fecha/base, lag, regla de actualización y congelamiento.
   - Falta semántica de componente indexatorio en generación inicial.
   - Falta estrategia de re-cálculo/versionado de obligaciones futuras.

3. **Anticipo + cuotas indexadas**
   - Combina brechas de anticipo actual + motor indexado por tramo.
   - Falta contrato para fijar anticipo nominal y saldo indexable.

4. **Cuotas escalonadas**
   - Falta método explícito (escalones por monto/tasa/plazo), hoy solo aproximable manualmente con bloques.

5. **Saldo extraordinario / refuerzos**
   - Falta endpoint dedicado o reglas de validación de refuerzos dentro del flujo formal de generación.
   - Falta cobertura de tests de idempotencia/compatibilidad para patrones combinados con refuerzo.

## 9. Propuesta de arquitectura para métodos extensibles

Recomendación para esta etapa de diseño:

- **Modelo híbrido**: `strategy por método` + persistencia en bloques parametrizados.
  1. Mantener `plan_pago_venta` como cabecera y agregar nuevos códigos de `metodo_plan_pago` cuando se implemente cada método.
  2. Mantener `plan_pago_venta_bloque` como representación estructural común.
  3. Crear capa `LiquidationStrategy` por método (ej. `ContadoStrategy`, `CuotasIgualesStrategy`, `InteresDirectoStrategy`, `IndexadoStrategy`, `AnticipoIndexadoStrategy`).
  4. Cada strategy produce un **PlanResult canónico** (bloques + obligaciones previstas + componentes).
  5. El repositorio V2 persiste desde ese resultado canónico sin conocer reglas financieras específicas.

- **No recomendado como núcleo único**: configuración JSON libre sin estrategia tipada (riesgo de semántica difusa y validaciones débiles).

## 10. Roadmap de implementación

1. **Fase 0 (documental/contrato)**
   - Especificar contratos de método (request/response) y matriz CORE-EF por endpoint write nuevo.
2. **Fase 1 (interés directo)**
   - Nuevo método + strategy + tests unitarios/integración + composición capital/interés.
3. **Fase 2 (indexación base)**
   - Strategy indexada + referencia de índice + tests de recalculo/versionado.
4. **Fase 3 (combinados)**
   - Anticipo + indexadas; refuerzos formales; escalonadas tipadas.
5. **Fase 4 (hardening)**
   - Idempotencia avanzada por payload equivalente, conflictos de plan vivo, regresión integral.

## 11. Riesgos

- Riesgo de mezclar semántica comercial con financiera si cálculo detallado queda en router/repository.
- Riesgo de inconsistencias si se agrega método sin ampliar `metodo_plan_pago` + tests + constraints.
- Riesgo de sobreprometer indexación usando endpoints de ajuste financiero que no son alta de plan.
- Riesgo de deuda técnica si se fuerza configuración libre sin estrategias tipadas.

## 12. Comandos ejecutados

- `rg --files | rg 'AGENTS.md|comercial_router.py|financiero_router.py'`
- `rg -n "plan pago v2|plan-pago-v2|plan_pago_venta|..." backend/app backend/tests backend/database backend/documentacion/DEV-SRV backend/documentacion/CORE-EF backend/documentacion/issues`
- `sed -n '1,260p' backend/app/api/routers/financiero_router.py`
- `sed -n '1,260p' backend/app/api/routers/comercial_router.py`
- `rg -n "plan-pago-v2|cuotas-iguales|anticipo-mas-cuotas|preview|..." backend/app/api/routers/comercial_router.py backend/app/application/comercial backend/app/infrastructure/persistence/repositories/plan_pago_venta_v2_repository.py backend/tests`
- `nl -ba backend/app/api/routers/comercial_router.py | sed -n '2260,2565p'`
- `nl -ba backend/app/application/comercial/services/generate_plan_pago_venta_v2_por_bloques_service.py | sed -n '1,320p'`
- `nl -ba backend/app/application/comercial/services/build_plan_pago_venta_v2_por_bloques_preview_service.py | sed -n '1,340p'`
- `rg -n "CREATE TABLE .*plan_pago_venta|plan_pago_venta_bloque|obligacion_financiera|composicion_obligacion|generacion_cronograma_financiero" backend/database`
- `rg -n "plan-pago-v2|cuotas_iguales_simple|anticipo_mas_cuotas|PLAN_POR_BLOQUES|BLOQUE|preview_plan_pago" backend/tests`
- `nl -ba backend/app/application/comercial/services/generate_plan_pago_venta_cuotas_iguales_simple_service.py | sed -n '1,180p'`
- `nl -ba backend/app/application/comercial/services/generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service.py | sed -n '1,220p'`
- `nl -ba backend/database/patch_plan_pago_venta_bloques_v2_20260515.sql | sed -n '1,290p'`
- `nl -ba backend/database/patch_plan_pago_venta_cronograma_v2_20260514.sql | sed -n '54,220p'`
