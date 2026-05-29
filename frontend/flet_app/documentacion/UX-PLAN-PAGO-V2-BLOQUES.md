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
- el prototipo principal para probar el flujo completo es `frontend/flet_app/prototypes/venta_completa_wizard_prototype.py`;
- `frontend/flet_app/prototypes/plan_pago_v2_bloques_prototype.py` queda como referencia aislada/auxiliar y no es el flujo principal de venta completa;
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

## 3. Prototipo principal

El soporte visual de Plan Pago V2 por bloques debe validarse en
`frontend/flet_app/prototypes/venta_completa_wizard_prototype.py`, porque ese
archivo representa el wizard principal de venta completa. La pantalla aislada
`plan_pago_v2_bloques_prototype.py` puede servir como referencia UX auxiliar,
pero no debe considerarse el flujo principal para probar venta completa.

## 4. Principios UX

- La pantalla debe hablar en terminos comerciales: contado, anticipo, cuotas,
  refuerzos, saldo, interes directo e indexacion.
- La validacion visual debe anticipar errores antes de llamar al backend.
- La `Estructura del plan` es solo un borrador visual de bloques cargados; no es
  cronograma, no calcula cuotas reales y no reemplaza al backend.
- El `Preview oficial backend` es la unica fuente del cronograma visible; consume
  exclusivamente `POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview`.
- El prototipo no calcula fechas de cuotas, interes directo ni indexacion
  localmente para el preview oficial.
- El paso Plan Pago V2 muestra un campo `ID venta backend` visible para cargar
  una venta existente de la base DEV antes de usar preview/generate.
- Las acciones se presentan como flujo guiado: `1. Previsualizar plan`,
  `2. Generar plan de pago`, `3. Ver plan generado`.
- Preview y consulta integral son lectura/visualizacion; no prometen pago,
  caja, recibo ni emision posterior de cuotas indexadas.
- Una vez generado, el plan se presenta como estructura de consulta cerrada.

## 5. Flujo de pantalla

1. El usuario ingresa al prototipo o al detalle de una venta.
2. Selecciona `CONTADO` o `FINANCIADO`.
3. Carga bloques comerciales.
4. En cada `TRAMO_CUOTAS` elige `Metodo de liquidacion`.
5. La pantalla valida suma, campos requeridos y exclusividad de metodos.
6. El usuario informa `ID venta backend` con el ID de una venta existente en
   base DEV; si falta o es invalido, la UI muestra `Ingresá el ID de una venta
   backend existente para probar el plan.` y deja deshabilitadas las acciones
   backend.
7. `1. Previsualizar plan`: ejecuta preview oficial con `POST /preview` y muestra
   el cronograma calculado por backend.
8. `2. Generar plan de pago`: se habilita solo con preview oficial vigente;
   envia headers CORE-EF requeridos y, si responde OK, refresca
   `GET /api/v1/ventas/{id_venta}/plan-pago-v2`.
9. `3. Ver plan generado`: se habilita cuando ya se genero el plan o hay una
   consulta integral cargada para la venta.
10. Si cambia el `ID venta backend`, se limpia el preview oficial, la consulta
    integral y el estado de generate; se debe previsualizar nuevamente.
11. El paso final muestra checklist operativo: venta backend, preview oficial y
    plan generado.

## 6. Editor de bloques

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

### 6.1 Bloques de pago unico

Aplica a `CONTADO`, `ANTICIPO`, `REFUERZO` y `SALDO`.

Campos visibles:

- etiqueta;
- `importe_total_bloque`;
- `fecha_vencimiento`.

Conceptos esperados:

- `CONTADO` se materializa como item `SALDO` con `CAPITAL_VENTA`.
- `ANTICIPO` usa `ANTICIPO_VENTA`.
- `REFUERZO` y `SALDO` usan `CAPITAL_VENTA`.

### 6.2 TRAMO_CUOTAS: campos base

Campos visibles:

- etiqueta;
- `importe_total_bloque` / capital inicial del tramo;
- `cantidad_cuotas`;
- `fecha_primer_vencimiento`;
- `periodicidad = MENSUAL`;
- selector `Metodo de liquidacion`.

## 7. Metodo de liquidacion por TRAMO_CUOTAS

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

### 7.1 SIN_INTERES / legacy

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

### 7.2 INTERES_DIRECTO

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

### 7.3 INDEXACION

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

## 8. Validaciones UX

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

## 9. Preview oficial

La seccion local `Estructura del plan` muestra solo el borrador visual de los
bloques ingresados por el usuario. No debe llamarse `Cronograma preview`, no debe
calcular fechas de cuotas, no debe calcular interes directo, no debe calcular
indexacion y no debe inventar estados locales de indexacion.

