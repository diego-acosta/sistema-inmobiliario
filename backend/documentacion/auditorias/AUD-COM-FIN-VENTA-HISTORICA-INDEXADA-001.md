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

Propuesta: detectar venta histórica cuando `fecha_venta::date` sea anterior a una fecha de corte de negocio aún no definida formalmente y existan cuotas/bloques con vencimientos o períodos exigibles entre `fecha_venta` y esa fecha de corte. La fecha de corte histórica no surge actualmente de CORE-EF: los headers transversales transportan `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` y eventualmente `If-Match-Version`, pero no una fecha operativa de negocio. Debe definirse como dato de negocio explícito del request o, en su defecto, derivarse de una regla formal del backend, por ejemplo `current_date`, una fecha de confirmación persistida si se incorpora formalmente u otra fecha comercial definida por contrato. No debe inferirse de `created_at`, `updated_at` ni de headers transversales.

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
3. El preview/generate de Plan Pago V2 ya puede calcular y materializar cuotas indexadas si existe valor publicado aplicable; eso no debe duplicarse con una corrida inmediata sobre la misma obligación.
4. `PreviewIndexacionCuotasV2Service` requiere plan/bloque/configuración/obligaciones ya persistidos; por eso no sirve tal cual antes de generar cronograma.
5. La aplicación V2 modifica obligaciones existentes y exige corrida persistida, versión, lock e idempotencia; debe reservarse para hechos posteriores a la generación o correcciones, no para reindexar inmediatamente obligaciones ya creadas con ajuste.
6. La preparación por publicación solo usa `origen_corrida = 'PUBLICACION_INDICE'`; para venta histórica existe origen SQL permitido `ALTA_MANUAL_VENTA_HISTORICA`, pero no se observó servicio orquestador que lo use.
7. Falta definir fecha de corte funcional de venta histórica.
8. Falta definir si confirmar debe bloquear ante índice faltante o permitir cuotas futuras proyectadas.
9. Falta política para obligaciones ya materializadas por reintentos parciales o flujos granulares.

## 9. Decisiones pendientes

- Fecha de corte: parámetro de negocio explícito en el request, `current_date` del backend, fecha de confirmación persistida si se incorpora formalmente u otra fecha comercial definida por contrato. CORE-EF no transporta esta fecha.
- Umbral de historicidad: `fecha_venta < fecha_corte`, existencia de cuotas vencidas, o ambas.
- Política por mes de la cuota: qué hacer con cuota del mismo mes de alta histórica.
- Si `fecha_publicacion IS NULL` debe bloquear siempre para cuotas exigibles históricas. Recomendación: sí.
- Si una corrida posterior debe generarse solo para obligaciones no indexadas en generación, publicaciones futuras o correcciones; no debe aplicarse una segunda vez sobre obligaciones ya indexadas por el generador.
- Cómo exponer preview histórico sin crear deuda: endpoint existente extendido vs nuevo endpoint futuro.
- Si las cuotas futuras deben persistir un estado de indexación más allá de `obligacion_financiera_indexacion` ausente.
- Política para moneda no ARS: hoy la aplicación V2 bloquea obligaciones cuya moneda no sea `ARS`.

## 10. Alternativas evaluadas

### A. Crear obligaciones ya indexadas

La confirmación/generación materializa capital, ajuste y total directamente cuando ya existe valor publicado aplicable.

Ventajas:

- Evita una mutación inmediata posterior sobre la misma obligación.
- Reduce riesgo de doble aplicación si se apoya en una única fuente de cálculo.
- Es coherente con el comportamiento vigente del generador V2: el preview resuelve el valor publicado, la generación persiste el `importe_total` indexado, agrega `AJUSTE_INDEXACION` en `composicion_obligacion` y crea `obligacion_financiera_indexacion` cuando corresponde.

Riesgos:

- Sería inválido reimplementar esta lógica dentro de `comercial`; el cálculo financiero debe seguir concentrado en los servicios V2 existentes.
- Si se omite trazabilidad financiera, se perdería evidencia del índice aplicado. El generador vigente ya mitiga esto mediante `obligacion_financiera_indexacion`.
- No cubre por sí sola publicaciones posteriores, rectificaciones o obligaciones futuras que pasan a ser alcanzadas.

Trazabilidad: alta si se conserva la persistencia vigente de `AJUSTE_INDEXACION` y `obligacion_financiera_indexacion`.

Atomicidad: alta durante generación del Plan Pago V2, porque la obligación nace ya con el importe calculado y su trazabilidad asociada.

