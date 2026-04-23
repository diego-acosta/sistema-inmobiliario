# INT-DEC-002 - Politica de disponibilidad post-venta

## 1. Contexto actual

### 1.1 Flujo comercial efectivamente materializado

La implementacion actual del flujo comercial write materializa, en lo relevante para disponibilidad:

1. `reserva_venta confirmada` reemplaza la disponibilidad vigente `DISPONIBLE` por una nueva disponibilidad `RESERVADA`
2. `generar venta` desde una reserva `confirmada` preserva el bloqueo `RESERVADA`
3. `venta_confirmada` no modifica `disponibilidad`
4. `escrituracion_registrada` no modifica `disponibilidad` en la implementacion actual

Esto surge de:

1. `COM-DEC-001`
2. `INT-DEC-001`
3. `INT-EVT-001`
4. `INT-CONS-001`
5. `DEV-API-COMERCIAL`
6. `SRV-COM-002`
7. `SRV-COM-006`
8. `test_reservas_venta_confirm.py`
9. `test_reservas_venta_generate_venta.py`
10. `test_ventas_confirm.py`
11. `test_escrituraciones_create.py`

### 1.2 Ownership semantico

El dominio `inmobiliario` es el owner exclusivo de `disponibilidad`.

En consecuencia:

1. `comercial` puede validar elegibilidad contra `disponibilidad`
2. `comercial` puede emitir eventos de negocio relevantes
3. el cambio operativo post-venta, si existe, debe ser ejecutado por `inmobiliario`

### 1.3 Estado hoy observable

El ultimo estado operativo hoy verificable para un activo vendido cuyo flujo proviene de reserva confirmada es:

1. `RESERVADA` luego de confirmar la reserva
2. `RESERVADA` luego de generar la venta
3. `RESERVADA` luego de confirmar la venta
4. `RESERVADA` luego de registrar la escrituracion

Por lo tanto, mientras el evento `escrituracion_registrada` permanezca pendiente, el activo puede seguir observable en `RESERVADA`; una vez consumido por `inmobiliario`, la politica implementada pasa a resolver `RESERVADA -> NO_DISPONIBLE`.

## 2. Problema

La version actual presenta un vacio de politica post-venta:

1. el activo puede quedar indefinidamente en `RESERVADA`
2. no esta definido de forma cerrada el estado operativo final post-venta
3. no esta definido de forma cerrada que evento habilita el cambio
4. el flujo comercial llega a hitos relevantes `venta_confirmada` y `escrituracion_registrada`, pero el estado operativo del activo no sale automaticamente del bloqueo comercial heredado de la reserva

El problema no es de ownership sino de politica interdominio.

La pregunta arquitectonica a resolver es:

1. si debe existir mutacion automatica post-venta
2. en que hito debe ocurrir
3. con que estado operativo resultante
4. bajo que responsabilidad de ejecucion

## 3. Alternativas evaluadas

### 3.1 Mantener `RESERVADA` hasta decision manual

Descripcion:

1. no se define automatismo interdominio
2. el activo permanece en `RESERVADA` hasta una intervencion manual o una futura capacidad aun no definida

Ventajas:

1. no introduce automatismos prematuros
2. no exige consumidor interdominio inmediato

Desventajas:

1. deja al activo indefinidamente en un estado de bloqueo transitorio
2. no resuelve la politica post-venta
3. degrada trazabilidad operativa porque `RESERVADA` deja de representar un bloqueo comercial temporal y pasa a comportarse como estado terminal de hecho

### 3.2 Cambiar disponibilidad al confirmar venta

Descripcion:

1. `venta_confirmada` dispara el cambio post-venta

Ventajas:

1. elimina rapidamente la permanencia indefinida en `RESERVADA`
2. usa un evento ya existente en outbox

Desventajas:

1. adelanta el cierre operativo antes del hito juridico hoy mas fuerte del flujo implementado
2. contradice la definicion vigente de `COM-DEC-001`, que considera cierre logico actual a `venta confirmada + escrituracion registrada`
3. confunde confirmacion comercial con cierre operativo definitivo del activo

### 3.3 Cambiar disponibilidad al registrar escrituracion

Descripcion:

1. `escrituracion_registrada` dispara el cambio post-venta

