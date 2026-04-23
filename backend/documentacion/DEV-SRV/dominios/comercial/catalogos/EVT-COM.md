# EVT-COM — Eventos del dominio Comercial

## Objetivo
Definir los eventos observables relevantes del dominio comercial.

## Alcance
Incluye reservas, ventas, instrumentos, cesiones, escrituración y rescisiones.

---

## A. Eventos de reservas

### EVT-COM-001 — Reserva creada
- codigo: reserva_creada
- descripcion: se registró una nueva reserva comercial.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-002 — Reserva modificada
- codigo: reserva_modificada
- descripcion: se actualizaron datos de una reserva comercial.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-003 — Reserva confirmada
- codigo: reserva_confirmada
- descripcion: una reserva pasó a estado confirmado dentro del flujo comercial.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-004 — Reserva cancelada
- codigo: reserva_cancelada
- descripcion: una reserva comercial fue cancelada.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-005 — Objeto inmobiliario asociado a reserva
- codigo: objeto_inmobiliario_asociado_a_reserva
- descripcion: se vinculó un objeto inmobiliario a una reserva comercial.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-006 — Objeto inmobiliario desasociado de reserva
- codigo: objeto_inmobiliario_desasociado_de_reserva
- descripcion: se desvinculó un objeto inmobiliario de una reserva comercial.
- origen_principal: SRV-COM-001
- entidad_principal: reserva_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## B. Eventos de ventas

### EVT-COM-007 — Venta creada
- codigo: venta_creada
- descripcion: se registró una nueva operación de venta.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-008 — Venta modificada
- codigo: venta_modificada
- descripcion: se actualizaron datos de una operación de venta.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-009 — Venta confirmada
- codigo: venta_confirmada
- descripcion: una venta alcanzó estado confirmado dentro del flujo comercial.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-010 — Venta cancelada
- codigo: venta_cancelada
- descripcion: una operación de venta fue cancelada.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-011 — Objeto inmobiliario asociado a venta
- codigo: objeto_inmobiliario_asociado_a_venta
- descripcion: se vinculó un objeto inmobiliario a una venta.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-012 — Objeto inmobiliario desasociado de venta
- codigo: objeto_inmobiliario_desasociado_de_venta
- descripcion: se desvinculó un objeto inmobiliario de una venta cuando el proceso lo permitió.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-013 — Comprador asociado a venta
- codigo: comprador_asociado_a_venta
- descripcion: se vinculó el sujeto comprador a la operación de venta.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-014 — Condiciones comerciales definidas
- codigo: condiciones_comerciales_definidas
- descripcion: se definieron condiciones comerciales asociadas a una operación de venta.
- origen_principal: SRV-COM-003
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-015 — Condiciones comerciales modificadas
- codigo: condiciones_comerciales_modificadas
- descripcion: se modificaron condiciones comerciales de una operación de venta.
- origen_principal: SRV-COM-003
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-016 — Condiciones financieras definidas
- codigo: condiciones_financieras_definidas
- descripcion: se definieron condiciones financieras derivadas de la operación comercial.
- origen_principal: SRV-COM-003
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí
- observaciones: el efecto financiero se materializa en su dominio; aquí solo se registra el hecho comercial origen.

### EVT-COM-017 — Condiciones financieras confirmadas
- codigo: condiciones_financieras_confirmadas
- descripcion: se confirmó el conjunto de condiciones financieras derivadas de la operación comercial.
- origen_principal: SRV-COM-003
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí
- observaciones: no reemplaza eventos financieros posteriores.

### EVT-COM-018 — Relación generadora generada desde venta
- codigo: relacion_generadora_generada_desde_venta
- descripcion: la venta generó una relación comercial apta para integración con el dominio financiero.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí
- observaciones: el evento financiero definitivo pertenece a su dominio de origen.

### EVT-COM-019 — Relación generadora activada desde venta
- codigo: relacion_generadora_activada_desde_venta
- descripcion: la relación comercial derivada de la venta quedó activada para integración con procesos posteriores.
- origen_principal: SRV-COM-002
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: cuando_corresponda
- genera_trazabilidad: sí
- observaciones: no reemplaza eventos propios del dominio financiero.

## C. Eventos de instrumentos comerciales

