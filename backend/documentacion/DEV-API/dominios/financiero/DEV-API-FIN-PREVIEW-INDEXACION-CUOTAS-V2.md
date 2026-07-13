# Preview de indexación de cuotas V2 — Issue #342

## Contrato

Endpoint implementado: `POST /api/v1/financiero/indexacion-cuotas-v2/preview`.

El request recibe identificadores físicos ya existentes: `id_plan_pago_venta`, `id_plan_pago_venta_bloque`, `id_plan_pago_venta_bloque_indexacion`, `id_indice_financiero`, `id_indice_financiero_valor_aplicado`, `fecha_corte`, `periodo_aplicado` y `persistir`.

## Modos

- `persistir=false`: preview efímero. No inserta cabecera, no inserta detalles y no modifica obligaciones, composiciones, pagos, imputaciones ni saldos.
- `persistir=true`: command write técnico sincronizable. Exige headers CORE-EF comunes (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`) y persiste una corrida con estado físico existente `PREVISUALIZADA` y detalle por obligación analizada. No aplica indexación ni actualiza deuda.

## Cálculo

- Capital base: composición activa con concepto financiero físico `CAPITAL_VENTA`.
- Ajuste anterior: composición activa con concepto financiero físico `AJUSTE_INDEXACION`, si existe.
- Coeficiente: `valor_indice_aplicado / valor_base_indice`, cuantizado a 8 decimales.
- Ajuste nuevo: `capital_base * (coeficiente - 1)`, cuantizado a 2 decimales.
- Diferencia neta: `ajuste_nuevo - ajuste_anterior`.
- Importes y saldos nuevos: importes y saldos actuales más diferencia neta.

## Elegibilidad

Estados físicos usados: `ELEGIBLE` y `EXCLUIDA`.

Motivos controlados actuales:

- `OBLIGACION_NO_ACTIVA`.
- `SIN_CAPITAL_INDEXABLE`.
- `AJUSTE_INDEXACION_NEGATIVO`.

Pagos, imputaciones y mora se informan como advertencias (`OBLIGACION_CON_PAGOS`, `OBLIGACION_CON_IMPUTACIONES`, `OBLIGACION_CON_MORA`) porque el diseño vigente no confirma que deban excluir automáticamente del preview. No se implementan locks funcionales nuevos.

## Hash reproducible

Se genera con SHA-256 sobre JSON canónico ordenado que incluye alcance, valores de índice, coeficiente, obligaciones ordenadas, versiones esperadas y resultados determinantes. Excluye timestamps de ejecución e IDs generados por la corrida.

## Decisión CORE-EF

- Preview efímero: `PREVIEW_READLIKE`, sin headers write.
- Preview persistido: `COMMAND_WRITE_TECNICO`, usa helper común CORE-EF, idempotencia por `op_id + payload_hash + hash_corrida`, sin `If-Match-Version` porque no modifica entidad versionada existente, sin outbox, sin lock lógico persistente, versionado snapshot-only y transacción atómica de cabecera/detalles.

## Límite respecto de #343

No aplica indexación, no crea ni actualiza `AJUSTE_INDEXACION`, no incrementa versiones y no valida aplicación final. La aplicación posterior debe validar los snapshots guardados antes de modificar deuda.
