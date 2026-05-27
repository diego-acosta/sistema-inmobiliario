# AUDITORIA PROFUNDA CORE-EF POR ENDPOINT WRITE (TANDA 001)

Fecha de corte: 2026-05-27 (UTC).

## 1. Resumen ejecutivo

Se auditaron 5 endpoints write prioritarios con traza completa hasta router, command/service, repository, SQL (cuando hubo evidencia directa), y tests.

Resultado global:
- 1 endpoint: **CUMPLE PARCIAL** con evidencia fuerte de idempotencia/rollback/op_id pero sin `If-Match-Version` ni outbox distribuible explícito.
- 3 endpoints: **CUMPLE PARCIAL** con orquestación correcta y control de versión donde aplica, pero con brechas de evidencia profunda en idempotencia técnica por `X-Op-Id` a nivel repository/SQL y lock lógico explícito.
- 1 endpoint: **CUMPLE PARCIAL** con `If-Match-Version` y outbox en flujo de confirmación, pero sin evidencia de idempotencia por `X-Op-Id` del PATCH.

No se detectó evidencia de endpoints en estado **NO CUMPLE** absoluto para la capa HTTP/headers; las brechas están en hardening profundo CORE-EF (idempotencia integral por endpoint, locks lógicos explícitos, outbox/inbox aplicabilidad formalizada por caso).

## 2. Metodología

1. Revisión de contratos en routers (`Header`, `ErrorResponse`, construcción de command/contexto técnico).
2. Traza a services/commands para verificar:
   - uso de `op_id`;
   - validación de `version_registro` cuando aplica;
   - manejo de idempotencia;
   - control transaccional y rollback.
3. Traza a repositories para validar:
   - `version_registro`, `op_id_alta`, `op_id_ultima_modificacion`, `id_instalacion_*`;
   - patrones SQL de concurrencia (`WHERE version_registro = expected` o equivalente);
   - `deleted_at` y anti-overwrite silencioso.
4. Revisión de tests existentes por endpoint (happy path, headers, concurrencia, rollback, idempotencia, outbox/inbox).
5. Clasificación por endpoint: `CUMPLE`, `CUMPLE PARCIAL`, `NO CUMPLE`, `NO CONFIRMADO`.

## 3. Tabla resumen por endpoint

| endpoint | clasificación | síntesis |
|---|---|---|
| POST /api/v1/financiero/pagos | CUMPLE PARCIAL | Headers CORE-EF y ErrorResponse ok; idempotencia por `X-Op-Id` implementada en service/repository y testeada; no usa `If-Match-Version` (decisión de endpoint sin precondición de versión); outbox no evidenciado. |
| POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir | CUMPLE PARCIAL | Headers CORE-EF y errores ok; rollback e idempotencia funcional (reversión repetida) testeada; sin `If-Match-Version`; outbox no evidenciado. |
| POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa | CUMPLE PARCIAL | Headers + `If-Match-Version` + separación 400/409 presentes; rollback de flujo compuesto testeado; falta evidencia directa de idempotencia por `X-Op-Id` del endpoint compuesto. |
| POST /api/v1/ventas/directa/confirmar-venta-completa | CUMPLE PARCIAL | Headers CORE-EF y no expone `If-Match-Version` por contrato actual; rollback compuesto testeado; falta evidencia de idempotencia por `X-Op-Id` y de lock lógico explícito. |
| PATCH /api/v1/ventas/{id_venta}/confirmar | CUMPLE PARCIAL | Requiere `If-Match-Version`; flujo de confirmación con outbox en service; cobertura de headers/concurrencia presente; sin evidencia explícita de idempotencia por `X-Op-Id`. |

## 4. Análisis detallado endpoint por endpoint

### 4.1 POST /api/v1/financiero/pagos

**A. Router**
- Exige headers CORE-EF (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) vía helper y retorna `ErrorResponse` estándar en validaciones/errores.
- No requiere `If-Match-Version` (consistente con endpoint de alta/movimiento agrupado).
- Construye contexto técnico y lo inyecta a service.

**B. Command/Service**
- `RegistrarPagoPersonaService` usa `context.op_id` para idempotencia y trazabilidad.
- Evalúa `get_pago_persona_by_op_id`; mismo `op_id` + payload equivalente => replay seguro, distinto payload => `IDEMPOTENCY_PAYLOAD_CONFLICT`.
- Maneja caso `PAGO_YA_REVERTIDO` cuando `op_id` corresponde a pago anulado.
- Mantiene lógica de aplicación de pago/mora y delega persistencia multipago.

**C. Repository/SQL**
- Evidencia de persistencia de `version_registro`, `op_id_alta`, `op_id_ultima_modificacion`, `id_instalacion_*` en inserts de movimiento/aplicación y componentes relacionados.
- Uso de transacción con `commit`/`rollback` en errores.
- No aplica patrón `UPDATE ... WHERE version_registro = expected` por naturaleza de create/movimientos; requiere control de idempotencia (sí implementado).

