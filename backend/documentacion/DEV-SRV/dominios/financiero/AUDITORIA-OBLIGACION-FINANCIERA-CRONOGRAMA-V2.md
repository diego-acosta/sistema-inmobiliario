# AUDITORIA-OBLIGACION-FINANCIERA-CRONOGRAMA-V2

## Objetivo

Auditar si `obligacion_financiera` y sus tablas relacionadas soportan el rol de
cronograma V2 de planes de pago de venta, bajo las decisiones congeladas del
modelo V2 documentado en `MODELO-PLANES-PAGO-VENTA.md`.

## Alcance y restricciones

Esta auditoria es documental y de lectura de implementacion existente.

Este documento no implementa cambios SQL ni backend, no migra datos y no
elimina `venta_plan_cuota`. La version original de la auditoria analizaba
brechas antes de materializar V2; la actualizacion 2026-05-14 registra el
estado ya implementado en SQL/codigo/tests para el minimo
`CUOTAS_IGUALES_SIMPLE`.

Actualizacion 2026-05-14:

- el backend minimo para `CUOTAS_IGUALES_SIMPLE V2` ya esta implementado
- existe `plan_pago_venta` como cabecera/regla comercial
- existe `generacion_cronograma_financiero` como corrida tecnica/idempotente
- `obligacion_financiera` ya materializa los campos minimos V2:
  `id_generacion_cronograma_financiero`, `numero_obligacion`,
  `tipo_item_cronograma`, `etiqueta_obligacion` y `clave_funcional_origen`
- el endpoint implementado es
  `POST /api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`
- esta actualizacion no cambia el alcance historico de la auditoria; deja
  documentado que varias brechas senaladas abajo fueron resueltas para el caso
  V2 inicial

Clasificacion arquitectonica:

- cronograma financiero exigible/proyectado: nucleo financiero
- regla comercial de plan de pago de venta: nucleo comercial
- `venta_plan_cuota`: compatibilidad heredada V1 para `CUOTAS_FIJAS`
- `composicion_obligacion` y `obligacion_obligado`: soporte financiero de la
  obligacion

## Fuentes revisadas

- SQL: `backend/database/schema_inmobiliaria_20260418.sql`
- Seeds/catalogos: `backend/database/seed_minimo.sql`,
  `backend/database/seed_test_baseline.sql`
- Servicio de venta confirmada:
  `backend/app/application/financiero/services/handle_venta_confirmada_event_service.py`
- Repositorio financiero:
  `backend/app/infrastructure/persistence/repositories/financiero_repository.py`
- Servicio generico de obligacion:
  `backend/app/application/financiero/services/create_obligacion_financiera_service.py`
- Schemas/API financiero: `backend/app/api/schemas/financiero.py`
- Tests financieros/comerciales relacionados:
  - `backend/tests/test_fin_event_venta_confirmada.py`
  - `backend/tests/test_fin_estado_cuenta.py`
  - `backend/tests/test_fin_estado_cuenta_persona.py`
  - `backend/tests/test_fin_registrar_pago_persona.py`
  - `backend/tests/test_fin_regenerar_cronograma.py`
  - `backend/tests/test_ventas_definir_condiciones_comerciales.py`
  - `backend/tests/test_ventas_detalle_integral.py`
- Documentacion:
  - `backend/documentacion/DEV-SRV/dominios/comercial/MODELO-PLANES-PAGO-VENTA.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-003-generacion-de-obligaciones.md`
  - `backend/documentacion/DEV-SRV/dominios/financiero/MODELO-FINANCIERO-FIN.md`
  - `backend/documentacion/DEV-API/dominios/financiero/DEV-API-FIN-001.md`
  - `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`

## Diagnostico ejecutivo

`obligacion_financiera` ya puede representar deudas/proyecciones con monto,
vencimiento, estado, relacion generadora, composiciones y obligados. Tambien ya
acepta `PROYECTADA` en SQL y el flujo de venta confirmada crea obligaciones de
venta en estado `PROYECTADA`.

