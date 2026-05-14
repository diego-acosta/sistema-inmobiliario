# MODELO-PLANES-PAGO-VENTA - Modelo V2 de planes de pago de venta

## Objetivo

Definir el modelo formal V2 para planes de pago de venta, preservando la
separacion de ownership entre `comercial` y `financiero`.

Este documento no implementa SQL ni backend. Congela la decision conceptual
para orientar la evolucion desde `venta_plan_cuota` V1 hacia un cronograma
basado en `obligacion_financiera`.

## Alcance

Incluye:

- diagnostico de `venta_plan_cuota`
- decision de arquitectura para planes V2
- modelo conceptual comercial-financiero
- metodos soportados por etapas
- reglas de generacion de obligaciones
- transicion desde `venta_plan_cuota`
- campos minimos requeridos para cronogramas financieros
- plan incremental de implementacion

No incluye:

- migracion SQL
- cambios de endpoints
- implementacion de servicios
- eliminacion de estructuras V1
- recalculo de deuda desde consultas comerciales

## Diagnostico actual

`venta_plan_cuota` existe en SQL y esta implementada.

Rol actual:

- es una tabla activa de compatibilidad V1
- soporta exclusivamente `CUOTAS_FIJAS`
- persiste cuotas pactadas como detalle comercial minimo
- es leida por financiero para materializar obligaciones desde
  `venta_confirmada`
- es expuesta en respuestas comerciales de detalle/condiciones cuando aplica

No es tabla muerta.

No debe eliminarse todavia porque actualmente afecta:

- definicion de condiciones comerciales de venta
- confirmacion de venta con `tipo_plan_financiero = CUOTAS_FIJAS`
- generacion de obligaciones financieras por venta confirmada
- detalle integral de venta
- seed demo UI
- tests de condiciones comerciales, financiero y detalle integral
- documentacion DEV-SRV, DEV-API y DER vigente

`venta_plan_cuota` no debe expandirse. No debe absorber nuevos metodos de
financiacion, intereses, indexacion, tramos, refinanciaciones, cancelaciones
anticipadas ni reglas avanzadas.

Clasificacion arquitectonica:

- tipo: compatibilidad heredada
- alcance: `CUOTAS_FIJAS V1`
- dominio semantico de la condicion comercial: `comercial`
- dominio semantico de deuda, saldo, imputacion y mora: `financiero`

## Decision de arquitectura

La decision congelada para V2 es:

- todo monto exigible o proyectado debe representarse como
  `obligacion_financiera`
- el cronograma de pagos vive en `obligacion_financiera`
- el desglose de cada obligacion vive en `composicion_obligacion`
- los responsables de pago viven en `obligacion_obligado`
- `plan_pago_venta`, si se crea, sera solo cabecera/regla comercial del plan
- no se crea `plan_pago_venta_cuota`
- no se crea `plan_pago_venta_tramo`
- `venta_plan_cuota` queda como compatibilidad heredada V1 para
  `CUOTAS_FIJAS`

La separacion de ownership es obligatoria:

- `comercial` define venta, condiciones comerciales y regla pactada del plan
- `financiero` define obligaciones, saldos, composiciones, imputacion, mora,
  emision y estado financiero
- una consulta comercial puede leer obligaciones asociadas a una venta, pero no
  recalcular deuda ni reemplazar reglas financieras

## Modelo conceptual

### venta

Entidad comercial principal de compraventa.

Responsabilidades:

- identifica la operacion comercial
- mantiene monto total, moneda y estado comercial
- contiene o referencia la regla comercial del plan vigente
- emite eventos comerciales como `venta_confirmada`

No debe contener el cronograma financiero V2 como lista de cuotas.

### plan_pago_venta

Cabecera/regla comercial opcional para V2.

Responsabilidades posibles:

- identificar el metodo comercial pactado
- guardar parametros de generacion del cronograma
- registrar moneda, cantidad de cuotas, periodicidad, fecha inicial, anticipo,
  tasa o indice si el metodo lo requiere
