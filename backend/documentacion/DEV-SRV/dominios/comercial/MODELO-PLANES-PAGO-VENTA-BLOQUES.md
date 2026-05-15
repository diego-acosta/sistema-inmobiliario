# MODELO-PLANES-PAGO-VENTA-BLOQUES - Planes de pago por bloques

## Objetivo

Definir el modelo conceptual para expresar planes de pago de venta como una
cabecera `plan_pago_venta` compuesta por bloques comerciales ordenados.

El objetivo es representar como el usuario negocia y carga una forma de pago:
contado o financiado, anticipo opcional, tramos de cuotas, refuerzos, saldo
final y, en etapas posteriores, indexacion o interes.

Este documento es de diseno. No implementa SQL, backend, UI ni migracion.

## Principio rector

Todo monto exigible o proyectado vive en `obligacion_financiera`.

Por lo tanto:

- `plan_pago_venta_bloque` no es deuda
- `plan_pago_venta_bloque` no es cuota financiera
- `plan_pago_venta_bloque` no tiene saldo
- `plan_pago_venta_bloque` no se paga
- `plan_pago_venta_bloque` no reemplaza `obligacion_financiera`
- `plan_pago_venta_bloque` solo describe una regla comercial que genera una o
  mas obligaciones financieras

La materializacion financiera sigue siendo:

- `relacion_generadora`
- `generacion_cronograma_financiero`
- `obligacion_financiera`
- `composicion_obligacion`
- `obligacion_obligado`

## Decision: tabla de bloques

Conviene crear una tabla `plan_pago_venta_bloque`.

Razon:

- el usuario no carga metodos tecnicos aislados, carga una forma de pago
  compuesta
- `plan_pago_venta` como cabecera unica no alcanza para describir varios tramos,
  refuerzos o saldos finales
- usar endpoints especificos por combinacion genera explosion de casos:
  `anticipo + cuotas`, `anticipo + dos tramos`, `cuotas + refuerzo`, etc.
- `venta_plan_cuota` no debe expandirse porque es compatibilidad heredada V1
- crear tablas de cuotas financieras volveria a duplicar
  `obligacion_financiera`

Clasificacion:

- `plan_pago_venta`: nucleo comercial, cabecera/regla general
- `plan_pago_venta_bloque`: nucleo comercial, estructura de negociacion
- `obligacion_financiera`: nucleo financiero, deuda/proyeccion
- `composicion_obligacion`: soporte financiero de desglose
- `obligacion_obligado`: soporte financiero de responsabilidad
- `venta_plan_cuota`: compatibilidad heredada V1

## Bloque comercial vs obligacion financiera

### Bloque comercial

Describe una parte de la forma de pago pactada.

Ejemplos:

- anticipo de un monto fijo
- tramo de 6 cuotas de un importe
- refuerzo extraordinario en diciembre
- saldo contra escritura
- tramo futuro indexado

Responsabilidades:

- ordenar la estructura comercial del plan
- guardar parametros de generacion
- permitir explicar por que se generaron ciertas obligaciones
- servir como origen funcional de una parte del cronograma

No responsabilidades:

- no guarda saldo pendiente
- no guarda importe cancelado
- no guarda estado financiero de pago
- no recibe imputaciones
- no genera mora
- no emite recibos
- no define caja ni tesoreria

### Obligacion financiera

Representa un hito exigible o proyectado del cronograma.

Responsabilidades:

- importe total
- saldo pendiente
- fecha de vencimiento
- estado financiero
- composiciones
- obligados
- pagos, imputaciones, mora y reportes financieros

Una obligacion puede haberse originado en un bloque, pero una vez creada es la
fuente de verdad financiera.

## Tipos de bloque

### CONTADO

Pago unico por el total o por el saldo total del plan.

Uso:

- venta sin financiacion
- una sola obligacion `CAPITAL_VENTA`

Datos minimos:

- `orden_bloque`
- `tipo_bloque = CONTADO`
- `monto_bloque`
- `fecha_vencimiento`
- `moneda`

Materializacion:

- 1 obligacion
- `tipo_item_cronograma = SALDO` con el catalogo SQL vigente; `CONTADO`
  como item de cronograma solo podria usarse si una decision futura lo agrega al
  catalogo/SQL
- composicion `CAPITAL_VENTA`

### ANTICIPO

Pago inicial anterior o simultaneo al inicio del cronograma de cuotas.

Datos minimos:

- `orden_bloque`
- `tipo_bloque = ANTICIPO`
- `monto_bloque`
- `fecha_vencimiento`
- `moneda`

Materializacion:

- 1 obligacion
- `tipo_item_cronograma = ANTICIPO`
- composicion `ANTICIPO_VENTA`

### TRAMO_CUOTAS

Conjunto de cuotas homogéneas por cantidad, periodicidad y regla de importe.

