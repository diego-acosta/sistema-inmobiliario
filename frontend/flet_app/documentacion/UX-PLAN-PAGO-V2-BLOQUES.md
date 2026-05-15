# UX-PLAN-PAGO-V2-BLOQUES - Carga y visualizacion de plan de pago V2 por bloques

## 1. Objetivo

Definir la experiencia de usuario para cargar, validar, generar y visualizar un
plan de pago de venta V2 por bloques antes de implementar frontend productivo.

Alcance:

- documentacion UX solamente
- no modifica backend
- no modifica SQL
- no toca pagos, caja ni recibos
- no implementa UI productiva

Endpoint objetivo:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar
```

Fuente de lectura posterior:

```text
GET /api/v1/ventas/{id_venta}/detalle-integral
```

Campo de lectura:

```text
plan_pago_v2
```

## 2. Principios UX

- La pantalla debe hablar en terminos comerciales: contado, anticipo, cuotas,
  refuerzos y saldo.
- No debe exponer claves tecnicas ni identificadores internos que asigna el
  backend.
- La validacion visual debe anticipar los errores de negocio antes de ejecutar
  la generacion.
- El preview debe mostrar el cronograma resultante de forma entendible, sin
  prometer pago, caja ni recibo.
- Una vez generado, el plan debe verse como estructura cerrada de consulta, no
  como formulario editable.

## 3. Flujo de Pantalla

1. El usuario ingresa al detalle de una venta.
2. Si no existe `plan_pago_v2`, se muestra un estado vacio con accion
   `Cargar forma de pago`.
3. Al abrir la carga, el usuario selecciona `CONTADO` o `FINANCIADO`.
4. El usuario completa bloques comerciales.
5. La pantalla valida suma, campos requeridos y reglas por tipo.
6. La pantalla muestra preview del cronograma.
7. El usuario confirma con `Generar plan de pago`.
8. Se ejecuta `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar`.
9. Si la respuesta es exitosa, el detalle se refresca y muestra
   `plan_pago_v2`.
10. Si hay error, se muestra mensaje contextual y se conserva el borrador visual.

## 4. Pantalla de Carga

### 4.1 Cabecera

Campos visibles:

- `Tipo de pago`: control segmentado `CONTADO` / `FINANCIADO`
- `Monto total del plan`
- `Moneda`
- resumen de suma:
  - total de bloques
  - diferencia contra monto total
  - cantidad estimada de obligaciones

Acciones:

- `Cancelar`
- `Generar plan de pago`

Estados del boton `Generar plan de pago`:

- deshabilitado si hay errores de validacion UX
- loading durante el POST
- habilitado si el borrador visual es valido

### 4.2 Modo CONTADO

Campos:

- importe total
- fecha de vencimiento
- etiqueta opcional

Regla de UX:

- se representa internamente como un unico bloque `CONTADO`
- no se permite agregar otros bloques
- el preview muestra una obligacion tipo `SALDO`, porque el backend materializa
  contado como item de cronograma `SALDO`

### 4.3 Modo FINANCIADO

Secciones sugeridas:

- Anticipo opcional
- Tramos de cuotas
- Refuerzos / cuotas especiales
- Saldo final opcional

Reglas:

- debe existir al menos un bloque financiado
- no se permite bloque `CONTADO`
- puede haber uno o mas `TRAMO_CUOTAS`
- puede haber cero o mas `REFUERZO`
- puede haber cero o un `ANTICIPO`
- puede haber cero o un `SALDO`

## 5. Editor de Bloques

Cada bloque se presenta como card editable. Radio de borde maximo sugerido: 8px.
La card debe ser compacta, pensada para carga operativa y comparacion rapida.

Campos editables por bloque:

- `tipo_bloque`
- `etiqueta_bloque`
- `importe_total_bloque`
- `fecha_vencimiento`
- `cantidad_cuotas`
- `importe_cuota`
- `fecha_primer_vencimiento`
- `periodicidad`

Campos no visibles y no editables:

- `numero_bloque`
- `clave_bloque`
- `numero_obligacion`
- `clave_funcional_origen`
- `id_plan_pago_venta_bloque`

### 5.1 Bloque ANTICIPO

Campos visibles:

- etiqueta
- importe total
- fecha de vencimiento

Concepto esperado en preview:

- `ANTICIPO_VENTA`

### 5.2 Bloque TRAMO_CUOTAS

Campos visibles:

- etiqueta
- cantidad de cuotas
- importe de cuota
- fecha primer vencimiento
- periodicidad

Periodicidad inicial:

- `MENSUAL`

Concepto esperado en preview:

- `CAPITAL_VENTA`

### 5.3 Bloque REFUERZO

Campos visibles:

- etiqueta
- importe total
- fecha de vencimiento

Concepto esperado en preview:

- `CAPITAL_VENTA`

### 5.4 Bloque SALDO

Campos visibles:

- etiqueta
- importe total
- fecha de vencimiento

Concepto esperado en preview:

- `CAPITAL_VENTA`

## 6. Validaciones UX

Validaciones generales:

- `monto_total_plan` debe ser mayor a cero
- todos los importes deben aceptar como maximo dos decimales
- `moneda` debe estar informada
- la suma de bloques debe coincidir con `monto_total_plan`
- si hay diferencia, mostrar el importe de diferencia

Validaciones por `tipo_pago`:

- `CONTADO` solo admite un bloque `CONTADO`
- `FINANCIADO` no admite bloque `CONTADO`

Validaciones por bloque:

- pagos unicos (`CONTADO`, `ANTICIPO`, `REFUERZO`, `SALDO`) requieren:
  - `importe_total_bloque`
  - `fecha_vencimiento`
- `TRAMO_CUOTAS` requiere:
  - `cantidad_cuotas`
  - `importe_cuota`
  - `fecha_primer_vencimiento`
  - `periodicidad = MENSUAL`

Mensajes sugeridos:

- `La suma de bloques no coincide con el monto total del plan.`
- `Un pago contado no puede mezclarse con otros bloques.`
- `Un plan financiado no admite bloque CONTADO.`
- `El tramo de cuotas requiere cantidad, importe y primer vencimiento.`
- `El bloque requiere importe y vencimiento.`
- `Los importes deben tener como maximo dos decimales.`

## 7. Preview de Cronograma

La pantalla debe mostrar una tabla de preview antes de confirmar. El preview es
visual y no persiste datos.

Columnas:

```text
N° | Bloque | Tipo obligacion | Etiqueta | Vencimiento | Importe | Concepto
```

Reglas de preview:

- `CONTADO` genera una fila `SALDO`
- `ANTICIPO` genera una fila `ANTICIPO`
- cada `TRAMO_CUOTAS` genera N filas `CUOTA`
- `REFUERZO` genera una fila `REFUERZO`
- `SALDO` genera una fila `SALDO`
- las cuotas mensuales se expanden desde `fecha_primer_vencimiento`
- el orden respeta el orden visual de bloques

Nota:

- el preview no debe mostrar `clave_funcional_origen`
- el preview no debe mostrar `numero_obligacion` como dato editable; solo puede
  mostrar el ordinal visual `N°`

## 8. Confirmacion

Boton principal:

```text
Generar plan de pago
```

Comportamiento:

1. Validar borrador visual.
2. Construir payload.
3. Ejecutar POST.
4. Bloquear controles durante loading.
5. En exito, refrescar detalle integral de venta.
6. En error, conservar borrador visual.

## 9. Payloads Esperados

### 9.1 CONTADO

```json
{
  "tipo_pago": "CONTADO",
  "monto_total_plan": 12000000.00,
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "CONTADO",
      "etiqueta_bloque": "Pago contado",
      "importe_total_bloque": 12000000.00,
      "fecha_vencimiento": "2026-06-10"
    }
  ]
}
```

### 9.2 FINANCIADO

```json
{
  "tipo_pago": "FINANCIADO",
  "monto_total_plan": 12700000.00,
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "ANTICIPO",
      "etiqueta_bloque": "Anticipo",
      "importe_total_bloque": 2000000.00,
      "fecha_vencimiento": "2026-06-10"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "etiqueta_bloque": "Primer tramo",
      "cantidad_cuotas": 6,
      "importe_cuota": 500000.00,
      "fecha_primer_vencimiento": "2026-07-10",
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
      "fecha_vencimiento": "2027-06-10"
    }
  ]
}
```

## 10. Visualizacion Posterior

Desde detalle integral de venta, si existe `plan_pago_v2`, mostrar:

Cabecera:

- metodo plan pago
- estado
- monto total
- moneda
- cantidad de bloques
- cantidad de obligaciones
- saldo pendiente total

Bloques:

- ordenados por `numero_bloque`
- card o expansion panel por bloque
- mostrar tipo, etiqueta, importe, fechas, cantidad de cuotas y periodicidad
- mostrar obligaciones dentro del bloque

Obligaciones dentro de cada bloque:

- numero
- tipo item
- etiqueta
- fecha de vencimiento
- importe total
- saldo pendiente
- estado
- composiciones

Composiciones:

- concepto
- tipo de concepto
- naturaleza
- importe componente
- saldo componente
- moneda componente

No mostrar en vista principal:

- `clave_bloque`
- `clave_funcional_origen`

Se pueden mostrar en una seccion tecnica colapsada solo para usuarios internos.

## 11. Estados UX

### 11.1 Sin plan cargado

Texto sugerido:

```text
La venta no tiene plan de pago V2 generado.
```

Accion:

```text
Cargar forma de pago
```

### 11.2 Edicion de borrador visual

Estado local no persistido. Debe mostrar:

- bloques editables
- suma actual
- diferencia
- preview de cronograma

### 11.3 Loading

Mostrar:

- controles bloqueados
- indicador de progreso
- texto `Generando plan de pago...`

### 11.4 Error de suma

Mostrar cerca del resumen:

```text
Falta asignar $X o hay $X excedente respecto del monto total.
```

### 11.5 Error de validacion

Mostrar en la card correspondiente y en resumen superior.

### 11.6 Plan vivo incompatible

Respuesta esperada:

```text
409 CONFLICT
PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE
```

Mensaje sugerido:

```text
La venta ya tiene un plan de pago vivo incompatible con esta carga.
```

Acciones:

- `Ver plan generado`
- `Cancelar`

No sugerir reemplazo automatico en este alcance.

### 11.7 Exito

Mostrar:

```text
Plan de pago generado correctamente.
```

Luego refrescar el detalle integral.

### 11.8 Plan generado

La pantalla muestra vista de lectura:

- cabecera
- bloques
- obligaciones
- composiciones
- estados y saldos

No mostrar formulario editable sobre un plan generado.

## 12. Estructura de Componentes

Componentes sugeridos:

- `PlanPagoV2Section`
- `PlanPagoV2EmptyState`
- `PlanPagoV2FormDialog`
- `TipoPagoSegmentedControl`
- `PlanPagoV2Summary`
- `BloquePagoEditorCard`
- `BloquePagoList`
- `CronogramaPreviewTable`
- `PlanPagoV2ReadOnlyView`
- `BloquePagoReadOnlyPanel`
- `ObligacionesBloqueTable`
- `ComposicionesObligacionPanel`
- `PlanPagoV2ErrorBanner`

## 13. Wireframe Textual

```text
Detalle de venta
------------------------------------------------------------
Condiciones comerciales
...

