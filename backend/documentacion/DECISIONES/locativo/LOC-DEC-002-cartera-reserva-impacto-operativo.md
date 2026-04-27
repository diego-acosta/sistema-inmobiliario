# LOC-DEC-002 — Cartera, Reserva e Impacto Operativo Locativo

## 1. Objetivo

Definir el comportamiento del flujo previo al contrato en el dominio locativo y su impacto sobre:

- disponibilidad
- ocupación
- estado operativo del activo

---

## 2. Principios

- Locativo define el flujo de alquiler, no el estado físico del activo
- Inmobiliario es owner de disponibilidad y ocupación
- Todas las modificaciones operativas se realizan vía eventos
- No existe modificación directa de disponibilidad desde locativo

---

## 3. Componentes del flujo

### 3.1 Cartera locativa

Representa el conjunto de activos habilitados para alquiler.

#### Reglas

- Se construye sobre inmuebles / unidades existentes
- No modifica disponibilidad
- Puede tener criterios de inclusión (estado, condiciones, etc.)
- Es un filtro lógico, no una entidad operativa obligatoria

---

### 3.2 Solicitud de alquiler

Representa la intención de alquilar un activo.

#### Reglas

- No impacta disponibilidad
- No bloquea el activo
- Puede existir múltiples solicitudes para un mismo activo
- Es previa a la reserva

---

### 3.3 Reserva locativa

Representa el bloqueo temporal de uno o más objetos inmobiliarios para alquiler.

La reserva es **multiobjeto**: una sola `reserva_locativa` puede cubrir varios inmuebles o unidades funcionales. El detalle de objetos se materializa en `reserva_locativa_objeto`.

#### 3.3.1 Modelo

**`reserva_locativa`** — entidad raíz, ya materializada en SQL:

| Campo | Tipo | Notas |
|---|---|---|
| `id_reserva_locativa` | bigint | PK |
| `uid_global` | uuid | único |
| `codigo_reserva` | varchar(50) | único |
| `fecha_reserva` | timestamp | requerido |
| `fecha_vencimiento` | timestamp | nullable; debe ser >= `fecha_reserva` |
| `estado_reserva` | varchar(30) | requerido; ver catálogo de estados |
| `id_solicitud_alquiler` | bigint | nullable; FK a solicitud origen |
| `observaciones` | text | nullable |
| metadatos `CORE-EF` | — | `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_*`, `op_id_*` |

**`reserva_locativa_objeto`** — detalle multiobjeto, materializada en schema oficial:

| Campo | Tipo | Notas |
|---|---|---|
| `id_reserva_locativa_objeto` | bigint | PK |
| `id_reserva_locativa` | bigint | FK requerido |
| `id_inmueble` | bigint | nullable; XOR con `id_unidad_funcional` |
| `id_unidad_funcional` | bigint | nullable; XOR con `id_inmueble` |
| `observaciones` | text | nullable |
| metadatos `CORE-EF` | — | subset mínimo |

