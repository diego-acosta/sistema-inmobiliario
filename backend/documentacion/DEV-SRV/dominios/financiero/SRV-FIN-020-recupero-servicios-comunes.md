# SRV-FIN-020 - Recupero de servicios comunes

## Estado
- estado: `IMPLEMENTADA V1`
- implementacion: egreso proveedor, anulacion, liquidacion, consulta formal y anulacion conservadora de recupero V1 implementados
- dominio owner: `financiero`
- origen operativo: `factura_servicio` del dominio `inmobiliario`
- clasificacion: nucleo financiero para recuperos contra personas

## Objetivo

Documentar el flujo `EMPRESA_PAGA_Y_RECUPERA` para facturas comunes,
compartidas, porcentuales o de servicios/impuestos comunes donde la
empresa/inmobiliaria paga al proveedor y luego recupera total o parcialmente el
importe contra responsables.

Este flujo no reemplaza `SERVICIO_TRASLADADO DIRECTO_RESPONSABLE`. Es un
circuito distinto: primero existe egreso real de la empresa y despues una deuda
de recupero a favor de la empresa.

## Alcance V1 de diseno

Incluye:

- facturas externas registradas como `factura_servicio`;
- servicios comunes o compartidos;
- facturas con responsables proporcionales o multiples responsables;
- pago al proveedor como egreso/caja/tesoreria de la empresa;
- generacion manual/controlada de obligaciones de recupero contra personas;
- cobro posterior mediante el flujo normal de pagos financieros.

No incluye:

- uso de `PAGO_EXTERNO_INFORMADO`;
- automatizacion desde evento `factura_servicio_registrada`;
- liquidacion automatica de expensas;
- impuestos trasladados completos;
- prorrateos complejos por cambio de responsable;
- reversion historica con recomputacion.

## Decision V1

1. `EMPRESA_PAGA_Y_RECUPERA` no usa `PAGO_EXTERNO_INFORMADO`.
2. El pago al proveedor representa egreso real de la empresa y debe pertenecer
   al circuito de caja/tesoreria.
3. El recupero posterior genera `obligacion_financiera` contra personas.
4. En V1, el egreso proveedor se registra explicitamente y el recupero sera
   manual/controlado, no automatico.
5. No se mezcla con `SERVICIO_TRASLADADO DIRECTO_RESPONSABLE`.
6. Expensas, impuestos y servicios comunes pueden usar este circuito como
   patron, pero no se implementan todos juntos.

## Flujo Conceptual

```text
proveedor emite factura externa
-> inmobiliario registra factura_servicio
-> empresa paga al proveedor
-> tesoreria registra egreso proveedor
-> financiero genera liquidacion de recupero manual/controlada
-> financiero crea obligacion_financiera de recupero
-> composicion_obligacion usa concepto de recupero
-> obligacion_obligado define responsables
-> responsable paga a la empresa por POST /api/v1/financiero/pagos
```

El pago del responsable a la empresa es un cobro normal. Debe poder generar
movimientos, aplicaciones, grupo de pago, constancia interna y efectos de caja
que correspondan al circuito financiero de pagos.

## Concepto financiero de recupero

Alternativas evaluadas:

1. `SERVICIO_RECUPERADO`
   - recomendado para V1 de recupero de servicios comunes;
   - distingue el recupero de una factura pagada por la empresa de
     `SERVICIO_TRASLADADO DIRECTO_RESPONSABLE`;
   - evita reutilizar `EXPENSA_TRASLADADA` cuando aun no existe liquidacion
     formal de expensas;
   - incorporado al catalogo `concepto_financiero` como base del flujo V1.

2. `EXPENSA_TRASLADADA`
   - reservar para una futura `liquidacion_expensa` o circuito formal de
     expensas;
   - no usar como concepto generico de todo servicio recuperado en V1.

3. `CARGO_RECUPERO`
   - alternativa generica futura si se decide unificar recuperos heterogeneos;
   - no recomendada para V1 porque pierde semantica de servicio y dificulta
     reportes por origen.

Decision recomendada V1:

- usar `SERVICIO_RECUPERADO` para recupero manual/controlado de servicios
  comunes pagados por la empresa;
- naturaleza: `DEBITO`;
- `es_imputable = true`;
- `permite_saldo = true`;
- `aplica_punitorio = true`, porque el recupero sera deuda exigible con la
  empresa y se cobrara por el flujo normal de pagos financieros;
- mantener `EXPENSA_TRASLADADA` para expensas formalmente liquidadas;
- mantener `IMPUESTO_TRASLADADO` para un flujo especifico futuro de impuestos;
- dejar `CARGO_RECUPERO` como opcion futura si se crea una liquidacion
  transversal de cargos.

## Reglas funcionales V1

- Una factura compartida o porcentual no habilita `PAGO_EXTERNO_INFORMADO`.
- `porcentaje_responsabilidad` de `asignacion_servicio_responsable` no
  significa pago directo proporcional al proveedor.
- El pago al proveedor y el recupero a personas son hechos distintos.
- La obligacion de recupero representa deuda con la empresa, no deuda con el
  proveedor.
- La generacion de recupero debe ser explicita e idempotente.
- El egreso proveedor minimo se registra con
  `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`.
