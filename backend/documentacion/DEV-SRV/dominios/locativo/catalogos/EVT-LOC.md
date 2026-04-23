# EVT-LOC — Eventos del dominio Locativo

## Objetivo
Definir eventos observables del dominio locativo.

## Alcance
Incluye solicitudes, reservas, contratos, condiciones, ajustes, modificaciones, rescisión y restitución.

---

## A. Eventos de solicitudes

### EVT-LOC-001 — Solicitud de alquiler creada
- codigo: solicitud_alquiler_creada
- descripcion: se registró una nueva solicitud de alquiler.
- origen_principal: SRV-LOC-001
- entidad_principal: solicitud_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-002 — Solicitud de alquiler modificada
- codigo: solicitud_alquiler_modificada
- descripcion: se actualizaron datos de una solicitud de alquiler.
- origen_principal: SRV-LOC-001
- entidad_principal: solicitud_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-003 — Solicitud de alquiler aprobada
- codigo: solicitud_alquiler_aprobada
- descripcion: una solicitud de alquiler fue aprobada dentro del flujo locativo.
- origen_principal: SRV-LOC-001
- entidad_principal: solicitud_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-004 — Solicitud de alquiler rechazada
- codigo: solicitud_alquiler_rechazada
- descripcion: una solicitud de alquiler fue rechazada.
- origen_principal: SRV-LOC-001
- entidad_principal: solicitud_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-005 — Solicitud de alquiler cancelada
- codigo: solicitud_alquiler_cancelada
- descripcion: una solicitud de alquiler fue cancelada.
- origen_principal: SRV-LOC-001
- entidad_principal: solicitud_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de reservas locativas

### EVT-LOC-006 — Reserva locativa creada
- codigo: reserva_locativa_creada
- descripcion: se registró una nueva reserva locativa.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-007 — Reserva locativa modificada
- codigo: reserva_locativa_modificada
- descripcion: se actualizaron datos de una reserva locativa.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-008 — Reserva locativa confirmada
- codigo: reserva_locativa_confirmada
- descripcion: una reserva locativa fue confirmada para continuar hacia contrato.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-009 — Reserva locativa cancelada
- codigo: reserva_locativa_cancelada
- descripcion: una reserva locativa fue cancelada.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-010 — Objeto locativo asociado a reserva
- codigo: objeto_locativo_asociado_a_reserva
- descripcion: se vinculó un objeto locativo a una reserva.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-011 — Objeto locativo desasociado de reserva
- codigo: objeto_locativo_desasociado_de_reserva
- descripcion: se desvinculó un objeto locativo de una reserva locativa.
- origen_principal: SRV-LOC-001
- entidad_principal: reserva_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de contratos de alquiler

### EVT-LOC-012 — Contrato de alquiler creado
- codigo: contrato_alquiler_creado
- descripcion: se registró un nuevo contrato de alquiler.
- origen_principal: SRV-LOC-001
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-013 — Contrato de alquiler modificado
- codigo: contrato_alquiler_modificado
- descripcion: se actualizaron datos de un contrato de alquiler.
- origen_principal: SRV-LOC-001
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-014 — Contrato de alquiler activado
- codigo: contrato_alquiler_activado
- descripcion: un contrato de alquiler alcanzó estado activo o vigente.
- origen_principal: SRV-LOC-001
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-015 — Contrato de alquiler cancelado
- codigo: contrato_alquiler_cancelado
- descripcion: un contrato de alquiler fue cancelado o invalidado.
- origen_principal: SRV-LOC-001
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-016 — Contrato de alquiler finalizado
- codigo: contrato_alquiler_finalizado
- descripcion: un contrato de alquiler completó o cerró su vigencia funcional.
- origen_principal: SRV-LOC-004
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-017 — Objeto locativo asociado a contrato
- codigo: objeto_locativo_asociado_a_contrato
- descripcion: se vinculó un objeto locativo a un contrato de alquiler.
- origen_principal: SRV-LOC-001
- entidad_principal: contrato_objeto_locativo
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-018 — Ocupación iniciada por contrato
- codigo: contrato_ocupacion_iniciada
- descripcion: el contrato activó el inicio de ocupación sobre el objeto locativo.
- origen_principal: SRV-LOC-005
- entidad_principal: ocupacion_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## D. Eventos de condiciones económicas

### EVT-LOC-019 — Condiciones económicas definidas
- codigo: condiciones_economicas_definidas
- descripcion: se definieron condiciones económicas para un contrato locativo.
- origen_principal: SRV-LOC-002
- entidad_principal: condicion_economica_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-020 — Condiciones económicas modificadas
- codigo: condiciones_economicas_modificadas
- descripcion: se actualizaron condiciones económicas de un contrato.
- origen_principal: SRV-LOC-002
- entidad_principal: condicion_economica_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-021 — Condiciones económicas activadas
- codigo: condiciones_economicas_activadas
- descripcion: un conjunto de condiciones económicas pasó a regir efectivamente sobre el contrato.
- origen_principal: SRV-LOC-002
- entidad_principal: condicion_economica_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## E. Eventos de ajustes locativos