Para `CUOTAS_IGUALES_SIMPLE V2`, la estructura actual ya incorpora el minimo
requerido: orden estable del item de cronograma, etiqueta estable para UI y
reportes, clave funcional/idempotente por item y referencia a la corrida en
`generacion_cronograma_financiero`.

Para metodos futuros como `ANTICIPO_MAS_CUOTAS_IGUALES` o
`CRONOGRAMA_DEFINIDO`, siguen pendientes reglas especificas de negocio,
validacion, reemplazo y distribucion de obligados.

La unicidad vigente `(id_relacion_generadora, periodo_desde, periodo_hasta)` es
util para cronogramas periodicos locativos, pero no alcanza para venta V2: en
ventas confirmadas actuales `periodo_desde` y `periodo_hasta` quedan nulos, y
varios items pueden compartir vencimiento o no tener un periodo mensual natural.

## Estructura actual de `obligacion_financiera`

Columnas reales en SQL:

| Columna | Tipo SQL | Observacion para cronograma V2 |
| --- | --- | --- |
| `id_obligacion_financiera` | `bigint` | PK tecnica |
| `uid_global` | `uuid` | identificador global tecnico |
| `version_registro` | `integer` | version core EF |
| `created_at` | `timestamp without time zone` | auditoria |
| `updated_at` | `timestamp without time zone` | auditoria |
| `deleted_at` | `timestamp without time zone` | baja logica |
| `id_instalacion_origen` | `bigint` | core EF |
| `id_instalacion_ultima_modificacion` | `bigint` | core EF |
| `op_id_alta` | `uuid` | trazabilidad operacion |
| `op_id_ultima_modificacion` | `uuid` | trazabilidad operacion |
| `id_relacion_generadora` | `bigint` | vinculo con origen financiero |
| `codigo_obligacion_financiera` | `varchar(50)` | existe, pero no se carga en generacion de venta confirmada |
| `descripcion_operativa` | `text` | existe, pero hoy funciona como texto libre/nulo en generacion comun |
| `fecha_generacion` | `timestamp without time zone` | default SQL |
| `fecha_emision` | `date` | NOT NULL |
| `fecha_vencimiento` | `date` | vencimiento financiero |
| `periodo_desde` | `date` | usado en cronogramas periodicos, no en venta confirmada actual |
| `periodo_hasta` | `date` | usado en cronogramas periodicos, no en venta confirmada actual |
| `fecha_cierre` | `timestamp without time zone` | cierre financiero |
| `importe_total` | `numeric(14,2)` | total de obligacion |
| `saldo_pendiente` | `numeric(14,2)` | saldo vigente |
| `importe_cancelado_acumulado` | `numeric(14,2)` | default 0 |
| `importe_bonificado_acumulado` | `numeric(14,2)` | default 0 |
| `importe_anulado_acumulado` | `numeric(14,2)` | default 0 |
| `moneda` | `varchar(10)` | default `ARS` |
| `estado_obligacion` | `varchar(30)` | estado financiero validado por constraint |
| `es_exigible` | `boolean` | flag operativo default false |
| `es_proyectada` | `boolean` | flag operativo default false; no se sincroniza automaticamente por constraint |
| `es_emitida` | `boolean` | flag operativo default false; no se sincroniza automaticamente por constraint |
| `es_vencida` | `boolean` | flag operativo default false; no se sincroniza automaticamente por constraint |
| `genera_recibo` | `boolean` | default true |
| `afecta_estado_cuenta` | `boolean` | default true |
| `afecta_libre_deuda` | `boolean` | default true |
| `id_obligacion_reemplazada` | `bigint` | trazabilidad de reemplazo |
| `id_obligacion_reemplazante` | `bigint` | trazabilidad de reemplazo |
| `motivo_reemplazo` | `text` | motivo libre de reemplazo |
| `observaciones` | `text` | texto libre |
| `id_generacion_cronograma_financiero` | `bigint` | referencia tecnica a la corrida V2 |
| `numero_obligacion` | `integer` | orden funcional del item de cronograma V2 |
| `tipo_item_cronograma` | `varchar` | tipo funcional del hito, por ejemplo `CUOTA` |
| `etiqueta_obligacion` | `varchar` | etiqueta estable para UI/reportes |
| `clave_funcional_origen` | `varchar` | clave idempotente por item de cronograma |

