# RN-COM - Reglas del dominio Comercial

## Objetivo
Definir reglas de negocio del dominio comercial.

## Alcance
Incluye reservas, ventas, instrumentos, cesiones, escrituracion y rescisiones.

---

## A. Reglas de reservas

### RN-COM-001 - La reserva debe vincular al menos un objeto inmobiliario
- descripcion: toda reserva comercial valida debe estar asociada a uno o mas objetos inmobiliarios.
- aplica_a: reserva_venta, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-002 - Un objeto no puede estar reservado simultaneamente de forma incompatible
- descripcion: un mismo objeto inmobiliario no debe quedar comprometido por reservas vigentes incompatibles entre si.
- aplica_a: reserva_venta, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-003 - La reserva puede cancelarse antes de convertirse en venta
- descripcion: la reserva admite cancelacion mientras no haya avanzado validamente al siguiente estado comercial.
- aplica_a: reserva_venta
- origen_principal: DEV-SRV

### RN-COM-004 - La reserva confirmada puede derivar en venta
- descripcion: una reserva confirmada puede utilizarse como base comercial para registrar una venta.
- aplica_a: reserva_venta, venta
- origen_principal: DEV-SRV

### RN-COM-005 - La reserva no genera efectos financieros por si misma
- descripcion: la reserva no define deuda, saldo ni pago como logica financiera primaria.
- aplica_a: reserva_venta
- origen_principal: DEV-SRV

### RN-COM-006 - La reserva no implica transferencia de titularidad
- descripcion: la existencia de una reserva no produce transferencia juridica ni comercial definitiva del objeto.
- aplica_a: reserva_venta, objeto_inmobiliario
- origen_principal: DER

### RN-COM-007 - La reserva debe tener estado comercial definido
- descripcion: toda reserva debe mantenerse en un estado comercial explicito y coherente con su ciclo de vida.
- aplica_a: reserva_venta
- origen_principal: DEV-SRV
- observaciones: estados esperables incluyen borrador, activa, confirmada, cancelada, vencida y finalizada cuando corresponda segun el modelo del dominio.

## B. Reglas de ventas

### RN-COM-008 - La venta puede derivar de una reserva o crearse directamente
- descripcion: la venta puede originarse desde una reserva previa o generarse en forma directa si la politica comercial lo permite.
- aplica_a: venta, reserva_venta
- origen_principal: DEV-SRV

### RN-COM-009 - La venta debe vincular objetos inmobiliarios
- descripcion: toda venta valida debe asociarse a uno o mas objetos inmobiliarios comercializados.
- aplica_a: venta, venta_objeto_inmobiliario, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-010 - La venta no puede existir sin sujeto comprador
- descripcion: la operacion de venta requiere identificacion de la contraparte compradora.
- aplica_a: venta, persona
- origen_principal: DER

### RN-COM-011 - La venta no implica por si misma escrituracion
- descripcion: la existencia de la venta comercial no equivale a su formalizacion legal por escrituracion.
- aplica_a: venta, escrituracion
- origen_principal: DEV-SRV

### RN-COM-012 - La venta puede cancelarse bajo condiciones definidas
- descripcion: la cancelacion de venta solo procede dentro de las condiciones previstas por el flujo comercial.
- aplica_a: venta
- origen_principal: DEV-SRV

### RN-COM-013 - La venta puede generar instrumentos comerciales
- descripcion: una venta puede dar origen a instrumentos comerciales que formalicen o documenten la operacion.
- aplica_a: venta, instrumento_compraventa
- origen_principal: DEV-SRV

### RN-COM-014 - La venta no debe duplicar objetos en conflicto
- descripcion: un objeto inmobiliario no debe quedar incorporado a ventas vigentes incompatibles entre si.
- aplica_a: venta, venta_objeto_inmobiliario, objeto_inmobiliario
- origen_principal: DEV-SRV

## C. Reglas de instrumentos comerciales

### RN-COM-015 - Todo instrumento debe vincularse a una operacion comercial
- descripcion: un instrumento comercial valido debe asociarse a una operacion base del dominio.
- aplica_a: instrumento_compraventa, reserva_venta, venta
- origen_principal: DEV-SRV

