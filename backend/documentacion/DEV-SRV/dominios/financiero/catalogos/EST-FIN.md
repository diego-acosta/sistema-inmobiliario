# EST-FIN — Estados del dominio Financiero

## Objetivo
Definir los estados del dominio financiero.

## Alcance
Incluye relaciones generadoras, obligaciones, imputaciones, ajustes y estado de deuda.

---

## A. Estados de relaciones generadoras

### EST-FIN-001 — Borrador
- codigo: borrador
- tipo: entidad
- aplica_a: relacion_generadora
- descripcion: Estado inicial de una relación generadora aún no activada.
- estado_inicial: sí
- estado_final: no

### EST-FIN-002 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: relacion_generadora
- descripcion: La relación generadora se encuentra habilitada para producir efecto financiero.
- estado_inicial: no
- estado_final: no

### EST-FIN-003 — Cancelada
- codigo: cancelada
- tipo: entidad
- aplica_a: relacion_generadora
- descripcion: La relación generadora dejó de habilitar nuevas obligaciones u operaciones futuras compatibles.
- estado_inicial: no
- estado_final: sí

### EST-FIN-004 — Finalizada
- codigo: finalizada
- tipo: entidad
- aplica_a: relacion_generadora
- descripcion: La relación generadora alcanzó su cierre funcional completo sin pendientes incompatibles.
- estado_inicial: no
- estado_final: sí

## B. Estados de obligaciones

### EST-FIN-005 — Pendiente
- codigo: pendiente
- tipo: entidad
- aplica_a: obligacion_financiera
- descripcion: La obligación se encuentra vigente con saldo exigible pendiente de cancelación.
- estado_inicial: sí
- estado_final: no

### EST-FIN-006 — Vencida
- codigo: vencida
- tipo: entidad
- aplica_a: obligacion_financiera
- descripcion: La obligación superó su fecha de vencimiento manteniendo saldo pendiente.
- estado_inicial: no
- estado_final: no

### EST-FIN-007 — Parcialmente cancelada
- codigo: parcialmente_cancelada
- tipo: entidad
- aplica_a: obligacion_financiera
- descripcion: La obligación recibió imputaciones parciales pero aún conserva saldo pendiente.
- estado_inicial: no
- estado_final: no

### EST-FIN-008 — Cancelada
- codigo: cancelada
- tipo: entidad
- aplica_a: obligacion_financiera
- descripcion: La obligación quedó cancelada en forma total y ya no mantiene saldo exigible.
- estado_inicial: no
- estado_final: sí

## C. Estados de imputaciones

### EST-FIN-009 — Registrada
- codigo: registrada
- tipo: entidad
- aplica_a: aplicacion_financiera
- descripcion: La imputación fue registrada dentro del circuito financiero.
- estado_inicial: sí
- estado_final: no

### EST-FIN-010 — Aplicada
- codigo: aplicada
- tipo: entidad
- aplica_a: aplicacion_financiera
- descripcion: La imputación ya produjo efecto sobre el saldo de la obligación objetivo.
- estado_inicial: no
- estado_final: no

### EST-FIN-011 — Parcial
- codigo: parcial
- tipo: entidad
- aplica_a: aplicacion_financiera
- descripcion: La imputación cubrió solo una parte del saldo aplicable.
- estado_inicial: no
- estado_final: no

### EST-FIN-012 — Anulada
- codigo: anulada
- tipo: entidad
- aplica_a: aplicacion_financiera
- descripcion: La imputación fue anulada según el circuito financiero permitido.
- estado_inicial: no
- estado_final: sí

### EST-FIN-013 — Revertida
- codigo: revertida
- tipo: entidad
- aplica_a: aplicacion_financiera
- descripcion: La imputación fue revertida, restaurando su efecto financiero anterior.
- estado_inicial: no
- estado_final: sí

## D. Estados de ajustes

### EST-FIN-014 — Generado
- codigo: generado
- tipo: entidad
- aplica_a: ajuste_financiero
- descripcion: El ajuste financiero fue creado y se encuentra disponible para su aplicación.
- estado_inicial: sí
- estado_final: no

### EST-FIN-015 — Aplicado
- codigo: aplicado
- tipo: entidad
- aplica_a: ajuste_financiero
- descripcion: El ajuste financiero produjo efecto sobre la obligación o saldo correspondiente.
- estado_inicial: no
- estado_final: no

