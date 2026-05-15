# DISENO-ENDPOINT-PLAN-PAGO-V2-GENERAR - Endpoint unificado por bloques

## Estado

Documento de diseno futuro. No implementado.

Este documento no modifica SQL, backend productivo, UI, pagos, caja, recibos ni
endpoints publicos vigentes.

Endpoint futuro:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar
```

## Objetivo

Recibir una forma de pago de venta expresada como bloques comerciales y
materializarla como cronograma financiero V2.

El endpoint debe operar sobre:

- `plan_pago_venta` como cabecera/regla comercial
- `plan_pago_venta_bloque` como estructura comercial del acuerdo
- `obligacion_financiera` como cronograma financiero proyectado
- `composicion_obligacion` como desglose economico
- `obligacion_obligado` como responsable financiero
- `id_plan_pago_venta_bloque` como trazabilidad bloque -> obligacion
- `clave_funcional_origen` como idempotencia financiera

Clasificacion:

- `plan_pago_venta`: nucleo comercial
- `plan_pago_venta_bloque`: nucleo comercial
- `obligacion_financiera`: nucleo financiero
- `composicion_obligacion`: soporte financiero
- `obligacion_obligado`: soporte financiero
- `venta_plan_cuota`: compatibilidad heredada V1

## Contrato de request

Request base:

```json
{
  "tipo_pago": "FINANCIADO",
  "monto_total_plan": 12700000.00,
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "ANTICIPO",
      "importe_total_bloque": 2000000.00,
      "fecha_vencimiento": "2026-05-10"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "cantidad_cuotas": 6,
      "importe_cuota": 500000.00,
      "fecha_primer_vencimiento": "2026-06-10",
      "periodicidad": "MENSUAL"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "cantidad_cuotas": 6,
      "importe_cuota": 700000.00,
      "fecha_primer_vencimiento": "2026-12-10",
      "periodicidad": "MENSUAL"
    },
    {
      "tipo_bloque": "REFUERZO",
      "etiqueta_bloque": "Refuerzo diciembre",
      "importe_total_bloque": 1500000.00,
      "fecha_vencimiento": "2026-12-20"
    },
    {
      "tipo_bloque": "SALDO",
      "etiqueta_bloque": "Saldo contra escritura",
      "importe_total_bloque": 2000000.00,
      "fecha_vencimiento": "2027-03-10"
    }
  ]
}
```

Campos de cabecera:

| Campo | Tipo | Requerido | Regla |
| --- | --- | --- | --- |
| `tipo_pago` | enum | si | `CONTADO` o `FINANCIADO` |
| `monto_total_plan` | decimal(14,2) | si | mayor que cero |
| `moneda` | string | si | codigo normalizado, inicialmente `ARS` |
| `bloques` | array | si | no vacio |
| `observaciones` | string | no | texto libre de cabecera |

Campos comunes de bloque:

| Campo | Tipo | Requerido | Regla |
| --- | --- | --- | --- |
| `tipo_bloque` | enum | si | `CONTADO`, `ANTICIPO`, `TRAMO_CUOTAS`, `REFUERZO`, `SALDO` |
| `etiqueta_bloque` | string | no | si falta, el backend asigna una etiqueta por defecto |
| `importe_total_bloque` | decimal(14,2) | segun tipo | importe comercial del bloque |
| `fecha_vencimiento` | date | segun tipo | requerida para pago unico |
| `cantidad_cuotas` | integer | segun tipo | requerida para `TRAMO_CUOTAS` |
| `importe_cuota` | decimal(14,2) | segun tipo | requerida para `TRAMO_CUOTAS` inicial |
| `fecha_primer_vencimiento` | date | segun tipo | requerida para `TRAMO_CUOTAS` |
| `periodicidad` | enum | segun tipo | inicialmente solo `MENSUAL` |
| `regla_redondeo` | enum | no | default `ULTIMA_CUOTA` para tramos |
| `observaciones` | string | no | texto libre del bloque |

El request no recibe `numero_bloque`, `clave_bloque`, `numero_obligacion`,
`clave_funcional_origen` ni ids tecnicos. El backend los asigna.

## tipo_pago

Debe existir `tipo_pago = CONTADO | FINANCIADO`.

Motivo:

- evita inferir contado solo por cantidad de bloques
- permite reglas de validacion simples y explicitas
- separa la forma comercial pactada del detalle tecnico de materializacion

Reglas:

- `CONTADO` solo admite un bloque `CONTADO`
- `FINANCIADO` admite `ANTICIPO`, `TRAMO_CUOTAS`, `REFUERZO` y `SALDO`
- `FINANCIADO` no admite bloque `CONTADO`

## Request contado

```json
{
  "tipo_pago": "CONTADO",
  "monto_total_plan": 12000000.00,
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "CONTADO",
      "importe_total_bloque": 12000000.00,
      "fecha_vencimiento": "2026-05-10"
    }
  ]
}
```

Para `CONTADO`, `importe_total_bloque` puede omitirse en una version futura si
se define que toma `monto_total_plan`. Para el primer endpoint unificado se
recomienda exigirlo para mantener una validacion homogenea de suma de bloques.

## Request financiado

El request financiado puede contener:

- anticipo opcional
- uno o mas tramos de cuotas
- refuerzos o cuotas especiales
- saldo final opcional

Ejemplo:

```json
{
  "tipo_pago": "FINANCIADO",
  "monto_total_plan": 12700000.00,
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "ANTICIPO",
      "importe_total_bloque": 2000000.00,
      "fecha_vencimiento": "2026-05-10"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "cantidad_cuotas": 6,
      "importe_cuota": 500000.00,
      "fecha_primer_vencimiento": "2026-06-10",
      "periodicidad": "MENSUAL"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "cantidad_cuotas": 6,
      "importe_cuota": 700000.00,
      "fecha_primer_vencimiento": "2026-12-10",
      "periodicidad": "MENSUAL"
    },
    {
      "tipo_bloque": "REFUERZO",
      "etiqueta_bloque": "Refuerzo diciembre",
      "importe_total_bloque": 1500000.00,
      "fecha_vencimiento": "2026-12-20"
    },
    {
      "tipo_bloque": "SALDO",
      "etiqueta_bloque": "Saldo contra escritura",
      "importe_total_bloque": 2000000.00,
      "fecha_vencimiento": "2027-03-10"
    }
  ]
}
```

## Validacion de suma

La suma de bloques debe coincidir exactamente con `monto_total_plan`.

Valor de cada bloque:

| Tipo bloque | Valor para suma |
| --- | --- |
| `CONTADO` | `importe_total_bloque` |
| `ANTICIPO` | `importe_total_bloque` |
| `TRAMO_CUOTAS` | `cantidad_cuotas * importe_cuota` |
| `REFUERZO` | `importe_total_bloque` |
| `SALDO` | `importe_total_bloque` |

Reglas:

- todos los importes se validan con precision de centavos
- no se aceptan importes negativos ni cero
- no se acepta diferencia por redondeo en el primer alcance
- `regla_redondeo = ULTIMA_CUOTA` queda reservada para tramos que en el futuro
  permitan `importe_total_bloque` distribuido; con `importe_cuota` explicito la
  suma es aritmetica directa

Error recomendado:

```text
SUMA_BLOQUES_INVALIDA
```

## Numeracion de bloques

`numero_bloque` se asigna por orden del array recibido, comenzando en 1.

Reglas:

- el request no debe enviar `numero_bloque`
- el backend persiste `numero_bloque = indice + 1`
- el orden del array es parte del contrato funcional
- la idempotencia de bloque usa `id_plan_pago_venta + clave_bloque`

## Numeracion de obligaciones

`numero_obligacion` se asigna sobre la secuencia cronologica funcional de
materializacion, siguiendo el orden de bloques y el orden interno de cada
bloque.

Reglas:

- la primera obligacion generada tiene `numero_obligacion = 1`
- bloques de pago unico generan una obligacion
- `TRAMO_CUOTAS` genera una obligacion por cuota, en orden de vencimiento
- la numeracion no se reinicia por bloque

Ejemplo:

| Bloque | Obligaciones | Numeros |
| --- | --- | --- |
| `ANTICIPO` | 1 | 1 |
| `TRAMO_CUOTAS` de 6 cuotas | 6 | 2 a 7 |
| `TRAMO_CUOTAS` de 6 cuotas | 6 | 8 a 13 |
| `REFUERZO` | 1 | 14 |
| `SALDO` | 1 | 15 |

## clave_bloque

Convencion:

```text
PLAN_PAGO_VENTA:{id_plan_pago_venta}:BLOQUE:{tipo_bloque}:{ordinal_tipo}
```

Ejemplos:

```text
PLAN_PAGO_VENTA:20:BLOQUE:ANTICIPO:1
PLAN_PAGO_VENTA:20:BLOQUE:TRAMO_CUOTAS:1
PLAN_PAGO_VENTA:20:BLOQUE:TRAMO_CUOTAS:2
PLAN_PAGO_VENTA:20:BLOQUE:REFUERZO:1
PLAN_PAGO_VENTA:20:BLOQUE:SALDO:1
```

`ordinal_tipo` cuenta ocurrencias del mismo `tipo_bloque` dentro del plan.

Motivo:

- estable para idempotencia por `id_plan_pago_venta + clave_bloque`
- no depende de ids tecnicos de bloque
- permite mas de un tramo de cuotas o mas de un refuerzo
- evita usar texto libre o fechas como parte de la clave

Nota de compatibilidad:

- los endpoints especificos actuales ya usan `TRAMO_CUOTAS:1`
- el endpoint unificado debe conservar esa convencion

## clave_funcional_origen

Convencion futura para obligaciones del endpoint unificado:

```text
PLAN_PAGO_VENTA:{id_plan_pago_venta}:BLOQUE:{numero_bloque}:{tipo_item_cronograma}:{n}
```

Ejemplos:

```text
PLAN_PAGO_VENTA:20:BLOQUE:1:ANTICIPO:1
PLAN_PAGO_VENTA:20:BLOQUE:2:CUOTA:1
PLAN_PAGO_VENTA:20:BLOQUE:2:CUOTA:6
PLAN_PAGO_VENTA:20:BLOQUE:3:CUOTA:1
PLAN_PAGO_VENTA:20:BLOQUE:4:REFUERZO:1
PLAN_PAGO_VENTA:20:BLOQUE:5:SALDO:1
```

Reglas:

- la clave pertenece a `obligacion_financiera`
- no se reemplaza por `id_plan_pago_venta_bloque`
- `id_plan_pago_venta_bloque` es trazabilidad
- la idempotencia financiera sigue siendo
  `(id_relacion_generadora, clave_funcional_origen)` sobre obligaciones activas
- no debe depender de importe, fecha, etiqueta ni ids de obligacion

## Mapeo bloque -> item cronograma

| `tipo_bloque` | `tipo_item_cronograma` | Observacion |
| --- | --- | --- |
| `CONTADO` | `SALDO` | mientras SQL no soporte `CONTADO` como item |
| `ANTICIPO` | `ANTICIPO` | pago inicial |
| `TRAMO_CUOTAS` | `CUOTA` | una obligacion por cuota |
| `REFUERZO` | `REFUERZO` | pago especial |
| `SALDO` | `SALDO` | saldo final |

## Mapeo bloque -> composicion

| `tipo_bloque` | Concepto financiero |
| --- | --- |
| `CONTADO` | `CAPITAL_VENTA` |
| `ANTICIPO` | `ANTICIPO_VENTA` |
| `TRAMO_CUOTAS` | `CAPITAL_VENTA` |
| `REFUERZO` | `CAPITAL_VENTA` inicialmente |
| `SALDO` | `CAPITAL_VENTA` |

No crear conceptos nuevos para este primer endpoint unificado.

## CONTADO y tipo_item_cronograma SALDO

`CONTADO` es una forma comercial de pago. El catalogo vigente de
`tipo_item_cronograma` no necesita incorporar `CONTADO` para el primer alcance.

Decision:

- persistir el bloque comercial como `tipo_bloque = CONTADO`
- materializar una unica obligacion con `tipo_item_cronograma = SALDO`
- usar composicion `CAPITAL_VENTA`
- mantener `etiqueta_obligacion = Contado` o `Saldo contado`

Motivo:

- no modificar SQL
- no ampliar catalogos financieros
- evitar duplicar semantica entre forma comercial e item exigible

## Reglas por bloque

### CONTADO

- solo valido con `tipo_pago = CONTADO`
- debe ser el unico bloque
- `importe_total_bloque > 0`
- `importe_total_bloque = monto_total_plan`
- `fecha_vencimiento` obligatoria
- genera una obligacion `tipo_item_cronograma = SALDO`
- composicion `CAPITAL_VENTA`

### ANTICIPO

- solo valido con `tipo_pago = FINANCIADO`
- `importe_total_bloque > 0`
- `fecha_vencimiento` obligatoria
- genera una obligacion `tipo_item_cronograma = ANTICIPO`
- composicion `ANTICIPO_VENTA`

### TRAMO_CUOTAS

- valido con `tipo_pago = FINANCIADO`
- `cantidad_cuotas > 0`
- `importe_cuota > 0`
- `fecha_primer_vencimiento` obligatoria
- `periodicidad = MENSUAL` inicialmente
- `regla_redondeo = ULTIMA_CUOTA` si se informa; default recomendado
- genera N obligaciones `tipo_item_cronograma = CUOTA`
- composicion `CAPITAL_VENTA`

### REFUERZO

- valido con `tipo_pago = FINANCIADO`
- `importe_total_bloque > 0`
- `fecha_vencimiento` obligatoria
- genera una obligacion `tipo_item_cronograma = REFUERZO`
- composicion inicial `CAPITAL_VENTA` salvo decision distinta futura

### SALDO

- valido con `tipo_pago = FINANCIADO`
- `importe_total_bloque > 0`
- `fecha_vencimiento` obligatoria
- genera una obligacion `tipo_item_cronograma = SALDO`
- composicion `CAPITAL_VENTA`

## Validaciones generales

- `id_venta` positivo
- venta existente y no dada de baja
- `monto_total_plan > 0`
- `moneda` obligatoria
- `bloques` no vacio
- `tipo_pago` obligatorio
- `tipo_pago = CONTADO` exige un unico bloque `CONTADO`
- `tipo_pago = FINANCIADO` no permite bloque `CONTADO`
- `tipo_pago = FINANCIADO` exige al menos un bloque financiado valido
- no permitir bloque `CONTADO` junto con otros bloques
- suma de bloques igual a `monto_total_plan`
- cada `TRAMO_CUOTAS` suma `cantidad_cuotas * importe_cuota`
- fechas obligatorias segun tipo
- comprador financiero unico resoluble
- conceptos financieros requeridos existentes y activos
- si existe plan vivo, debe ser compatible con el request
- no usar `venta_plan_cuota`
- no crear `plan_pago_venta_cuota`
- no crear `plan_pago_venta_tramo`

## Persistencia esperada

El flujo transaccional futuro debe:

1. validar request y venta
2. resolver comprador unico
3. crear o reutilizar `plan_pago_venta`
4. crear o reutilizar `plan_pago_venta_bloque` por bloque
5. asegurar `relacion_generadora` de la venta
6. crear o reutilizar `generacion_cronograma_financiero`
7. expandir bloques a obligaciones
8. persistir `id_plan_pago_venta_bloque` en cada obligacion
9. crear `composicion_obligacion`
10. crear `obligacion_obligado`
11. devolver cabecera, bloques, generacion y obligaciones

## Response esperada

```json
{
  "ok": true,
  "data": {
    "id_venta": 1,
    "id_relacion_generadora": 10,
    "plan_pago_venta": {
      "id_plan_pago_venta": 20,
      "id_venta": 1,
      "metodo_plan_pago": "BLOQUES",
      "estado_plan_pago": "GENERADO",
      "tipo_pago": "FINANCIADO",
      "moneda": "ARS",
      "monto_total_plan": 12700000.00
    },
    "bloques": [
      {
        "id_plan_pago_venta_bloque": 100,
        "id_plan_pago_venta": 20,
        "numero_bloque": 1,
        "tipo_bloque": "ANTICIPO",
        "etiqueta_bloque": "Anticipo",
        "clave_bloque": "PLAN_PAGO_VENTA:20:BLOQUE:ANTICIPO:1",
        "importe_total_bloque": 2000000.00,
        "fecha_vencimiento": "2026-05-10",
        "concepto_financiero_codigo": "ANTICIPO_VENTA"
      }
    ],
    "generacion_cronograma_financiero": {
      "id_generacion_cronograma_financiero": 30,
      "id_relacion_generadora": 10,
      "id_plan_pago_venta": 20,
      "tipo_generacion": "PLAN_PAGO_VENTA_V2",
      "clave_generacion": "PLAN_PAGO_VENTA:20:BLOQUES",
      "estado_generacion": "GENERADA"
    },
    "obligaciones": [
      {
        "id_obligacion_financiera": 200,
        "id_relacion_generadora": 10,
        "id_generacion_cronograma_financiero": 30,
        "id_plan_pago_venta_bloque": 100,
        "numero_obligacion": 1,
        "tipo_item_cronograma": "ANTICIPO",
        "etiqueta_obligacion": "Anticipo",
        "clave_funcional_origen": "PLAN_PAGO_VENTA:20:BLOQUE:1:ANTICIPO:1",
        "fecha_vencimiento": "2026-05-10",
        "importe_total": 2000000.00,
        "saldo_pendiente": 2000000.00,
        "moneda": "ARS",
        "estado_obligacion": "PROYECTADA"
      }
    ]
  }
}
```

Nota: `tipo_pago` hoy no existe confirmado como columna en `plan_pago_venta`.
Si no se agrega SQL, el response puede derivarlo del metodo o devolverlo solo
como dato calculado del servicio. La implementacion futura debe confirmar esta
decision contra SQL vigente.

## Errores esperados

| Situacion | Error recomendado |
| --- | --- |
| Venta inexistente | `NOT_FOUND_VENTA` |
| Plan vivo incompatible | `PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE` |
| Suma de bloques invalida | `SUMA_BLOQUES_INVALIDA` |
| Bloque invalido | `BLOQUE_INVALIDO` |
| Contado con multiples bloques | `CONTADO_BLOQUES_INVALIDOS` |
| Financiado con bloque contado | `FINANCIADO_NO_PERMITE_CONTADO` |
| Comprador no resoluble | `COMPRADOR_VENTA_NO_RESUELTO` |
| Comprador multiple | `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` |
| Concepto financiero faltante | `NOT_FOUND_CONCEPTO:{codigo}` |
| Conflicto de idempotencia | `IDEMPOTENCY_CONFLICT` |
| Schema invalido | `422` |

## Convivencia con endpoints especificos actuales

Endpoints vigentes:

- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales`

