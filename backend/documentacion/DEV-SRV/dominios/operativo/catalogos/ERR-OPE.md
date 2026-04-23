# ERR-OPE — Errores del dominio Operativo

## Objetivo
Definir errores del dominio Operativo como apoyo a implementación backend.

## Alcance del dominio
Incluye sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja, consultas operativas y errores transversales del dominio.

---

## A. Errores de sucursales

### ERR-OPE-001 — sucursal_no_encontrada
- codigo: sucursal_no_encontrada
- descripcion: la sucursal indicada no existe o no está disponible.
- tipo: funcional
- aplica_a: sucursal
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-002 — sucursal_inactiva
- codigo: sucursal_inactiva
- descripcion: la sucursal se encuentra inactiva y no admite la operación solicitada.
- tipo: funcional
- aplica_a: sucursal
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-003 — sucursal_duplicada
- codigo: sucursal_duplicada
- descripcion: ya existe una sucursal en conflicto con las reglas de unicidad del dominio.
- tipo: integridad
- aplica_a: sucursal
- origen: SQL
- es_reintento_valido: no
- observaciones: aplica cuando el modelo real impone restricción de unicidad.

## B. Errores de instalaciones

### ERR-OPE-004 — instalacion_no_encontrada
- codigo: instalacion_no_encontrada
- descripcion: la instalación indicada no existe o no está disponible.
- tipo: funcional
- aplica_a: instalacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-005 — instalacion_inactiva
- codigo: instalacion_inactiva
- descripcion: la instalación se encuentra inactiva y no admite la operación solicitada.
- tipo: funcional
- aplica_a: instalacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-006 — instalacion_duplicada
- codigo: instalacion_duplicada
- descripcion: ya existe una instalación en conflicto con las reglas de unicidad del dominio.
- tipo: integridad
- aplica_a: instalacion
- origen: SQL
- es_reintento_valido: no
- observaciones: aplica cuando el modelo real impone restricción de unicidad.

### ERR-OPE-007 — instalacion_sin_sucursal_valida
- codigo: instalacion_sin_sucursal_valida
- descripcion: la instalación no puede operar porque la sucursal asociada no es válida para la operación solicitada.
- tipo: validacion
- aplica_a: instalacion, sucursal
- origen: DEV-SRV
- es_reintento_valido: no

## C. Errores de caja operativa

### ERR-OPE-008 — caja_operativa_no_encontrada
- codigo: caja_operativa_no_encontrada
- descripcion: la caja operativa indicada no existe o no está disponible.
- tipo: funcional
- aplica_a: caja_operativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-009 — caja_operativa_inactiva
- codigo: caja_operativa_inactiva
- descripcion: la caja operativa se encuentra inactiva y no admite la operación solicitada.
- tipo: funcional
- aplica_a: caja_operativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-010 — estado_caja_invalido
- codigo: estado_caja_invalido
- descripcion: el estado actual de la caja no permite la transición u operación requerida.
- tipo: validacion
- aplica_a: caja_operativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-011 — apertura_caja_invalida
- codigo: apertura_caja_invalida
- descripcion: no es válido abrir la caja en el contexto operativo informado.
- tipo: validacion
- aplica_a: caja_operativa, instalacion, sucursal, usuario
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de movimientos de caja

### ERR-OPE-012 — movimiento_caja_no_encontrado
- codigo: movimiento_caja_no_encontrado
- descripcion: el movimiento de caja indicado no existe o no está disponible.
- tipo: funcional
- aplica_a: movimiento_caja
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-013 — movimiento_caja_invalido
- codigo: movimiento_caja_invalido
- descripcion: el movimiento de caja no cumple las validaciones operativas requeridas.
- tipo: validacion
- aplica_a: movimiento_caja
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-014 — movimiento_caja_anulado
- codigo: movimiento_caja_anulado
- descripcion: el movimiento de caja ya se encuentra anulado y no admite la operación solicitada.
- tipo: funcional
- aplica_a: movimiento_caja
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-015 — anulacion_movimiento_invalida
- codigo: anulacion_movimiento_invalida
- descripcion: no es válida la anulación del movimiento en el contexto operativo actual.
- tipo: validacion
- aplica_a: movimiento_caja
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de cierre de caja

### ERR-OPE-016 — cierre_caja_no_encontrado
- codigo: cierre_caja_no_encontrado
- descripcion: el cierre de caja indicado no existe o no está disponible.
- tipo: funcional
- aplica_a: cierre_caja
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-017 — cierre_caja_invalido
- codigo: cierre_caja_invalido
- descripcion: el cierre de caja no cumple las condiciones operativas requeridas.
- tipo: validacion
- aplica_a: cierre_caja, caja_operativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-018 — cierre_caja_inconsistente
- codigo: cierre_caja_inconsistente
- descripcion: el cierre de caja presenta inconsistencias entre movimientos, totales o estado resultante.
- tipo: integridad
- aplica_a: cierre_caja, movimiento_caja, caja_operativa
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores de consultas operativas

### ERR-OPE-019 — criterio_consulta_operativa_invalido
- codigo: criterio_consulta_operativa_invalido
- descripcion: los criterios de consulta operativa informados no son válidos.
- tipo: validacion
- aplica_a: consultas operativas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-OPE-020 — informacion_operativa_no_disponible
- codigo: informacion_operativa_no_disponible
- descripcion: no se encuentra disponible la información operativa solicitada para el contexto indicado.
- tipo: funcional
- aplica_a: consultas operativas
- origen: DEV-SRV
- es_reintento_valido: no

## G. Errores transversales del dominio operativo

### ERR-OPE-021 — version_esperada_invalida
- codigo: version_esperada_invalida
- descripcion: la versión esperada informada no coincide con la versión vigente del registro operativo.
- tipo: concurrencia
- aplica_a: sucursal, instalacion, caja_operativa, movimiento_caja, cierre_caja
- origen: CORE-EF
- es_reintento_valido: no

### ERR-OPE-022 — op_id_duplicado
- codigo: op_id_duplicado
- descripcion: la operación ya fue registrada con el mismo op_id y mismo contenido.
- tipo: concurrencia
- aplica_a: dominio_operativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-OPE-023 — op_id_duplicado_con_payload_distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el op_id ya existe asociado a un contenido distinto y genera conflicto técnico-operativo.
- tipo: concurrencia
- aplica_a: dominio_operativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-OPE-024 — conflicto_concurrencia
- codigo: conflicto_concurrencia
- descripcion: se detectó un conflicto de concurrencia incompatible con la operación operativa solicitada.
- tipo: concurrencia
- aplica_a: dominio_operativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-OPE-025 — integridad_operativa_invalida
- codigo: integridad_operativa_invalida
- descripcion: existe una inconsistencia de integridad entre entidades o estados del dominio operativo.
- tipo: integridad
- aplica_a: dominio_operativo
- origen: DEV-SRV
- es_reintento_valido: no

## Notas
- El catálogo deriva del DEV-SRV del dominio Operativo.
- No reemplaza al CAT-CU maestro.
- Debe mantenerse alineado con CU-OPE y con los servicios SRV-OPE reales del dominio.
- No debe contaminarse con semántica de workflow genérico ni con el dominio Técnico.