Tablas relacionadas relevantes:

- `composicion_obligacion` guarda el desglose por concepto financiero,
  `orden_composicion`, importes/saldos por componente, moneda y detalle de
  calculo/observaciones.
- `obligacion_obligado` guarda persona obligada, rol financiero y porcentaje de
  responsabilidad.

## Estados actuales

El constraint `chk_obligacion_estado` permite actualmente:

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `CANCELADA`
- `VENCIDA`
- `ANULADA`
- `REEMPLAZADA`
- `PENDIENTE_AJUSTE`

`PROYECTADA` existe en SQL, en el servicio generico de creacion de obligaciones,
en el flujo financiero de venta confirmada y en tests de estado de cuenta/venta
confirmada. A la vez, otros flujos financieros documentados e implementados
crean obligaciones `EMITIDA`, especialmente traslados, recuperos y cronogramas
locativos.

Brecha menor: los flags `es_proyectada`, `es_emitida`, `es_exigible` y
`es_vencida` existen en SQL, pero la implementacion revisada decide el estado por
`estado_obligacion` y no valida ni sincroniza esos flags como fuente funcional
principal.

## Vinculo actual de obligacion con origen venta/cuota

El vinculo canonico con venta es indirecto:

1. `relacion_generadora.tipo_origen = 'venta'`
2. `relacion_generadora.id_origen = venta.id_venta`
3. `obligacion_financiera.id_relacion_generadora`

Para `CUOTAS_FIJAS` V1, el servicio financiero lee `venta_plan_cuota` desde el
repositorio, ordena por `numero_cuota`, valida secuencia 1..N y crea una
obligacion por cuota con composicion `CAPITAL_VENTA`.

No existe en `obligacion_financiera` una columna de referencia directa a
`venta_plan_cuota.id_venta_plan_cuota`. Tampoco se persiste hoy el
`numero_cuota` en la obligacion generada. Por lo tanto, la trazabilidad V1 ->
obligacion queda inferida por venta, importe, vencimiento, orden de generacion y
concepto, no por clave formal.

## Orden actual del cronograma

El orden actual depende del contexto de consulta:

- lectura de `venta_plan_cuota`: `ORDER BY numero_cuota ASC`
- obligaciones activas por relacion generadora: `ORDER BY id_obligacion_financiera ASC`
- estado de cuenta financiero/persona: `ORDER BY fecha_vencimiento ASC NULLS LAST,
  id_obligacion_financiera ASC`
- tests de cuotas fijas/anticipo y saldo: ordenan por `fecha_vencimiento ASC`
- regeneracion locativa: usa `periodo_desde ASC, id_obligacion_financiera ASC`

Para cronogramas V2 ya existen `numero_obligacion`, `tipo_item_cronograma`,
`etiqueta_obligacion` y `clave_funcional_origen` en `obligacion_financiera`.
`orden_composicion` sigue ordenando componentes dentro de una obligacion, no
items del cronograma.

## Etiqueta estable para UI/reportes

Existe `etiqueta_obligacion` para cronogramas V2. En
`CUOTAS_IGUALES_SIMPLE`, el servicio carga `Cuota N`.

`descripcion_operativa` existe, pero no se usa como etiqueta estable del
cronograma y la respuesta documentada del alta generica puede devolverla en
`null`.

`codigo_obligacion_financiera` tambien existe, pero el insert comun de
obligaciones no lo recibe ni lo persiste desde venta confirmada. Hoy no hay una
convencion implementada que permita mostrar de forma estable `Anticipo`,
`Cuota 1`, `Cuota 2`, `Saldo de venta` sin inferir desde concepto/fecha/orden.

Conclusion: `descripcion_operativa` debe considerarse descripcion libre/no
funcional. Para cronogramas V2, la etiqueta contractual es
`etiqueta_obligacion` y la clave idempotente es `clave_funcional_origen`.

## Concepto: obligacion, composicion o ambos