Decision:

- quedan como compatibilidad inicial
- no se eliminan
- no cambian su contrato publico
- no deben crecer para soportar combinaciones nuevas
- a futuro pueden convertirse en wrappers del endpoint unificado

Traduccion futura:

| Endpoint especifico | Traduccion a bloques |
| --- | --- |
| `cuotas-iguales-simple` | un bloque `TRAMO_CUOTAS` |
| `anticipo-mas-cuotas-iguales` | bloque `ANTICIPO` + bloque `TRAMO_CUOTAS` |

## Tests necesarios

Tests de contrato:

- request contado valido
- request financiado con un tramo de cuotas
- request financiado con anticipo y tramo
- request financiado con dos tramos
- request financiado con refuerzo
- request financiado con saldo final
- response incluye `id_venta`, `id_relacion_generadora`, `plan_pago_venta`,
  `bloques`, `generacion_cronograma_financiero` y `obligaciones`

Tests de bloques:

- `numero_bloque` se asigna por orden del array
- `clave_bloque` usa ordinal por tipo
- reejecutar mismo payload no duplica bloques
- cada bloque tiene campos requeridos segun tipo

Tests de obligaciones:

- `numero_obligacion` es secuencial global
- `clave_funcional_origen` es estable
- cada obligacion apunta a `id_plan_pago_venta_bloque`
- reejecutar mismo payload no duplica obligaciones
- `CONTADO` genera `tipo_item_cronograma = SALDO`
- `ANTICIPO` genera composicion `ANTICIPO_VENTA`
- cuotas, refuerzos y saldo generan composicion `CAPITAL_VENTA`