Datos minimos:

- `orden_bloque`
- `tipo_bloque = TRAMO_CUOTAS`
- `cantidad_cuotas`
- `importe_cuota` o `monto_bloque` a distribuir
- `fecha_primer_vencimiento`
- `periodicidad`
- `regla_redondeo`
- `moneda`

Materializacion:

- N obligaciones
- `tipo_item_cronograma = CUOTA`
- composicion `CAPITAL_VENTA`
- etiqueta operativa `Cuota N`

### REFUERZO

Pago extraordinario pactado fuera de la secuencia regular de cuotas.

Datos minimos:

- `orden_bloque`
- `tipo_bloque = REFUERZO`
- `monto_bloque`
- `fecha_vencimiento`
- `moneda`
- `etiqueta_bloque` opcional, por ejemplo `Refuerzo diciembre`

Materializacion:

- 1 obligacion por refuerzo
- `tipo_item_cronograma = REFUERZO`
- composicion `CAPITAL_VENTA` salvo que se defina un concepto financiero
  especifico

### SALDO

Pago final condicionado por un hito comercial, por ejemplo escritura.

Datos minimos:

- `orden_bloque`
- `tipo_bloque = SALDO`
- `monto_bloque` o regla de saldo remanente
- `fecha_vencimiento` o `hito_vencimiento`
- `moneda`

Materializacion:

- 1 obligacion
- `tipo_item_cronograma = SALDO`
- composicion `CAPITAL_VENTA`

### Futuro TRAMO_INDEXADO

Tramo de cuotas con ajuste por indice.

Datos minimos futuros:

- indice de referencia
- base de actualizacion
- frecuencia de actualizacion
- regla de redondeo
- regla de reemplazo o ajuste de obligaciones ya generadas

Materializacion futura:

- obligaciones `CAPITAL_VENTA`
- composicion `AJUSTE_INDEXACION` cuando el ajuste se materialice
- no mezclar ajuste dentro de `CAPITAL_VENTA`

### Futuro TRAMO_INTERES

Tramo con interes financiero pactado.

Datos minimos futuros:

- tasa
- sistema de calculo
- base de capital
- periodicidad
- regla de amortizacion

Materializacion futura:

- capital en `CAPITAL_VENTA`
- interes en `INTERES_FINANCIERO`
- no mezclar interes dentro de capital

## Datos minimos de plan_pago_venta_bloque

Campos candidatos:

- `id_plan_pago_venta_bloque`
- metadatos core EF
- `id_plan_pago_venta`
- `orden_bloque`
- `tipo_bloque`
- `estado_bloque`
- `moneda`
- `monto_bloque`
- `cantidad_cuotas`
- `importe_cuota`
- `fecha_vencimiento`
- `fecha_primer_vencimiento`
- `periodicidad`
- `regla_redondeo`
- `hito_vencimiento`
- `indice_referencia`
- `tasa_interes`
- `observaciones`

No todos los campos aplican a todos los tipos de bloque. Deben existir checks
por tipo para evitar combinaciones ambiguas. Los importes guardados en el bloque
son parametros de regla comercial, no saldo financiero ni deuda exigible.

## Datos que NO debe guardar

`plan_pago_venta_bloque` no debe guardar:

- `saldo_pendiente`
- `importe_cancelado`
- `estado_obligacion`
- `estado_pago`
- `id_movimiento_financiero`
- `id_aplicacion_financiera`
- datos de recibo
- datos de caja o tesoreria
- mora calculada
- punitorios liquidados
- composiciones financieras detalladas como si fueran saldo
- obligados financieros finales como si reemplazaran `obligacion_obligado`

Tampoco debe guardar una fila por cuota regular. Para un tramo de 12 cuotas debe
existir un bloque `TRAMO_CUOTAS`, no 12 bloques-cuota, salvo que cada cuota sea
un acuerdo comercial especial y no un tramo uniforme.

## Materializacion en obligacion_financiera

La generacion del plan debe:

1. leer `plan_pago_venta`
2. leer bloques activos ordenados por `orden_bloque`
3. asegurar `relacion_generadora` de venta
4. crear una `generacion_cronograma_financiero`
5. expandir cada bloque en obligaciones
6. crear composiciones segun tipo de bloque
7. crear obligados segun regla vigente de compradores
8. devolver plan, generacion y obligaciones resultantes

Ejemplos:

| Bloque | Obligaciones generadas | Composicion |
| --- | --- | --- |
| `CONTADO` | 1 | `CAPITAL_VENTA` |
| `ANTICIPO` | 1 | `ANTICIPO_VENTA` |
| `TRAMO_CUOTAS` de 6 cuotas | 6 | `CAPITAL_VENTA` |
| `REFUERZO` | 1 | `CAPITAL_VENTA` o concepto especifico futuro |
| `SALDO` | 1 | `CAPITAL_VENTA` |