La seccion `Preview oficial backend` es la unica fuente del cronograma. Sus
estados esperados son:

- sin venta backend: `Disponible cuando exista una venta backend asociada.` y
  pedido de ingresar un ID de venta backend existente;
- con venta backend sin preview: `Presioná Previsualizar plan para ver el
  cronograma calculado por backend.`;
- con borrador modificado: aviso `Preview desactualizado` y pedido de volver a
  previsualizar;
- con preview vigente: tabla renderizada exclusivamente desde las `obligaciones`
  devueltas por el backend.

La tabla de preview oficial debe mostrar:

```text
N° | Bloque | Tipo bloque | Etiqueta | Vencimiento | Capital cuota | Ajuste indexacion | Importe total | Estado indexacion | Concepto
```

Reglas:

- `CONTADO` genera una fila `SALDO`.
- `ANTICIPO` genera una fila `ANTICIPO`.
- Cada `TRAMO_CUOTAS` genera N filas `CUOTA`.
- `REFUERZO` genera una fila `REFUERZO`.
- `SALDO` genera una fila `SALDO`.
- El orden respeta el orden visual de bloques.

Para la columna `Capital cuota`, la UI muestra `capital_cuota` si viene
informado y usa `importe_total` como fallback visual cuando `capital_cuota` es
null. Para `INDEXACION`, `capital_cuota` sigue siendo la fuente principal y el
ajuste permanece separado en `ajuste_indexacion_cuota`; no se recalculan importes
localmente.

Para `INDEXACION`, la UI no inventa estados locales: muestra
`estado_preview_indexacion`, importes y ajustes tal como vienen en cada
obligacion del backend.

Resumen de preview:

- `total_calculado`;
- `total_con_interes`;
- `total_con_indexacion`;
- `total_ajuste_indexacion`.

## 10. Generate

Accion guiada:

```text
2. Generar plan de pago
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

## 11. Consulta integral posterior

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

## 12. CORE-EF

Decision UX/prototipo:

- La UI/prototipo no modifica endpoint write ni contratos backend.
- `POST /preview`: `PREVIEW_READLIKE`; no fuerza headers write.
- `GET /plan-pago-v2`: `QUERY_READLIKE`; no fuerza headers write.
- `POST /generar`: `COMMAND_WRITE_NEGOCIO` existente; el prototipo envia los
  headers CORE-EF requeridos por backend.
- Idempotencia, outbox, lock logico, versionado y rollback se consideran
  responsabilidad del backend existente; la UI no declara cumplimiento profundo
  sin evidencia de router/service/repository/SQL/tests.

## 13. Fuera de alcance

Queda explicitamente fuera de alcance:

- pagos;
- caja;
- recibos fiscales persistidos;
- documental real;
- emision posterior de cuotas indexadas;
- cambios SQL;
- cambios backend;
- cambios de reglas financieras.

## 14. Criterios de aceptacion UX

- El usuario puede construir un plan contado sin ver campos tecnicos.
- El usuario puede construir un plan financiado con anticipo, tramos, refuerzos
  y saldo.
- Cada `TRAMO_CUOTAS` permite elegir `SIN_INTERES`, `INTERES_DIRECTO` o
  `INDEXACION`.
- La UI impide mezclar `INTERES_DIRECTO` e `INDEXACION` en el mismo bloque.
- La pantalla bloquea confirmacion si la suma no coincide.
- La `Estructura del plan` queda limitada a borrador visual local.
- Las acciones backend aparecen guiadas como `1. Previsualizar plan`,
  `2. Generar plan de pago`, `3. Ver plan generado`.
- Sin `ID venta backend` valido, la UI explica el prerequisito y deshabilita
  preview/generate/ver plan.
- Al cambiar el `ID venta backend`, se descartan preview oficial, consulta
  integral y generate previos para evitar mezclar respuestas de otra venta.
- El `Preview oficial backend` es la unica fuente del cronograma y muestra
  capital, ajuste de indexacion, importe total, estado de indexacion y concepto
  desde la respuesta backend.
- Si `capital_cuota` viene null, la columna `Capital cuota` usa `importe_total`
  como fallback visual sin recalcular importes.
- El prototipo no calcula fechas, interes directo ni indexacion localmente para
  el preview oficial.
- Generate envia headers CORE-EF.
- La consulta integral muestra cabecera, bloques, indexacion, obligaciones,
  composiciones y resumen.
- No hay acciones de pago, caja ni recibo.
