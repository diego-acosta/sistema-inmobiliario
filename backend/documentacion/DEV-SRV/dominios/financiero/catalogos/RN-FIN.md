# RN-FIN — Reglas del dominio Financiero

## Objetivo
Definir reglas del dominio financiero.

## Alcance
Incluye relaciones generadoras, obligaciones, imputaciones, ajustes y consultas.

---

## A. Reglas de relaciones generadoras

### RN-FIN-001 — Relación generadora como origen financiero
- descripcion: Una relación generadora constituye el origen formal de obligaciones financieras dentro del sistema.
- aplica_a: relacion_generadora
- origen_principal: DEV-SRV

### RN-FIN-002 — Estados válidos de relación generadora
- descripcion: Una relación generadora puede encontrarse en estado borrador, activa, cancelada o finalizada según su ciclo de vida.
- aplica_a: relacion_generadora
- origen_principal: DEV-SRV

### RN-FIN-003 — Generación desde relación activa
- descripcion: Solo una relación generadora activa puede generar nuevas obligaciones financieras.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-004 — Relación cancelada sin nuevas obligaciones
- descripcion: Una relación generadora cancelada no debe generar nuevas obligaciones.
- aplica_a: relacion_generadora
- origen_principal: DEV-SRV

### RN-FIN-005 — Finalización sin deuda pendiente
- descripcion: Una relación generadora finalizada no debe mantener deuda pendiente ni obligaciones abiertas incompatibles con su cierre.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-006 — Relación generadora sin deuda propia
- descripcion: La relación generadora no almacena deuda como valor primario; la deuda se expresa en las obligaciones que genera.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV

## B. Reglas de obligaciones

### RN-FIN-007 — Obligación como deuda exigible
- descripcion: Una obligación financiera representa una deuda exigible dentro del dominio.
- aplica_a: obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-008 — Asociación obligatoria con relación generadora
- descripcion: Toda obligación debe estar asociada a una relación generadora válida dentro del sistema.
- aplica_a: obligacion_financiera, relacion_generadora
- origen_principal: DER

### RN-FIN-009 — Componentes básicos de obligación
- descripcion: Una obligación debe contar con monto, fecha de vencimiento y estado financiero definidos.
- aplica_a: obligacion_financiera
- origen_principal: DER

### RN-FIN-010 — Estados operativos de obligación
- descripcion: Una obligación puede encontrarse pendiente, cancelada o vencida según su evolución financiera.
- aplica_a: obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-011 — No modificación destructiva de obligación
- descripcion: Una obligación no debe modificarse directamente de forma destructiva una vez generada; los cambios deben canalizarse por ajustes o mecanismos equivalentes.
- aplica_a: obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-012 — Reducción de saldo por imputación
- descripcion: El saldo de una obligación se reduce por imputaciones financieras válidas aplicadas sobre ella.
- aplica_a: obligacion_financiera, aplicacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-013 — Multiplicidad de imputaciones
- descripcion: Una obligación puede recibir múltiples imputaciones a lo largo de su ciclo de vida.
- aplica_a: obligacion_financiera, aplicacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-014 — Obligación ajustable
- descripcion: Una obligación puede ser ajustada conforme a las reglas del dominio financiero.
- aplica_a: obligacion_financiera, ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-015 — Prohibición de saldo negativo
- descripcion: Una obligación no debe quedar con saldo negativo como resultado de imputaciones o ajustes.
- aplica_a: obligacion_financiera
- origen_principal: DEV-SRV

## C. Reglas de imputaciones financieras

### RN-FIN-016 — Imputación como aplicación de pago o crédito
- descripcion: Una imputación financiera aplica un pago o crédito a una obligación determinada.
- aplica_a: aplicacion_financiera, movimiento_financiero, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-017 — Reducción operativa del saldo
- descripcion: La imputación reduce el saldo operativo de la obligación sobre la cual se aplica.
- aplica_a: aplicacion_financiera, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-018 — Imputación parcial o total
- descripcion: Una imputación puede cubrir total o parcialmente una obligación, según el monto aplicado.
- aplica_a: aplicacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-019 — Límite por saldo disponible
- descripcion: Una imputación no debe exceder el saldo vigente de la obligación al momento de aplicarse.
- aplica_a: aplicacion_financiera, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-020 — Imputación distribuida
- descripcion: Un mismo pago o crédito puede imputarse a múltiples obligaciones cuando la operatoria lo permita.
- aplica_a: aplicacion_financiera, movimiento_financiero
- origen_principal: DEV-SRV

