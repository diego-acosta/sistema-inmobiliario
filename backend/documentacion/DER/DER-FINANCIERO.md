# DER-FIN-001 — Dominio Financiero
Sistema Inmobiliario

---

## 1. Propósito del dominio

El dominio financiero gestiona el ciclo económico completo del sistema:

- generación de obligaciones
- registro de movimientos
- imputación de pagos
- gestión de mora, ajustes y créditos
- administración de caja
- reporting financiero consolidado

Es un dominio transversal, desacoplado de los dominios de negocio.

---

## 2. Alcance funcional (alineado a DEV-SRV-FIN)

El dominio soporta:

- SRV-FIN-001 / 002 → relación generadora
- SRV-FIN-003 → generación de obligaciones
- SRV-FIN-004 / 005 → índices financieros
- SRV-FIN-006 → cronogramas
- SRV-FIN-007 → simulación y registro de pagos
- SRV-FIN-008 → imputación financiera
- SRV-FIN-009 → mora, créditos y débitos
- SRV-FIN-010 → emisión
- SRV-FIN-011 → caja y garantías
- SRV-FIN-012 → reporting

---

## 3. Principios del modelo

### FIN-PR-001 — Raíz del circuito

Toda estructura financiera se organiza a partir de:

- `relacion_generadora`

---

### FIN-PR-002 — Separación estructural

Se diferencian:

- obligación → deuda
- movimiento → hecho económico
- aplicación → imputación

---

### FIN-PR-003 — Desacople del negocio

El dominio financiero no depende directamente de:

- locativo
- comercial

Estos generan `relacion_generadora`.

---

### FIN-PR-004 — Modelo reconstruible

No existen:

- cuenta corriente física
- subcuentas físicas

El estado financiero se reconstruye dinámicamente.

---

### FIN-PR-005 — Composicion economica por conceptos

La `obligacion_financiera` no debe tipificarse rigidamente como venta, alquiler, servicio, expensa u otra categoria de negocio.

El origen financiero se interpreta desde `relacion_generadora`.

La naturaleza economica de la deuda se interpreta desde:

- `composicion_obligacion`
- `concepto_financiero`

Por lo tanto, una cuota de venta, un anticipo, un canon locativo, un servicio trasladado, una mora o una liquidacion final se representan por sus componentes y conceptos financieros, no por una columna central de tipo de obligacion.

---

## 4. Entidades principales

---

### 4.1 relacion_generadora

#### Descripción
Raíz del circuito financiero.

#### Función
- vincular negocio origen con estructura financiera

#### Origen
Se crea desde otros dominios (ej: contrato, venta).

#### Idempotencia estructural

`relacion_generadora` tiene unicidad parcial por
`(tipo_origen, id_origen) WHERE deleted_at IS NULL`.

---

### 4.2 obligacion_financiera

#### Descripción
Representa una deuda exigible o proyectada dentro del dominio financiero.

#### Generación
Definida en:
- SRV-FIN-003
- SRV-FIN-006

#### Relaciones
- pertenece a relacion_generadora
- tiene obligados
- debe tener una o mas composiciones cuando se materializa como deuda persistente
- se cancela mediante aplicaciones

#### Nota estructural
La obligacion no codifica rigidamente el tipo economico. El significado de sus importes surge de `composicion_obligacion` y `concepto_financiero`.

Para cronogramas periodicos, la DB impide duplicar obligaciones activas con la
misma `(id_relacion_generadora, periodo_desde, periodo_hasta)`.

#### Cronograma locativo V2 minimo

Para obligaciones generadas desde `contrato_alquiler`, el obligado principal se
materializa en `obligacion_obligado` a partir del locatario principal asociado
al contrato por `relacion_persona_rol` y `rol_participacion`.

El garante no se incorpora automaticamente como obligado principal.

---

### 4.3 obligacion_obligado

#### Descripción
Vincula obligación con personas.

#### Fuente
Dominio personas.

