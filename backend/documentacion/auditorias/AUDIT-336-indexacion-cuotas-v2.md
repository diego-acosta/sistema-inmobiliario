# AUDIT-336 — Indexación de cuotas V2

## 1. Objetivo

Auditar el estado real del backend y de la documentación antes de diseñar o implementar una V2 de indexación/actualización de cuotas de planes de pago de venta.

Este documento es **solo documental / auditoría técnica**. No diseña contrato definitivo, no modifica lógica de negocio, no cambia SQL estructural, no cambia endpoints y no toca frontend.

Clasificación de dominio:

- `plan_pago_venta` y `plan_pago_venta_bloque`: núcleo comercial para condiciones de venta y plan de pago de venta.
- `generacion_cronograma_financiero`, `obligacion_financiera`, `composicion_obligacion`, `obligacion_obligado`, índices y ajustes: núcleo financiero / soporte financiero de cronograma, deuda, componentes y trazabilidad.
- `AJUSTE_INDEXACION`: concepto financiero de composición/ajuste; no reemplaza por sí mismo la semántica comercial del plan ni la trazabilidad de índices.

## 2. Fuentes revisadas

### Backend

- Routers:
  - `backend/app/api/routers/comercial_router.py`
  - `backend/app/api/routers/financiero_router.py`
- Schemas/API:
  - `backend/app/api/schemas/comercial.py`
- Servicios comerciales de planes de pago V2:
  - `backend/app/application/comercial/services/generate_plan_pago_venta_cuotas_iguales_simple_service.py`
  - `backend/app/application/comercial/services/generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service.py`
  - `backend/app/application/comercial/services/build_plan_pago_venta_v2_por_bloques_preview_service.py`
  - `backend/app/application/comercial/services/generate_plan_pago_venta_v2_por_bloques_service.py`
  - `backend/app/application/comercial/services/get_plan_pago_venta_v2_integral_service.py`
- Servicios financieros relacionados:
  - `backend/app/application/financiero/services/indexacion_cuota_calculator.py`
  - `backend/app/application/financiero/services/aplicar_ajuste_indexacion_service.py`
  - `backend/app/application/financiero/services/aplicar_bonificacion_indexacion_service.py`
  - `backend/app/application/financiero/services/registrar_pago_persona_service.py`
  - `backend/app/application/financiero/services/create_imputacion_financiera_service.py`
- Repositorios:
  - `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
  - `backend/app/infrastructure/persistence/repositories/financiero_repository.py`
  - `backend/app/infrastructure/persistence/repositories/plan_pago_venta_v2_repository.py`
- SQL/seeds/patches:
  - `backend/database/seed_minimo.sql`
  - `backend/database/seed_test_baseline.sql`
  - `backend/database/patch_concepto_financiero_aplica_punitorio_20260505.sql`
  - `backend/database/patch_plan_pago_venta_bloque_indexacion_20260528.sql`
- Tests:
  - `backend/tests/test_plan_pago_venta_v2_cuotas_iguales.py`
  - `backend/tests/test_plan_pago_venta_v2_anticipo_mas_cuotas.py`
  - `backend/tests/test_plan_pago_venta_v2_bloques_preview.py`
  - `backend/tests/test_plan_pago_venta_v2_bloques_unificado.py`
  - `backend/tests/test_plan_pago_venta_v2_consulta_integral.py`
  - `backend/tests/test_indexacion_cuota_calculator.py`
  - `backend/tests/test_fin_registrar_pago_persona.py`
  - `backend/tests/test_reservas_venta_confirmar_venta_completa.py`
  - `backend/tests/test_ventas_directa_confirmar_venta_completa.py`

### Documentación

- Arquitectura obligatoria:
  - `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/analitico/DEV-ARCH-ANA-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`
- DEV-API:
  - `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
  - `backend/documentacion/DEV-API/dominios/financiero/DEV-API-FIN-001.md`
