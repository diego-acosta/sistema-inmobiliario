# RN-LOC — Reglas del dominio Locativo

## Objetivo
Definir reglas del dominio locativo.

## Alcance
Incluye solicitudes, reservas, contratos, condiciones económicas, ajustes, modificaciones, rescisión y restitución.

---

## A. Reglas de solicitudes de alquiler

### RN-LOC-001 — La solicitud debe vincular solicitante y objeto locativo
- descripcion: toda solicitud de alquiler válida debe referenciar al menos un solicitante y un objeto locativo.
- aplica_a: solicitud_alquiler, persona, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-002 — La solicitud puede aprobarse o rechazarse
- descripcion: la solicitud admite resolución positiva o negativa dentro del flujo locativo.
- aplica_a: solicitud_alquiler
- origen_principal: DEV-SRV

### RN-LOC-003 — La solicitud aprobada puede derivar en reserva
- descripcion: la aprobación de la solicitud habilita su continuidad hacia una reserva locativa cuando el proceso lo contemple.
- aplica_a: solicitud_alquiler, reserva_locativa
- origen_principal: DEV-SRV

### RN-LOC-004 — La solicitud no implica contrato
- descripcion: la mera existencia o aprobación de la solicitud no constituye contrato de alquiler.
- aplica_a: solicitud_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-005 — La solicitud no genera efectos financieros
- descripcion: la solicitud no define deuda, saldo ni pagos como verdad financiera primaria.
- aplica_a: solicitud_alquiler
- origen_principal: DEV-SRV

## B. Reglas de reservas locativas

### RN-LOC-006 — La reserva locativa debe vincular objeto locativo
- descripcion: toda reserva locativa válida debe asociarse a un objeto locativo.
- aplica_a: reserva_locativa, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-007 — Un objeto no puede estar reservado simultáneamente en conflicto
- descripcion: un mismo objeto locativo no debe quedar comprometido por reservas incompatibles entre sí.
- aplica_a: reserva_locativa, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-008 — La reserva puede confirmarse o cancelarse
- descripcion: la reserva locativa admite confirmación o cancelación conforme a su flujo locativo.
- aplica_a: reserva_locativa
- origen_principal: DEV-SRV

### RN-LOC-009 — La reserva confirmada puede derivar en contrato
- descripcion: una reserva confirmada puede utilizarse como base para registrar un contrato de alquiler.
- aplica_a: reserva_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-010 — La reserva no implica contrato activo
- descripcion: una reserva vigente o confirmada no equivale por sí misma a un contrato de alquiler activo.
- aplica_a: reserva_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-011 — La reserva no genera obligaciones financieras por sí misma
- descripcion: la reserva locativa no crea por sí sola obligaciones financieras en el dominio financiero.
- aplica_a: reserva_locativa
- origen_principal: DEV-SRV

## C. Reglas de contratos de alquiler

### RN-LOC-012 — El contrato debe vincular objeto locativo
- descripcion: todo contrato de alquiler válido debe asociarse a uno o más objetos locativos.
- aplica_a: contrato_alquiler, contrato_objeto_locativo, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-013 — El contrato debe vincular locador y locatario
- descripcion: la relación contractual debe identificar las partes principales de la locación.
- aplica_a: contrato_alquiler, persona
- origen_principal: DER

### RN-LOC-014 — El contrato puede activarse, modificarse, rescindirse o finalizarse
- descripcion: el contrato posee ciclo de vida propio con transiciones funcionales definidas.
- aplica_a: contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-015 — Un contrato activo implica ocupación del objeto
- descripcion: la activación contractual habilita la ocupación locativa del objeto dentro del marco del dominio.
- aplica_a: contrato_alquiler, ocupacion_locativa, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-016 — Un contrato no puede solaparse en el mismo objeto
- descripcion: no deben coexistir contratos incompatibles sobre el mismo objeto locativo en vigencias superpuestas.
- aplica_a: contrato_alquiler, contrato_objeto_locativo, objeto_locativo
- origen_principal: DEV-SRV