---

### 4.4 composicion_obligacion

#### Descripción
Detalle economico de una obligacion.

#### Uso
- capital
- interés
- mora
- recargos
- impuestos
- cargos administrativos
- bonificaciones o creditos cuando corresponda

#### Nota
Toda composicion debe referenciar exactamente un `concepto_financiero`.

---

### 4.4.1 concepto_financiero

#### Descripción
Catalogo financiero que define el significado de cada componente economico de una obligacion.

#### Funcion
- clasificar la naturaleza economica de una composicion
- permitir que una obligacion combine varios conceptos
- evitar que `obligacion_financiera` codifique tipos rigidos como venta, alquiler, servicio o expensa
- definir con `aplica_punitorio` si el saldo del concepto integra la base
  morable para liquidar `PUNITORIO`

#### Ejemplos conceptuales
- `CAPITAL_VENTA`
- `ANTICIPO_VENTA`
- `CANON_LOCATIVO`
- `SERVICIO_TRASLADADO`
- `SERVICIO_RECUPERADO`
- `INTERES_MORA` (compatibilidad heredada; no activo para mora persistida V1)
- `PUNITORIO`

#### Base morable

`aplica_punitorio` es booleano obligatorio con default `false`. Solo las
composiciones cuyo concepto tenga `aplica_punitorio = true` integran la base de
calculo de `PUNITORIO`. `PUNITORIO` y accesorios no marcados no integran esa
base.

---

### 4.4.2 liquidacion_punitorio

#### Descripcion
Trazabilidad de cada liquidacion positiva de `PUNITORIO` generada al registrar
un pago.

#### Funcion
- registrar el periodo y parametros usados para liquidar punitorio
- vincular la liquidacion con `obligacion_financiera`
- vincular la liquidacion con la `composicion_obligacion` `PUNITORIO`
- vincular la liquidacion con `uid_pago_grupo` y `codigo_pago_grupo`

#### Nota
No crea deuda nueva, no reemplaza `aplicacion_financiera` y no modifica saldos.
El saldo sigue derivando de `composicion_obligacion` y
`aplicacion_financiera`.

---

### 4.4.3 parametro_punitorio

#### Descripcion
Parametro formal de calculo de mora/punitorio V1.

#### Funcion
- definir `tasa_diaria` y `dias_gracia` vigentes por fecha
- soportar alcance `GLOBAL`, `CONCEPTO` y `RELACION_GENERADORA`
- permitir prioridad de resolucion: relacion generadora, concepto, global,
  default tecnico

#### Nota
No crea deuda, no registra liquidaciones y no modifica saldos. La liquidacion
persistida sigue ocurriendo mediante `composicion_obligacion` `PUNITORIO` y su
trazabilidad en `liquidacion_punitorio`.

---

### 4.5 movimiento_financiero

#### Descripción
Evento económico registrado.

#### Origen
- SRV-FIN-007
- SRV-FIN-009

#### Tipos
Definidos en catálogo (EST-FIN / RN-FIN).

---

#### Agrupacion de pagos por persona
En `POST /api/v1/financiero/pagos`, cada obligacion afectada conserva su propio
`movimiento_financiero`. Los campos opcionales `uid_pago_grupo` y
`codigo_pago_grupo` agrupan los movimientos creados por la misma operacion de
pago, sin modificar las relaciones con `aplicacion_financiera`.

### 4.6 aplicacion_financiera

#### Descripción
Entidad central de imputación.

#### Función
Relaciona:

- movimiento_financiero
- obligacion_financiera

#### Definición funcional
Reglas en:
- SRV-FIN-008
- RN-FIN

---

### 4.7 indice_financiero

#### Descripción
Valores utilizados para actualización.

#### Uso
- ajuste de obligaciones
- actualización monetaria

---

### 4.8 cuenta_financiera

#### Descripción
Entidad de tesorería.

#### Gestión
SRV-FIN-011

---

