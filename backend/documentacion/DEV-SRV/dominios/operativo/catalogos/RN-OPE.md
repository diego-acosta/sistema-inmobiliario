# RN-OPE — Reglas del dominio Operativo

## Objetivo
Definir reglas del dominio Operativo como apoyo a implementación backend.

## Alcance del dominio
Incluye sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consultas operativas consolidadas.

---

## A. Reglas de sucursales

### RN-OPE-001 — Trazabilidad de sucursal
- descripcion: toda alta, modificación o baja lógica de sucursal debe preservar trazabilidad operativa y organizativa.
- aplica_a: sucursal
- origen_principal: DEV-SRV

### RN-OPE-002 — Baja lógica sin destrucción de historial
- descripcion: la baja lógica de sucursal no debe destruir historial ni referencias operativas relevantes.
- aplica_a: sucursal
- origen_principal: DEV-SRV

### RN-OPE-003 — Consistencia organizativa de sucursal
- descripcion: los datos organizativos de la sucursal deben mantenerse consistentes y sin duplicidad indebida cuando el modelo lo requiera.
- aplica_a: sucursal
- origen_principal: SQL
- observaciones: la unicidad exacta depende del modelo real del dominio.

## B. Reglas de instalaciones

### RN-OPE-004 — Trazabilidad de instalación
- descripcion: toda alta, modificación o baja lógica de instalación debe preservar trazabilidad técnica y operativa.
- aplica_a: instalacion
- origen_principal: DEV-SRV

### RN-OPE-005 — Consistencia entre instalación y sucursal
- descripcion: una instalación debe mantener una vinculación consistente con la sucursal asociada.
- aplica_a: instalacion, sucursal
- origen_principal: DEV-SRV

### RN-OPE-006 — Baja lógica de instalación con preservación histórica
- descripcion: la baja lógica de instalación no debe destruir historial ni romper consistencia con la sucursal y sus referencias operativas.
- aplica_a: instalacion
- origen_principal: DEV-SRV

## C. Reglas de caja operativa

### RN-OPE-007 — Apertura de caja en contexto válido
- descripcion: la apertura de caja solo puede realizarse en un contexto operativo válido con instalación, sucursal y usuario consistentes.
- aplica_a: caja_operativa, instalacion, sucursal, usuario
- origen_principal: DEV-SRV

### RN-OPE-008 — Unicidad operativa de caja activa
- descripcion: no debe existir más de una caja operativa activa por instalación cuando el modelo operativo no lo permita.
- aplica_a: caja_operativa, instalacion
- origen_principal: DEV-SRV

### RN-OPE-009 — Transición válida de estado de caja
- descripcion: los cambios de estado de caja operativa deben respetar transiciones válidas y control de versión cuando corresponda.
- aplica_a: caja_operativa
- origen_principal: DEV-SRV

## D. Reglas de movimientos de caja

### RN-OPE-010 — Movimiento solo sobre caja válida
- descripcion: un movimiento de caja solo puede registrarse sobre una caja operativa válida para la operación solicitada.
- aplica_a: movimiento_caja, caja_operativa
- origen_principal: DEV-SRV

### RN-OPE-011 — Consistencia de montos y tipo de movimiento
- descripcion: los montos y el tipo de movimiento deben ser coherentes con el contexto operativo y con las validaciones del servicio.
- aplica_a: movimiento_caja
- origen_principal: DEV-SRV

### RN-OPE-012 — Anulación con preservación de trazabilidad
- descripcion: la anulación de un movimiento debe preservar trazabilidad y no eliminar indebidamente el registro original.
- aplica_a: movimiento_caja
- origen_principal: DEV-SRV

### RN-OPE-013 — Vinculación con financiero cuando corresponda
- descripcion: la vinculación de un movimiento de caja con movimiento financiero solo aplica cuando el servicio operativo así lo requiera.
- aplica_a: movimiento_caja, movimiento_financiero
- origen_principal: DEV-SRV
- observaciones: no traslada lógica financiera al dominio operativo.

## E. Reglas de cierre de caja

### RN-OPE-014 — Cierre solo con condiciones previas válidas
- descripcion: el cierre de caja solo puede ejecutarse si se cumplen las condiciones previas definidas para caja activa y movimientos consolidados.
- aplica_a: cierre_caja, caja_operativa, movimiento_caja
- origen_principal: DEV-SRV

### RN-OPE-015 — Consistencia de totales y diferencias
- descripcion: el cierre de caja debe preservar consistencia entre totales calculados, totales declarados y diferencias detectadas.
- aplica_a: cierre_caja
- origen_principal: DEV-SRV

### RN-OPE-016 — Cierre con preservación de historial
- descripcion: la ejecución del cierre no debe perder historial de movimientos, observaciones ni resultado operativo.
- aplica_a: cierre_caja, caja_operativa
- origen_principal: DEV-SRV

## F. Reglas de consultas operativas

### RN-OPE-017 — Consultas sin efectos persistentes
- descripcion: las consultas operativas no generan efectos persistentes ni alteran el estado del dominio.
- aplica_a: consultas operativas
- origen_principal: DEV-SRV

### RN-OPE-018 — Reportes sin alteración de estado
- descripcion: los reportes operativos deben consolidar información sin modificar sucursales, instalaciones, cajas, movimientos o cierres.
- aplica_a: consultas operativas
- origen_principal: DEV-SRV

### RN-OPE-019 — Consolidación respetando trazabilidad
- descripcion: la consulta operativa consolidada debe respetar la trazabilidad del dominio y la coherencia entre sus entidades.
- aplica_a: consultas operativas
- origen_principal: DEV-SRV

## Notas
- El catálogo deriva del DEV-SRV del dominio Operativo.
- No reemplaza al CAT-CU maestro.
- Debe mantenerse alineado con CU-OPE y con los servicios SRV-OPE reales del dominio.
- No debe contaminarse con semántica de workflow genérico ni con el dominio Técnico.
