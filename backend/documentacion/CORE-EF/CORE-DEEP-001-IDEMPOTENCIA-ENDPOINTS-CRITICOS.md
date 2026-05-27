# CORE-DEEP-001 — Auditoría de idempotencia real por endpoint crítico

Fecha de corte: 2026-05-27 (UTC).
Issue: #104.

## 1. Resumen ejecutivo

Se auditó evidencia real (router → service → repository → SQL → tests) para 5 endpoints críticos de financiero/comercial.

Resultado consolidado:
- **POST /api/v1/financiero/pagos**: **CUMPLE PARCIAL** (idempotencia por `X-Op-Id` implementada y probada; persiste `op_id`; sin evidencia de tabla técnica inbox/outbox específica del endpoint).
- **POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir**: **CUMPLE PARCIAL** (reversión repetida idempotente funcional; `op_id` propagado/persistido en reversión; falta conflicto explícito mismo `op_id`+payload distinto para este endpoint).
- **POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa**: **NO CONFIRMADO** en idempotencia por `op_id` (headers/core-ef y transaccionalidad presentes, pero sin guard idempotente explícito ni tests dedicados).
- **POST /api/v1/ventas/directa/confirmar-venta-completa**: **NO CONFIRMADO** en idempotencia por `op_id` (propaga/persiste `op_id` en entidades de negocio; sin guard idempotente ni test replay/conflict).
- **PATCH /api/v1/ventas/{id_venta}/confirmar**: **NO CONFIRMADO** en idempotencia por `op_id` (control de concurrencia por `If-Match-Version` sí presente; no se observa política idempotente explícita por op_id).

## 2. Tabla de estado por endpoint

| Endpoint | X-Op-Id router | Propagación a service | Persistencia op_id negocio | Registro técnico idempotencia | Replay mismo op_id + mismo payload | Mismo op_id + payload distinto | Retry post-error parcial | Estado |
|---|---|---|---|---|---|---|---|---|
| POST /api/v1/financiero/pagos | Sí | Sí | Sí | Parcial (`payload_idempotencia` en consulta agregada por op_id) | Sí (testeado) | Sí (409 `IDEMPOTENCY_PAYLOAD_CONFLICT`) | Parcial (sin prueba explícita de falla intermedia DB) | CUMPLE PARCIAL |
| POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir | Sí | Sí | Sí | No confirmado (no tabla técnica dedicada) | Sí (testeado: segunda reversión sin duplicar) | No confirmado | Parcial | CUMPLE PARCIAL |
| POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa | Sí | Sí | Sí (por subservicios) | No confirmado | No confirmado | No confirmado | No confirmado (rollback compuesto testeado, retry no probado) | NO CONFIRMADO |
| POST /api/v1/ventas/directa/confirmar-venta-completa | Sí | Sí | Sí (payloads con op_id_alta/op_id_ultima_modificacion) | No confirmado | No confirmado | No confirmado | No confirmado (rollback compuesto testeado, retry no probado) | NO CONFIRMADO |
| PATCH /api/v1/ventas/{id_venta}/confirmar | Sí | Sí | Sí (`op_id_ultima_modificacion`) | No confirmado | No confirmado | No confirmado | Parcial (control por versión; no test de retry idempotente por op_id) | NO CONFIRMADO |

## 3. Evidencia por endpoint

### 3.1 POST /api/v1/financiero/pagos
- Router valida `X-Op-Id` y headers CORE-EF, construye `context` y ejecuta `RegistrarPagoPersonaService`.
- Service consulta por `op_id` (`get_pago_persona_by_op_id`) y aplica:
  - mismo payload: replay seguro (retorna resultado existente);
  - payload distinto: `IDEMPOTENCY_PAYLOAD_CONFLICT`.
- Repository tiene `get_pago_persona_by_op_id` y persiste `op_id_alta/op_id_ultima_modificacion` en `movimiento_financiero` y registros relacionados del pago.
- SQL base confirma columnas `op_id_alta/op_id_ultima_modificacion` en tablas financieras involucradas.

