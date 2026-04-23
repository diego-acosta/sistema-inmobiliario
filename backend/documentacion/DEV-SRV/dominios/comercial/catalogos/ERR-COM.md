# ERR-COM — Errores del dominio Comercial

## Objetivo
Definir errores funcionales y transversales del dominio comercial.

## Alcance
Incluye errores asociados a reservas, ventas, instrumentos, cesiones, escrituración y rescisiones.

---

## A. Errores de reservas

### ERR-COM-001 — Reserva no encontrada
- codigo: reserva_no_encontrada
- descripcion: no existe una reserva comercial para el criterio indicado.
- tipo: funcional
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-002 — Reserva inactiva
- codigo: reserva_inactiva
- descripcion: la reserva existe pero no se encuentra activa para la operación solicitada.
- tipo: funcional
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-003 — Reserva cancelada
- codigo: reserva_cancelada
- descripcion: la reserva fue cancelada y no puede continuar su flujo normal.
- tipo: funcional
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-004 — Reserva ya confirmada
- codigo: reserva_ya_confirmada
- descripcion: la reserva ya se encuentra confirmada y no admite la acción solicitada.
- tipo: funcional
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-005 — Reserva duplicada
- codigo: reserva_duplicada
- descripcion: existe una reserva equivalente incompatible con la nueva operación.
- tipo: integridad
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-006 — Objeto inmobiliario no encontrado
- codigo: objeto_inmobiliario_no_encontrado
- descripcion: no existe el objeto inmobiliario requerido para la operación comercial.
- tipo: funcional
- aplica_a: objeto_inmobiliario
- origen: DER
- es_reintento_valido: no

### ERR-COM-007 — Objeto inmobiliario no disponible
- codigo: objeto_inmobiliario_no_disponible
- descripcion: el objeto inmobiliario no se encuentra disponible para reserva comercial.
- tipo: funcional
- aplica_a: objeto_inmobiliario, reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-008 — Conflicto de reserva sobre objeto
- codigo: conflicto_reserva_objeto
- descripcion: existe un conflicto comercial por reserva simultánea o incompatible sobre el mismo objeto.
- tipo: integridad
- aplica_a: reserva_venta, objeto_inmobiliario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-009 — Reserva sin objeto
- codigo: reserva_sin_objeto
- descripcion: la reserva no posee objetos inmobiliarios válidamente asociados.
- tipo: validacion
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-010 — Estado de reserva inválido
- codigo: estado_reserva_invalido
- descripcion: el estado actual de la reserva no admite la operación solicitada.
- tipo: validacion
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-011 — Transición de estado de reserva inválida
- codigo: transicion_estado_reserva_invalida
- descripcion: la transición entre estados de reserva no es válida según el flujo comercial.
- tipo: validacion
- aplica_a: reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de ventas

### ERR-COM-012 — Venta no encontrada
- codigo: venta_no_encontrada
- descripcion: no existe una venta para el criterio indicado.
- tipo: funcional
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-013 — Venta inactiva
- codigo: venta_inactiva
- descripcion: la venta existe pero no se encuentra activa para la operación solicitada.
- tipo: funcional
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-014 — Venta cancelada
- codigo: venta_cancelada
- descripcion: la venta fue cancelada y no admite continuidad comercial ordinaria.
- tipo: funcional
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-015 — Venta duplicada
- codigo: venta_duplicada
- descripcion: existe una operación de venta incompatible o duplicada para el mismo contexto comercial.
- tipo: integridad
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-016 — Venta sin objeto
- codigo: venta_sin_objeto
- descripcion: la venta no posee objetos inmobiliarios válidamente asociados.
- tipo: validacion
- aplica_a: venta, venta_objeto_inmobiliario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-017 — Venta sin comprador
- codigo: venta_sin_comprador
- descripcion: la venta no posee sujeto comprador válido.
- tipo: validacion
- aplica_a: venta, persona
- origen: DER
- es_reintento_valido: no

### ERR-COM-018 — Conflicto de objeto en venta
- codigo: conflicto_objeto_en_venta
- descripcion: uno o más objetos de la venta están comprometidos en otra operación incompatible.
- tipo: integridad
- aplica_a: venta, objeto_inmobiliario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-019 — Estado de venta inválido
- codigo: estado_venta_invalido
- descripcion: el estado actual de la venta no admite la operación solicitada.
- tipo: validacion
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-020 — Transición de estado de venta inválida
- codigo: transicion_estado_venta_invalida
- descripcion: la transición entre estados de venta no es válida según el flujo comercial.
- tipo: validacion
- aplica_a: venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-021 — Operación comercial inconsistente
- codigo: operacion_comercial_inconsistente
- descripcion: la operación comercial presenta inconsistencia entre sujetos, objetos o estado.
- tipo: integridad
- aplica_a: reserva_venta, venta, objeto_inmobiliario
- origen: DER
- es_reintento_valido: no

