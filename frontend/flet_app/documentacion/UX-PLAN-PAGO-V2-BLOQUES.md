# UX-PLAN-PAGO-V2-BLOQUES - Plan de pago V2 por bloques

## 1. Objetivo y alcance

Definir la experiencia de usuario para cargar, previsualizar, generar y consultar
un plan de pago de venta V2 por bloques, incluyendo liquidacion visual por bloque
`TRAMO_CUOTAS` con:

- `SIN_INTERES` / comportamiento legacy.
- `INTERES_DIRECTO`.
- `INDEXACION`.
- Consulta integral posterior del plan generado.

Alcance del documento y del prototipo:

- documentacion UX y prototipo Flet no productivo;
- no modifica backend;
- no modifica SQL;
- no implementa pagos, caja, recibos ni emision posterior de cuotas indexadas;
- no cambia reglas financieras: refleja los contratos existentes del backend.

Endpoints usados por la UX/prototipo:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview
POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar
GET  /api/v1/ventas/{id_venta}/plan-pago-v2
```

## 2. Clasificacion y dominio

- Dominio correcto: `comercial`, porque el plan de pago V2 pertenece a las
  condiciones comerciales de una venta.
- Conceptos financieros de composicion (`CAPITAL_VENTA`, `INTERES_FINANCIERO`,
  `AJUSTE_INDEXACION`) se muestran como lectura de la respuesta existente, sin
  ejecutar pagos, imputaciones, caja ni recibos.
- La UX no invade dominio operativo ni pagos/caja.

## 3. Principios UX

- La pantalla debe hablar en terminos comerciales: contado, anticipo, cuotas,
  refuerzos, saldo, interes directo e indexacion.
- La validacion visual debe anticipar errores antes de llamar al backend.
- Preview y consulta integral son lectura/visualizacion; no prometen pago,
  caja, recibo ni emision posterior de cuotas indexadas.
- Una vez generado, el plan se presenta como estructura de consulta cerrada.

## 4. Flujo de pantalla

1. El usuario ingresa al prototipo o al detalle de una venta.
2. Selecciona `CONTADO` o `FINANCIADO`.
3. Carga bloques comerciales.
4. En cada `TRAMO_CUOTAS` elige `Metodo de liquidacion`.
5. La pantalla valida suma, campos requeridos y exclusividad de metodos.
6. Ejecuta preview oficial con `POST /preview`.
7. Revisa cronograma, interes, ajustes e indexacion proyectada/aplicada.
8. Confirma con `Generar plan de pago`.
9. El generate envia headers CORE-EF requeridos y, si responde OK, refresca
   `GET /api/v1/ventas/{id_venta}/plan-pago-v2`.
10. El plan generado se visualiza con cabecera, bloques, obligaciones,
    composiciones, indexacion por obligacion y resumen.

## 5. Editor de bloques

Cada bloque se muestra como card editable.

Campos comunes:

- `tipo_bloque`.
- `etiqueta_bloque`.
- importes y fechas segun tipo.

Campos no principales / tecnicos:

- `numero_bloque`.
- `clave_bloque`.
- `numero_obligacion`.
- `clave_funcional_origen`.
- `id_plan_pago_venta_bloque`.

### 5.1 Bloques de pago unico

Aplica a `CONTADO`, `ANTICIPO`, `REFUERZO` y `SALDO`.

Campos visibles:

- etiqueta;
- `importe_total_bloque`;
- `fecha_vencimiento`.

Conceptos esperados:

- `CONTADO` se materializa como item `SALDO` con `CAPITAL_VENTA`.
- `ANTICIPO` usa `ANTICIPO_VENTA`.
- `REFUERZO` y `SALDO` usan `CAPITAL_VENTA`.

### 5.2 TRAMO_CUOTAS: campos base

Campos visibles:

- etiqueta;
- `importe_total_bloque` / capital inicial del tramo;
- `cantidad_cuotas`;
- `fecha_primer_vencimiento`;
- `periodicidad = MENSUAL`;
- selector `Metodo de liquidacion`.

## 6. Metodo de liquidacion por TRAMO_CUOTAS

Selector obligatorio de UX:

```text
SIN_INTERES | INTERES_DIRECTO | INDEXACION
```

Reglas:

- `INTERES_DIRECTO` e `INDEXACION` son excluyentes dentro del mismo bloque.
- Pueden coexistir en bloques distintos del mismo plan.
- Si se elige `INTERES_DIRECTO`, la UI oculta y limpia campos de `INDEXACION`.
- Si se elige `INDEXACION`, la UI oculta y limpia campos de `INTERES_DIRECTO`.
- Si se elige `SIN_INTERES`, la UI oculta y limpia ambos grupos.

### 6.1 SIN_INTERES / legacy

No muestra campos adicionales de liquidacion.

Payload por bloque:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "etiqueta_bloque": "Tramo sin interes",
  "importe_total_bloque": 6000000.0,
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "SIN_INTERES"
}
```

