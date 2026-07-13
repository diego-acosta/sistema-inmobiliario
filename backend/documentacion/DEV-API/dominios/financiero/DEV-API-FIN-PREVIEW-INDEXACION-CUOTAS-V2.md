# Preview de indexación de cuotas V2 — Issue #342

## Contrato

Endpoint implementado: `POST /api/v1/financiero/indexacion-cuotas-v2/preview`.

El request recibe identificadores físicos ya existentes: `id_plan_pago_venta`, `id_plan_pago_venta_bloque`, `id_plan_pago_venta_bloque_indexacion`, `id_indice_financiero`, `id_indice_financiero_valor_aplicado`, `fecha_corte`, `periodo_aplicado`, `persistir` y `motivo`.

## Modos

- `persistir=false`: preview efímero. No inserta cabecera, no inserta detalles y no modifica obligaciones, composiciones, pagos, imputaciones ni saldos.
- `persistir=true`: command write técnico sincronizable. Exige headers CORE-EF comunes (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) y persiste una corrida con estado físico existente `PREVISUALIZADA` y detalle por obligación analizada. No aplica indexación ni actualiza deuda.

## Estados y elegibilidad

Estados reales elegibles en V2 inicial, si no tienen efectos incompatibles: `PROYECTADA`, `EMITIDA`, `EXIGIBLE` y `VENCIDA`.

Estados no elegibles: `PARCIALMENTE_CANCELADA`, `CANCELADA`, `ANULADA`, `REEMPLAZADA`, `PENDIENTE_AJUSTE` u otros estados no listados como elegibles.

Matriz de efectos posteriores:

- Aplicaciones/imputaciones activas: `EXCLUIDA` con `OBLIGACION_CON_IMPUTACIONES_ACTIVAS`.
- Pagos activos aplicados: `EXCLUIDA` con `OBLIGACION_CON_PAGOS_ACTIVOS`.
- Punitorios/mora persistida incompatible: `EXCLUIDA` con `OBLIGACION_CON_MORA_INCOMPATIBLE`.
- Recibos/documentos congelantes: si existe evidencia física futura, `EXCLUIDA` con `OBLIGACION_CON_RECIBOS_CONGELANTES`; en el schema reconstruido actual no existe tabla física de recibos internos vinculables al preview.
- `VENCIDA` sin efectos posteriores: elegible con advertencia `OBLIGACION_VENCIDA_SIN_EFECTOS_POSTERIORES`.

El alcance temporal del preview incluye únicamente obligaciones del bloque con `fecha_vencimiento IS NULL OR fecha_vencimiento <= fecha_corte`; las obligaciones posteriores al corte no forman parte de `detalles`, cantidades, totales, `snapshot_versiones` ni `hash_corrida`. La mora reproducible se evalúa con `fecha_vencimiento < fecha_corte`, no con `CURRENT_DATE`.

## Cálculo

- Capital base: composición activa con concepto financiero físico `CAPITAL_VENTA`.
- Ajuste anterior: composición activa con concepto financiero físico `AJUSTE_INDEXACION`, si existe.
- Coeficiente: `valor_indice_aplicado / valor_base_indice`, cuantizado a 8 decimales.
- Ajuste objetivo: `capital_base * (coeficiente - 1)`, cuantizado a 2 decimales.
- Diferencia neta para elegibles: `ajuste_nuevo - ajuste_anterior`. Para excluidas siempre es `0` y los totales se calculan desde los valores persistibles sin efecto.
- Importes y saldos nuevos para elegibles: importes y saldos actuales más diferencia neta.

## Ajuste negativo

La V2 inicial no soporta componentes negativos. Si el ajuste objetivo resulta negativo, el detalle queda `EXCLUIDA` con `AJUSTE_NEGATIVO_NO_SOPORTADO`; las columnas físicas restringidas/persistibles conservan ausencia de modificación (`ajuste_nuevo = ajuste_anterior`, `diferencia_neta = 0`, `importe_nuevo = importe_anterior`, `saldo_nuevo = saldo_anterior`) y el ajuste negativo calculado se preserva en `snapshot_despues.ajuste_objetivo_calculado`.

## Snapshots

Cada detalle persistido guarda snapshots reproducibles:

- `snapshot_antes`: estado, versión, capital, ajuste anterior, importe, saldo, composiciones relevantes, trazabilidad vigente y flags de pagos/imputaciones/mora/punitorios/recibos.
- `snapshot_despues`: elegibilidad, motivo, ajuste objetivo calculado, ajuste persistible, diferencia, importe/saldo nuevos, advertencias y versión esperada.

## Fecha de publicación

La cabecera persistida conserva `fecha_publicacion_indice` desde `indice_financiero_valor.fecha_publicacion` del valor aplicado.

## Hashes e idempotencia

- `payload_hash`: SHA-256 del request canónico funcional (`alcance`, `fecha_corte`, `periodo_aplicado`, `origen_corrida`, `motivo` y `persistir`), sin timestamps ni IDs generados.
- `hash_corrida`: SHA-256 del cálculo canónico, incluyendo alcance, valores, coeficiente, IDs de composiciones/trazabilidad, versiones, elegibilidad, advertencias, motivos y snapshots determinantes. El orden de obligaciones es estable por `id_obligacion_financiera`.
- Reintento con mismo `X-Op-Id`, mismo `payload_hash` y mismo `hash_corrida`: reutiliza la corrida.
- Mismo `X-Op-Id` con payload/hash distinto: `IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE`.

