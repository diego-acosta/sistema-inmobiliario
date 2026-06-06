# AUDITORIA-PREVIEW-PLAN-PAGO-V2-WIZARD-VENTA-COMPLETA

## 1. Resumen ejecutivo

Esta auditoría revisa el soporte backend actual de preview/simulación de Plan Pago V2 por bloques para definir si puede ser consumido por el Wizard Venta Completa V3 **antes de confirmar** una venta financiada.

Conclusión: **Opción B**.

El endpoint actual existe y la simulación interna es read-like, no persiste plan, venta ni obligaciones, y ya calcula cronograma simulado para `SIN_INTERES`, `INTERES_DIRECTO`, `INDEXACION`, anticipo, contado, tramos, saldo y cuotas_refuerzo internas. Sin embargo, el contrato HTTP público vigente está montado bajo una venta existente:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview
```

Por esa razón **no debe integrarse como endpoint objetivo del Wizard Venta Completa V3 antes de crear/persistir la venta**, porque el wizard todavía no tiene `id_venta` real y no debe inventar un identificador para cumplir una ruta que semánticamente pertenece a una venta persistida.

Se recomienda crear un endpoint nuevo de preview sin venta persistida:

```text
POST /api/v1/ventas/plan-pago-v2/preview
```

El endpoint nuevo debería reutilizar el mismo motor de preview, aceptar el mismo cuerpo `plan_pago_v2` sin `id_venta` en path ni body, devolver simulación sin side effects y mantener clasificación CORE-EF `PREVIEW_READLIKE`.

## 2. Alcance y fuentes revisadas

### 2.1 Implementación revisada

- Servicio de simulación: `backend/app/application/comercial/services/build_plan_pago_venta_v2_por_bloques_preview_service.py`.
- Router comercial: `backend/app/api/routers/comercial_router.py`.
- Schemas API comerciales: `backend/app/api/schemas/comercial.py`.
- Command de Plan Pago V2 por bloques: `backend/app/application/comercial/commands/generate_plan_pago_venta_v2_por_bloques.py`.
- Consulta de índices: `backend/app/application/financiero/services/indexacion_cuota_calculator.py` y `backend/app/infrastructure/persistence/repositories/indice_financiero_repository.py`.
- Tests específicos: `backend/tests/test_plan_pago_venta_v2_bloques_preview.py`.

### 2.2 Documentación revisada

- `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`.
- `backend/documentacion/DEV-SRV/dominios/comercial/MODELO-PLANES-PAGO-VENTA-BLOQUES.md`.
- `backend/documentacion/DEV-SRV/dominios/comercial/DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`.
- `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-014-plan-financiero-venta.md`.
- `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-METODOS-LIQUIDACION-PLAN-PAGO-V2.md`.
- `backend/documentacion/DEV-SRV/dominios/financiero/METODO-PLAN-PAGO-INTERES-DIRECTO.md`.
- `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-METODO-LIQUIDACION-INDEXACION-PLAN-PAGO-V2.md`.
- `backend/documentacion/DEV-SRV/dominios/financiero/AUDITORIA-CUOTAS-REFUERZO-INTERNAS-PLAN-PAGO-V2.md`.

## 3. Clasificación arquitectónica

| Concepto | Clasificación | Dominio dueño | Observación |
| --- | --- | --- | --- |
| Venta, reserva, compradores y objetos de venta | núcleo del dominio | comercial | El wizard arma una operación de compraventa. |
| `plan_pago_venta` y `plan_pago_venta_bloque` | núcleo del dominio | comercial | Cabecera y estructura comercial de negociación del plan. |
| Preview/simulación de plan | soporte de decisión UI / read-like | comercial con cálculo financiero consumido | No debe materializar venta ni obligaciones. |
| `obligacion_financiera` | núcleo del dominio | financiero | En preview son solo obligaciones simuladas, no filas persistidas. |
| `composicion_obligacion` | soporte financiero | financiero | En preview actual no se devuelve una lista de composiciones simuladas por obligación. |
| Índices financieros | núcleo/soporte financiero según catálogo | financiero | El preview puede leer valores publicados, sin persistir ni modificar índices. |
| Outbox, locks, idempotencia command | soporte transversal técnico | transversal | No aplica al preview si no persiste. |

La integración objetivo no mueve ownership: el frontend comercial no calcula cronograma, interés directo, indexación ni obligaciones. Solo envía la forma de pago al backend y presenta el resultado simulado.

## 4. Endpoint HTTP existente hoy

### 4.1 Ruta

Existe el endpoint:

```text
POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview
```

Handler:

```text
preview_plan_pago_venta_v2_por_bloques
```

Response model:

```text
PreviewPlanPagoVentaV2PorBloquesResponse
```

### 4.2 Naturaleza del endpoint actual

- Es un preview/simulación, no un command de persistencia.
- No exige headers CORE-EF write (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) en el router actual.
- No exige `If-Match-Version`.
- Construye un command con `id_venta` recibido por path.
- Instancia `BuildPlanPagoVentaV2PorBloquesPreviewService` con `IndiceFinancieroRepository(db)` para poder consultar índices publicados.
- Si el servicio retorna error funcional, responde HTTP 400 con `ErrorResponse` y `details.errors`.
- Si Pydantic rechaza el payload por schema, FastAPI responde 422.
- Si ocurre excepción no controlada, responde 500 con `ErrorResponse`.

## 5. Payload esperado por el endpoint actual

El body corresponde a `PreviewPlanPagoVentaV2PorBloquesRequest`, que hereda de `GeneratePlanPagoVentaV2PorBloquesRequest`.

### 5.1 Cabecera

```json
{
  "tipo_pago": "FINANCIADO",
  "monto_total_plan": "12700000.00",
  "moneda": "ARS",
  "bloques": [],
  "observaciones": "opcional"
}
```

Campos:

| Campo | Tipo | Requerido | Observación |
| --- | --- | --- | --- |
| `tipo_pago` | string | sí | Valores funcionales soportados por validación: `CONTADO` o `FINANCIADO`. |
| `monto_total_plan` | decimal | sí | Debe ser mayor a cero y coincidir con la suma de bloques por capital. |
| `moneda` | string | no | Default API: `ARS`; el backend normaliza a upper/strip en la respuesta. |
| `bloques` | array | sí | Lista no vacía de bloques. |
| `observaciones` | string | no | Texto libre de cabecera. |

El schema tiene `extra="forbid"`, por lo que no acepta campos internos como `id_plan_pago_venta`.

### 5.2 Bloque `CONTADO`

```json
{
  "tipo_bloque": "CONTADO",
  "importe_total_bloque": "12000000.00",
  "fecha_vencimiento": "2026-07-10"
}
```

Uso: `tipo_pago = CONTADO`, un único bloque `CONTADO`, una obligación simulada tipo `SALDO` con concepto `CAPITAL_VENTA`.

### 5.3 Bloque `ANTICIPO`

```json
{
  "tipo_bloque": "ANTICIPO",
  "importe_total_bloque": "2000000.00",
  "fecha_vencimiento": "2026-07-10"
}
```

Uso: dentro de `tipo_pago = FINANCIADO`, genera una obligación simulada tipo `ANTICIPO` con concepto `ANTICIPO_VENTA`.

### 5.4 Bloque `TRAMO_CUOTAS` sin interés

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "importe_total_bloque": "10000000.00",
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-08-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "SIN_INTERES"
}
```