Hoy la naturaleza economica se guarda principalmente en
`composicion_obligacion` mediante `concepto_financiero`:

- anticipo: composicion `ANTICIPO_VENTA`
- capital/cuota/saldo: composicion `CAPITAL_VENTA`
- interes: composicion `INTERES_FINANCIERO`
- ajuste por indexacion: composicion `AJUSTE_INDEXACION`

Esto es correcto para desglose financiero, intereses e indexaciones. Pero no
alcanza para distinguir funcionalmente `Cuota 1` vs `Cuota 2` cuando ambas son
`CAPITAL_VENTA` por importes iguales o vencimientos iguales. La identidad del
item del cronograma debe estar en la obligacion o en una estructura tecnica de
trazabilidad/idempotencia; la composicion no debe reemplazar ese rol.

## Idempotencia actual

Hay dos mecanismos parciales:

- `relacion_generadora` se reutiliza por `tipo_origen` + `id_origen`.
- En venta confirmada, si ya existen obligaciones activas para la relacion, el
  servicio no regenera el plan; solo completa obligados faltantes.

En cronogramas periodicos existe unicidad parcial
`(id_relacion_generadora, periodo_desde, periodo_hasta) WHERE deleted_at IS NULL`
y algunos inserts usan `ON CONFLICT` con esa clave.

Para venta V2 inicial ya existe clave por item funcional del cronograma:
`clave_funcional_origen`. En `CUOTAS_IGUALES_SIMPLE`, la convencion actual es
`PLAN_PAGO_VENTA:{id_plan_pago_venta}:CUOTA:{N}`.

Sigue pendiente definir claves para metodos futuros que involucren `ANTICIPO`,
`SALDO`, items manuales, reemplazos o versionados complejos.

## Respuestas a las preguntas de auditoria

1. **Columnas reales de `obligacion_financiera`:** listadas en la seccion
   "Estructura actual".
2. **Existe `estado_obligacion = PROYECTADA`:** si, existe en constraint SQL,
   backend y tests.
3. **Estados permitidos actualmente:** `PROYECTADA`, `EMITIDA`, `EXIGIBLE`,
   `PARCIALMENTE_CANCELADA`, `CANCELADA`, `VENCIDA`, `ANULADA`, `REEMPLAZADA`,
   `PENDIENTE_AJUSTE`.
4. **Campo de orden funcional:** existe `numero_obligacion` para cronogramas V2.
5. **Etiqueta estable UI/reportes:** existe `etiqueta_obligacion` para
   cronogramas V2; en `CUOTAS_IGUALES_SIMPLE` se carga como `Cuota N`.
6. **Uso de `descripcion_operativa`:** actualmente debe tratarse como descripcion
   libre/nula, no como dato funcional contractual.
7. **Clave funcional/idempotente:** existe `clave_funcional_origen` para item de
   cronograma de venta V2. La unicidad por periodo no se usa para este caso.
8. **Vinculo obligacion-origen venta/cuota:** venta por `relacion_generadora`;
   cuota V1 solo como fuente leida antes de generar, sin FK persistida en la
   obligacion.
9. **Referencia a `venta_plan_cuota.id_venta_plan_cuota`:** existe lectura en
   repositorio, pero no referencia persistida en `obligacion_financiera`.
10. **Orden actual del cronograma:** por `numero_cuota` antes de materializar V1;
    luego por `fecha_vencimiento`, `periodo_desde` o `id_obligacion_financiera`
    segun consulta.
11. **Distincion Anticipo/Cuota N/Saldo:** anticipo se distingue por
    `ANTICIPO_VENTA`; cuotas y saldo suelen ser `CAPITAL_VENTA`, por lo que
    `Cuota N`/`Saldo` no quedan diferenciados formalmente si no se infieren por
    plan/orden/fecha.
12. **Concepto:** naturaleza economica en composicion; identidad funcional del
    hito deberia estar en obligacion o trazabilidad tecnica, no solo en
    composicion.
13. **Faltantes para `CUOTAS_IGUALES_SIMPLE`:** resueltos para el V2 inicial:
    metodo/regla comercial fuente, numero/orden funcional, etiqueta estable,
    clave idempotente por cuota, corrida de generacion y convencion de redondeo.
    Quedan pendientes validacion estricta contra monto/moneda de venta,
    multiples compradores y regeneracion avanzada.
