# ERR-LOC — Errores del dominio Locativo

## Objetivo
Definir errores del dominio locativo.

## Alcance
Incluye solicitudes, reservas, contratos, condiciones, ajustes, modificaciones, rescisión y restitución.

---

## A. Errores de solicitudes de alquiler

### ERR-LOC-001 — Solicitud no encontrada
- codigo: solicitud_no_encontrada
- descripcion: no existe una solicitud de alquiler para el criterio indicado.
- tipo: funcional
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-002 — Solicitud inactiva
- codigo: solicitud_inactiva
- descripcion: la solicitud existe pero no se encuentra activa para la operación solicitada.
- tipo: funcional
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-003 — Solicitud cancelada
- codigo: solicitud_cancelada
- descripcion: la solicitud fue cancelada y no puede continuar su flujo locativo.
- tipo: funcional
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-004 — Solicitud rechazada
- codigo: solicitud_rechazada
- descripcion: la solicitud fue rechazada y no admite continuidad dentro del proceso locativo.
- tipo: funcional
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-005 — Solicitud duplicada
- codigo: solicitud_duplicada
- descripcion: existe una solicitud incompatible o redundante para el mismo solicitante, objeto o contexto.
- tipo: integridad
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-006 — Solicitud sin objeto
- codigo: solicitud_sin_objeto
- descripcion: la solicitud no posee objeto locativo válidamente asociado.
- tipo: validacion
- aplica_a: solicitud_alquiler, objeto_locativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-007 — Estado de solicitud inválido
- codigo: estado_solicitud_invalido
- descripcion: el estado actual de la solicitud no admite la operación requerida.
- tipo: validacion
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-008 — Transición de estado de solicitud inválida
- codigo: transicion_estado_solicitud_invalida
- descripcion: la transición de estado solicitada no es válida para el flujo locativo.
- tipo: validacion
- aplica_a: solicitud_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de reservas locativas

### ERR-LOC-009 — Reserva locativa no encontrada
- codigo: reserva_locativa_no_encontrada
- descripcion: no existe una reserva locativa para el criterio indicado.
- tipo: funcional
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-010 — Reserva locativa inactiva
- codigo: reserva_locativa_inactiva
- descripcion: la reserva locativa existe pero no se encuentra activa para la operación solicitada.
- tipo: funcional
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-011 — Reserva locativa cancelada
- codigo: reserva_locativa_cancelada
- descripcion: la reserva locativa fue cancelada y no puede avanzar a etapas posteriores.
- tipo: funcional
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-012 — Reserva locativa duplicada
- codigo: reserva_locativa_duplicada
- descripcion: existe una reserva locativa incompatible o redundante para el mismo objeto o contexto.
- tipo: integridad
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-013 — Objeto locativo no encontrado
- codigo: objeto_locativo_no_encontrado
- descripcion: no existe el objeto locativo requerido para la operación.
- tipo: funcional
- aplica_a: objeto_locativo
- origen: DER
- es_reintento_valido: no

### ERR-LOC-014 — Objeto locativo no disponible
- codigo: objeto_locativo_no_disponible
- descripcion: el objeto locativo no se encuentra disponible para reserva o contratación.
- tipo: funcional
- aplica_a: objeto_locativo, reserva_locativa, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-015 — Conflicto de reserva locativa
- codigo: conflicto_reserva_locativa
- descripcion: existe un conflicto por reserva simultánea o incompatible sobre el mismo objeto locativo.
- tipo: integridad
- aplica_a: reserva_locativa, objeto_locativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-016 — Reserva locativa sin objeto
- codigo: reserva_locativa_sin_objeto
- descripcion: la reserva locativa no posee objeto válidamente asociado.
- tipo: validacion
- aplica_a: reserva_locativa, objeto_locativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-017 — Estado de reserva locativa inválido
- codigo: estado_reserva_locativa_invalido
- descripcion: el estado actual de la reserva locativa no admite la operación solicitada.
- tipo: validacion
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-018 — Transición de estado de reserva locativa inválida
- codigo: transicion_estado_reserva_locativa_invalida
- descripcion: la transición de estado solicitada no es válida para el flujo de reserva locativa.
- tipo: validacion
- aplica_a: reserva_locativa
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de contratos de alquiler

