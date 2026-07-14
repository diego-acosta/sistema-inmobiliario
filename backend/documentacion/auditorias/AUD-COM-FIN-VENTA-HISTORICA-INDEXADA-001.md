# AUD-COM-FIN-VENTA-HISTORICA-INDEXADA-001 — Auditoría para indexar cuotas al registrar una venta histórica (#345)

## 1. Contexto

Esta auditoría releva el flujo real de alta manual de ventas, generación de Plan Pago Venta V2 y motor de indexación de cuotas V2 para definir un camino incremental de implementación de #345. No implementa la funcionalidad completa, no agrega endpoints y no modifica deuda.

Clasificación de conceptos:

- `venta`, condiciones comerciales y roles de comprador: núcleo del dominio `comercial`.
- `plan_pago_venta` y `plan_pago_venta_bloque`: regla/cronograma comercial pactado que origina deuda; soporte de integración comercial-financiera.
- `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, corridas e indexación aplicada: núcleo/soporte del dominio financiero según la semántica de deuda.
- `relacion_persona_rol` y `rol_participacion`: soporte transversal, no ownership semántico.

La arquitectura vigente exige que `comercial` no ejecute ni redefina lógica financiera primaria: la venta y sus condiciones pueden originar obligaciones, pero deuda, saldo, ajustes, pagos e imputaciones pertenecen al dominio financiero.

## 2. Flujo actual real

### 2.1 Alta manual completa sin reserva previa

El flujo manual completo materializado para carga de venta sin reserva es:

1. `POST /api/v1/ventas/directa/confirmar-venta-completa`.
2. El router construye `ConfirmVentaDirectaCompletaCommand` con `generar_venta.fecha_venta`, compradores, objetos, condiciones comerciales, plan V2 y confirmación.
3. `ConfirmVentaDirectaCompletaService.execute()` abre una transacción.
4. Dentro de esa transacción:
   - resuelve compradores contextuales;
   - crea la venta en `borrador` con `_create_venta_directa_tx`;
   - define condiciones comerciales con `DefineCondicionesComercialesVentaService`;
   - genera Plan Pago Venta V2 con `GeneratePlanPagoVentaV2PorBloquesService.execute_in_existing_transaction()`;
   - confirma la venta con `ConfirmVentaService`;
   - devuelve ids de venta, plan, generación y obligaciones.

Este es el punto más natural para venta histórica manual porque recibe `fecha_venta`, plan V2 por bloques e indexación por bloque en un único payload y ya tiene frontera transaccional compuesta.

### 2.2 Alta completa desde reserva

El flujo completo desde una reserva es:

1. `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`.
2. `ConfirmVentaCompletaDesdeReservaService.execute()` abre una transacción.
3. Dentro de esa transacción:
   - genera venta desde reserva con `GenerateVentaFromReservaVentaService`;
   - define condiciones comerciales;
   - genera Plan Pago Venta V2;
   - confirma venta;
   - devuelve ids de reserva, venta, plan, generación y obligaciones.

Este flujo también puede recibir una `fecha_venta` histórica, pero semánticamente no es el caso principal de carga manual histórica si la venta no nació de una reserva vigente.

### 2.3 Flujo granular existente

Además existen endpoints separados:

- `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta` crea una venta en `borrador` desde reserva.
- `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales` define condiciones.
- `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar` genera Plan Pago Venta V2.
- `PATCH /api/v1/ventas/{id_venta}/confirmar` confirma una venta existente.

El flujo granular permite armar una venta por etapas, pero #345 debería evitar crear una lógica paralela si el alta histórica manual real debe permanecer en el orquestador completo.

## 3. Endpoints encontrados

| Endpoint | Naturaleza CORE-EF | Uso actual relevante para #345 |
| --- | --- | --- |
| `POST /api/v1/ventas/directa/confirmar-venta-completa` | `COMMAND_WRITE_NEGOCIO` | Alta manual completa: venta + condiciones + Plan Pago V2 + confirmación. |
| `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa` | `COMMAND_WRITE_NEGOCIO` | Variante completa desde reserva. |
| `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta` | `COMMAND_WRITE_NEGOCIO` | Crea `venta` en borrador desde reserva. |
| `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales` | `COMMAND_WRITE_NEGOCIO` | Completa condiciones comerciales. |
| `POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview` | `PREVIEW_READLIKE` | Preview de Plan Pago V2 con cálculo de indexación de cuota si hay valor publicado. |
| `POST /api/v1/ventas/plan-pago-v2/preview` | `PREVIEW_READLIKE` | Preview sin venta persistida para wizard. |
| `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar` | `COMMAND_WRITE_NEGOCIO` | Persiste Plan Pago V2, cronograma, obligaciones y trazabilidad de indexación por obligación cuando corresponde. |
| `PATCH /api/v1/ventas/{id_venta}/confirmar` | `COMMAND_WRITE_NEGOCIO` | Cambia venta a confirmada y emite outbox `venta_confirmada`. |
| Endpoints financieros V2 de preview/aplicación/preparación de corridas | `PREVIEW_READLIKE`/`COMMAND_WRITE_*` según operación | Motor existente a reutilizar, no duplicar. |

## 4. Servicios encontrados

### Comercial

- `ConfirmVentaDirectaCompletaService`: orquestador transaccional de venta directa completa.
- `ConfirmVentaCompletaDesdeReservaService`: orquestador transaccional desde reserva.
- `GenerateVentaFromReservaVentaService`: generación de venta desde reserva.
- `DefineCondicionesComercialesVentaService`: persistencia de condiciones comerciales.
- `BuildPlanPagoVentaV2PorBloquesPreviewService`: arma cuotas preview y calcula estado de indexación por cuota si el bloque usa indexación.
- `GeneratePlanPagoVentaV2PorBloquesService`: persiste plan, bloques, relación generadora, generación cronograma, obligaciones, composiciones, obligados y trazabilidad de indexación por obligación.
- `ConfirmVentaService`: confirma venta y emite outbox.

### Financiero

- `IndexacionCuotaCalculator`: calcula cuota indexada por coeficiente; cuando no hay valor devuelve `PROYECTADA_SIN_INDICE`.
- `PreviewIndexacionCuotasV2Service`: genera preview/persistencia opcional de corrida V2 para un plan+bloque+configuración+índice+valor.
- `AplicarIndexacionCuotasV2Service`: aplica una corrida persistida sobre obligaciones elegibles con lock lógico, idempotencia por `op_id`, control de versión y outbox.
- `PrepararCorridasIndexacionCuotasV2Service`: al publicar un índice, prepara corridas por configuraciones alcanzadas y clasifica otro valor del mismo período como `REQUIERE_CORRECCION`.
- `HandleVentaConfirmadaEventService`: consumidor financiero heredado de evento `venta_confirmada`; genera obligaciones desde condiciones comerciales no V2 si no existen obligaciones activas para la relación generadora.

## 5. Tablas involucradas

| Tabla | Rol auditado |
| --- | --- |
| `venta` | Cabecera comercial; contiene `fecha_venta`, estado, monto y condiciones financieras heredadas. |
| `plan_pago_venta` | Cabecera de plan V2; no representa deuda por sí misma. |
| `plan_pago_venta_bloque` | Bloques/tramos del plan V2; incluye `metodo_liquidacion` y vínculo funcional a obligaciones. |
| `plan_pago_venta_bloque_indexacion` | Configuración de indexación por bloque: índice, fecha base, valor base, modo y política. |
| `generacion_cronograma_financiero` | Marca la generación del cronograma financiero desde el plan. |
| `relacion_generadora` | Relación polimórfica `venta` → obligaciones. |
| `obligacion_financiera` | Deuda/proyección materializada; contiene importes, saldo, vencimiento, estado y flags financieros. |
| `composicion_obligacion` | Desglose de capital, interés y ajuste de indexación. |
| `obligacion_financiera_indexacion` | Trazabilidad de índice aplicado por obligación. |
| `corrida_indexacion_financiera` | Cabecera de corrida V2. |
| `corrida_indexacion_financiera_detalle` | Detalle por obligación analizada/elegible/excluida. |
| `indice_financiero` | Definición y estado del índice. |
| `indice_financiero_valor` | Valores publicados; incluye `fecha_valor`, `valor_indice`, `fecha_publicacion` y estado. |

## 6. Fecha histórica efectiva

No existe hoy un campo o flag físico `venta_historica` ni un flujo específico `historica` en endpoints, schemas o servicios.

La fecha efectiva más sólida para detectar que una venta es histórica es `venta.fecha_venta`, porque:

- es obligatoria en la tabla `venta`;
- está presente en los commands de generación/alta completa;
- se persiste desde el payload de alta;
- el consumidor financiero heredado la usa para el vencimiento de venta contado;
- no se encontró `fecha_firma`, `fecha_confirmacion`, `fecha_base_plan` o `fecha_alta` como criterio implementado de historicidad.

La `fecha_base_indice` del bloque no define que la venta sea histórica; define la base de cálculo de cada bloque indexado. La `fecha_primer_vencimiento`/`fecha_vencimiento` define exigibilidad de cuotas. La fecha de confirmación no está persistida como campo dedicado en `venta`; solo hay `updated_at`, que no debe reinterpretarse como fecha comercial.

Propuesta: detectar venta histórica cuando `fecha_venta::date` sea anterior a la fecha operativa de confirmación/alta y existan cuotas/bloques con vencimientos o períodos exigibles entre `fecha_venta` y la fecha de corte. La fecha de corte exacta debe definirse en #345-A1; por defecto debería ser la fecha operativa recibida por CORE-EF o `current_date` del backend si no hay fecha operativa formal.

## 7. Estados relevantes

`PROYECTADA_SIN_INDICE` existe físicamente como constante de servicio, no como constraint de `obligacion_financiera.estado_obligacion`.

Uso actual:

- En `IndexacionCuotaCalculator`, si no hay valor publicado aplicable, devuelve `estado_indexacion = "PROYECTADA_SIN_INDICE"` y mantiene `importe_total = capital_cuota`.
- En Plan Pago V2 preview/generate, ese valor se propaga como `estado_preview_indexacion` de la obligación preview.
- En persistencia, cuando la obligación queda sin valor publicado no se crea `obligacion_financiera_indexacion`; la obligación sigue siendo una `obligacion_financiera` normal con estado financiero como `PROYECTADA`.

Invariante auditada: `PROYECTADA_SIN_INDICE` no debe usarse como nuevo `estado_obligacion` sin migración SQL, porque la constraint de `obligacion_financiera` no lo permite. Para cuotas futuras conviene mantenerlo como estado de indexación/trazabilidad preview o, si se requiere persistencia explícita, agregar una columna/tabla de estado de indexación en un PR posterior.

Compatibilidad con obligaciones futuras: compatible si se conserva como estado de cálculo/indexación y no como estado financiero principal. Las publicaciones futuras pueden preparar corridas normales sobre obligaciones del bloque cuando exista valor publicado y obligación analizable.

## 8. Brechas

1. No hay detección formal de venta histórica.
2. No hay prevalidación específica de índices antes de confirmar una venta histórica.
3. El preview/generate de Plan Pago V2 puede calcular cuotas con valor publicado si existe, pero eso no equivale a una corrida V2 histórica trazable.
4. `PreviewIndexacionCuotasV2Service` requiere plan/bloque/configuración/obligaciones ya persistidos; por eso no sirve tal cual antes de generar cronograma.
5. La aplicación V2 modifica obligaciones existentes y exige corrida persistida, versión, lock e idempotencia; no está integrada al orquestador de venta completa.
6. La preparación por publicación solo usa `origen_corrida = 'PUBLICACION_INDICE'`; para venta histórica existe origen SQL permitido `ALTA_MANUAL_VENTA_HISTORICA`, pero no se observó servicio orquestador que lo use.
7. Falta definir fecha de corte funcional de venta histórica.
8. Falta definir si confirmar debe bloquear ante índice faltante o permitir cuotas futuras proyectadas.
9. Falta política para obligaciones ya materializadas por reintentos parciales o flujos granulares.

## 9. Decisiones pendientes

- Fecha de corte: fecha operativa, fecha actual del sistema, fecha de confirmación o parámetro explícito.
- Umbral de historicidad: `fecha_venta < fecha_corte`, existencia de cuotas vencidas, o ambas.
- Política por mes de la cuota: qué hacer con cuota del mismo mes de alta histórica.
- Si `fecha_publicacion IS NULL` debe bloquear siempre para cuotas exigibles históricas. Recomendación: sí.
- Si la confirmación crea corrida en `PREVISUALIZADA` y aplica en el mismo comando o si queda pendiente de aplicación manual.
- Cómo exponer preview histórico sin crear deuda: endpoint existente extendido vs nuevo endpoint futuro.
- Si las cuotas futuras deben persistir un estado de indexación más allá de `obligacion_financiera_indexacion` ausente.
- Política para moneda no ARS: hoy la aplicación V2 bloquea obligaciones cuya moneda no sea `ARS`.

## 10. Alternativas evaluadas

### A. Crear obligaciones ya indexadas

La confirmación calcula capital, ajuste y total directamente al materializar obligaciones.

Ventajas:

- Menos pasos de ejecución.
- Una sola transacción de venta/plan/obligaciones.
- Menor dependencia del motor de corridas.

Riesgos:

- Duplica lógica financiera de indexación.
- Pierde trazabilidad de corrida V2 o fuerza una corrida artificial posterior.
- Aumenta acoplamiento de `comercial` con deuda.
- Dificulta rollback y auditoría de diferencias.
- Riesgo de incompatibilidad con #343/#344 si esos issues esperan identidad mensual de corridas y tratamiento de correcciones.

Trazabilidad: baja/media, salvo que se replique `corrida_indexacion_financiera`.

Atomicidad: alta para alta inicial, baja para controles financieros posteriores.

Sincronización: riesgosa si no se emiten eventos financieros equivalentes.

### B. Crear obligaciones base y luego aplicar corrida V2

La confirmación crea obligaciones base, genera preview/corrida V2 para períodos históricos exigibles y aplica la corrida.

Ventajas:

- Reutiliza servicios V2 existentes.
- Conserva trazabilidad de corrida y detalle por obligación.
- Respeta ownership financiero.
- Es compatible con identidad mensual por plan+bloque+configuración+índice+mes y con corrección posterior.

Riesgos:

- Requiere orquestación transaccional compleja entre alta de venta y aplicación V2.
- Si la corrida se aplica dentro de la misma transacción, los servicios actuales pueden necesitar modo `execute_in_existing_transaction` porque `PreviewIndexacionCuotasV2Repository.create_corrida_preview()` y `AplicarIndexacionCuotasV2Service` hacen `commit()`.
- Si se separa en dos transacciones, hay ventana con deuda base sin ajuste.
- Necesita diseño de rollback y locks.

Trazabilidad: alta.

Atomicidad: viable pero requiere adaptar repositorios/servicios para no commitear internamente en modo orquestado.

Sincronización: buena si se preserva outbox de venta confirmada y outbox financiero de aplicación.

### C. Flujo híbrido

- Se crean obligaciones base con Plan Pago V2.
- Para cuotas históricas exigibles, se genera y aplica corrida V2 con origen `ALTA_MANUAL_VENTA_HISTORICA`.
- Para cuotas futuras, se mantienen como base/proyectadas sin aplicación inmediata; si no tienen valor se conserva `PROYECTADA_SIN_INDICE` como estado de indexación/preview, no como estado financiero.
- Las publicaciones futuras siguen el flujo mensual normal de preparación y aplicación.

Ventajas:

- Reutiliza el motor V2 donde corresponde.
- Evita aplicar cuotas futuras antes de que exista índice exigible.
- Conserva trazabilidad para ajustes históricos.
- Minimiza duplicación y respeta límites comercial/financiero.
- Encaja con preparación automática de corridas y correcciones mensuales ya existentes.

Riesgos:

- Requiere resolver con precisión el corte histórico y la clasificación de cuota del mes.
- Requiere prevalidar índices antes de crear deuda si se quiere rollback completo.
- Requiere adaptar servicios para modo transaccional orquestado o aceptar un flujo en etapas controladas.

Trazabilidad: alta.

Atomicidad: recomendable en confirmación funcional, siempre que la aplicación de corridas históricas pueda participar de la misma frontera transaccional o que la confirmación se bloquee antes si falta índice.

Sincronización: buena; no necesita inventar eventos nuevos para #345-A1 y puede reutilizar outbox financiero al aplicar.

## 11. Alternativa recomendada

Recomendada: **C. Flujo híbrido**.

Justificación:

- Mantiene el alta comercial como origen, pero deja deuda/indexación en servicios financieros.
- Usa Plan Pago V2 como fuente del cronograma base.
- Usa corridas V2 para cuotas históricas exigibles y deja cuotas futuras al flujo mensual normal.
- Evita duplicar cálculo financiero.
- Es la opción más compatible con #343/#344: identidad mensual de corridas, publicación de índices y `REQUIERE_CORRECCION` cuando aparece otro valor del mismo mes.
- Permite un primer PR funcional pequeño de prevalidación/preview sin modificar deuda.

## 12. Propuesta transaccional

Objetivo final recomendado para confirmación histórica:

1. Prevalidar antes de persistir o antes de confirmar:
   - venta histórica detectada por `fecha_venta`;
   - bloques indexados existentes;
   - índice activo;
   - valor base válido;
   - valores publicados exigibles hasta fecha de corte;
   - moneda compatible;
   - ausencia de corrida activa incompatible por plan+bloque+config+índice+mes.
2. En una frontera transaccional única:
   - crear/actualizar venta en borrador;
   - definir condiciones;
   - generar Plan Pago V2, bloques, cronograma, obligaciones base y relación generadora;
   - persistir corridas históricas con origen `ALTA_MANUAL_VENTA_HISTORICA`;
   - aplicar ajustes históricos a obligaciones elegibles;
   - confirmar venta;
   - emitir outbox correspondiente.

Si falta un índice exigible o un valor publicado exigible:

- bloquear confirmación;
- rollback completo del intento si el endpoint es completo;
- mantener venta en borrador solo si el flujo granular ya había persistido la venta antes de la prevalidación;
- no dejar obligaciones parciales ni plan incompleto;
- no aplicar corridas automáticamente fuera de la frontera definida.

## 13. Bloqueos funcionales propuestos

Bloquear confirmación/prevalidación histórica cuando:

- falta configuración de índice en bloque indexado exigible;
- índice no existe, está inactivo, eliminado o anulado;
- `valor_base_indice <= 0` o `fecha_base_indice` inválida;
- no existe valor publicado para un período exigible;
- `fecha_publicacion IS NULL` para valor exigible;
- el valor aplicable no pertenece al índice configurado;
- ya existe corrida activa del mismo plan+bloque+configuración+índice+mes con otro valor aplicado;
- moneda de obligación/bloque no es compatible con el motor V2 actual (`ARS`);
- ya existen obligaciones activas duplicadas para la misma relación generadora y clave funcional;
- hay obligación con pagos, imputaciones, mora incompatible o punitorios donde el motor V2 no pueda aplicar;
- el replay por `op_id` trae payload distinto.

## 14. Errores funcionales sugeridos

- `VENTA_HISTORICA_REQUIERE_PREVALIDACION_INDEXACION`
- `FECHA_VENTA_HISTORICA_INVALIDA`
- `INDICE_FINANCIERO_INACTIVO`
- `VALOR_INDICE_EXIGIBLE_NO_PUBLICADO`
- `FECHA_PUBLICACION_INDICE_REQUERIDA`
- `VALOR_BASE_INDICE_INVALIDO`
- `CORRIDA_HISTORICA_YA_EXISTE_CON_OTRO_VALOR`
- `MONEDA_INDEXACION_INCOMPATIBLE`
- `OBLIGACIONES_DUPLICADAS_PARA_PLAN`
- `OBLIGACION_HISTORICA_NO_ELEGIBLE_INDEXACION`
- `IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE`

## 15. Estrategia de idempotencia

- Alta histórica completa: `X-Op-Id` + hash canónico del payload completo de venta directa/reserva, incluyendo `fecha_venta`, objetos, compradores, plan, bloques e índices.
- Preview histórico: `X-Op-Id` + hash de alcance (`fecha_corte`, plan/bloques simulados, índice, valores exigibles), sin persistir deuda.
- Confirmación: mismo `op_id` + mismo payload debe devolver el resultado ya creado; mismo `op_id` + payload distinto debe devolver conflicto.
- Corrida por plan+bloque+mes: clave funcional `(id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion, id_indice_financiero, mes(periodo_aplicado), origen_corrida)`; para publicación mensual ya existe lógica de detección de otro valor como `REQUIERE_CORRECCION`.
- No duplicación de obligaciones: conservar claves funcionales de generación V2 y `create_obligacion_cronograma_v2_if_not_exists`; verificar obligación activa por plan/bloque/número/período antes de aplicar ajustes.

## 16. Plan incremental

### PR 1 — Prevalidación y preview histórico

- Detectar venta histórica por `fecha_venta` y fecha de corte definida.
- Resolver bloques indexados desde el payload/preview de Plan Pago V2.
- Resolver índices y valores publicados exigibles.
- Devolver preview histórico sin modificar deuda.
- Documentar decisión CORE-EF como `PREVIEW_READLIKE` si no persiste.

### PR 2 — Confirmación transaccional histórica

- Integrar prevalidación al orquestador completo.
- Generar venta, plan, cronograma y obligaciones base.
- Persistir corridas con `origen_corrida = 'ALTA_MANUAL_VENTA_HISTORICA'`.
- Aplicar ajustes históricos dentro de una frontera transaccional controlada.
- Evitar commits internos de servicios financieros en modo orquestado.

### PR 3 — Cuotas futuras e integración mensual

- Confirmar cómo persistir/exponer `PROYECTADA_SIN_INDICE` para cuotas futuras sin usarlo como `estado_obligacion`.
- Validar que publicaciones futuras encuentren las configuraciones y obligaciones alcanzadas.
- Agregar tests de preparación/aplicación posteriores al alta histórica.

### PR 4 — Importación masiva

Fuera de #345. Corresponde a #346.

### PR posterior — Corrección/reversión avanzada

Fuera de #345. Corresponde a #349.

## 17. Archivos previstos para el siguiente PR

Probables archivos a tocar en #345-A1/#345-A2:

- `backend/app/api/routers/comercial_router.py`
- `backend/app/api/schemas/comercial.py`
- `backend/app/application/comercial/commands/confirm_venta_directa_completa.py`
- `backend/app/application/comercial/commands/confirm_venta_completa_desde_reserva.py`
- `backend/app/application/comercial/services/confirm_venta_directa_completa_service.py`
- `backend/app/application/comercial/services/confirm_venta_completa_desde_reserva_service.py`
- `backend/app/application/comercial/services/build_plan_pago_venta_v2_por_bloques_preview_service.py`
- `backend/app/application/financiero/services/preview_indexacion_cuotas_v2_service.py`
- `backend/app/application/financiero/services/aplicar_indexacion_cuotas_v2_service.py`
- `backend/app/infrastructure/persistence/repositories/preview_indexacion_cuotas_v2_repository.py`
- `backend/app/infrastructure/persistence/repositories/aplicar_indexacion_cuotas_v2_repository.py`
- tests comerciales de venta directa/reserva y tests financieros V2 de preview/aplicación/preparación.

## 18. Riesgos

- Alto riesgo de deuda base sin ajuste si se confirma en una transacción y se aplica corrida en otra.
- Riesgo de duplicación si se intenta recrear obligaciones ante retry sin una clave funcional completa.
- Riesgo de violar dominio si `comercial` calcula ajustes financieros directamente.
- Riesgo de confundir `PROYECTADA_SIN_INDICE` con `estado_obligacion`.
- Riesgo de bloqueo operativo si no se define la fecha de corte y el tratamiento del mes actual.
- Riesgo de inconsistencias si `fecha_publicacion IS NULL` se acepta para valores exigibles históricos.

## 19. Relación con #343, #344, #346 y #349

- #343/#344: la recomendación reutiliza identidad mensual por plan+bloque+configuración+índice+mes, preparación por publicación y clasificación `REQUIERE_CORRECCION` para otro valor del mismo mes.
- #346: importación masiva queda explícitamente fuera; la auditoría solo cubre alta manual y diseño incremental.
- #349: reversión/corrección avanzada queda fuera; solo se sugieren bloqueos para evitar estados que requieran corrección inmediata.

## 20. Conclusión

El flujo real de alta manual completa es `POST /api/v1/ventas/directa/confirmar-venta-completa`. La fecha histórica efectiva hoy es `fecha_venta`; no existe un campo específico de venta histórica. Plan Pago Venta V2 ya genera obligaciones y soporta configuración de indexación por bloque, pero la corrida V2 histórica no está integrada al alta/confirmación. La alternativa recomendada es un flujo híbrido: obligaciones base + corridas V2 para cuotas históricas exigibles + cuotas futuras proyectadas para el flujo mensual normal. Este PR no cierra #345 como funcionalidad completa; deja la propuesta técnica para los PRs siguientes.
