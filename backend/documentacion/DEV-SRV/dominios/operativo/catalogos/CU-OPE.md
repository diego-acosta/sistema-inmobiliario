# CU-OPE — Casos de uso del dominio Operativo

## Objetivo
Definir los casos de uso del dominio Operativo orientados a implementación backend.

## Alcance del dominio
Incluye gestión de sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consultas operativas consolidadas.

## Bloques del dominio
- Sucursales
- Instalaciones
- Caja operativa
- Movimientos de caja
- Cierre de caja
- Consultas operativas

---

## A. Sucursales

### CU-OPE-001 — Alta de sucursal
- servicio_origen: SRV-OPE-001
- tipo: write
- objetivo: Registrar una nueva sucursal preservando consistencia organizativa y trazabilidad.
- entidades: sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-002 — Modificación de sucursal
- servicio_origen: SRV-OPE-001
- tipo: write
- objetivo: Actualizar datos de una sucursal existente respetando versionado y consistencia operativa.
- entidades: sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-003 — Baja lógica de sucursal
- servicio_origen: SRV-OPE-001
- tipo: write
- objetivo: Aplicar baja lógica sobre una sucursal preservando historial y trazabilidad.
- entidades: sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-004 — Consulta de sucursal
- servicio_origen: SRV-OPE-001
- tipo: read
- objetivo: Consultar sucursales y sus datos organizativos.
- entidades: sucursal
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Instalaciones

### CU-OPE-005 — Alta de instalación
- servicio_origen: SRV-OPE-002
- tipo: write
- objetivo: Registrar una nueva instalación vinculada a una sucursal preservando consistencia operativa y trazabilidad técnica.
- entidades: instalacion, sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-006 — Modificación de instalación
- servicio_origen: SRV-OPE-002
- tipo: write
- objetivo: Actualizar datos de una instalación existente respetando su vínculo con sucursal y el control de versión.
- entidades: instalacion, sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-007 — Baja lógica de instalación
- servicio_origen: SRV-OPE-002
- tipo: write
- objetivo: Aplicar baja lógica sobre una instalación preservando historial y consistencia operativa.
- entidades: instalacion, sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-008 — Consulta de instalación
- servicio_origen: SRV-OPE-002
- tipo: read
- objetivo: Consultar instalaciones y su relación con la sucursal asociada.
- entidades: instalacion, sucursal
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Caja operativa

### CU-OPE-009 — Apertura de caja
- servicio_origen: SRV-OPE-003
- tipo: write
- objetivo: Iniciar una nueva caja operativa vinculada a instalación y usuario responsable.
- entidades: caja_operativa, instalacion, sucursal, usuario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-010 — Cambio de estado de caja
- servicio_origen: SRV-OPE-003
- tipo: write
- objetivo: Actualizar el estado de una caja operativa respetando las transiciones permitidas y el control de versión.
- entidades: caja_operativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-011 — Consulta de caja
- servicio_origen: SRV-OPE-003
- tipo: read
- objetivo: Consultar el estado y los datos vigentes de una caja operativa.
- entidades: caja_operativa, instalacion, usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Movimientos de caja

### CU-OPE-012 — Registro de movimiento
- servicio_origen: SRV-OPE-004
- tipo: write
- objetivo: Registrar un movimiento de caja operativa asociado a una caja activa y, cuando corresponda, a un movimiento financiero.
- entidades: movimiento_caja, caja_operativa, movimiento_financiero
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-013 — Anulación de movimiento
- servicio_origen: SRV-OPE-004
- tipo: write
- objetivo: Anular un movimiento de caja existente respetando las reglas de anulabilidad y preservando trazabilidad.
- entidades: movimiento_caja, caja_operativa
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-014 — Consulta de movimientos
- servicio_origen: SRV-OPE-004
- tipo: read
- objetivo: Consultar movimientos de caja según estado, tipo, medio de pago o rango temporal.
- entidades: movimiento_caja, caja_operativa
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Cierre de caja

### CU-OPE-015 — Ejecución de cierre
- servicio_origen: SRV-OPE-005
- tipo: write
- objetivo: Ejecutar el cierre de una caja operativa, incluyendo las validaciones previas necesarias, consolidando movimientos y actualizando su estado final.
- entidades: cierre_caja, caja_operativa, movimiento_caja
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-OPE-016 — Consulta de cierre
- servicio_origen: SRV-OPE-005
- tipo: read
- objetivo: Consultar cierres de caja con sus totales, diferencias y observaciones.
- entidades: cierre_caja, caja_operativa
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## F. Consultas operativas

### CU-OPE-017 — Consulta operativa consolidada
- servicio_origen: SRV-OPE-006
- tipo: read
- objetivo: Consultar de forma consolidada sucursales, instalaciones, cajas, movimientos y cierres del dominio operativo.
- entidades: sucursal, instalacion, caja_operativa, movimiento_caja, cierre_caja
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-OPE-018 — Reportes operativos
- servicio_origen: SRV-OPE-006
- tipo: read
- objetivo: Obtener reportes operativos consolidados del dominio sin generar efectos persistentes.
- entidades: sucursal, instalacion, caja_operativa, movimiento_caja, cierre_caja
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Operativo.
- No reemplaza al CAT-CU maestro.
- Los casos aquí listados se usan como apoyo a implementación backend.
- Debe mantenerse alineado con los servicios SRV-OPE del dominio y con el modelo real del dominio operativo.