### RN-COM-016 - Un instrumento no existe sin operacion base
- descripcion: no debe generarse un instrumento comercial autonomo sin referencia a una operacion comercial existente.
- aplica_a: instrumento_compraventa
- origen_principal: DEV-SRV

### RN-COM-017 - La anulacion del instrumento no elimina la operacion base
- descripcion: anular un instrumento no implica borrar ni cancelar automaticamente la reserva o venta relacionada.
- aplica_a: instrumento_compraventa, reserva_venta, venta
- origen_principal: DEV-SRV

### RN-COM-018 - Los instrumentos no redefinen por si solos el estado comercial de la operacion
- descripcion: el instrumento acompana o formaliza la operacion, pero no sustituye la logica de estados comerciales.
- aplica_a: instrumento_compraventa, venta, reserva_venta
- origen_principal: DEV-SRV

### RN-COM-019 - Un instrumento puede tener estados propios independientes
- descripcion: el ciclo de vida del instrumento puede diferenciarse del ciclo de vida de la operacion base.
- aplica_a: instrumento_compraventa
- origen_principal: DEV-SRV

## D. Reglas de cesiones

### RN-COM-020 - La cesion implica cambio de sujeto en la operacion
- descripcion: la cesion transfiere la posicion del sujeto comercial dentro de la operacion alcanzada.
- aplica_a: cesion, venta, persona
- origen_principal: DEV-SRV

### RN-COM-021 - La cesion no debe alterar la identidad del objeto comercializado
- descripcion: la cesion modifica la parte involucrada, no el objeto inmobiliario de la operacion.
- aplica_a: cesion, venta, objeto_inmobiliario
- origen_principal: DER

### RN-COM-022 - La cesion debe mantener trazabilidad del titular anterior
- descripcion: la operacion cedida debe conservar referencia trazable del sujeto previo.
- aplica_a: cesion, venta, persona
- origen_principal: DEV-SRV

### RN-COM-023 - La cesion puede requerir validaciones adicionales
- descripcion: la cesion puede quedar sujeta a condiciones comerciales especificas antes de resultar valida.
- aplica_a: cesion
- origen_principal: DEV-SRV

## E. Reglas de escrituracion

### RN-COM-024 - La escrituracion implica formalizacion legal de la operacion
- descripcion: la escrituracion representa una instancia de formalizacion juridica posterior o complementaria a la venta.
- aplica_a: escrituracion, venta
- origen_principal: DEV-SRV

### RN-COM-025 - Una venta puede existir sin escrituracion
- descripcion: la venta comercial puede mantenerse sin escrituracion hasta que el proceso avance a esa instancia.
- aplica_a: venta, escrituracion
- origen_principal: DEV-SRV

### RN-COM-026 - La escrituracion no redefine la operacion comercial previa
- descripcion: la escrituracion formaliza la operacion base sin sustituir ni reescribir su identidad comercial.
- aplica_a: escrituracion, venta
- origen_principal: DEV-SRV

### RN-COM-027 - La escrituracion debe vincularse a la operacion base
- descripcion: toda escrituracion debe referenciar la operacion comercial de origen.
- aplica_a: escrituracion, venta
- origen_principal: DEV-SRV

## F. Reglas de rescisiones comerciales

### RN-COM-028 - La rescision invalida la operacion comercial
- descripcion: la rescision deja sin efecto la continuidad esperada de la operacion alcanzada.
- aplica_a: rescision_venta, venta
- origen_principal: DEV-SRV

### RN-COM-029 - La rescision no borra el historial
- descripcion: la rescision no elimina rastros ni antecedentes de la operacion comercial previa.
- aplica_a: rescision_venta, venta
- origen_principal: DEV-SRV

### RN-COM-030 - La rescision debe ser trazable
- descripcion: toda rescision debe preservar trazabilidad sobre causa, momento y relacion con la operacion base.
- aplica_a: rescision_venta, venta
- origen_principal: DEV-SRV

### RN-COM-031 - Una operacion rescindida no debe continuar su flujo normal
- descripcion: una vez rescindida, la operacion no debe seguir avanzando por el ciclo comercial ordinario.
- aplica_a: rescision_venta, venta
- origen_principal: DEV-SRV