Tests de validacion:

- suma de bloques invalida
- `CONTADO` con multiples bloques
- `FINANCIADO` con bloque `CONTADO`
- bloque sin fecha requerida
- tramo sin cantidad, importe o primer vencimiento
- periodicidad distinta de `MENSUAL`
- comprador inexistente o multiple
- concepto financiero faltante
- plan vivo incompatible

Tests de compatibilidad:

- no se crean filas en `venta_plan_cuota` para V2 unificado
- no se crean `plan_pago_venta_cuota` ni `plan_pago_venta_tramo`
- endpoints especificos actuales siguen pasando
- `CUOTAS_FIJAS V1` sigue usando `venta_plan_cuota`
- tests de schema de cronograma V2 siguen pasando

## Fuera del primer endpoint unificado

No implementar en el primer alcance:

- SQL nuevo
- cambios de UI
- pagos
- caja
- recibos
- movimientos de tesoreria
- imputaciones
- mora
- punitorios
- indexacion
- interes
- sistema frances
- sistema aleman
- refinanciacion
- cancelacion anticipada
- regeneracion con obligaciones pagadas
- multiples compradores o prorrateo de obligados
- endpoint de previsualizacion
- migracion de `venta_plan_cuota`

## Decisiones cerradas para implementacion futura

- El endpoint recibe bloques, no metodos tecnicos aislados.
- `tipo_pago` debe existir en el request.
- `numero_bloque` lo asigna backend por orden del array.
- `clave_bloque` se genera por plan, tipo de bloque y ordinal por tipo.
- `numero_obligacion` es secuencial global del cronograma.
- `clave_funcional_origen` sigue siendo la idempotencia financiera.
- `id_plan_pago_venta_bloque` es trazabilidad, no idempotencia.
- `CONTADO` se materializa como item `SALDO` mientras SQL no soporte item
  `CONTADO`.
- V2 unificado no usa `venta_plan_cuota`.
- Los endpoints especificos se conservan como compatibilidad.

## Proximo prompt recomendado

Implementar `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar` segun
`backend/documentacion/DEV-SRV/dominios/comercial/DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`,
sin modificar SQL ni UI, reutilizando `plan_pago_venta`,
`plan_pago_venta_bloque` y `obligacion_financiera.id_plan_pago_venta_bloque`,
manteniendo los endpoints especificos actuales como compatibilidad y agregando
tests de contrato, idempotencia, trazabilidad y no uso de `venta_plan_cuota`.