### RN-FIN-021 — Trazabilidad de imputación
- descripcion: Toda imputación debe ser trazable respecto de pago, obligación, fecha y contexto de aplicación.
- aplica_a: aplicacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-022 — Reversibilidad controlada
- descripcion: Una imputación puede revertirse si el flujo financiero y el estado de las entidades lo permiten.
- aplica_a: aplicacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-023 — Restauración de saldo por reversión
- descripcion: La reversión de una imputación debe restaurar el saldo operativo original afectado por dicha aplicación.
- aplica_a: aplicacion_financiera, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-024 — Obligación sin alteración estructural por imputación
- descripcion: La imputación no modifica la definición estructural de la obligación, sino solo su saldo operativo.
- aplica_a: aplicacion_financiera, obligacion_financiera
- origen_principal: DEV-SRV

## D. Reglas de ajustes financieros

### RN-FIN-025 — Ajuste como modificación de valor financiero
- descripcion: Un ajuste financiero modifica el valor económico visible de una obligación o componente asociado.
- aplica_a: ajuste_financiero, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-026 — Tipos funcionales de ajuste
- descripcion: Un ajuste puede representar interés, recargo, bonificación u otra variación financiera admitida por el dominio.
- aplica_a: ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-027 — No modificación destructiva de base
- descripcion: Un ajuste no debe modificar destructivamente la obligación base sobre la que actúa.
- aplica_a: ajuste_financiero, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-028 — Dependencia de reglas externas
- descripcion: Un ajuste puede depender de reglas externas como índices, fechas o condiciones predefinidas.
- aplica_a: ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-029 — Trazabilidad de ajuste
- descripcion: Todo ajuste debe ser trazable respecto de causa, fecha, obligación y criterio aplicado.
- aplica_a: ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-030 — Aplicación automática o manual
- descripcion: Un ajuste puede aplicarse en forma automática o manual según la política financiera correspondiente.
- aplica_a: ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-031 — Ajuste sin imputación implícita
- descripcion: Un ajuste no genera por sí mismo una imputación financiera.
- aplica_a: ajuste_financiero, aplicacion_financiera
- origen_principal: DEV-SRV

## E. Reglas de consultas financieras

### RN-FIN-032 — Consultas sin efectos persistentes
- descripcion: Las consultas financieras no deben generar efectos persistentes ni mutaciones de estado.
- aplica_a: consultas_financieras
- origen_principal: DEV-SRV

### RN-FIN-033 — Cálculo de deuda a fecha
- descripcion: Las consultas financieras pueden calcular deuda al corte de una fecha determinada.
- aplica_a: consultas_financieras, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-034 — Inclusión de ajustes e intereses en consulta
- descripcion: El cálculo financiero a fecha puede incluir ajustes, intereses u otros componentes visibles según las reglas del dominio.
- aplica_a: consultas_financieras, ajuste_financiero, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-035 — Consolidación de múltiples obligaciones
- descripcion: Las consultas financieras pueden consolidar múltiples obligaciones dentro de una misma vista de lectura.
- aplica_a: consultas_financieras, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-036 — Consulta sin modificación de datos
- descripcion: Ninguna consulta financiera debe modificar obligaciones, imputaciones, ajustes o relaciones generadoras.
- aplica_a: consultas_financieras
- origen_principal: DEV-SRV

## F. Reglas transversales financieras

### RN-FIN-037 — Exclusividad del cálculo de deuda
- descripcion: El dominio financiero es el único responsable del cálculo de deuda del sistema.
- aplica_a: dominio_financiero
- origen_principal: DEV-SRV

### RN-FIN-038 — Prohibición de recálculo externo
- descripcion: Otros dominios no deben recalcular deuda como fuente primaria de verdad.
- aplica_a: dominio_financiero
- origen_principal: DEV-SRV

