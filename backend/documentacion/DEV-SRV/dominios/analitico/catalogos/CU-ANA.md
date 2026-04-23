# CU-ANA — Casos de uso del dominio Analítico

## Objetivo
Definir los casos de uso del dominio Analítico orientados a implementación backend.

## Alcance del dominio
Incluye consultas analíticas transversales, vistas consolidadas por dominio, reportes, indicadores, métricas, cruces de información y análisis histórico sin generar efectos persistentes.

## Bloques del dominio
- Consulta general del sistema
- Consulta analítica por dominio
- Consulta analítica financiera especializada

---

## A. Consulta general del sistema

### CU-ANA-001 — Consulta general del sistema
- servicio_origen: SRV-ANA-001
- tipo: read
- objetivo: Consultar una vista consolidada y transversal del sistema con métricas globales, resúmenes por dominio e indicadores agregados.
- entidades: dominios funcionales consolidados, indicadores_globales, metricas_globales
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Consulta analítica por dominio

### CU-ANA-002 — Consulta analítica inmobiliaria
- servicio_origen: SRV-ANA-002
- tipo: read
- objetivo: Consultar inventario inmobiliario, disponibilidad, ocupación e indicadores resumidos del activo.
- entidades: desarrollo, inmueble, unidad_funcional, disponibilidad, ocupacion
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-003 — Consulta analítica comercial
- servicio_origen: SRV-ANA-003
- tipo: read
- objetivo: Consultar reservas, ventas, instrumentos y estados resumidos del pipeline comercial.
- entidades: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-004 — Consulta analítica locativa
- servicio_origen: SRV-ANA-004
- tipo: read
- objetivo: Consultar cartera locativa, contratos, reservas, condiciones económicas y estados resumidos del ciclo locativo.
- entidades: cartera_locativa, reserva_locativa, contrato_alquiler, condicion_economica_alquiler, ajuste_alquiler
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-005 — Consulta analítica financiera
- servicio_origen: SRV-ANA-005
- tipo: read
- objetivo: Consultar deuda, saldo, cobranzas, mora, refinanciaciones e indicadores financieros consolidados de alto nivel.
- entidades: relacion_generadora, obligacion_financiera, movimiento_financiero, aplicacion_financiera, cuenta_financiera
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-006 — Consulta analítica documental
- servicio_origen: SRV-ANA-006
- tipo: read
- objetivo: Consultar actividad documental, numeración, estados documentales y trazabilidad agregada.
- entidades: documento, tipo_documental, numeracion_documental, estado_documental, historial_documental
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-007 — Consulta analítica operativa y administrativa
- servicio_origen: SRV-ANA-007
- tipo: read
- objetivo: Consultar sucursales, instalaciones, cajas, auditoría, usuarios y actividad operativa-administrativa en forma consolidada.
- entidades: sucursal, instalacion, caja_operativa, usuario, auditoria
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Consulta analítica financiera especializada

### CU-ANA-008 — Consulta de deuda
- servicio_origen: SRV-ANA-008
- tipo: read
- objetivo: Consultar deuda consolidada, distribuida y temporal según dimensiones financieras relevantes.
- entidades: obligacion_financiera, composicion_obligacion, relacion_generadora, estado_financiero
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-009 — Consulta de flujo financiero
- servicio_origen: SRV-ANA-009
- tipo: read
- objetivo: Consultar ingresos, egresos y evolución temporal del flujo financiero consolidado.
- entidades: movimiento_financiero, aplicacion_financiera, cuenta_financiera, flujo_financiero
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-010 — Consulta de cobranzas
- servicio_origen: SRV-ANA-010
- tipo: read
- objetivo: Consultar montos cobrados, distribución, composición y evolución temporal de cobranzas.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera, relacion_generadora
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-011 — Consulta de mora
- servicio_origen: SRV-ANA-011
- tipo: read
- objetivo: Consultar deuda vencida, saldos morosos, evolución temporal e indicadores de concentración de mora.
- entidades: obligacion_financiera, composicion_obligacion, relacion_generadora, estado_financiero
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-012 — Consulta de refinanciaciones
- servicio_origen: SRV-ANA-012
- tipo: read
- objetivo: Consultar refinanciaciones, obligaciones originales y derivadas, y su evolución temporal.
- entidades: refinanciacion, obligacion_financiera, relacion_generadora, estado_financiero
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-013 — Consulta de saldos a fecha
- servicio_origen: SRV-ANA-013
- tipo: read
- objetivo: Consultar saldos financieros al corte, comparaciones entre fechas y distribución por dimensiones.
- entidades: obligacion_financiera, composicion_obligacion, obligacion_obligado, relacion_generadora, estado_financiero
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ANA-014 — Consulta de cancelaciones anticipadas
- servicio_origen: SRV-ANA-014
- tipo: read
- objetivo: Consultar cancelaciones anticipadas, montos asociados, impacto financiero y evolución temporal.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera, relacion_generadora
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Analítico.
- No reemplaza al CAT-CU maestro.
- Los casos aquí listados se usan como apoyo a implementación backend.
- Debe mantenerse alineado con los servicios `SRV-ANA` y con `SYS-MAP-002`.
- Este dominio es estrictamente read-only y no debe incorporar altas, modificaciones, bajas ni ejecución de procesos.