### ERR-LOC-019 — Contrato no encontrado
- codigo: contrato_no_encontrado
- descripcion: no existe un contrato de alquiler para el criterio indicado.
- tipo: funcional
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-020 — Contrato inactivo
- codigo: contrato_inactivo
- descripcion: el contrato existe pero no se encuentra activo para la operación solicitada.
- tipo: funcional
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-021 — Contrato cancelado
- codigo: contrato_cancelado
- descripcion: el contrato fue cancelado o invalidado y no admite continuidad ordinaria.
- tipo: funcional
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-022 — Contrato duplicado
- codigo: contrato_duplicado
- descripcion: existe un contrato incompatible o redundante para el mismo contexto locativo.
- tipo: integridad
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-023 — Contrato sin objeto
- codigo: contrato_sin_objeto
- descripcion: el contrato no posee objeto locativo válidamente asociado.
- tipo: validacion
- aplica_a: contrato_alquiler, contrato_objeto_locativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-024 — Contrato sin partes
- codigo: contrato_sin_partes
- descripcion: el contrato no posee partes locativas principales válidamente definidas.
- tipo: validacion
- aplica_a: contrato_alquiler, persona
- origen: DER
- es_reintento_valido: no

### ERR-LOC-025 — Contrato solapado
- codigo: contrato_solapado
- descripcion: existe superposición inválida de contratos sobre el mismo objeto locativo.
- tipo: integridad
- aplica_a: contrato_alquiler, contrato_objeto_locativo, objeto_locativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-026 — Objeto locativo ocupado
- codigo: objeto_locativo_ocupado
- descripcion: el objeto locativo ya se encuentra ocupado por otro vínculo incompatible.
- tipo: funcional
- aplica_a: objeto_locativo, contrato_alquiler, ocupacion_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-027 — Vigencia de contrato inválida
- codigo: vigencia_contrato_invalida
- descripcion: la vigencia informada para el contrato es inválida o inconsistente.
- tipo: validacion
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-028 — Estado de contrato inválido
- codigo: estado_contrato_invalido
- descripcion: el estado actual del contrato no admite la operación solicitada.
- tipo: validacion
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-029 — Transición de estado de contrato inválida
- codigo: transicion_estado_contrato_invalida
- descripcion: la transición de estado solicitada no es válida para el ciclo del contrato.
- tipo: validacion
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### Error implementado — Sin condición económica
- codigo_backend: `SIN_CONDICION_ECONOMICA`
- descripcion: no se permite activar un contrato de alquiler sin `condicion_economica_alquiler`.
- tipo: funcional
- aplica_a: contrato_alquiler, condicion_economica_alquiler
- origen: backend actual
- es_reintento_valido: sí, luego de registrar una condición económica válida

## D. Errores de condiciones económicas

### ERR-LOC-030 — Condición económica no encontrada
- codigo: condicion_economica_no_encontrada
- descripcion: no existe una condición económica para el contrato o criterio indicado.
- tipo: funcional
- aplica_a: condicion_economica_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-031 — Condición económica inválida
- codigo: condicion_economica_invalida
- descripcion: la condición económica informada no cumple con las reglas locativas del sistema.
- tipo: validacion
- aplica_a: condicion_economica_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-032 — Condición económica duplicada
- codigo: condicion_economica_duplicada
- descripcion: existe una condición económica incompatible o redundante para la misma vigencia y contrato.
- tipo: integridad
- aplica_a: condicion_economica_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-033 — Vigencia de condición inválida
- codigo: vigencia_condicion_invalida
- descripcion: la vigencia de la condición económica es inválida o incompatible con otras vigencias.
- tipo: validacion
- aplica_a: condicion_economica_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-034 — Inconsistencia de condición económica
- codigo: inconsistencia_condicion_economica
- descripcion: la condición económica presenta inconsistencia entre montos, periodicidad o actualización.
- tipo: integridad
- aplica_a: condicion_economica_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de ajustes locativos

