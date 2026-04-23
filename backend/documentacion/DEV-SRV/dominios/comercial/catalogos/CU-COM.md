# CU-COM — Casos de uso del dominio Comercial

## Objetivo
Definir los casos de uso del dominio comercial relacionados a reservas, ventas, instrumentos, cesiones, escrituraciones y rescisiones.

## Alcance
Incluye la gestión de operaciones comerciales sobre objetos inmobiliarios.

---

## A. Reservas

### CU-COM-001 — Alta de reserva de venta
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: registrar una nueva reserva comercial sobre uno o más objetos inmobiliarios.
- entidades: reserva_venta, objeto_inmobiliario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-002 — Modificación de reserva
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: actualizar datos permitidos de una reserva existente.
- entidades: reserva_venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-003 — Cancelación de reserva
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: cancelar una reserva de venta según condiciones del proceso comercial.
- entidades: reserva_venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-004 — Confirmación de reserva
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: confirmar una reserva para habilitar su continuidad comercial.
- entidades: reserva_venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-005 — Asociación de objeto inmobiliario a reserva
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: vincular un objeto inmobiliario a una reserva comercial.
- entidades: reserva_venta, objeto_inmobiliario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-006 — Desasociación de objeto inmobiliario
- servicio_origen: SRV-COM-001
- tipo: write
- objetivo: desvincular un objeto inmobiliario de una reserva cuando el proceso lo permita.
- entidades: reserva_venta, objeto_inmobiliario
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-007 — Consulta de reserva
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar una reserva comercial y su estado.
- entidades: reserva_venta
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-008 — Consulta de reservas por estado
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar reservas comerciales filtradas por estado.
- entidades: reserva_venta
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Ventas

### CU-COM-009 — Alta de venta
- servicio_origen: SRV-COM-002
- tipo: write
- objetivo: registrar una operación de venta sobre objetos inmobiliarios.
- entidades: venta, venta_objeto_inmobiliario
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-010 — Modificación de venta
- servicio_origen: SRV-COM-002
- tipo: write
- objetivo: actualizar datos permitidos de una venta existente.
- entidades: venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-011 — Cancelación de venta
- servicio_origen: SRV-COM-002
- tipo: write
- objetivo: cancelar una venta conforme a las reglas del proceso comercial.
- entidades: venta
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-012 — Confirmación de venta
- servicio_origen: SRV-COM-002
- tipo: write
- objetivo: confirmar una venta y consolidar su estado comercial.
- entidades: venta
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-013 — Asociación de objeto inmobiliario a venta
- servicio_origen: SRV-COM-002
- tipo: write
- objetivo: vincular uno o más objetos inmobiliarios a una venta.
- entidades: venta, venta_objeto_inmobiliario, objeto_inmobiliario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-014 — Consulta de venta
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar una operación de venta y su estado comercial.
- entidades: venta
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-015 — Consulta de ventas por estado
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar ventas filtradas por estado comercial.
- entidades: venta
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Instrumentos comerciales

### CU-COM-016 — Generación de instrumento de compraventa
- servicio_origen: SRV-COM-004
- tipo: write
- objetivo: registrar un instrumento comercial asociado a una operación de compraventa.
- entidades: instrumento_compraventa, instrumento_objeto_inmobiliario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-017 — Modificación de instrumento
- servicio_origen: SRV-COM-004
- tipo: write
- objetivo: actualizar datos permitidos de un instrumento comercial.
- entidades: instrumento_compraventa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-018 — Anulación de instrumento
- servicio_origen: SRV-COM-004
- tipo: write
- objetivo: anular un instrumento comercial conforme al proceso definido.
- entidades: instrumento_compraventa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-019 — Asociación de instrumento a operación
- servicio_origen: SRV-COM-004
- tipo: write
- objetivo: vincular un instrumento comercial con una operación de reserva o venta.
- entidades: instrumento_compraventa, reserva_venta, venta
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-020 — Consulta de instrumento
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar un instrumento comercial y su estado.
- entidades: instrumento_compraventa
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-021 — Consulta de instrumentos por operación
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar instrumentos asociados a una operación comercial.
- entidades: instrumento_compraventa, reserva_venta, venta
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Cesiones

### CU-COM-022 — Registro de cesión
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: registrar una cesión sobre una operación comercial existente.
- entidades: cesion, venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-023 — Modificación de cesión
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: actualizar datos permitidos de una cesión.
- entidades: cesion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-024 — Anulación de cesión
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: anular una cesión registrada.
- entidades: cesion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-025 — Consulta de cesión
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar una cesión comercial y su estado.
- entidades: cesion
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Escrituración

### CU-COM-026 — Registro de escrituración
- servicio_origen: SRV-COM-006
- tipo: write
- objetivo: registrar el proceso de escrituración asociado a una operación comercial.
- entidades: escrituracion, venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-027 — Modificación de escrituración
- servicio_origen: SRV-COM-006
- tipo: write
- objetivo: actualizar datos permitidos de una escrituración.
- entidades: escrituracion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-028 — Anulación de escrituración
- servicio_origen: SRV-COM-006
- tipo: write
- objetivo: anular un registro de escrituración.
- entidades: escrituracion
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-029 — Consulta de escrituración
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar la información de escrituración de una operación comercial.
- entidades: escrituracion
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## F. Rescisiones comerciales

### CU-COM-030 — Registro de rescisión de venta
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: registrar una rescisión sobre una venta cuando el proceso comercial lo contemple.
- entidades: rescision_venta, venta
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-031 — Modificación de rescisión
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: actualizar datos permitidos de una rescisión comercial.
- entidades: rescision_venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-032 — Anulación de rescisión
- servicio_origen: SRV-COM-005
- tipo: write
- objetivo: anular un registro de rescisión comercial.
- entidades: rescision_venta
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: sí
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-COM-033 — Consulta de rescisión
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar una rescisión de venta y su estado comercial.
- entidades: rescision_venta
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## G. Consultas comerciales

### CU-COM-034 — Consulta operativa comercial
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar una vista operativa consolidada del dominio comercial.
- entidades: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion, rescision_venta
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-035 — Consulta integral de operación comercial
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar de forma integral una operación comercial con sus vínculos relevantes.
- entidades: reserva_venta, venta, instrumento_compraventa, objeto_inmobiliario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-036 — Consulta de estado comercial
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: consultar el estado comercial de una operación o conjunto de operaciones.
- entidades: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion, rescision_venta
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-COM-037 — Reporte comercial consolidado
- servicio_origen: SRV-COM-008
- tipo: read
- objetivo: obtener una vista consolidada del dominio comercial para seguimiento y análisis.
- entidades: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion, rescision_venta
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
3. No mezclar lógica comercial con financiera.
4. Consolidar variantes similares.
5. Mantener numeración CU-COM-XXX.

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio comercial.
- No reemplaza catálogo funcional global.
- Sirve como base para implementación backend.