### RN-FIN-039 — Sin gestión de objetos inmobiliarios
- descripcion: El dominio financiero no gestiona objetos inmobiliarios ni su disponibilidad estructural.
- aplica_a: dominio_financiero
- origen_principal: DEV-SRV

### RN-FIN-040 — Sin gestión de contratos locativos
- descripcion: El dominio financiero no gestiona contratos locativos ni define su lógica operativa.
- aplica_a: dominio_financiero
- origen_principal: DEV-SRV

### RN-FIN-041 — Sin gestión de operaciones comerciales
- descripcion: El dominio financiero no gestiona operaciones comerciales ni su flujo de negocio.
- aplica_a: dominio_financiero
- origen_principal: DEV-SRV

### RN-FIN-042 — Requisitos transversales de write sincronizable
- descripcion: Toda operación write del dominio debe respetar versionado, op_id y outbox cuando resulte sincronizable.
- aplica_a: operaciones_write_financieras
- origen_principal: DEV-SRV
- observaciones: Regla aplicada en alineación con la infraestructura transversal del sistema.

### RN-FIN-043 — Separación entre estados financieros y estados externos
- descripcion: Los estados financieros no deben confundirse con estados comerciales, locativos o documentales.
- aplica_a: relacion_generadora, obligacion_financiera, aplicacion_financiera, ajuste_financiero
- origen_principal: DEV-SRV

### RN-FIN-044 — factura_servicio como origen, no como emision propia
- descripcion: `factura_servicio` puede actuar como origen de generacion financiera bajo tipo_origen conceptual `SERVICIO_TRASLADADO` solo cuando exista registro de origen compatible; el sistema no emite esa factura.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV

### RN-FIN-045 — Obligacion derivada de factura_servicio
- descripcion: La obligacion financiera derivada de `factura_servicio` debe generarse desde una relacion generadora valida y no puede quedar como deuda suelta ni ser calculada por el dominio inmobiliario.
- aplica_a: relacion_generadora, obligacion_financiera, composicion_obligacion
- origen_principal: DEV-SRV

### RN-FIN-046 — Unicidad de obligacion activa por factura_servicio
- descripcion: Una `factura_servicio` no debe generar mas de una obligacion financiera activa. La generacion financiera desde `factura_servicio` debe ser idempotente con clave conceptual `id_factura_servicio`.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV
- estado: PENDIENTE / NO IMPLEMENTADO a nivel funcional; `factura_servicio` existe como tabla SQL estructural, pero no existe API/backend, evento ni consumer financiero.

### RN-FIN-047 — Relacion generadora para SERVICIO_TRASLADADO
- descripcion: Para `SERVICIO_TRASLADADO`, la decision conceptual recomendada es que 1 servicio asociado a inmueble o unidad funcional use 1 `relacion_generadora`, que esa relacion pueda existir antes de la primera `factura_servicio`, y que cada factura posterior genere 1 `obligacion_financiera` dentro de esa misma relacion.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: DEV-SRV
- estado: CONCEPTUAL / PENDIENTE / NO IMPLEMENTADO a nivel funcional; `factura_servicio` existe como tabla SQL estructural, pero no existe contrato, API/backend, evento ni consumer financiero.

### RN-FIN-048 — Resolucion de obligado para SERVICIO_TRASLADADO
- descripcion: Antes de generar la obligacion por `factura_servicio`, financiero debe resolver o solicitar la resolucion del obligado segun contrato locativo vigente si el objeto esta ocupado/alquilado, ocupacion vigente, o propietario/responsable operativo si no hay contrato locativo vigente.
- aplica_a: relacion_generadora, obligacion_financiera, obligacion_obligado
- origen_principal: DEV-SRV
- estado: CONCEPTUAL / PENDIENTE de formalizacion completa.
- observaciones: inmobiliario no decide deuda ni crea obligaciones; financiero conserva ownership sobre la generacion y la composicion de la deuda. Pendiente de formalización en INT-FIN-002 — Resolución de obligado financiero.

---

## G. Reglas estructurales de obligacion y conceptos