## Uso de composicion_obligacion

`composicion_obligacion` explica la naturaleza economica de cada obligacion.

Reglas:

- anticipo ordinario: `ANTICIPO_VENTA`
- cuotas de capital: `CAPITAL_VENTA`
- saldo final de capital: `CAPITAL_VENTA`
- refuerzo de capital: `CAPITAL_VENTA` mientras no exista concepto especifico
- indexacion futura: `AJUSTE_INDEXACION`
- interes futuro: `INTERES_FINANCIERO`

No se deben crear conceptos financieros por conveniencia de UI. Cada concepto
nuevo requiere decision del catalogo financiero.

## clave_funcional_origen

La idempotencia debe seguir apoyandose en `clave_funcional_origen`.

Convencion recomendada:

```text
PLAN_PAGO_VENTA:{id_plan_pago_venta}:BLOQUE:{orden_bloque}:{tipo_item}:{n}
```

Ejemplos:

```text
PLAN_PAGO_VENTA:10:BLOQUE:1:ANTICIPO:1
PLAN_PAGO_VENTA:10:BLOQUE:2:CUOTA:1
PLAN_PAGO_VENTA:10:BLOQUE:2:CUOTA:2
PLAN_PAGO_VENTA:10:BLOQUE:4:REFUERZO:1
PLAN_PAGO_VENTA:10:BLOQUE:5:SALDO:1
```

La clave no debe depender de:

- importe
- fecha de vencimiento
- texto libre
- `id_obligacion_financiera`

Debe depender de:

- plan
- bloque
- tipo funcional del item
- numero funcional dentro del bloque

## Vinculo obligacion-bloque

Hay dos alternativas.

### Alternativa A: solo clave_funcional_origen

Ventajas:

- no agrega FK nueva
- mantiene el modelo minimo actual
- alcanza para idempotencia

Desventajas:

- consultar obligaciones por bloque requiere parsear o construir claves
- no hay integridad referencial directa
- migraciones y reportes son mas fragiles

### Alternativa B: FK id_plan_pago_venta_bloque en obligacion_financiera

Ventajas:

- trazabilidad directa
- consultas simples por bloque
- evita depender de parseo de strings
- facilita explicar UI: bloque -> obligaciones generadas
- facilita regeneracion parcial por bloque antes de pagos

Desventajas:

- requiere SQL nuevo
- acopla la obligacion a una regla comercial de origen
- requiere definir comportamiento si el bloque se reemplaza o anula

Decision recomendada:

- para un diseno robusto conviene agregar
  `obligacion_financiera.id_plan_pago_venta_bloque`
- mantener `clave_funcional_origen` igualmente como clave idempotente estable
- no usar la FK como clave de negocio unica

Motivo:

La FK responde trazabilidad y consulta. `clave_funcional_origen` responde
idempotencia. Son problemas distintos.

## Endpoint unificado propuesto

Endpoint futuro:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar
```

El contrato detallado queda separado en:

- `DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`

Decisiones principales:

- el request recibe `tipo_pago = CONTADO | FINANCIADO`
- el request recibe bloques comerciales, no metodos tecnicos aislados
- `numero_bloque` se asigna por orden del array
- `clave_bloque` se genera por plan, tipo de bloque y ordinal del tipo
- `clave_funcional_origen` sigue siendo la clave idempotente de obligacion
- `id_plan_pago_venta_bloque` es trazabilidad, no idempotencia
- `CONTADO` se materializa como `tipo_item_cronograma = SALDO` mientras SQL no
  soporte un item `CONTADO`
- el endpoint unificado no usa `venta_plan_cuota`
- no implementa pagos, caja, recibos, indexacion, interes, sistema frances ni
  sistema aleman

## Endpoints especificos actuales

Endpoints existentes:

- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales`

Decision de transicion:

- mantenerlos funcionando
- tratarlos como wrappers de compatibilidad V2 inicial
- no eliminarlos hasta que el endpoint unificado este implementado, documentado
  y cubierto por tests
- internamente, en una etapa futura, pueden traducirse a bloques:
  - `CUOTAS_IGUALES_SIMPLE` -> un bloque `TRAMO_CUOTAS`
  - `ANTICIPO_MAS_CUOTAS_IGUALES` -> bloque `ANTICIPO` + bloque
    `TRAMO_CUOTAS`

No deben seguir creciendo para cubrir combinaciones nuevas.

## Transicion sin romper lo implementado

Fase 1, documentacion:

- crear este modelo de bloques
- mantener servicios existentes sin cambios

Fase 2, SQL futuro:

- crear `plan_pago_venta_bloque`
- opcional recomendado: agregar
  `obligacion_financiera.id_plan_pago_venta_bloque`
- agregar constraints por tipo de bloque
- agregar indices de orden e idempotencia

