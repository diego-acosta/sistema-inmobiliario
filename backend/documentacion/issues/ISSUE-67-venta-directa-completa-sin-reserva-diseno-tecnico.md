# ISSUE-67 — Diseño técnico: venta directa completa sin reserva

## Estado de implementación actual (backend)

> **Actualizado al estado real del repositorio:** este diseño base ya fue implementado en backend y el flujo está operativo.

- Endpoint implementado: `POST /api/v1/ventas/directa/confirmar-venta-completa`.
- Ya no es skeleton ni retorna `501`.
- El orquestador implementado es `ConfirmVentaDirectaCompletaService`.
- La creación inicial de venta directa en borrador dentro de la transacción se realiza con `_create_venta_directa_tx`.
- El flujo real implementado en una única transacción física integra: crear venta directa (`_create_venta_directa_tx`) → definir condiciones comerciales → generar Plan Pago V2 → confirmar venta.
- Ante cualquier falla funcional o técnica, el flujo aplica rollback transaccional total.
- Validaciones relevantes implementadas:
  - disponibilidad actual `DISPONIBLE`
  - ocupación conflictiva
  - venta conflictiva
  - reserva conflictiva
  - comprador válido
  - rol comprador (`COMPRADOR`)
  - coherencia de monto total entre objetos, condiciones comerciales y plan
  - validación jerárquica inmueble ↔ unidad funcional (agregada en PR #74).

**Aclaración:** este endpoint no representa un “alta directa simple de venta”; implementa una orquestación completa transaccional de punta a punta.

**Pendientes fuera de este documento**

- Actualizar DEV-API comercial para reflejar el estado implementado.
- Evaluar regla jerárquica equivalente para reservas de venta.
- Definir política documental para documentos históricos / `_tmp`.
- Cerrar decisión de transición de disponibilidad post confirmación, si aún no está formalizada.

---

## 1) Contexto

Ya existe y funciona el flujo completo desde reserva existente:

`POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`

Ese flujo permite confirmar una venta completa partiendo de una `reserva_venta` confirmada, coordinando en una única transacción la generación de venta, condiciones comerciales, Plan Pago V2 y confirmación.

El origen pendiente del wizard es **Venta directa sin reserva**.

Este nuevo flujo:

- No debe crear una reserva artificial.
- No debe usar `reserva_venta` como paso obligatorio.
- No debe romper el flujo desde reserva existente.
- No debe rediseñar Plan Pago V2.
- No debe tocar pagos, caja ni recibos.
- No debe calcular cronograma financiero en frontend.

Dominio dueño: **comercial**. La venta directa pertenece al dominio comercial porque crea y confirma una compraventa. Las reglas de disponibilidad deben validarse contra el estado operativo/inmobiliario existente, pero sin mover ownership ni introducir efectos operativos nuevos dentro de este issue.

---

## 2) Endpoint recomendado

Endpoint propuesto:

```http
POST /api/v1/ventas/directa/confirmar-venta-completa
```

Justificación:

- Expresa que el caso de uso crea y confirma una venta completa.
- Deja claro que no parte de una reserva.
- Mantiene separado el flujo directo del flujo desde reserva.
- Evita sobrecargar endpoints genéricos de ventas.

Alternativas descartadas:

- `POST /api/v1/ventas`: se descarta por ambigüedad entre crear una venta borrador y ejecutar la confirmación completa.
- `POST /api/v1/ventas/directa`: se descarta porque no expresa que confirma todo el flujo; podría interpretarse como creación simple de venta directa.

---

## 3) Payload propuesto

```json
{
  "generar_venta": {
    "codigo_venta": "VD-0001",
    "fecha_venta": "2026-05-22T10:00:00",
    "monto_total": "12000000.00",
    "observaciones": "Venta directa"
  },
  "objetos": [
    {
      "id_inmueble": 10,
      "id_unidad_funcional": null,
      "precio_asignado": "12000000.00",
      "observaciones": null
    }
  ],
  "compradores": [
    {
      "id_persona": 25,
      "id_rol_participacion": 3,
      "fecha_desde": "2026-05-22",
      "fecha_hasta": null,
      "observaciones": null
    }
  ],
  "condiciones_comerciales": {
    "monto_total": "12000000.00",
    "tipo_plan_financiero": "CUOTAS_FIJAS",
    "moneda": "ARS",
    "importe_anticipo": "2000000.00",
    "fecha_vencimiento_anticipo": "2026-05-30",
    "importe_saldo": "10000000.00",
    "fecha_vencimiento_saldo": null,
    "cuotas": 10
  },
  "plan_pago_v2": {
    "tipo_pago": "FINANCIADO",
    "monto_total_plan": "12000000.00",
    "moneda": "ARS",
    "bloques": [],
    "observaciones": null
  },
  "confirmacion": {
    "observaciones": "Confirmada desde venta directa"
  }
}
```

Regla importante:

- Los objetos deben ir arriba del payload, en `objetos`.
- No deben duplicarse dentro de `condiciones_comerciales.objetos`.
- El service debe derivar internamente los objetos requeridos por `DefineCondicionesComercialesVentaService`.

Esto evita una doble fuente de verdad entre:

- objetos usados para crear la venta;
- objetos usados para definir precios comerciales.

---

## 4) Response esperado

```json
{
  "ok": true,
  "data": {
    "venta": {
      "id_venta": 123,
      "codigo_venta": "VD-0001",
      "estado_venta": "confirmada",
      "version_registro": 4
    },
    "plan_pago_v2": {
      "id_plan_pago_venta": 55,
      "estado_plan_pago": "generado"
    },
    "generacion_cronograma_financiero": {
      "ok": true,
      "cantidad_obligaciones": 10
    },
    "obligaciones": {
      "cantidad": 10,
      "ids": [1001, 1002]
    }
  }
}
```

La respuesta no debe incluir `reserva_venta`, porque el flujo no parte de una reserva.

---

## 5) Orquestador

Nuevo service propuesto:

```text
ConfirmVentaDirectaCompletaService
```

Flujo transaccional:

1. Validar payload base.
2. Abrir una única transacción física.
3. Crear venta directa en estado `borrador` con `id_reserva_venta = NULL`.
4. Asociar objetos inmobiliarios a la venta.
5. Asociar comprador mediante `relacion_persona_rol`.
6. Llamar a `DefineCondicionesComercialesVentaService` con adapter transaccional.
7. Llamar a `GeneratePlanPagoVentaV2PorBloquesService.execute_in_existing_transaction(...)`.
8. Llamar a `ConfirmVentaService` con adapter transaccional.
9. Hacer commit único al final.
10. Hacer rollback total ante cualquier error funcional o técnico.

El orquestador no debe llamar a wrappers públicos que hagan commit interno.

Debe seguir el patrón transaccional del orquestador desde reserva, pero reemplazando la generación desde reserva por una creación directa de venta borrador.

---

## 6) Repository

Método interno propuesto:

```python
_create_venta_directa_tx(...)
```

Responsabilidad:

- Insertar `venta` con `id_reserva_venta = NULL`.
- Insertar `venta_objeto_inmobiliario`.
- Insertar relaciones comprador/rol para la venta.
- No hacer commit.
- No hacer rollback.
- Devolver snapshot mínimo:
  - `id_venta`
  - `codigo_venta`
  - `estado_venta`
  - `version_registro`

No se recomienda agregar wrapper público todavía, salvo que se implemente un endpoint separado para crear una venta directa en borrador.

Para este issue, el consumidor esperado es únicamente el orquestador `ConfirmVentaDirectaCompletaService`.

---

## 7) Reglas de validación

### 7.1 Disponibilidad

Para venta directa, los objetos deben tener disponibilidad actual `DISPONIBLE`.

Debe rechazarse:

- Objeto en disponibilidad `RESERVADA`.
- Objeto en disponibilidad `NO_DISPONIBLE`.
- Objeto sin disponibilidad activa.
- Objeto con múltiples disponibilidades activas.
- Objeto con ocupación activa.
- Objeto con venta activa o conflictiva existente.
- Objeto con reserva activa o confirmada vigente.

La diferencia clave contra el flujo desde reserva es:

- Venta desde reserva parte de objetos `RESERVADA`.
- Venta directa debe partir de objetos `DISPONIBLE`.

### 7.2 Multiobjeto

Reglas:

- Cada item debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`.
- No puede haber objetos duplicados.
- Todos los objetos deben existir.
- La suma de `precio_asignado` debe ser igual a `condiciones_comerciales.monto_total`.
- `condiciones_comerciales.monto_total` debe ser igual a `plan_pago_v2.monto_total_plan`.

### 7.3 Comprador

Primera implementación:

- Exigir exactamente un comprador financiero principal.
- El rol debe ser `COMPRADOR`.
- La relación `relacion_persona_rol` debe crearse antes de generar Plan Pago V2.
- El caso multi-comprador queda fuera de esta etapa.

Motivo:

Plan Pago V2 resuelve comprador desde la venta. Si la relación comprador/venta no existe antes de generar el plan, la generación financiera puede fallar o quedar sin sujeto comercial claro.

---

## 8) Archivos tocados en la implementación

> Esta sección se conserva como traza histórica del diseño base.

Backend:

- `backend/app/api/schemas/comercial.py`
- `backend/app/api/routers/comercial_router.py`
- `backend/app/application/comercial/commands/confirm_venta_directa_completa.py`
- `backend/app/application/comercial/services/confirm_venta_directa_completa_service.py`
- `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
- `backend/tests/test_ventas_directa_confirmar_venta_completa.py`
- `backend/tests/test_ventas_directa_create_tx.py`

Frontend posterior (si aplica):

- `frontend/flet_app/app/api_client.py`
- `frontend/flet_app/app/pages/venta_create_wizard_page.py`

---

## 9) Tests mínimos


Casos mínimos para backend:

- Venta directa exitosa.
- Objeto inexistente.
- Objeto no disponible.
- Objeto reservado por reserva vigente.
- Venta activa existente sobre objeto.
- Falla en condiciones comerciales.
- Falla en Plan Pago V2.
- Falla en confirmación.
- Código de venta duplicado.
- Multiobjeto exitoso.
- Multiobjeto duplicado.
- Sin comprador o comprador con rol distinto de `COMPRADOR`.
- Regresión del flujo desde reserva existente.

Los casos de falla deben verificar rollback total:

- No queda venta creada.
- No quedan objetos asociados a una venta huérfana.
- No quedan relaciones comprador/venta huérfanas.
- No quedan plan ni obligaciones si falla después de crearse la venta.

---

## 10) Subissues recomendados (traza histórica)

1. Contrato backend y skeleton del endpoint.
2. Repository `_create_venta_directa_tx` y validaciones asociadas.
3. Orquestador `ConfirmVentaDirectaCompletaService`.
4. Tests de rollback y conflictos comerciales.
5. Conexión frontend del origen `VENTA_DIRECTA`.
6. Seed demo con objeto `DISPONIBLE` y comprador válido.

---

## 11) Riesgos pendientes

Disponibilidad es el punto más sensible.

El flujo desde reserva parte de objetos `RESERVADA`, mientras que venta directa debe partir de objetos `DISPONIBLE`. La implementación debe evitar que la venta directa saltee una reserva vigente.

Queda pendiente definir si confirmar una venta directa debe cambiar disponibilidad física del objeto. Si ese cambio requiere un evento operativo o una nueva regla de integración entre dominios, debe diseñarse en otro issue. No conviene mezclar ese efecto operativo dentro de este caso de uso comercial.

También debe mantenerse la separación con la lógica financiera:

- El frontend no calcula cronograma.
- El orquestador no duplica lógica financiera.
- Plan Pago V2 sigue siendo la fuente de cálculo y generación de obligaciones.