### RN-FIN-049 — Origen desde relacion generadora
- descripcion: El origen de una obligacion financiera se interpreta desde `relacion_generadora.tipo_origen` e `id_origen`; no desde un tipo rigido persistido en la obligacion.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-050 — Naturaleza economica por composicion
- descripcion: La naturaleza economica de una obligacion se interpreta desde sus filas de `composicion_obligacion` y el `concepto_financiero` asociado.
- aplica_a: obligacion_financiera, composicion_obligacion, concepto_financiero
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-051 — Prohibicion de tipo_obligacion como eje estructural
- descripcion: La obligacion financiera no debe codificar rigidamente como logica central si es venta, alquiler, servicio, expensa u otra categoria de negocio.
- aplica_a: obligacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-052 — Composicion obligatoria
- descripcion: Toda obligacion financiera materializada debe tener una o mas composiciones economicas.
- aplica_a: obligacion_financiera, composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-053 — Concepto obligatorio por composicion
- descripcion: Toda composicion de obligacion debe referenciar exactamente un `concepto_financiero`.
- aplica_a: composicion_obligacion, concepto_financiero
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-054 — Multiples conceptos por obligacion
- descripcion: Si una obligacion combina varios conceptos economicos, cada concepto debe representarse en una fila separada de `composicion_obligacion`.
- aplica_a: obligacion_financiera, composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-055 — Saldo conciliable contra componentes
- descripcion: El saldo de la obligacion debe ser reconstruible o conciliable contra sus componentes financieros.
- aplica_a: obligacion_financiera, composicion_obligacion, aplicacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN
- estado: CONCEPTUAL / PENDIENTE de politica fisica de saldo por componente.

### RN-FIN-056 — Cancelacion mediante imputacion
- descripcion: Un pago no cancela directamente una obligacion; la cancelacion total o parcial debe pasar por `aplicacion_financiera` / imputacion financiera.
- aplica_a: movimiento_financiero, aplicacion_financiera, obligacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN

---

## I. Reglas de regeneracion de cronograma locativo

### RN-FIN-075 — Regeneracion no modifica obligaciones con pagos
- descripcion: La regeneracion de cronograma locativo no debe borrar fisicamente obligaciones ni modificar pagos, movimientos financieros ni mora existentes.
- aplica_a: obligacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: IMPLEMENTADO en `POST /api/v1/financiero/contratos-alquiler/{id}/regenerar-cronograma`
- observaciones: Una obligacion con al menos una `aplicacion_financiera` activa es intocable ante regeneracion, independientemente de su estado. Los `movimiento_financiero` asociados a pagos no se alteran.

### RN-FIN-076 — Obligaciones protegidas ante regeneracion
- descripcion: No pueden ser reemplazadas por regeneracion las obligaciones en estado `CANCELADA` o `PARCIALMENTE_CANCELADA`, ni las que posean al menos una `aplicacion_financiera` activa.
- aplica_a: obligacion_financiera, aplicacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: IMPLEMENTADO
- observaciones: El mecanismo de reemplazo es logico: las obligaciones elegibles (EMITIDA, VENCIDA, PENDIENTE_AJUSTE sin pagos) pasan a `REEMPLAZADA` con `deleted_at` seteado. No existe borrado fisico ni modificacion de saldo.

### RN-FIN-077 — Soft-delete de obligaciones reemplazadas y no duplicacion de periodos activos
- descripcion: Las obligaciones reemplazadas quedan con `estado_obligacion = REEMPLAZADA` y `deleted_at` seteado para liberar el indice unico parcial, garantizando que no pueden coexistir dos obligaciones activas para el mismo periodo.
- aplica_a: obligacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: IMPLEMENTADO
- observaciones: El indice unico parcial `(id_relacion_generadora, periodo_desde, periodo_hasta) WHERE deleted_at IS NULL` impide duplicacion de periodos activos. El soft-delete libera esa restriccion sin perder la trazabilidad historica.

### RN-FIN-078 — Regeneracion es idempotente
- descripcion: La regeneracion aplica solo a obligaciones cuyo `periodo_desde >= fecha_corte`. Obligaciones anteriores a la fecha_corte no se tocan. Una segunda llamada con la misma `fecha_corte` produce el mismo resultado final.
- aplica_a: obligacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: IMPLEMENTADO
- observaciones: Una segunda llamada con la misma `fecha_corte` reemplaza las obligaciones EMITIDA creadas en la corrida anterior y genera nuevas equivalentes. El resultado final es siempre exactamente 1 obligacion activa por periodo cubierto.