- conservar trazabilidad comercial de la regla aplicada
- permitir regeneracion controlada antes de que existan pagos o aplicaciones,
  si las reglas financieras lo permiten

Restricciones:

- no representa una cuota exigible
- no contiene tramos materializados como deuda
- no reemplaza `obligacion_financiera`
- no define saldo ni estado financiero
- no debe duplicar el cronograma

### relacion_generadora

Vincula el origen comercial con el mundo financiero.

Para ventas:

- `tipo_origen = 'venta'`
- `id_origen = venta.id_venta`

Responsabilidades:

- agrupar obligaciones de una misma venta
- servir como scope para consulta, imputacion y trazabilidad financiera
- evitar mezclar deudas de distintas relaciones generadoras

### obligacion_financiera

Unidad financiera de deuda, proyeccion o exigibilidad.

En V2 representa cada hito del cronograma:

- anticipo
- cuota
- saldo
- ajuste emitido o proyectado
- importe extraordinario si se formaliza como deuda financiera

Estados relevantes:

- `PROYECTADA`: obligacion prevista por cronograma, aun no emitida o exigida
  operativamente
- `EMITIDA`: obligacion emitida dentro del circuito financiero vigente
- otros estados existentes mantienen su semantica financiera:
  `VENCIDA`, `PARCIALMENTE_CANCELADA`, `CANCELADA`, `ANULADA`,
  `REEMPLAZADA`, `PENDIENTE_AJUSTE`

### composicion_obligacion

Desglose financiero de una obligacion.

Cada obligacion puede contener uno o mas componentes:

- `CAPITAL_VENTA`
- `ANTICIPO_VENTA`
- `INTERES_FINANCIERO`
- `AJUSTE_INDEXACION`
- otros conceptos financieros formalmente existentes

La suma de composiciones activas debe explicar el importe financiero de la
obligacion segun las reglas vigentes del modulo financiero.

### obligacion_obligado

Define quien debe responder por una obligacion.

Para venta V2 inicial:

- obligado canonico: comprador
- fuente: roles comerciales vigentes de la venta
- rol financiero: `COMPRADOR`
- responsabilidad default: 100%

Multiples compradores, porcentajes diferenciados, cesiones o sustituciones de
obligado requieren reglas explicitas antes de implementarse.

## Metodos soportados por etapas

### V1 actual

#### CONTADO

- fuente comercial: `venta`
- cronograma financiero: una obligacion `CAPITAL_VENTA`
- vencimiento: fecha de venta o regla V1 vigente
- estado: segun servicio financiero vigente

#### ANTICIPO_Y_SALDO

- fuente comercial: columnas minimas en `venta`
- cronograma financiero: dos obligaciones
- composiciones:
  - `ANTICIPO_VENTA`
  - `CAPITAL_VENTA`

#### CUOTAS_FIJAS legacy

- fuente comercial V1: `venta_plan_cuota`
- cronograma financiero: una obligacion por cuota activa
- composicion: `CAPITAL_VENTA`
- estado: segun servicio financiero vigente
- clasificacion: compatibilidad heredada

### V2 propuesto

#### CUOTAS_IGUALES_SIMPLE

Regla:

- divide el capital de venta en N obligaciones
- no calcula interes financiero
- no usa tabla de cuotas comercial
- cada cuota se materializa como `obligacion_financiera`
- cada obligacion tiene composicion `CAPITAL_VENTA`

Parametros minimos esperados en `plan_pago_venta`:

- `id_venta`
- metodo `CUOTAS_IGUALES_SIMPLE`
- cantidad de cuotas
- fecha de primer vencimiento
- periodicidad
- moneda
- regla de redondeo

#### ANTICIPO_MAS_CUOTAS_IGUALES

Regla:

