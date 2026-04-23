# CU-LOC — Casos de uso del dominio Locativo

## Objetivo
Definir los casos de uso del dominio locativo relacionados a alquileres.

## Alcance
Incluye solicitudes, reservas locativas, contratos, condiciones económicas, ajustes, modificaciones, rescisiones y restitución de inmuebles.

---

## A. Solicitudes de alquiler

### CU-LOC-001 — Alta de solicitud de alquiler
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: registrar una solicitud inicial vinculada al proceso locativo cuando el flujo la contemple.
- entidades: solicitud_alquiler, objeto_locativo
- criticidad: media
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-002 — Modificación de solicitud
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: actualizar datos permitidos de una solicitud locativa.
- entidades: solicitud_alquiler
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-003 — Cancelación de solicitud
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: cancelar una solicitud de alquiler antes de su conversión a una etapa posterior.
- entidades: solicitud_alquiler
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-004 — Aprobación de solicitud
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: aprobar una solicitud de alquiler para permitir su continuidad locativa.
- entidades: solicitud_alquiler
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-005 — Rechazo de solicitud
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: rechazar una solicitud de alquiler según validaciones del proceso.
- entidades: solicitud_alquiler
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-006 — Consulta de solicitud
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar una solicitud de alquiler y su estado locativo.
- entidades: solicitud_alquiler
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Reservas locativas

### CU-LOC-007 — Alta de reserva locativa
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: registrar una reserva locativa sobre un objeto locativo.
- entidades: reserva_locativa, objeto_locativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-008 — Modificación de reserva locativa
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: actualizar datos permitidos de una reserva locativa.
- entidades: reserva_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-009 — Cancelación de reserva locativa
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: cancelar una reserva locativa antes de su conversión a contrato.
- entidades: reserva_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-010 — Confirmación de reserva locativa
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: confirmar una reserva locativa para habilitar la generación contractual.
- entidades: reserva_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-011 — Asociación de objeto locativo
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: vincular un objeto locativo a una reserva.
- entidades: reserva_locativa, objeto_locativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-012 — Consulta de reserva locativa
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar una reserva locativa y su situación actual.
- entidades: reserva_locativa
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Contratos de alquiler

### CU-LOC-013 — Alta de contrato de alquiler
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: registrar un contrato de alquiler como entidad raíz del dominio locativo.
- entidades: contrato_alquiler, contrato_objeto_locativo
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-014 — Modificación de contrato
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: actualizar datos permitidos de un contrato de alquiler.
- entidades: contrato_alquiler
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-015 — Cancelación de contrato
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: invalidar o cancelar un contrato cuando el proceso lo permita.
- entidades: contrato_alquiler
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-016 — Activación de contrato
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: activar un contrato para llevarlo a estado vigente.
- entidades: contrato_alquiler
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-017 — Asociación de objeto locativo a contrato
- servicio_origen: SRV-LOC-001
- tipo: write
- objetivo: vincular uno o más objetos locativos a un contrato.
- entidades: contrato_alquiler, contrato_objeto_locativo, objeto_locativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-018 — Consulta de contrato
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar un contrato de alquiler y su estado locativo.
- entidades: contrato_alquiler
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Condiciones económicas

### CU-LOC-019 — Definición de condiciones económicas
- servicio_origen: SRV-LOC-002
- tipo: write
- objetivo: definir condiciones económicas vigentes para un contrato locativo.
- entidades: condicion_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-020 — Modificación de condiciones económicas
- servicio_origen: SRV-LOC-002
- tipo: write
- objetivo: actualizar condiciones económicas de un contrato conforme a reglas de vigencia.
- entidades: condicion_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-021 — Consulta de condiciones económicas
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar condiciones económicas vigentes o históricas de un contrato.
- entidades: condicion_locativa
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Ajustes locativos

### CU-LOC-022 — Registro de ajuste locativo
- servicio_origen: SRV-LOC-002
- tipo: write
- objetivo: registrar un ajuste locativo derivado de condiciones o esquemas de actualización.
- entidades: ajuste_alquiler, condicion_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-023 — Modificación de ajuste locativo
- servicio_origen: SRV-LOC-002
- tipo: write
- objetivo: actualizar un ajuste locativo registrado cuando la política lo permita.
- entidades: ajuste_alquiler
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-024 — Aplicación de ajuste
- servicio_origen: SRV-LOC-002
- tipo: write
- objetivo: aplicar un ajuste locativo al esquema vigente del contrato.
- entidades: ajuste_alquiler, condicion_locativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-025 — Consulta de ajustes
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar ajustes locativos aplicados o pendientes.
- entidades: ajuste_alquiler
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## F. Modificaciones locativas