Ventajas:

1. es consistente con `INT-CONS-001`
2. es consistente con la definicion logica vigente de cierre en `COM-DEC-001`
3. mantiene separacion entre confirmacion comercial y formalizacion juridica
4. evita que `RESERVADA` quede como estado abierto indefinido si existe consumidor interdominio
5. conserva trazabilidad historica usando el patron existente de cierre + nueva disponibilidad

Desventajas:

1. requiere consumidor interdominio para ejecutarse fuera del write comercial
2. sigue dependiendo de un hito comercial/documental que no equivale por si solo a `ocupacion`

### 3.4 Cambiar disponibilidad por evento externo posterior

Descripcion:

1. el cambio post-venta se produce solo ante un evento externo registral o legal posterior a `escrituracion_registrada`

Ventajas:

1. empuja el cambio al hito mas fuerte de regularizacion externa

Desventajas:

1. ese evento no esta materializado hoy en backend
2. no existe payload ni contrato write que lo respalde
3. deja la politica operativa dependiente de una capacidad inexistente en el workspace actual

### 3.5 Inventar un estado nuevo especifico post-venta

Descripcion:

1. crear un estado nuevo para disponibilidad, por ejemplo `VENDIDA`

Ventajas:

1. podria expresar semantica mas especifica

Desventajas:

1. contradice la regla de no inventar estados no respaldados por el workspace
2. no existe respaldo hoy en SQL, backend ni tests
3. mezcla necesidad documental con expansion no implementada del modelo

## 4. Criterios de decision

La politica debe evaluarse contra los siguientes criterios:

### 4.1 Separacion de dominios

1. `comercial` emite hitos de negocio
2. `inmobiliario` decide y ejecuta cambios sobre `disponibilidad`
3. la politica no puede trasladar ownership operativo a `comercial`

### 4.2 Consistencia con el flujo real implementado

1. la reserva confirmada ya deja el activo en `RESERVADA`
2. la venta confirmada no cambia hoy ese estado
3. la escrituracion registrada tampoco lo cambia hoy
4. la politica no debe describir como vigente un automatismo que aun no existe en codigo

### 4.3 Evitar automatismos prematuros

1. no debe dispararse el cierre operativo en un hito mas temprano que el cierre logico hoy aceptado
2. no debe apoyarse la politica en eventos externos no implementados

### 4.4 Trazabilidad historica de disponibilidad

1. la salida de `RESERVADA` debe preservar historial
2. debe reutilizarse el patron real de `inmobiliario`: cierre del registro vigente + alta de uno nuevo
3. no debe reescribirse retrospectivamente el bloqueo previo

### 4.5 Compatibilidad con modelo multiobjeto

1. la politica debe ser aplicable a ventas con uno o varios objetos
2. el evento disparador debe permitir identificar todos los activos afectados
3. el cambio debe poder ejecutarse por objeto sin perder coherencia transaccional local

### 4.6 Restriccion de no invencion

1. no deben inventarse estados no respaldados por SQL, backend o tests
2. no deben inventarse eventos adicionales fuera del contrato ya cerrado

## 5. Decision propuesta

### 5.1 Evento disparador

Se decide que la politica post-venta no debe disparar el cambio de `disponibilidad` en `venta_confirmada`.

Se decide que el evento habilitante del cambio operativo post-venta es `escrituracion_registrada`.

### 5.2 Ejecutor del cambio

Se decide que la mutacion debe ser ejecutada por `inmobiliario`, nunca por `comercial`.

La integracion debe mantenerse:

1. asincronica
2. event-driven
3. unidireccional `comercial -> inmobiliario`

### 5.3 Regla de politica

La politica definida para esta version es:

1. mientras solo exista `venta_confirmada`, la disponibilidad no cambia automaticamente
2. cuando `escrituracion_registrada` sea consumido por `inmobiliario`, debe resolverse la salida de `RESERVADA`
3. hasta que ese consumo asincronico ocurra, el comportamiento observable puede seguir siendo permanencia temporal en `RESERVADA`
4. si el consumidor recibe una inconsistencia permanente para el payload ya emitido, el evento no debe permanecer en `PENDING`; debe cerrarse en un estado terminal de rechazo operacional