### RN-FIN-079 — Regeneracion requiere fecha_corte explicita
- descripcion: Las obligaciones generadas por regeneracion aplican la misma logica que la generacion inicial y requieren `fecha_corte` explicita en el request; no existe regeneracion automatica por cambios de condiciones economicas.
- aplica_a: obligacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: IMPLEMENTADO
- observaciones: El endpoint no infiere ni calcula la fecha de corte; es responsabilidad del caller proveerla. Aplica prorrateo, vencimiento real, obligado financiero e idempotencia por indice unico parcial.

### RN-FIN-080 — Pendientes de trazabilidad de reemplazo
- descripcion: Los campos `id_obligacion_reemplazada` e `id_obligacion_reemplazante` existen en el esquema SQL pero no se vinculan aun en la regeneracion V1; la cadena de reemplazo solo es trazable por estado y `deleted_at`.
- aplica_a: obligacion_financiera, regeneracion_cronograma
- origen_principal: DEV-SRV
- estado: PENDIENTE
- observaciones: Pendiente tambien: endpoint de consulta historica de reemplazos y desacoplamiento tecnico de la logica de generacion entre activacion y regeneracion.

---

### RN-FIN-057 — Saldo operativo por componente
- descripcion: El saldo operativo real debe poder existir a nivel `composicion_obligacion`; `saldo_componente` representa el saldo vivo de ese concepto dentro de la obligacion.
- aplica_a: composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN
- estado: CONCEPTUAL / PENDIENTE SQL; SQL vigente no posee `saldo_componente`.

### RN-FIN-058 — Saldo consolidado de obligacion
- descripcion: `obligacion_financiera.saldo_pendiente` representa el saldo total consolidado y debe ser igual a la suma de `saldo_componente` de composiciones activas, salvo transicion tecnica documentada.
- aplica_a: obligacion_financiera, composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN
- estado: CONCEPTUAL / PENDIENTE SQL para saldo por componente.

### RN-FIN-059 — Imputacion preferente por componente
- descripcion: La imputacion financiera debe aplicarse contra componentes cuando exista desglose economico; si se registra a nivel obligacion, debe distribuirse hacia componentes por politica documentada.
- aplica_a: aplicacion_financiera, obligacion_financiera, composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN

### RN-FIN-060 — Prioridad de distribucion de pago global
- descripcion: Cuando un pago global deba distribuirse hacia componentes, la prioridad base es `INTERES_MORA`, `PUNITORIO`, `CARGO_ADMINISTRATIVO`, `INTERES_FINANCIERO`, `AJUSTE_INDEXACION`, capitales/canones/trasladados, y luego otros conceptos de cierre.
- aplica_a: aplicacion_financiera, composicion_obligacion, concepto_financiero
- origen_principal: MODELO-FINANCIERO-FIN
- estado: IMPLEMENTADA PARCIALMENTE en `POST /api/v1/financiero/imputaciones`.
- observaciones: La implementacion actual distribuye dentro de una obligacion, genera una o mas aplicaciones y usa `orden_aplicacion`.

### RN-FIN-061 — Cancelacion exige componentes sin saldo
- descripcion: No debe permitirse que una obligacion figure cancelada si alguna composicion activa conserva `saldo_componente > 0`.
- aplica_a: obligacion_financiera, composicion_obligacion
- origen_principal: MODELO-FINANCIERO-FIN
- estado: CONCEPTUAL / PENDIENTE SQL para saldo por componente.

### RN-FIN-062 — Saldo negativo de composicion prohibido
- descripcion: No debe permitirse que una composicion quede con saldo negativo salvo nota de credito o credito manual explicitamente modelado.
- aplica_a: composicion_obligacion, aplicacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN
- estado: CONCEPTUAL / PENDIENTE SQL para saldo por componente.