### EST-FIN-016 — Anulado
- codigo: anulado
- tipo: entidad
- aplica_a: ajuste_financiero
- descripcion: El ajuste financiero fue dejado sin efecto.
- estado_inicial: no
- estado_final: sí

## E. Estados de deuda

### EST-FIN-017 — Sin deuda
- codigo: sin_deuda
- tipo: entidad
- aplica_a: estado_deuda
- descripcion: El sujeto, relación o universo consultado no presenta deuda exigible.
- estado_inicial: no
- estado_final: no

### EST-FIN-018 — Con deuda
- codigo: con_deuda
- tipo: entidad
- aplica_a: estado_deuda
- descripcion: Existe deuda financiera vigente en el universo consultado.
- estado_inicial: no
- estado_final: no

### EST-FIN-019 — Deuda parcial
- codigo: deuda_parcial
- tipo: entidad
- aplica_a: estado_deuda
- descripcion: La deuda se encuentra parcialmente cancelada pero aún mantiene saldo remanente.
- estado_inicial: no
- estado_final: no

### EST-FIN-020 — Deuda vencida
- codigo: deuda_vencida
- tipo: entidad
- aplica_a: estado_deuda
- descripcion: Existe deuda con vencimiento superado y saldo aún pendiente.
- estado_inicial: no
- estado_final: no

### EST-FIN-021 — Deuda cancelada
- codigo: deuda_cancelada
- tipo: entidad
- aplica_a: estado_deuda
- descripcion: La deuda del universo consultado quedó totalmente cancelada.
- estado_inicial: no
- estado_final: sí

## F. Estados operativos transversales

### EST-FIN-022 — Éxito
- codigo: exito
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación financiera se ejecutó correctamente.
- estado_inicial: no
- estado_final: sí

### EST-FIN-023 — Error
- codigo: error
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación financiera finalizó con error bloqueante.
- estado_inicial: no
- estado_final: sí

### EST-FIN-024 — Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación detectó una colisión funcional o técnica que impide su cierre normal.
- estado_inicial: no
- estado_final: sí

### EST-FIN-025 — Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación fue rechazada por validación o por regla financiera aplicable.
- estado_inicial: no
- estado_final: sí

### EST-FIN-026 — Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación no puede avanzar por lock o restricción vigente.
- estado_inicial: no
- estado_final: sí

### EST-FIN-027 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: ejecucion_servicio_financiero
- descripcion: La operación detectó inconsistencias entre contexto, entidad y estado esperado.
- estado_inicial: no
- estado_final: sí

### EST-FIN-028 — Versión válida
- codigo: version_valida
- tipo: operativo
- aplica_a: control_versionado_financiero
- descripcion: La versión esperada coincide con la versión vigente de la entidad financiera.
- estado_inicial: no
- estado_final: sí

### EST-FIN-029 — Versión inválida
- codigo: version_invalida
- tipo: operativo
- aplica_a: control_versionado_financiero
- descripcion: La versión esperada no coincide con la versión vigente de la entidad financiera.
- estado_inicial: no
- estado_final: sí

### EST-FIN-030 — Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: control_idempotencia_financiera
- descripcion: La operación fue ejecutada y registrada válidamente.
- estado_inicial: no
- estado_final: sí

### EST-FIN-031 — Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: control_idempotencia_financiera
- descripcion: La operación ya había sido registrada previamente con el mismo identificador operativo.
- estado_inicial: no
- estado_final: sí

### EST-FIN-032 — Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: control_idempotencia_financiera
- descripcion: La operación repite identificador pero con diferencias incompatibles respecto de la ejecución previa.
- estado_inicial: no
- estado_final: sí

---

## Reglas de normalización

1. No duplicar estados.
2. Consolidar estados comunes.
3. No mezclar estados con eventos.
4. Mantener estados reutilizables.
5. Mantener numeración `EST-FIN-XXX`.

---

## Notas

- Este catálogo deriva del DEV-SRV y del DER financiero.
- Es uno de los dominios más críticos del sistema.
- No define lógica, solo estados posibles.
- Debe mantenerse alineado con RN-FIN.
- Sirve como base para validaciones y flujos.