**D. Outbox/Inbox**
- No se observó outbox explícito para este caso.
- Clasificación: **brecha media/no confirmado** para integración distribuida (depende de si negocio exige emisión de evento externo del pago agrupado en esta fase).

**E. Idempotencia**
- Fuerte: implementada y testeada (mismo op_id + mismo payload; conflicto con payload distinto; retry seguro).

**F. Locks lógicos**
- No se observó lock lógico de negocio explícito de alto nivel (sí hay controles en persistencia y consistencia transaccional).
- Clasificación: **no confirmado** si el riesgo operativo requiere lock adicional en escenarios de alta concurrencia externa.

**G. Tests**
- Cobertura observada para happy path, validaciones de headers, idempotencia de `X-Op-Id`, conflicto de payload, no duplicación, y múltiples escenarios de aplicación/reversión asociados.
- Faltante: evidencia específica de outbox/inbox del caso.

### 4.2 POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir

**A. Router**
- Exige headers CORE-EF por helper y envelope `ErrorResponse` estándar.
- No exige `If-Match-Version`.
- Construye contexto y delega a `RevertirPagoAgrupadoService`.

**B. Command/Service**
- Valida motivo obligatorio.
- Verifica existencia del pago agrupado y operación posterior antes de revertir.
- Usa `context.op_id` e `id_instalacion` para trazabilidad técnica.

**C. Repository/SQL**
- Evidencia de transaccionalidad (`commit`/`rollback`) en operaciones financieras.
- Por test funcional, la reversión no duplica efectos en reintentos y respeta consistencia de saldos/aplicaciones.
- `If-Match-Version` no aplica por diseño actual del endpoint.

**D. Outbox/Inbox**
- No se observó generación explícita de outbox.
- Clasificación: **no confirmado/brecha media** según necesidad de publicar evento de reversión.

**E. Idempotencia**
- Evidencia funcional de reversión repetida idempotente.
- Faltante: explicitud documental de regla técnica payload-aware para reversión (en comparación a pago).

**F. Locks lógicos**
- Hay control funcional de “operaciones posteriores” (protección de integridad).
- No se encontró lock lógico de proceso explícito (clasificar como **no confirmado**).

**G. Tests**
- Cobertura sólida de happy path, operación posterior (409), inexistente (404), idempotencia de reversión repetida, y validación de headers.

### 4.3 POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa

**A. Router**
- Exige headers CORE-EF + `If-Match-Version`.
- Evita duplicación de headers en OpenAPI (comentario explícito).
- Separa 400/409 con `ErrorResponse` estándar.
- Construye `ConfirmVentaCompletaDesdeReservaCommand` con contexto y campos de subflujos.

**B. Command/Service**
- Orquesta generar venta + condiciones comerciales + plan pago v2 + confirmación.
- Usa versionado por `if_match_version_reserva`.
- Tests evidencian rollback integral si falla cualquier subpaso.

**C. Repository/SQL**
- Evidencia indirecta fuerte por tests de rollback y versión; no se cerró traza completa de cada write SQL interno del flujo compuesto en esta auditoría.
- Clasificación parcial: **no confirmado** en detalle fino `UPDATE ... WHERE version_registro = expected` para cada entidad tocada.

**D. Outbox/Inbox**
- No confirmado explícitamente para el endpoint compuesto completo.

**E. Idempotencia**
- No se encontró test específico de mismo `X-Op-Id` replay para este endpoint compuesto.
- Brecha media.

**F. Locks lógicos**
- No lock lógico explícito de caso de uso observado.

**G. Tests**
- Cobertura: endpoint en OpenAPI, no duplicación headers, validación request, `If-Match-Version` faltante/inválido/mismatch, happy path, rollback en fallas intermedias.
- Faltante: idempotencia por `X-Op-Id`, outbox/inbox.

### 4.4 POST /api/v1/ventas/directa/confirmar-venta-completa

**A. Router**
- Exige headers CORE-EF.
- Contractualmente **no** expone `If-Match-Version` en este endpoint.
- Construye command compuesto con contexto.

**B. Command/Service**
- Orquestación equivalente a flujo compuesto directo.
- Uso de `op_id` en payloads internos (según service), con evidencias de trazabilidad.
- Rollback integral cubierto por tests cuando fallan subetapas.

**C. Repository/SQL**
- Evidencia de versionado/op_id en entidades creadas/actualizadas por servicios y repositorios comerciales/plan pago.
- Falta trazado puntual end-to-end SQL por cada operación interna en este informe.

**D. Outbox/Inbox**
- No confirmado explícitamente para endpoint compuesto global.

**E. Idempotencia**
- No hay evidencia de pruebas dedicadas a replay `X-Op-Id` (mismo payload vs distinto payload).

**F. Locks lógicos**
- No evidenciado lock lógico explícito.

**G. Tests**
- Cobertura: OpenAPI, no duplicación headers, validaciones de request/headers, happy path, rollback en fallas de condiciones/plan/confirmación.
- Faltante: idempotencia por op_id, outbox/inbox.

### 4.5 PATCH /api/v1/ventas/{id_venta}/confirmar

