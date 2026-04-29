# CU-FIN — Casos de uso del dominio Financiero

## Objetivo
Definir los casos de uso financieros del sistema.

## Alcance
Incluye generación de obligaciones, imputaciones, ajustes y consultas de estado financiero.

---

## A. Relaciones generadoras

### CU-FIN-001 — Alta de relación generadora
- tipo: write
- objetivo: Registrar una nueva relación generadora dentro del circuito financiero.
- entidades: relacion_generadora
- criticidad: alta

### CU-FIN-002 — Modificación de relación generadora
- tipo: write
- objetivo: Actualizar una relación generadora mientras se encuentre en un estado compatible con edición.
- entidades: relacion_generadora
- criticidad: alta

### CU-FIN-003 — Activación de relación generadora
- tipo: write
- objetivo: Activar una relación generadora para habilitar la producción de efectos financieros.
- entidades: relacion_generadora
- criticidad: crítica

### CU-FIN-004 — Cancelación de relación generadora
- tipo: write
- objetivo: Cancelar una relación generadora preservando su trazabilidad histórica.
- entidades: relacion_generadora
- criticidad: alta

### CU-FIN-005 — Finalización de relación generadora
- tipo: write
- objetivo: Finalizar una relación generadora al completar su ciclo financiero sin pendientes incompatibles.
- entidades: relacion_generadora
- criticidad: alta

## B. Generación de obligaciones

### CU-FIN-006 — Generación de obligación
- tipo: write
- objetivo: Generar una obligación financiera individual a partir de una relación generadora válida.
- entidades: relacion_generadora, obligacion_financiera, composicion_obligacion, concepto_financiero
- criticidad: crítica

### CU-FIN-007 — Generación masiva de obligaciones
- tipo: write
- objetivo: Generar múltiples obligaciones financieras dentro de un mismo proceso de emisión o exigibilidad.
- entidades: relacion_generadora, obligacion_financiera, composicion_obligacion, concepto_financiero
- criticidad: crítica

### CU-FIN-008 — Reversión de generación de obligación
- tipo: write
- objetivo: Revertir la generación de una obligación cuando el circuito financiero lo permita.
- entidades: obligacion_financiera, relacion_generadora
- criticidad: crítica

## C. Imputación financiera

### CU-FIN-009 — Registro de débito financiero
- tipo: write
- objetivo: Registrar un débito financiero dentro de la cuenta o circuito correspondiente, dentro del modelo financiero del sistema.
- entidades: movimiento_financiero
- criticidad: crítica

### CU-FIN-010 — Registro de crédito financiero
- tipo: write
- objetivo: Registrar un crédito financiero disponible para aplicación o compensación, dentro del modelo financiero del sistema.
- entidades: movimiento_financiero
- criticidad: crítica

### CU-FIN-011 — Imputación de pago
- tipo: write
- objetivo: Aplicar un pago o crédito sobre una o más obligaciones financieras.
- entidades: movimiento_financiero, aplicacion_financiera, obligacion_financiera
- criticidad: crítica

### CU-FIN-012 — Reversión de imputación
- tipo: write
- objetivo: Revertir una imputación financiera previamente aplicada.
- entidades: aplicacion_financiera, movimiento_financiero, obligacion_financiera
- criticidad: crítica

## D. Ajustes financieros

### CU-FIN-013 — Registro de ajuste positivo
- tipo: write
- objetivo: Registrar un ajuste financiero incremental sobre una obligación o saldo.
- entidades: ajuste_financiero, obligacion_financiera
- criticidad: alta

### CU-FIN-014 — Registro de ajuste negativo
- tipo: write
- objetivo: Registrar un ajuste financiero reductor sobre una obligación o saldo.
- entidades: ajuste_financiero, obligacion_financiera
- criticidad: alta

## E. Cancelaciones

### CU-FIN-015 — Cancelación de obligación
- tipo: write
- objetivo: Cancelar una obligación financiera al extinguirse completamente su saldo exigible.
- entidades: obligacion_financiera, composicion_obligacion, concepto_financiero
- criticidad: crítica

### CU-FIN-016 — Regularización de deuda
- tipo: write
- objetivo: Registrar una regularización financiera sobre deuda existente según reglas del dominio, sin alterar indebidamente la trazabilidad original.
- entidades: obligacion_financiera, ajuste_financiero, aplicacion_financiera
- criticidad: crítica

## F. Consultas financieras

### CU-FIN-017 — Consulta de obligación
- tipo: read
- objetivo: Consultar el detalle financiero de una obligación determinada.
- entidades: obligacion_financiera
- criticidad: media

### CU-FIN-018 — Consulta de obligaciones
- tipo: read
- objetivo: Listar y filtrar obligaciones financieras según criterios operativos.
- entidades: obligacion_financiera
- criticidad: media

### CU-FIN-019 — Consulta de estado de deuda
- tipo: read
- objetivo: Consultar el estado de deuda de una relación, sujeto o universo financiero.
- entidades: obligacion_financiera, relacion_generadora
- criticidad: media

### CU-FIN-020 — Consulta de movimientos financieros
- tipo: read
- objetivo: Consultar débitos, créditos e imputaciones registradas en el dominio financiero.
- entidades: movimiento_financiero, aplicacion_financiera
- criticidad: media

### CU-FIN-021 — Consulta de historial financiero
- tipo: read
- objetivo: Consultar la evolución histórica de obligaciones, ajustes, imputaciones y estados financieros.
- entidades: obligacion_financiera, movimiento_financiero, aplicacion_financiera, ajuste_financiero
- criticidad: media

---

## Reglas

1. No generar contratos.
2. No gestionar clientes.
3. No ejecutar lógica comercial.
4. No depender de UI.
5. Mantener separación con LOC.

---

## Notas

- Este dominio gestiona el estado económico del sistema.
- Todas las obligaciones derivan de una relación generadora.
- La naturaleza economica de una obligacion deriva de sus composiciones y conceptos financieros, no de un tipo rigido de obligacion.
- La imputación modifica el estado de deuda.
- La reversión implica deshacer una operación financiera previa dentro de un circuito válido.
- La cancelación implica la extinción final de una obligación sin modificar su historial.
- No define contratos, solo efectos financieros.