### 4.9 movimiento_tesoreria

#### Descripción
Impacto en cuentas financieras.

#### Relación
Deriva de movimiento_financiero.

Para egreso proveedor minimo de `EMPRESA_PAGA_Y_RECUPERA`, V1 permite
`movimiento_tesoreria` sin `movimiento_financiero`, vinculado a
`factura_servicio` por `egreso_proveedor_factura_servicio`. Esta excepcion
representa egreso real de empresa y no deuda logica.

### 4.9.1 egreso_proveedor_factura_servicio

#### Descripcion
Tabla puente entre `factura_servicio` y `movimiento_tesoreria` para registrar
pagos de proveedor realizados por la empresa.

#### Funcion
- vincular el egreso real con la factura externa;
- soportar pagos parciales y multiples egresos;
- proveer idempotencia por `op_id_alta`;
- mantener separado el egreso proveedor de `PAGO_EXTERNO_INFORMADO` y de la
  futura obligacion de recupero.

---

### 4.10 conciliacion_bancaria

#### Descripción
Proceso de conciliación.

---

### 4.11 detalle_conciliacion

#### Descripción
Detalle de conciliación.

---

## 5. Relaciones del modelo

### Núcleo

- relacion_generadora 1 --- N obligacion_financiera
- obligacion_financiera 1 --- N obligacion_obligado
- obligacion_financiera 1 --- N composicion_obligacion
- concepto_financiero 1 --- N composicion_obligacion
- obligacion_financiera 1 --- N liquidacion_punitorio
- composicion_obligacion 1 --- N liquidacion_punitorio
- relacion_generadora 1 --- N parametro_punitorio
- concepto_financiero 1 --- N parametro_punitorio

---

### Cancelación

- movimiento_financiero → aplicacion_financiera
- obligacion_financiera → aplicacion_financiera
- composicion_obligacion 0..1 → aplicacion_financiera

---

### Tesorería

- movimiento_financiero → movimiento_tesoreria
- cuenta_financiera → movimiento_tesoreria

---

## 6. Reglas del dominio

Las reglas NO se definen en este documento.

Se delegan a:

- RN-FIN → reglas de negocio
- EST-FIN → estados
- ERR-FIN → errores
- EVT-FIN → eventos

---

## 7. Flujo operativo

### 1. Generación de relación
Desde dominio de negocio.

---

### 2. Generación de obligaciones
SRV-FIN-003 / 006

---

### 3. Registro de movimiento
SRV-FIN-007

---

### 4. Imputación
SRV-FIN-008

---

### 5. Ajustes / mora
SRV-FIN-009

---

### 6. Caja / tesorería
SRV-FIN-011

---

### 7. Reporting
SRV-FIN-012

---

## 8. Integración con otros dominios

### Locativo
- contrato → relacion_generadora
- eventos → generación de obligaciones

### Comercial
- venta → relacion_generadora

