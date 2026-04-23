# EST-LOC — Estados del dominio Locativo

## Objetivo
Definir los estados del dominio locativo.

## Alcance
Incluye solicitudes, reservas, contratos, condiciones, ajustes, modificaciones, rescisión y restitución.

---

## A. Estados de solicitudes

### EST-LOC-001 — Borrador
- codigo: borrador
- tipo: entidad
- aplica_a: solicitud_alquiler
- descripcion: Estado inicial de una solicitud aún no presentada o no evaluada.
- estado_inicial: sí
- estado_final: no

### EST-LOC-002 — Pendiente
- codigo: pendiente
- tipo: entidad
- aplica_a: solicitud_alquiler
- descripcion: La solicitud fue presentada y permanece pendiente de evaluación.
- estado_inicial: no
- estado_final: no

### EST-LOC-003 — Aprobada
- codigo: aprobada
- tipo: entidad
- aplica_a: solicitud_alquiler
- descripcion: La solicitud fue aprobada y puede derivar en una reserva locativa.
- estado_inicial: no
- estado_final: no

### EST-LOC-004 — Rechazada
- codigo: rechazada
- tipo: entidad
- aplica_a: solicitud_alquiler
- descripcion: La solicitud fue rechazada y no continúa su flujo locativo.
- estado_inicial: no
- estado_final: sí

### EST-LOC-005 — Cancelada
- codigo: cancelada
- tipo: entidad
- aplica_a: solicitud_alquiler
- descripcion: La solicitud fue cancelada antes de completar su circuito normal.
- estado_inicial: no
- estado_final: sí

## B. Estados de reservas locativas

### EST-LOC-006 — Borrador
- codigo: borrador
- tipo: entidad
- aplica_a: reserva_locativa
- descripcion: Estado inicial de una reserva locativa aún no formalizada.
- estado_inicial: sí
- estado_final: no

### EST-LOC-007 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: reserva_locativa
- descripcion: La reserva locativa está vigente y mantiene el objeto locativo comprometido.
- estado_inicial: no
- estado_final: no

### EST-LOC-008 — Confirmada
- codigo: confirmada
- tipo: entidad
- aplica_a: reserva_locativa
- descripcion: La reserva fue confirmada y puede derivar en contrato de alquiler.
- estado_inicial: no
- estado_final: no

### EST-LOC-009 — Cancelada
- codigo: cancelada
- tipo: entidad
- aplica_a: reserva_locativa
- descripcion: La reserva locativa fue cancelada y deja de producir efectos operativos.
- estado_inicial: no
- estado_final: sí

### EST-LOC-010 — Vencida
- codigo: vencida
- tipo: entidad
- aplica_a: reserva_locativa
- descripcion: La reserva perdió vigencia por vencimiento de plazo o condición temporal.
- estado_inicial: no
- estado_final: sí

## C. Estados de contratos de alquiler

### EST-LOC-011 — Borrador
- codigo: borrador
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato se encuentra en preparación y aún no produce efectos plenos.
- estado_inicial: sí
- estado_final: no

### EST-LOC-012 — Activo
- codigo: activo
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato está vigente y habilitado para su ejecución locativa.
- estado_inicial: no
- estado_final: no

### EST-LOC-013 — En ejecución
- codigo: en_ejecucion
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato se encuentra en desarrollo operativo dentro de su vigencia.
- estado_inicial: no
- estado_final: no
- observaciones: Puede coexistir conceptualmente con ocupación activa del objeto locativo.

### EST-LOC-014 — Rescindido
- codigo: rescindido
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato fue interrumpido antes de su finalización natural mediante rescisión.
- estado_inicial: no
- estado_final: sí

### EST-LOC-015 — Finalizado
- codigo: finalizado
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato completó su ciclo normal y concluyó su vigencia.
- estado_inicial: no
- estado_final: sí

### EST-LOC-016 — Cancelado
- codigo: cancelado
- tipo: entidad
- aplica_a: contrato_alquiler
- descripcion: El contrato fue cancelado antes de entrar plenamente en ejecución o continuar su curso.
- estado_inicial: no
- estado_final: sí