Clasificación: **CUMPLE PARCIAL** (idempotencia fuerte para el endpoint; falta evidencia de inbox/outbox técnico dedicado de este caso).

### 3.2 POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir
- Router valida `X-Op-Id` y construye contexto CORE-EF.
- Service usa `context.op_id` y delega en `repository.revertir_pago_agrupado`.
- Repository revierte movimientos/aplicaciones en transacción y escribe `op_id_ultima_modificacion`.
- Existe test de reversión repetida idempotente (sin duplicar efecto).

Clasificación: **CUMPLE PARCIAL** (idempotencia funcional de replay presente; falta evidencia explícita de conflicto por mismo op_id + payload distinto en reversión).

### 3.3 POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa
- Router exige `X-Op-Id` + `If-Match-Version` y arma comando compuesto.
- Service orquesta 4 etapas en transacción (generar venta, definir condiciones, plan pago v2, confirmar venta) con rollback por `_StageFailed`.
- `op_id` se propaga vía `context` a subservicios, que persisten `op_id` en entidades tocadas.
- No se observó guard idempotente del endpoint compuesto por `op_id` (ni lookup técnico equivalente), ni tests de replay/conflict por op_id.

Clasificación: **NO CONFIRMADO** en idempotencia real por endpoint.

### 3.4 POST /api/v1/ventas/directa/confirmar-venta-completa
- Router exige headers CORE-EF (incluyendo `X-Op-Id`).
- Service compuesto transaccional con rollback y construcción de payloads que incluyen `op_id_alta/op_id_ultima_modificacion`.
- No se observa verificación previa por `op_id` para detectar replay/conflict a nivel endpoint.
- Tests existentes cubren contrato y rollback transaccional, pero no prueban retry posterior con el mismo X-Op-Id ni conflicto por payload distinto.

Clasificación: **NO CONFIRMADO**.

### 3.5 PATCH /api/v1/ventas/{id_venta}/confirmar
- Router exige `X-Op-Id` y `If-Match-Version`.
- `ConfirmVentaService` aplica concurrencia por `version_registro` y persiste `op_id_ultima_modificacion`; además genera outbox de `venta_confirmada`.
- No hay guard explícito por `op_id` para replay del PATCH (la protección principal es `If-Match-Version`).

Clasificación: **NO CONFIRMADO** en idempotencia por op_id (aunque cumple concurrencia por versión).

## 4. Tests existentes

Cobertura relevante identificada:
- `backend/tests/test_fin_registrar_pago_persona.py`:
  - idempotencia en `POST /financiero/pagos` (replay y conflicto payload).
  - reversión de pagos, incluyendo reversión repetida idempotente y casos de conflicto funcional.
- `backend/tests/test_reservas_venta_confirmar_venta_completa.py`:
  - contrato de endpoint, validaciones, concurrencia por `If-Match-Version`, rollback de flujo compuesto.
- `backend/tests/test_ventas_directa_confirmar_venta_completa.py` y `..._contract.py`:
  - contrato y comportamiento funcional principal del endpoint directo.
- `backend/tests/test_ventas_confirm.py` (+ `test_outbox_events.py`):
  - confirmación de venta por PATCH, concurrencia por versión y evidencia de evento outbox asociado.

## 5. Tests faltantes

1. **Reserva confirmar-venta-completa**:
   - mismo `X-Op-Id` + mismo payload => replay idempotente;
   - mismo `X-Op-Id` + payload distinto => conflicto 409 explícito.
2. **Venta directa confirmar-venta-completa**:
   - replay idempotente por op_id;
   - conflicto payload por op_id reutilizado.
3. **PATCH ventas/{id}/confirmar**:
   - política explícita para segundo intento con mismo op_id (mismo/diferente payload).
4. **Revertir pago agrupado**:
   - caso explícito de conflicto por reutilización de op_id en reversión semánticamente distinta (si contrato lo requiere).
5. **Retry post-error parcial** (todos):
   - pruebas de falla inyectada entre pasos para validar que retry con mismo op_id no duplica ni deja estado inconsistente.