- DEV-SRV / auditorías previas:
  - `backend/documentacion/DEV-SRV/dominios/comercial/MODELO-PLANES-PAGO-VENTA.md`
  - `backend/documentacion/DEV-SRV/dominios/comercial/MODELO-PLANES-PAGO-VENTA-BLOQUES.md`
  - `backend/documentacion/DEV-SRV/dominios/comercial/DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/MODELO-FINANCIERO-FIN.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-006-cronograma-y-obligaciones.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-008-gestion-de-imputacion-financiera.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-METODOS-LIQUIDACION-PLAN-PAGO-V2.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-METODO-LIQUIDACION-INDEXACION-PLAN-PAGO-V2.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-FORMULA-INDEXACION-PLAN-PAGO-V2.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-SOPORTE-FISICO-INDICES-FINANCIEROS.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-OBLIGACION-FINANCIERA-CRONOGRAMA-V2.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-PREVIEW-PLAN-PAGO-V2-WIZARD-VENTA-COMPLETA.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-CUOTAS-REFUERZO-INTERNAS-PLAN-PAGO-V2.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-SQL-FIN.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/RN-FIN.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/TIPO-OBLIGACION-FIN.md`
- DER:
  - `backend/documentacion/DER/DER-COMERCIAL.md`
  - `backend/documentacion/DER/DER-FINANCIERO.md`

## 3. Estado implementado en backend

### Endpoints públicos relacionados con plan-pago-v2

Existen endpoints comerciales para consulta, preview y generación de planes V2:

- `GET /api/v1/ventas/{id_venta}/plan-pago-v2`.
- `POST /api/v1/ventas/plan-pago-v2/preview`.
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview`.
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar`.
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`.
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales`.

También existen endpoints financieros para operar ajuste/bonificación de indexación sobre obligaciones existentes:

- `POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/ajuste-indexacion`.
- `POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/bonificacion-indexacion`.

Estos endpoints financieros son capacidad real sobre obligaciones, pero no equivalen a una V2 completa de reindexación de cuotas de planes de pago de venta.

### Métodos de plan/generación relevados

- `CUOTAS_IGUALES_SIMPLE`: implementado como generación de plan y obligaciones con cuotas iguales simples.
- `ANTICIPO_MAS_CUOTAS_IGUALES`: implementado como generación con anticipo y cuotas posteriores.
- `PLAN_POR_BLOQUES`: implementado como plan V2 por bloques, con preview y generación.
- `SIN_INTERES`, `INTERES_DIRECTO` e `INDEXACION`: aparecen como métodos de liquidación por bloque/tramo en el modelo V2 por bloques. `INDEXACION` tiene soporte parcial/real, no una corrida de recalculo general de cuotas ya existentes.

### Soporte de indexación observado

Existe soporte backend para:

- Configuración de indexación por bloque (`plan_pago_venta_bloque_indexacion`).
- Catálogo/valores de índices (`indice_financiero`, `indice_financiero_valor`).
- Trazabilidad por obligación (`obligacion_financiera_indexacion`).
- Cálculo puro por coeficiente (`IndexacionCuotaCalculator`) con estados `CON_INDICE_APLICADO` y `PROYECTADA_SIN_INDICE`.
- Materialización de `AJUSTE_INDEXACION` como composición en algunos flujos de generación indexada y como ajuste/bonificación sobre obligación existente.
- Consulta integral que expone configuración de bloque, trazabilidad de obligación, composiciones y resumen con `total_ajuste_indexacion`.

No se encontró implementación de una **corrida de indexación/reajuste** con idempotencia propia para recalcular cuotas de un plan ya generado. Tampoco se encontró una operación única que tome un plan existente y actualice/recalcule masivamente obligaciones por índice, controlando pagos parciales, reversión y auditoría de corrida.

## 4. Estado documentado

La documentación ya reconoce más de una capa:

- Modelo comercial de planes de venta y bloques: documenta `plan_pago_venta`, `plan_pago_venta_bloque`, métodos de generación, bloques/tramos y la idea de separar capital/ajuste cuando aplique indexación.
- Modelo financiero: documenta obligaciones, composiciones, imputación y conceptos financieros, incluyendo `AJUSTE_INDEXACION`.
- Auditorías financieras previas: documentan soporte físico para índices, método `INDEXACION`, fórmula esperada, preview, cronograma y riesgos con cuotas/refuerzos.
- DER financiero/comercial: documenta las tablas financieras de obligación/composición/obligado y estructuras comerciales del plan.

Documentado pero no confirmado como flujo completo de producción para V2 de reindexación posterior:

- Corridas de indexación/reajuste con entidad propia.
- Reversión de corridas.
- Recalculo idempotente de cuotas ya generadas y potencialmente pagadas.
- Convivencia completa con mora, pagos, imputaciones y recibos para reindexación posterior.
- Versionado explícito de obligación/plan para recalcular con control de concurrencia.

## 5. Modelo financiero actual

### `plan_pago_venta`

Representa el encabezado comercial del plan de pago asociado a una venta. Contiene método global, estado, moneda, monto total, cantidad de cuotas, periodicidad, primer vencimiento, anticipo y observaciones. En V2 por bloques actúa como contenedor comercial; no debe absorber la semántica financiera de obligación, pago o imputación.

### `plan_pago_venta_bloque`

Representa bloques/tramos del plan. En el flujo por bloques contiene número, tipo, etiqueta, clave, cantidad de cuotas, importes, vencimientos, periodicidad, redondeo, método de liquidación (`SIN_INTERES`, `INTERES_DIRECTO`, `INDEXACION`) y parámetros específicos como interés directo. Para indexación, la configuración detallada se separa en `plan_pago_venta_bloque_indexacion`.

### `generacion_cronograma_financiero`

Registra la generación del cronograma financiero que materializa obligaciones desde una relación generadora/plan. Permite vincular obligaciones con una ejecución de generación. No se observó que funcione como corrida de reindexación posterior; su rol actual es generación de cronograma.

### `obligacion_financiera`

Representa una deuda concreta generada. Contiene relación generadora, generación de cronograma, posible bloque de plan, número, tipo de ítem, etiqueta/clave funcional, vencimiento, `importe_total`, `saldo_pendiente`, moneda y estado. Es el punto donde una indexación materializada impactaría el total exigible y el saldo, pero esa decisión es sensible cuando existen pagos o aplicaciones.

### `composicion_obligacion`

Descompone la obligación en conceptos financieros (`CAPITAL_VENTA`, `INTERES_FINANCIERO`, `AJUSTE_INDEXACION`, etc.) con importe y saldo por componente. Es la estructura natural para preservar capital original y explicar diferencias por ajuste sin reescribir la composición de capital.

### `obligacion_obligado`

Vincula obligación con personas obligadas y su rol/responsabilidad. La indexación no debería redefinir obligados; si modifica importes, la responsabilidad informativa debe seguir derivándose del total vigente y del porcentaje, salvo decisión contraria futura.

## 6. Soporte actual para indexación

### Existente

- Concepto financiero `AJUSTE_INDEXACION` en seeds y uso backend.
- Tablas de índices y valores (`indice_financiero`, `indice_financiero_valor`) en soporte físico documentado/patch.
- Configuración de indexación por bloque (`plan_pago_venta_bloque_indexacion`).
- Trazabilidad de índice aplicado por obligación (`obligacion_financiera_indexacion`).
- Helper puro de cálculo de cuota indexada por coeficiente (`IndexacionCuotaCalculator`).
- Tests de cálculo puro, preview por bloques, generación por bloques, consulta integral y pagos con ajuste/bonificación de indexación.
- Consulta integral V2 con bloque, obligación, composición, obligados, generación y resumen.

### Parcial

- `INDEXACION` como método de liquidación por bloque existe, pero no cubre por sí solo una política completa de reindexación posterior de cuotas ya emitidas.
- `AJUSTE_INDEXACION` puede explicar diferencias, pero no existe una entidad de corrida que agrupe un recalculo masivo por plan/bloque/fecha.
- La trazabilidad por obligación guarda datos técnicos del índice aplicado, pero no define por sí sola reversión, reemplazo o versionado de la obligación.
- Existen endpoints financieros para ajuste/bonificación de indexación sobre obligación existente, pero son operaciones puntuales, no un proceso V2 de indexación de plan.

### Inexistente

- Tabla de corrida de indexación/reajuste de cuotas.
- Endpoint público específico para recalcular/indexar cuotas V2 existentes.
- Contrato API de preview definitivo para reindexación de obligaciones ya generadas con pagos.
- Reversión de una corrida de indexación.
- Idempotencia específica de corrida (`op_id + payload`, hash de parámetros, mismo plan/bloque/fecha/índice).
- Lock lógico documentado/implementado para evitar pagos e indexación concurrentes sobre las mismas obligaciones.
- Versionado explícito aplicado al recalculo de obligación por indexación V2.

### Dudoso / requiere decisión