## Decisión CORE-EF

- Preview efímero: `PREVIEW_READLIKE`, sin headers write.
- Preview persistido: `COMMAND_WRITE_TECNICO`, usa helper común CORE-EF, sin `If-Match-Version` porque no modifica entidad versionada existente.
- Metadata CORE-EF persistida en cabecera y detalle: `op_id`, `op_id_alta`, `op_id_ultima_modificacion`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `id_usuario` e `id_sucursal` donde existen columnas físicas.
- Outbox: NO APLICA; no hay evento de negocio publicado.
- Lock lógico: NO APLICA en preview; no aplica deuda ni reserva obligaciones.
- Versionado: snapshot-only, no incrementa versiones.
- Transacción: el repositorio sigue el patrón vigente del proyecto y hace `commit` solo después de insertar cabecera y todos los detalles; si falla un detalle antes del commit, no queda cabecera ni detalle parcial.

## Límite respecto de #343

No aplica indexación, no crea ni actualiza `AJUSTE_INDEXACION`, no incrementa versiones y no valida aplicación final. La aplicación posterior debe validar los snapshots guardados antes de modificar deuda.

---

# Aplicación de corridas de indexación de cuotas V2 — Issue #343

Endpoint implementado: `POST /api/v1/financiero/indexacion-cuotas-v2/corridas/{id_corrida_indexacion_financiera}/aplicar`.

## Decisión CORE-EF

- Clasificación: `COMMAND_WRITE_NEGOCIO`.
- Headers obligatorios: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version`; se parsean con el helper común de CORE-EF.
- Idempotencia: aplica por `X-Op-Id` de aplicación. Mismo `op_id` sobre la misma corrida ya `APLICADA` devuelve `modo=IDEMPOTENTE`; mismo `op_id` sobre otra corrida se rechaza con conflicto.
- Outbox: aplica dentro de la transacción funcional con `outbox_event.event_type = financiero.indexacion_cuotas_v2.corrida_aplicada` y `aggregate_type = corrida_indexacion_financiera`.
- Lock lógico: aplica por obligación usando `lock_logico` con `tipo_entidad = OBLIGACION_FINANCIERA`, orden estable por `id_obligacion_financiera`, `op_id` como owner y liberación al finalizar la aplicación.
- Versionado: aplica optimistic locking sobre `corrida_indexacion_financiera.version_registro` vía `If-Match-Version` y sobre cada `obligacion_financiera.version_registro` persistida en el detalle del preview.
- Rollback/transacción: obligación, composición, trazabilidad, detalle, corrida y outbox se modifican en una transacción funcional. Ante drift funcional se revierte y se marca la corrida `FALLIDA` en transacción técnica separada si la corrida no fue aplicada.

## Contrato

Request body:

```json
{
  "hash_corrida": "sha256 opcional esperado por el cliente"
}
```

Response exitosa:

```json
{
  "ok": true,
  "data": {
    "modo": "APLICADA | IDEMPOTENTE",
    "id_corrida_indexacion_financiera": 123,
    "estado_corrida": "APLICADA",
    "cantidad_aplicada": 2,
    "hash_corrida": "...",
    "idempotente": false
  }
}
```

## Precondiciones y límites

- Solo aplica corridas persistidas no borradas en estados físicos `PREVISUALIZADA` o `PENDIENTE_APLICACION`.
- No confía en importes enviados por cliente; usa cabecera y detalles persistidos.
- Rechaza hash esperado incompatible, corrida reemplazada, corrida no aplicable, versión de corrida incompatible, versión de obligación incompatible, drift de capital, drift de ajuste previo, pagos/imputaciones activos, punitorios incompatibles y locks lógicos activos de otro owner.
- Las excluidas del preview no modifican obligaciones ni se cuentan como aplicadas.
- No implementa reversión, corrección avanzada, cuotas pagadas/parcialmente canceladas, reimputación, notas de crédito, bonificación por ajuste negativo, jobs ni publicación automática; esos límites quedan fuera del alcance de #343 y de #349.

## Persistencia aplicada

Para cada detalle elegible confirmado:

- valida `CAPITAL_VENTA` real por composición persistida;
- crea o actualiza la composición activa `AJUSTE_INDEXACION` con el importe objetivo del detalle, sin acumular ciegamente;
- actualiza `obligacion_financiera.importe_total`, `saldo_pendiente`, `op_id_ultima_modificacion`, `id_instalacion_ultima_modificacion` y el versionado por triggers CORE-EF;
- registra/actualiza `obligacion_financiera_indexacion` con índice, valor aplicado, coeficiente y referencia técnica a la corrida;
- completa el detalle con `version_resultante`, ids finales de ajuste/trazabilidad y snapshot posterior;
- actualiza la cabecera a `APLICADA`, `fecha_aplicacion`, `cantidad_aplicada`, metadata CORE-EF y limpia campos de error;
- inserta el evento transaccional en `outbox_event`.

## FALLIDA

Si una validación de aplicación falla después de iniciar la transacción funcional, la transacción se revierte y se abre una transacción técnica separada para persistir `estado_corrida = FALLIDA`, `codigo_error`, `etapa_error`, `diagnostico_tecnico`, `op_id_ultima_modificacion` e `id_instalacion_ultima_modificacion`. No se sobrescribe una corrida ya `APLICADA`.