### EVT-LOC-022 — Ajuste locativo registrado
- codigo: ajuste_locativo_registrado
- descripcion: se registró un ajuste locativo sobre un contrato.
- origen_principal: SRV-LOC-002
- entidad_principal: ajuste_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-023 — Ajuste locativo modificado
- codigo: ajuste_locativo_modificado
- descripcion: se actualizaron datos de un ajuste locativo.
- origen_principal: SRV-LOC-002
- entidad_principal: ajuste_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-024 — Ajuste locativo aplicado
- codigo: ajuste_locativo_aplicado
- descripcion: un ajuste locativo fue aplicado operativamente al contrato.
- origen_principal: SRV-LOC-002
- entidad_principal: ajuste_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-025 — Ajuste locativo anulado
- codigo: ajuste_locativo_anulado
- descripcion: un ajuste locativo fue dejado sin efecto.
- origen_principal: SRV-LOC-002
- entidad_principal: ajuste_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## F. Eventos de modificaciones locativas

### EVT-LOC-026 — Modificación locativa registrada
- codigo: modificacion_locativa_registrada
- descripcion: se registró una modificación sobre la relación locativa o sus condiciones.
- origen_principal: SRV-LOC-004
- entidad_principal: modificacion_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-027 — Modificación locativa modificada
- codigo: modificacion_locativa_modificada
- descripcion: se actualizaron datos de una modificación locativa.
- origen_principal: SRV-LOC-004
- entidad_principal: modificacion_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-028 — Modificación locativa anulada
- codigo: modificacion_locativa_anulada
- descripcion: una modificación locativa fue anulada.
- origen_principal: SRV-LOC-004
- entidad_principal: modificacion_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## G. Eventos de rescisión y finalización

### EVT-LOC-029 — Rescisión de contrato registrada
- codigo: rescision_contrato_registrada
- descripcion: se registró una rescisión sobre un contrato de alquiler.
- origen_principal: SRV-LOC-004
- entidad_principal: rescision_finalizacion_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-030 — Rescisión de contrato modificada
- codigo: rescision_contrato_modificada
- descripcion: se actualizaron datos de una rescisión de contrato.
- origen_principal: SRV-LOC-004
- entidad_principal: rescision_finalizacion_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-031 — Rescisión de contrato anulada
- codigo: rescision_contrato_anulada
- descripcion: una rescisión de contrato fue anulada.
- origen_principal: SRV-LOC-004
- entidad_principal: rescision_finalizacion_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-032 — Contrato rescindido
- codigo: contrato_rescindido
- descripcion: el contrato quedó rescindido y fuera de su ciclo ordinario.
- origen_principal: SRV-LOC-004
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-033 — Contrato finalizado
- codigo: contrato_finalizado
- descripcion: el contrato completó o cerró su ciclo locativo.
- origen_principal: SRV-LOC-004
- entidad_principal: contrato_alquiler
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## H. Eventos de entrega y restitución

### EVT-LOC-034 — Entrega de inmueble registrada
- codigo: entrega_inmueble_registrada
- descripcion: se registró la entrega del objeto locativo al inicio de la ocupación.
- origen_principal: SRV-LOC-005
- entidad_principal: entrega_restitucion_inmueble
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-035 — Restitución de inmueble registrada
- codigo: restitucion_inmueble_registrada
- descripcion: se registró la restitución del objeto locativo.
- origen_principal: SRV-LOC-005
- entidad_principal: entrega_restitucion_inmueble
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-036 — Restitución de inmueble confirmada
- codigo: restitucion_inmueble_confirmada
- descripcion: la restitución del inmueble quedó confirmada dentro del proceso locativo.
- origen_principal: SRV-LOC-005
- entidad_principal: entrega_restitucion_inmueble
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-LOC-037 — Ocupación finalizada
- codigo: ocupacion_finalizada
- descripcion: la ocupación locativa del objeto fue dada por finalizada.
- origen_principal: SRV-LOC-005
- entidad_principal: ocupacion_locativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## I. Notas de compatibilidad transversal

- los eventos locativos no generan deuda por sí mismos
- los eventos locativos pueden disparar efectos en financiero (obligaciones)
- los eventos locativos afectan disponibilidad en inmobiliario
- esos efectos no deben duplicarse como eventos locativos
- los writes sincronizables usan op_id y outbox

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio locativo.
- No reemplaza eventos financieros ni administrativos.
- Debe mantenerse alineado con CU-LOC y RN-LOC.
- Es base para trazabilidad y observabilidad del dominio.