- genera una obligacion de anticipo
- divide el saldo en N obligaciones iguales
- no usa tabla de cuotas comercial
- el anticipo usa `ANTICIPO_VENTA`
- las cuotas usan `CAPITAL_VENTA`

Parametros minimos esperados:

- importe o porcentaje de anticipo
- fecha de vencimiento del anticipo
- cantidad de cuotas de saldo
- fecha de primer vencimiento de saldo
- periodicidad
- moneda
- regla de redondeo

#### CRONOGRAMA_DEFINIDO

Regla:

- permite cargar un cronograma definido por el usuario
- el cronograma se persiste como obligaciones financieras
- no se crea `plan_pago_venta_cuota`
- no se crea `plan_pago_venta_tramo`
- cada item cargado genera una `obligacion_financiera`
- cada desglose cargado genera `composicion_obligacion`

Uso esperado:

- planes pactados manualmente
- refinamientos comerciales simples antes de emision
- importes no uniformes definidos por acuerdo comercial

Restriccion:

- la interfaz puede recibir items de cronograma como input transitorio, pero la
  persistencia fuente del cronograma debe ser `obligacion_financiera`

### Futuro

Los siguientes metodos quedan fuera del V2 inicial y requieren reglas
adicionales:

- `INDEXADO`
- `INTERES_DIRECTO`
- `SISTEMA_FRANCES`
- `SISTEMA_ALEMAN`

No deben inferirse desde texto libre ni desde campos incompletos.

Para habilitarlos se requiere definir:

- formula financiera
- conceptos involucrados
- redondeo
- periodicidad
- recalculo permitido
- impacto de pagos ya aplicados
- reemplazo o ajuste de obligaciones existentes
- interaccion con mora
- trazabilidad de parametros usados

## Reglas de generacion V2

### Precondiciones

Antes de generar cronograma V2:

- la venta debe existir y no estar eliminada
- la venta debe estar en estado compatible con definicion de condiciones
- el monto total debe estar definido
- la moneda debe estar definida
- los objetos de venta deben tener precio asignado consistente
- debe existir comprador financiero resoluble
- debe existir o poder crearse `relacion_generadora` de venta
- los conceptos financieros requeridos deben existir y estar activos

### Generacion de obligaciones

Cada hito del plan debe generar una `obligacion_financiera`.

Campos minimos por obligacion:

- `id_relacion_generadora`
- `fecha_emision`
- `fecha_vencimiento`
- `importe_total`
- `saldo_pendiente`
- `moneda`
- `estado_obligacion`
- metadatos core EF

Estado inicial:

- usar `PROYECTADA` cuando el cronograma representa montos previstos todavia no
  emitidos
- usar `EMITIDA` solo cuando el proceso financiero formalice la obligacion como
  emitida segun regla de negocio documentada

La transicion `PROYECTADA -> EMITIDA` debe ser explicita. No debe depender de
lecturas comerciales.

### Composicion

Cada obligacion debe tener al menos una composicion activa.

Mapeo base:

- anticipo ordinario: `ANTICIPO_VENTA`
- capital ordinario de cuotas o saldo: `CAPITAL_VENTA`
- interes ordinario pactado: `INTERES_FINANCIERO`
- ajuste por indice: `AJUSTE_INDEXACION`

Reglas:

- una cuota puede tener capital e interes en composiciones separadas
- una cuota indexada puede incorporar ajuste como composicion si el metodo lo
  define
- no se debe mezclar interes o ajuste dentro de `CAPITAL_VENTA`
- no se deben crear conceptos nuevos sin decision de catalogo financiero

### Obligados

Cada obligacion generada por venta debe asociar obligado financiero.

Regla V2 inicial:

- resolver comprador canonico desde la venta
- crear `obligacion_obligado`
- `rol_obligado = 'COMPRADOR'`
- `porcentaje_responsabilidad = 100.00`

Si hay multiples compradores o cesiones, la generacion debe fallar o quedar
pendiente hasta que exista regla documentada de distribucion.

### Idempotencia y reemplazo