14. **Faltantes para `ANTICIPO_MAS_CUOTAS_IGUALES`:** lo anterior mas tipo de
    hito (`ANTICIPO` vs `CUOTA`), numero de cuota para saldo, y forma estable de
    asociar anticipo y cuotas al mismo plan/corrida.
15. **Faltantes para `CRONOGRAMA_DEFINIDO`:** identificador estable de cada item
    cargado, orden explicito, etiqueta, desglose de composiciones validado,
    idempotencia por item y trazabilidad de input/corrida sin crear tabla de
    cuotas como entidad de negocio.
16. **Migracion conceptual desde `venta_plan_cuota`:** crear/asegurar relacion
    generadora por venta, crear una obligacion por cuota activa con composicion
    `CAPITAL_VENTA`, obligado comprador, preservar importe/moneda/vencimiento,
    mapear `numero_cuota` a orden funcional nuevo, guardar trazabilidad de origen
    V1 y evitar duplicados.
17. **Documentacion desalineada:** hay drift parcial: el modelo V2 documenta la
    necesidad de orden/etiqueta/idempotencia como pendiente, pero DEV-API
    comercial aun describe `CUOTAS_FIJAS` desde `venta_plan_cuota` como flujo
    vigente; DEV-API/DEV-SRV financiero mezclan ejemplos genericos
    `PROYECTADA` con otros procesos que crean `EMITIDA`. No es contradiccion
    tecnica, pero debe explicitarse por caso de uso: venta confirmada V1 crea
    `PROYECTADA`; traslados/recuperos/locativo pueden crear `EMITIDA`.

## Brechas para cronograma V2

### Brechas SQL

- Resuelto para V2 inicial: `numero_obligacion`.
- Resuelto para V2 inicial: `tipo_item_cronograma`.
- Resuelto para V2 inicial: `etiqueta_obligacion`.
- Resuelto para V2 inicial: `clave_funcional_origen`.
- Resuelto para V2 inicial: referencia a
  `id_generacion_cronograma_financiero`.
- Falta trazabilidad explicita de migracion V1 sin depender permanentemente de
  `venta_plan_cuota`.

### Brechas backend

- `HandleVentaConfirmadaEventService` no soporta metodos V2 nuevos; el V2
  inicial se genera por endpoint explicito.
- `GeneratePlanPagoVentaCuotasIgualesSimpleService` transporta numero
  funcional, etiqueta, tipo de hito y clave idempotente.
- La creacion comun de obligaciones sigue sin recibir campos V2; el servicio V2
  usa repositorio especifico de cronograma.
- La idempotencia de venta confirmada es de relacion completa, no de item de
  cronograma.
- Las consultas generales de estado de cuenta no dependen aun de
  `numero_obligacion` como orden principal.

### Brechas tests

- Los tests actuales validan `CONTADO`, `ANTICIPO_Y_SALDO` y `CUOTAS_FIJAS` V1.
- Los tests de cuotas fijas dependen de `venta_plan_cuota` como fuente.
- Hay cobertura para `CUOTAS_IGUALES_SIMPLE` sin `venta_plan_cuota`,
  incluyendo plan, corrida, obligaciones, idempotencia, redondeo, vencimientos
  mensuales, orden funcional, etiqueta estable y comprador unico.
- No hay cobertura para `ANTICIPO_MAS_CUOTAS_IGUALES` ni
  `CRONOGRAMA_DEFINIDO` sin `venta_plan_cuota`.
- No hay cobertura de migracion V1 con trazabilidad formal.

## Recomendacion de campos minimos

La recomendacion minima ya fue implementada para el V2 inicial mediante campos
en `obligacion_financiera` y la tabla tecnica
`generacion_cronograma_financiero`:

1. `numero_obligacion` o `numero_item_cronograma`: entero positivo, orden
   funcional dentro de `id_relacion_generadora`/plan/corrida.