Notas:

- `metodo_liquidacion` puede omitirse y el servicio asume `SIN_INTERES`.
- Si se informa `importe_total_bloque`, el backend calcula `importe_cuota` y ajusta la última cuota por redondeo.
- El contrato legacy por `importe_cuota` también sigue funcionando.

### 5.5 Bloque `TRAMO_CUOTAS` con interés directo

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "importe_total_bloque": "10000000.00",
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-08-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INTERES_DIRECTO",
  "tasa_interes_directo_periodica": "0.02",
  "cantidad_periodos": 6,
  "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE"
}
```

Reglas auditadas:

- Solo aplica a `TRAMO_CUOTAS`.
- Requiere `tasa_interes_directo_periodica`, `cantidad_periodos` y `base_calculo_interes`.
- La base válida implementada es `CAPITAL_INICIAL_BLOQUE`.
- No permite mezclar configuración de indexación en el mismo bloque.
- Devuelve `total_con_interes` a nivel raíz de la respuesta preview y devuelve los parámetros de interés directo en cada bloque. El contrato actual no expone `total_con_interes` por bloque.

### 5.6 Bloque `TRAMO_CUOTAS` con indexación

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "importe_total_bloque": "3000.00",
  "cantidad_cuotas": 3,
  "fecha_primer_vencimiento": "2026-08-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INDEXACION",
  "id_indice_financiero": 1,
  "fecha_base_indice": "2026-05-01",
  "valor_base_indice": "100.00000000",
  "modo_indexacion": "POR_COEFICIENTE",
  "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
  "tipo_generacion_indexada": "DEFINITIVA",
  "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
  "conserva_capital_original": true,
  "genera_ajuste_por_diferencia": true
}
```

