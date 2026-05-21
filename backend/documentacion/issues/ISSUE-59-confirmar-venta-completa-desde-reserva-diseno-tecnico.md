# ISSUE-59 — Diseño técnico: confirmar venta completa desde reserva

## 0) Alcance y restricciones validadas

- Dominio dueño: **comercial** (reserva/venta/condiciones/confirmación). Plan de pago V2 y obligaciones se consumen vía servicios existentes sin rediseñar su semántica.
- No se modifica SQL.
- No se tocan pagos, caja ni recibos.
- No se elimina `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`.
- No se implementa venta directa sin reserva en este issue.

## 1) Estado actual (implementación verificada)

### 1.1 Router comercial actual

Secuencia actualmente fragmentada en endpoints separados:

1. `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta` → crea venta `borrador` y finaliza reserva.
2. `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales`.
3. `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar` (o variantes).
4. `PATCH /api/v1/ventas/{id_venta}/confirmar`.

### 1.2 Schemas existentes

- `GenerateVentaFromReservaVentaRequest/Response`.
- `DefineCondicionesComercialesVentaRequest/Response`.
- `GeneratePlanPagoVentaV2PorBloquesRequest/Response` + `Preview...`.
- `ConfirmVentaRequest/Response`.

No existe schema para “confirmar venta completa desde reserva” en un solo request/response.

### 1.3 Commands existentes

- `GenerateVentaFromReservaVentaCommand`.
- `DefineCondicionesComercialesVentaCommand`.
- `GeneratePlanPagoVentaV2PorBloquesCommand`.
- `ConfirmVentaCommand`.

No existe comando orquestador end-to-end.

### 1.4 Services existentes

- `GenerateVentaFromReservaVentaService`.
- `DefineCondicionesComercialesVentaService`.
- `GeneratePlanPagoVentaV2PorBloquesService`.
- `ConfirmVentaService`.

Observación crítica: cada servicio usa su propia frontera de validación/concurrencia y asume invocación endpoint por endpoint.

### 1.5 Repositories actuales

- `ComercialRepository`: reserva/venta/confirmación y escritura de outbox de venta confirmada.
- `PlanPagoVentaV2Repository`: plan pago v2, relación generadora, generación cronograma y obligaciones.

No existe una abstracción común única para transaccionar todos los pasos en una sola unidad de trabajo coordinada.

### 1.6 Tests actuales relevantes

- Flujo reserva→venta: `backend/tests/test_reservas_venta_generate_venta.py`.
- Condiciones: `backend/tests/test_ventas_definir_condiciones_comerciales.py`.
- Plan V2 bloques: `backend/tests/test_plan_pago_venta_v2_bloques_unificado.py`.
- Confirmación: `backend/tests/test_ventas_confirm.py`.
- E2E comercial-financiero: `backend/tests/test_fin_comercial_financiero_e2e.py`.

Conclusión: hay cobertura por pasos, pero no cobertura de un endpoint atómico “completo desde reserva”.

---

## 2) Recomendación de endpoint definitivo

### Recomendación principal

**Agregar**:

`POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`

Justificación:

- Mantiene el agregado raíz de entrada en `reserva_venta` para el caso “desde reserva”.
- Evita que el frontend encadene pasos tempranos que dejen estado intermedio inconsistente.
- Es explícito semánticamente y no rompe compatibilidad con endpoints actuales.

### Alternativa aceptable (menos preferida)

`POST /api/v1/ventas/confirmar-desde-reserva/{id_reserva_venta}`.

Se desaconseja por menor coherencia con el origen del flujo y porque la entidad venta todavía no existe al inicio.

---

## 3) Request schema propuesto

`ConfirmVentaCompletaDesdeReservaRequest`

```json
{
  "generar_venta": {
    "codigo_venta": "V-...",
    "fecha_venta": "2026-...Z",
    "observaciones": "..."
  },
  "condiciones_comerciales": {
    "monto_total": 123.45,
    "tipo_plan_financiero": "CUOTAS_FIJAS | CONTADO | ANTICIPO_Y_SALDO",
    "moneda": "ARS",
    "importe_anticipo": 0,
    "fecha_vencimiento_anticipo": "2026-...",
    "importe_saldo": 0,
    "fecha_vencimiento_saldo": "2026-...",
    "cuotas": [],
    "objetos": []
  },
  "plan_pago_v2": {
    "tipo_pago": "CONTADO | FINANCIADO",
    "monto_total_plan": 123.45,
    "moneda": "ARS",
    "bloques": [],
    "observaciones": "..."
  },
  "confirmacion": {
    "observaciones": "..."
  }
}
```

