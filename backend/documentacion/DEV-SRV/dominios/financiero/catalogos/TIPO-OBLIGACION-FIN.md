# TIPO-OBLIGACION-FIN - Compatibilidad documental

## Estado del documento

- estado: `REEMPLAZADO CONCEPTUALMENTE POR MODELO-FINANCIERO-FIN`
- dominio: `financiero`
- clasificacion: compatibilidad documental
- NO ES CATALOGO OPERATIVO
- NO DEBE USARSE PARA LOGICA DE NEGOCIO
- NO DEBE USARSE COMO FK CENTRAL
- NO DEBE USARSE PARA DECIDIR CALCULOS, IMPUTACION, MORA, CANCELACION NI REPORTES NORMATIVOS
- no es catalogo SQL
- no define columna `tipo_obligacion`
- no crea endpoints
- no modifica DER
- no modifica SQL

Este documento se conserva para dejar trazabilidad de la decision: la obligacion financiera no debe tipificarse rigidamente como venta, alquiler, servicio, expensa u otra categoria de negocio.

Uso permitido:

- glosario legacy
- puente conceptual para usuarios
- compatibilidad documental
- ayuda para migraciones
- mapeo hacia origen financiero y conceptos financieros

La definicion normativa vigente para el modelo es:

- `backend/documentacion/DEV-SRV/dominios/financiero/MODELO-FINANCIERO-FIN.md`
- `backend/documentacion/DER/DER-FINANCIERO.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/RN-FIN.md`

---

## 1. Decision conceptual

No existe catalogo normativo de tipos de `obligacion_financiera`.

El modelo financiero se interpreta asi:

```text
relacion_generadora
    1 --- N obligacion_financiera

obligacion_financiera
    1 --- N composicion_obligacion

concepto_financiero
    1 --- N composicion_obligacion
```

Reglas:

- el origen se interpreta desde `relacion_generadora`;
- la naturaleza economica se interpreta desde `composicion_obligacion` + `concepto_financiero`;
- `obligacion_financiera` conserva deuda, saldo y estado;
- la obligacion no debe codificar rigidamente `tipo_obligacion` como logica central;
- un pago no cancela directamente una obligacion: la cancelacion pasa por `aplicacion_financiera` / imputacion.

---

## 2. Mapeo de compatibilidad

Los codigos documentales previos deben leerse como agrupadores o ejemplos de composicion, no como tipos persistibles de obligacion.

Cada "tipo" legacy debe mapearse hacia:

- `relacion_generadora.origen` / entidad generadora
- uno o mas `concepto_financiero`
- una composicion economica concreta

| Tipo legacy | Origen / entidad generadora | Conceptos financieros | Composicion economica |
|---|---|---|---|
| cuota de venta | `VENTA` | `CAPITAL_VENTA`; `INTERES_FINANCIERO` si corresponde | Capital y/o interes ordinario de una obligacion originada por venta. |
| anticipo | `VENTA` | `ANTICIPO_VENTA` | Anticipo exigible de venta. |
| alquiler mensual | `CONTRATO_ALQUILER` | `CANON_LOCATIVO` | Canon locativo del periodo. |
| servicio trasladado | `SERVICIO` / `CONTRATO_ALQUILER` segun contrato futuro | `SERVICIO_TRASLADADO` | Servicio trasladado al obligado financiero. |
| expensa trasladada | `CONTRATO_ALQUILER` | `EXPENSA_TRASLADADA` | Expensa trasladada al obligado financiero. |
| impuesto trasladado | `CONTRATO_ALQUILER` o `INMUEBLE` segun origen documentado futuro | `IMPUESTO_TRASLADADO` | Impuesto o tasa trasladada. |
| mora | Origen de la obligacion afectada | `PUNITORIO` en V1; `INTERES_MORA` solo compatibilidad heredada | Componentes de mora asociados a deuda vencida. |
| liquidacion final | Relacion generadora cerrada o en cierre | `LIQUIDACION_FINAL` y conceptos complementarios | Cierre economico de la relacion. |
| refinanciacion | Refinanciacion o proceso financiero formal | `REFINANCIACION` y conceptos resultantes | Nueva composicion derivada de deuda refinanciada. |
| cancelacion anticipada | Cancelacion anticipada o proceso formal equivalente | `CANCELACION_ANTICIPADA` y conceptos resultantes | Cargo, saldo o ajuste por cancelacion antes del vencimiento natural. |

---

## 3. Catalogo conceptual vigente de conceptos

El catalogo conceptual base de `concepto_financiero` queda definido en `MODELO-FINANCIERO-FIN`:

- `CAPITAL_VENTA`
- `ANTICIPO_VENTA`
- `SALDO_EXTRAORDINARIO`
- `CANON_LOCATIVO`
- `EXPENSA_TRASLADADA`
- `SERVICIO_TRASLADADO`
- `IMPUESTO_TRASLADADO`
- `INTERES_FINANCIERO`
- `PUNITORIO`
- `INTERES_MORA` (compatibilidad heredada; no se usa como concepto activo de mora persistida en V1)
- `CARGO_ADMINISTRATIVO`
- `LIQUIDACION_FINAL`
- `REFINANCIACION`
- `CANCELACION_ANTICIPADA`
- `AJUSTE_INDEXACION`
- `CREDITO_MANUAL`
- `DEBITO_MANUAL`

Estado:

- `DEFINIDO CONCEPTUALMENTE`
- `NO IMPLEMENTADO COMO SEED SQL CONFIRMADO`
- `NO IMPLEMENTADO COMO CATALOGO DE TIPOS DE OBLIGACION`

---

## 4. Restricciones

- No usar este archivo para crear columna `tipo_obligacion`.
- No usar estos codigos como estado ni tipo persistido de `obligacion_financiera`.
- No usar estos codigos para decidir calculos, imputacion, mora, cancelacion ni reportes normativos.
- No usar estos codigos como FK central ni como discriminador principal de comportamiento.
- No inferir endpoints desde este documento.
- No habilitar `SERVICIO_TRASLADADO` hasta que existan contrato, API/backend, evento y consumer financiero.
- Toda implementacion futura debe apoyarse en `concepto_financiero` y `composicion_obligacion`.