**A. Router**
- Endpoint con headers CORE-EF y `If-Match-Version` requerido.
- Contrato de error estándar (`CONCURRENCY_ERROR` ante mismatch de versión).

**B. Command/Service**
- `ConfirmVentaService` valida `if_match_version` contra `version_registro` actual.
- Construye payload de actualización con incremento de versión y `op_id_ultima_modificacion`.
- Genera `OutboxEventPayload` para evento de venta confirmada en confirmación.

**C. Repository/SQL**
- Evidencia de uso de versionado y op_id por payload del servicio.
- No se cerró en este informe lectura SQL exacta `WHERE version_registro = expected` de la implementación concreta de repository para este endpoint (clasificar no confirmado fino).

**D. Outbox/Inbox**
- Outbox: **evidencia presente en service** (evento de confirmación de venta).
- Inbox: no aplica directo al endpoint.

**E. Idempotencia**
- Sin evidencia de política explícita por `X-Op-Id` a nivel endpoint PATCH.
- Concurrencia de versión sí cubierta.

**F. Locks lógicos**
- No lock lógico explícito identificado; se apoya en control de versión.

**G. Tests**
- `backend/tests/test_ventas_confirm.py` cubre happy path, mismatch/faltante/inválido `If-Match-Version`, y casos de estado.
- Faltante: pruebas explícitas de idempotencia por op_id y verificación outbox persistido en misma transacción.

## 5. Brechas críticas

1. **Idempotencia no uniforme por endpoint write compuesto comercial**:
   - Falta prueba/evidencia explícita de replay seguro `X-Op-Id` en confirmar venta completa (reserva/directa) y en PATCH confirmar venta.
2. **Trazabilidad SQL de concurrencia en flujos compuestos**:
   - En endpoints compuestos comerciales no se confirmó línea por línea todos los `UPDATE` con guardas de concurrencia.

## 6. Brechas medias

1. **Outbox no confirmado en pagos/reversión financiera** (si requieren sincronización distribuida).
2. **Locks lógicos explícitos no evidenciados** en endpoints de alta criticidad de transición de estado.
3. **Pruebas de outbox/inbox por endpoint** incompletas en esta tanda.

## 7. Qué NO corregir todavía

1. No introducir caja operativa ni comprobante fiscal persistido en esta auditoría.
2. No rediseñar contratos HTTP ya normalizados CORE-EF (fase anterior cerrada).
3. No agregar lock distribuido sin criterio formal por caso de uso y riesgo.

## 8. Roadmap de hardening recomendado

1. **Fase A (rápida):** tests de idempotencia por `X-Op-Id` en los 3 endpoints comerciales auditados.
2. **Fase B:** trazado SQL verificable por endpoint (matriz de `tabla/campo/version/op_id/id_instalacion/deleted_at`).
3. **Fase C:** definición explícita de política outbox por endpoint financiero de pagos/reversión.
4. **Fase D:** definir criterio de locks lógicos por criticidad y escenarios de carrera.

## 9. Issues sugeridos

1. `CORE-EF-HARDEN-EP-PAGOS-001` — Formalizar política outbox/idempotencia técnica extendida para `POST /financiero/pagos` y reversión.
2. `CORE-EF-HARDEN-EP-COM-001` — Idempotencia por `X-Op-Id` para confirmación venta completa (reserva/directa).
3. `CORE-EF-HARDEN-EP-COM-002` — Evidencia SQL de concurrencia/versionado para PATCH confirmar venta y flujos compuestos.
4. `CORE-EF-HARDEN-TESTS-001` — Suite de tests cruzados: rollback + outbox misma transacción + replay op_id.

## 10. Comandos ejecutados

- `rg --files -g 'AGENTS.md'`
- `cat AGENTS.md`
- `rg -n "financiero/pagos|revertir|confirmar-venta-completa|ventas/directa|PATCH /api/v1/ventas" backend/app/api/routers backend/tests backend/app/application backend/app/infrastructure/persistence/repositories backend/database backend/documentacion/CORE-EF backend/documentacion/DEV-SRV backend/documentacion/DEV-API`
- `sed -n '1,260p' backend/documentacion/CORE-EF/MATRIZ-CUMPLIMIENTO-ENDPOINTS-WRITE.md`
- `python - <<'PY' ...` (búsqueda focalizada de patrones en routers/services/repositories/tests)
- `rg -n "confirmar_venta_completa_desde_reserva|confirmar_venta_directa_completa|confirm_venta\(|registrar_pago_persona\(|revertir_pago_agrupado\(|class .*Service|Repository" ...`
- `sed -n '2760,3065p' backend/app/api/routers/financiero_router.py`
- `sed -n '1,260p' backend/app/application/financiero/services/registrar_pago_persona_service.py`
- `sed -n '1,220p' backend/app/application/financiero/services/revertir_pago_agrupado_service.py`
- `sed -n '2060,2360p' backend/app/infrastructure/persistence/repositories/financiero_repository.py`
- `sed -n '1360,1705p' backend/app/api/routers/comercial_router.py`
- `rg -n "ventas/.*/confirmar|confirm_venta\b|If-Match-Version" backend/tests`