Plan de pago V2
------------------------------------------------------------
[Sin plan cargado]
La venta no tiene plan de pago V2 generado.
[ Cargar forma de pago ]

Modal / panel de carga
------------------------------------------------------------
Tipo de pago: [ CONTADO | FINANCIADO ]
Monto total: [ 12.700.000,00 ]  Moneda: [ ARS ]

Resumen
Total bloques: 12.700.000,00
Diferencia: 0,00
Obligaciones estimadas: 15

Bloques
[Card] Anticipo
  Importe: [ 2.000.000,00 ]
  Vencimiento: [ 2026-06-10 ]

[Card] Primer tramo
  Cantidad cuotas: [ 6 ]
  Importe cuota: [ 500.000,00 ]
  Primer vencimiento: [ 2026-07-10 ]
  Periodicidad: [ MENSUAL ]

[ + Agregar tramo ] [ + Agregar refuerzo ] [ + Agregar saldo ]

Preview
N° | Bloque        | Tipo | Etiqueta | Vencimiento | Importe | Concepto
1  | Anticipo      | ANT  | Anticipo | 2026-06-10  | ...     | ANTICIPO_VENTA
2  | Primer tramo  | CUO  | Cuota 1  | 2026-07-10  | ...     | CAPITAL_VENTA

[ Cancelar ] [ Generar plan de pago ]
```

## 14. Errores Mostrables

Mapeo sugerido:

| Error backend | Mensaje UX |
| --- | --- |
| `NOT_FOUND_VENTA` | La venta indicada no existe. |
| `PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE` | La venta ya tiene un plan de pago vivo incompatible. |
| `SUMA_BLOQUES_INVALIDA` | La suma de bloques no coincide con el monto total. |
| `CONTADO_BLOQUES_INVALIDOS` | Contado solo admite un unico bloque contado. |
| `FINANCIADO_NO_PERMITE_CONTADO` | Financiado no admite bloque contado. |
| `BLOQUE_INVALIDO` | Revisar campos requeridos del bloque. |
| `INVALID_PERIODICIDAD` | La periodicidad debe ser mensual. |
| `INVALID_REGLA_REDONDEO` | La regla de redondeo no es valida para este tramo. |
| `COMPRADOR_VENTA_NO_RESUELTO` | La venta debe tener un comprador financiero resoluble. |
| `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` | La venta tiene mas de un comprador financiero. |
| `NOT_FOUND_CONCEPTO:*` | Falta un concepto financiero requerido. |

## 15. Criterios de Aceptacion UX

- El usuario puede construir un plan contado sin ver campos tecnicos.
- El usuario puede construir un plan financiado con anticipo, tramos, refuerzos
  y saldo.
- La pantalla bloquea confirmacion si la suma no coincide.
- La pantalla bloquea combinaciones invalidas por tipo de pago.
- El preview permite revisar fechas, importes y conceptos antes de generar.
- El plan generado se visualiza desde detalle integral agrupado por bloques.
- Las obligaciones muestran saldo, estado y composiciones.
- No hay acciones de pago, caja ni recibo.

## 16. Proximo Prompt Recomendado

```text
Implementar prototipo Flet de carga y visualizacion de plan de pago V2 por bloques.

Usar el documento:
frontend/flet_app/documentacion/UX-PLAN-PAGO-V2-BLOQUES.md

Alcance:
- prototipo UI en frontend/flet_app
- consumir GET /api/v1/ventas/{id_venta}/detalle-integral
- consumir POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar
- no tocar backend
- no tocar SQL
- no implementar pagos, caja ni recibos
- mantener endpoints existentes

Debe incluir:
- estado sin plan
- formulario CONTADO / FINANCIADO
- editor de bloques
- validaciones UX
- preview de cronograma
- vista read-only de plan generado
```