## C. Errores de instrumentos comerciales

### ERR-COM-022 — Instrumento no encontrado
- codigo: instrumento_no_encontrado
- descripcion: no existe un instrumento comercial para el criterio indicado.
- tipo: funcional
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-023 — Instrumento duplicado
- codigo: instrumento_duplicado
- descripcion: existe un instrumento comercial incompatible o duplicado para la misma operación base.
- tipo: integridad
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-024 — Instrumento sin operación base
- codigo: instrumento_sin_operacion_base
- descripcion: el instrumento no posee una operación comercial base válida asociada.
- tipo: validacion
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-025 — Instrumento anulado
- codigo: instrumento_anulado
- descripcion: el instrumento fue anulado y no admite la acción solicitada.
- tipo: funcional
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-026 — Asociación de instrumento inválida
- codigo: asociacion_instrumento_invalida
- descripcion: la vinculación del instrumento con la operación comercial es inválida.
- tipo: validacion
- aplica_a: instrumento_compraventa, venta, reserva_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-027 — Estado de instrumento inválido
- codigo: estado_instrumento_invalido
- descripcion: el estado actual del instrumento no admite la operación solicitada.
- tipo: validacion
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-028 — Transición de estado de instrumento inválida
- codigo: transicion_estado_instrumento_invalida
- descripcion: la transición de estado del instrumento no es válida según su ciclo de vida.
- tipo: validacion
- aplica_a: instrumento_compraventa
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de cesiones

### ERR-COM-029 — Cesión no encontrada
- codigo: cesion_no_encontrada
- descripcion: no existe una cesión para el criterio indicado.
- tipo: funcional
- aplica_a: cesion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-030 — Cesión inválida
- codigo: cesion_invalida
- descripcion: la cesión no cumple las condiciones comerciales requeridas para ser válida.
- tipo: validacion
- aplica_a: cesion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-031 — Cesión duplicada
- codigo: cesion_duplicada
- descripcion: existe una cesión incompatible o redundante sobre la misma operación.
- tipo: integridad
- aplica_a: cesion, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-032 — Sujeto cesionario inválido
- codigo: sujeto_cesionario_invalido
- descripcion: el sujeto informado como cesionario no es válido para la operación.
- tipo: validacion
- aplica_a: cesion, persona
- origen: DER
- es_reintento_valido: no

### ERR-COM-033 — Conflicto de cesión sobre operación
- codigo: conflicto_cesion_operacion
- descripcion: la operación comercial presenta conflicto para admitir la cesión solicitada.
- tipo: integridad
- aplica_a: cesion, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-034 — Estado de cesión inválido
- codigo: estado_cesion_invalido
- descripcion: el estado actual de la cesión no admite la operación solicitada.
- tipo: validacion
- aplica_a: cesion
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de escrituración

### ERR-COM-035 — Escrituración no encontrada
- codigo: escrituracion_no_encontrada
- descripcion: no existe una escrituración para el criterio indicado.
- tipo: funcional
- aplica_a: escrituracion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-036 — Escrituración inválida
- codigo: escrituracion_invalida
- descripcion: la escrituración no cumple condiciones válidas para el proceso comercial.
- tipo: validacion
- aplica_a: escrituracion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-037 — Escrituración duplicada
- codigo: escrituracion_duplicada
- descripcion: existe una escrituración incompatible o duplicada para la misma operación.
- tipo: integridad
- aplica_a: escrituracion, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-038 — Operación no escriturable
- codigo: operacion_no_escriturable
- descripcion: la operación comercial no cumple condiciones para escrituración.
- tipo: funcional
- aplica_a: escrituracion, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-039 — Estado de escrituración inválido
- codigo: estado_escrituracion_invalido
- descripcion: el estado actual de la escrituración no admite la operación solicitada.
- tipo: validacion
- aplica_a: escrituracion
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores de rescisiones comerciales