Sincronización: compatible si no se duplica el ajuste con corridas inmediatas.

### B. Forzar deuda sin ajuste inicial y mutarla con corrida V2

La confirmación fuerza deuda inicial sin ajuste y luego genera/aplica una corrida V2 inmediata para períodos históricos exigibles.

Ventajas:

- Concentraría toda indexación aplicada en corridas formales.
- Podría ser viable solo si se rediseñara deliberadamente el generador para no aplicar índices durante la generación.

Riesgos:

- No es recomendable para el alta inicial con el diseño vigente, porque el generador ya materializa el ajuste cuando encuentra valor publicado aplicable.
- Implicaría generar deuda base artificial para mutarla inmediatamente.
- Puede aplicar dos veces el ajuste si se corre sobre obligaciones ya indexadas por generación.
- Puede crear una corrida correctiva innecesaria y duplicar trazabilidad.
- Aumenta complejidad transaccional y contradice el diseño documentado vigente.

Trazabilidad: alta en la corrida, pero riesgosa por duplicación si convive con indexación en generación.

Atomicidad: más compleja que la generación directa vigente.

Sincronización: no recomendada salvo rediseño explícito fuera de este PR.

### C. Flujo híbrido con indexación en generación y corridas posteriores

- Durante la generación del Plan Pago V2, para cada cuota con valor publicado aplicable se conserva el cálculo del preview y se materializa directamente la obligación con capital + ajuste.
- La generación persiste `AJUSTE_INDEXACION` en `composicion_obligacion` y `obligacion_financiera_indexacion` cuando corresponde.
- Para cuota histórica exigible con índice obligatorio sin valor válido, se bloquea la confirmación; no se crea una obligación base desactualizada como solución silenciosa.
- Para cuota futura donde todavía no corresponde aplicar índice, se mantiene la proyección vigente; `PROYECTADA_SIN_INDICE` queda solo como estado de cálculo/preview, no como `estado_obligacion`.
- Las corridas V2 quedan reservadas para valores publicados después de la generación, obligaciones futuras que pasan a ser alcanzadas, reintentos idempotentes del flujo mensual, actualizaciones posteriores permitidas y correcciones/rectificaciones futuras según #349.

Ventajas:

- Respeta el comportamiento real de `GeneratePlanPagoVentaV2PorBloquesService`.
- Evita doble aplicación sobre obligaciones que ya nacen indexadas.
- Reutiliza el preview/generador V2 y mantiene el cálculo financiero fuera de `comercial`.
- Bloquea faltantes exigibles históricos en vez de crear deuda base silenciosamente desactualizada.
- Mantiene el flujo mensual de corridas para hechos posteriores a la generación.
- Encaja con preparación automática de corridas y `REQUIERE_CORRECCION` para otro valor del mismo mes.

Riesgos:

- Requiere definir formalmente fecha de corte y clasificación de cuotas históricas/futuras.
- Requiere distinguir con precisión obligación ya indexada durante generación vs obligación futura alcanzada posteriormente.
- Requiere tests para evitar doble aplicación de corridas sobre obligaciones con `obligacion_financiera_indexacion` vigente.

Trazabilidad: alta; generación conserva trazabilidad por obligación y corridas posteriores conservan trazabilidad mensual/correctiva.

Atomicidad: recomendable dentro de la generación/confirmación para el alta inicial, sin aplicación inmediata obligatoria de corrida sobre cuotas ya indexadas.

Sincronización: buena; las corridas conservan semántica propia para hechos posteriores y correcciones.

## 11. Alternativa recomendada

Recomendada: **C. Flujo híbrido con indexación en generación y corridas posteriores**.

Justificación:

- Mantiene el alta comercial como origen, pero deja cálculo y trazabilidad financiera en servicios V2.
- Usa el preview de Plan Pago V2 para resolver valores publicados aplicables.
- Si existe valor publicado aplicable, la obligación nace con `importe_total` indexado, composición `AJUSTE_INDEXACION` y `obligacion_financiera_indexacion`.
- Si una cuota histórica exigible no tiene valor válido, la confirmación debe bloquearse.
- Si una cuota es futura, queda proyectada según comportamiento vigente y será alcanzada por corridas mensuales posteriores cuando corresponda.
- No ejecuta inmediatamente una corrida V2 sobre obligaciones ya indexadas por generación.
- Es la opción más compatible con #343/#344 y mantiene #349 como alcance de corrección avanzada.

## 12. Propuesta transaccional

Objetivo final recomendado para confirmación histórica:

1. Crear venta en borrador.
2. Definir condiciones comerciales.
3. Ejecutar preview del Plan Pago V2.
4. Prevalidar valores de índice requeridos según fecha de corte de negocio definida formalmente.
5. Bloquear si una cuota histórica exigible carece de valor válido publicado.
6. Generar plan, bloques, cronograma, relación generadora y obligaciones.
7. Persistir, durante la generación, `AJUSTE_INDEXACION` y `obligacion_financiera_indexacion` cuando el preview ya resolvió un valor publicado aplicable.
8. Confirmar venta.
9. Commit.

La transacción recomendada no incluye una aplicación inmediata obligatoria de corrida V2 sobre cuotas ya indexadas por generación. Las corridas posteriores deben conservar su propia semántica, hash, idempotencia, locks, estados y trazabilidad para publicaciones posteriores, obligaciones futuras alcanzadas o correcciones permitidas.

Si falta un índice exigible o un valor publicado exigible:

- bloquear confirmación;
- rollback completo del intento si el endpoint es completo;
- mantener venta en borrador solo si el flujo granular ya había persistido la venta antes de la prevalidación;
- no dejar obligaciones parciales ni plan incompleto;
- no crear obligaciones base desactualizadas como fallback silencioso;
- no aplicar corridas automáticamente para compensar un faltante de índice obligatorio durante el alta.

## 13. Bloqueos funcionales propuestos

Bloquear confirmación/prevalidación histórica cuando:

- cuota histórica exigible + índice requerido sin valor válido;
- falta configuración de índice en bloque indexado exigible;
- índice no existe, está inactivo, eliminado o anulado;
- `estado_valor_indice != 'PUBLICADO'` para el valor requerido;
- `fecha_publicacion IS NULL` para valor exigible;
- `valor_base_indice <= 0` o `fecha_base_indice` inválida;
- el valor aplicable no pertenece al índice configurado;
- moneda de obligación/bloque incompatible con indexación vigente;
- ya existen obligaciones activas duplicadas para la misma relación generadora y clave funcional;
- hay obligación con pagos, imputaciones, mora incompatible o punitorios donde el motor V2 no pueda aplicar una corrida posterior;
- obligación ya indexada durante generación y se intenta volver a aplicar una corrida inmediata sobre esa misma obligación;
- corrida mensual posterior del mismo plan+bloque+configuración+índice+mes con otro valor: clasificar como `REQUIERE_CORRECCION`, no como alta ordinaria adicional;
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

### PR 1 — Prevalidación histórica

- Detectar historicidad.
- Definir fecha de corte de negocio.
- Clasificar cuotas históricas/futuras.
- Validar valores publicados requeridos.
- Devolver preview sin cambios de deuda.
- Documentar decisión CORE-EF como `PREVIEW_READLIKE` si no persiste.

### PR 2 — Integración con generación vigente

- Reutilizar el preview de Plan Pago V2.
- Confirmar que las obligaciones se materializan con ajuste cuando hay índice publicado aplicable.
- Persistir `AJUSTE_INDEXACION` y `obligacion_financiera_indexacion` mediante el generador vigente.
- Bloquear faltantes exigibles.
- No ejecutar una segunda indexación ni una corrida inmediata sobre obligaciones ya indexadas.

### PR 3 — Integración con corridas posteriores

- Asegurar que obligaciones futuras entren al flujo mensual normal.
- Verificar compatibilidad con preparación por publicación.
- Evitar doble aplicación sobre obligaciones ya indexadas durante generación.
- Mantener `REQUIERE_CORRECCION` para otro valor del mismo mes.

### PR 4 — Importación

Fuera de #345. Corresponde a #346.

### Corrección avanzada

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

- Riesgo de doble ajuste si se aplica una corrida inmediata sobre obligaciones ya indexadas durante generación.
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

El flujo real de alta manual completa es `POST /api/v1/ventas/directa/confirmar-venta-completa`. La fecha histórica efectiva hoy es `fecha_venta`; no existe un campo específico de venta histórica y la fecha de corte histórica no surge de CORE-EF. Plan Pago Venta V2 ya puede generar obligaciones indexadas cuando el preview encuentra valor publicado aplicable, persistiendo `AJUSTE_INDEXACION` y `obligacion_financiera_indexacion`. La alternativa recomendada es un flujo híbrido con indexación en generación, bloqueo de faltantes exigibles y corridas V2 reservadas para hechos posteriores, obligaciones futuras alcanzadas y correcciones fuera de alcance de #345 inicial. Este PR no cierra #345 como funcionalidad completa; deja la propuesta técnica para los PRs siguientes.