## G. Reglas transversales comerciales

### RN-COM-032 - El dominio comercial no calcula deuda ni saldo
- descripcion: el dominio comercial no define ni recalcula deuda, saldo o mora como verdad primaria.
- aplica_a: dominio comercial
- origen_principal: DEV-SRV

### RN-COM-033 - El dominio comercial no gestiona pagos
- descripcion: la gestion de pagos e imputaciones pertenece al dominio financiero.
- aplica_a: dominio comercial
- origen_principal: DEV-SRV

### RN-COM-034 - Los efectos financieros se delegan al dominio financiero
- descripcion: los impactos economicos derivados de la operacion comercial deben resolverse en el dominio financiero.
- aplica_a: venta, reserva_venta, cesion, escrituracion, rescision_venta
- origen_principal: DEV-SRV

### RN-COM-035 - Los estados comerciales no deben confundirse con estados financieros
- descripcion: el estado de una reserva o venta debe evaluarse con semantica comercial y no financiera.
- aplica_a: reserva_venta, venta, instrumento_compraventa, rescision_venta
- origen_principal: DEV-SRV

### RN-COM-036 - La disponibilidad del objeto depende del dominio inmobiliario
- descripcion: la elegibilidad del objeto comercializado depende de la informacion y estado definidos por el dominio inmobiliario.
- aplica_a: objeto_inmobiliario, reserva_venta, venta
- origen_principal: DEV-SRV

### RN-COM-037 - La operacion comercial depende del objeto inmobiliario
- descripcion: no debe existir operacion comercial valida sin referencia a objeto inmobiliario conforme al modelo.
- aplica_a: reserva_venta, venta, instrumento_objeto_inmobiliario, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-038 - Las operaciones comerciales deben mantener trazabilidad
- descripcion: reservas, ventas, instrumentos, cesiones, escrituraciones y rescisiones deben poder reconstruirse funcionalmente.
- aplica_a: reserva_venta, venta, instrumento_compraventa, cesion, escrituracion, rescision_venta
- origen_principal: DEV-SRV

### RN-COM-039 - Toda operacion write sincronizable debe respetar control tecnico transversal
- descripcion: las mutaciones comerciales sincronizables deben respetar versionado, op_id y outbox conforme al marco transversal aplicable.
- aplica_a: operaciones write sincronizables del dominio comercial
- origen_principal: DEV-SRV
- observaciones: la semantica tecnica proviene del marco transversal; aqui se aplica como regla de dominio.

## H. Reglas de convivencia entre reserva y venta

### Alcance especifico
Estas reglas aplican a:
- servicios de reservas
- servicios de venta
- validaciones de disponibilidad
- logica transaccional multiobjeto

### RN-COM-040 - `activa`, `confirmada` y `venta` no son equivalentes
- descripcion: `activa` y `confirmada` son estados de `reserva_venta`; `venta` es una entidad comercial independiente y no un estado de la reserva. Una reserva `activa` es valida sin bloqueo operativo, mientras que una reserva `confirmada` es valida con bloqueo operativo sobre disponibilidad.
- aplica_a: reserva_venta, venta, disponibilidad, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-041 - La reserva confirmada bloquea disponibilidad e impide operaciones incompatibles
- descripcion: si existe una `reserva_venta` en estado `confirmada` sobre un objeto, debe bloquear la disponibilidad del objeto e impedir nuevas reservas incompatibles, la confirmacion de otras reservas incompatibles y la generacion de una `venta` incompatible. Todo intento incompatible debe fallar por conflicto.
- aplica_a: reserva_venta, venta, disponibilidad, objeto_inmobiliario
- origen_principal: DEV-SRV
- observaciones: aplica por cada objeto involucrado y alcanza escenarios multiobjeto.

### RN-COM-042 - La reserva activa no bloquea disponibilidad y puede perder prioridad
- descripcion: una `reserva_venta` en estado `activa` no bloquea la disponibilidad del objeto y puede perder prioridad frente a otra reserva que alcance `confirmada` o frente a una `venta` incompatible. Si pierde prioridad debe cerrarse como `cancelada` por accion manual o `vencida` por agotamiento automatico de vigencia.
- aplica_a: reserva_venta, venta, disponibilidad, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-043 - Solo una reserva confirmada puede convertirse en venta
- descripcion: la generacion de una `venta` a partir de una `reserva_venta` solo es valida cuando la reserva se encuentra en estado `confirmada`. La conversion debe cerrar la reserva en estado `finalizada`.
- aplica_a: reserva_venta, venta
- origen_principal: DEV-SRV