### CU-LOC-026 — Registro de modificación locativa
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: registrar una modificación relevante sobre la relación locativa o su vigencia.
- entidades: modificacion_locativa, contrato_alquiler
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-027 — Modificación de modificación locativa
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: actualizar una modificación locativa previamente registrada.
- entidades: modificacion_locativa
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-028 — Anulación de modificación
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: anular una modificación locativa cuando corresponda.
- entidades: modificacion_locativa
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-029 — Consulta de modificaciones
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar modificaciones locativas registradas sobre un contrato o cartera.
- entidades: modificacion_locativa
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## G. Rescisión y finalización

### CU-LOC-030 — Registro de rescisión de contrato
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: registrar la rescisión anticipada de un contrato de alquiler.
- entidades: rescision_finalizacion_alquiler, contrato_alquiler
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-031 — Modificación de rescisión
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: actualizar datos permitidos de una rescisión registrada.
- entidades: rescision_finalizacion_alquiler
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-032 — Anulación de rescisión
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: anular una rescisión registrada cuando la política lo permita.
- entidades: rescision_finalizacion_alquiler
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-033 — Finalización de contrato
- servicio_origen: SRV-LOC-004
- tipo: write
- objetivo: cerrar un contrato por vencimiento u otra causal válida.
- entidades: contrato_alquiler, rescision_finalizacion_alquiler
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-034 — Consulta de rescisión
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar rescisión o finalización de contrato y su trazabilidad.
- entidades: rescision_finalizacion_alquiler
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## H. Entrega y restitución

### CU-LOC-035 — Registro de entrega de inmueble
- servicio_origen: SRV-LOC-005
- tipo: write
- objetivo: registrar la entrega inicial del objeto locativo dentro del ciclo del contrato.
- entidades: entrega_restitucion_inmueble, contrato_alquiler, objeto_locativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-036 — Registro de restitución
- servicio_origen: SRV-LOC-005
- tipo: write
- objetivo: registrar la restitución del objeto locativo al cierre o corte del vínculo locativo.
- entidades: entrega_restitucion_inmueble, contrato_alquiler, objeto_locativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-037 — Modificación de entrega o restitución
- servicio_origen: SRV-LOC-005
- tipo: write
- objetivo: actualizar datos permitidos de una entrega o restitución registrada.
- entidades: entrega_restitucion_inmueble
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-LOC-038 — Consulta de entrega o restitución
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar registros de entrega y restitución del objeto locativo.
- entidades: entrega_restitucion_inmueble
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## I. Consultas locativas

### CU-LOC-039 — Consulta operativa locativa
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar una vista operativa consolidada del dominio locativo.
- entidades: solicitud_alquiler, reserva_locativa, contrato_alquiler, condicion_locativa, ajuste_alquiler, modificacion_locativa, rescision_finalizacion_alquiler, entrega_restitucion_inmueble
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-LOC-040 — Consulta integral de contrato locativo
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar un contrato locativo con sus condiciones, objetos y cambios asociados.
- entidades: contrato_alquiler, contrato_objeto_locativo, condicion_locativa, modificacion_locativa
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-LOC-041 — Consulta de estado locativo
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: consultar el estado locativo de una relación contractual o de un objeto locativo.
- entidades: contrato_alquiler, objeto_locativo, rescision_finalizacion_alquiler, entrega_restitucion_inmueble
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-LOC-042 — Reporte locativo consolidado
- servicio_origen: SRV-LOC-007
- tipo: read
- objetivo: obtener una vista consolidada del dominio locativo para seguimiento y análisis.
- entidades: reserva_locativa, contrato_alquiler, condicion_locativa, ajuste_alquiler, modificacion_locativa, rescision_finalizacion_alquiler, entrega_restitucion_inmueble
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

---

## Reglas de normalización

1. No duplicar casos.
2. No mezclar estados con acciones.
3. No mezclar lógica financiera.
4. Consolidar variantes similares.
5. Mantener numeración CU-LOC-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio locativo.
- No reemplaza al dominio financiero.
- Sirve como base para implementación backend.