Fase 3, backend futuro:

- implementar endpoint unificado
- agregar generador por bloques
- conservar endpoints especificos como adaptadores
- no tocar `venta_plan_cuota`

Fase 4, UI futura:

- construir editor visual de bloques
- mostrar previsualizacion de obligaciones antes de generar
- mostrar plan generado como bloques + obligaciones asociadas

Fase 5, migracion/control:

- decidir si planes V2 existentes se migran a bloques o quedan como V2 inicial
- mantener compatibilidad de lectura
- no migrar deuda si ya existen pagos sin regla explicita

## Impacto en tests

Tests futuros esperados:

- crear plan contado como un bloque
- crear plan financiado sin anticipo como un bloque `TRAMO_CUOTAS`
- crear plan financiado con anticipo como `ANTICIPO + TRAMO_CUOTAS`
- crear plan con dos tramos de cuotas
- crear plan con refuerzo
- crear plan con saldo final
- validar suma de bloques contra total
- validar idempotencia por bloque e item
- validar que no se crea `venta_plan_cuota`
- validar que cada obligacion queda vinculada al bloque de origen
- validar que endpoints especificos actuales siguen pasando
- validar que `CUOTAS_FIJAS V1` sigue usando `venta_plan_cuota`

## Impacto en SQL futuro

SQL futuro probable:

- tabla `plan_pago_venta_bloque`
- constraints por `tipo_bloque`
- indice unico por `(id_plan_pago_venta, orden_bloque)` para bloques activos
- indice por `(id_plan_pago_venta, tipo_bloque)`
- FK desde `plan_pago_venta_bloque` a `plan_pago_venta`
- FK opcional recomendada desde `obligacion_financiera` a
  `plan_pago_venta_bloque`

No crear:

- `plan_pago_venta_cuota`
- `plan_pago_venta_tramo` como entidad separada
- tablas financieras paralelas de cuotas

## Impacto en UI futura

La UI deberia permitir armar bloques, no elegir solo un metodo tecnico.

Flujos:

- pago contado: un bloque `CONTADO`
- financiado sin anticipo: un bloque `TRAMO_CUOTAS`
- financiado con anticipo: `ANTICIPO + TRAMO_CUOTAS`
- varios tramos: varios bloques `TRAMO_CUOTAS`
- refuerzos: bloques `REFUERZO`
- saldo final: bloque `SALDO`

La UI puede mostrar una previsualizacion de obligaciones, pero esa
previsualizacion no es deuda hasta que se materialice como
`obligacion_financiera`.

## Ejemplo completo

Pago financiado:

- anticipo de $ 2.000.000
- 6 cuotas de $ 500.000
- 6 cuotas de $ 700.000
- refuerzo diciembre de $ 1.500.000
- saldo contra escritura

Bloques:

1. `ANTICIPO`
2. `TRAMO_CUOTAS`
3. `TRAMO_CUOTAS`
4. `REFUERZO`
5. `SALDO`

Materializacion:

- 1 obligacion `ANTICIPO`
- 6 obligaciones `CUOTA` desde el primer tramo
- 6 obligaciones `CUOTA` desde el segundo tramo
- 1 obligacion `REFUERZO`
- 1 obligacion `SALDO`

Composiciones:

- anticipo: `ANTICIPO_VENTA`
- cuotas: `CAPITAL_VENTA`
- refuerzo: `CAPITAL_VENTA`
- saldo: `CAPITAL_VENTA`

Claves funcionales ejemplo:

```text
PLAN_PAGO_VENTA:10:BLOQUE:1:ANTICIPO:1
PLAN_PAGO_VENTA:10:BLOQUE:2:CUOTA:1
PLAN_PAGO_VENTA:10:BLOQUE:2:CUOTA:6
PLAN_PAGO_VENTA:10:BLOQUE:3:CUOTA:1
PLAN_PAGO_VENTA:10:BLOQUE:3:CUOTA:6
PLAN_PAGO_VENTA:10:BLOQUE:4:REFUERZO:1
PLAN_PAGO_VENTA:10:BLOQUE:5:SALDO:1
```

## Limitaciones explicitas

Este modelo no implementa:

- SQL
- endpoint unificado
- refactor de servicios existentes
- UI
- pagos
- caja/tesoreria
- recibos
- mora
- indexacion
- interes
- sistema frances
- sistema aleman
- migracion de `venta_plan_cuota`

## Proximo paso tecnico recomendado

Disenar SQL minimo para `plan_pago_venta_bloque`:

1. definir columnas y checks por tipo de bloque
2. definir si `obligacion_financiera.id_plan_pago_venta_bloque` se agrega en el
   mismo cambio
3. definir convencion final de `clave_funcional_origen`
4. agregar tests de schema
5. recien despues implementar el endpoint unificado
