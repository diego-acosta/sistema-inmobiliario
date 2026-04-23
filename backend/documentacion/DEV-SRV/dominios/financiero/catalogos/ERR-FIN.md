# ERR-FIN — Errores del dominio Financiero

## Objetivo
Definir errores del dominio financiero.

## Alcance
Incluye relaciones generadoras, obligaciones, imputaciones, ajustes y consultas.

---

## A. Errores de relaciones generadoras

### ERR-FIN-001 — Relación generadora no encontrada
- codigo: relacion_generadora_no_encontrada
- descripcion: No existe la relación generadora solicitada en el contexto informado.
- tipo: funcional
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-002 — Relación generadora inactiva
- codigo: relacion_generadora_inactiva
- descripcion: La relación generadora existe pero no se encuentra activa para la operación solicitada.
- tipo: funcional
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-003 — Relación generadora cancelada
- codigo: relacion_generadora_cancelada
- descripcion: La relación generadora fue cancelada y no admite nuevas operaciones incompatibles con ese estado.
- tipo: funcional
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-004 — Relación generadora finalizada
- codigo: relacion_generadora_finalizada
- descripcion: La relación generadora ya se encuentra finalizada y no admite nuevas mutaciones incompatibles.
- tipo: funcional
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-005 — Relación generadora duplicada
- codigo: relacion_generadora_duplicada
- descripcion: Ya existe una relación generadora equivalente e incompatible con la nueva alta.
- tipo: integridad
- aplica_a: relacion_generadora
- origen: DER
- es_reintento_valido: no

### ERR-FIN-006 — Estado de relación inválido
- codigo: estado_relacion_invalido
- descripcion: El estado actual de la relación generadora no permite ejecutar la operación solicitada.
- tipo: validacion
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-007 — Transición de estado de relación inválida
- codigo: transicion_estado_relacion_invalida
- descripcion: La transición entre estados de la relación generadora no es válida según el ciclo de vida definido.
- tipo: validacion
- aplica_a: relacion_generadora
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de obligaciones

### ERR-FIN-008 — Obligación no encontrada
- codigo: obligacion_no_encontrada
- descripcion: No existe la obligación financiera solicitada.
- tipo: funcional
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-009 — Obligación inactiva
- codigo: obligacion_inactiva
- descripcion: La obligación existe pero no se encuentra operativa para la acción requerida.
- tipo: funcional
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-010 — Obligación duplicada
- codigo: obligacion_duplicada
- descripcion: Ya existe una obligación equivalente que impide registrar otra con la misma identidad funcional.
- tipo: integridad
- aplica_a: obligacion_financiera
- origen: DER
- es_reintento_valido: no

### ERR-FIN-011 — Obligación sin relación
- codigo: obligacion_sin_relacion
- descripcion: La obligación no posee una relación generadora válida asociada.
- tipo: integridad
- aplica_a: obligacion_financiera
- origen: DER
- es_reintento_valido: no

### ERR-FIN-012 — Estado de obligación inválido
- codigo: estado_obligacion_invalido
- descripcion: El estado actual de la obligación no permite la operación solicitada.
- tipo: validacion
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-013 — Saldo negativo
- codigo: saldo_negativo
- descripcion: La operación produciría un saldo negativo no permitido para la obligación.
- tipo: integridad
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-014 — Inconsistencia de obligación
- codigo: inconsistencia_obligacion
- descripcion: La obligación presenta inconsistencias de monto, estado, composición o relación asociada.
- tipo: integridad
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-015 — Obligación vencida inválida
- codigo: obligacion_vencida_invalida
- descripcion: La condición de vencimiento de la obligación no resulta coherente con su estado o fechas.
- tipo: validacion
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-016 — Monto de obligación inválido
- codigo: monto_obligacion_invalido
- descripcion: El monto informado para la obligación no es válido para su generación o ajuste.
- tipo: validacion
- aplica_a: obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de imputaciones financieras

### ERR-FIN-017 — Imputación no encontrada
- codigo: imputacion_no_encontrada
- descripcion: No existe la imputación financiera solicitada.
- tipo: funcional
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-018 — Imputación inválida
- codigo: imputacion_invalida
- descripcion: La imputación solicitada no cumple las reglas financieras aplicables.
- tipo: validacion
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-019 — Imputación duplicada
- codigo: imputacion_duplicada
- descripcion: Ya existe una imputación equivalente para el mismo pago, obligación y contexto.
- tipo: integridad
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-020 — Monto de imputación inválido
- codigo: monto_imputacion_invalido
- descripcion: El monto de la imputación no es válido para la aplicación solicitada.
- tipo: validacion
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-021 — Imputación excede saldo
- codigo: imputacion_excede_saldo
- descripcion: El monto a imputar excede el saldo vigente de la obligación objetivo.
- tipo: validacion
- aplica_a: aplicacion_financiera, obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-022 — Imputación sin obligación
- codigo: imputacion_sin_obligacion
- descripcion: La imputación no cuenta con una obligación válida sobre la cual aplicarse.
- tipo: integridad
- aplica_a: aplicacion_financiera
- origen: DER
- es_reintento_valido: no

### ERR-FIN-023 — Conflicto de imputación múltiple
- codigo: conflicto_imputacion_multiple
- descripcion: La distribución de una imputación múltiple entra en conflicto con otras aplicaciones o restricciones vigentes.
- tipo: concurrencia
- aplica_a: aplicacion_financiera, movimiento_financiero
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-FIN-024 — Inconsistencia de imputación
- codigo: inconsistencia_imputacion
- descripcion: La imputación presenta inconsistencias entre pago, obligación, monto o saldo resultante.
- tipo: integridad
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-025 — Reversión de imputación inválida
- codigo: reversion_imputacion_invalida
- descripcion: La imputación no puede revertirse en el estado actual del proceso financiero.
- tipo: validacion
- aplica_a: aplicacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de ajustes financieros