### 6.2 INTERES_DIRECTO

Ayuda visible:

```text
Interes directo: interes simple sobre capital inicial del bloque.
```

Campos visibles:

- `tasa_interes_directo_periodica`;
- `cantidad_periodos`;
- `base_calculo_interes = CAPITAL_INICIAL_BLOQUE`.

Payload de ejemplo:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "etiqueta_bloque": "Tramo con interes directo",
  "importe_total_bloque": 6000000.0,
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INTERES_DIRECTO",
  "tasa_interes_directo_periodica": 2.5,
  "cantidad_periodos": 6,
  "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE"
}
```

### 6.3 INDEXACION

Campos visibles:

- `id_indice_financiero` o selector de indice;
- `fecha_base_indice`;
- `valor_base_indice`;
- `modo_indexacion = POR_COEFICIENTE`;
- `base_calculo_indexacion = CAPITAL_INICIAL_BLOQUE`;
- `tipo_generacion_indexada = DEFINITIVA`;
- `politica_valor_no_disponible = ERROR_SI_NO_EXISTE`;
- `conserva_capital_original = true`;
- `genera_ajuste_por_diferencia = true`.

Para demo/prototipo se ofrecen:

- `CAC_DEMO`;
- `IPC_DEMO`;
- `UVA_DEMO`;
- `RIPTE_DEMO`.

La UI debe aclarar: `valores demo/no oficiales`. Si no existe endpoint frontend
para buscar indices, se permite lista mock local y campo editable de
`id_indice_financiero` para ajustar la base DEV local.

Payload de ejemplo:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "etiqueta_bloque": "Tramo indexado CAC",
  "importe_total_bloque": 6000000.0,
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INDEXACION",
  "id_indice_financiero": 1,
  "fecha_base_indice": "2026-01-01",
  "valor_base_indice": 1000.0,
  "modo_indexacion": "POR_COEFICIENTE",
  "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
  "tipo_generacion_indexada": "DEFINITIVA",
  "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
  "conserva_capital_original": true,
  "genera_ajuste_por_diferencia": true
}
```

## 7. Validaciones UX

Generales:

- `monto_total_plan > 0`;
- `moneda` informada;
- importes con maximo dos decimales;
- suma UX de bloques = `monto_total_plan`;
- suma enviada al backend = `monto_total_plan`;
- `CONTADO` solo admite un bloque `CONTADO`;
- `FINANCIADO` no admite bloque `CONTADO`.

Por `TRAMO_CUOTAS`:

- requiere `importe_total_bloque` / capital del tramo;
- requiere `cantidad_cuotas`;
- requiere `fecha_primer_vencimiento`;
- requiere `periodicidad = MENSUAL`.

Por `INTERES_DIRECTO`:

- requiere `tasa_interes_directo_periodica`;
- requiere `cantidad_periodos`;
- requiere `base_calculo_interes = CAPITAL_INICIAL_BLOQUE`;
- bloquea campos de `INDEXACION` en el mismo bloque.

Por `INDEXACION`:

- requiere `importe_total_bloque`, no solo `importe_cuota`;
- requiere `id_indice_financiero`;
- requiere `fecha_base_indice`;
- requiere `valor_base_indice > 0`;
- requiere `base_calculo_indexacion = CAPITAL_INICIAL_BLOQUE`;
- bloquea campos de `INTERES_DIRECTO` en el mismo bloque.

## 8. Preview oficial

La tabla de preview debe mostrar:

```text
N° | Bloque | Tipo obligacion | Etiqueta | Vencimiento | Capital cuota | Interes / Ajuste | Importe total | Estado indexacion | Concepto
```

Reglas:

- `CONTADO` genera una fila `SALDO`.
- `ANTICIPO` genera una fila `ANTICIPO`.
- Cada `TRAMO_CUOTAS` genera N filas `CUOTA`.
- `REFUERZO` genera una fila `REFUERZO`.
- `SALDO` genera una fila `SALDO`.
- El orden respeta el orden visual de bloques.

Para `INDEXACION`:

- Si la cuota tiene indice aplicado, mostrar `Con indice aplicado`, valor
  aplicado, coeficiente y ajuste.
- Si no tiene indice, mostrar `Proyectada sin indice` y capital base.

Resumen de preview:

- `total_calculado`;
- `total_con_interes`;
- `total_con_indexacion`;
- `total_ajuste_indexacion`;
- diferencia contra el monto total.

## 9. Generate

Boton:

```text
Generar plan de pago
```

Comportamiento:

- requiere preview oficial vigente y sin errores;
- ejecuta `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar`;
- si responde OK, muestra mensaje de exito y refresca consulta integral;
- si responde error, conserva borrador y muestra error backend contextual.

Headers CORE-EF para generate:

```text
X-Op-Id
X-Usuario-Id
X-Sucursal-Id
X-Instalacion-Id
```

Preview y consulta integral no requieren `X-Op-Id`.

## 10. Consulta integral posterior

Usar:

```text
GET /api/v1/ventas/{id_venta}/plan-pago-v2
```

Mostrar:

- cabecera del plan;
- bloques;
- configuracion de indexacion por bloque;
- obligaciones;
- composiciones;
- detalle de indexacion por obligacion si existe;
- resumen.

Resumen requerido:

- `total_capital`;
- `total_interes`;
- `total_ajuste_indexacion`;
- `total_obligaciones`;
- `cantidad_obligaciones_con_indexacion`;
- `cantidad_obligaciones_proyectadas_sin_indexacion`.

Composiciones por obligacion:

- `CAPITAL_VENTA`;
- `INTERES_FINANCIERO`;
- `AJUSTE_INDEXACION`.

Si `obligacion.indexacion != null`, mostrar valor aplicado, coeficiente y
fecha de valor. Si la obligacion pertenece a bloque `INDEXACION` pero
`indexacion == null`, mostrar:

```text
Proyectada sin indice aplicado
```

## 11. CORE-EF

Decision UX/prototipo:

- La UI/prototipo no modifica endpoint write ni contratos backend.
- `POST /preview`: `PREVIEW_READLIKE`; no fuerza headers write.
- `GET /plan-pago-v2`: `QUERY_READLIKE`; no fuerza headers write.
- `POST /generar`: `COMMAND_WRITE_NEGOCIO` existente; el prototipo envia los
  headers CORE-EF requeridos por backend.
- Idempotencia, outbox, lock logico, versionado y rollback se consideran
  responsabilidad del backend existente; la UI no declara cumplimiento profundo
  sin evidencia de router/service/repository/SQL/tests.

## 12. Fuera de alcance

Queda explicitamente fuera de alcance:

- pagos;
- caja;
- recibos fiscales persistidos;
- documental real;
- emision posterior de cuotas indexadas;
- cambios SQL;
- cambios backend;
- cambios de reglas financieras.

## 13. Criterios de aceptacion UX

- El usuario puede construir un plan contado sin ver campos tecnicos.
- El usuario puede construir un plan financiado con anticipo, tramos, refuerzos
  y saldo.
- Cada `TRAMO_CUOTAS` permite elegir `SIN_INTERES`, `INTERES_DIRECTO` o
  `INDEXACION`.
- La UI impide mezclar `INTERES_DIRECTO` e `INDEXACION` en el mismo bloque.
- La pantalla bloquea confirmacion si la suma no coincide.
- El preview muestra capital, interes/ajuste, importe total, estado de
  indexacion y concepto.
- Generate envia headers CORE-EF.
- La consulta integral muestra cabecera, bloques, indexacion, obligaciones,
  composiciones y resumen.
- No hay acciones de pago, caja ni recibo.