### ERR-LOC-035 — Ajuste locativo no encontrado
- codigo: ajuste_locativo_no_encontrado
- descripcion: no existe un ajuste locativo para el criterio indicado.
- tipo: funcional
- aplica_a: ajuste_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-036 — Ajuste locativo inválido
- codigo: ajuste_locativo_invalido
- descripcion: el ajuste locativo informado no cumple las reglas del contrato o condición.
- tipo: validacion
- aplica_a: ajuste_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-037 — Ajuste locativo duplicado
- codigo: ajuste_locativo_duplicado
- descripcion: existe un ajuste incompatible o redundante para el mismo período o contrato.
- tipo: integridad
- aplica_a: ajuste_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-038 — Aplicación de ajuste inválida
- codigo: aplicacion_ajuste_invalida
- descripcion: el ajuste no puede aplicarse en el contexto temporal o contractual informado.
- tipo: validacion
- aplica_a: ajuste_alquiler, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-039 — Período de ajuste inválido
- codigo: periodo_ajuste_invalido
- descripcion: el período informado para el ajuste no es válido respecto del contrato o vigencia aplicable.
- tipo: validacion
- aplica_a: ajuste_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-040 — Inconsistencia de ajuste
- codigo: inconsistencia_ajuste
- descripcion: el ajuste locativo presenta inconsistencia entre contrato, condición, período o criterio de actualización.
- tipo: integridad
- aplica_a: ajuste_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores de modificaciones locativas

### ERR-LOC-041 — Modificación locativa no encontrada
- codigo: modificacion_locativa_no_encontrada
- descripcion: no existe una modificación locativa para el criterio indicado.
- tipo: funcional
- aplica_a: modificacion_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-042 — Modificación locativa inválida
- codigo: modificacion_locativa_invalida
- descripcion: la modificación locativa no cumple condiciones válidas para el contrato o contexto informado.
- tipo: validacion
- aplica_a: modificacion_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-043 — Modificación locativa duplicada
- codigo: modificacion_locativa_duplicada
- descripcion: existe una modificación locativa incompatible o redundante sobre el mismo contrato o vigencia.
- tipo: integridad
- aplica_a: modificacion_locativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-044 — Modificación no aplicable
- codigo: modificacion_no_aplicable
- descripcion: la modificación solicitada no puede aplicarse al contrato en su estado actual.
- tipo: funcional
- aplica_a: modificacion_locativa, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-045 — Estado de modificación inválido
- codigo: estado_modificacion_invalido
- descripcion: el estado actual de la modificación no admite la operación solicitada.
- tipo: validacion
- aplica_a: modificacion_locativa
- origen: DEV-SRV
- es_reintento_valido: no

## G. Errores de rescisión y finalización

### ERR-LOC-046 — Rescisión no encontrada
- codigo: rescision_no_encontrada
- descripcion: no existe una rescisión para el criterio indicado.
- tipo: funcional
- aplica_a: rescision_finalizacion_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-047 — Rescisión inválida
- codigo: rescision_invalida
- descripcion: la rescisión informada no cumple con las condiciones locativas exigidas.
- tipo: validacion
- aplica_a: rescision_finalizacion_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-048 — Rescisión duplicada
- codigo: rescision_duplicada
- descripcion: existe una rescisión incompatible o redundante sobre el mismo contrato.
- tipo: integridad
- aplica_a: rescision_finalizacion_alquiler, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-049 — Contrato no rescindible
- codigo: contrato_no_rescindible
- descripcion: el contrato no admite rescisión en el estado actual.
- tipo: funcional
- aplica_a: contrato_alquiler, rescision_finalizacion_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-050 — Contrato ya finalizado
- codigo: contrato_ya_finalizado
- descripcion: el contrato ya se encuentra finalizado y no admite la operación solicitada.
- tipo: funcional
- aplica_a: contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-051 — Estado de rescisión inválido
- codigo: estado_rescision_invalido
- descripcion: el estado actual de la rescisión no admite la operación solicitada.
- tipo: validacion
- aplica_a: rescision_finalizacion_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

## H. Errores de entrega y restitución

### ERR-LOC-052 — Entrega no encontrada
- codigo: entrega_no_encontrada
- descripcion: no existe un registro de entrega para el criterio indicado.
- tipo: funcional
- aplica_a: entrega_restitucion_inmueble
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-053 — Restitución no encontrada
- codigo: restitucion_no_encontrada
- descripcion: no existe un registro de restitución para el criterio indicado.
- tipo: funcional
- aplica_a: entrega_restitucion_inmueble
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-054 — Entrega inválida
- codigo: entrega_invalida
- descripcion: la entrega informada no cumple condiciones válidas respecto del contrato o estado del objeto.
- tipo: validacion
- aplica_a: entrega_restitucion_inmueble, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-055 — Restitución inválida
- codigo: restitucion_invalida
- descripcion: la restitución informada no cumple condiciones válidas respecto del contrato o estado del objeto.
- tipo: validacion
- aplica_a: entrega_restitucion_inmueble, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-056 — Restitución sin contrato
- codigo: restitucion_sin_contrato
- descripcion: no puede registrarse restitución sin vínculo contractual previo válido.
- tipo: validacion
- aplica_a: entrega_restitucion_inmueble, contrato_alquiler
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-057 — Objeto no ocupado
- codigo: objeto_no_ocupado
- descripcion: el objeto locativo no se encuentra ocupado para admitir la restitución solicitada.
- tipo: funcional
- aplica_a: objeto_locativo, ocupacion_locativa, entrega_restitucion_inmueble
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-LOC-058 — Estado de entrega inválido
- codigo: estado_entrega_invalido
- descripcion: el estado actual de entrega o restitución no admite la operación solicitada.
- tipo: validacion
- aplica_a: entrega_restitucion_inmueble
- origen: DEV-SRV
- es_reintento_valido: no

