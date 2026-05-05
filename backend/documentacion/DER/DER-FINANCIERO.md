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
- `INTERES_MORA` (compatibilidad heredada; no activo para mora persistida V1)
- `PUNITORIO`

#### Base morable

`aplica_punitorio` es booleano obligatorio con default `false`. Solo las
composiciones cuyo concepto tenga `aplica_punitorio = true` integran la base de
calculo de `PUNITORIO`. `PUNITORIO` y accesorios no marcados no integran esa
base.

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
- `factura_servicio` registrada como origen operativo pendiente -> relacion_generadora
- origen conceptual: `SERVICIO_TRASLADADO`
- la factura la emite un proveedor externo; el sistema no factura servicios
- la obligacion derivada se modela en financiero mediante relacion_generadora, obligacion_financiera y composicion_obligacion
- requiere entidad intermedia `factura_servicio`; la tabla SQL estructural existe, pero no existe API/backend, evento ni consumer financiero
- una `factura_servicio` no debe generar mas de una obligacion financiera activa
- la generacion financiera desde `factura_servicio` debe ser idempotente con clave conceptual `id_factura_servicio`; queda PENDIENTE / NO IMPLEMENTADO a nivel funcional
- decision conceptual recomendada para `SERVICIO_TRASLADADO`: 1 servicio asociado a inmueble o unidad funcional -> 1 `relacion_generadora`; cada `factura_servicio` registrada -> 1 `obligacion_financiera` dentro de esa relacion
- ciclo de vida conceptual: para `SERVICIO_TRASLADADO`, la `relacion_generadora` puede existir antes de la primera `factura_servicio`; las facturas posteriores generan obligaciones dentro de esa misma relacion
- esta decision queda PENDIENTE / NO IMPLEMENTADO hasta que exista contrato, API/backend, evento y consumer financiero
- existe tabla SQL `factura_servicio`, pero no existe endpoint documentado vigente para ese origen en inmobiliario y no se genera `relacion_generadora` ni `obligacion_financiera`

### Personas
- obligacion_obligado → persona

---

## 9. Consideraciones de implementación

- modelo basado en eventos
- uso de outbox/inbox
- trazabilidad completa obligatoria
- consistencia validada por DB + servicios
