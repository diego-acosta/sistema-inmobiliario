# EVT-FIN — Eventos del dominio Financiero

## Objetivo
Definir eventos observables del dominio financiero.

## Alcance
Incluye relaciones generadoras, obligaciones, imputaciones, ajustes y consultas.

---

## A. Eventos de relaciones generadoras

### EVT-FIN-001 — Relación generadora creada
- codigo: relacion_generadora_creada
- descripcion: Se registró una nueva relación generadora dentro del dominio financiero.
- origen_principal: SRV-FIN-001
- entidad_principal: relacion_generadora
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-002 — Relación generadora modificada
- codigo: relacion_generadora_modificada
- descripcion: Se modificó una relación generadora en un estado compatible con edición.
- origen_principal: SRV-FIN-001
- entidad_principal: relacion_generadora
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-003 — Relación generadora activada
- codigo: relacion_generadora_activada
- descripcion: La relación generadora pasó a estado activo y habilitó su efecto financiero correspondiente.
- origen_principal: SRV-FIN-001
- entidad_principal: relacion_generadora
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-004 — Relación generadora cancelada
- codigo: relacion_generadora_cancelada
- descripcion: La relación generadora fue cancelada y dejó de habilitar nuevas obligaciones incompatibles con ese estado.
- origen_principal: SRV-FIN-001
- entidad_principal: relacion_generadora
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-005 — Relación generadora finalizada
- codigo: relacion_generadora_finalizada
- descripcion: La relación generadora alcanzó su cierre financiero completo.
- origen_principal: SRV-FIN-001
- entidad_principal: relacion_generadora
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de obligaciones

### EVT-FIN-006 — Obligación generada
- codigo: obligacion_generada
- descripcion: Se generó una nueva obligación financiera a partir de una relación generadora.
- origen_principal: SRV-FIN-002
- entidad_principal: obligacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-007 — Obligación modificada
- codigo: obligacion_modificada
- descripcion: Se registró una modificación permitida sobre una obligación financiera cuando el modelo lo admite.
- origen_principal: SRV-FIN-002
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí
- observaciones: Solo aplica si el modelo financiero contempla mutaciones válidas sobre la obligación ya generada.

### EVT-FIN-008 — Obligación vencida
- codigo: obligacion_vencida
- descripcion: La obligación alcanzó su vencimiento y pasó a condición financiera vencida.
- origen_principal: SRV-FIN-002
- entidad_principal: obligacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-009 — Obligación cancelada
- codigo: obligacion_cancelada
- descripcion: La obligación quedó cancelada financieramente.
- origen_principal: SRV-FIN-002
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-010 — Obligación ajustada
- codigo: obligacion_ajustada
- descripcion: La obligación recibió un ajuste financiero que modificó su valor visible.
- origen_principal: SRV-FIN-004
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de imputaciones financieras

### EVT-FIN-011 — Pago registrado
- codigo: pago_registrado
- descripcion: Se registró un pago o movimiento financiero con capacidad de imputación.
- origen_principal: SRV-FIN-003
- entidad_principal: movimiento_financiero
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-012 — Imputación realizada
- codigo: imputacion_realizada
- descripcion: Se aplicó una imputación financiera sobre una obligación determinada.
- origen_principal: SRV-FIN-003
- entidad_principal: aplicacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-013 — Imputación parcial aplicada
- codigo: imputacion_parcial_aplicada
- descripcion: Se aplicó parcialmente un pago o crédito sobre una obligación.
- origen_principal: SRV-FIN-003
- entidad_principal: aplicacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-014 — Imputación múltiple aplicada
- codigo: imputacion_multiple_aplicada
- descripcion: Se distribuyó una imputación sobre múltiples obligaciones o conceptos financieros.
- origen_principal: SRV-FIN-003
- entidad_principal: aplicacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-015 — Imputación revertida
- codigo: imputacion_revertida
- descripcion: Se revirtió una imputación financiera previamente aplicada.
- origen_principal: SRV-FIN-003
- entidad_principal: aplicacion_financiera
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-016 — Imputación anulada
- codigo: imputacion_anulada
- descripcion: La imputación fue anulada como hecho observable del circuito financiero.
- origen_principal: SRV-FIN-003
- entidad_principal: aplicacion_financiera
- tipo_evento: historizacion
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí
- observaciones: Aplicable cuando el modelo distingue anulación de reversión.