- Si la unidad de operación debe ser obligación, bloque o plan.
- Si una indexación futura puede modificar `importe_total` y `saldo_pendiente` directamente o debe agregar composiciones diferenciales sin tocar capital.
- Si obligaciones pagadas deben quedar cerradas, generar ajuste separado, excluirse o emitir nueva obligación complementaria.
- Cómo tratar obligaciones parcialmente pagadas: ajuste solo sobre saldo, sobre capital original, o diferencia de total con imputación pendiente.
- Cómo convivir con mora/punitorios ya calculados, recibos, imputaciones y anulaciones.

## 7. Brechas detectadas

1. Falta entidad de corrida de indexación/reajuste con estado, parámetros, hash/idempotencia, usuario, fecha de ejecución y resultado.
2. Falta política única para obligaciones ya pagadas, parcialmente pagadas, vencidas o con imputaciones activas.
3. Falta definición de si `importe_total` se reemplaza, se incrementa por composición o se complementa con una nueva obligación.
4. Falta definición transaccional: alcance de rollback y qué queda persistido ante fallo parcial.
5. Falta lock lógico para evitar concurrencia entre pagos, imputaciones, mora y recalculo de indexación.
6. Falta contrato API de preview/recalculo con errores estándar y decisión CORE-EF write.
7. Falta auditoría funcional legible de antes/después por obligación y composición.
8. Falta reversión/recalculo seguro cuando cambia un valor de índice publicado.
9. Falta decisión sobre si la base de cálculo es siempre capital original, saldo pendiente u otra base por bloque.
10. Falta completar documentación DEV-API/DEV-SRV específica del flujo V2 de indexación posterior.

## 8. Riesgos funcionales

- **Cuotas pagadas:** modificar una obligación pagada puede romper conciliación, recibos e imputaciones. Debe decidirse si se excluye, se genera complemento o se permite ajuste con trazabilidad estricta.
- **Cuotas parcialmente pagadas:** el ajuste puede afectar `saldo_pendiente`, composición y orden de imputación. Sin regla explícita, se puede cobrar de más o perder trazabilidad.
- **`saldo_pendiente`:** si aumenta `importe_total`, el saldo debería aumentar solo por la diferencia no aplicada; si baja, hay riesgo de saldo negativo o remanente/saldo a favor no modelado.
- **Reejecución:** sin idempotencia de corrida, la misma indexación puede duplicar `AJUSTE_INDEXACION` o dejar trazas inconsistentes.
- **Idempotencia:** hoy hay controles puntuales contra duplicados de `AJUSTE_INDEXACION`, pero no una idempotencia de proceso de plan/bloque/fecha.
- **Auditoría:** las tablas actuales permiten cierta trazabilidad técnica por obligación, pero no registran una corrida con snapshot antes/después.
- **Reversión:** no hay mecanismo claro para revertir una indexación aplicada, especialmente con pagos posteriores.
- **Diferencia entre importe original e importe actualizado:** conviene mantener `CAPITAL_VENTA` como capital original y materializar diferencias en `AJUSTE_INDEXACION`; reescribir capital dificultaría explicar la deuda.
- **Mora, imputaciones y recibos:** la indexación debe convivir con prioridad de imputación, aplicaciones existentes, punitorios/mora y documentos/recibos; no debe alterar pagos ya emitidos sin decisión explícita.

## 9. Decisiones pendientes

1. Unidad de operación: obligación, bloque, plan o combinación plan+bloque.
2. Base de cálculo: capital original de cuota, capital inicial de bloque, saldo pendiente, o política configurable.
3. Política para cuotas pagadas y parcialmente pagadas.
4. Persistencia del capital original: confirmar si basta `CAPITAL_VENTA` en `composicion_obligacion` o si se requiere snapshot adicional.
5. Estrategia de actualización de `importe_total` y `saldo_pendiente`.
6. Entidad de corrida: campos, estados, idempotencia, auditoría, reversión.
7. Concurrencia: lock lógico con pagos/imputaciones/mora/recibos.
8. Corrección de índices publicados: recalculo, reversión o ajuste compensatorio.
9. API pública: preview read-like vs command write, headers CORE-EF y errores estándar.
10. Alcance inicial: solo cuotas futuras/proyectadas o también obligaciones ya generadas.