Reglas auditadas:

- Solo aplica a `TRAMO_CUOTAS`.
- Requiere índice, fecha base, valor base, modo, base de cálculo, tipo de generación, política de valor no disponible y flags de conservación/ajuste.
- La implementación vigente soporta `POR_COEFICIENTE`, `CAPITAL_INICIAL_BLOQUE`, `DEFINITIVA`, `ERROR_SI_NO_EXISTE`, `conserva_capital_original = true` y `genera_ajuste_por_diferencia = true`.
- No permite mezclar configuración de interés directo en el mismo bloque.
- Si hay índice publicado aplicable, devuelve cuota con `CON_INDICE_APLICADO`, coeficiente, valor aplicado y ajuste.
- Si no hay índice publicado aplicable, devuelve cuota `PROYECTADA_SIN_INDICE` y mantiene el capital sin inventar valor aplicado.

### 5.7 Cuotas_refuerzo internas

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "importe_total_bloque": "24000000.00",
  "cantidad_cuotas": 24,
  "fecha_primer_vencimiento": "2026-01-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "SIN_INTERES",
  "cuotas_refuerzo": [
    {
      "numero_cuota": 6,
      "etiqueta": "Refuerzo cuota 6",
      "unidades_refuerzo": "1.00"
    },
    {
      "numero_cuota": 12,
      "etiqueta": "Refuerzo cuota 12",
      "unidades_refuerzo": "1.00"
    }
  ]
}
```

Reglas auditadas:

- `cuotas_refuerzo` solo aplica a `TRAMO_CUOTAS`.
- `numero_cuota` debe estar dentro de `1..cantidad_cuotas`.
- No puede repetirse el mismo `numero_cuota`.
- `unidades_refuerzo` debe ser positiva y actualmente solo se soporta `1.00` cuando se informa.
- No agrega obligaciones extras; marca determinadas posiciones del tramo como `REFUERZO` dentro de la misma secuencia de obligaciones simuladas.

## 6. Respuesta actual del preview

El endpoint devuelve:

```json
{
  "ok": true,
  "data": {
    "id_venta": 1,
    "metodo_plan_pago": "PLAN_POR_BLOQUES",
    "tipo_pago": "FINANCIADO",
    "moneda": "ARS",
    "monto_total_plan": "10000000.00",
    "total_calculado": "10000000.00",
    "total_con_interes": "11200000.00",
    "total_con_indexacion": "11200000.00",
    "total_ajuste_indexacion": "0.00",
    "diferencia": "0.00",
    "bloques": [],
    "obligaciones": [],
    "redondeos": []
  }
}
```

### 6.1 Datos de bloques devueltos

Cada bloque simulado devuelve, entre otros:

- `numero_bloque`.
- `tipo_bloque`.
- `etiqueta_bloque`.
- `cantidad_cuotas`.
- `importe_total_bloque`.
- `importe_cuota`.
- `fecha_vencimiento`.
- `fecha_primer_vencimiento`.
- `periodicidad`.
- `regla_redondeo`.
- `metodo_liquidacion`.
- campos de interés directo.
- campos de indexación.
- `total_con_indexacion`.
- `total_ajuste_indexacion`.
- cantidad de cuotas con índice y proyectadas sin índice.
- `concepto_financiero_codigo`.

Los bloques **no** exponen hoy `total_con_interes` por bloque. Ese total existe en la raíz de la respuesta preview como total agregado del plan. Si el Wizard V3 necesitara mostrar total con interés por tramo/bloque, debería tratarse como una brecha futura/mejora de contrato y no como comportamiento actual.

### 6.2 Obligaciones/cuotas simuladas devueltas

Cada obligación simulada devuelve, entre otros:

- `numero_obligacion`.
- `numero_bloque`.
- `tipo_bloque`.
- `tipo_item_cronograma` (`ANTICIPO`, `CUOTA`, `REFUERZO`, `SALDO`).
- `etiqueta_obligacion`.
- `item_numero`.
- `fecha_vencimiento`.
- `importe_total`.
- `moneda`.
- `concepto_financiero_codigo`.
- `numero_cuota_asociada` para tramos.
- campos de indexación por cuota cuando aplica.

### 6.3 Composiciones

El preview actual **no devuelve una lista de composiciones simuladas por obligación** con estructura equivalente a `composicion_obligacion`.

Lo que sí devuelve es `concepto_financiero_codigo` por bloque y obligación, lo cual permite explicar el concepto principal (`CAPITAL_VENTA` o `ANTICIPO_VENTA`) pero no reemplaza una composición financiera detallada.

Para el Wizard V3, si la UI necesita mostrar desglose por composición, el endpoint nuevo debería agregar una estructura read-like explícita, por ejemplo:

```json
"composiciones": [
  {
    "orden_composicion": 1,
    "codigo_concepto_financiero": "CAPITAL_VENTA",
    "importe_componente": "1000.00",
    "moneda_componente": "ARS"
  }
]
```

Esa ampliación debe ser solo simulada y no debe persistir `composicion_obligacion`.

## 7. Respuestas a preguntas de auditoría

| # | Pregunta | Respuesta |
| --- | --- | --- |
| 1 | Qué endpoint HTTP existe hoy para preview de Plan Pago V2. | `POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview`. |
| 2 | Qué payload espera. | `tipo_pago`, `monto_total_plan`, `moneda`, `bloques`, `observaciones`; cada bloque acepta tipo, importes, fechas, cuotas, método de liquidación, interés directo, indexación y `cuotas_refuerzo`. |
| 3 | Si requiere `id_venta` existente. | A nivel HTTP sí requiere `id_venta` en la ruta. La implementación auditada no valida existencia de venta antes de simular, pero el contrato público presupone un identificador de venta. |
| 4 | Si puede usarse antes de crear/persistir la venta. | No como endpoint objetivo del Wizard V3. Técnicamente no persiste, pero semánticamente requiere `{id_venta}` y devuelve `id_venta`; usar un dummy sería inválido. |
| 5 | Si acepta `monto_total_plan`, `moneda` y bloques sin `id_venta` real. | El body sí acepta esos campos sin ids internos; la ruta no permite omitir `id_venta`. |
| 6 | Si soporta `cuotas_refuerzo` internas. | Sí, para `TRAMO_CUOTAS`, con validaciones de rango, duplicados y unidades. |
| 7 | Si devuelve obligaciones/cuotas simuladas. | Sí, devuelve `obligaciones` simuladas con número, bloque, tipo item, vencimiento, importe, moneda y datos de indexación cuando aplica. |
| 8 | Si devuelve composiciones. | Parcial/no. Devuelve `concepto_financiero_codigo`, pero no lista `composiciones` simuladas por obligación. |
| 9 | Si devuelve datos de interés directo. | Sí, en bloques (`metodo_liquidacion`, `tasa_interes_directo_periodica`, `cantidad_periodos`, `base_calculo_interes`) y en totales (`total_con_interes`). |
| 10 | Si devuelve datos de indexación. | Sí, en bloques y obligaciones: estado, índice, valor base, valor aplicado, coeficiente, capital, ajuste y totales. |
| 11 | Si devuelve errores funcionales útiles para UI. | Sí parcialmente. Errores del servicio salen como HTTP 400 `APPLICATION_ERROR` con `details.errors`; errores de schema salen como 422; excepciones no controladas serían 500. |
| 12 | Si el preview hace lecturas de índices reales o solo usa valores base enviados. | Hace lecturas read-only de índices publicados cuando se inyecta `IndiceFinancieroRepository`; si no encuentra valor aplicable, proyecta sin inventar índice usando el capital/base enviada. |
| 13 | Si el preview tiene side effects o es puramente read-like. | Es read-like para plan/venta/obligaciones. Los tests verifican que no persiste plan, bloques, generación, obligaciones, composiciones ni obligados. La consulta de índices es solo lectura. |
| 14 | Qué necesita el Wizard V3 para consumirlo. | Un endpoint sin `id_venta`, payload derivado de `plan_pago_v2` del wizard, respuesta con cronograma simulado, errores UI-friendly y, si se requiere, composiciones simuladas explícitas. |
| 15 | Si hace falta un endpoint nuevo de preview de venta completa sin persistir. | Sí. Se recomienda `POST /api/v1/ventas/plan-pago-v2/preview` como mínimo para plan; si el wizard necesita validar toda la venta en conjunto, un preview de venta completa puede ser una etapa posterior. |

## 8. Soporte funcional auditado

| Funcionalidad | Estado actual | Observación |
| --- | --- | --- |
| `SIN_INTERES` | soportado | Default cuando no se informa `metodo_liquidacion`; genera cuotas por capital. |
| `INTERES_DIRECTO` | soportado en preview | Calcula `total_con_interes` agregado a nivel raíz sobre `CAPITAL_INICIAL_BLOQUE` y propaga parámetros del método en el bloque; no expone `total_con_interes` por bloque. |
| `INDEXACION` | soportado en preview | Consulta índice publicado y calcula ajuste; si no hay índice, marca `PROYECTADA_SIN_INDICE`. |
| Cuotas_refuerzo internas | soportado | Dentro de `TRAMO_CUOTAS`; no agrega cuotas, convierte posiciones en `REFUERZO`. |
| Anticipo | soportado | Bloque `ANTICIPO`, obligación simulada con `ANTICIPO_VENTA`. |
| Contado | soportado | `tipo_pago=CONTADO` con bloque `CONTADO`, obligación simulada tipo `SALDO`. |
| Tramos | soportado | Uno o más bloques `TRAMO_CUOTAS`; permite planes mixtos. |
| Composiciones | parcial/no | No hay array de composiciones simuladas; solo concepto principal. |
| Obligaciones simuladas | soportado | Lista `obligaciones` en response. |
| Errores funcionales | parcial | 400 con `details.errors` para errores del servicio; 422 para schema; debe cuidarse no convertir payload inválido en 500. |

## 9. Diseño objetivo para Wizard Venta Completa V3

La UI debe poder solicitar simulación real antes de confirmar:

- sin crear venta;
- sin crear obligaciones;
- sin persistir relación generadora;
- sin outbox;
- sin modificar disponibilidad;
- sin modificar objetos;
- sin registrar compradores;
- sin calcular cronograma, interés directo, indexación ni obligaciones localmente.

### 9.1 Endpoint mínimo sugerido

```text
POST /api/v1/ventas/plan-pago-v2/preview
```

Naturaleza:

```text
PREVIEW_READLIKE
```

Body: igual a `PreviewPlanPagoVentaV2PorBloquesRequest`, sin `id_venta` en path ni body.

Response sugerida:

- Debe mantener `metodo_plan_pago`, `tipo_pago`, `moneda`, `monto_total_plan`, totales, bloques, obligaciones y redondeos.
- Debe eliminar `id_venta` o devolverlo como `null`/no presente para evitar fingir venta persistida.
- Debe agregar `composiciones` simuladas por obligación si el Wizard V3 necesita mostrar desglose financiero equivalente al alta real.
- Debe conservar errores funcionales en formato estándar `ErrorResponse`.

### 9.2 Payload desde el wizard

El Wizard V3 puede mapear su estado interno de forma de pago a:

```json
{
  "tipo_pago": "FINANCIADO",
  "monto_total_plan": "24000000.00",
  "moneda": "ARS",
  "bloques": [
    {
      "tipo_bloque": "ANTICIPO",
      "importe_total_bloque": "4000000.00",
      "fecha_vencimiento": "2026-07-10"
    },
    {
      "tipo_bloque": "TRAMO_CUOTAS",
      "importe_total_bloque": "20000000.00",
      "cantidad_cuotas": 24,
      "fecha_primer_vencimiento": "2026-08-10",
      "periodicidad": "MENSUAL",
      "metodo_liquidacion": "SIN_INTERES",
      "cuotas_refuerzo": [
        {
          "numero_cuota": 12,
          "etiqueta": "Refuerzo interno",
          "unidades_refuerzo": "1.00"
        }
      ]
    }
  ]
}
```

La UI debe tratar la respuesta como simulación no confirmada y debe volver a confirmar contra backend al crear la venta, porque la disponibilidad, compradores, índices y condiciones pueden cambiar entre preview y confirmación.

### 9.3 ¿Endpoint de preview de venta completa?

No es obligatorio para resolver la necesidad mínima de cronograma de Plan Pago V2, pero puede ser necesario si el Wizard V3 quiere validar una venta completa antes de confirmar, incluyendo:

- consistencia entre suma de `precio_asignado` de objetos y `monto_total_plan`;
- compradores y porcentajes;
- origen reserva/directa;
- disponibilidad informativa de objetos;
- resumen comercial + plan simulado en una única respuesta.

Si se implementa, debería ser otro endpoint `PREVIEW_READLIKE`, por ejemplo:

```text
POST /api/v1/ventas-completas-v3/preview
```

Ese endpoint debería orquestar validaciones read-only y reutilizar el preview de Plan Pago V2 internamente, sin persistir entidades ni reservar disponibilidad.

## 10. Decisión CORE-EF

Clasificación del endpoint actual y del endpoint sugerido:

```text
PREVIEW_READLIKE
```

| Aspecto CORE-EF | Decisión |
| --- | --- |
| Headers write (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) | NO APLICA: preview no persiste ni sincroniza command de negocio. |
| `If-Match-Version` | NO APLICA: no modifica entidad existente/versionada. |
| Idempotencia command | NO APLICA: no hay escritura; mismas entradas deberían producir misma simulación salvo cambios read-only de índices publicados. |
| Outbox | NO APLICA: no hay evento de negocio ni transacción de escritura. |
| Lock lógico | NO APLICA: no bloquea venta, objetos, disponibilidad ni obligaciones. |
| Versionado | NO APLICA: no modifica `version_registro`. |
| Rollback/transacción | NO APLICA para negocio: no hay frontera transaccional de escritura. Si consulta índices, la operación es read-only. |
| Errores | Debe devolver `ErrorResponse` funcional para validaciones y nunca 500 por payload inválido esperado. |

## 11. Tests futuros recomendados

Para el endpoint nuevo sin `id_venta`:

1. Preview sin `id_venta` con `SIN_INTERES`.
2. Preview sin `id_venta` con `INTERES_DIRECTO`.
3. Preview sin `id_venta` con `INDEXACION`.
4. Preview sin `id_venta` con `cuotas_refuerzo` internas.
5. Preview no persiste venta.
6. Preview no persiste `plan_pago_venta` ni `plan_pago_venta_bloque`.
7. Preview no persiste `relacion_generadora`.
8. Preview no persiste `generacion_cronograma_financiero`.
9. Preview no persiste `obligacion_financiera`.
10. Preview no persiste `composicion_obligacion`.
11. Preview no persiste `obligacion_obligado`.
12. Preview no genera outbox.
13. Payload inválido devuelve error controlado (`ErrorResponse` o 422 de schema, según capa) y no 500.
14. Indexación con índice publicado lee datos reales read-only y devuelve `CON_INDICE_APLICADO`.
15. Indexación sin índice publicado no inventa valores y devuelve `PROYECTADA_SIN_INDICE`.

## 12. Riesgos y restricciones

- No usar el endpoint actual con `id_venta=0`, `id_venta=-1` o un dummy desde el Wizard V3. Aunque el servicio no valide existencia, esa integración contradice la semántica del path.
- No trasladar cálculo financiero al frontend.
- No persistir venta para poder previsualizar y luego descartarla.
- No generar obligaciones ni relación generadora en preview.
- No emitir outbox ni modificar disponibilidad en preview.
- No declarar composiciones completas en UI si el backend solo devuelve `concepto_financiero_codigo`.

## 13. Conclusión

El backend ya tiene un motor de preview útil y cubierto por tests para Plan Pago V2 por bloques, incluyendo interés directo, indexación, tramos y cuotas_refuerzo internas. La limitación principal no está en el cálculo sino en el contrato HTTP público actual: exige `{id_venta}` en la ruta y devuelve `id_venta`, lo que lo vuelve inadecuado como integración directa del Wizard Venta Completa V3 antes de confirmar.

Decisión final: **Opción B**.

Implementar un endpoint nuevo sin venta persistida:

```text
POST /api/v1/ventas/plan-pago-v2/preview
```

El nuevo endpoint debe reutilizar el servicio de preview, mantener naturaleza `PREVIEW_READLIKE`, no exigir headers write, no persistir entidades, no generar outbox, leer índices solo de forma read-only y devolver errores funcionales útiles para UI.
