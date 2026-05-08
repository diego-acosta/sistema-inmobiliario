# SRV-FIN-021 - Impuestos trasladados

## Estado
- estado: `IMPLEMENTADA V1`
- implementacion: registro y consulta de `comprobante_impuesto`, egreso empresa, consulta, anulacion, liquidacion `IMPUESTO_TRASLADADO`, consulta formal, listado por comprobante, pago externo informado `DIRECTO_RESPONSABLE`, anulacion conservadora y bloqueo de egreso base usado por liquidacion activa implementados. Submodulo `impuesto_trasladado` cerrado en V1.
- dominio owner: `financiero`
- origen operativo: `comprobante_impuesto`
- clasificacion: nucleo financiero para traslado de impuestos, tasas o contribuciones a responsables

## Objetivo

Documentar el diseno V1 corregido para impuestos, tasas o contribuciones
trasladadas, separado de los circuitos de servicios.

El flujo no usa `factura_servicio`, no usa `SERVICIO_TRASLADADO`, no usa
`SERVICIO_RECUPERADO` y no usa `EXPENSA_TRASLADADA`.

## Entidad origen

V1 crea entidad propia `comprobante_impuesto`.

Datos minimos:

- organismo
- tipo_impuesto
- partida o nomenclatura como snapshot textual V1
- numero_comprobante
- periodo_desde
- periodo_hasta
- fecha_emision
- fecha_vencimiento
- importe_total
- `id_inmueble` o `id_unidad_funcional`
- estado del comprobante
- observaciones

`comprobante_impuesto` registra el origen documental. No genera deuda
automaticamente. La modalidad financiera define que operaciones se habilitan.

Endpoints implementados:

- `POST /api/v1/comprobantes-impuesto`
- `GET /api/v1/comprobantes-impuesto/{id_comprobante_impuesto}`
- `GET /api/v1/comprobantes-impuesto`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos`
- `PATCH /api/v1/financiero/egresos-impuesto-empresa/{id_egreso_impuesto_empresa}/anular`
- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `GET /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `POST /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/pago-externo`
- `PATCH /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/anular`

Reglas implementadas:

- XOR entre `id_inmueble` e `id_unidad_funcional`;
- organismo, tipo de impuesto y numero de comprobante obligatorios;
- importe no negativo;
- periodo valido si se informa completo;
- vencimiento no anterior a emision si se informa `fecha_emision`;
- modalidad en `EMPRESA_ASUME`, `DIRECTO_RESPONSABLE` o
  `EMPRESA_PAGA_Y_RECUPERA`;
- duplicado activo por organismo + numero de comprobante bloqueado;
- no crea `movimiento_tesoreria`, `relacion_generadora`,
  `obligacion_financiera` ni `composicion_obligacion`.

## Concepto financiero

La deuda fiscal trasladada debe usar `IMPUESTO_TRASLADADO`.

Decision V1:

- no crear `IMPUESTO_RECUPERADO`;
- no reutilizar `SERVICIO_RECUPERADO`;
- no usar `EXPENSA_TRASLADADA`;
- mantener `IMPUESTO_TRASLADADO.aplica_punitorio = false` salvo decision
  posterior documentada y migrada.

## Modalidades V1

### EMPRESA_ASUME

La empresa paga el impuesto y no lo recupera.

Reglas:

- se registra egreso de tesoreria;
- no genera `obligacion_financiera`;
- no genera `IMPUESTO_TRASLADADO`;
- no genera `PAGO_EXTERNO_INFORMADO`;
- no aparece como deuda de responsable;
- bloquea `liquidacion_impuesto_trasladado` con
  `IMPUESTO_EMPRESA_ASUME_NO_TRASLADABLE`.

### DIRECTO_RESPONSABLE

El responsable debe pagar directamente al organismo.

Reglas:

- V1 materializa una obligacion `IMPUESTO_TRASLADADO` desde
  `liquidacion_impuesto_trasladado`;
- no requiere `egreso_impuesto_empresa`;
- la base de liquidacion es `comprobante_impuesto.importe_total`;
- los responsables son explicitos, con porcentajes positivos que suman 100%;
- el pago externo informado esta implementado sobre la liquidacion fiscal;
- el pago externo no crea caja, tesoreria, egreso de empresa ni recibo interno;
- reduce saldo mediante movimiento/aplicacion financiera de tipo
  `PAGO_EXTERNO_INFORMADO`, con reglas analogas al escenario
  `DIRECTO_RESPONSABLE` de servicios, pero sobre origen fiscal propio.

### EMPRESA_PAGA_Y_RECUPERA

La empresa paga el impuesto al organismo y luego recupera el importe total o
parcial contra responsables.

Reglas:

- el pago al organismo registra egreso de tesoreria;
- el recupero se liquida explicitamente;
- la liquidacion genera obligacion `IMPUESTO_TRASLADADO`;
- requiere `egreso_impuesto_empresa` `REGISTRADO` disponible;
- puede trasladar hasta el total egresado disponible;
- vincula egresos usados mediante `liquidacion_impuesto_trasladado_egreso`
  `ACTIVO`;
- el responsable paga a la empresa por el flujo normal de pago por persona;
- la liquidacion no crea `movimiento_tesoreria` nuevo;
- la anulacion es conservadora y se bloquea si existen pagos, aplicaciones,
  punitorios u operaciones posteriores.

## Relacion con tesoreria

El pago real del impuesto por la empresa debe entrar por `movimiento_tesoreria`.

V1 separa:

- egreso por impuesto asumido por la empresa;
- egreso por impuesto que luego se recupera;
- pago externo informado por responsable, que no impacta tesoreria.

### Egreso empresa implementado

`egreso_impuesto_empresa` registra pagos parciales o totales de la empresa al
organismo fiscal.

Reglas implementadas:

- requiere `comprobante_impuesto` existente y `REGISTRADO`;
- aplica solo a modalidades `EMPRESA_ASUME` y `EMPRESA_PAGA_Y_RECUPERA`;
- bloquea `DIRECTO_RESPONSABLE`;
- requiere `cuenta_financiera` origen activa;
- permite multiples parciales sin superar `importe_total`;
- crea `movimiento_tesoreria` con
  `tipo_movimiento_tesoreria = EGRESO_IMPUESTO_EMPRESA`;
- crea vinculo `egreso_impuesto_empresa`;
- no crea `movimiento_financiero`, `relacion_generadora`,
  `obligacion_financiera` ni `IMPUESTO_TRASLADADO`;
- no impacta estado de cuenta;
- no usa `PAGO_EXTERNO_INFORMADO`.

Consulta implementada:

- deriva `total_egresado`, `saldo_pendiente_pago_impuesto` y
  `estado_pago_impuesto`;
- suma solo egresos `REGISTRADO` y no eliminados;
- lista egresos no eliminados, incluyendo anulados;
- no persiste estado de pago en `comprobante_impuesto`;
- no modifica deuda, saldos ni estado de cuenta.

Anulacion implementada:

- `PATCH /api/v1/financiero/egresos-impuesto-empresa/{id}/anular`;
- si el egreso esta `REGISTRADO`, marca `egreso_impuesto_empresa.estado_egreso`
  y `movimiento_tesoreria.estado` como `ANULADO`;
- preserva observaciones y agrega motivo de anulacion;
- es idempotente si ya estaba `ANULADO`;
- no toca `comprobante_impuesto`;
- no crea ni modifica `movimiento_financiero`, `relacion_generadora`,
  `obligacion_financiera` ni estado de cuenta;
- bloquea anulacion si una `liquidacion_impuesto_trasladado` activa usa el
  egreso.

## Relacion con liquidacion_recupero

No reutilizar `liquidacion_recupero` directamente.

`liquidacion_recupero` pertenece al circuito de servicios comunes y esta
acoplada a `factura_servicio`, `egreso_proveedor_factura_servicio` y
`SERVICIO_RECUPERADO`.

V1 de impuestos puede reutilizar el patron:

- entidad de liquidacion propia;
- vinculos a comprobantes;
- vinculos a egresos fiscales usados;
- snapshot de responsables;
- relacion generadora propia;
- obligacion derivada;
- anulacion conservadora;
- liberacion logica de egresos usados.

Entidad implementada: `liquidacion_impuesto_trasladado`.

### Liquidacion implementada V1

`liquidacion_impuesto_trasladado` materializa deuda fiscal trasladada sin
reutilizar `liquidacion_recupero`.

Endpoint implementado:

- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `GET /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `POST /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/pago-externo`
- `PATCH /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/anular`

Estructura persistida:

- cabecera `liquidacion_impuesto_trasladado`;
- snapshot de comprobante en
  `liquidacion_impuesto_trasladado_comprobante`;
- vinculo a egresos de empresa en
  `liquidacion_impuesto_trasladado_egreso` para
  `EMPRESA_PAGA_Y_RECUPERA`;
- snapshot de responsables en
  `liquidacion_impuesto_trasladado_responsable`;
- `relacion_generadora.tipo_origen = liquidacion_impuesto_trasladado`;
- `obligacion_financiera` `EMITIDA`;
- `composicion_obligacion` con `IMPUESTO_TRASLADADO`;
- `obligacion_obligado` con rol
  `RESPONSABLE_IMPUESTO_TRASLADADO`.

Reglas implementadas:

- requiere `comprobante_impuesto` existente y `REGISTRADO`;
- bloquea `EMPRESA_ASUME`;
- `DIRECTO_RESPONSABLE` liquida sin egreso de empresa;
- `EMPRESA_PAGA_Y_RECUPERA` requiere egreso registrado disponible y bloquea
  reutilizacion de egresos con vinculo activo;
- `importe_total_trasladar` debe ser mayor que cero y no superar la base de la
  modalidad;
- responsables obligatorios, con porcentajes mayores que cero y suma 100;
- calcula importes por responsable a dos decimales, asignando residuo al ultimo
  responsable;
- aplica idempotencia por `X-Op-Id`;
- no crea `movimiento_tesoreria`;
- no crea `PAGO_EXTERNO_INFORMADO`;
- no toca `comprobante_impuesto` ni `egreso_impuesto_empresa`.

Consultas read-only implementadas:

- detalle por id, con comprobantes, egresos si corresponden, responsables,
  relacion generadora, obligacion, composiciones y obligados;
- listado por `comprobante_impuesto`, incluyendo liquidaciones no eliminadas
  aunque esten anuladas;
- para `DIRECTO_RESPONSABLE`, el detalle devuelve lista de egresos vacia;
- no crean movimientos, obligaciones ni modifican saldos.

Anulacion conservadora implementada:

- requiere motivo;
- si la liquidacion no existe, devuelve
  `LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND`;
- si ya esta `ANULADA`, devuelve respuesta idempotente `YA_ANULADA`;
- si hay aplicaciones financieras, movimientos financieros activos,
  punitorios o composiciones posteriores, bloquea con
  `LIQUIDACION_IMPUESTO_TRASLADADO_TIENE_OPERACIONES`;
- si procede, marca `liquidacion_impuesto_trasladado.estado_liquidacion =
  ANULADA`;
- marca la `relacion_generadora` asociada como `CANCELADA`;
- marca la `obligacion_financiera` y sus composiciones como `ANULADA`;
- para `EMPRESA_PAGA_Y_RECUPERA`, libera logicamente los vinculos
  `liquidacion_impuesto_trasladado_egreso` activos, sin tocar
  `egreso_impuesto_empresa` ni `movimiento_tesoreria`;
- no borra registros fisicamente;
- no modifica pagos, comprobantes existentes ni egresos de empresa.

### Pago externo informado DIRECTO_RESPONSABLE

Endpoint implementado:

- `POST /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}/pago-externo`

Reglas:

- aplica solo a liquidaciones `EMITIDA` con modalidad `DIRECTO_RESPONSABLE`;
- bloquea liquidaciones `ANULADA`, `EMPRESA_ASUME` y
  `EMPRESA_PAGA_Y_RECUPERA`;
- requiere relacion generadora, obligacion activa y composicion activa
  `IMPUESTO_TRASLADADO` con saldo;
- si hay un responsable unico, `id_persona` puede omitirse y se resuelve desde
  la liquidacion;
- si hay multiples responsables, `id_persona` es obligatorio;
- no permite informar mas que el saldo imputable a la responsabilidad de la
  persona;
- crea `movimiento_financiero.tipo_movimiento = PAGO_EXTERNO_INFORMADO`;
- crea `aplicacion_financiera.tipo_aplicacion = PAGO_EXTERNO_INFORMADO`;
- reduce saldos mediante los triggers de composicion/aplicacion financiera;
- no crea `movimiento_tesoreria`, caja, egreso de impuesto, codigo de grupo de
  pago ni recibo interno;
- usa idempotencia por `X-Op-Id`: mismo payload devuelve el resultado existente,
  payload distinto devuelve `IDEMPOTENCY_PAYLOAD_CONFLICT`.

Errores principales:

- `LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND`;
- `LIQUIDACION_IMPUESTO_TRASLADADO_ANULADA`;
- `PAGO_EXTERNO_IMPUESTO_NO_APLICA_MODALIDAD`;
- `OBLIGACION_IMPUESTO_TRASLADADO_NO_EXISTE`;
- `SIN_SALDO_APLICABLE`;
- `RESPONSABLE_IMPUESTO_NO_VALIDO`;
- `PAGO_EXTERNO_IMPUESTO_SUPERA_RESPONSABILIDAD`;
- `IDEMPOTENCY_PAYLOAD_CONFLICT`.

## Estado de cuenta

Las obligaciones activas con composicion `IMPUESTO_TRASLADADO` deben verse en
grupo `TRASLADADOS`, separadas por su relacion generadora.

Las modalidades sin deuda al responsable, como `EMPRESA_ASUME`, no deben
aparecer en estado de cuenta del responsable.

## Fuera de alcance V1

- usar `factura_servicio` para impuestos;
- expensas formales;
- crear `IMPUESTO_RECUPERADO`;
- maestro catastral completo;
- integracion automatica con organismos;
- liquidacion automatica desde contrato locativo;
- prorrateos complejos por cambios de responsable;
- reversion historica con recomputacion.

## Referencias

- [[MODELO-FINANCIERO-FIN]]
- [[catalogos/RN-FIN]]
- [[catalogos/TIPO-OBLIGACION-FIN]]
- [[SRV-FIN-020-recupero-servicios-comunes]]
