# AUDITORIA / DECISION TECNICA
## Soporte fisico de indices financieros e historico de valores

- Fecha: 2026-05-27
- Tipo: Documental / tecnico (sin cambios de codigo, SQL ni tests)
- Dominio: financiero
- Relacion: complemento de `AUDITORIA-METODO-LIQUIDACION-INDEXACION-PLAN-PAGO-V2.md` (PR #118)

---

## 0) Alcance y restricciones del presente PR

Este PR:

- NO implementa codigo.
- NO modifica SQL.
- NO modifica tests.
- NO crea endpoints.
- NO implementa INDEXACION en Plan Pago V2.

Objetivo: dejar auditoria verificable + decision tecnica previa para habilitar soporte real de indices financieros.

---

## 1) Relevamiento ejecutado en repositorio

## 1.1 SQL actual (schema, patches, seeds)

Resultado de busqueda de terminos `indice_financiero`, `valor_indice`, `historico_indice`, `CAC`, `UVA`, `IPC`, `indexacion`, `actualizacion`:

- No se detecta tabla operativa `indice_financiero` en `schema_inmobiliaria_20260418.sql`.
- No se detecta tabla operativa de historico de valores (`indice_financiero_valor` o equivalente) en schema ni patches.
- No se detectan seeds de catalogo de indices financieros (CAC/UVA/IPC u otros).
- Si existe concepto financiero `AJUSTE_INDEXACION` en seeds (`seed_minimo.sql`, `seed_test_baseline.sql`) y en patch de concepto financiero.

Conclusion SQL actual: existe base conceptual para composicion de ajuste por indexacion, pero no existe soporte fisico de catalogo + historico de indices.

## 1.2 Backend actual (repositories/services/schemas/routers/tests)

Resultado del relevamiento:

- No se detecta repository/query operativo para "indice por fecha".
- No se detecta service/endpoint para alta o modificacion de indice financiero.
- Si existen endpoints y servicios para `AJUSTE_INDEXACION` y `BONIFICACION_INDEXACION` sobre obligaciones existentes.
- Esos endpoints/materializaciones no reemplazan la falta de fuente fisica de indice por fecha.

Conclusion backend: hay operaciones de ajuste/bonificacion sobre obligaciones, pero no hay subsistema implementado de administracion/consulta de indices financieros historicos.

## 1.3 Documentacion DEV-SRV / financiero

- Existe `SRV-FIN-004-gestion-de-indices-financieros.md` con definicion funcional del servicio.
- SRV-FIN-004 ya define funcionalmente:
  - alta de indice financiero;
  - modificacion de indice financiero;
  - actualizacion de valor de indice;
  - mantenimiento de vigencia;
  - contexto tecnico (`usuario_id`, `sucursal_id`, `instalacion_id`, `op_id`, `version_esperada`);
  - validacion de idempotencia;
  - registro de outbox cuando corresponda.
- Existe auditoria previa de INDEXACION en Plan Pago V2 que ya marca como pendiente el soporte de indice financiero por fecha.
- Existe documentacion financiera y comercial que menciona `AJUSTE_INDEXACION` y uso futuro en planes, sin confirmacion de soporte fisico implementado para indice/historico.

Conclusion documental: la definicion funcional del servicio ya existe (SRV-FIN-004); la brecha confirmada en este PR es de soporte fisico/implementacion.

## 1.4 Relacion con SRV-FIN-004

Esta auditoria:

- no crea ni inventa un servicio nuevo;
- toma `SRV-FIN-004-gestion-de-indices-financieros.md` como fuente funcional vigente;
- delimita la brecha tecnica efectiva para ejecutar SRV-FIN-004 en implementacion real.

Brecha confirmada (fisica/de implementacion, no funcional-documental):

- no se confirmo tabla `indice_financiero`;
- no se confirmo tabla `indice_financiero_valor`;
- no se confirmo seed/catalogo de indices financieros;
- no se confirmo repository/query de indice por fecha;
- no se confirmo endpoint/service implementado para alta/modificacion/actualizacion.

---

## 2) Respuestas explicitas (A. Estado actual)

1. Existe tabla `indice_financiero` real?  
   - **NO CONFIRMADO / NO IMPLEMENTADO** en SQL actual relevado.

2. Existe tabla de valores historicos por fecha?  
   - **NO CONFIRMADO / NO IMPLEMENTADO**.

3. Existe seed/catalogo de indices?  
   - **NO CONFIRMADO / NO IMPLEMENTADO** para catalogo de indices financieros.

4. Existe repository/query para consultar indice por fecha?  
   - **NO CONFIRMADO / NO IMPLEMENTADO**.

5. Existe endpoint o service para cargar/modificar indices?  
   - **NO CONFIRMADO / NO IMPLEMENTADO** en codigo; solo especificacion documental SRV-FIN-004.

6. Existe concepto financiero para `AJUSTE_INDEXACION`?  
   - **SI, IMPLEMENTADO** a nivel de catalogo de concepto financiero.

7. Existe uso real de indice en obligaciones/mora/ajustes/planes?  
   - **PARCIAL**: existe uso real de `AJUSTE_INDEXACION`/`BONIFICACION_INDEXACION` como composiciones/aplicaciones; **NO** existe uso real confirmado de "indice financiero historico por fecha" como fuente fisica para calculo.

---

## 3) Brecha tecnica (B)

Si se pretende implementar `INDEXACION` robusta en Plan Pago V2, hoy faltan como minimo:

1. Catalogo persistido de indices financieros (`indice_financiero`).
2. Historico persistido de valores por fecha (`indice_financiero_valor`).
3. Reglas de vigencia/estado y unicidad compatibles con soft delete.
4. Query deterministica "indice por fecha" (exacto y fallback ultimo <= fecha).
5. Politica explicita para ausencia de valor vigente.
6. Contrato de congelamiento de valor aplicado al generar obligaciones.

No debe asumirse:

- que exista una tabla de indice por haber referencias documentales;
- que `AJUSTE_INDEXACION` resuelva por si mismo la obtencion del indice;
- que agregar solo campos en `plan_pago_venta_bloque_indexacion` alcance para calcular indexacion sin fuente de valores historicos.

---

## 4) Modelo fisico propuesto (C)

Diseno minimo recomendado (para patch SQL futuro, no en este PR).

## 4.1 Tabla `indice_financiero`

Campos candidatos:

- `id_indice_financiero` (PK)
- `uid_global`
- `version_registro`
- `created_at`, `updated_at`, `deleted_at`
- `id_instalacion_origen`
- `id_instalacion_ultima_modificacion`
- `op_id_alta`
- `op_id_ultima_modificacion`
- `codigo_indice_financiero`
- `nombre_indice_financiero`
- `descripcion`
- `tipo_indice`
- `unidad_medida`
- `frecuencia_publicacion`
- `fuente_indice`
- `estado_indice_financiero`
- `observaciones`

## 4.2 Tabla `indice_financiero_valor`

Campos candidatos:

- `id_indice_financiero_valor` (PK)
- `uid_global`
- `version_registro`
- `created_at`, `updated_at`, `deleted_at`
- `id_instalacion_origen`
- `id_instalacion_ultima_modificacion`
- `op_id_alta`
- `op_id_ultima_modificacion`
- `id_indice_financiero` (FK -> `indice_financiero`)
- `fecha_valor`
- `valor_indice`
- `fecha_publicacion`
- `fuente_valor`
- `estado_valor_indice`
- `observaciones`

---

## 5) Constraints e indices sugeridos (D)

Compatibles con soft delete (`deleted_at IS NULL` en unicidades activas):

1. `UNIQUE (codigo_indice_financiero) WHERE deleted_at IS NULL`.
2. `UNIQUE (id_indice_financiero, fecha_valor) WHERE deleted_at IS NULL`.
3. `CHECK (valor_indice > 0)`.
4. `CHECK (fecha_publicacion IS NULL OR fecha_publicacion >= fecha_valor)`.
5. `CHECK estado_indice_financiero IN ('ACTIVO','INACTIVO','BORRADOR','ANULADO')` (cerrar catalogo final en patch).
6. `CHECK estado_valor_indice IN ('PUBLICADO','BORRADOR','ANULADO')`.
7. Indices sugeridos:
   - `idx_indice_financiero_codigo_activo`
   - `idx_indice_financiero_estado_activo`
   - `idx_indice_valor_fecha_activo`
   - `idx_indice_valor_indice_fecha_activo` (`id_indice_financiero, fecha_valor`)

Nota: los estados exactos deben cerrarse en catalogo formal para evitar divergencia semantica.

---

## 6) CORE-EF e idempotencia futura (E)

Para implementacion futura (no aplicada en este PR):

1. Alta/modificacion de `indice_financiero`: **COMMAND_WRITE_NEGOCIO** (afecta reglas financieras y calculo downstream).
2. Alta/modificacion de `indice_financiero_valor`: **COMMAND_WRITE_NEGOCIO** critico.
3. Headers obligatorios: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
4. Versionado: uso de `If-Match-Version` cuando haya modificacion de entidad versionada.
5. Idempotencia por `op_id + payload`.
6. Conflicto obligatorio: mismo indice + misma fecha + valor distinto => conflicto de idempotencia/negocio.
7. Outbox: **APLICA** si la operacion es sincronizable y con efectos externos.
8. Rollback: transaccion atomica negocio + outbox (si aplica).

---

## 7) Politica de consulta por fecha (F)

Definicion recomendada para query de consumo:

1. **Exacta por fecha**: buscar valor `PUBLICADO` para `fecha_valor = fecha_objetivo`.
2. **Fallback deterministico**: si no existe exacto, tomar ultimo `PUBLICADO` con `fecha_valor <= fecha_objetivo`.
3. **Si no existe valor utilizable**: error controlado de negocio (`INDICE_SIN_VALOR_PARA_FECHA`).
4. Valores en `BORRADOR` o `ANULADO`: no computables para generate definitivo.
5. Preview: puede usar ultimo publicado disponible (debe declararse en respuesta).
6. Generate: debe congelar referencia aplicada (`id_valor` o `fecha+valor+fuente`) para trazabilidad e idempotencia.

---

## 8) Relacion con Plan Pago V2 INDEXACION (G)

Estas tablas habilitarian, en etapas posteriores:

1. `plan_pago_venta_bloque_indexacion`: referenciar indice y politica sin hardcodear valores fijos sin fuente.
2. Preview Plan Pago V2: calcular `total_con_indexacion` usando query por fecha.
3. Generate Plan Pago V2: congelar valor aplicado para cada obligacion generada.
4. `composicion_obligacion`: materializar diferencia con `AJUSTE_INDEXACION` sin reescribir capital base.
5. Idempotencia de generacion indexada: validar consistencia entre `op_id`, payload y referencia de valor de indice congelado.

---

## 9) Roadmap recomendado (H)

1. Patch SQL de `indice_financiero` + `indice_financiero_valor` con constraints e indices.
2. Seed minimo de indices (si aplica politica de arranque; p.ej. catalogo inicial controlado).
3. Repository/query de consulta de indice por fecha (exacta + fallback <= fecha).
4. Patch SQL `plan_pago_venta_bloque_indexacion` (alineado a auditoria INDEXACION previa).
5. Propagacion app para `INDEXACION` en preview/generate V2 sin endpoint nuevo.
6. Strategy de liquidacion INDEXACION real + tests de no regresion.

---

## 10) Decision CORE-EF del PR actual (I)

- Naturaleza: **PR documental**.
- Endpoint write: **NO APLICA**.
- SQL: **NO MODIFICA**.
- Codigo: **NO MODIFICA**.
- Tests: **NO MODIFICA**.
