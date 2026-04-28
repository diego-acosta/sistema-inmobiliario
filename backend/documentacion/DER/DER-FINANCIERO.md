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

## 4. Entidades principales

---

### 4.1 relacion_generadora

#### Descripción
Raíz del circuito financiero.

#### Función
- vincular negocio origen con estructura financiera

#### Origen
Se crea desde otros dominios (ej: contrato, venta).

---

### 4.2 obligacion_financiera

#### Descripción
Representa una obligación económica.

#### Generación
Definida en:
- SRV-FIN-003
- SRV-FIN-006

#### Relaciones
- pertenece a relacion_generadora
- tiene obligados
- puede tener composiciones
- se cancela mediante aplicaciones

---

### 4.3 obligacion_obligado

#### Descripción
Vincula obligación con personas.

#### Fuente
Dominio personas.

---

### 4.4 composicion_obligacion

#### Descripción
Detalle de una obligación.

#### Uso
- capital
- interés
- mora
- recargos

#### Nota
La mora se modela como composición o como nueva obligación según RN-FIN.

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

- relacion_generadora → obligacion_financiera
- obligacion_financiera → obligacion_obligado
- obligacion_financiera → composicion_obligacion

---

### Cancelación

- movimiento_financiero → aplicacion_financiera
- obligacion_financiera → aplicacion_financiera

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

### Personas
- obligacion_obligado → persona

---

## 9. Consideraciones de implementación

- modelo basado en eventos
- uso de outbox/inbox
- trazabilidad completa obligatoria
- consistencia validada por DB + servicios