- Los egresos proveedor registrados se consultan con
  `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor`.
- Los egresos proveedor registrados por error se anulan con
  `PATCH /api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular`.
- El recupero financiero se liquida explicitamente con
  `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`.
- La liquidacion se consulta con
  `GET /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}`.
- Las liquidaciones de una factura se listan con
  `GET /api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero`.
- El egreso proveedor crea `movimiento_tesoreria` y
  `egreso_proveedor_factura_servicio`.
- El egreso proveedor no crea `movimiento_financiero`,
  `obligacion_financiera`, composiciones, `SERVICIO_RECUPERADO`,
  `PAGO_EXTERNO_INFORMADO` ni recibo interno.
- Se permiten multiples egresos parciales hasta cubrir el importe total de la
  factura.
- No se permite que la suma de egresos activos supere
  `factura_servicio.importe_total`.
- El estado de pago proveedor es derivado en lectura; no se persiste en
  `factura_servicio`.
- Para totales de pago proveedor solo cuentan egresos no eliminados con
  `estado_egreso = REGISTRADO`.
- Estados derivados: `SIN_PAGO`, `PAGO_PARCIAL`, `PAGADA`, `SOBREPAGADA`.
- La anulacion V1 no borra fisicamente: cambia
  `egreso_proveedor_factura_servicio.estado_egreso = ANULADO` y
  `movimiento_tesoreria.estado = ANULADO`, preservando observaciones y motivo.
- La anulacion repetida devuelve resultado idempotente `YA_ANULADO`.
- Si un egreso proveedor ya fue usado por una `liquidacion_recupero` activa,
  su anulacion se bloquea.
- `liquidacion_recupero` V1 parte de una sola `factura_servicio`, usa egresos
  proveedor `REGISTRADO` no eliminados y no usados por liquidaciones activas.
- El vinculo `liquidacion_recupero_egreso` tiene estado propio
  `ACTIVO`/`ANULADO` y soft-delete; solo los vinculos `ACTIVO` sin
  `deleted_at` bloquean reutilizacion del egreso.
- La liquidacion permite recuperar hasta el total egresado disponible.
- La parte no recuperada queda como `importe_absorbido_empresa` y no genera
  obligacion.
- La liquidacion crea `relacion_generadora.tipo_origen = LIQUIDACION_RECUPERO`,
  `obligacion_financiera` `EMITIDA`, composicion `SERVICIO_RECUPERADO` y
  `obligacion_obligado` desde responsables explicitos del request.
- Los responsables de la liquidacion son snapshot explicito; V1 exige
  porcentajes mayores a cero y suma 100.
- Las consultas de `liquidacion_recupero` son solo lectura: no modifican saldos,
  no crean movimientos de tesoreria, no crean movimientos financieros y no
  generan obligaciones.
- La anulacion conservadora de `liquidacion_recupero` se ejecuta con
  `PATCH /api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}/anular`.
- La anulacion de `liquidacion_recupero` solo se permite si la obligacion
  asociada no tiene `aplicacion_financiera` activa, movimientos financieros
  activos asociados a esas aplicaciones, `liquidacion_punitorio` `ACTIVA` ni
  composiciones activas posteriores.
- Si existen operaciones activas, se bloquea con
  `LIQUIDACION_RECUPERO_TIENE_OPERACIONES`.
- Si ya estaba anulada, la repeticion devuelve `YA_ANULADA`.
- Al anular, se marca `liquidacion_recupero.estado_liquidacion = ANULADA`,
  `obligacion_financiera.estado_obligacion = ANULADA`,
  `composicion_obligacion.estado_composicion_obligacion = ANULADA`,
  `relacion_generadora.estado_relacion_generadora = CANCELADA` y el vinculo
  `liquidacion_recupero_egreso` queda `ANULADO` con `deleted_at`.
- La anulacion de `liquidacion_recupero` libera egresos para nueva liquidacion
  y no toca `movimiento_tesoreria`, `egreso_proveedor_factura_servicio`,
  `factura_servicio` ni pagos normales.
- El pago posterior del responsable se realiza por el flujo normal de pago por
  persona.

## Pendientes de definicion

- reglas de reparto por inmueble, unidad funcional, servicio, consumo o
  porcentaje para automatizar responsables;
- reversion historica de recuperos ya cobrados;
- tratamiento de impuestos trasladados;
- tratamiento de expensas formales.

## Implementacion V1

1. Registrar factura externa de servicio.
2. Registrar uno o mas egresos proveedor.
3. Liquidar recupero manual/controlado con responsables explicitos.
4. Materializar obligacion de recupero con obligados usando
   `SERVICIO_RECUPERADO`.
5. Consultar el detalle de la liquidacion o listar liquidaciones por factura.
6. Anular la liquidacion solo si no tiene operaciones financieras activas.
7. Cobrar por el flujo normal de pagos financieros.
8. La reversion historica de recuperos cobrados queda pendiente.

## Referencias

- [[SRV-INM-005-gestion-de-servicios-e-infraestructura]]
- [[MODELO-FINANCIERO-FIN]]
- [[RN-FIN]]
- [[RN-INM]]
- [[SRV-FIN-011-gestion-de-caja-financiera-y-garantias-monetarias]]
- [[SRV-FIN-019-registro-pago-persona]]