### Inmobiliario
- `factura_servicio` registrada como origen operativo -> relacion_generadora
- origen financiero V1: `relacion_generadora.tipo_origen = FACTURA_SERVICIO`
- id origen V1: `relacion_generadora.id_origen = id_factura_servicio`
- concepto de la obligacion derivada: `SERVICIO_TRASLADADO`
- la factura la emite un proveedor externo; el sistema no factura servicios
- la obligacion derivada se modela en financiero mediante relacion_generadora, obligacion_financiera y composicion_obligacion
- requiere `factura_servicio` como origen externo registrado; la API/backend inmobiliaria V1 registra la factura externa y financiero expone materializacion explicita
- una `factura_servicio` no debe generar mas de una obligacion financiera activa
- la creacion de `relacion_generadora` `FACTURA_SERVICIO` es idempotente por `id_factura_servicio`
- decision V1: cada `factura_servicio` registrada -> 1 `relacion_generadora` propia -> 1 obligacion `SERVICIO_TRASLADADO`
- decision V1: el responsable se resuelve desde `asignacion_servicio_responsable`, entidad inmobiliaria especifica vinculada por `id_servicio` + `id_inmueble` o `id_unidad_funcional`
- `asignacion_servicio_responsable` define `id_persona`, vigencia y `porcentaje_responsabilidad`; los porcentajes aplicables deben sumar 100%
- si no hay responsable vigente: `OBLIGADO_NO_RESUELTO`
- si hay responsables inconsistentes: `RESPONSABLE_SERVICIO_AMBIGUO`
- si la factura cruza cambio de responsable: `FACTURA_CRUZA_CAMBIO_RESPONSABLE`
- V1 no prorratea por cambio de responsable, no usa composiciones negativas ni saldos a favor en este bloque
- la habilitacion estructural de `FACTURA_SERVICIO` en `relacion_generadora` esta implementada; la generacion explicita de obligacion esta implementada en `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar`
- `DIRECTO_RESPONSABLE` usa `SERVICIO_TRASLADADO` y puede registrar
  `PAGO_EXTERNO_INFORMADO` solo si existe un responsable unico 100%
- `EMPRESA_PAGA_Y_RECUPERA` no usa `PAGO_EXTERNO_INFORMADO`: la empresa paga
  al proveedor por caja/tesoreria y luego genera una obligacion de recupero
  contra personas
- el egreso proveedor minimo de `EMPRESA_PAGA_Y_RECUPERA` crea
  `movimiento_tesoreria` y `egreso_proveedor_factura_servicio`; no crea
  `movimiento_financiero`, `obligacion_financiera` ni recibo interno
- `liquidacion_recupero` V1 es entidad financiera propia para convertir
  egresos proveedor registrados en deuda de recupero contra personas
- la relacion generadora del recupero usa
  `tipo_origen = LIQUIDACION_RECUPERO` e `id_origen = id_liquidacion_recupero`
- la obligacion derivada usa composicion `SERVICIO_RECUPERADO`
- `liquidacion_recupero_factura` vincula la liquidacion con la
  `factura_servicio`; `liquidacion_recupero_egreso` guarda los egresos usados
  con columnas CORE-EF, `deleted_at` y estado `ACTIVO`/`ANULADO`; solo los
  vinculos activos/no eliminados bloquean su reutilizacion/anulacion;
  `liquidacion_recupero_responsable` guarda el snapshot de responsables y porcentajes
- `liquidacion_recupero` admite estados `EMITIDA` y `ANULADA`.
- la anulacion V1 de `liquidacion_recupero` marca la liquidacion como
  `ANULADA`, anula la obligacion `SERVICIO_RECUPERADO` asociada y sus
  composiciones, cancela la `relacion_generadora` `LIQUIDACION_RECUPERO` y
  libera los egresos mediante `liquidacion_recupero_egreso` en estado
  `ANULADO` con `deleted_at`.
- la anulacion V1 de `liquidacion_recupero` no toca
  `movimiento_tesoreria`, `egreso_proveedor_factura_servicio` ni
  `factura_servicio`.
- la anulacion V1 de `liquidacion_recupero` se bloquea si existen pagos,
  aplicaciones financieras activas, punitorios activos u operaciones
  financieras posteriores sobre la obligacion o sus composiciones.
- para V1 de servicios comunes recuperados se recomienda el concepto
  `SERVICIO_RECUPERADO`, disponible en `concepto_financiero` con naturaleza
  `DEBITO`, `es_imputable = true`, `permite_saldo = true` y
  `aplica_punitorio = true`; `EXPENSA_TRASLADADA` queda reservado para
  expensas formales e `IMPUESTO_TRASLADADO` para impuestos
- no existe evento ni consumer automatico para `factura_servicio_registrada`

### Personas
- obligacion_obligado → persona

---

## 9. Consideraciones de implementación

- modelo basado en eventos
- uso de outbox/inbox
- trazabilidad completa obligatoria
- consistencia validada por DB + servicios