## D. Estados de condiciones económicas

### EST-LOC-017 — Definidas
- codigo: definidas
- tipo: entidad
- aplica_a: condicion_economica_alquiler
- descripcion: Las condiciones económicas fueron establecidas para el contrato.
- estado_inicial: sí
- estado_final: no

### EST-LOC-018 — Vigentes
- codigo: vigentes
- tipo: entidad
- aplica_a: condicion_economica_alquiler
- descripcion: Las condiciones económicas se encuentran activas y aplicables en el período actual.
- estado_inicial: no
- estado_final: no

### EST-LOC-019 — Modificadas
- codigo: modificadas
- tipo: entidad
- aplica_a: condicion_economica_alquiler
- descripcion: Las condiciones económicas fueron alteradas respecto de una versión o vigencia previa.
- estado_inicial: no
- estado_final: no

### EST-LOC-020 — Inactivas
- codigo: inactivas
- tipo: entidad
- aplica_a: condicion_economica_alquiler
- descripcion: Las condiciones económicas ya no se encuentran operativas para nuevas aplicaciones.
- estado_inicial: no
- estado_final: sí

## E. Estados de ajustes locativos

### EST-LOC-021 — Registrado
- codigo: registrado
- tipo: entidad
- aplica_a: ajuste_alquiler
- descripcion: El ajuste fue incorporado al sistema y se encuentra pendiente de tratamiento operativo.
- estado_inicial: sí
- estado_final: no

### EST-LOC-022 — Pendiente de aplicación
- codigo: pendiente_aplicacion
- tipo: entidad
- aplica_a: ajuste_alquiler
- descripcion: El ajuste ya está definido pero todavía no fue aplicado sobre la condición económica operativa.
- estado_inicial: no
- estado_final: no

### EST-LOC-023 — Aplicado
- codigo: aplicado
- tipo: entidad
- aplica_a: ajuste_alquiler
- descripcion: El ajuste fue aplicado y produce efecto en la operación locativa.
- estado_inicial: no
- estado_final: sí

### EST-LOC-024 — Anulado
- codigo: anulado
- tipo: entidad
- aplica_a: ajuste_alquiler
- descripcion: El ajuste quedó sin efecto antes o después de su evaluación operativa.
- estado_inicial: no
- estado_final: sí

## F. Estados de modificaciones locativas

### EST-LOC-025 — Registrada
- codigo: registrada
- tipo: entidad
- aplica_a: modificacion_locativa
- descripcion: La modificación fue registrada y cuenta con trazabilidad dentro del contrato.
- estado_inicial: sí
- estado_final: no

### EST-LOC-026 — Vigente
- codigo: vigente
- tipo: entidad
- aplica_a: modificacion_locativa
- descripcion: La modificación locativa se encuentra activa y aplicable al contrato.
- estado_inicial: no
- estado_final: no

### EST-LOC-027 — Anulada
- codigo: anulada
- tipo: entidad
- aplica_a: modificacion_locativa
- descripcion: La modificación locativa fue dejada sin efecto y no debe seguir aplicándose.
- estado_inicial: no
- estado_final: sí

## G. Estados de rescisión y finalización

### EST-LOC-028 — Registrada
- codigo: registrada
- tipo: entidad
- aplica_a: rescision_finalizacion_alquiler
- descripcion: La rescisión o finalización fue registrada y aún puede requerir pasos adicionales.
- estado_inicial: sí
- estado_final: no

### EST-LOC-029 — En proceso
- codigo: en_proceso
- tipo: entidad
- aplica_a: rescision_finalizacion_alquiler
- descripcion: La rescisión o finalización se encuentra en tratamiento operativo.
- estado_inicial: no
- estado_final: no

### EST-LOC-030 — Efectiva
- codigo: efectiva
- tipo: entidad
- aplica_a: rescision_finalizacion_alquiler
- descripcion: La rescisión o finalización ya produjo efectos sobre la vigencia contractual.
- estado_inicial: no
- estado_final: sí

