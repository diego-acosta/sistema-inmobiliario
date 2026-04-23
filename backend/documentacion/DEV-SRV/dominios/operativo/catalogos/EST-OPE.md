# EST-OPE — Estados del dominio Operativo

## Objetivo
Definir estados del dominio Operativo como apoyo a implementación backend y consistencia del dominio.

## Alcance del dominio
Incluye estados de sucursales, instalaciones, caja operativa, movimientos de caja y cierre de caja.

---

## A. Estados de sucursales

### EST-OPE-001 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: sucursal
- descripcion: la sucursal se encuentra vigente y operativa.
- estado_inicial: sí
- estado_final: no

### EST-OPE-002 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: sucursal
- descripcion: la sucursal no se encuentra operativa para nuevas acciones del dominio.
- estado_inicial: no
- estado_final: no

### EST-OPE-003 — Dada de baja
- codigo: dada_de_baja
- tipo: entidad
- aplica_a: sucursal
- descripcion: la sucursal fue dada de baja lógica preservando historial.
- estado_inicial: no
- estado_final: sí

## B. Estados de instalaciones

### EST-OPE-004 — Activa
- codigo: activa
- tipo: entidad
- aplica_a: instalacion
- descripcion: la instalación se encuentra vigente y disponible para operación.
- estado_inicial: sí
- estado_final: no

### EST-OPE-005 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: instalacion
- descripcion: la instalación no se encuentra operativa para nuevas acciones del dominio.
- estado_inicial: no
- estado_final: no

### EST-OPE-006 — Dada de baja
- codigo: dada_de_baja
- tipo: entidad
- aplica_a: instalacion
- descripcion: la instalación fue dada de baja lógica preservando historial.
- estado_inicial: no
- estado_final: sí

## C. Estados de caja operativa

### EST-OPE-007 — Abierta
- codigo: abierta
- tipo: entidad
- aplica_a: caja_operativa
- descripcion: la caja operativa se encuentra abierta y habilitada para registrar movimientos.
- estado_inicial: sí
- estado_final: no

### EST-OPE-008 — Cerrada
- codigo: cerrada
- tipo: entidad
- aplica_a: caja_operativa
- descripcion: la caja operativa finalizó su vigencia mediante cierre.
- estado_inicial: no
- estado_final: sí

### EST-OPE-009 — Inactiva
- codigo: inactiva
- tipo: entidad
- aplica_a: caja_operativa
- descripcion: la caja operativa no se encuentra habilitada para operación.
- estado_inicial: no
- estado_final: no

### EST-OPE-010 — Bloqueada
- codigo: bloqueada
- tipo: entidad
- aplica_a: caja_operativa
- descripcion: la caja operativa se encuentra temporalmente bloqueada para nuevas acciones.
- estado_inicial: no
- estado_final: no
- observaciones: aplica cuando el servicio o el modelo operativo contemplan restricción temporal de uso.

## D. Estados de movimientos de caja

### EST-OPE-011 — Registrado
- codigo: registrado
- tipo: entidad
- aplica_a: movimiento_caja
- descripcion: el movimiento de caja fue registrado correctamente.
- estado_inicial: sí
- estado_final: no

### EST-OPE-012 — Anulado
- codigo: anulado
- tipo: entidad
- aplica_a: movimiento_caja
- descripcion: el movimiento de caja fue anulado preservando trazabilidad.
- estado_inicial: no
- estado_final: sí

## E. Estados de cierre de caja

### EST-OPE-013 — Ejecutado
- codigo: ejecutado
- tipo: entidad
- aplica_a: cierre_caja
- descripcion: el cierre de caja fue ejecutado y consolidó el resultado operativo.
- estado_inicial: no
- estado_final: sí

### EST-OPE-014 — Inconsistente
- codigo: inconsistente
- tipo: entidad
- aplica_a: cierre_caja
- descripcion: el cierre de caja fue registrado pero presenta inconsistencias que afectan su validez operativa.
- estado_inicial: no
- estado_final: sí

## Notas
- El catálogo deriva del DEV-SRV del dominio Operativo.
- No reemplaza al CAT-CU maestro.
- Debe mantenerse alineado con CU-OPE y con los servicios SRV-OPE reales del dominio.
- No debe contaminarse con semántica de workflow genérico ni con el dominio Técnico.
