# AUDITORIA-SQL-FIN - Auditoria documental vs SQL financiero

Estado: AUDITORIA HISTORICA / PARCIALMENTE OBSOLETA

Fecha: 2026-04-29

Nota 2026-04-30:

Esta auditoria queda como registro historico. La documentacion operativa vigente del dominio financiero fue alineada contra el backend real en:

- `MODELO-FINANCIERO-FIN.md`
- `SRV-FIN-003-generacion-de-obligaciones.md`
- `SRV-FIN-008-gestion-de-imputacion-financiera.md`
- `SRV-FIN-013-generacion-de-mora.md`
- `catalogos/RN-FIN.md`
- `catalogos/EST-FIN.md`
- `backend/documentacion/DEV-API/dominios/financiero/DEV-API-FIN-001.md`

Algunas brechas indicadas abajo, como la ausencia de `saldo_componente`, ya no reflejan el SQL/backend usado por los tests financieros actuales.

## 1. Alcance

Esta auditoria compara la documentacion financiera vigente contra el SQL real disponible en `backend/database`.

Documentos revisados:

- `backend/documentacion/DER/DER-FINANCIERO.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/MODELO-FINANCIERO-FIN.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/RN-FIN.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/EST-FIN.md`
- `backend/documentacion/DEV-API/dominios/financiero/DEV-API-FIN-001.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-003-generacion-de-obligaciones.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-006-cronograma-y-obligaciones.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/SRV-FIN-008-gestion-de-imputacion-financiera.md`
- `backend/documentacion/DEV-SRV/dominios/financiero/catalogos/TIPO-OBLIGACION-FIN.md`

SQL revisado:

- `backend/database/schema_inmobiliaria_20260418.sql`
- `backend/database/patch_*.sql`
- `backend/database/seed_minimo.sql`
- `backend/database/seed_test_baseline.sql`

No se modifico SQL, backend ni tests.

## 2. Resumen ejecutivo

El SQL real ya contiene las entidades estructurales principales del modelo financiero:

- `relacion_generadora`
- `obligacion_financiera`
- `composicion_obligacion`
- `concepto_financiero`
- `aplicacion_financiera`

Tambien existen FKs relevantes, indices, triggers de consistencia de imputacion y un trigger que recalcula `obligacion_financiera.saldo_pendiente` desde `aplicacion_financiera`.

La brecha principal no es la ausencia completa del modelo, sino que la documentacion conceptual reciente es mas rica que la estructura SQL vigente. En especial:

- no existe `composicion_obligacion.saldo_componente`;
- no existe `moneda` en `obligacion_financiera` ni en `composicion_obligacion`;
- `concepto_financiero` existe, pero con campos minimos y nombres mas cortos;
- los estados normalizados documentados no tienen `CHECK` SQL;
- no hay vinculos fisicos para reemplazo, reemision o refinanciacion;
- no hay seeds para el catalogo base de `concepto_financiero`;
- OBSOLETO 2026-04-30: esta brecha ya no debe tomarse como vigente en la documentacion operativa actual.

## 3. Tabla documentado vs existente en SQL