### Reglas de request

- `monto_total` de condiciones debe coincidir con suma de objetos.
- `monto_total_plan` debe coincidir con `monto_total` (regla del orquestador para evitar confirmación comercial con plan divergente).
- `plan_pago_v2` obligatorio para este endpoint (porque el objetivo explícito del issue es confirmar completo con plan + obligaciones).
- `If-Match-Version` requerido sobre `reserva_venta` como lock optimista de entrada.

---

## 4) Response schema propuesto

`ConfirmVentaCompletaDesdeReservaResponse`

```json
{
  "ok": true,
  "data": {
    "reserva_venta": {
      "id_reserva_venta": 1,
      "estado_reserva": "finalizada",
      "version_registro": 3
    },
    "venta": {
      "id_venta": 10,
      "estado_venta": "confirmada",
      "version_registro": 4
    },
    "plan_pago_v2": {
      "id_plan_pago_venta": 100,
      "estado_plan_pago": "GENERADO"
    },
    "generacion_cronograma_financiero": {
      "id_generacion_cronograma_financiero": 55,
      "estado_generacion": "GENERADA"
    },
    "obligaciones": {
      "cantidad": 15,
      "ids": [1000, 1001]
    }
  }
}
```

Nota: incluir resumen y no duplicar payloads completos ya disponibles en endpoints especializados.

---

## 5) Command propuesto

`ConfirmVentaCompletaDesdeReservaCommand`

Campos mínimos:

- `context`.
- `id_reserva_venta`.
- `if_match_version_reserva`.
- `generar_venta` (subestructura).
- `condiciones_comerciales` (subestructura).
- `plan_pago_v2` (subestructura).
- `confirmacion` (subestructura).

---

## 6) Service/orquestador propuesto

`ConfirmVentaCompletaDesdeReservaService` (application/comercial/services)

Secuencia interna:

1. Validación de precondiciones de entrada (request coherente y monto_total == monto_total_plan).
2. Ejecutar `GenerateVentaFromReservaVentaService`.
3. Con `id_venta` resultante, ejecutar `DefineCondicionesComercialesVentaService`.
4. Ejecutar `GeneratePlanPagoVentaV2PorBloquesService`.
5. Ejecutar `ConfirmVentaService`.
6. Armar response agregado.

### Reuso recomendado

- Reusar servicios actuales para no duplicar reglas de negocio.
- Introducir utilitario interno para normalizar mapeo de errores de cada paso → error final del orquestador.

---

## 7) Lógica a mover/compartir para evitar commits intermedios

No mover reglas de dominio entre servicios. Sí extraer piezas de orquestación técnica:

- Constructor común de `ComercialCommandContext` en router.
- Helper para parsear `If-Match-Version`.
- Mapeador común `service_errors -> HTTP` para comercial.

Si no se extrae, el endpoint nuevo duplicará mucho código del router actual.

---

## 8) Frontera transaccional

## Opción A (recomendada): **una sola transacción física**

- El endpoint abre una única transacción de DB (`Session.begin()`).
- Todos los servicios invocados usan la **misma session**.
- Cualquier excepción o `AppResult.fail` en cualquier paso dispara rollback total.

Ventajas:

- Cero estado intermedio persistido (ni venta borrador huérfana ni reserva finalizada sin plan).
- Mantiene consistencia fuerte del caso de uso.

Condición técnica:

- Verificar que `GeneratePlanPagoVentaV2PorBloquesService` no cierre/commit independiente incompatible (hoy usa `_transaction()` interno; habría que permitir modo “usar transacción externa”).

## Opción B (si A no es viable en primera iteración)

Saga local con estados recuperables:

- Paso 1 crea venta en borrador y marca `origen_confirmacion_completa_pendiente=true` (lógico, no SQL nuevo: usar observación/metadato existente sólo si ya existe soporte; si no existe, esta opción pierde trazabilidad).
- Si falla un paso posterior, endpoint retorna estado recuperable con `id_venta` y error explícito para reintento interno.

Desventaja: deja estado intermedio, exactamente lo que el issue busca evitar. Usar sólo como contingencia temporal.