### ERR-COM-040 — Rescisión no encontrada
- codigo: rescision_no_encontrada
- descripcion: no existe una rescisión comercial para el criterio indicado.
- tipo: funcional
- aplica_a: rescision_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-041 — Rescisión inválida
- codigo: rescision_invalida
- descripcion: la rescisión no cumple condiciones válidas para el proceso comercial.
- tipo: validacion
- aplica_a: rescision_venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-042 — Rescisión duplicada
- codigo: rescision_duplicada
- descripcion: existe una rescisión incompatible o redundante sobre la misma operación.
- tipo: integridad
- aplica_a: rescision_venta, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-043 — Operación no rescindible
- codigo: operacion_no_rescindible
- descripcion: la operación comercial no admite rescisión en el estado actual.
- tipo: funcional
- aplica_a: rescision_venta, venta
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-COM-044 — Estado de rescisión inválido
- codigo: estado_rescision_invalido
- descripcion: el estado actual de la rescisión no admite la operación solicitada.
- tipo: validacion
- aplica_a: rescision_venta
- origen: DEV-SRV
- es_reintento_valido: no

## G. Errores transversales comerciales

### ERR-COM-045 — Versión esperada inválida
- codigo: version_esperada_invalida
- descripcion: la versión esperada no coincide con la versión vigente de la entidad comercial.
- tipo: concurrencia
- aplica_a: entidades write sincronizables del dominio comercial
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-COM-046 — Lock lógico activo
- codigo: lock_logico_activo
- descripcion: existe un lock lógico vigente que impide la operación comercial solicitada.
- tipo: concurrencia
- aplica_a: operaciones write sensibles del dominio comercial
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-COM-047 — Recurso bloqueado
- codigo: recurso_bloqueado
- descripcion: el recurso comercial requerido se encuentra bloqueado para modificación concurrente.
- tipo: concurrencia
- aplica_a: entidades write del dominio comercial
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-COM-048 — Op_id duplicado
- codigo: op_id_duplicado
- descripcion: la operación comercial ya fue registrada previamente con el mismo op_id.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio comercial
- origen: CORE-EF
- es_reintento_valido: no

### ERR-COM-049 — Op_id duplicado con payload distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el mismo op_id fue reutilizado con contenido diferente y constituye conflicto técnico.
- tipo: integridad
- aplica_a: operaciones write sincronizables del dominio comercial
- origen: CORE-EF
- es_reintento_valido: no

### ERR-COM-050 — Conflicto de concurrencia
- codigo: conflicto_concurrencia
- descripcion: la operación comercial no puede completarse por conflicto concurrente sobre la misma entidad o contexto.
- tipo: concurrencia
- aplica_a: entidades write del dominio comercial
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-COM-051 — Inconsistencia de contexto técnico
- codigo: inconsistencia_contexto_tecnico
- descripcion: el contexto técnico mínimo exigido para la operación comercial es inválido o insuficiente.
- tipo: validacion
- aplica_a: operaciones write sincronizables del dominio comercial
- origen: CORE-EF
- es_reintento_valido: no

### ERR-COM-052 — Entidad no encontrada
- codigo: entidad_no_encontrada
- descripcion: la entidad comercial requerida no existe en el contexto consultado.
- tipo: funcional
- aplica_a: entidades comerciales sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-COM-053 — Entidad inactiva
- codigo: entidad_inactiva
- descripcion: la entidad comercial existe pero se encuentra inactiva para la operación solicitada.
- tipo: funcional
- aplica_a: entidades comerciales sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-COM-054 — Error de idempotencia
- codigo: error_idempotencia
- descripcion: no puede garantizarse la idempotencia esperada para la operación comercial.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio comercial
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-COM-055 — Inconsistencia de objeto inmobiliario
- codigo: inconsistencia_objeto_inmobiliario
- descripcion: el objeto inmobiliario referido por la operación comercial presenta inconsistencia de identidad, vínculo o elegibilidad.
- tipo: integridad
- aplica_a: objeto_inmobiliario, reserva_venta, venta
- origen: DER
- es_reintento_valido: no

### ERR-COM-056 — Conflicto de estado comercial
- codigo: conflicto_de_estado_comercial
- descripcion: el estado comercial observable entra en conflicto con la operación solicitada o con otra operación vigente.
- tipo: integridad
- aplica_a: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion, rescision_venta
- origen: DEV-SRV
- es_reintento_valido: no

---

## Reglas de normalización

1. No duplicar errores con distinto nombre.
2. Separar errores funcionales de concurrencia.
3. No incluir errores financieros en este catálogo.
4. No incluir errores técnicos de infraestructura profunda.
5. Consolidar variantes similares en un único error canónico.
6. Mantener numeración local `ERR-COM-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio comercial y de las restricciones estructurales del DER.
- No reemplaza a RN-COM ni al dominio inmobiliario.
- Sirve como base para manejo consistente de errores en backend y API.
- Debe mantenerse alineado con CU-COM y RN-COM.
