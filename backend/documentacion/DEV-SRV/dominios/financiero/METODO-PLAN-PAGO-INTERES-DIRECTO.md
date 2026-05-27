# METODO-PLAN-PAGO-INTERES-DIRECTO

## 1) Propósito
Definir el diseño funcional/técnico de **INTERES_DIRECTO** para Plan Pago V2 sin implementación de código en este PR.

## 2) Decisión arquitectónica
- **PLAN_POR_BLOQUES** permanece como estructura principal y extensible del plan.
- **INTERES_DIRECTO no es un método global de plan** ni un endpoint paralelo.
- **INTERES_DIRECTO se modela como `metodo_liquidacion` por bloque/tramo**, especialmente para bloques `TRAMO_CUOTAS`.

## 3) Modelo conceptual
Un plan puede combinar bloques heterogéneos, por ejemplo:
- `ANTICIPO`
- `TRAMO_CUOTAS` con `metodo_liquidacion=INTERES_DIRECTO`
- `REFUERZO`
- `SALDO`

Esto evita competencia semántica entre “método de plan” y “método de liquidación”.

## 4) Campos propuestos por bloque/tramo
Para bloques financiados (principalmente `TRAMO_CUOTAS`):
- `metodo_liquidacion`
- `tasa_interes_directo_periodica`
- `cantidad_periodos`
- `base_calculo_interes`

Notas:
- `base_calculo_interes` define explícitamente la base del interés del tramo (ej. capital inicial del bloque).
- La periodicidad operativa del bloque debe ser consistente con la periodicidad de la tasa periódica.

## 5) Fórmula conceptual
Para `INTERES_DIRECTO`:

**interés total del bloque = capital inicial del bloque × tasa periódica × cantidad de períodos**

Luego:
- Capital y/o interés se distribuyen entre cuotas del bloque según regla de prorrateo definida.
- El total de cuota resulta de la suma de componentes capital + interés.

## 6) Tasa total vs tasa periódica
- **Tasa total**: agrega el costo financiero para todo el tramo.
- **Tasa periódica**: tasa aplicada por período del bloque.

Regla de diseño:
- El contrato operativo del bloque debe preferir **tasa periódica explícita**.
- Si se recibe tasa total en capas superiores, debe transformarse explícitamente a tasa periódica antes de liquidar el bloque (sin ambigüedad).

## 7) Composición capital/interés
Cada obligación del bloque debe soportar composición separada:
- componente capital
- componente interés

Objetivo:
- trazabilidad financiera por concepto,
- soporte de saldos por componente,
- compatibilidad con procesos posteriores de estado de cuenta e imputación.

## 8) Redondeo y última cuota
- Redondeo monetario a escala de moneda (ej. 2 decimales).
- Cualquier diferencia acumulada por redondeo se absorbe en la **última cuota** del bloque.
- Debe existir regla explícita y determinista para reproducibilidad e idempotencia funcional.

## 9) Refuerzos y saldos
`INTERES_DIRECTO` en `TRAMO_CUOTAS` debe coexistir con bloques:
- `REFUERZO` (hitos puntuales)
- `SALDO` (cierre/ajuste del plan)

El método de liquidación aplica **solo al bloque que lo declara** y no redefine el comportamiento de otros bloques.

## 10) Persistencia esperada (futura)
Sin cambiar SQL en este PR, el diseño apunta a:
- `plan_pago_venta_bloque`: metadatos del bloque + parámetros de liquidación (`metodo_liquidacion`, tasa, períodos, base).
- `obligacion_financiera`: obligaciones resultantes por cuota/hito con importe total.
- `composicion_obligacion`: detalle por componentes (capital/interés) por cada obligación.

## 11) Endpoints futuros posibles (no implementados aquí)
Opciones compatibles con el modelo:
1. Extender endpoint unificado de plan por bloques para aceptar `metodo_liquidacion` por bloque.
2. Endpoint técnico de enriquecimiento/validación de bloque (si fuera necesario).

Restricción:
- No crear endpoint “método global INTERES_DIRECTO” que compita con PLAN_POR_BLOQUES.

## 12) Decisión CORE-EF futura (AGENTS.md §14)
Cuando se implemente write real:
- Clasificar endpoint (`COMMAND_WRITE_NEGOCIO` o el que corresponda).
- Usar helper CORE-EF existente (sin parseo manual).
- Declarar explícitamente idempotencia, outbox, lock lógico, versionado y frontera transaccional.
- Exigir `If-Match-Version` solo si el contrato de modificación/versionado de entidad lo requiere.
- Mantener `ErrorResponse` estándar.

## 13) Tests requeridos para implementación futura
Mínimos esperados:
- Happy path de bloque `TRAMO_CUOTAS` con `INTERES_DIRECTO`.
- Cálculo de interés total según fórmula conceptual.
- Separación de composición capital/interés por obligación.
- Redondeo y ajuste de última cuota.
- Convivencia con `ANTICIPO`, `REFUERZO` y `SALDO` sin invasión semántica.
- Idempotencia según criterio CORE-EF definido para el endpoint final.
- Headers CORE-EF faltantes/inválidos en endpoint write final.
- No regresión de métodos existentes por bloques/cuotas/anticipo.

## 14) Fuera de alcance explícito de este PR
- No implementación de código funcional.
- No cambios SQL estructurales.
- No cambios en tests existentes.
- No indexación por índice.
- No sistema francés.
- No sistema alemán.
- No caja, pagos ni recibos.