## 6. Riesgos

- **Riesgo alto** en endpoints compuestos comerciales: sin guard idempotente explícito por endpoint, reintentos distribuidos podrían crear/duplicar efectos bajo ciertas carreras.
- **Riesgo medio** en reversión financiera: idempotencia funcional existe, pero falta regla explícita de conflicto por op_id reutilizado en variantes de payload.
- **Riesgo medio** en PATCH confirmar venta: depende de `If-Match-Version`; no distingue formalmente replay idempotente por op_id.

## 7. Recomendación de hardening incremental

1. Definir contrato técnico uniforme de idempotencia por endpoint (`op_id` + hash payload canónico).
2. Introducir registro técnico de idempotencia por endpoint crítico (o índice funcional equivalente) con estado de ejecución y respuesta canónica.
3. Mantener `If-Match-Version` como guard de concurrencia, pero no como sustituto de idempotencia de reintentos distribuidos.
4. Agregar tests de replay/conflict/retry post-falla en cada endpoint crítico antes de cambios funcionales mayores.

## 8. Issues/PRs sugeridos

1. `CORE-DEEP-001-A1` — Idempotencia explícita en `confirmar-venta-completa` desde reserva (guard op_id + payload hash + tests).
2. `CORE-DEEP-001-A2` — Idempotencia explícita en `ventas/directa/confirmar-venta-completa` (guard op_id + payload hash + tests).
3. `CORE-DEEP-001-A3` — Política op_id para `PATCH /ventas/{id}/confirmar` (replay/conflict) + tests.
4. `CORE-DEEP-001-A4` — Reversión de pagos: formalizar conflicto op_id/payload y cobertura de retry post-falla.

## 9. Comandos ejecutados

- `find .. -name AGENTS.md -print`
- `sed -n '1,220p' AGENTS.md`
- `rg -n "financiero/pagos|revertir|confirmar-venta-completa|ventas/directa|ventas/.*/confirmar|X-Op-Id|x_op_id|op_id|idempot" backend/app/api/routers backend/app/application backend/app/infrastructure/persistence/repositories backend/tests backend/database backend/documentacion/CORE-EF -S`
- `rg -n "@router\.(post|patch).*financiero/pagos|revertir|confirmar-venta-completa|ventas/directa|ventas/\{id_venta\}/confirmar|X-Op-Id|x_op_id" backend/app/api/routers -S`
- `sed -n '2920,3065p' backend/app/api/routers/financiero_router.py`
- `sed -n '2740,2875p' backend/app/api/routers/financiero_router.py`
- `sed -n '1360,1455p' backend/app/api/routers/comercial_router.py`
- `sed -n '1510,1605p' backend/app/api/routers/comercial_router.py`
- `sed -n '2588,2675p' backend/app/api/routers/comercial_router.py`
- `sed -n '1,260p' backend/app/application/financiero/services/registrar_pago_persona_service.py`
- `sed -n '1,240p' backend/app/application/financiero/services/revertir_pago_agrupado_service.py`
- `sed -n '1,280p' backend/app/application/comercial/services/confirm_venta_completa_desde_reserva_service.py`
- `sed -n '1,260p' backend/app/application/comercial/services/confirm_venta_directa_completa_service.py`
- `sed -n '1,260p' backend/app/application/comercial/services/confirm_venta_service.py`
- `rg -n "def get_pago_persona_by_op_id|def registrar_pago_multipago|payload_idempotencia|def revertir_pago_agrupado|def _create_venta_directa_tx|def _generate_venta_from_reserva_tx|def _confirm_venta_tx|op_id_alta|ux_.*op_id|pago_grupo" backend/app/infrastructure/persistence/repositories backend/database backend/tests -S`
- `rg -n "/api/v1/financiero/pagos|revertir|confirmar-venta-completa|/api/v1/ventas/.*/confirmar|IDEMPOTENCY_PAYLOAD_CONFLICT|PAGO_YA_REVERTIDO|CONCURRENCY_ERROR" backend/tests -S`


