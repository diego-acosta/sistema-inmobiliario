# SRV-FIN-021 - Impuestos trasladados

## Estado
- estado: `IMPLEMENTADO PARCIAL V1`
- implementacion: registro y consulta de `comprobante_impuesto` implementados; egreso empresa implementado para `EMPRESA_ASUME` y `EMPRESA_PAGA_Y_RECUPERA`; liquidacion `IMPUESTO_TRASLADADO` fase 1 implementada con consultas read-only; anulacion de liquidacion y pago externo aun no implementados
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

- fase 1 materializa una obligacion `IMPUESTO_TRASLADADO` desde
  `liquidacion_impuesto_trasladado`;
- no requiere `egreso_impuesto_empresa`;
- la base de liquidacion es `comprobante_impuesto.importe_total`;
- los responsables son explicitos, con porcentajes positivos que suman 100%;
- el pago informado externo queda pendiente;
- cuando se implemente, el pago externo no debe crear caja, tesoreria ni recibo
  interno;
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
- la anulacion futura debe ser conservadora y bloquearse si existen pagos,
  aplicaciones, punitorios u operaciones posteriores.

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
- pendiente futuro: bloquear anulacion si una
  `liquidacion_impuesto_trasladado` activa usa el egreso.

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

Entidad sugerida: `liquidacion_impuesto_trasladado`.

### Liquidacion implementada fase 1

`liquidacion_impuesto_trasladado` materializa deuda fiscal trasladada sin
reutilizar `liquidacion_recupero`.

Endpoint implementado:

- `POST /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`
- `GET /api/v1/financiero/liquidaciones-impuesto-trasladado/{id_liquidacion_impuesto_trasladado}`
- `GET /api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado`

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
  aunque en el futuro esten anuladas;
- para `DIRECTO_RESPONSABLE`, el detalle devuelve lista de egresos vacia;
- no crean movimientos, obligaciones ni modifican saldos.

## Estado de cuenta

Las obligaciones activas con composicion `IMPUESTO_TRASLADADO` deben verse en
grupo `TRASLADADOS`, separadas por su relacion generadora.

Las modalidades sin deuda al responsable, como `EMPRESA_ASUME`, no deben
aparecer en estado de cuenta del responsable.

## Fuera de alcance V1

- usar `factura_servicio` para impuestos;
- anulacion/reversion de `liquidacion_impuesto_trasladado`, pendiente posterior;
- pago externo informado de impuesto, pendiente posterior;
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