### RN-FIN-063 — Saldos conciliables con aplicaciones
- descripcion: Los saldos acumulados de la obligacion y sus componentes deben ser conciliables con movimientos y aplicaciones financieras.
- aplica_a: obligacion_financiera, composicion_obligacion, movimiento_financiero, aplicacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN

---

## H. Reglas de estados y transiciones de obligacion_financiera

### RN-FIN-064 — Cancelacion solo sin saldo
- descripcion: No se puede cancelar una obligacion sin `saldo_pendiente = 0` y sin componentes activos con saldo vivo.
- aplica_a: obligacion_financiera, composicion_obligacion
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN

### RN-FIN-065 — Emision con relacion generadora valida
- descripcion: No se puede emitir una obligacion si su `relacion_generadora` no esta en estado valido para generar o emitir.
- aplica_a: relacion_generadora, obligacion_financiera
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN

### RN-FIN-066 — Reemplazo con trazabilidad
- descripcion: No se puede reemplazar una obligacion sin dejar trazabilidad hacia la obligacion nueva o hacia el proceso formal de refinanciacion, regeneracion o reemision.
- aplica_a: obligacion_financiera
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN

### RN-FIN-067 — Anulacion con pagos aplicados
- descripcion: No se puede anular una obligacion con pagos aplicados sin reversion de imputaciones o tratamiento financiero documentado.
- aplica_a: obligacion_financiera, aplicacion_financiera
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN

### RN-FIN-068 — Vencida materializada o derivada
- descripcion: `VENCIDA` puede ser estado materializado o derivado por `fecha_vencimiento` superada y saldo pendiente mayor a cero.
- aplica_a: obligacion_financiera
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN
- estado: DECISION FISICA PENDIENTE.

### RN-LOC-FIN-001 - Condicion economica aplicable al periodo locativo
- descripcion: La condicion economica aplicable a un periodo locativo es la vigente en `periodo_desde`, salvo regla explicita de prorrateo o division del periodo.
- aplica_a: contrato_alquiler, condicion_economica_alquiler, obligacion_financiera
- origen_principal: SRV-FIN-015-plan-financiero-locativo
- estado: IMPLEMENTADA sin prorrateo.

### RN-LOC-FIN-002 - Obligado principal del canon locativo
- descripcion: El obligado financiero principal del canon locativo se resuelve desde el locatario principal del contrato. El garante no se incorpora automaticamente como obligado principal.
- aplica_a: contrato_alquiler, relacion_persona_rol, rol_participacion, obligacion_obligado
- origen_principal: SRV-FIN-015-plan-financiero-locativo / INT-FIN-002
- estado: IMPLEMENTACION MINIMA.

### RN-LOC-FIN-003 - Fecha de vencimiento del canon locativo
- descripcion: La fecha de vencimiento de una obligacion locativa se determina a partir de `contrato_alquiler.dia_vencimiento_canon`. Si el campo esta informado, `fecha_vencimiento` es ese dia dentro del mes del periodo. Si el dia no existe en el mes, se usa el ultimo dia real del mes. Si el dia calculado quedara antes de `periodo_desde`, se usa `periodo_desde`. Si `dia_vencimiento_canon` es NULL, se usa `periodo_desde` como fallback tecnico. No hay dias de gracia ni ajuste por feriados.
- aplica_a: contrato_alquiler, obligacion_financiera
- origen_principal: SRV-FIN-015-plan-financiero-locativo
- estado: IMPLEMENTADA.

### RN-LOC-FIN-005 - Prorrateo de canon locativo por cambio de condición dentro del período
- descripcion: Cuando `condicion_economica_alquiler.fecha_desde` cae estrictamente dentro de un período mensual (> `periodo_desde` y <= `periodo_hasta`), el período se divide en segmentos. Cada segmento genera una `obligacion_financiera` separada con `importe = monto_base * dias_segmento / dias_mes` (días reales del mes), redondeado a 2 decimales. Cuando todos los segmentos comparten el mismo `monto_base`, el último segmento absorbe el residuo de redondeo para garantizar suma exacta. Si no hay cambio de condición dentro del período, se genera una sola obligación con el monto_base completo.
- aplica_a: condicion_economica_alquiler, obligacion_financiera, relacion_generadora
- origen_principal: SRV-FIN-015-plan-financiero-locativo
- estado: IMPLEMENTADA.

