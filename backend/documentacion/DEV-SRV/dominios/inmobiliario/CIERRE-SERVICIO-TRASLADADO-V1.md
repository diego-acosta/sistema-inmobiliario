# CIERRE-SERVICIO-TRASLADADO-V1

## Alcance Cerrado V1

SERVICIO_TRASLADADO V1 queda cerrado como flujo explícito entre inmobiliario y financiero para registrar facturas externas de servicios y, cuando corresponde, materializar una obligación financiera trasladada.

Incluye:

- `servicio`.
- `inmueble_servicio` / `unidad_funcional_servicio`.
- `factura_servicio`.
- `FACTURA_SERVICIO` como `relacion_generadora`.
- `asignacion_servicio_responsable`.
- materialización financiera de `SERVICIO_TRASLADADO`.
- estado de cuenta por persona con deuda agrupada en `TRASLADADOS`.
- pago externo informado para escenario `DIRECTO_RESPONSABLE`.

## Endpoints Implementados

Servicios:

- `POST /api/v1/servicios`
- `GET /api/v1/servicios`
- `GET /api/v1/servicios/{id_servicio}`
- `PUT /api/v1/servicios/{id_servicio}`
- `PUT /api/v1/servicios/{id_servicio}/baja`

Asociación servicio-objeto:

- `POST /api/v1/inmuebles/{id_inmueble}/servicios`
- `GET /api/v1/inmuebles/{id_inmueble}/servicios`
- `POST /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
- `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
- `GET /api/v1/servicios/{id_servicio}/inmuebles`
- `GET /api/v1/servicios/{id_servicio}/unidades-funcionales`

Facturas externas de servicio:

- `POST /api/v1/facturas-servicio`
- `GET /api/v1/facturas-servicio/{id_factura_servicio}`
- `GET /api/v1/facturas-servicio`

Responsables de servicios trasladados:

- `POST /api/v1/asignaciones-servicio-responsable`
- `GET /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}`
- `GET /api/v1/asignaciones-servicio-responsable`
- `PUT /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}`
- `PATCH /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}/baja`

Materialización y pago externo:

- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar`
- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/pago-externo`

Consulta financiera:

- `GET /api/v1/financiero/personas/{id_persona}/estado-cuenta`
- `GET /api/v1/financiero/deuda`
- `GET /api/v1/financiero/deuda/consolidado`

## Reglas Funcionales Principales

- El sistema no factura servicios.
- El sistema registra facturas externas emitidas por proveedores.
- `factura_servicio` no genera deuda automáticamente.
- La deuda se genera solo mediante materialización financiera explícita.
- Para materializar `SERVICIO_TRASLADADO`, `factura_servicio` debe tener `periodo_desde` y `periodo_hasta`.
- La materialización crea o reutiliza una `relacion_generadora` con `tipo_origen = FACTURA_SERVICIO` e `id_origen = id_factura_servicio`.
- La obligación financiera queda `EMITIDA`, con una composición `SERVICIO_TRASLADADO`.
- Los obligados se materializan desde `asignacion_servicio_responsable` vigente para el servicio + inmueble/UF + período.
- Si falta responsable vigente, se devuelve `OBLIGADO_NO_RESUELTO`.
- Si los porcentajes aplicables no suman 100%, se devuelve `RESPONSABLE_SERVICIO_AMBIGUO`.
- Si la factura cruza cambio de responsable, se devuelve `FACTURA_CRUZA_CAMBIO_RESPONSABLE`.
- `DIRECTO_RESPONSABLE` requiere un único `obligacion_obligado` activo con `porcentaje_responsabilidad = 100`.
- `PAGO_EXTERNO_INFORMADO` reduce o cancela deuda de `SERVICIO_TRASLADADO`.
- `PAGO_EXTERNO_INFORMADO` no impacta caja, tesorería, `codigo_pago_grupo` ni recibo interno.
- Las facturas compartidas, comunes o porcentuales corresponden al flujo futuro `EMPRESA_PAGA_Y_RECUPERA`.

## Decisiones Explícitas

- No se usa `relacion_persona_rol` como regla de traslado de servicios.
- No se usan porcentajes para registrar pagos directos proporcionales al proveedor.
- No se mezclan expensas ni impuestos trasladados en este flujo V1.
- No existe evento/consumer automático `factura_servicio_registrada` todavía.
- No existe recupero automático `EMPRESA_PAGA_Y_RECUPERA` todavía.
- No se emite comprobante fiscal ni recibo interno por `PAGO_EXTERNO_INFORMADO`.
- No se crea movimiento de caja ni tesorería por pago externo informado.

## Patches SQL Relevantes

- `backend/database/patch_relacion_generadora_factura_servicio_20260505.sql`
  - habilita `FACTURA_SERVICIO` como origen estructural de `relacion_generadora`.
- `backend/database/patch_asignacion_servicio_responsable_20260506.sql`
  - crea `asignacion_servicio_responsable` con metadata CORE-EF, FKs, XOR, vigencia, estado, porcentaje e índices.

Notas:

- `factura_servicio` ya forma parte del schema principal `backend/database/schema_inmobiliaria_20260418.sql`.
- La API V1 de `factura_servicio` no requiere patch SQL propio identificado en este cierre.
- El concepto financiero `SERVICIO_TRASLADADO` debe existir en catálogo para materializar; si falta, financiero devuelve `NOT_FOUND_CONCEPTO`.

## Tests De Cierre

Al cierre auditado:

```powershell
python -m pytest -q
```

Resultado:

```text
955 passed
```

También se ejecutó el conjunto focalizado:

```powershell
python -m pytest tests/test_factura_servicio_api.py tests/test_asignacion_servicio_responsable_api.py tests/test_fin_estado_cuenta_persona.py tests/test_fin_registrar_pago_persona.py -q
```

Resultado:

```text
134 passed
```

## Pendientes Futuros

- `EMPRESA_PAGA_Y_RECUPERA`.
- Expensas y recupero de servicios comunes.
- Impuestos trasladados.
- Reversión/anulación de `PAGO_EXTERNO_INFORMADO` si se requiere.
- Evento automático `factura_servicio_registrada`.
- Consumer financiero automático para `factura_servicio`.
- Recibos/reportes específicos de pagos externos.
- Implementar recupero `EMPRESA_PAGA_Y_RECUPERA`; el diseno V1 posterior
  recomienda `SERVICIO_RECUPERADO` para servicios comunes recuperados,
  reservando `EXPENSA_TRASLADADA` para expensas formales e
  `IMPUESTO_TRASLADADO` para impuestos.

## Decisión De Cierre

SERVICIO_TRASLADADO V1 queda cerrado funcionalmente para:

1. registro de factura externa,
2. resolución de responsable,
3. materialización financiera explícita,
4. lectura en estado de cuenta,
5. pago externo informado solo para `DIRECTO_RESPONSABLE`.

Queda fuera del cierre V1 todo recupero posterior de facturas comunes, compartidas o porcentuales bajo `EMPRESA_PAGA_Y_RECUPERA`.
