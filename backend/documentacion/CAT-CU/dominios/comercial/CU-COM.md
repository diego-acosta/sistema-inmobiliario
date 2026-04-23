# CU-COM — Casos de uso del dominio Comercial

## Objetivo
Definir los casos de uso comerciales del sistema.

## Alcance
Incluye clientes, operaciones comerciales, reservas e interacciones comerciales.

---

## A. Gestión de clientes

### CU-COM-001 — Alta de cliente
- tipo: write
- objetivo: Registrar un nuevo cliente dentro del circuito comercial.
- entidades: cliente
- criticidad: alta

### CU-COM-002 — Modificación de cliente
- tipo: write
- objetivo: Actualizar datos relevantes de un cliente existente.
- entidades: cliente
- criticidad: alta

### CU-COM-003 — Baja lógica de cliente
- tipo: write
- objetivo: Dar de baja lógica a un cliente preservando su trazabilidad comercial.
- entidades: cliente
- criticidad: alta

### CU-COM-004 — Consulta de cliente
- tipo: read
- objetivo: Consultar información operativa y comercial de un cliente.
- entidades: cliente
- criticidad: media

### CU-COM-005 — Consulta de clientes
- tipo: read
- objetivo: Listar y filtrar clientes según criterios comerciales.
- entidades: cliente
- criticidad: media

## B. Gestión de operaciones comerciales

### CU-COM-006 — Alta de operación comercial
- tipo: write
- objetivo: Registrar una nueva operación comercial de venta o alquiler en etapa comercial.
- entidades: operacion_comercial
- criticidad: crítica

### CU-COM-007 — Modificación de operación
- tipo: write
- objetivo: Actualizar datos relevantes de una operación comercial existente.
- entidades: operacion_comercial
- criticidad: alta

### CU-COM-008 — Cambio de estado de operación comercial
- tipo: write
- objetivo: Actualizar el estado del flujo comercial de una operación existente.
- entidades: operacion_comercial
- criticidad: alta

### CU-COM-009 — Cierre de operación comercial
- tipo: write
- objetivo: Cerrar una operación comercial al concluir su ciclo previo a contratación o derivación.
- entidades: operacion_comercial
- criticidad: alta

### CU-COM-010 — Cancelación de operación
- tipo: write
- objetivo: Cancelar una operación comercial preservando su trazabilidad.
- entidades: operacion_comercial
- criticidad: alta

### CU-COM-011 — Consulta de operación
- tipo: read
- objetivo: Consultar el detalle de una operación comercial.
- entidades: operacion_comercial
- criticidad: media

### CU-COM-012 — Consulta de operaciones
- tipo: read
- objetivo: Listar y filtrar operaciones comerciales según criterios operativos.
- entidades: operacion_comercial
- criticidad: media

## C. Reservas e intenciones comerciales

### CU-COM-013 — Generación de reserva
- tipo: write
- objetivo: Registrar una reserva o intención comercial dentro del flujo comercial previo a contratación, potencialmente asociada a una operación comercial.
- entidades: reserva_comercial
- criticidad: alta

### CU-COM-014 — Confirmación de reserva
- tipo: write
- objetivo: Confirmar una reserva comercial cuando se cumplen las condiciones del flujo comercial.
- entidades: reserva_comercial
- criticidad: alta

### CU-COM-015 — Cancelación de reserva
- tipo: write
- objetivo: Cancelar una reserva comercial manteniendo su trazabilidad.
- entidades: reserva_comercial
- criticidad: alta

### CU-COM-016 — Consulta de reservas
- tipo: read
- objetivo: Consultar y listar reservas comerciales según criterios administrativos o comerciales.
- entidades: reserva_comercial
- criticidad: media

## D. Seguimiento comercial

### CU-COM-017 — Registro de interacción con cliente
- tipo: write
- objetivo: Registrar una interacción comercial relevante con un cliente.
- entidades: cliente, interaccion_comercial
- criticidad: media

### CU-COM-018 — Consulta de historial comercial
- tipo: read
- objetivo: Consultar el historial de interacciones y evolución comercial de clientes, operaciones y reservas.
- entidades: interaccion_comercial, cliente, operacion_comercial, reserva_comercial
- criticidad: media

### CU-COM-019 — Consulta de pipeline comercial
- tipo: read
- objetivo: Consultar el estado consolidado del pipeline comercial a partir de operaciones comerciales, reservas, interacciones y estados del flujo comercial.
- entidades: operacion_comercial, reserva_comercial, interaccion_comercial
- criticidad: media

---

## Reglas

1. No duplicar casos.
2. No incluir lógica financiera.
3. No incluir contratos.
4. No incluir gestión de inmuebles.
5. Mantener separación clara con otros dominios.

---

## Notas

- Este dominio se estructura sobre clientes, operaciones y reservas.
- Una operación comercial representa una instancia concreta del proceso comercial.
- El dominio comercial no incluye una entidad CRM separada de oportunidad comercial salvo que el modelo la incorpore explícitamente en el futuro.
- Este dominio representa el flujo comercial previo al contrato.
- Es el origen de procesos locativos o de venta.
- No ejecuta obligaciones financieras.
- Puede originar procesos locativos o de venta, pero no los reemplaza.
- Debe mantenerse alineado con dominios locativo y financiero.