La generacion V2 debe ser idempotente.

Debe evitar:

- duplicar obligaciones activas para la misma venta y mismo item de cronograma
- recrear obligaciones ya pagadas
- reemplazar obligaciones con aplicaciones activas sin regla explicita
- mezclar obligaciones V1 y V2 para el mismo plan como fuentes simultaneas

Si se regenera un plan antes de pagos:

- las obligaciones anteriores deben marcarse de forma logica segun regla
  financiera vigente
- las nuevas obligaciones deben conservar trazabilidad suficiente hacia el plan
  y corrida que las genero

## Transicion de venta_plan_cuota

### Decision

`venta_plan_cuota` se mantiene como legacy V1.

No se usa para nuevos metodos V2.

No se elimina hasta que:

- los datos V1 existentes esten migrados o preservados
- los tests dependientes hayan sido ajustados
- la API documente claramente el cambio
- el seed demo UI no dependa de esa tabla como fuente principal
- financiero lea cronogramas desde `obligacion_financiera`

### Riesgos de eliminacion temprana

Eliminar `venta_plan_cuota` ahora romperia:

- persistencia de condiciones comerciales `CUOTAS_FIJAS`
- validacion de confirmacion de venta V1
- materializacion financiera de cuotas fijas V1
- detalle integral de venta con cuotas pactadas
- tests de condiciones comerciales
- tests de evento financiero de venta confirmada
- tests de detalle integral
- seed demo UI
- documentacion actual que referencia `CUOTAS_FIJAS V1`

### Migracion futura

La migracion de `venta_plan_cuota` a obligaciones debe:

1. identificar ventas `CUOTAS_FIJAS` con cuotas activas
2. asegurar `relacion_generadora` de venta
3. crear una obligacion por cuota activa no migrada
4. crear composicion `CAPITAL_VENTA`
5. crear obligado comprador
6. preservar importes, moneda y vencimientos
7. registrar trazabilidad de origen V1
8. evitar duplicados
9. dejar `venta_plan_cuota` como lectura legacy hasta retirar compatibilidad

Mapeo conceptual:

| `venta_plan_cuota` | V2 |
| --- | --- |
| `id_venta` | `relacion_generadora(tipo_origen='venta', id_origen=id_venta)` |
| `numero_cuota` | identificador funcional/orden del item migrado |
| `importe_cuota` | `obligacion_financiera.importe_total` y composicion `CAPITAL_VENTA` |
| `fecha_vencimiento` | `obligacion_financiera.fecha_vencimiento` |
| `moneda` | `obligacion_financiera.moneda` |
| `observaciones` | observacion/trazabilidad, si se define campo destino |

## Campos minimos de obligacion_financiera

### Auditoria actual

La tabla `obligacion_financiera` ya tiene campos utiles para V2:

- `id_obligacion_financiera`
- `uid_global`
- `version_registro`
- `created_at`
- `updated_at`
- `deleted_at`
- `id_instalacion_origen`
- `id_instalacion_ultima_modificacion`
- `op_id_alta`
- `op_id_ultima_modificacion`
- `id_relacion_generadora`
- `codigo_obligacion_financiera`
- `descripcion_operativa`
- `fecha_generacion`
- `fecha_emision`
- `fecha_vencimiento`
- `periodo_desde`
- `periodo_hasta`
- `importe_total`
- `saldo_pendiente`
- `moneda`
- `estado_obligacion`
- flags operativos y campos de reemplazo

El estado `PROYECTADA` ya existe en el constraint de estados.

### Brechas para V2

Antes de implementar liquidacion V2 debe decidirse si hace falta agregar campos
o convenciones para:

- `numero_obligacion`: orden funcional dentro del plan o cronograma
- `etiqueta_obligacion`: texto estable para UI y reportes
- referencia funcional del item de plan que genero la obligacion
- referencia de corrida/generacion de cronograma
- trazabilidad de migracion desde `venta_plan_cuota`