| Elemento documentado | Estado SQL | Evidencia SQL | Brecha |
|---|---:|---|---|
| `relacion_generadora` | EXISTE | Tabla con `id_relacion_generadora`, `tipo_origen`, `id_origen`, `estado_relacion_generadora` | Parcial: origen fisico limitado por trigger a `venta` y `contrato_alquiler`; documentacion contempla mas origenes conceptuales. |
| `obligacion_financiera` | EXISTE | Tabla con `id_obligacion_financiera`, `id_relacion_generadora`, `codigo_obligacion`, `fecha_emision`, `fecha_vencimiento`, `importe_original`, `saldo_pendiente`, `estado_obligacion` | Parcial: faltan moneda, periodos, acumulados, flags y estados normalizados controlados. |
| `composicion_obligacion` | EXISTE | Tabla con `id_composicion_obligacion`, `id_obligacion_financiera`, `id_concepto_financiero`, `importe`, `observaciones` | Parcial: falta `saldo_componente`, moneda, orden, estado y detalle de calculo. |
| `concepto_financiero` | EXISTE | Tabla con `codigo_concepto`, `nombre_concepto`, `tipo_concepto`, `estado_concepto` | Parcial: faltan descripcion, naturaleza y banderas economicas documentadas. |
| `aplicacion_financiera` | EXISTE | Tabla con `id_movimiento_financiero`, `id_obligacion_financiera`, `id_composicion_obligacion`, `importe_aplicado` | Parcial: no existe `estado_aplicacion`; permite imputacion por componente, pero no mantiene saldo por componente persistido. |
| Saldo total de obligacion | EXISTE | `obligacion_financiera.saldo_pendiente` | Existe y se recalcula por trigger desde aplicaciones contra obligacion. |
| Saldo por componente | NO EXISTE | No hay columna `saldo_componente` en `composicion_obligacion` | Brecha critica contra politica documental nueva. |
| Moneda de obligacion | NO EXISTE | No hay `moneda` en `obligacion_financiera` | Brecha para obligaciones multimoneda. |
| Moneda de composicion | NO EXISTE | No hay `moneda_componente` en `composicion_obligacion` | Brecha para conciliacion por componente si difiere moneda. |
| `estado_obligacion` | EXISTE | `obligacion_financiera.estado_obligacion varchar(30)` | Sin `CHECK` de estados normalizados ni transiciones. |
| Reemplazo / reemision / refinanciacion | NO EXISTE | No hay FK a obligacion nueva/anterior ni tabla de trazabilidad especifica | Brecha para estado `REEMPLAZADA`. |
| Tipo de obligacion operativo | NO EXISTE | No hay columna `tipo_obligacion` | Correcto respecto de la decision documental: no usar tipo rigido como eje normativo. |

## 4. Campos faltantes

### 4.1 `concepto_financiero`

Documentado pero no existente fisicamente:

- `descripcion_concepto_financiero`
- `naturaleza_concepto`
- `afecta_capital`
- `afecta_interes`
- `afecta_mora`
- `afecta_impuesto`
- `afecta_caja`
- `es_imputable`
- `permite_saldo`
- `observaciones`

### 4.2 `obligacion_financiera`

Documentado pero no existente fisicamente:

- `descripcion_operativa`
- `fecha_generacion`
- `periodo_desde`
- `periodo_hasta`
- `fecha_cierre`
- `importe_total`
- `importe_cancelado_acumulado`
- `importe_bonificado_acumulado`
- `importe_anulado_acumulado`
- `moneda`
- `es_exigible`
- `es_proyectada`
- `es_emitida`
- `es_vencida`
- `genera_recibo`
- `afecta_estado_cuenta`
- `afecta_libre_deuda`
- vinculo a obligacion reemplazante, obligacion reemplazada o proceso de refinanciacion/reemision

### 4.3 `composicion_obligacion`

Documentado pero no existente fisicamente:

- `orden_composicion`
- `estado_composicion_obligacion`
- `importe_componente`
- `saldo_componente`
- `moneda_componente`
- `detalle_calculo`

### 4.4 `aplicacion_financiera`

Documentado o requerido por estados de imputacion, pero no existente fisicamente:

- `estado_aplicacion`
- politica fisica de distribucion de pago global hacia componentes
- trazabilidad explicita de reversa/anulacion si se requiere separar de registros negativos o nuevos movimientos

## 5. Campos existentes con nombre distinto

| Concepto documental | Campo SQL vigente | Observacion |
|---|---|---|
| `codigo_concepto_financiero` | `concepto_financiero.codigo_concepto` | Equivalente funcional probable. Documentar/migrar con cuidado para no duplicar. |
| `nombre_concepto_financiero` | `concepto_financiero.nombre_concepto` | Equivalente funcional probable. |
| `tipo_concepto_financiero` | `concepto_financiero.tipo_concepto` | Equivalente parcial; falta semantica normalizada. |
| `estado_concepto_financiero` | `concepto_financiero.estado_concepto` | Equivalente parcial; falta catalogo de estados si aplica. |
| `codigo_obligacion_financiera` | `obligacion_financiera.codigo_obligacion` | Equivalente funcional probable. |
| `importe_total` | `obligacion_financiera.importe_original` | Equivalente parcial: `importe_original` refleja alta inicial, no necesariamente total vigente tras anulaciones/bonificaciones/reemplazos. |
| `importe_componente` | `composicion_obligacion.importe` | Equivalente funcional probable. |