### ERR-FIN-026 — Ajuste no encontrado
- codigo: ajuste_no_encontrado
- descripcion: No existe el ajuste financiero solicitado.
- tipo: funcional
- aplica_a: ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-027 — Ajuste inválido
- codigo: ajuste_invalido
- descripcion: El ajuste financiero no cumple las condiciones o reglas exigidas por el dominio.
- tipo: validacion
- aplica_a: ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-028 — Ajuste duplicado
- codigo: ajuste_duplicado
- descripcion: Ya existe un ajuste equivalente e incompatible con el nuevo ajuste propuesto.
- tipo: integridad
- aplica_a: ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-029 — Tipo de ajuste inválido
- codigo: tipo_ajuste_invalido
- descripcion: El tipo de ajuste informado no es válido para la operación o entidad objetivo.
- tipo: validacion
- aplica_a: ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-030 — Aplicación de ajuste inválida
- codigo: aplicacion_ajuste_invalida
- descripcion: No es posible aplicar el ajuste en el contexto o estado actual de la obligación.
- tipo: validacion
- aplica_a: ajuste_financiero, obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-031 — Inconsistencia de ajuste
- codigo: inconsistencia_ajuste
- descripcion: El ajuste presenta inconsistencias de cálculo, contexto o trazabilidad.
- tipo: integridad
- aplica_a: ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de consultas financieras

### ERR-FIN-032 — Consulta financiera inválida
- codigo: consulta_financiera_invalida
- descripcion: Los parámetros o el contexto de la consulta financiera no son válidos.
- tipo: validacion
- aplica_a: consultas_financieras
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-033 — Inconsistencia de cálculo de deuda
- codigo: inconsistencia_calculo_deuda
- descripcion: El cálculo de deuda a fecha o consolidado produjo un resultado inconsistente con el estado financiero esperado.
- tipo: integridad
- aplica_a: consultas_financieras, obligacion_financiera
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-034 — Inconsistencia de resultado financiero
- codigo: inconsistencia_resultado_financiero
- descripcion: El resultado de la consulta financiera no resulta coherente con las entidades o filtros aplicados.
- tipo: integridad
- aplica_a: consultas_financieras
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores transversales financieros

### ERR-FIN-035 — Versión esperada inválida
- codigo: version_esperada_invalida
- descripcion: La versión esperada no coincide con la versión vigente de la entidad financiera.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-036 — Lock lógico activo
- codigo: lock_logico_activo
- descripcion: La entidad financiera se encuentra protegida por un lock lógico activo.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-037 — Recurso bloqueado
- codigo: recurso_bloqueado
- descripcion: El recurso financiero no puede modificarse por una restricción o bloqueo vigente.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-038 — Op id duplicado
- codigo: op_id_duplicado
- descripcion: La operación financiera ya fue registrada con el mismo identificador idempotente.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-039 — Op id duplicado con payload distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: El identificador de operación ya existe pero con un payload distinto al actual.
- tipo: integridad
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: no

### ERR-FIN-040 — Conflicto de concurrencia
- codigo: conflicto_concurrencia
- descripcion: La operación entró en conflicto con otra mutación concurrente sobre la misma entidad o proceso financiero.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-041 — Inconsistencia de contexto técnico
- codigo: inconsistencia_contexto_tecnico
- descripcion: El contexto técnico de la operación no es válido o no resulta coherente para procesar el cambio.
- tipo: integridad
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: no

### ERR-FIN-042 — Entidad no encontrada
- codigo: entidad_no_encontrada
- descripcion: La entidad objetivo de la operación financiera no existe al momento de aplicar el cambio.
- tipo: funcional
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: no

### ERR-FIN-043 — Entidad inactiva
- codigo: entidad_inactiva
- descripcion: La entidad objetivo existe pero se encuentra inactiva para la operación solicitada.
- tipo: funcional
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: no

### ERR-FIN-044 — Error de idempotencia
- codigo: error_idempotencia
- descripcion: No fue posible resolver correctamente la idempotencia de la operación financiera.
- tipo: concurrencia
- aplica_a: operaciones_write_financieras
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-FIN-045 — Inconsistencia financiera global
- codigo: inconsistencia_financiera_global
- descripcion: Se detectó una inconsistencia relevante entre relaciones, obligaciones, imputaciones, ajustes o resultados consolidados.
- tipo: integridad
- aplica_a: relacion_generadora, obligacion_financiera, aplicacion_financiera, ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-FIN-046 — Conflicto de estado financiero
- codigo: conflicto_estado_financiero
- descripcion: El estado financiero visible entra en conflicto con la operación solicitada o con otro cambio concurrente.
- tipo: concurrencia
- aplica_a: relacion_generadora, obligacion_financiera, aplicacion_financiera, ajuste_financiero
- origen: DEV-SRV
- es_reintento_valido: sí

---

## Reglas de normalización

1. No duplicar errores.
2. Separar errores funcionales de concurrencia.
3. No incluir errores de otros dominios.
4. No incluir errores técnicos de infraestructura profunda.
5. Consolidar variantes similares.
6. Mantener numeración `ERR-FIN-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio financiero.
- Es uno de los dominios más críticos del sistema.
- Debe mantenerse alineado con CU-FIN y RN-FIN.
- Sirve como base para manejo consistente de errores financieros.
