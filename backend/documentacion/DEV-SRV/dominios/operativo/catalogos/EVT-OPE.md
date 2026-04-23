# EVT-OPE — Eventos del dominio Operativo

## Objetivo
Definir eventos observables del dominio Operativo como apoyo a implementación backend y trazabilidad.

## Alcance del dominio
Incluye eventos de sucursales, instalaciones, caja operativa, movimientos de caja y cierre de caja.

---

## A. Eventos de sucursales

### EVT-OPE-001 — Sucursal creada
- codigo: sucursal_creada
- descripcion: se registró una nueva sucursal dentro del dominio operativo.
- origen_principal: SRV-OPE-001
- entidad_principal: sucursal
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-002 — Sucursal modificada
- codigo: sucursal_modificada
- descripcion: se modificaron datos de una sucursal existente.
- origen_principal: SRV-OPE-001
- entidad_principal: sucursal
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-003 — Sucursal dada de baja lógica
- codigo: sucursal_dada_de_baja_logica
- descripcion: se aplicó baja lógica sobre una sucursal preservando trazabilidad.
- origen_principal: SRV-OPE-001
- entidad_principal: sucursal
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de instalaciones

### EVT-OPE-004 — Instalación creada
- codigo: instalacion_creada
- descripcion: se registró una nueva instalación vinculada a una sucursal.
- origen_principal: SRV-OPE-002
- entidad_principal: instalacion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-005 — Instalación modificada
- codigo: instalacion_modificada
- descripcion: se modificaron datos de una instalación existente.
- origen_principal: SRV-OPE-002
- entidad_principal: instalacion
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-006 — Instalación dada de baja lógica
- codigo: instalacion_dada_de_baja_logica
- descripcion: se aplicó baja lógica sobre una instalación preservando su historial operativo.
- origen_principal: SRV-OPE-002
- entidad_principal: instalacion
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## C. Eventos de caja operativa

### EVT-OPE-007 — Caja operativa abierta
- codigo: caja_operativa_abierta
- descripcion: se abrió una nueva caja operativa en un contexto válido de instalación y sucursal.
- origen_principal: SRV-OPE-003
- entidad_principal: caja_operativa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-008 — Estado de caja cambiado
- codigo: estado_caja_cambiado
- descripcion: cambió el estado de una caja operativa dentro de las transiciones permitidas.
- origen_principal: SRV-OPE-003
- entidad_principal: caja_operativa
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## D. Eventos de movimientos de caja

### EVT-OPE-009 — Movimiento de caja registrado
- codigo: movimiento_caja_registrado
- descripcion: se registró un nuevo movimiento sobre una caja operativa válida.
- origen_principal: SRV-OPE-004
- entidad_principal: movimiento_caja
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-OPE-010 — Movimiento de caja anulado
- codigo: movimiento_caja_anulado
- descripcion: se anuló un movimiento de caja preservando la trazabilidad del registro original.
- origen_principal: SRV-OPE-004
- entidad_principal: movimiento_caja
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad: sí

## E. Eventos de cierre de caja

### EVT-OPE-011 — Cierre de caja ejecutado
- codigo: cierre_caja_ejecutado
- descripcion: se ejecutó un cierre de caja con consolidación de movimientos y actualización de estado resultante.
- origen_principal: SRV-OPE-005
- entidad_principal: cierre_caja
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## F. Notas de compatibilidad transversal

- El dominio Operativo gestiona sucursales, instalaciones, caja, movimientos y cierres, y no reemplaza dominios funcionales ajenos.
- Los eventos operativos pueden ser consumidos por auditoría, financiero o reportes, sin duplicar eventos propios de otros dominios.
- Los writes sincronizables del dominio operativo deben respetar op_id, versionado y trazabilidad según CORE-EF.
- Los eventos operativos no deben contaminarse con semántica de workflow genérico ni con el dominio Técnico.

## Notas
- El catálogo deriva del DEV-SRV del dominio Operativo.
- No reemplaza al CAT-CU maestro.
- Debe mantenerse alineado con CU-OPE y con los servicios SRV-OPE reales del dominio.
- No debe contaminarse con semántica de workflow genérico ni con el dominio Técnico.
