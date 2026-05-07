# Cierre EMPRESA_PAGA_Y_RECUPERA V1

## 1. Alcance cerrado V1

Queda cerrado el circuito V1 de `EMPRESA_PAGA_Y_RECUPERA` para recupero financiero de servicios comunes pagados por la empresa:

- `SERVICIO_RECUPERADO` como concepto financiero de deuda recuperable.
- `egreso_proveedor_factura_servicio` como registro del pago de la empresa al proveedor.
- Consulta de egresos proveedor por `factura_servicio`.
- Anulacion de egreso proveedor.
- `liquidacion_recupero`.
- Consulta formal de `liquidacion_recupero`.
- `relacion_generadora` de tipo `LIQUIDACION_RECUPERO`.
- `obligacion_financiera` con composicion `SERVICIO_RECUPERADO`.
- `obligacion_obligado` para responsables de la liquidacion.
- Pago posterior por flujo normal de pago por persona.

## 2. Flujo funcional

```text
factura_servicio
-> empresa paga proveedor
-> egreso proveedor
-> liquidacion_recupero
-> obligacion SERVICIO_RECUPERADO
-> responsable paga a empresa
```

## 3. Endpoints implementados

- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`
- `PATCH /api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular`
- `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`
- `GET /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}`
- `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`

## 4. Reglas principales

- No usa `PAGO_EXTERNO_INFORMADO`.
- No usa `SERVICIO_TRASLADADO`.
- No usa `EXPENSA_TRASLADADA`.
- No crea `movimiento_tesoreria` al liquidar recupero.
- No crea pago externo informado al liquidar recupero.
- Requiere egreso proveedor registrado.
- Bloquea egreso usado en liquidacion activa.
- Las consultas de `liquidacion_recupero` son solo lectura y no modifican
  saldos ni crean movimientos u obligaciones.
- El cobro posterior usa pago por persona.

## 5. Tests de cierre

- `reset_db.bat` reconstruye correctamente.
- `python -m pytest -q` -> `994 passed`.

## 6. Pendientes futuros no bloqueantes

- Anulacion/reversion de `liquidacion_recupero`.
- Agrupacion de varias facturas en una liquidacion.
- Recuperacion automatica desde egreso proveedor.
- Expensas formales.
- Impuestos trasladados.
- Test de segunda liquidacion con otro `X-Op-Id` para confirmar que no puede reutilizar el mismo egreso.
- Test de conteo antes/despues para confirmar que liquidar recupero no crea `movimiento_tesoreria` ni `PAGO_EXTERNO_INFORMADO`.
- Asserts directos sobre `liquidacion_recupero_factura`, `liquidacion_recupero_egreso` y `liquidacion_recupero_responsable`.

## 7. Decisiones explicitas

- `EMPRESA_PAGA_Y_RECUPERA` es circuito separado de `DIRECTO_RESPONSABLE`.
- `PAGO_EXTERNO_INFORMADO` queda reservado al pago directo al proveedor por responsable unico 100%.
- `SERVICIO_RECUPERADO` representa deuda recuperable con la empresa.
- `EXPENSA_TRASLADADA` queda reservada para expensas formales.
- `LIQUIDACION_RECUPERO` se persiste internamente como `tipo_origen = liquidacion_recupero` y puede exponerse en API/documentacion como `LIQUIDACION_RECUPERO`.

## Referencias

- [[SRV-FIN-020-recupero-servicios-comunes]]
- [[SRV-FIN-011-gestion-de-caja-financiera-y-garantias-monetarias]]
- [[SRV-FIN-019-registro-pago-persona]]
- [[MODELO-FINANCIERO-FIN]]
- [[RN-FIN]]
