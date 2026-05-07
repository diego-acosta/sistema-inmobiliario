# SRV-FIN-021 - Impuestos trasladados

## Estado
- estado: `DISENO V1 DOCUMENTADO / NO IMPLEMENTADO`
- dominio owner: `financiero`
- origen operativo propuesto: `comprobante_impuesto`
- clasificacion: nucleo financiero para traslado de impuestos, tasas o contribuciones a responsables

## Objetivo

Documentar el diseno V1 corregido para impuestos, tasas o contribuciones
trasladadas, separado de los circuitos de servicios.

El flujo no usa `factura_servicio`, no usa `SERVICIO_TRASLADADO`, no usa
`SERVICIO_RECUPERADO` y no usa `EXPENSA_TRASLADADA`.

## Entidad origen

V1 debe crear entidad propia `comprobante_impuesto`.

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
- no aparece como deuda de responsable.

### DIRECTO_RESPONSABLE

El responsable debe pagar directamente al organismo.

Reglas:

- puede materializar una obligacion `IMPUESTO_TRASLADADO`;
- requiere unico responsable 100%;
- el pago informado es externo;
- el pago externo no crea caja, tesoreria ni recibo interno;
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
- el responsable paga a la empresa por el flujo normal de pago por persona;
- la liquidacion no crea `movimiento_tesoreria` nuevo;
- la anulacion futura debe ser conservadora y bloquearse si existen pagos,
  aplicaciones, punitorios u operaciones posteriores.

## Relacion con tesoreria

El pago real del impuesto por la empresa debe entrar por `movimiento_tesoreria`.

V1 debe separar:

- egreso por impuesto asumido por la empresa;
- egreso por impuesto que luego se recupera;
- pago externo informado por responsable, que no impacta tesoreria.

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