## 6. Constraints existentes

Existen constraints relevantes:

- PKs en `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `concepto_financiero`, `aplicacion_financiera`.
- UNIQUE por `uid_global` en las entidades financieras principales.
- UNIQUE `uq_concepto_codigo` sobre `concepto_financiero.codigo_concepto`.
- FK `obligacion_financiera.id_relacion_generadora -> relacion_generadora.id_relacion_generadora`.
- FK `composicion_obligacion.id_obligacion_financiera -> obligacion_financiera.id_obligacion_financiera`.
- FK `composicion_obligacion.id_concepto_financiero -> concepto_financiero.id_concepto_financiero`.
- FK `aplicacion_financiera.id_obligacion_financiera -> obligacion_financiera.id_obligacion_financiera`.
- FK `aplicacion_financiera.id_composicion_obligacion -> composicion_obligacion.id_composicion_obligacion`.
- FK `aplicacion_financiera.id_movimiento_financiero -> movimiento_financiero.id_movimiento_financiero`.
- `chk_obligacion_financiera_fechas`: `fecha_vencimiento >= fecha_emision` si hay vencimiento.
- `chk_obligacion_importes_no_negativos`: `importe_original >= 0` y `saldo_pendiente >= 0`.
- `chk_obligacion_saldo_no_supera_original`: `saldo_pendiente <= importe_original`.
- `chk_composicion_importes_no_negativos`: `composicion_obligacion.importe >= 0`.
- `chk_aplicacion_financiera_importe`: `importe_aplicado >= 0`.
- `chk_relacion_generadora_estado`: estados fisicos de relacion `BORRADOR`, `ACTIVA`, `CANCELADA`, `FINALIZADA`.

## 7. Constraints faltantes

Faltan constraints o validaciones fisicas para reglas documentadas:

- asegurar que toda `obligacion_financiera` tenga una o mas `composicion_obligacion`;
- asegurar que la suma de `composicion_obligacion.importe` coincida con `obligacion_financiera.importe_original` o con el total definido;
- asegurar `saldo_pendiente = SUM(saldo_componente)` cuando exista saldo por componente;
- impedir `CANCELADA` con `saldo_pendiente > 0`;
- impedir `CANCELADA` con componentes activos con saldo vivo;
- restringir `estado_obligacion` a estados normalizados documentados;
- controlar transiciones validas de `estado_obligacion`;
- impedir cambios de saldo sin `aplicacion_financiera`, anulacion formal o credito documentado;
- vincular `REEMPLAZADA` a obligacion nueva o proceso formal;
- validar moneda obligatoria cuando se incorpore fisicamente;
- validar `tipo_origen` de `relacion_generadora` contra todos los origenes documentados o contra un catalogo formal.

## 8. Triggers existentes

Existen triggers relevantes:

- `trg_biu_relacion_generadora_polimorfica`: valida `relacion_generadora.tipo_origen` e `id_origen`.
- `trg_biu_aplicacion_financiera_validar_consistencia`: valida que la composicion pertenezca a la obligacion y evita sobreaplicacion por composicion u obligacion.
- `trg_aiud_aplicacion_financiera_refrescar_saldo_obligacion`: recalcula `obligacion_financiera.saldo_pendiente` como `importe_original - SUM(aplicacion_financiera.importe_aplicado)`.
- triggers Core EF de insert/update sobre entidades financieras.

Observacion critica: el trigger de saldo opera a nivel obligacion. Aunque `aplicacion_financiera.id_composicion_obligacion` existe, no hay persistencia ni refresco de `saldo_componente`.

## 9. Triggers faltantes

Faltan triggers o mecanismos equivalentes para:

- mantener `composicion_obligacion.saldo_componente`;
- distribuir pagos globales sin componente segun prioridad documental;
- mantener estado `PARCIALMENTE_CANCELADA` / `CANCELADA` segun saldo;
- derivar o materializar `VENCIDA`;
- bloquear transiciones prohibidas de `estado_obligacion`;
- validar obligacion con al menos una composicion antes de emitir/exigir;
- validar suma de composiciones contra total de obligacion;
- mantener trazabilidad de reemplazo/reemision/refinanciacion.

## 10. Seeds faltantes

No se encontraron inserts en `seed_minimo.sql` ni `seed_test_baseline.sql` para `concepto_financiero` ni para el catalogo base documentado.

Catalogo base documentado pendiente de seed:

- `CAPITAL_VENTA`
- `ANTICIPO_VENTA`
- `SALDO_EXTRAORDINARIO`
- `CANON_LOCATIVO`
- `EXPENSA_TRASLADADA`
- `SERVICIO_TRASLADADO`
- `IMPUESTO_TRASLADADO`
- `INTERES_FINANCIERO`
- `INTERES_MORA`
- `PUNITORIO`
- `CARGO_ADMINISTRATIVO`
- `LIQUIDACION_FINAL`
- `REFINANCIACION`
- `CANCELACION_ANTICIPADA`
- `AJUSTE_INDEXACION`
- `CREDITO_MANUAL`
- `DEBITO_MANUAL`

## 11. Riesgos de implementacion

- Riesgo de falsa completitud: las tablas existen, pero no soportan todo el contrato conceptual documentado.
- Riesgo de inconsistencia de saldos: `saldo_pendiente` se recalcula por obligacion, pero no hay saldo vivo persistido por componente.
- Riesgo de estados libres: `estado_obligacion` acepta cualquier `varchar(30)` y no impone el ciclo documentado.
- Riesgo de origen limitado: `relacion_generadora.tipo_origen` solo acepta `venta` y `contrato_alquiler` en trigger, mientras la documentacion contempla servicios trasladados, impuestos u otros origenes conceptuales.
- Riesgo de multimoneda: obligaciones y composiciones no guardan moneda fisica.
- Riesgo de implementacion API prematura: varios endpoints documentados siguen en estado conceptual/no implementado y no deben asumirse como disponibles.
- Riesgo de migracion de nombres: algunos campos documentados tienen equivalentes SQL con nombres distintos; duplicarlos sin decision puede fragmentar el modelo.

## 12. Recomendacion de migracion minima

Sin ejecutar cambios todavia, la migracion minima futura deberia priorizar:

1. Confirmar nomenclatura fisica: mantener campos SQL actuales (`codigo_concepto`, `importe`, `importe_original`) o migrar a nombres documentales. Evitar columnas duplicadas con la misma semantica.
2. Agregar `saldo_componente` a `composicion_obligacion` o definir formalmente que se deriva de `importe - SUM(aplicaciones)` por componente. La documentacion actual prefiere saldo operativo real por componente.
3. Agregar soporte de moneda en `obligacion_financiera` y, si corresponde, `composicion_obligacion`.
4. Agregar restricciones o validaciones transaccionales para estados de `obligacion_financiera`.
5. Agregar mecanismo de trazabilidad para reemplazo/reemision/refinanciacion.
6. Sembrar `concepto_financiero` con el catalogo base documentado.
7. Ajustar `trg_relacion_generadora_polimorfica` o reemplazarlo por una politica extensible de origenes financieros si se incorporan servicios, impuestos u otros origenes.
8. Reconciliar `saldo_pendiente` contra componentes y aplicaciones con una unica regla de verdad.

## 13. Que NO tocar todavia

- No crear columna `tipo_obligacion`.
- No crear catalogo operativo de tipos de obligacion.
- No modificar endpoints hasta cerrar primero la brecha SQL/backend.
- No cambiar triggers de imputacion sin pruebas especificas de saldos y sobreaplicacion.
- No ampliar `tipo_origen` de `relacion_generadora` sin definir ownership y origen real de cada hecho.
- No introducir refinanciacion/reemision fisica sin decidir trazabilidad y ciclo de vida.
- No modificar seeds productivos hasta confirmar los codigos definitivos de `concepto_financiero`.

## 14. Conclusion

La estructura SQL vigente soporta un MVP financiero con relaciones generadoras, obligaciones, composiciones, conceptos e imputaciones. La documentacion financiera actual define un modelo objetivo mas completo. La brecha critica es la falta de soporte fisico para saldo por componente, estados/transiciones normalizadas y catalogo semantico completo de conceptos financieros.

La siguiente tarea recomendada es redactar una propuesta tecnica de migracion SQL/backend incremental, sin implementar todavia, que preserve el modelo existente y cierre primero saldos por componente, moneda, estados y seeds de `concepto_financiero`.
