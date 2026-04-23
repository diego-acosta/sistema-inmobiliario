# EST-COM - Estados del dominio Comercial

## Objetivo
Definir los estados posibles de las entidades del dominio comercial.

## Alcance
Incluye reservas, ventas, instrumentos, cesiones, escrituracion y rescisiones.

---

## A. Estados de reservas

### EST-COM-001 - Borrador
- codigo: borrador
- tipo: entidad
- aplica_a: reserva_venta, venta
- descripcion: la entidad fue creada pero aun no alcanzo un estado operativo consolidado.
- estado_inicial: si
- estado_final: no

### EST-COM-002 - Activa
- codigo: activa
- tipo: entidad
- aplica_a: reserva_venta, venta, cesion
- descripcion: la entidad se encuentra vigente y en curso dentro de su flujo comercial.
- estado_inicial: no
- estado_final: no

### EST-COM-003 - Confirmada
- codigo: confirmada
- tipo: entidad
- aplica_a: reserva_venta, venta
- descripcion: la entidad alcanzo validacion suficiente para continuar en el flujo comercial.
- estado_inicial: no
- estado_final: no

### EST-COM-004 - Cancelada
- codigo: cancelada
- tipo: entidad
- aplica_a: reserva_venta, venta
- descripcion: la entidad comercial fue cancelada y no debe continuar su ciclo normal.
- estado_inicial: no
- estado_final: si

### EST-COM-005 - Vencida
- codigo: vencida
- tipo: entidad
- aplica_a: reserva_venta
- descripcion: la reserva perdio vigencia por vencimiento temporal cuando el modelo lo contemple.
- estado_inicial: no
- estado_final: si
- observaciones: aplica cuando exista politica temporal de vencimiento de reserva.

## B. Estados de ventas

### EST-COM-006 - En proceso
- codigo: en_proceso
- tipo: entidad
- aplica_a: venta, escrituracion
- descripcion: la entidad se encuentra en ejecucion o avance dentro de un flujo comercial formalizado.
- estado_inicial: no
- estado_final: no

### EST-COM-007 - Finalizada
- codigo: finalizada
- tipo: entidad
- aplica_a: reserva_venta, venta
- descripcion: la entidad completo su ciclo comercial segun la politica del dominio.
- estado_inicial: no
- estado_final: si
- observaciones: para `reserva_venta`, aplica como cierre posterior a una conversion valida a `venta`; para `venta`, aplica cuando el flujo contemple cierre comercial explicito.

## C. Estados de instrumentos comerciales

### EST-COM-008 - Generado
- codigo: generado
- tipo: entidad
- aplica_a: instrumento_compraventa
- descripcion: el instrumento fue emitido o creado dentro del proceso comercial.
- estado_inicial: si
- estado_final: no

### EST-COM-009 - Vigente
- codigo: vigente
- tipo: entidad
- aplica_a: instrumento_compraventa
- descripcion: el instrumento se encuentra valido y con efectos dentro de su ciclo de vida.
- estado_inicial: no
- estado_final: no

### EST-COM-010 - Anulado
- codigo: anulado
- tipo: entidad
- aplica_a: instrumento_compraventa
- descripcion: el instrumento fue dejado sin efecto.
- estado_inicial: no
- estado_final: si

### EST-COM-011 - Pendiente
- codigo: pendiente
- tipo: entidad
- aplica_a: instrumento_compraventa, escrituracion
- descripcion: la entidad se encuentra pendiente de una accion o formalizacion posterior.
- estado_inicial: si
- estado_final: no

### EST-COM-012 - Firmado
- codigo: firmado
- tipo: entidad
- aplica_a: instrumento_compraventa
- descripcion: el instrumento alcanzo estado de firma o formalizacion equivalente.
- estado_inicial: no
- estado_final: no
- observaciones: aplica cuando el modelo diferencia explicitamente la firma del resto del ciclo del instrumento.

## D. Estados de cesiones

### EST-COM-013 - Registrada
- codigo: registrada
- tipo: entidad
- aplica_a: cesion, rescision_venta
- descripcion: la entidad fue registrada formalmente dentro del dominio comercial.
- estado_inicial: si
- estado_final: no

