# Cierre EMPRESA_PAGA_Y_RECUPERA V1

## 1. Alcance cerrado V1

Quedan cerrados los circuitos V1 hermanos de recupero financiero de servicios
comunes e impuestos trasladados:

- `SERVICIO_RECUPERADO` como concepto financiero de deuda recuperable.
- `egreso_proveedor_factura_servicio` como registro del pago de la empresa al proveedor.
- Consulta de egresos proveedor por `factura_servicio`.
- Anulacion de egreso proveedor.
- `liquidacion_recupero`.
- Consulta formal de `liquidacion_recupero`.
- Anulacion conservadora de `liquidacion_recupero` sin pagos/aplicaciones.
- `relacion_generadora` de tipo `LIQUIDACION_RECUPERO`.
- `obligacion_financiera` con composicion `SERVICIO_RECUPERADO`.
- `obligacion_obligado` para responsables de la liquidacion.
- Pago posterior por flujo normal de pago por persona.
- `IMPUESTO_TRASLADADO` como concepto financiero de deuda fiscal trasladada.
- `comprobante_impuesto` como origen documental fiscal.
- `egreso_impuesto_empresa` como registro del pago de la empresa al organismo.
- `liquidacion_impuesto_trasladado`.
- Consulta formal de `liquidacion_impuesto_trasladado`.
- Listado de liquidaciones por `comprobante_impuesto`.
- Anulacion conservadora de `liquidacion_impuesto_trasladado`.
- Bloqueo de anulacion de egreso impuesto si sostiene liquidacion activa.

## 2. Flujo funcional

```text
factura_servicio
-> empresa paga proveedor
-> egreso proveedor
-> liquidacion_recupero
-> obligacion SERVICIO_RECUPERADO
-> responsable paga a empresa

comprobante_impuesto
-> empresa paga organismo o responsable directo
-> egreso_impuesto_empresa si corresponde
-> liquidacion_impuesto_trasladado
-> obligacion IMPUESTO_TRASLADADO
-> responsable paga a empresa por flujo normal, salvo pago externo futuro
```

## 3. Endpoints implementados

- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `PATCH /api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular`
- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`
- `GET /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`
- `PATCH /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}/anular`
- `POST /api/v1/comprobantes-impuesto`
- `GET /api/v1/comprobantes-impuesto/{id_comprobante_impuesto}`
- `GET /api/v1/comprobantes-impuesto`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos`
- `PATCH /api/v1/financiero/egresos-impuesto-empresa/{id_egreso_impuesto_empresa}/anular`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `GET /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `PATCH /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/anular`

## 4. Reglas principales

- No usa `PAGO_EXTERNO_INFORMADO`.
- No usa `SERVICIO_TRASLADADO`.
- No usa `EXPENSA_TRASLADADA`.
- No crea `movimiento_tesoreria` al liquidar recupero.
- No crea pago externo informado al liquidar recupero.
- Requiere egreso proveedor registrado.
- Bloquea egreso usado en liquidacion activa.
- Bloquea egreso impuesto usado en liquidacion fiscal activa con
  `EGRESO_IMPUESTO_CON_LIQUIDACION_TRASLADADA`.
- El vinculo `liquidacion_recupero_egreso` soporta soft-delete y estado
  `ACTIVO`/`ANULADO`; solo vinculos activos bloquean reutilizacion del egreso.
- Las consultas de `liquidacion_recupero` son solo lectura y no modifican
  saldos ni crean movimientos u obligaciones.
- La anulacion V1 de `liquidacion_recupero` solo se permite si la obligacion
  `SERVICIO_RECUPERADO` no tiene aplicaciones activas, movimientos financieros
  asociados, punitorios activos ni composiciones posteriores activas.
- La anulacion V1 marca `liquidacion_recupero = ANULADA`,
  `obligacion_financiera = ANULADA`, composiciones `ANULADA`,
  `relacion_generadora = CANCELADA` y libera egresos anulando logicamente
  `liquidacion_recupero_egreso`.
- La anulacion de `liquidacion_recupero` no toca `movimiento_tesoreria`,
  `egreso_proveedor_factura_servicio`, `factura_servicio` ni pagos normales.
- La anulacion repetida devuelve `YA_ANULADA`.
- El cobro posterior usa pago por persona.

## 5. Tests de cierre

- `reset_db.bat` reconstruye correctamente.
- `python -m pytest tests/test_impuesto_trasladado_api.py -q` -> `58 passed`.
- `python -m pytest -q` -> `1064 passed`.

## 6. Pendientes futuros no bloqueantes

- Reversion historica de `liquidacion_recupero` ya cobrada.
- Agrupacion de varias facturas en una liquidacion.
- Recuperacion automatica desde egreso proveedor.
- Expensas formales.
- Test de conteo antes/despues para confirmar que liquidar recupero no crea `movimiento_tesoreria` ni `PAGO_EXTERNO_INFORMADO`.
- Asserts directos sobre `liquidacion_recupero_factura` y `liquidacion_recupero_responsable`.
- Pago externo informado para impuesto `DIRECTO_RESPONSABLE`.

## 7. Decisiones explicitas

- `EMPRESA_PAGA_Y_RECUPERA` es circuito separado de `DIRECTO_RESPONSABLE`.
- `PAGO_EXTERNO_INFORMADO` queda reservado al pago directo al proveedor por responsable unico 100%.
- `SERVICIO_RECUPERADO` representa deuda recuperable con la empresa.
- `EXPENSA_TRASLADADA` queda reservada para expensas formales.
- `LIQUIDACION_RECUPERO` se persiste internamente como `tipo_origen = liquidacion_recupero` y puede exponerse en API/documentacion como `LIQUIDACION_RECUPERO`.
- `IMPUESTO_TRASLADADO` no reutiliza `liquidacion_recupero`; usa
  `liquidacion_impuesto_trasladado` como entidad propia.
- La anulacion conservadora no reescribe tesoreria historica ni movimientos
  financieros; bloquea cuando hay avance financiero.

## Referencias

- [[SRV-FIN-020-recupero-servicios-comunes]]
- [[SRV-FIN-021-impuestos-trasladados]]
- [[SRV-FIN-011-gestion-de-caja-financiera-y-garantias-monetarias]]
- [[SRV-FIN-019-registro-pago-persona]]
- [[MODELO-FINANCIERO-FIN]]
- [[RN-FIN]]