### RN-FIN-069 — Reduccion de saldo controlada
- descripcion: Ninguna transicion puede reducir saldo sin `aplicacion_financiera`, anulacion formal o credito documentado.
- aplica_a: obligacion_financiera, composicion_obligacion, aplicacion_financiera
- origen_principal: EST-FIN / MODELO-FINANCIERO-FIN

### RN-FIN-070 - Calculo de mora diaria simple
- descripcion: La mora V1 se calcula dinamicamente como `saldo_pendiente * tasa_diaria_mora * dias_atraso`, redondeada a 2 decimales, sobre obligaciones vencidas con saldo pendiente. `tasa_diaria_mora` y `dias_gracia` se resuelven via `resolver_mora_params` con prioridad: origen > concepto > default global.
- aplica_a: obligacion_financiera, estado_cuenta, deuda_consolidada
- origen_principal: SRV-FIN-013-generacion-de-mora
- estado: IMPLEMENTADA.

### RN-LOC-FIN-004 - Resolver centralizado de parámetros de mora
- descripcion: Los parametros de mora (`tasa_diaria`, `dias_gracia`) se resuelven con prioridad: (1) regla por origen `<tipo_origen>:<id_origen>`, (2) regla por `codigo_concepto`, (3) default global `TASA_DIARIA_MORA_DEFAULT=0.001` y `DIAS_GRACIA_MORA_DEFAULT=5`. V1: no existen reglas en DB; siempre retorna el default. Todos los endpoints de calculo de mora usan el mismo resolver.
- aplica_a: obligacion_financiera, relacion_generadora, concepto_financiero
- origen_principal: SRV-FIN-013-generacion-de-mora / resolver_mora.py
- estado: IMPLEMENTADA (V1 default only; extensible via `reglas` dict).

### RN-FIN-071 - Mora no capitalizable
- descripcion: La mora diaria no se persiste como obligacion financiera ni incrementa el saldo de la obligacion base; se expone como calculo de lectura.
- aplica_a: obligacion_financiera, estado_cuenta, deuda_consolidada
- origen_principal: SRV-FIN-013-generacion-de-mora
- estado: IMPLEMENTADA.

### RN-FIN-072 - Marcado idempotente de vencidas
- descripcion: El proceso de mora solo cambia `EMITIDA` a `VENCIDA` cuando `fecha_vencimiento < fecha_proceso` y `saldo_pendiente > 0`; ejecuciones repetidas no vuelven a modificar la obligacion.
- aplica_a: obligacion_financiera
- origen_principal: SRV-FIN-013-generacion-de-mora
- estado: IMPLEMENTADA.

### RN-FIN-073 - Transicion automatica por saldo luego de imputacion
- descripcion: Despues de registrar aplicaciones, si `saldo_pendiente = 0` la obligacion pasa a `CANCELADA`; si `saldo_pendiente < importe_total` pasa a `PARCIALMENTE_CANCELADA`.
- aplica_a: obligacion_financiera, aplicacion_financiera
- origen_principal: SRV-FIN-008-gestion-de-imputacion-financiera
- estado: IMPLEMENTADA.
- observaciones: La base de datos actualiza saldos por triggers; el backend actualiza el estado leyendo el saldo resultante.

### RN-FIN-074 - Backend no recalcula saldos como fuente primaria
- descripcion: El saldo de obligacion y composicion se actualiza en la base de datos; los servicios backend no deben duplicar ese calculo como verdad primaria.
- aplica_a: obligacion_financiera, composicion_obligacion, aplicacion_financiera
- origen_principal: MODELO-FINANCIERO-FIN
- estado: IMPLEMENTADA.

---

## Reglas de normalización

1. No duplicar reglas.
2. Consolidar variantes similares.
3. Separar claramente cálculo financiero de otros dominios.
4. No incluir reglas técnicas profundas.
5. Mantener numeración RN-FIN-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio financiero.
- Es uno de los dominios centrales del sistema.
- Define la lógica económica del sistema.
- Debe mantenerse alineado con CU-FIN.