### RN-LOC-017 — Un contrato debe tener vigencia definida
- descripcion: todo contrato de alquiler debe poseer una delimitación temporal explícita o determinable.
- aplica_a: contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-018 — Un contrato puede existir sin ajustes aplicados inicialmente
- descripcion: la existencia del contrato no depende de que ya se hayan aplicado ajustes locativos.
- aplica_a: contrato_alquiler, ajuste_alquiler
- origen_principal: DEV-SRV

## D. Reglas de condiciones económicas

### RN-LOC-019 — Las condiciones económicas deben asociarse a un contrato
- descripcion: las condiciones económicas locativas se definen en relación con un contrato de alquiler.
- aplica_a: condicion_economica_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-020 — Las condiciones definen montos, periodicidad y reglas de actualización
- descripcion: la condición económica delimita canon, frecuencia y criterios de actualización aplicables.
- aplica_a: condicion_economica_alquiler
- origen_principal: DEV-SRV

### RN-LOC-021 — Las condiciones no ejecutan cálculos financieros directamente
- descripcion: la condición económica describe parámetros locativos pero no sustituye la lógica financiera de cálculo.
- aplica_a: condicion_economica_alquiler
- origen_principal: DEV-SRV

### RN-LOC-022 — Las condiciones pueden modificarse según reglas del sistema
- descripcion: las condiciones económicas pueden cambiar dentro de las restricciones y vigencias definidas.
- aplica_a: condicion_economica_alquiler
- origen_principal: DEV-SRV

### RN-LOC-023 — Las condiciones deben tener vigencia
- descripcion: toda condición económica válida debe poder ubicarse temporalmente dentro del contrato.
- aplica_a: condicion_economica_alquiler
- origen_principal: DEV-SRV

## E. Reglas de ajustes locativos

### RN-LOC-024 — Un ajuste se aplica sobre un contrato
- descripcion: todo ajuste locativo debe quedar asociado al contrato que modifica operativamente.
- aplica_a: ajuste_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-025 — Un ajuste no modifica el contrato original sino su valor operativo
- descripcion: el ajuste altera condiciones operativas vigentes sin reemplazar la identidad del contrato base.
- aplica_a: ajuste_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-026 — Un ajuste debe respetar reglas de periodicidad
- descripcion: los ajustes locativos deben aplicarse conforme a la periodicidad definida para el contrato o condición.
- aplica_a: ajuste_alquiler, condicion_economica_alquiler
- origen_principal: DEV-SRV

### RN-LOC-027 — Un ajuste puede depender de índices externos
- descripcion: el ajuste puede tomar referencia de índices o mecanismos externos definidos en la condición locativa.
- aplica_a: ajuste_alquiler, condicion_economica_alquiler
- origen_principal: DEV-SRV

### RN-LOC-028 — Un ajuste no genera por sí mismo obligaciones financieras
- descripcion: el ajuste locativo no sustituye la generación de obligaciones, que corresponde al dominio financiero.
- aplica_a: ajuste_alquiler
- origen_principal: DEV-SRV

## F. Reglas de modificaciones locativas

### RN-LOC-029 — Una modificación altera condiciones del contrato
- descripcion: la modificación locativa cambia condiciones relevantes del vínculo contractual.
- aplica_a: modificacion_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-030 — Una modificación no elimina el contrato original
- descripcion: el contrato original permanece como referencia aun cuando sus condiciones sean modificadas.
- aplica_a: modificacion_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-031 — Una modificación debe ser trazable
- descripcion: toda modificación locativa debe preservar trazabilidad sobre qué se alteró y cuándo.
- aplica_a: modificacion_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-032 — Una modificación puede ser anulada
- descripcion: la modificación locativa admite anulación cuando el flujo y la política del sistema lo permitan.
- aplica_a: modificacion_locativa
- origen_principal: DEV-SRV

## G. Reglas de rescisión y finalización

### RN-LOC-033 — Una rescisión corta la vigencia del contrato
- descripcion: la rescisión interrumpe la continuidad de vigencia del contrato de alquiler.
- aplica_a: rescision_finalizacion_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-034 — Una rescisión no elimina historial
- descripcion: la rescisión no borra antecedentes ni registros históricos del contrato.
- aplica_a: rescision_finalizacion_alquiler, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-035 — Una rescisión puede implicar penalidades fuera de este dominio
- descripcion: la rescisión puede producir efectos económicos, pero su cálculo no pertenece al dominio locativo.
- aplica_a: rescision_finalizacion_alquiler
- origen_principal: DEV-SRV