## 10. Propuesta de diseño incremental

Próximos issues sugeridos:

1. **[Financiero] Diseño de indexación de cuotas V2.** Definir unidad de operación, reglas de negocio, estados, política de cuotas pagadas/parciales y convivencia con pagos/mora.
2. **[Financiero] SQL base para índices/coefs/corridas de indexación.** Agregar, si se decide, entidad de corrida y detalle de corrida sin tocar lógica de negocio hasta tener contrato cerrado.
3. **[Financiero] Backend mínimo para calcular actualización de cuotas proyectadas.** Extender cálculo puro y preview sin persistir cambios de obligaciones existentes.
4. **[Financiero] Consulta de detalle de cuota con capital original + ajuste.** Exponer claramente `CAPITAL_VENTA`, `AJUSTE_INDEXACION`, índice aplicado y estado de indexación.
5. **[Financiero] Command CORE-EF para aplicar indexación de cuotas V2.** Solo después del diseño: headers write, idempotencia, lock, outbox si aplica, versionado y rollback.
6. **[Frontend] Visualización de cuotas indexadas en ficha de venta.** Consumir contratos ya cerrados; no adelantar UI sin backend/API definidos.

## 11. Recomendación

No conviene integrar directamente con obligaciones como primer paso de V2. La recomendación es:

1. Implementar primero **diseño funcional/técnico** de indexación V2 posterior, con decisión explícita para cuotas pagadas/parciales y unidad de operación.
2. Luego implementar **SQL base de corrida/auditoría** si el diseño confirma que la trazabilidad actual por obligación no alcanza.
3. Luego ampliar o reutilizar el **helper de cálculo puro** y un preview read-like para validar importes sin persistencia.
4. Recién después implementar un command write CORE-EF que modifique obligaciones/composiciones, con idempotencia, lock lógico, versionado, rollback y tests obligatorios.

## 12. Decisión CORE-EF

- Clasificación: `QUERY_READLIKE / DOCUMENTACION`.
- Headers write: **NO APLICA**. Este PR no agrega ni modifica endpoints write.
- Idempotencia: **NO APLICA**. No hay comando ni persistencia nueva.
- Outbox: **NO APLICA**. No se emiten eventos.
- Lock lógico: **NO APLICA**. No hay operación concurrente nueva.
- Versionado: **NO APLICA**. No se modifica entidad versionada.
- Rollback/transacción: **NO APLICA**. No hay cambios de negocio ni SQL estructural.
- Tests funcionales write mínimos: **NO APLICA**. Es auditoría documental; las validaciones esperadas son estáticas/compilación.

## 13. Respuestas directas a puntos críticos

- ¿Existe composición `AJUSTE_INDEXACION`? **Sí**, existe como concepto financiero en seeds y uso backend/documentación.
- ¿Existe tabla de índices o coeficientes? **Sí**, se relevaron `indice_financiero` e `indice_financiero_valor`; coeficiente aplicado se traza en `obligacion_financiera_indexacion`.
- ¿Existe tabla de corrida de indexación/reajuste? **No confirmada / no encontrada**.
- ¿Dónde se guardaría el capital original? **Parcialmente soportado** en `composicion_obligacion` con `CAPITAL_VENTA`; falta decidir si requiere snapshot de corrida.
- ¿Cómo se modificaría `importe_total`? **Pendiente**. Técnicamente existe campo en obligación, pero falta regla V2 para recalculo posterior.
- ¿Cómo se modificaría `saldo_pendiente`? **Pendiente**. Debe depender de pagos/aplicaciones existentes y política de ajuste.
- ¿Qué pasa con obligaciones ya pagadas o parcialmente pagadas? **Pendiente crítico**.
- ¿Existe versionado/idempotencia para recalcular? **No confirmado para corrida V2**.
- ¿La indexación debería operar por obligación, por bloque o por plan? **Pendiente de diseño**.
- ¿Hay soporte para auditoría de cambios? **Parcial** por trazabilidad de obligación/indexación; falta corrida con snapshot antes/después.
- ¿Hay soporte para revertir o recalcular? **No confirmado / no encontrado como flujo completo**.
- ¿Cómo convive con pagos, mora, imputaciones y recibos? **Pendiente crítico**; existen pagos/imputaciones, pero no una política V2 cerrada de convivencia con reindexación posterior.