## I. Errores transversales locativos

### ERR-LOC-059 — Versión esperada inválida
- codigo: version_esperada_invalida
- descripcion: la versión esperada no coincide con la versión vigente de la entidad locativa.
- tipo: concurrencia
- aplica_a: entidades write sincronizables del dominio locativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-LOC-060 — Lock lógico activo
- codigo: lock_logico_activo
- descripcion: existe un lock lógico vigente que impide la operación locativa solicitada.
- tipo: concurrencia
- aplica_a: operaciones write sensibles del dominio locativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-LOC-061 — Recurso bloqueado
- codigo: recurso_bloqueado
- descripcion: el recurso locativo requerido se encuentra bloqueado para modificación concurrente.
- tipo: concurrencia
- aplica_a: entidades write del dominio locativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-LOC-062 — Op_id duplicado
- codigo: op_id_duplicado
- descripcion: la operación locativa ya fue registrada previamente con el mismo op_id.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio locativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-LOC-063 — Op_id duplicado con payload distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el mismo op_id fue reutilizado con contenido distinto y constituye conflicto técnico.
- tipo: integridad
- aplica_a: operaciones write sincronizables del dominio locativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-LOC-064 — Conflicto de concurrencia
- codigo: conflicto_concurrencia
- descripcion: la operación locativa no puede completarse por conflicto concurrente sobre la misma entidad o contexto.
- tipo: concurrencia
- aplica_a: entidades write del dominio locativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-LOC-065 — Inconsistencia de contexto técnico
- codigo: inconsistencia_contexto_tecnico
- descripcion: el contexto técnico mínimo exigido para la operación locativa es inválido o insuficiente.
- tipo: validacion
- aplica_a: operaciones write sincronizables del dominio locativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-LOC-066 — Entidad no encontrada
- codigo: entidad_no_encontrada
- descripcion: la entidad locativa requerida no existe en el contexto consultado.
- tipo: funcional
- aplica_a: entidades locativas sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-LOC-067 — Entidad inactiva
- codigo: entidad_inactiva
- descripcion: la entidad locativa existe pero se encuentra inactiva para la operación solicitada.
- tipo: funcional
- aplica_a: entidades locativas sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-LOC-068 — Error de idempotencia
- codigo: error_idempotencia
- descripcion: no puede garantizarse la idempotencia esperada para la operación locativa.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio locativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-LOC-069 — Inconsistencia de objeto locativo
- codigo: inconsistencia_objeto_locativo
- descripcion: el objeto locativo presenta inconsistencia de identidad, disponibilidad, ocupación o vínculo.
- tipo: integridad
- aplica_a: objeto_locativo, reserva_locativa, contrato_alquiler, entrega_restitucion_inmueble
- origen: DER
- es_reintento_valido: no

### ERR-LOC-070 — Conflicto de estado locativo
- codigo: conflicto_estado_locativo
- descripcion: el estado locativo observable entra en conflicto con la operación solicitada o con otra operación vigente.
- tipo: integridad
- aplica_a: solicitud_alquiler, reserva_locativa, contrato_alquiler, modificacion_locativa, rescision_finalizacion_alquiler, entrega_restitucion_inmueble
- origen: DEV-SRV
- es_reintento_valido: no

---

## Reglas de normalización

1. No duplicar errores.
2. Separar errores funcionales de concurrencia.
3. No incluir errores financieros.
4. No incluir errores técnicos de infraestructura profunda.
5. Consolidar variantes similares.
6. Mantener numeración `ERR-LOC-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio locativo.
- No reemplaza el dominio financiero ni inmobiliario.
- Debe mantenerse alineado con CU-LOC y RN-LOC.
- Sirve como base para manejo consistente de errores.