## D. Eventos de ajustes financieros

### EVT-FIN-017 — Ajuste generado
- codigo: ajuste_generado
- descripcion: Se registró un nuevo ajuste financiero sobre una obligación o contexto asociado.
- origen_principal: SRV-FIN-004
- entidad_principal: ajuste_financiero
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-018 — Ajuste aplicado
- codigo: ajuste_aplicado
- descripcion: El ajuste financiero fue aplicado y produjo efecto sobre el valor financiero visible.
- origen_principal: SRV-FIN-004
- entidad_principal: ajuste_financiero
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-019 — Ajuste anulado
- codigo: ajuste_anulado
- descripcion: El ajuste financiero fue anulado preservando la trazabilidad del cambio.
- origen_principal: SRV-FIN-004
- entidad_principal: ajuste_financiero
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-020 — Ajuste recalculado
- codigo: ajuste_recalculado
- descripcion: El ajuste financiero fue recalculado cuando el modelo operativo así lo permite.
- origen_principal: SRV-FIN-004
- entidad_principal: ajuste_financiero
- tipo_evento: historizacion
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí
- observaciones: Aplicable solo si el ajuste admite recomputación explícita dentro del modelo financiero.

## E. Eventos de estado financiero

### EVT-FIN-021 — Deuda generada
- codigo: deuda_generada
- descripcion: Se originó deuda financiera visible como resultado de la generación de obligaciones.
- origen_principal: SRV-FIN-002
- entidad_principal: obligacion_financiera
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-022 — Deuda actualizada
- codigo: deuda_actualizada
- descripcion: La deuda visible fue actualizada por ajustes, imputaciones o vencimientos.
- origen_principal: SRV-FIN-005
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí

### EVT-FIN-023 — Deuda cancelada
- codigo: deuda_cancelada
- descripcion: La deuda asociada quedó cancelada total o funcionalmente.
- origen_principal: SRV-FIN-003
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-FIN-024 — Saldo actualizado
- codigo: saldo_actualizado
- descripcion: Se actualizó el saldo financiero visible de una obligación, relación o cuenta.
- origen_principal: SRV-FIN-003
- entidad_principal: obligacion_financiera
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí
- observaciones: Puede derivar de imputaciones, ajustes u otras mutaciones financieras válidas.

### EVT-FIN-025 — Estado financiero consolidado calculado
- codigo: estado_financiero_consolidado_calculado
- descripcion: Se calculó un estado financiero consolidado como hecho observable del procesamiento financiero cuando corresponde.
- origen_principal: SRV-FIN-005
- entidad_principal: estado_financiero
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí
- observaciones: Solo aplicable si el cálculo consolidado se registra explícitamente como hecho observable y no como simple consulta.

## F. Notas de compatibilidad transversal

- El dominio financiero es el único responsable del cálculo de deuda.
- Los eventos financieros no deben duplicarse en otros dominios.
- Otros dominios pueden disparar eventos financieros.
- Esos disparadores no deben registrarse como eventos financieros principales.
- Los writes sincronizables utilizan `op_id` y outbox según CORE-EF.

---

## Reglas de normalización

1. No listar consultas como eventos salvo excepción justificada.
2. No duplicar eventos bajo distintos nombres.
3. No usar “éxito” o “error”.
4. Mantener eventos centrados en cambios reales de estado financiero.
5. Mantener numeración `EVT-FIN-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio financiero.
- Es uno de los dominios más críticos del sistema.
- No reemplaza eventos administrativos ni técnicos.
- Debe mantenerse alineado con CU-FIN y RN-FIN.
- Es base para trazabilidad, auditoría y outbox financiero.