No debe usarse `venta_plan_cuota.id_venta_plan_cuota` como dependencia
permanente del modelo V2.

Alternativas posibles:

- usar `codigo_obligacion_financiera` con una convencion estable
- usar `descripcion_operativa` solo como descripcion no funcional
- agregar campos especificos en SQL para orden y referencia funcional
- agregar una tabla tecnica de trazabilidad de generacion, sin representar
  cuotas como entidad de negocio

Decision pendiente:

- definir si `numero_obligacion` y `etiqueta_obligacion` pertenecen a
  `obligacion_financiera` o a una estructura tecnica de generacion
- definir clave de idempotencia para cada obligacion del cronograma
- definir como se consulta el orden del cronograma sin depender de texto libre

## Plan incremental de implementacion

### Paso 1 - Documentacion

- crear este documento
- alinear DEV-SRV financiero y comercial con la decision V2
- marcar `venta_plan_cuota` como legacy V1 en documentos afectados
- documentar cualquier drift entre estado implementado y estado documentado

### Paso 2 - SQL de cabecera comercial

Crear `plan_pago_venta` solo si el caso de uso requiere persistir regla
comercial del plan.

Debe contener cabecera y parametros, no cuotas.

Campos candidatos:

- `id_plan_pago_venta`
- metadatos core EF
- `id_venta`
- `metodo_plan_pago`
- `estado_plan_pago`
- `moneda`
- `monto_total_plan`
- `cantidad_cuotas`
- `periodicidad`
- `fecha_primer_vencimiento`
- `importe_anticipo`
- `fecha_vencimiento_anticipo`
- `tasa_interes`
- `indice_referencia`
- `regla_redondeo`
- `observaciones`

Los campos exactos deben validarse contra SQL, DEV-API, DEV-SRV y tests antes
de implementarse.

### Paso 3 - Campos minimos en financiero

Auditar si `obligacion_financiera` necesita campos nuevos para cronogramas V2.

Prioridad:

1. orden funcional de obligacion dentro del plan
2. etiqueta estable de obligacion
3. referencia funcional de origen/corrida
4. clave de idempotencia

No avanzar a generacion V2 sin resolver duplicados e idempotencia.

### Paso 4 - Servicio de liquidacion/generacion V2

Crear servicio que:

- reciba venta y regla comercial del plan
- valide condiciones comerciales
- resuelva comprador
- asegure `relacion_generadora`
- genere obligaciones proyectadas o emitidas
- cree composiciones y obligados
- sea idempotente
- no use `venta_plan_cuota` para metodos V2

### Paso 5 - Migracion de CUOTAS_FIJAS

Disenar migracion de V1 a V2:

- convertir cuotas activas a obligaciones financieras
- preservar trazabilidad
- ajustar seeds
- ajustar tests
- mantener lectura legacy durante transicion

### Paso 6 - Deprecacion de venta_plan_cuota

Cuando V2 este estable:

- dejar de escribir nuevas filas V1
- migrar o congelar datos existentes
- actualizar API y documentacion
- retirar dependencia de tests
- evaluar eliminacion fisica solo con decision explicita

## Reglas de no duplicacion

Durante la transicion:

- una venta no debe tener dos cronogramas activos equivalentes
- si `venta_plan_cuota` genera obligaciones V1, esas obligaciones son la deuda
  financiera; la tabla legacy no debe volver a interpretarse como deuda activa
  paralela
- si V2 genera obligaciones desde `plan_pago_venta`, no debe crear
  `venta_plan_cuota`
- las consultas deben distinguir entre regla comercial, cronograma financiero y
  compatibilidad legacy

## Estado del documento

Estado: propuesta formal V2, sin implementacion.

Restricciones vigentes:

- no modificar SQL por este documento
- no modificar backend productivo por este documento
- no eliminar `venta_plan_cuota`
- no crear tablas de cuotas o tramos de plan de pago de venta
- no asumir campos inexistentes como implementados