2. `tipo_item_cronograma`: enum/check textual controlado (`ANTICIPO`, `CUOTA`,
   `SALDO`, `REFUERZO`, `AJUSTE`, etc.).
3. `etiqueta_obligacion`: texto estable para UI/reportes, derivado de tipo y
   numero pero persistido para contrato de lectura.
4. `clave_funcional_origen`: clave deterministica idempotente por item, por
   ejemplo `VENTA:{id_venta}:PLAN:{id_plan_o_version}:CUOTA:{n}`.
5. `id_generacion_cronograma_financiero`: identificador de corrida/version del
   cronograma para auditoria e idempotencia.
6. `id_plan_pago_venta_bloque`: trazabilidad nullable hacia el bloque comercial
   de origen cuando la obligacion proviene de plan de pago de venta V2 por
   bloques; no es idempotencia.
7. `origen_legacy_tipo` / `origen_legacy_id` o tabla tecnica equivalente para
   migrar desde `venta_plan_cuota` sin convertirla en dependencia permanente del
   modelo V2.

No se creo `plan_pago_venta_cuota` ni `plan_pago_venta_tramo`.

## Recomendacion de idempotencia

La clave idempotente no debe depender de `descripcion_operativa`, importe,
fecha de vencimiento ni `id_obligacion_financiera`.

Debe depender de:

- origen financiero: `id_relacion_generadora`
- clave deterministica de item: `clave_funcional_origen`
- plan/regla/corrida vigente
- tipo de hito (`ANTICIPO`, `CUOTA`, `SALDO`, `REFUERZO`, `AJUSTE`)
- numero funcional cuando aplique
- version de generacion cuando se permita reemplazo controlado

Indice recomendado a disenar:

- unico parcial por obligaciones activas/no eliminadas sobre
  `(id_relacion_generadora, clave_funcional_origen)`; o
- unico parcial equivalente sobre
  `(id_relacion_generadora, id_corrida_generacion, tipo_item_cronograma,
  numero_obligacion)`.

Para regeneracion, si no hay pagos/aplicaciones activas, marcar obligaciones
anteriores como `REEMPLAZADA`/baja logica segun regla financiera y crear nuevas
con trazabilidad cruzada. Si hay pagos, no reemplazar sin regla explicita de
refinanciacion/ajuste.

## Impacto en docs y tests

Docs a alinear antes o junto con SQL V2:

- DEV-SRV financiero: diferenciar creacion generica `PROYECTADA`, venta
  confirmada `PROYECTADA` y procesos que nacen `EMITIDA`.
- DEV-API financiero: documentar campos nuevos de cronograma y orden de
  respuesta cuando existan.
- DEV-API comercial: marcar `venta_plan_cuota` como V1 legacy para
  `CUOTAS_FIJAS` y documentar que metodos V2 no lo usan.
- DER financiero/comercial: reflejar que `obligacion_financiera.id_plan_pago_venta_bloque` es trazabilidad de origen comercial y que `clave_funcional_origen` conserva la idempotencia financiera.

Tests pendientes o a ampliar en una etapa posterior:

- venta confirmada con `ANTICIPO_MAS_CUOTAS_IGUALES` sin filas en
  `venta_plan_cuota`.
- `CRONOGRAMA_DEFINIDO` con items de importes y conceptos distintos.
- migracion V1: `venta_plan_cuota.numero_cuota` preservado en campo nuevo o
  trazabilidad tecnica.
- pagos: no reemplazar obligaciones con aplicaciones sin regla explicita.

## Proximo prompt recomendado

Extender el modelo V2 mas alla de `CUOTAS_IGUALES_SIMPLE` sin modificar reglas
financieras vigentes:

- definir reglas para `ANTICIPO_MAS_CUOTAS_IGUALES`;
- definir reglas para `CRONOGRAMA_DEFINIDO`;
- decidir validacion estricta de `monto_total_plan` y `moneda` contra venta;
- decidir politica transversal para `X-Op-Id` invalido;
- definir migracion conceptual de `venta_plan_cuota` legacy V1 a campos V2;
- ampliar tests para multiples compradores, regeneracion y pagos existentes.