### EVT-COM-020 — Instrumento de compraventa creado
- codigo: instrumento_compraventa_creado
- descripcion: se registró un nuevo instrumento comercial de compraventa.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_compraventa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-021 — Instrumento de compraventa modificado
- codigo: instrumento_compraventa_modificado
- descripcion: se actualizaron datos de un instrumento de compraventa.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_compraventa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-022 — Instrumento de compraventa anulado
- codigo: instrumento_compraventa_anulado
- descripcion: un instrumento comercial fue anulado.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_compraventa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-023 — Instrumento asociado a operación
- codigo: instrumento_asociado_a_operacion
- descripcion: se vinculó un instrumento comercial a una operación base.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_compraventa
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-024 — Objeto inmobiliario asociado a instrumento
- codigo: objeto_inmobiliario_asociado_a_instrumento
- descripcion: se vinculó un objeto inmobiliario a un instrumento comercial.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_objeto_inmobiliario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-025 — Objeto inmobiliario desasociado de instrumento
- codigo: objeto_inmobiliario_desasociado_de_instrumento
- descripcion: se desvinculó un objeto inmobiliario de un instrumento comercial cuando el proceso lo permitió.
- origen_principal: SRV-COM-004
- entidad_principal: instrumento_objeto_inmobiliario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## D. Eventos de cesiones

### EVT-COM-026 — Cesión registrada
- codigo: cesion_registrada
- descripcion: se registró una cesión sobre una operación comercial.
- origen_principal: SRV-COM-005
- entidad_principal: cesion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-027 — Cesión modificada
- codigo: cesion_modificada
- descripcion: se actualizaron datos de una cesión comercial.
- origen_principal: SRV-COM-005
- entidad_principal: cesion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-028 — Cesión anulada
- codigo: cesion_anulada
- descripcion: una cesión comercial fue anulada.
- origen_principal: SRV-COM-005
- entidad_principal: cesion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-029 — Cesionario asociado
- codigo: cesionario_asociado
- descripcion: se vinculó el nuevo sujeto cesionario a la operación cedida.
- origen_principal: SRV-COM-005
- entidad_principal: cesion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-030 — Titularidad comercial transferida
- codigo: titularidad_comercial_transferida
- descripcion: la posición comercial del sujeto anterior fue transferida al cesionario.
- origen_principal: SRV-COM-005
- entidad_principal: cesion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## E. Eventos de escrituración

### EVT-COM-031 — Escrituración registrada
- codigo: escrituracion_registrada
- descripcion: se registró una escrituración vinculada a una operación comercial.
- origen_principal: SRV-COM-006
- entidad_principal: escrituracion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-032 — Escrituración modificada
- codigo: escrituracion_modificada
- descripcion: se actualizaron datos de una escrituración.
- origen_principal: SRV-COM-006
- entidad_principal: escrituracion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-033 — Escrituración anulada
- codigo: escrituracion_anulada
- descripcion: una escrituración fue anulada.
- origen_principal: SRV-COM-006
- entidad_principal: escrituracion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-034 — Operación escriturada
- codigo: operacion_escriturada
- descripcion: la operación comercial alcanzó el hito de escrituración.
- origen_principal: SRV-COM-006
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## F. Eventos de rescisiones comerciales

### EVT-COM-035 — Rescisión de venta registrada
- codigo: rescision_venta_registrada
- descripcion: se registró una rescisión sobre una venta.
- origen_principal: SRV-COM-005
- entidad_principal: rescision_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-036 — Rescisión de venta modificada
- codigo: rescision_venta_modificada
- descripcion: se actualizaron datos de una rescisión comercial.
- origen_principal: SRV-COM-005
- entidad_principal: rescision_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-037 — Rescisión de venta anulada
- codigo: rescision_venta_anulada
- descripcion: una rescisión comercial fue anulada.
- origen_principal: SRV-COM-005
- entidad_principal: rescision_venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

### EVT-COM-038 — Operación comercial rescindida
- codigo: operacion_comercial_rescindida
- descripcion: la operación comercial quedó rescindida y fuera de su flujo ordinario.
- origen_principal: SRV-COM-005
- entidad_principal: venta
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad: sí

## G. Notas de compatibilidad transversal

- los writes comerciales sincronizables generan trazabilidad, op_id y outbox según CORE-EF
- los eventos comerciales no reemplazan los eventos financieros
- los eventos comerciales pueden disparar efectos integrados en:
  - inmobiliario (disponibilidad)
  - financiero (relación generadora)
  - documental (instrumentos / documentación)
- esos efectos integrados no deben duplicarse como eventos comerciales si pertenecen claramente a otro dominio; solo referenciarlos en observaciones cuando corresponda

---

## Notas

- Este catálogo deriva del DEV-SRV del dominio comercial y del DER comercial/global.
- No reemplaza a la auditoría administrativa ni a los eventos técnicos de sincronización.
- Debe mantenerse alineado con CU-COM, RN-COM y con los servicios SRV-COM del dominio.
- Sirve como base para trazabilidad, outbox y observabilidad del dominio comercial.
