# CU-LOC — Casos de uso del dominio Locativo

## Objetivo
Definir los casos de uso locativos del sistema.

## Alcance
Incluye contratos de alquiler, condiciones, vigencia y finalización.

---

## A. Gestión de contratos locativos

### CU-LOC-001 — Alta de contrato locativo
- tipo: write
- objetivo: Registrar un nuevo contrato de alquiler dentro del dominio locativo.
- entidades: contrato_locativo
- criticidad: crítica

### CU-LOC-002 — Modificación de contrato locativo
- tipo: write
- objetivo: Actualizar datos relevantes de un contrato locativo vigente o editable.
- entidades: contrato_locativo
- criticidad: alta

### CU-LOC-003 — Cancelación de contrato locativo
- tipo: write
- objetivo: Cancelar un contrato locativo preservando su trazabilidad contractual, aplicable a contratos no activados o sin vigencia efectiva, sin confundirse con rescisión contractual.
- entidades: contrato_locativo
- criticidad: alta

## B. Condiciones locativas

### CU-LOC-004 — Definición de condiciones locativas
- tipo: write
- objetivo: Registrar las condiciones locativas iniciales aplicables a un contrato.
- entidades: contrato_locativo, condicion_locativa
- criticidad: alta

### CU-LOC-005 — Modificación de condiciones locativas
- tipo: write
- objetivo: Actualizar condiciones locativas dentro del marco permitido por el contrato.
- entidades: contrato_locativo, condicion_locativa
- criticidad: alta

### CU-LOC-006 — Consulta de condiciones locativas
- tipo: read
- objetivo: Consultar las condiciones locativas vigentes o históricas de un contrato.
- entidades: contrato_locativo, condicion_locativa
- criticidad: media

## C. Vigencia y estados contractuales

### CU-LOC-007 — Activación de contrato locativo
- tipo: write
- objetivo: Activar un contrato locativo para iniciar formalmente su vigencia operativa.
- entidades: contrato_locativo
- criticidad: crítica

### CU-LOC-008 — Suspensión de contrato locativo
- tipo: write
- objetivo: Suspender temporalmente un contrato locativo dentro de las reglas del dominio, sin implicar finalización ni rescisión y manteniendo la vigencia contractual en estado suspendido.
- entidades: contrato_locativo
- criticidad: alta

### CU-LOC-009 — Finalización de contrato locativo
- tipo: write
- objetivo: Finalizar un contrato locativo al concluir su ciclo de vida contractual.
- entidades: contrato_locativo
- criticidad: alta

## D. Renovaciones

### CU-LOC-010 — Generación de renovación
- tipo: write
- objetivo: Registrar una renovación contractual para extender o reconfigurar la vigencia locativa, pudiendo generar una nueva vigencia o un nuevo contrato derivado según reglas del dominio.
- entidades: contrato_locativo, renovacion_locativa
- criticidad: alta

### CU-LOC-011 — Confirmación de renovación
- tipo: write
- objetivo: Confirmar una renovación locativa para consolidar su efecto contractual.
- entidades: contrato_locativo, renovacion_locativa
- criticidad: alta

## E. Rescisiones

### CU-LOC-012 — Solicitud de rescisión
- tipo: write
- objetivo: Registrar la solicitud de rescisión de un contrato locativo.
- entidades: contrato_locativo, rescision_locativa
- criticidad: alta

### CU-LOC-013 — Aprobación de rescisión
- tipo: write
- objetivo: Aprobar una rescisión locativa cuando se cumplen las condiciones del dominio.
- entidades: contrato_locativo, rescision_locativa
- criticidad: alta

### CU-LOC-014 — Ejecución de rescisión
- tipo: write
- objetivo: Ejecutar la rescisión locativa para producir el cierre contractual correspondiente.
- entidades: contrato_locativo, rescision_locativa
- criticidad: crítica

## F. Consultas locativas

### CU-LOC-015 — Consulta de contrato locativo
- tipo: read
- objetivo: Consultar el detalle de un contrato locativo determinado.
- entidades: contrato_locativo
- criticidad: media

### CU-LOC-016 — Consulta de contratos locativos
- tipo: read
- objetivo: Listar y filtrar contratos locativos según criterios operativos.
- entidades: contrato_locativo
- criticidad: media

### CU-LOC-017 — Consulta de estado contractual
- tipo: read
- objetivo: Consultar el estado contractual vigente de un contrato locativo.
- entidades: contrato_locativo
- criticidad: media

### CU-LOC-018 — Consulta de historial contractual
- tipo: read
- objetivo: Consultar la evolución histórica de un contrato locativo incluyendo estados, renovaciones y rescisiones.
- entidades: contrato_locativo, historial_contrato
- criticidad: media

---

## Reglas

1. No generar obligaciones financieras.
2. No registrar pagos.
3. No incluir lógica comercial.
4. No incluir gestión de inmuebles.
5. Mantener separación con FIN.

---

## Notas

- Este dominio define contratos y su ciclo de vida.
- Un contrato locativo no se considera vigente hasta su activación explícita.
- La alta de contrato locativo no implica inicio de vigencia ni efectos operativos.
- No calcula deuda ni pagos.
- Es el origen del dominio financiero.
- Debe mantenerse alineado con COM y FIN.