### EST-LOC-031 — Anulada
- codigo: anulada
- tipo: entidad
- aplica_a: rescision_finalizacion_alquiler
- descripcion: La rescisión o finalización registrada fue anulada.
- estado_inicial: no
- estado_final: sí

## H. Estados de entrega y restitución

### EST-LOC-032 — Pendiente de entrega
- codigo: pendiente_entrega
- tipo: entidad
- aplica_a: entrega_restitucion_inmueble
- descripcion: El proceso de entrega inicial del inmueble aún no fue concretado.
- estado_inicial: sí
- estado_final: no

### EST-LOC-033 — Entregado
- codigo: entregado
- tipo: entidad
- aplica_a: entrega_restitucion_inmueble
- descripcion: El inmueble fue entregado y habilita el inicio de ocupación.
- estado_inicial: no
- estado_final: no

### EST-LOC-034 — En ocupación
- codigo: en_ocupacion
- tipo: entidad
- aplica_a: entrega_restitucion_inmueble
- descripcion: El inmueble permanece ocupado dentro del marco contractual vigente.
- estado_inicial: no
- estado_final: no

### EST-LOC-035 — Restitución pendiente
- codigo: restitucion_pendiente
- tipo: entidad
- aplica_a: entrega_restitucion_inmueble
- descripcion: El contrato se encuentra en etapa de devolución pendiente del inmueble.
- estado_inicial: no
- estado_final: no

### EST-LOC-036 — Restituido
- codigo: restituido
- tipo: entidad
- aplica_a: entrega_restitucion_inmueble
- descripcion: El inmueble fue restituido y finalizó la ocupación asociada.
- estado_inicial: no
- estado_final: sí

## I. Estados operativos transversales

### EST-LOC-037 — Éxito
- codigo: exito
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación locativa fue ejecutada correctamente.
- estado_inicial: no
- estado_final: sí

### EST-LOC-038 — Error
- codigo: error
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación locativa terminó con error bloqueante.
- estado_inicial: no
- estado_final: sí

### EST-LOC-039 — Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación detectó una colisión funcional o técnica que impide su cierre normal.
- estado_inicial: no
- estado_final: sí

### EST-LOC-040 — Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación fue rechazada por validación o por regla del dominio.
- estado_inicial: no
- estado_final: sí

### EST-LOC-041 — Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación no puede continuar por bloqueo lógico o restricción equivalente.
- estado_inicial: no
- estado_final: sí

### EST-LOC-042 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: ejecucion_servicio_locativo
- descripcion: La operación detectó inconsistencias entre contexto, entidad y estado esperado.
- estado_inicial: no
- estado_final: sí

### EST-LOC-043 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: control_versionado_locativo
- descripcion: La versión esperada coincide con la versión vigente al momento de procesar la operación.
- estado_inicial: no
- estado_final: sí

### EST-LOC-044 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: control_versionado_locativo
- descripcion: La versión esperada no coincide con la versión vigente.
- estado_inicial: no
- estado_final: sí

### EST-LOC-045 — Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: control_idempotencia_locativa
- descripcion: La operación fue ejecutada y registrada válidamente.
- estado_inicial: no
- estado_final: sí

### EST-LOC-046 — Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: control_idempotencia_locativa
- descripcion: La operación ya había sido ejecutada con el mismo contexto idempotente.
- estado_inicial: no
- estado_final: sí

### EST-LOC-047 — Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: control_idempotencia_locativa
- descripcion: La operación repite identificador idempotente pero con inconsistencia relevante respecto de la ejecución previa.
- estado_inicial: no
- estado_final: sí

---

## Reglas de normalización

1. No duplicar estados.
2. Consolidar estados comunes.
3. No mezclar estados con eventos.
4. Mantener estados reutilizables.
5. Mantener numeración `EST-LOC-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV y del DER locativo.
- No define lógica, solo estados posibles.
- Debe mantenerse alineado con RN-LOC.
- Sirve como base para validaciones y flujos.
