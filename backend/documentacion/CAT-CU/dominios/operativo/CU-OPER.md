# CU-OPER — Casos de uso del dominio Operativo

## Objetivo
Definir los casos de uso del dominio Operativo.

## Alcance
Incluye sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consultas operativas del sistema.

---

## A. Sucursales

### CU-OPER-001 — Alta de sucursal
- tipo: write
- objetivo: Registrar una nueva sucursal dentro del dominio operativo.
- entidades: sucursal
- criticidad: alta

### CU-OPER-002 — Modificación de sucursal
- tipo: write
- objetivo: Actualizar datos relevantes de una sucursal existente.
- entidades: sucursal
- criticidad: alta

### CU-OPER-003 — Baja lógica de sucursal
- tipo: write
- objetivo: Aplicar baja lógica sobre una sucursal preservando historial y trazabilidad.
- entidades: sucursal
- criticidad: alta

### CU-OPER-004 — Consulta de sucursal
- tipo: read
- objetivo: Consultar sucursales y sus datos operativos vigentes.
- entidades: sucursal
- criticidad: media

## B. Instalaciones

### CU-OPER-005 — Alta de instalación
- tipo: write
- objetivo: Registrar una nueva instalación vinculada a una sucursal.
- entidades: instalacion, sucursal
- criticidad: alta

### CU-OPER-006 — Modificación de instalación
- tipo: write
- objetivo: Actualizar datos relevantes de una instalación existente.
- entidades: instalacion, sucursal
- criticidad: alta

### CU-OPER-007 — Baja lógica de instalación
- tipo: write
- objetivo: Aplicar baja lógica sobre una instalación preservando historial y consistencia operativa.
- entidades: instalacion, sucursal
- criticidad: alta

### CU-OPER-008 — Consulta de instalación
- tipo: read
- objetivo: Consultar instalaciones y su relación con la sucursal asociada.
- entidades: instalacion, sucursal
- criticidad: media

## C. Caja operativa

### CU-OPER-009 — Apertura de caja
- tipo: write
- objetivo: Iniciar una nueva caja operativa en una instalación habilitada.
- entidades: caja_operativa, instalacion, sucursal, usuario
- criticidad: alta

### CU-OPER-010 — Cambio de estado de caja
- tipo: write
- objetivo: Actualizar el estado de una caja operativa según las transiciones permitidas.
- entidades: caja_operativa
- criticidad: alta

### CU-OPER-011 — Consulta de caja
- tipo: read
- objetivo: Consultar el estado y los datos vigentes de una caja operativa.
- entidades: caja_operativa, instalacion, usuario
- criticidad: media

## D. Movimientos de caja

### CU-OPER-012 — Registro de movimiento
- tipo: write
- objetivo: Registrar un movimiento de caja operativa asociado a una caja válida.
- entidades: movimiento_caja, caja_operativa, movimiento_financiero
- criticidad: alta

### CU-OPER-013 — Anulación de movimiento
- tipo: write
- objetivo: Anular un movimiento de caja existente preservando su trazabilidad.
- entidades: movimiento_caja, caja_operativa
- criticidad: alta

### CU-OPER-014 — Consulta de movimientos
- tipo: read
- objetivo: Consultar movimientos de caja según criterios operativos del dominio.
- entidades: movimiento_caja, caja_operativa
- criticidad: media

## E. Cierre de caja

### CU-OPER-015 — Ejecución de cierre
- tipo: write
- objetivo: Ejecutar el cierre de una caja operativa consolidando sus movimientos.
- entidades: cierre_caja, caja_operativa, movimiento_caja
- criticidad: crítica

### CU-OPER-016 — Validación de cierre
- tipo: write
- objetivo: Validar las condiciones previas necesarias para el cierre de caja.
- entidades: cierre_caja, caja_operativa, movimiento_caja
- criticidad: alta

### CU-OPER-017 — Consulta de cierre
- tipo: read
- objetivo: Consultar cierres de caja con sus resultados operativos.
- entidades: cierre_caja, caja_operativa
- criticidad: media

## F. Consultas operativas

### CU-OPER-018 — Consulta operativa consolidada
- tipo: read
- objetivo: Consultar de forma consolidada sucursales, instalaciones, cajas, movimientos y cierres del dominio operativo.
- entidades: sucursal, instalacion, caja_operativa, movimiento_caja, cierre_caja
- criticidad: media

### CU-OPER-019 — Reportes operativos
- tipo: read
- objetivo: Obtener reportes operativos del dominio sin generar efectos persistentes.
- entidades: sucursal, instalacion, caja_operativa, movimiento_caja, cierre_caja
- criticidad: media

---

## Reglas

1. No definir procesos, tareas, colas ni workflow genérico como parte del dominio Operativo.
2. No reemplazar la lógica financiera sobre obligaciones, pagos o imputaciones.
3. No sustituir la lógica administrativa de usuarios y permisos.
4. Mantener el foco del dominio en sucursales, instalaciones, caja operativa, movimientos, cierres y consultas operativas.
5. Mantener alineación con los servicios reales `SRV-OPE-001` a `SRV-OPE-006`.

---

## Notas

- Este catálogo debe interpretarse en conjunto con el DEV-SRV del dominio Operativo.
- No reemplaza la documentación de implementación backend.
- Su contenido debe mantenerse alineado con `CU-OPE` y con los servicios reales del dominio.