### 5.4 Estado de implementacion de la politica

La politica queda definida arquitectonicamente en esta decision y ya tiene materializacion tecnica inicial en el consumidor de `escrituracion_registrada` de `inmobiliario`.

Por lo tanto:

1. la politica decidida no equivale a afirmar que el backend actual ya la ejecuta
2. la version actual implementada sigue sin cambio automatico post-venta
3. el contrato de ownership y el disparador objetivo quedan cerrados desde ahora

## 6. Estado final del activo

### 6.1 Analisis del workspace actual

En el workspace actual no existe un estado especifico de disponibilidad que nombre semanticamente el activo como `vendido`, `escriturado` o equivalente.

Por lo tanto:

1. no existe hoy un estado final post-venta especifico de negocio materializado en `disponibilidad`
2. no corresponde inventarlo en esta decision

### 6.2 Estado operativo respaldado disponible

Si se requiere expresar la salida del activo desde `RESERVADA` sin inventar estados nuevos, el estado operativo hoy respaldado por workspace es `NO_DISPONIBLE`.

Ese estado:

1. existe en documentacion, codigo y tests
2. no introduce un catalogo nuevo
3. permite representar que el activo deja de estar disponible comercialmente

### 6.3 Alcance de la decision sobre estado final

La presente decision no congela un estado final de negocio especifico del activo vendido.

La presente decision si fija que:

1. no debe inventarse un nuevo estado final especifico post-venta
2. el estado operativo resultante utilizable con respaldo actual es `NO_DISPONIBLE`
3. la definicion semantica completa del estado final real del activo sigue pendiente

## 7. Pendientes

1. definir idempotencia y trazabilidad del consumo con una estrategia mas fuerte que el criterio operativo actual de `ALREADY_APPLIED`
2. definir observabilidad, reporte y eventual remediacion para eventos terminales `REJECTED`
3. definir si `NO_DISPONIBLE` es solo una resolucion operativa transitoria o el estado estable post-venta
4. definir si en el futuro debe existir un estado especifico de negocio post-venta, solo si el workspace lo respalda con cambios explicitos de SQL, backend y tests
5. definir si un evento registral externo posterior debe complementar o reemplazar a `escrituracion_registrada`

## 8. Base de verificacion

Esta decision se apoya en:

1. `backend/documentacion/DECISIONES/comercial/COM-DEC-001-cierre-del-ciclo-de-vida-de-venta.md`
2. `backend/documentacion/DECISIONES/integracion/INT-DEC-001-integracion-comercial-inmobiliario.md`
3. `backend/documentacion/DECISIONES/integracion/INT-EVT-001-eventos-integracion-comercial-inmobiliario.md`
4. `backend/documentacion/DECISIONES/integracion/INT-CONS-001-comportamiento-inmobiliario-ante-eventos.md`
5. `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`
6. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-002-gestion-de-venta.md`
7. `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-006-gestion-de-escrituracion.md`
8. `backend/documentacion/DEV-API/dominios/inmobiliario/DEV-API-INM-001.md`
9. `backend/app/application/comercial/services/confirm_venta_service.py`
10. `backend/app/application/comercial/services/create_escrituracion_service.py`
11. `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
12. `backend/tests/test_reservas_venta_confirm.py`
13. `backend/tests/test_reservas_venta_generate_venta.py`
14. `backend/tests/test_ventas_confirm.py`
15. `backend/tests/test_escrituraciones_create.py`
16. `backend/tests/test_outbox_events.py`
17. `backend/tests/test_disponibilidades_reemplazar_vigente.py`
18. `AGENTS.md`

## 9. Contradicciones detectadas

Se detectan contradicciones documentales no bloqueantes:

1. `SRV-INM-007` continua describiendo `disponibilidad` como sin API/backend vigente, en conflicto con `DEV-API-INM-001`, codigo y tests actuales
2. `RN-INM` y `EST-INM` continúan tratando `disponibilidad` como `PARCIAL` por falta de backend, lo que ya no coincide con la implementacion real
3. `DEV-API-COMERCIAL` y `SRV-COM` admiten posibilidad de ajuste post-venta por integracion; el backend actual ya materializa ese ajuste mediante el consumidor de `escrituracion_registrada` en `inmobiliario`