---

## 9) Rollback / compensación

### Si Opción A

- Rollback automático transaccional ante cualquier fallo.
- No se requiere compensación de negocio adicional.

### Si Opción B

Compensaciones mínimas:

- Si falla después de generar plan/obligaciones y antes de confirmar venta: anular/descartar plan borrador generado dentro del mismo flujo de reintento.
- Si falla después de finalizar reserva y antes de confirmar venta: reintentar sobre la misma venta (idempotencia por `codigo_venta`) y no regenerar duplicados.

---

## 10) Errores HTTP y `error_code` recomendados

Mantener contrato estilo router comercial actual:

- `404 NOT_FOUND`: reserva/venta/objeto inexistente.
- `409 CONCURRENCY_ERROR`: `If-Match-Version` inválido o mismatch.
- `409 CONFLICT`: plan vivo incompatible.
- `400 APPLICATION_ERROR`: reglas de negocio (estado inválido, condiciones incompletas, suma inválida, comprador no resoluble, etc.).
- `500 INTERNAL_ERROR`: excepción no controlada.

`details.errors` debe propagar códigos internos originales del servicio fallido para diagnóstico.

---

## 11) Tests mínimos necesarios (nuevo endpoint)

1. **Happy path**: confirma completa desde reserva y deja:
   - reserva `finalizada`,
   - venta `confirmada`,
   - plan `GENERADO`,
   - obligaciones creadas,
   - outbox `venta_confirmada` emitido.

2. **Rollback atómico**: forzar falla en paso 3/4 y validar que:
   - no queda venta creada,
   - reserva no se finaliza,
   - no quedan obligaciones ni plan.

3. **Concurrencia reserva**: `If-Match-Version` incorrecto → `409`.

4. **Condiciones inválidas**: mismatch objetos/montos → `400`.

5. **Plan inválido**: suma bloques inválida o comprador no resoluble → `400`.

6. **Conflicto plan vivo**: `409`.

7. **Idempotencia funcional mínima** (reintento con mismo `codigo_venta` tras error controlado) → error determinístico sin duplicación.

---

## 12) Archivos a modificar en futuro patch (lista precisa)

### Router / API
- `backend/app/api/routers/comercial_router.py`
- `backend/app/api/schemas/comercial.py`

### Application commands/services
- `backend/app/application/comercial/commands/confirm_venta_completa_desde_reserva.py` (nuevo)
- `backend/app/application/comercial/services/confirm_venta_completa_desde_reserva_service.py` (nuevo)
- `backend/app/application/comercial/services/generate_plan_pago_venta_v2_por_bloques_service.py` (ajuste para transacción externa opcional)

### Repositorios
- `backend/app/infrastructure/persistence/repositories/comercial_repository.py` (si hace falta helper de lectura agregada final)
- `backend/app/infrastructure/persistence/repositories/plan_pago_venta_v2_repository.py` (solo si requiere helper de sesión/transacción compartida)

### Tests
- `backend/tests/test_reservas_venta_confirmar_venta_completa.py` (nuevo)
- posible ajuste puntual en fixtures/utilidades existentes si se reutilizan helpers.

---

## 13) Riesgos detectados

1. **Riesgo transaccional**: servicio de plan V2 maneja transacción propia; si no se adapta, rompe atomicidad end-to-end.
2. **Riesgo de contratos de error**: cada endpoint actual mapea errores distinto; el orquestador puede devolver mensajes inconsistentes si no se centraliza mapping.
3. **Riesgo de duplicación**: repetir validaciones en orquestador y en servicios puede divergir.
4. **Riesgo de performance**: operación compuesta con múltiples lecturas/escrituras; requerirá test de integración robusto para tiempos y locks.

---

## 14) Recomendación final

**Implementar, pero dividido en subissues técnicos** para reducir riesgo:

1. **Subissue A**: contrato API (router + schemas + command + mapping errores) sin activar lógica final.
2. **Subissue B**: orquestador transaccional único + adaptación de servicio Plan V2 para transacción externa.
3. **Subissue C**: suite de tests atómicos/rollback/idempotencia y endurecimiento de errores.

Esto permite entregar valor incremental sin romper compatibilidad, y garantiza que el objetivo principal (evitar ventas incompletas con reserva finalizada) quede cubierto de forma verificable.
