# LOC-DEC-001 — Flujo Operativo Locativo

## 1. Objetivo

Definir el comportamiento operativo del dominio locativo y su relación con:

- disponibilidad
- ocupación
- contrato_alquiler

---

## 2. Principios

- Separación de dominios:
  - locativo define el flujo de alquiler
  - inmobiliario es owner de disponibilidad y ocupación

- contrato_alquiler NO modifica estado operativo directamente

- Impactos operativos son asincrónicos y event-driven

---

## 3. Estados operativos del activo (locativo)

El activo (inmueble / unidad_funcional) puede estar:

- DISPONIBLE
- RESERVADO_LOCATIVO
- OCUPADO
- NO_DISPONIBLE

⚠️ Estos estados:
- NO se persisten como un nuevo enum
- se derivan de disponibilidad + ocupación existentes

---

## 4. Flujo locativo

Cartera locativa  
→ Solicitud de alquiler  
→ Reserva locativa  
→ Contrato de alquiler  
→ Entrega / ocupación  
→ Finalización / restitución  

---

## 5. Reglas por etapa

### 5.1 Cartera locativa

- Define activos alquilables
- Fuente: dominio inmobiliario
- No modifica disponibilidad

---

### 5.2 Solicitud de alquiler

- No impacta disponibilidad
- Representa intención de alquiler

---

### 5.3 Reserva locativa

- Evento: `reserva_locativa_confirmada`
- Impacto:
  - disponibilidad → RESERVADA
- Owner: inmobiliario (por evento)

---

### 5.4 Contrato de alquiler

- No modifica disponibilidad
- No crea ocupación
- Representa acuerdo jurídico

---

### 5.5 Entrega / ocupación

- Evento: `entrega_locativa_registrada`
- Impacto:
  - creación de ocupación
  - disponibilidad → NO_DISPONIBLE

---

### 5.6 Finalización / restitución

- Evento: `restitucion_locativa_registrada`
- Impacto:
  - cierre de ocupación
  - disponibilidad → DISPONIBLE

---

## 6. Eventos del dominio locativo

- reserva_locativa_confirmada
- contrato_alquiler_activado
- entrega_locativa_registrada
- restitucion_locativa_registrada

---

## 7. Responsabilidades

| Dominio        | Responsabilidad |
|----------------|----------------|
| locativo       | flujo de alquiler |
| inmobiliario   | disponibilidad / ocupación |
| integración    | propagación de eventos |

---

## 8. Reglas clave

- contrato_alquiler NO modifica disponibilidad
- ocupación SOLO se crea en la entrega
- disponibilidad SOLO cambia mediante eventos
- consistencia eventual (no inmediata)

---

## 9. Estado actual del sistema

- contrato_alquiler ✔
- condiciones_economicas_alquiler ✔
- flujo previo ❌
- impacto operativo ❌

---

## 10. Próximo paso

Implementar:

- reserva_locativa

antes de continuar con otros bloques del dominio locativo.