### RN-COM-044 - La venta resuelve la incompatibilidad segun la reserva origen
- descripcion: cuando se genera una `venta` sobre un objeto, si la venta proviene de la misma reserva confirmada la reserva origen debe pasar de `confirmada` a `finalizada`; si existe otra reserva incompatible sobre el mismo objeto, una reserva en `activa` debe cerrarse como `cancelada` o `vencida` y una reserva en `confirmada` no debe coexistir con la venta, ya que constituye error de integridad.
- aplica_a: venta, reserva_venta, objeto_inmobiliario
- origen_principal: DEV-SRV

### RN-COM-045 - El cierre de una reserva confirmada libera disponibilidad
- descripcion: cuando una `reserva_venta` en estado `confirmada` se cierra como `cancelada` o `vencida`, debe liberar la disponibilidad previamente reservada sobre cada objeto alcanzado.
- aplica_a: reserva_venta, disponibilidad, objeto_inmobiliario
- origen_principal: DEV-SRV
- observaciones: en el estado actual implementado, esa liberacion se materializa como transicion `RESERVADA -> DISPONIBLE` para cada objeto afectado.
- observaciones: esta resolucion es valida para la implementacion vigente, pero queda pendiente definir si en el futuro la liberacion debe asumir siempre `DISPONIBLE` o si debe restaurar o recalcular el estado operativo efectivo del objeto segun otras causas concurrentes de indisponibilidad.
- observaciones: mientras no exista una politica mas rica de recomposicion de disponibilidad, el cierre de una reserva `confirmada` seguira materializando `DISPONIBLE`.
- observaciones: si a futuro existen otras causas de no disponibilidad, como bloqueo administrativo, restriccion juridica, venta u otra operacion incompatible, liberar una reserva confirmada no necesariamente deberia dejar el objeto en `DISPONIBLE`.
- observaciones: queda pendiente formal definir si la liberacion futura debe restaurar estado previo, recalcular disponibilidad efectiva o mantener la estrategia actual.

### RN-COM-046 - El vencimiento afecta disponibilidad segun el estado previo
- descripcion: el paso de `activa` a `vencida` no impacta disponibilidad porque la reserva no bloqueaba operativamente el objeto; el paso de `confirmada` a `vencida` debe liberar la disponibilidad previamente bloqueada.
- aplica_a: reserva_venta, disponibilidad
- origen_principal: DEV-SRV

### RN-COM-047 - La extension de vigencia solo procede sobre reservas vigentes
- descripcion: la extension de vigencia de una `reserva_venta` solo es valida en estados `activa` y `confirmada`; no debe admitirse extension sobre una reserva `vencida`.
- aplica_a: reserva_venta
- origen_principal: DEV-SRV

### RN-COM-048 - No puede existir venta incompatible con reserva confirmada vigente
- descripcion: nunca puede existir una `venta` sobre un objeto mientras subsista una `reserva_venta` `confirmada` vigente e incompatible sobre ese mismo objeto. Si esa coexistencia aparece, constituye error de integridad o falta de validacion en la capa de aplicacion.
- aplica_a: venta, reserva_venta, disponibilidad, objeto_inmobiliario
- origen_principal: DEV-SRV
- observaciones: esta invariante rige para validaciones transaccionales multiobjeto y para composicion de operaciones que afecten mas de un objeto.

---

## Reglas de normalizacion

1. No duplicar reglas.
2. Consolidar variantes similares.
3. Separar claramente lo comercial de lo financiero.
4. No incluir reglas tecnicas profundas de infraestructura.
5. Mantener numeracion RN-COM-XXX.

---

## Notas

- Este catalogo deriva del DEV-SRV del dominio comercial.
- No reemplaza el DER ni el dominio financiero.
- Debe mantenerse alineado con CU-COM.
- Es base para validaciones del backend.