## 10. Incremento #104 — hardening focalizado en `POST /api/v1/financiero/pagos`

Alcance aplicado en este incremento: **solo auditoría profunda de `registrar_pago_persona`** (router/service/repository/tests/persistencia), sin cambios de lógica de negocio ni SQL estructural.

### 10.1 Resultado de auditoría puntual

- **`X-Op-Id` en router**: se valida como header CORE-EF obligatorio y se inyecta en `context.op_id` antes de invocar `RegistrarPagoPersonaService`.
- **`X-Op-Id` en service/context**: el service toma `context.op_id` y hace lookup por `op_id` con `repository.get_pago_persona_by_op_id(...)` antes de ejecutar nuevas escrituras.
- **Lookup por op_id**: existe y consulta `movimiento_financiero` + `aplicacion_financiera` filtrando por `m.op_id_alta = :op_id` y `tipo_movimiento = 'PAGO'`.
- **Comparación de payload idempotente**: existe por `_payload_idempotencia_equivalente(...)` usando `id_persona`, `monto`, `fecha_pago`, `alcance_pago`, `id_obligacion_financiera`, `id_relacion_generadora`.
- **Persistencia relevante**: la evidencia del repository muestra persistencia de `op_id_alta`/`op_id_ultima_modificacion` en `movimiento_financiero` (y trazabilidad asociada por aplicaciones del grupo de pago).

### 10.2 Matriz de comportamiento validada (solo pagos)

- **Mismo `X-Op-Id` + mismo payload (retry secuencial posterior a éxito)**: retorna replay seguro con mismo resultado y sin duplicar movimientos (`201` con mismo `uid_pago_grupo`/`codigo_pago_grupo`).
- **Mismo `X-Op-Id` + payload distinto (retry secuencial posterior a éxito)**: retorna `409 IDEMPOTENCY_PAYLOAD_CONFLICT`.
- **`X-Op-Id` nuevo + payload distinto**: registra nuevo pago (si el estado financiero lo permite) y genera nuevo grupo de pago.
- **Retry tras respuesta exitosa**: cubierto por tests de retry idempotente (no duplica movimientos ni afecta saldo dos veces).
- **Retry de op_id original tras reversión**: retorna `409 PAGO_YA_REVERTIDO`.

### 10.3 Estado de cumplimiento del endpoint auditado

Para `POST /api/v1/financiero/pagos`, con evidencia actual en código + tests, el estado se mantiene en **CUMPLE PARCIAL**. La evidencia disponible confirma idempotencia para **reintentos secuenciales** posteriores a una respuesta exitosa (mismo `X-Op-Id` + mismo payload, y mismo `X-Op-Id` + payload distinto con conflicto `409`).

No queda confirmada en este incremento la idempotencia ante **concurrencia simultánea** de dos requests con el mismo `X-Op-Id`: ambos intentos podrían atravesar el lookup `get_pago_persona_by_op_id` antes del commit y no hay evidencia documentada aquí de un cierre duro de carrera (constraint única fuerte por `op_id_alta`, registro técnico idempotente, lock transaccional o índice/estrategia equivalente por `op_id`).

### 10.4 Brechas remanentes (sin implementar en este issue)

1. No hay prueba explícita de **falla intermedia DB inyectada** y retry con el mismo `X-Op-Id` para verificar recuperación post-error parcial.
2. No está cerrada con evidencia la carrera de **concurrencia simultánea** con mismo `X-Op-Id` (dos requests en paralelo antes de commit).
3. Hardening pendiente: definir y evidenciar cierre técnico de carrera por diseño futuro (por ejemplo, **constraint única**, **registro técnico idempotente**, **lock transaccional** o **índice/estrategia por `op_id`**).

### 10.5 Decisión de cambio en #104

- **No se cambia lógica de negocio** de pagos.
- **No se cambia SQL estructural**.
- **No se tocan otros endpoints**.
- Se actualiza únicamente documentación de evidencia de auditoría.
