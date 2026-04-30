# EST-FIN - Estados del dominio Financiero

## Objetivo

Definir los estados financieros usados por el backend vigente y separar los estados conceptuales no implementados.

## Alcance

Incluye:

- `relacion_generadora`
- `obligacion_financiera`
- `aplicacion_financiera` como entidad SQL sin estado persistido propio
- estado de deuda como lectura derivada

---

## A. Estados de relacion_generadora

Estados SQL vigentes:

| Estado | Uso |
|---|---|
| `BORRADOR` | Estado inicial de las relaciones creadas por API. |
| `ACTIVA` | Estado soportado por SQL, sin transicion backend implementada. |
| `CANCELADA` | Estado soportado por SQL, sin transicion backend implementada. |
| `FINALIZADA` | Estado soportado por SQL, sin transicion backend implementada. |

Implementado:

- alta de relacion en `BORRADOR`
- lectura y listado

No implementado:

- activar
- cancelar
- finalizar

---

## B. Estados de obligacion_financiera

Estados SQL vigentes y usados por backend:

| Estado | Uso implementado |
|---|---|
| `PROYECTADA` | Estado inicial de obligaciones creadas manualmente por API. Acepta imputacion. |
| `EMITIDA` | Estado aceptado para imputacion. No existe transicion backend que lo asigne. |
| `EXIGIBLE` | Estado aceptado para imputacion. La mora automatica se crea en este estado. |
| `PARCIALMENTE_CANCELADA` | Asignado por backend despues de imputacion parcial. Acepta imputacion. |
| `CANCELADA` | Asignado por backend cuando el saldo queda en cero. No acepta imputacion. |
| `VENCIDA` | Estado aceptado para imputacion. No se materializa automaticamente por fecha en backend. |
| `ANULADA` | Estado excluido de imputacion y de generacion de mora. |
| `REEMPLAZADA` | Estado excluido de imputacion y de generacion de mora. |

Estados solicitados como base operativa principal:

- `PROYECTADA`
- `EMITIDA`
- `PARCIALMENTE_CANCELADA`
- `CANCELADA`
- `ANULADA`
- `REEMPLAZADA`

Ademas, el SQL y backend actual tambien reconocen:

- `EXIGIBLE`
- `VENCIDA`

No deben eliminarse de la documentacion porque existen en constraints SQL y son usados por servicios.

---

## C. Reglas de transicion implementadas

### Alta de obligacion

`POST /api/v1/financiero/obligaciones`:

```text
nueva obligacion -> PROYECTADA
```

### Imputacion

Luego de registrar `aplicacion_financiera`, la DB actualiza saldos por triggers y el backend actualiza estado segun saldo resultante:

```text
saldo_pendiente = 0
    -> CANCELADA

saldo_pendiente < importe_total
    -> PARCIALMENTE_CANCELADA
```

La actualizacion no modifica obligaciones en estado:

- `ANULADA`
- `REEMPLAZADA`

### Mora

`POST /api/v1/financiero/mora/generar` crea nuevas obligaciones de mora en estado:

```text
EXIGIBLE
```

La mora no cambia el estado de la obligacion base.

---

## D. Estados que aceptan imputacion

El backend acepta imputacion para:

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `VENCIDA`

El backend rechaza imputacion para:

- `CANCELADA`
- `ANULADA`
- `REEMPLAZADA`

---

## E. Estados excluidos de mora

La generacion automatica de mora excluye:

- `ANULADA`
- `REEMPLAZADA`
- `CANCELADA`

Tambien excluye obligaciones ya generadas por mora automatica, identificadas por marca en `observaciones`.

---

## F. Estado de aplicacion_financiera

SQL vigente no tiene columna `estado_aplicacion`.

La imputacion queda representada por:

- `movimiento_financiero`
- `aplicacion_financiera`
- saldo actualizado por triggers
- estado resultante de `obligacion_financiera`

Estados documentales como `REGISTRADA`, `APLICADA`, `ANULADA` o `REVERTIDA` quedan pendientes hasta que exista soporte fisico o endpoint de reversion.

---

## G. Estados de deuda

La consulta implementada `GET /api/v1/financiero/deuda` no persiste un estado agregado de deuda. Devuelve obligaciones y composiciones con:

- `estado_obligacion`
- `saldo_pendiente`
- `fecha_vencimiento`
- composiciones con `saldo_componente`

Estados agregados como `sin_deuda`, `con_deuda`, `deuda_parcial`, `deuda_vencida` o `deuda_cancelada` son conceptuales para reportes futuros; no son persistidos por el backend actual.

---

## H. Pendientes

- transiciones explicitas de `relacion_generadora`
- transiciones explicitas de obligacion fuera de imputacion y mora
- reversion de imputaciones
- estado persistido de `aplicacion_financiera`
- estado agregado persistido de deuda