Restricción XOR: cada fila debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`. Esta regla se materializa como `CHECK` en SQL, igual que `contrato_objeto_locativo.chk_col_xor`.

#### 3.3.2 Estado de reserva

El campo `estado_reserva` en `reserva_locativa` es la fuente de verdad del estado. **No se usa campo `activo` boolean.** El campo `estado_reserva` ya existe en SQL como `varchar(30) NOT NULL`.

Catálogo de estados:

| Estado | Descripción | Tipo |
|---|---|---|
| `pendiente` | Reserva creada, pendiente de confirmación formal | activo |
| `confirmada` | Reserva confirmada; objetos bloqueados para alquiler | activo |
| `cancelada` | Reserva cancelada antes de generar contrato | terminal |
| `expirada` | `fecha_vencimiento` superada sin confirmación ni conversión | terminal |
| `convertida` | Reserva convertida en contrato de alquiler | terminal |

Estados activos (bloquean los objetos): `pendiente`, `confirmada`.
Estados terminales (liberan los objetos): `cancelada`, `expirada`, `convertida`.

Transiciones válidas:

```
pendiente → confirmada   (confirmación formal)
pendiente → cancelada    (cancelación antes de confirmación)
pendiente → expirada     (vencimiento sin acción)
confirmada → cancelada   (cancelación posterior a confirmación)
confirmada → convertida  (alta de contrato de alquiler)
```

#### 3.3.3 Reglas de modelo

- Una `reserva_locativa` debe tener al menos un `reserva_locativa_objeto`
- Cada `reserva_locativa_objeto` refiere a exactamente un objeto inmobiliario: un `inmueble` O una `unidad_funcional` (XOR)
- No se mezclan niveles dentro de una misma reserva: cada objeto se referencia por su nivel natural (inmueble completo vs. unidad funcional)
- La baja lógica de la reserva (`deleted_at`) no reemplaza la transición de estado; el estado debe transicionar explícitamente a uno terminal antes de la baja

#### 3.3.4 Unicidad de reserva activa por objeto

Para cada objeto inmobiliario (inmueble o unidad funcional) **no puede existir más de una `reserva_locativa_objeto` cuya `reserva_locativa` padre esté en estado activo** (`pendiente` o `confirmada`) en un momento dado.

Esta regla se controla a nivel de objeto, no de reserva:

- Una misma reserva puede cubrir N objetos distintos
- Cada uno de esos N objetos tiene garantía de unicidad frente al resto de reservas activas
- Si el objeto A está cubierto por una reserva `confirmada`, no puede añadirse al objeto A en ninguna otra reserva en estado `pendiente` o `confirmada`

**Mecanismo de control:**

| Capa | Mecanismo |
|---|---|
| Aplicación | Validación explícita antes de insertar `reserva_locativa_objeto` |
| SQL | Índice único parcial implementado: validación a nivel de `has_conflicting_active_reserva_locativa` vía join `reserva_locativa_objeto → reserva_locativa` filtrando por `estado_reserva IN ('pendiente', 'confirmada')` |

La validación en aplicación es bloqueante. El índice SQL actúa como red de seguridad ante concurrencia.

---

### 3.4 Generación de contrato desde reserva locativa

El endpoint `POST /api/v1/reservas-locativas/{id}/generar-contrato` permite crear un `contrato_alquiler` tomando como origen una reserva confirmada.

#### Reglas

- Solo se puede generar contrato a partir de una reserva en estado `confirmada`.
- Solo puede existir **un contrato activo por reserva**. Si ya existe un `contrato_alquiler` con `id_reserva_locativa = :id` y `deleted_at IS NULL`, la operación es rechazada.
- Los objetos del contrato se copian desde `reserva_locativa_objeto`. El caller no declara objetos en el body; son tomados directamente de la reserva.
- El contrato queda en estado `borrador`. El flujo de activación es independiente.
- El campo `id_reserva_locativa` en `contrato_alquiler` queda seteado con el FK a la reserva origen.

#### Impacto operativo

- **No modifica disponibilidad.** El estado del objeto en el dominio inmobiliario no cambia al generar el contrato.
- **No modifica ocupación.** La ocupación se registra al momento de la entrega (`entrega_locativa_registrada`), no al alta del contrato.
- **No emite evento outbox.** La generación del contrato no produce ningún mensaje hacia otros dominios.

#### Garantía de unicidad

| Capa | Mecanismo |
|---|---|
| Aplicación | Validación explícita `has_contrato_for_reserva_locativa` antes de insertar |
| SQL | `UNIQUE INDEX uq_ca_reserva_activa ON contrato_alquiler (id_reserva_locativa) WHERE id_reserva_locativa IS NOT NULL AND deleted_at IS NULL` |

La validación en aplicación es bloqueante y produce error claro (`RESERVA_YA_TIENE_CONTRATO`). El índice SQL actúa como red de seguridad ante concurrencia.

#### Body del request

```json
{
  "codigo_contrato": "string",
  "fecha_inicio": "date",
  "fecha_fin": "date | null",
  "observaciones": "string | null"
}
```

Los objetos **no se declaran**: se copian automáticamente desde la reserva.

---

## 4. Impacto operativo

### 4.1 Evento: reserva_locativa_confirmada

#### Generado por:
- dominio locativo, al transicionar `estado_reserva` a `confirmada`

#### Consumido por:
- dominio inmobiliario

#### Payload:
- `id_reserva_locativa`
- lista de objetos: uno o más pares `(id_inmueble | id_unidad_funcional)` correspondientes a los `reserva_locativa_objeto` de la reserva

#### Efecto por objeto:
- crear nueva disponibilidad:
  - estado: `RESERVADA`
- cerrar disponibilidad previa del mismo objeto (si aplica)

El evento se emite una sola vez por transición de la reserva. El dominio inmobiliario es responsable de procesar cada objeto contenido en el payload.

---

### 4.2 Evento: contrato_alquiler_activado

#### Efecto:

- NO modifica disponibilidad
- NO crea ocupación

---

### 4.3 Evento: entrega_locativa_registrada

#### Efecto:

- crear ocupación
- disponibilidad → NO_DISPONIBLE

---

### 4.4 Evento: restitucion_locativa_registrada

#### Efecto:

- cerrar ocupación
- disponibilidad → DISPONIBLE

---

## 5. Reglas de consistencia

- No puede haber:
  - reserva activa (`pendiente` o `confirmada`) si el objeto no está disponible
  - ocupación activa sin entrega
  - más de una reserva activa para el mismo objeto en simultáneo
- La disponibilidad y ocupación no se pisan:
  - una refleja estado comercial
  - la otra estado físico
- Una reserva `confirmada` no implica por sí sola la generación de un contrato; solo bloquea el objeto
- La conversión a contrato (`convertida`) se materializa al dar de alta el `contrato_alquiler` con FK a la reserva

---

## 6. Responsabilidades por dominio

| Dominio      | Responsabilidad |
|--------------|----------------|
| locativo     | flujo de alquiler, gestión de reserva y sus objetos |
| inmobiliario | disponibilidad / ocupación |
| integración  | propagación de eventos |

---

## 7. Secuencia completa

activo disponible
→ solicitud alquiler
→ reserva locativa (cubre uno o más objetos)
→ confirmación de reserva → evento `reserva_locativa_confirmada` por objeto
→ contrato alquiler (con FK a reserva)
→ entrega
→ ocupación activa
→ restitución
→ activo disponible

---

## 8. Estado actual del sistema

| Componente | Estado |
|---|---|
| `contrato_alquiler` | ✔ implementado |
| `condiciones_economicas_alquiler` | ✔ implementado |
| `reserva_locativa` (tabla SQL + backend) | ✔ implementado |
| `reserva_locativa_objeto` | ✔ implementado |
| `solicitud_alquiler` | ✔ implementado |
| impacto operativo (eventos) | ❌ parcial |

---

## 9. Próximo paso

Implementar `reserva_locativa` con diseño multiobjeto.

Requiere, en orden:

1. **Migración SQL**: crear tabla `reserva_locativa_objeto` con:
   - FK a `reserva_locativa`
   - columnas `id_inmueble` y `id_unidad_funcional` nullable
   - `CHECK` XOR igual al de `contrato_objeto_locativo`
   - índice para validación de unicidad de reserva activa por objeto

2. **Backend**: implementar endpoints en el dominio locativo:
   - `POST /api/v1/reservas-locativas` — alta con objetos embebidos
   - `PATCH /api/v1/reservas-locativas/{id}/confirmar` — transición `pendiente → confirmada`
   - `PATCH /api/v1/reservas-locativas/{id}/cancelar` — transición a `cancelada`
   - `GET /api/v1/reservas-locativas/{id}` — detalle con objetos embebidos
   - `GET /api/v1/reservas-locativas` — listado

3. **Validaciones clave**:
   - disponibilidad del objeto antes de crear reserva
   - unicidad de reserva activa por objeto (app + SQL)
   - coherencia `fecha_vencimiento >= fecha_reserva`
   - al menos un objeto requerido

4. **Evento**: emitir `reserva_locativa_confirmada` al confirmar, con payload multiobjeto

El dominio locativo no modifica disponibilidad directamente en ningún paso.
