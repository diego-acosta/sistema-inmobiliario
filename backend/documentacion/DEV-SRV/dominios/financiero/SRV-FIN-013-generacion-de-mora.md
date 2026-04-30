# SRV-FIN-013 - Generacion de mora diaria

## Objetivo

Generar obligaciones financieras de mora diaria para obligaciones vencidas con saldo pendiente, sin modificar la obligacion base.

## Estado

- estado: `IMPLEMENTADO`
- endpoint: `POST /api/v1/financiero/mora/generar`
- no modifica SQL
- no usa `tipo_obligacion`

## Alcance

Este servicio cubre:

- seleccion de obligaciones vencidas con saldo
- calculo simple de mora diaria
- creacion de nueva `obligacion_financiera`
- creacion de `composicion_obligacion` con concepto `INTERES_MORA`
- control operativo de duplicado por obligacion base y fecha de proceso

No cubre:

- punitorios
- capitalizacion de mora
- actualizacion de la obligacion base
- politicas variables de tasa
- refinanciacion
- reversion de mora

## Endpoint

`POST /api/v1/financiero/mora/generar`

Request:

```json
{
  "fecha_proceso": "2026-05-01"
}
```

Si `fecha_proceso` no viene, el backend usa la fecha actual.

Response:

```json
{
  "ok": true,
  "data": {
    "fecha_proceso": "2026-05-01",
    "procesadas": 10,
    "generadas": 7
  }
}
```

## Reglas de negocio

Una obligacion es elegible si cumple:

- `fecha_vencimiento < fecha_proceso`
- `saldo_pendiente > 0`
- `deleted_at IS NULL`
- `estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA', 'CANCELADA')`
- no es una obligacion generada por mora automatica

Reglas de calculo:

- concepto financiero obligatorio: `INTERES_MORA`
- tasa diaria fija inicial: `0.001`
- `importe_mora = saldo_pendiente * 0.001`
- redondeo a 2 decimales
- no se genera mora si `importe_mora <= 0`

Reglas de persistencia:

- se crea una nueva `obligacion_financiera`
- se usa la misma `id_relacion_generadora` de la obligacion base
- `fecha_emision = fecha_proceso`
- `fecha_vencimiento = fecha_proceso`
- `importe_total = importe_mora`
- `saldo_pendiente = importe_mora`
- `estado_obligacion = EXIGIBLE`
- se crea una unica composicion con `INTERES_MORA`

Reglas de no capitalizacion:

- la mora no incrementa el saldo de la obligacion base
- la mora queda como obligacion separada
- la consulta de deuda consolidada la muestra como otra obligacion de la misma relacion generadora

## Algoritmo implementado

1. resolver `fecha_proceso`
2. buscar `concepto_financiero` con codigo `INTERES_MORA`
3. seleccionar obligaciones elegibles con bloqueo `FOR UPDATE`
4. excluir obligaciones de mora automatica
5. verificar duplicado para obligacion base y fecha
6. calcular `saldo_pendiente * 0.001`
7. redondear a 2 decimales
8. omitir importes no positivos
9. crear obligacion de mora
10. crear composicion `INTERES_MORA`
11. confirmar transaccion

## Control de duplicado

Limitacion SQL actual:

- no existe FK desde obligacion de mora hacia obligacion base
- no existe columna `id_obligacion_base`
- no existe constraint unica para obligacion base + fecha de proceso

Control implementado:

- la obligacion de mora guarda en `observaciones` una marca:

```text
MORA_AUTO id_obligacion_base=<id> fecha_proceso=<yyyy-mm-dd> tasa_diaria=0.001
```

- el repositorio busca esa marca junto con una composicion `INTERES_MORA`
- el proceso no genera otra mora para la misma obligacion base y fecha si encuentra esa marca

Este control es operativo y compatible con el SQL vigente, pero no reemplaza una restriccion unica fisica.

## Ejemplo

Obligacion base:

```text
id_obligacion_financiera = 10
id_relacion_generadora = 1
fecha_vencimiento = 2026-04-01
saldo_pendiente = 1000.00
estado_obligacion = PROYECTADA
```

Proceso:

```json
{
  "fecha_proceso": "2026-05-01"
}
```

Resultado:

```text
importe_mora = 1000.00 * 0.001 = 1.00
```

Nueva obligacion:

```text
id_relacion_generadora = 1
fecha_emision = 2026-05-01
fecha_vencimiento = 2026-05-01
importe_total = 1.00
saldo_pendiente = 1.00
estado_obligacion = EXIGIBLE
composicion = INTERES_MORA
```

## Pendientes

- FK o referencia estructural a obligacion base
- restriccion unica fisica para no duplicar mora por dia
- politica configurable de tasa
- punitorios
- reversion/anulacion especifica de mora