## E. Estados de escrituracion

### EST-COM-014 - Escriturada
- codigo: escriturada
- tipo: entidad
- aplica_a: escrituracion
- descripcion: la operacion alcanzo formalizacion por escrituracion.
- estado_inicial: no
- estado_final: si

## F. Estados de rescisiones comerciales

### EST-COM-015 - Efectiva
- codigo: efectiva
- tipo: entidad
- aplica_a: rescision_venta
- descripcion: la rescision produjo efecto sobre la operacion comercial alcanzada.
- estado_inicial: no
- estado_final: si

## G. Estados operativos transversales

### EST-COM-016 - Exito
- codigo: exito
- tipo: operativo
- aplica_a: procesos comerciales, operaciones write, evaluaciones
- descripcion: la operacion o proceso finalizo correctamente.
- estado_inicial: no
- estado_final: si

### EST-COM-017 - Error
- codigo: error
- tipo: operativo
- aplica_a: procesos comerciales, operaciones write, evaluaciones
- descripcion: la operacion o proceso finalizo con error y sin resultado valido.
- estado_inicial: no
- estado_final: si

### EST-COM-018 - Conflicto
- codigo: conflicto
- tipo: operativo
- aplica_a: procesos comerciales, operaciones write sincronizables
- descripcion: la operacion no pudo completarse por conflicto funcional o tecnico.
- estado_inicial: no
- estado_final: si

### EST-COM-019 - Rechazado
- codigo: rechazado
- tipo: operativo
- aplica_a: validaciones comerciales, operaciones write
- descripcion: la operacion fue rechazada por regla del dominio o validacion previa.
- estado_inicial: no
- estado_final: si

### EST-COM-020 - Bloqueado
- codigo: bloqueado
- tipo: operativo
- aplica_a: operaciones write sensibles del dominio comercial
- descripcion: la operacion no puede avanzar por bloqueo logico o restriccion operativa.
- estado_inicial: no
- estado_final: no

### EST-COM-021 - Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: validaciones comerciales, verificaciones de integridad
- descripcion: se detecto inconsistencia en el contexto o en la entidad evaluada.
- estado_inicial: no
- estado_final: no

### EST-COM-022 - Version valida
- codigo: version_valida
- tipo: operativo
- aplica_a: control de versionado comercial
- descripcion: la version esperada coincide con la version vigente.
- estado_inicial: no
- estado_final: no

### EST-COM-023 - Version invalida
- codigo: version_invalida
- tipo: operativo
- aplica_a: control de versionado comercial
- descripcion: la version esperada no coincide con la version vigente.
- estado_inicial: no
- estado_final: si

### EST-COM-024 - Ejecutado
- codigo: ejecutado
- tipo: operativo
- aplica_a: control de idempotencia comercial
- descripcion: la operacion ya fue ejecutada validamente con la identidad tecnica informada.
- estado_inicial: no
- estado_final: no

### EST-COM-025 - Duplicado
- codigo: duplicado
- tipo: operativo
- aplica_a: control de idempotencia comercial
- descripcion: se detecto repeticion de una operacion comercial ya registrada con el mismo contenido.
- estado_inicial: no
- estado_final: si

### EST-COM-026 - Duplicado con conflicto
- codigo: duplicado_con_conflicto
- tipo: operativo
- aplica_a: control de idempotencia comercial
- descripcion: se detecto reutilizacion de op_id con diferencias incompatibles respecto de la operacion original.
- estado_inicial: no
- estado_final: si

---

## Reglas de normalizacion

1. No duplicar estados con distinto nombre.
2. Consolidar estados comunes (activo, cancelado, etc.).
3. No mezclar estados con eventos.
4. Mantener estados genericos reutilizables.
5. Mantener numeracion `EST-COM-XXX`.

---

## Notas

- Este catalogo deriva del DEV-SRV y del DER comercial.
- No define logica, solo estados posibles.
- Debe mantenerse alineado con RN-COM.
- Sirve como base para validaciones y flujos.