### RN-LOC-036 — Un contrato finalizado no debe continuar su flujo
- descripcion: un contrato finalizado no puede seguir avanzando por el ciclo locativo ordinario.
- aplica_a: contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-037 — Un contrato rescindido no puede reactivarse
- descripcion: una vez rescindido, el contrato no debe volver a estado activo como el mismo vínculo locativo.
- aplica_a: contrato_alquiler, rescision_finalizacion_alquiler
- origen_principal: DEV-SRV

## H. Reglas de entrega y restitución

### RN-LOC-038 — La entrega implica inicio de ocupación
- descripcion: la entrega del objeto locativo constituye el inicio material de la ocupación prevista por el contrato.
- aplica_a: entrega_restitucion_inmueble, ocupacion_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-039 — La restitución implica finalización de ocupación
- descripcion: la restitución del objeto locativo marca el cierre material de la ocupación.
- aplica_a: entrega_restitucion_inmueble, ocupacion_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-040 — La restitución debe vincularse a contrato
- descripcion: no debe registrarse una restitución sin referencia contractual válida.
- aplica_a: entrega_restitucion_inmueble, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-041 — No puede haber restitución sin contrato previo
- descripcion: la restitución requiere la existencia previa de un vínculo locativo que justifique la entrega del objeto.
- aplica_a: entrega_restitucion_inmueble, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-042 — La restitución no implica automáticamente cancelación financiera
- descripcion: la restitución del objeto no cancela por sí sola obligaciones o saldos del contrato.
- aplica_a: entrega_restitucion_inmueble
- origen_principal: DEV-SRV

## I. Reglas transversales locativas

### RN-LOC-043 — El dominio locativo no calcula deuda ni pagos
- descripcion: la deuda, el saldo, los pagos y su aplicación pertenecen al dominio financiero.
- aplica_a: dominio locativo
- origen_principal: DEV-SRV

### RN-LOC-044 — Los efectos financieros se delegan al dominio financiero
- descripcion: los impactos económicos derivados del vínculo locativo deben resolverse en el dominio financiero.
- aplica_a: contrato_alquiler, condicion_economica_alquiler, ajuste_alquiler, rescision_finalizacion_alquiler
- origen_principal: DEV-SRV

### RN-LOC-045 — La disponibilidad del objeto depende del dominio inmobiliario
- descripcion: la elegibilidad y disponibilidad material del objeto locativo provienen del dominio inmobiliario.
- aplica_a: objeto_locativo, reserva_locativa, contrato_alquiler
- origen_principal: DEV-SRV

### RN-LOC-046 — El contrato define ocupación, no propiedad
- descripcion: el contrato locativo regula uso y ocupación del objeto, no su titularidad dominial.
- aplica_a: contrato_alquiler, ocupacion_locativa, objeto_locativo
- origen_principal: DER

### RN-LOC-047 — Los estados locativos no deben confundirse con estados financieros
- descripcion: los estados del vínculo locativo deben resolverse con semántica locativa y no financiera.
- aplica_a: contrato_alquiler, reserva_locativa, rescision_finalizacion_alquiler
- origen_principal: DEV-SRV

### RN-LOC-048 — Toda operación write sincronizable debe respetar control técnico transversal
- descripcion: las mutaciones locativas sincronizables deben respetar versionado, op_id y outbox conforme al marco transversal aplicable.
- aplica_a: operaciones write sincronizables del dominio locativo
- origen_principal: DEV-SRV
- observaciones: la semántica técnica proviene del marco transversal; aquí se aplica como regla de dominio.

---

## Reglas de normalización

1. No duplicar reglas.
2. Consolidar variantes similares.
3. Separar claramente locativo de financiero.
4. No incluir reglas técnicas profundas.
5. Mantener numeración RN-LOC-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio locativo.
- No reemplaza el DER ni el dominio financiero.
- Debe mantenerse alineado con CU-LOC.
- Es base para validaciones backend.
