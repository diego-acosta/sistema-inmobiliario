# CU-FIN — Casos de uso del dominio Financiero

## Objetivo
Definir los casos de uso del dominio financiero.

## Alcance
Incluye relaciones generadoras, obligaciones, imputaciones financieras, ajustes y consultas.

---

## A. Relaciones generadoras

### CU-FIN-001 — Alta de relación generadora
- servicio_origen: SRV-FIN-001
- tipo: write
- objetivo: Registrar una nueva relación generadora dentro del circuito financiero.
- entidades: relacion_generadora
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-002 — Edición de relación generadora en borrador
- servicio_origen: SRV-FIN-001
- tipo: write
- objetivo: Modificar una relación generadora mientras permanezca en estado editable.
- entidades: relacion_generadora
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-003 — Activación de relación generadora
- servicio_origen: SRV-FIN-001
- tipo: write
- objetivo: Activar una relación generadora para habilitar su efecto financiero.
- entidades: relacion_generadora
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-004 — Cancelación de relación generadora
- servicio_origen: SRV-FIN-001
- tipo: write
- objetivo: Cancelar una relación generadora sin perder trazabilidad histórica.
- entidades: relacion_generadora
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-005 — Finalización de relación generadora
- servicio_origen: SRV-FIN-001
- tipo: write
- objetivo: Finalizar una relación generadora cuando su ciclo financiero concluye.
- entidades: relacion_generadora
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

## B. Obligaciones

### CU-FIN-006 — Generación de obligación
- servicio_origen: SRV-FIN-002
- tipo: write
- objetivo: Generar una obligación financiera a partir de la relación generadora correspondiente.
- entidades: obligacion_financiera, relacion_generadora, composicion_obligacion, concepto_financiero
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-007 — Consulta de obligación
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Obtener el detalle operativo de una obligación financiera.
- entidades: obligacion_financiera, composicion_obligacion, concepto_financiero
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-008 — Consulta de obligaciones por relación
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar las obligaciones vinculadas a una relación generadora determinada.
- entidades: obligacion_financiera, relacion_generadora
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-009 — Consulta de estado de obligación
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar el estado financiero vigente de una obligación.
- entidades: obligacion_financiera
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Imputaciones financieras

### CU-FIN-010 — Registro de pago
- servicio_origen: SRV-FIN-003
- tipo: write
- objetivo: Registrar un pago dentro del circuito financiero.
- entidades: movimiento_financiero
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-011 — Imputación de pago a obligación
- servicio_origen: SRV-FIN-003
- tipo: write
- objetivo: Aplicar un pago registrado sobre una obligación financiera determinada.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-012 — Imputación parcial de pago
- servicio_origen: SRV-FIN-003
- tipo: write
- objetivo: Aplicar parcialmente un pago sobre una o más obligaciones según corresponda.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-013 — Imputación múltiple de pago
- servicio_origen: SRV-FIN-003
- tipo: write
- objetivo: Distribuir un pago entre múltiples obligaciones o conceptos financieros.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-014 — Reversión de imputación
- servicio_origen: SRV-FIN-003
- tipo: write
- objetivo: Revertir una imputación financiera previamente aplicada.
- entidades: aplicacion_financiera, movimiento_financiero, obligacion_financiera
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-015 — Consulta de imputaciones
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar imputaciones financieras realizadas sobre pagos y obligaciones.
- entidades: aplicacion_financiera, movimiento_financiero, obligacion_financiera
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Ajustes financieros

### CU-FIN-016 — Generación de ajuste financiero
- servicio_origen: SRV-FIN-004
- tipo: write
- objetivo: Registrar un ajuste financiero sobre una obligación, movimiento o relación.
- entidades: ajuste_financiero, obligacion_financiera, relacion_generadora
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-017 — Aplicación de ajuste
- servicio_origen: SRV-FIN-004
- tipo: write
- objetivo: Aplicar el ajuste financiero sobre la entidad o composición objetivo.
- entidades: ajuste_financiero, obligacion_financiera, movimiento_financiero
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-018 — Anulación de ajuste
- servicio_origen: SRV-FIN-004
- tipo: write
- objetivo: Anular un ajuste financiero manteniendo trazabilidad del cambio.
- entidades: ajuste_financiero
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-FIN-019 — Consulta de ajustes
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar ajustes financieros registrados y su estado operativo.
- entidades: ajuste_financiero
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Consultas financieras

### CU-FIN-020 — Consulta de estado de deuda
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Obtener el estado actual de deuda asociado a relaciones, sujetos u obligaciones.
- entidades: obligacion_financiera, relacion_generadora
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-021 — Consulta de deuda a fecha
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar deuda financiera al corte de una fecha determinada.
- entidades: obligacion_financiera, aplicacion_financiera, movimiento_financiero
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-022 — Consulta de cuenta corriente
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Obtener la cuenta corriente financiera de una relación, sujeto o contrato.
- entidades: cuenta_financiera, movimiento_financiero, obligacion_financiera
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-023 — Consulta de movimientos financieros
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Consultar movimientos financieros registrados en el dominio.
- entidades: movimiento_financiero, aplicacion_financiera
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-FIN-024 — Reporte financiero consolidado
- servicio_origen: SRV-FIN-005
- tipo: read
- objetivo: Emitir una vista consolidada del estado financiero del sistema o de un universo definido.
- entidades: relacion_generadora, obligacion_financiera, movimiento_financiero, aplicacion_financiera, ajuste_financiero
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
3. No mezclar lógica financiera con otros dominios.
4. Consolidar variantes similares.
5. Mantener numeración CU-FIN-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio financiero.
- Es uno de los dominios centrales del sistema.
- Debe mantenerse alineado con DER y con SRV-FIN.
- Sirve como base para implementación backend y API.
