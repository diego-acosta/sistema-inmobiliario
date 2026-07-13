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

La mora reproducible se evalúa con `fecha_vencimiento < fecha_corte`, no con `CURRENT_DATE`.

## Cálculo

- Capital base: composición activa con concepto financiero físico `CAPITAL_VENTA`.
- Ajuste anterior: composición activa con concepto financiero físico `AJUSTE_INDEXACION`, si existe.
- Coeficiente: `valor_indice_aplicado / valor_base_indice`, cuantizado a 8 decimales.
- Ajuste objetivo: `capital_base * (coeficiente - 1)`, cuantizado a 2 decimales.
- Diferencia neta para elegibles: `ajuste_nuevo - ajuste_anterior`.
- Importes y saldos nuevos para elegibles: importes y saldos actuales más diferencia neta.

## Ajuste negativo

La V2 inicial no soporta componentes negativos. Si el ajuste objetivo resulta negativo, el detalle queda `EXCLUIDA` con `AJUSTE_NEGATIVO_NO_SOPORTADO`; las columnas físicas restringidas (`ajuste_nuevo`, `diferencia_neta`, `importe_nuevo`, `saldo_nuevo`) conservan valores no negativos/sin efecto y el ajuste negativo calculado se preserva en `snapshot_despues.ajuste_objetivo_calculado`.

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
