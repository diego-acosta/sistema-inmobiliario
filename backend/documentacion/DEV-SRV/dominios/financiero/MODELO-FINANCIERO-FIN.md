# MODELO-FINANCIERO-FIN - Modelo financiero implementado

## Estado del documento

- estado: `IMPLEMENTADO PARCIAL / ALINEADO A BACKEND`
- dominio: `financiero`
- ultima revision: `2026-04-30`
- alcance implementado: `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `concepto_financiero`, `movimiento_financiero`, `aplicacion_financiera`, `liquidacion_punitorio`, consulta de deuda consolidada y generacion de mora diaria.
- alineado a SQL vigente
- no define funcionalidad fuera del backend vigente

Este documento describe el modelo financiero real que hoy implementa el backend. El dominio financiero es el dueno semantico de deuda, saldos, imputaciones, estado financiero y mora.

---

## 1. Flujo implementado

```text
relacion_generadora
    -> obligacion_financiera
        -> composicion_obligacion + concepto_financiero
            -> aplicacion_financiera
                -> saldo_pendiente / saldo_componente
                    -> estado_obligacion
                        -> mora diaria si corresponde
```

Flujo operativo:

1. Se crea una `relacion_generadora` desde un origen permitido.
2. Se crea una `obligacion_financiera` asociada a esa relacion.
3. La obligacion se crea con una o mas `composicion_obligacion`.
4. Cada composicion referencia un `concepto_financiero`.
5. Una imputacion crea un `movimiento_financiero` y una o mas `aplicacion_financiera`.
6. La base de datos actualiza saldos por triggers.
7. El backend lee los saldos resultantes y actualiza `estado_obligacion` cuando corresponde.
8. El proceso de mora marca obligaciones `EMITIDA` vencidas como `VENCIDA` y calcula mora dinamica en lecturas.

---

## 2. Entidades implementadas

### 2.1 relacion_generadora

Raiz formal del circuito financiero.

Implementado:

- alta por `POST /api/v1/financiero/relaciones-generadoras`
- consulta puntual
- listado paginado con filtros basicos
- validacion de origen para `VENTA` y `CONTRATO_ALQUILER`

No implementado:

- activar
- cancelar
- finalizar
- validacion de reutilizacion de `X-Op-Id` con payload distinto

### 2.2 obligacion_financiera

Representa deuda dentro de una `relacion_generadora`.

Implementado:

- alta manual por `POST /api/v1/financiero/obligaciones`
- consulta puntual con composiciones
- `importe_total`
- `saldo_pendiente`
- `estado_obligacion`
- `fecha_emision`
- `fecha_vencimiento`

Reglas implementadas:

- toda obligacion creada por API requiere `id_relacion_generadora` existente
- toda obligacion creada por API requiere al menos una composicion
- no se usa `tipo_obligacion`
- el estado inicial de alta manual es `PROYECTADA`

### 2.3 composicion_obligacion

Representa el desglose economico de una obligacion.

Implementado:

- alta interna junto con la obligacion
- `id_concepto_financiero`
- `orden_composicion`
- `importe_componente`
- `saldo_componente`
- `estado_composicion_obligacion`

Reglas implementadas:

- cada composicion referencia un `concepto_financiero` existente
- el backend no expone alta autonoma de composiciones
- la naturaleza economica se interpreta desde `concepto_financiero`

### 2.4 concepto_financiero

Catalogo financiero que define la naturaleza economica de una composicion.

Implementado:

- consulta por `GET /api/v1/financiero/conceptos-financieros`
- busqueda interna por codigo para crear obligaciones e imputaciones
- catalogo base con `INTERES_MORA` disponible en seeds actuales solo por compatibilidad heredada; V1 no lo usa como concepto activo de mora persistida
- `aplica_punitorio`: indica si el saldo vivo de ese concepto integra la base
  morable para liquidar `PUNITORIO`

### 2.5 movimiento_financiero y aplicacion_financiera

`movimiento_financiero` representa el movimiento registrado por la imputacion.

`aplicacion_financiera` vincula ese movimiento con obligacion y composicion.

Para registro de pagos por persona, V1 mantiene un `movimiento_financiero` por
obligacion afectada. Los movimientos generados por una misma operacion de pago
comparten `uid_pago_grupo` y `codigo_pago_grupo`; esos campos son trazabilidad
comun y no reemplazan las `aplicacion_financiera`.

Para pago externo informado de `factura_servicio` en escenario
`DIRECTO_RESPONSABLE`, V1 usa
`movimiento_financiero.tipo_movimiento = PAGO_EXTERNO_INFORMADO` y
`aplicacion_financiera.tipo_aplicacion = PAGO_EXTERNO_INFORMADO`. Ese registro
reduce o cancela `SERVICIO_TRASLADADO`, pero no representa cobro de la
inmobiliaria: no crea movimiento de caja, no crea `movimiento_tesoreria`, no
usa `codigo_pago_grupo` y no genera constancia interna de cobro.

`DIRECTO_RESPONSABLE` debe entenderse en V1 como una factura/servicio de
responsabilidad 100% de una persona que paga directamente al proveedor. No
aplica a facturas comunes, compartidas, porcentuales ni repartidas.

Implementado:

- `POST /api/v1/financiero/imputaciones`
- una imputacion crea un movimiento tipo `PAGO`
- una imputacion puede generar una o varias aplicaciones
- cada aplicacion puede apuntar a una composicion
- `orden_aplicacion` refleja el orden de distribucion aplicado

No implementado:

- movimiento global unico por pago
- reversion parcial de aplicaciones sueltas
- estado persistido de aplicacion

### 2.6 liquidacion_punitorio

`liquidacion_punitorio` registra cada liquidacion positiva de mora persistida
como `PUNITORIO`.

Es una tabla de trazabilidad: no crea deuda nueva, no reemplaza
`composicion_obligacion`, no reemplaza `aplicacion_financiera` y no recalcula
saldos. Cada fila referencia la `obligacion_financiera`, la composicion
`PUNITORIO` afectada y el agrupador de pago `uid_pago_grupo` /
`codigo_pago_grupo`.

Campos funcionales principales:

- periodo de calculo: `fecha_vencimiento`, `fecha_inicio_calculo`,
  `fecha_fin_calculo`
- parametros del calculo: `base_morable`, `tasa_diaria`, `dias_calculados`
- importe trazado: `importe_liquidado`
- estado inicial: `ACTIVA`

### 2.7 parametro_punitorio

`parametro_punitorio` formaliza los parametros de calculo de mora/punitorio
V1. No crea deuda ni reemplaza `liquidacion_punitorio`; solo define
`tasa_diaria` y `dias_gracia` vigentes para una fecha de referencia.

Alcances V1:

- `GLOBAL`: sin `id_relacion_generadora` ni `id_concepto_financiero`
- `CONCEPTO`: con `id_concepto_financiero`
- `RELACION_GENERADORA`: con `id_relacion_generadora`

Resolucion:

1. `RELACION_GENERADORA`
2. `CONCEPTO`
3. `GLOBAL`
4. defaults tecnicos (`0.001`, `5`) si no hay tabla o parametro vigente

Solo aplican parametros `ACTIVO`, no eliminados y vigentes por
`fecha_desde`/`fecha_hasta`. V1 documenta el no solapamiento como regla de
servicio/repository; el SQL base no usa exclusion constraint.

---

## 3. Saldos

Regla real implementada:

- la base de datos actualiza `saldo_componente` mediante triggers sobre
  `composicion_obligacion` y `aplicacion_financiera`.
- `obligacion_financiera.importe_total` deriva de la suma de
  `importe_componente` de sus composiciones activas.
- `obligacion_financiera.saldo_pendiente` deriva de la suma de
  `saldo_componente` de sus composiciones activas.
- `obligacion_financiera.importe_cancelado_acumulado` deriva de las
  aplicaciones financieras registradas contra la obligacion.
- el backend no recalcula saldos como fuente primaria.
- luego de registrar aplicaciones, el backend lee el saldo resultante y actualiza el estado de la obligacion.

Esto aplica a:

- `obligacion_financiera.saldo_pendiente`
- `composicion_obligacion.saldo_componente`

Restriccion:

- no duplicar calculo de saldos en servicios de aplicacion.

---

## 4. Imputacion implementada

Estados que aceptan imputacion:

- `PROYECTADA`
- `EMITIDA`
- `EXIGIBLE`
- `PARCIALMENTE_CANCELADA`
- `VENCIDA`

Reglas:

- la obligacion debe existir y no estar dada de baja
- el monto debe ser mayor a cero
- el monto no puede exceder `saldo_pendiente`
- deben existir composiciones activas con saldo
- la distribucion se hace por prioridad de concepto y luego por `orden_composicion`

Prioridad implementada:

1. `PUNITORIO`
2. `CARGO_ADMINISTRATIVO`
3. `INTERES_FINANCIERO`
4. `AJUSTE_INDEXACION`
5. `CAPITAL_VENTA`
6. `ANTICIPO_VENTA`
7. `CANON_LOCATIVO`
8. `EXPENSA_TRASLADADA`
9. `SERVICIO_TRASLADADO`
10. `IMPUESTO_TRASLADADO`
11. otros conceptos por `orden_composicion`

---

## 4.1 Origen V1 Para Factura De Servicio Externa

Para V1, cada `factura_servicio` registrada sera una `relacion_generadora`
financiera propia:

- `relacion_generadora.tipo_origen = FACTURA_SERVICIO`
- `relacion_generadora.id_origen = id_factura_servicio`
- la obligacion financiera derivada usara el concepto `SERVICIO_TRASLADADO`

Estado implementado: `FACTURA_SERVICIO` esta habilitado como origen estructural
de `relacion_generadora`, validando que exista `factura_servicio` activa. La
API/backend inmobiliaria V1 permite registrar y consultar `factura_servicio`.
La materializacion explicita de la obligacion `SERVICIO_TRASLADADO` esta
implementada en:

`POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar`

Esta decision aplica solo a facturas externas emitidas por proveedores. El
sistema no factura servicios: registra el origen externo y el dominio
`financiero` genera la deuda trasladada cuando exista el flujo implementado.
El registro operativo/documental de la factura puede existir sin periodo; la
materializacion financiera de `SERVICIO_TRASLADADO` exige periodo completo para
resolver responsables.

Motivos:

- idempotencia directa por factura
- trazabilidad simple `factura_servicio` -> `relacion_generadora` -> obligacion
- evita crear una entidad intermedia de servicio facturable
- encaja con el modelo actual de `relacion_generadora(tipo_origen, id_origen)`

### Responsables De Servicios Trasladados

Decision V1 implementada en inmobiliario: el responsable de `SERVICIO_TRASLADADO` no se
resuelve rigidamente desde alquiler, venta u ocupacion, ni mediante
`relacion_persona_rol` como solucion final. La fuente de resolucion sera la
entidad inmobiliaria especifica `asignacion_servicio_responsable`.

Modelo conceptual:

`servicio`
-> `inmueble_servicio` / `unidad_funcional_servicio`
-> `asignacion_servicio_responsable`
-> `factura_servicio`
-> `relacion_generadora FACTURA_SERVICIO`
-> `obligacion_financiera SERVICIO_TRASLADADO`
-> `obligacion_obligado`

Reglas de materializacion V1:

- La factura debe existir, estar activa y no estar eliminada.
- La factura puede estar registrada sin periodo como documento externo, pero
  para materializar financieramente debe tener `periodo_desde` y
  `periodo_hasta`.
- Si falta `periodo_desde` o `periodo_hasta`, el endpoint devuelve
  `PERIODO_FACTURA_REQUERIDO` y no crea `relacion_generadora`,
  `obligacion_financiera`, `composicion_obligacion` ni
  `obligacion_obligado`.
- La operacion crea o reutiliza `relacion_generadora` con
  `tipo_origen = FACTURA_SERVICIO` e `id_origen = id_factura_servicio`.
- Si ya existe obligacion activa para esa relacion, el endpoint devuelve
  resultado idempotente `YA_MATERIALIZADA` sin duplicar relacion ni obligacion.
- Debe existir el concepto financiero `SERVICIO_TRASLADADO`; si falta, no se
  crea obligacion.
- La obligacion se crea en estado `EMITIDA`, copiando fechas, periodo e importe
  desde `factura_servicio`; la moneda usa `ARS` como fallback V1.
- `asignacion_servicio_responsable` se vincula por `id_servicio` + `id_inmueble`
  o `id_unidad_funcional`.
- No se vincula por FK directa a `inmueble_servicio` ni a
  `unidad_funcional_servicio`.
- `id_persona` y `porcentaje_responsabilidad` son obligatorios.
- Para el servicio + objeto + periodo de la factura, los porcentajes activos
  aplicables deben sumar 100%.
- Si no hay responsable vigente, la generacion financiera debe devolver
  `OBLIGADO_NO_RESUELTO`.
- Si existen responsables inconsistentes, debe devolver
  `RESPONSABLE_SERVICIO_AMBIGUO`.
- Si la factura cruza un cambio de responsable, debe devolver
  `FACTURA_CRUZA_CAMBIO_RESPONSABLE`.
- V1 no prorratea por cambio de responsable dentro del periodo de factura.
- V1 no usa composiciones negativas ni saldos a favor en este bloque.

Al crear la obligacion, financiero materializara una fila en
`obligacion_obligado` por responsable aplicable, copiando `id_persona` y
`porcentaje_responsabilidad` desde `asignacion_servicio_responsable`.

Estado V1: `asignacion_servicio_responsable` tiene SQL/API/backend inmobiliario.
La generacion financiera de `SERVICIO_TRASLADADO` desde una `factura_servicio`
esta implementada como endpoint financiero explicito y transaccional.

### Pago Externo Informado De Factura De Servicio

Endpoint implementado:

`POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/pago-externo`

Registra que el responsable pago la factura directamente al proveedor externo.
No es ingreso ni egreso de caja de la inmobiliaria.

Alcance vigente: `DIRECTO_RESPONSABLE`. En V1 solo corresponde cuando la
factura/servicio pertenece directamente a una persona responsable al 100%.
No debe usarse para repartir una factura comun entre varias personas ni para
representar que cada responsable paga su porcentaje al proveedor.

Reglas V1:

- La `factura_servicio` debe existir, estar activa y estar materializada.
- Debe existir `relacion_generadora.tipo_origen = FACTURA_SERVICIO` para esa
  factura.
- Debe existir una `obligacion_financiera` activa asociada a la relacion.
- La obligacion debe tener exactamente un `obligacion_obligado` activo.
- Ese unico obligado debe tener `porcentaje_responsabilidad = 100`.
- Si existen multiples obligados, o el unico obligado no es 100%, devuelve
  `PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO`.
- Debe existir una composicion activa `SERVICIO_TRASLADADO` con saldo.
- `importe_pagado` debe ser mayor a cero.
- El pago se aplica hasta el saldo disponible de `SERVICIO_TRASLADADO`.
- Si `importe_pagado` excede el saldo, se informa `remanente_no_aplicado`.
- Si no hay saldo aplicable, devuelve `SIN_SALDO_APLICABLE`.
- Crea `movimiento_financiero` y `aplicacion_financiera` con tipo
  `PAGO_EXTERNO_INFORMADO`.
- No crea `movimiento_tesoreria`, movimiento de caja ni recibo/constancia
  interna de cobro.
- No liquida punitorio, no revierte pagos, no toca cronograma ni indexacion.
- Con `X-Op-Id`, un reintento con el mismo payload devuelve el resultado
  existente; con payload distinto devuelve `IDEMPOTENCY_PAYLOAD_CONFLICT`.
- El endpoint bloquea facturas comunes, compartidas, porcentuales o repartidas
  mediante la validacion de responsable unico al 100%, porque esos casos
  pertenecen a `EMPRESA_PAGA_Y_RECUPERA`.

### Empresa Paga Y Recupera

Cuando una factura de proveedor debe dividirse entre empresa e
inquilino/comprador, o entre varias personas, el pago al proveedor no se divide
operativamente.

Decision:

- la empresa/inmobiliaria paga al proveedor.
- ese pago pertenece al circuito de egreso, caja y tesoreria de la empresa.
- luego se genera una obligacion de recupero a los responsables por la parte
  correspondiente.
- la obligacion de recupero representa deuda con la empresa, no pago al
  proveedor.
- `porcentaje_responsabilidad` de `asignacion_servicio_responsable` no debe
  interpretarse como porcentaje que cada persona paga directamente al proveedor.
- si una factura requiere reparto, no corresponde registrar
  `PAGO_EXTERNO_INFORMADO` por cada persona.
- el concepto financiero recomendado para V1 de servicios comunes es
  `SERVICIO_RECUPERADO`.
- `EXPENSA_TRASLADADA` queda reservado para una futura liquidacion formal de
  expensas; `IMPUESTO_TRASLADADO` para impuestos; `CARGO_RECUPERO` queda como
  alternativa generica futura si se decide unificar recuperos heterogeneos.
- en V1 la generacion de recupero es manual/controlada; la automatizacion desde
  una factura pagada queda pendiente.

Expensas e impuestos trasladados no se implementan en este bloque.
El diseno de este circuito queda documentado en
`SRV-FIN-020-recupero-servicios-comunes`.

---

## 5. Estado de obligacion

Regla implementada despues de imputar:

- si `saldo_pendiente = 0`, el backend actualiza `estado_obligacion` a `CANCELADA`
- si `saldo_pendiente < importe_total`, el backend actualiza `estado_obligacion` a `PARCIALMENTE_CANCELADA`
- no cambia estados `ANULADA` ni `REEMPLAZADA`

El proceso de mora materializa `VENCIDA` solo para obligaciones `EMITIDA` con `fecha_vencimiento < fecha_proceso` y `saldo_pendiente > 0`.

---

## 6. Mora V1 simple implementada

Endpoint:

- `POST /api/v1/financiero/mora/generar`

Regla:

- selecciona obligaciones con `fecha_vencimiento < fecha_proceso`
- requiere `saldo_pendiente > 0`
- requiere `estado_obligacion = 'EMITIDA'`
- tasa diaria y dias de gracia resueltos por `parametro_punitorio`
  (`RELACION_GENERADORA` > `CONCEPTO` > `GLOBAL` > default tecnico)
- `dias_atraso = max(0, fecha_corte - (fecha_vencimiento + dias_gracia_mora))`
- importe dinamico: `saldo_pendiente * tasa_diaria_mora * dias_atraso`
- redondeo a 2 decimales
- si no hay atraso o saldo, la mora calculada es `0`

Efecto:

- cambia `estado_obligacion` de `EMITIDA` a `VENCIDA`
- no crea `obligacion_financiera` nueva
- no crea composicion `INTERES_MORA`
- no capitaliza sobre la obligacion base
- expone `mora_calculada`, `dias_atraso` y `tasa_diaria_mora` en lecturas

Limitacion: V1 no expone endpoint administrativo para crear o modificar
`parametro_punitorio`; el seed crea un parametro `GLOBAL` equivalente al
default tecnico.

Nota: Mora V1 desacopla dos responsabilidades:

- estado persistido (`EMITIDA → VENCIDA`) → se determina contra la fecha real
  del sistema en el momento de correr `mora/generar`
- calculo financiero (`dias_atraso`, `mora_calculada`) → usa `fecha_corte` si
  se provee en la consulta, o `date.today()` si se omite
- dias de gracia: el calculo aplica 5 dias antes de acumular mora

Ver detalle en `SRV-FIN-013` seccion "Desacople entre estado persistido y
calculo financiero".

---

## 7. Consulta de deuda consolidada

Endpoint:

- `GET /api/v1/financiero/deuda`

Implementado:

- listado de obligaciones con composiciones
- filtros por relacion, estado, vencimiento y saldo
- paginacion `limit` / `offset`

La consulta es read-only y no recalcula saldos.

---

## 8. Estado de cuenta financiero

Descripcion:

Vista consolidada del estado financiero de una relacion generadora.

Incluye:

- obligaciones
- composiciones
- imputaciones mediante `aplicacion_financiera`
- saldos actuales
- estados de obligacion

Reglas:

- es una proyeccion del modelo, no una logica de negocio nueva
- no modifica datos
- usa saldos calculados por la DB
- usa datos persistidos para el resumen
- incluye composiciones y aplicaciones reales asociadas a cada obligacion

Notas:

- `cantidad_vencidas` se calcula contra la fecha actual del sistema.
- No existe aun fecha de referencia configurable para esta vista.

---

## 9. Estado de cuenta por persona

Endpoint: `GET /api/v1/financiero/personas/{id_persona}/estado-cuenta`

Descripcion:

Vista consolidada de las obligaciones financieras de una persona fisica o juridica, consultada desde `obligacion_obligado`.

Ruta de consulta: `persona -> obligacion_obligado -> obligacion_financiera -> relacion_generadora`

Incluye:

- todas las obligaciones donde la persona figura como obligada
- `porcentaje_responsabilidad` por obligacion
- `monto_responsabilidad = saldo_pendiente * porcentaje_responsabilidad / 100`
- mora dinamica calculada (no persistida) cuando `fecha_vencimiento < fecha_corte`
- dias de gracia y tasa resueltos por `parametro_punitorio`
- `total_con_mora = (saldo_pendiente + mora_calculada) * porcentaje_responsabilidad / 100`
- resumen: `saldo_pendiente_total`, `saldo_vencido`, `saldo_futuro`, `mora_calculada`, `total_con_mora`
- resumen funcional: `saldo_total`, `saldo_locativo`, `saldo_venta`, `saldo_trasladados`, `saldo_otros`
- `grupos_deuda`: lectura jerarquica por grupo funcional, relacion generadora,
  obligaciones y composiciones

Reglas:

- excluye obligaciones con estado `ANULADA` o `REEMPLAZADA`
- incluye `EMITIDA` y `VENCIDA` por defecto
- mora solo si `saldo_pendiente > 0` y
  `fecha_corte > fecha_vencimiento + dias_gracia` resueltos
- `fecha_corte = date.today()` si no se informa; puede configurarse por query param
- la mora de lectura no se persiste; el cargo por mora liquidado al registrar
  pagos se persiste como `PUNITORIO`
- cada `relacion_generadora` se muestra como bloque separado dentro de su grupo

Filtros opcionales:

- `estado`: filtra por `estado_obligacion`
- `tipo_origen`: filtra por `relacion_generadora.tipo_origen`
- `id_origen`: filtra por `relacion_generadora.id_origen`
- `vencidas=True`: solo obligaciones con `fecha_vencimiento < hoy AND saldo_pendiente > 0`
- `fecha_vencimiento_desde`, `fecha_vencimiento_hasta`

Devuelve 404 si la persona no existe.

Devuelve resumen en cero y lista vacia si existe pero no tiene obligaciones.

Nota: la pertenencia de una obligacion a una persona se determina exclusivamente por `obligacion_obligado`. No se infiere desde el contrato de alquiler ni desde la venta. Si `obligacion_obligado` no tiene una fila para esa persona, la obligacion no aparece en esta vista.

Clasificacion funcional V1:

- `contrato_alquiler` -> `LOCATIVO`
- `venta`, `reserva_venta`, `plan_venta` -> `VENTA`
- `factura_servicio` -> `TRASLADADOS`
- conceptos `SERVICIO_TRASLADADO`, `EXPENSA_TRASLADADA` o
  `IMPUESTO_TRASLADADO` como fallback -> `TRASLADADOS`
- resto -> `OTROS`

La respuesta conserva el arreglo plano `obligaciones` por compatibilidad, pero
la lectura funcional recomendada es `grupos_deuda`.

Referencia: `SRV-FIN-016-estado-cuenta-por-persona`

---

## Procesamiento de eventos (Inbox)

El dominio financiero implementa un endpoint de inbox para procesar eventos externos:

`POST /api/v1/financiero/inbox`

Flujo:

- recibe `event_type` y `payload`
- despacha a handler correspondiente
- ejecuta logica de negocio
- devuelve `204`

Eventos soportados:

- `venta_confirmada`
- `contrato_alquiler_activado`

Notas:

- procesamiento sincronico (no worker)
- no hay confirmacion de exito del handler en la respuesta HTTP

---

## 10. Estado de deuda consolidado

Endpoint: `GET /api/v1/financiero/deuda/consolidado`

Vista agregada de deuda global, agrupada por `relacion_generadora` y por `tipo_origen`.

Incluye:

- resumen global: `saldo_pendiente_total`, `saldo_vencido`, `saldo_futuro`, `mora_calculada`, `total_con_mora`
- resumen por `tipo_origen` (ej: `CONTRATO_ALQUILER`, `VENTA`)
- detalle por `relacion_generadora`: saldos, mora y cantidad de obligaciones

Reglas:

- solo obligaciones con `saldo_pendiente > 0`
- excluye `ANULADA` y `REEMPLAZADA`
- mora dinamica calculada con `fecha_corte` (configurable, default `date.today()`)
- el calculo de mora aplica los dias de gracia resueltos por `parametro_punitorio`
- `fecha_corte` no modifica estados persistidos
- filtro opcional por `tipo_origen`
- respuesta sin paginacion (agrega todo en memoria)

Referencia: `SRV-FIN-017-deuda-consolidado`

---

## 11. Simulación de pago por persona

Endpoint: `POST /api/v1/financiero/personas/{id_persona}/simular-pago`

Simula la aplicación de un monto sobre la deuda de una persona sin persistir cambios.

Incluye:

- ordenamiento: obligaciones vencidas primero, luego futuras; dentro de cada grupo por `fecha_vencimiento ASC`
- mora dinámica incluida en `total_a_cubrir` por obligación
- la mora dinamica respeta la tasa y dias de gracia resueltos por
  `parametro_punitorio`
- aplicación secuencial del monto hasta agotarlo o cubrir toda la deuda
- `remanente` si el monto supera la deuda total

Reglas:

- no crea `movimiento_financiero`, `aplicacion_financiera` ni `INTERES_MORA`
- no modifica ningún saldo en DB
- excluye `ANULADA` y `REEMPLAZADA`, solo obligaciones con `saldo_pendiente > 0`
- `fecha_corte` configurable; si se omite usa `date.today()`
- `monto` debe ser mayor que cero (validado en schema)

Referencia: `SRV-FIN-018-simulacion-pago-persona`

---

## 12. Registro de pago por persona V1

Endpoint: `POST /api/v1/financiero/pagos?id_persona={id}`

Aplica un pago contra la deuda de una persona, creando `movimiento_financiero` y `aplicacion_financiera` por cada obligación cubierta.

Reglas:

- si corresponde punitorio por mora al momento del pago, se liquida antes de
  imputar como `composicion_obligacion` `PUNITORIO`; no se crea obligacion nueva
  ni composicion `INTERES_MORA` para esta liquidacion V1
- cada liquidacion positiva de `PUNITORIO` registra una fila trazable en
  `liquidacion_punitorio` vinculada a la obligacion, composicion y
  `uid_pago_grupo`/`codigo_pago_grupo`
- orden de aplicación: obligaciones vencidas primero (por `fecha_vencimiento ASC`), luego futuras
- mora dinámica incluida en `total_a_cubrir`; cuando corresponde liquidacion al
  registrar el pago, el cargo por mora se persiste como `PUNITORIO`
- la mora dinamica respeta la tasa y dias de gracia resueltos por
  `parametro_punitorio`
- la porción aplicada a saldo (`monto_a_saldo`) se registra en `aplicacion_financiera` y actualiza `saldo_pendiente` vía trigger
- si saldo llega a 0 → `CANCELADA`; si reduce parcialmente → `PARCIALMENTE_CANCELADA`
- operación transaccional: si alguna escritura falla, se hace rollback de todas
- todos los movimientos creados por el mismo pago comparten
  `uid_pago_grupo` y `codigo_pago_grupo`, incluso cuando el pago afecta una sola
  obligacion
- con `X-Op-Id`, si ya existen movimientos `PAGO` asociados al mismo `op_id_alta`
  para la persona, se devuelve el resultado persistido sin crear nuevos
  movimientos ni volver a reducir saldos
- antes de devolver el resultado idempotente, valida `id_persona`,
  `monto_ingresado` normalizado a 2 decimales y `fecha_pago` efectiva contra
  el resumen persistido en `observaciones`
- si el mismo `X-Op-Id` se reutiliza con payload distinto, se devuelve
  `IDEMPOTENCY_PAYLOAD_CONFLICT`
- si la operacion original asociada al `X-Op-Id` ya fue revertida, el reintento
  devuelve `PAGO_YA_REVERTIDO` y no recrea pagos ni punitorios
- un reintento idempotente devuelve el mismo `uid_pago_grupo` y
  `codigo_pago_grupo` de la operacion original
- no crea `INTERES_MORA` ni modifica reglas de mora existentes
- `fecha_pago` registrada en `movimiento_financiero`; también usada como `fecha_corte` para mora

Referencia: `SRV-FIN-019-registro-pago-persona`

Integraciones por evento implementadas:

- Comercial -> Financiero:
  - `venta_confirmada`
  - crea o reutiliza `relacion_generadora` con `tipo_origen = 'venta'`
  - materializa una obligacion `CAPITAL_VENTA` para V1 contado
- Locativo -> Financiero:
  - `contrato_alquiler_activado`
  - crea o reutiliza `relacion_generadora` con
    `tipo_origen = 'contrato_alquiler'`
  - materializa un cronograma mensual de obligaciones `CANON_LOCATIVO`
  - omite los periodos mensuales sin condicion economica aplicable
  - no crea `relacion_generadora` si ningun periodo tiene condicion aplicable
  - materializa `obligacion_obligado` para el locatario principal resuelto
    desde el contrato locativo

---

## Procesamiento automatico de eventos (Outbox -> Inbox)

Flujo real implementado:

```text
outbox_event (status = PENDING)
-> worker interno (outbox_to_inbox_worker)
-> InboxEventDispatcher.dispatch(event_type, payload)
-> ejecucion de handler correspondiente
-> actualizacion:
   status = PUBLISHED
   published_at
   processed_at
```

Caracteristicas:

- procesamiento interno (sin HTTP)
- ejecucion sincronica por evento
- el worker continua ante errores
- eventos fallidos permanecen en estado `PENDING`

---

## 13. Reemplazo de obligaciones

Cuando `RegenerarCronogramaLocativoService` regenera el cronograma locativo desde
una `fecha_corte`, el ciclo de vida de las obligaciones sigue este patron:

### Obligaciones reemplazadas

- Las obligaciones elegibles sin pagos cuyo periodo se solapa con `fecha_corte`
  cambian a `estado_obligacion = REEMPLAZADA`.
- Se les asigna `deleted_at` con `CLOCK_TIMESTAMP()` (soft-delete).
- El soft-delete libera el indice unico parcial
  `(id_relacion_generadora, periodo_desde, periodo_hasta) WHERE deleted_at IS NULL`,
  permitiendo insertar nuevas obligaciones para los mismos periodos.
- Los registros no se eliminan fisicamente: quedan trazables en la tabla.

### Obligaciones nuevas

- Se crean con `estado_obligacion = EMITIDA`, igual que en la generacion inicial.
- Aplican la misma logica: prorrateo, vencimiento real, obligado financiero.
- Reutilizan la `relacion_generadora` existente del contrato.
- La idempotencia se garantiza por `ON CONFLICT DO NOTHING` sobre el indice unico parcial.
- Cuando una obligacion vieja y una nueva tienen exactamente el mismo
  `periodo_desde` y `periodo_hasta`, se vinculan con
  `id_obligacion_reemplazante` / `id_obligacion_reemplazada`.
- Si la regeneracion recorta o divide un periodo, no se fuerza vinculo directo
  1 a N.

### Estados que protegen una obligacion del reemplazo

| Estado | Motivo |
|---|---|
| `CANCELADA` | Saldo = 0; no hay nada que regenerar |
| `PARCIALMENTE_CANCELADA` | Tiene pagos; no se puede reescribir |
| Cualquier estado con `aplicacion_financiera` activa | Pago real aplicado; no modificable |
| `ANULADA` | Ya fuera de ciclo activo |
| `REEMPLAZADA` | Ya fue reemplazada por una corrida anterior |

Estados reemplazables (sin pagos): `EMITIDA`, `VENCIDA`, `PENDIENTE_AJUSTE`.

### Ajuste positivo por indice corregido V1

Cuando una obligacion indexada ya tiene pagos o aplicaciones activas y una
correccion del indice aumenta el importe, la obligacion no se reemplaza. En V1
se agrega una composicion positiva dentro de la obligacion base:

- concepto financiero existente: `AJUSTE_INDEXACION`
- `importe_componente` y `saldo_componente` iguales a la diferencia positiva
- no crea una obligacion nueva
- no modifica pagos, aplicaciones, cronograma ni punitorios existentes
- no implementa composiciones negativas
- si la obligacion no tiene aplicaciones financieras activas, se rechaza con
  `OBLIGACION_SIN_PAGOS_APLICADOS` y debe corregirse por regeneracion
- si ya existe una composicion activa `AJUSTE_INDEXACION` en la obligacion, se
  rechaza como duplicado salvo regla futura explicita de recalculo

Endpoint operativo:

`POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/ajuste-indexacion`

Los triggers de `composicion_obligacion` recalculan `importe_total` y
`saldo_pendiente`. Si una obligacion `CANCELADA` vuelve a tener saldo pendiente
por el ajuste y conserva aplicaciones activas, su estado pasa a
`PARCIALMENTE_CANCELADA`.

### Bonificacion por indice corregido V1

Cuando una obligacion indexada ya tiene pagos o aplicaciones activas y una
correccion del indice reduce el importe, la obligacion no se reemplaza y no se
crea una composicion negativa. En V1 se registra una bonificacion como
movimiento financiero de credito y aplicaciones positivas contra saldos
existentes:

- endpoint: `POST /api/v1/financiero/obligaciones/{id_obligacion_financiera}/bonificacion-indexacion`
- crea `movimiento_financiero.tipo_movimiento = BONIFICACION`
- crea `aplicacion_financiera.tipo_aplicacion = BONIFICACION_INDEXACION`
- aplica solo sobre composiciones activas con saldo que correspondan a canon,
  conceptos morables o `AJUSTE_INDEXACION`
- excluye `PUNITORIO`
- no modifica pagos existentes
- no crea obligacion nueva
- no modifica cronograma ni punitorios
- si la obligacion no tiene aplicaciones financieras activas, se rechaza con
  `OBLIGACION_SIN_PAGOS_APLICADOS` y debe corregirse por regeneracion
- no genera saldo a favor persistido; si el importe supera el saldo aplicable,
  se aplica hasta el disponible y se devuelve `remanente_no_aplicado`
- si no existe saldo aplicable, devuelve `SIN_SALDO_APLICABLE`

Los triggers de `aplicacion_financiera` recalculan saldos de composiciones y
obligacion. Luego se recalcula el estado de la obligacion segun saldo:
`CANCELADA` si queda en cero, `PARCIALMENTE_CANCELADA` si queda saldo menor al
importe total, `VENCIDA` si corresponde por fecha, o `EMITIDA`.

### Objetivo del mecanismo

- **Trazabilidad historica**: las obligaciones reemplazadas permanecen en la base con `deleted_at` seteado y son consultables directamente en SQL.
- **Consistencia contable**: los pagos ya realizados no quedan sin referencia; la obligacion sobre la que se imputaron permanece intacta.
- **Idempotencia**: una nueva llamada a regenerar con la misma `fecha_corte` produce el mismo resultado final (exactamente 1 obligacion activa por periodo).

### Pendientes de implementacion

- No existe vinculo bidireccional directo para reemplazos 1 a N cuando la
  regeneracion divide o recorta periodos.
- No existe endpoint de consulta historica de reemplazos (solo acceso directo via SQL).
- No hay regeneracion automatica por cambios de condiciones economicas; requiere
  llamada explicita al endpoint.
- La logica de generacion nueva reutiliza internamente
  `create_cronograma_obligaciones` del flujo de activacion (acoplamiento tecnico
  entre regeneracion y evento `contrato_alquiler_activado`).

---

## 9. Pendientes reales

- transiciones de `relacion_generadora`
- reversion parcial de aplicaciones sueltas
- endpoint autonomo de pagos
- endpoint autonomo de composiciones
- fecha de referencia configurable para estado de cuenta
- relacion fisica entre mora y obligacion base
- clave unica SQL para evitar duplicidad de mora por obligacion base y fecha
- validacion de reutilizacion de `X-Op-Id` con payload distinto
- outbox financiero para estos writes

---

## Limitaciones técnicas actuales

### Atomicidad en integración comercial-financiera

La creación de `relacion_generadora` y `obligacion_financiera`
desde el evento `venta_confirmada` se realiza actualmente dentro
de una única transacción.

Garantía:

- No pueden existir relaciones generadoras sin obligación
  por fallos intermedios en el proceso.

### Idempotencia en creación de relación generadora

La creación de `relacion_generadora` es idempotente a nivel de aplicación
mediante verificación previa por `(tipo_origen, id_origen)`.

Garantía SQL:

- Implementado con indices unicos parciales:
  `relacion_generadora(tipo_origen, id_origen) WHERE deleted_at IS NULL`
  y `obligacion_financiera(id_relacion_generadora, periodo_desde, periodo_hasta)
  WHERE deleted_at IS NULL`.
- El repositorio conserva la verificacion previa y usa conflicto SQL como
  defensa ante retry o concurrencia.

Prioridad:

- Implementada para cronograma locativo-financiero.

## Limitaciones actuales del pipeline de eventos

### Resultado del dispatcher no expuesto

- `InboxEventDispatcher.dispatch()` no devuelve resultado del handler.
- El worker solo detecta:
  - excepciones (errores duros)
  - payloads invalidos basicos

Implicacion:

- no es posible distinguir todos los casos de fallo logico (`AppResult.fail`)
- algunos eventos podrian marcarse como procesados sin verificacion completa de
  exito

Pendiente:

- hacer que `dispatch()` devuelva resultado explicito del handler

Prioridad:

- Media

### Procesamiento sin control de concurrencia

- no se utiliza locking (ej: `SELECT FOR UPDATE SKIP LOCKED`)
- potencial procesamiento duplicado en ejecucion concurrente

Semantica implementada:

- at-least-once
- un evento puede procesarse mas de una vez
- no existe garantia exactly-once
- se depende de la idempotencia de los handlers

Motivo:

- no hay locking ni deduplicacion a nivel `outbox_event`

Mitigacion actual:

- idempotencia en handlers

### Manejo de errores

- errores en handlers no se exponen en HTTP
- no existe persistencia de errores de procesamiento

Pendiente:

- logging estructurado
- tabla de eventos fallidos

### Cronograma locativo mensual implementado

La integracion `contrato_alquiler_activado` genera obligaciones mensuales para
el concepto `CANON_LOCATIVO`.

Reglas implementadas:

- una `obligacion_financiera` por periodo mensual aplicable
- cada obligacion tiene una composicion `CANON_LOCATIVO`
- cada obligacion tiene un `obligacion_obligado` para el locatario principal
- el monto surge de `condicion_economica_alquiler.monto_base`; se cobra completo
  solo cuando el segmento cubre el mes real completo
- si el periodo se recorta por inicio, fin o regeneracion desde mitad de mes,
  el importe se prorratea por dias reales del mes con `ROUND_HALF_UP`
- la condicion aplicable se resuelve contra `periodo_desde`
- si un periodo no tiene condicion aplicable, se omite
- si ningun periodo tiene condicion aplicable, no se crea
  `relacion_generadora`
- si no existe locatario principal, no se genera cronograma completo y el
  handler devuelve error funcional
- si ya existen obligaciones para la relacion generadora, no se duplican
- `moneda = condicion.moneda` o fallback `ARS`
- `fecha_emision = periodo_desde`
- `fecha_vencimiento` deriva de regla locativa; si no hay soporte fisico para
  `dia_vencimiento_canon`, se usa `periodo_desde` como fallback tecnico
- estado inicial: `EMITIDA`

### Limitaciones locativas actuales

- Solo se genera `CANON_LOCATIVO`.
- No se generan expensas, servicios, impuestos ni punitorios.
- No usa periodicidad para dividir periodos; el cronograma implementado es
  mensual.
- Prorratea cambios de condicion dentro del mes y periodos parciales
  (RN-LOC-FIN-005): genera una obligacion por segmento con importe proporcional
  a dias reales del mes.
- Si dos condiciones aplican al mismo `periodo_desde`, gana la condicion con
  `fecha_desde` mas reciente.
- La prevencion de solapamientos depende de validaciones de condiciones
  economicas; debe mantenerse alineada con el dominio locativo.
- La politica de moneda no esta normalizada.
- La regla real de vencimiento queda pendiente; dias de gracia para mora usa
  valor fijo inicial de 5 hasta parametrizacion formal.

## Mora de lectura y punitorio liquidado (V1)

En V1 conviven dos conceptos distintos y no intercambiables:

1. **Mora dinamica de lectura**: se calcula para deuda, estado de cuenta y
   simulacion. No crea composiciones por si sola, no modifica saldos por el
   solo hecho de consultar y no representa deuda accesoria persistida.
2. **PUNITORIO liquidado por pago**: se calcula al registrar un pago cuando
   corresponde. Si el importe es positivo, se persiste como
   `composicion_obligacion` `PUNITORIO`, modifica el importe/saldo persistido
   de la obligacion mediante composicion y triggers, y queda trazado en
   `liquidacion_punitorio`.

La mora dinamica de lectura implica:

- no se generan obligaciones financieras de tipo `INTERES_MORA`
- no se modifica el saldo de la obligacion base por consultar deuda, estado de
  cuenta o simulacion
- no se altera la composicion de la obligacion por el solo calculo de lectura
- el unico efecto persistido del proceso `mora/generar` es el cambio de estado
  `EMITIDA -> VENCIDA`

## Punitorio por pago - Regla funcional implementada

Estado: `IMPLEMENTADO` en `POST /api/v1/financiero/pagos`.

Al registrar pagos, cuando corresponde liquidar mora de forma persistida, el
cargo se modela como `PUNITORIO` dentro de la obligacion base. No se usa
`INTERES_MORA` como componente separado en V1 para esta liquidacion.

Reglas funcionales:

- con `fecha_pago <= fecha_vencimiento + dias_gracia`, el punitorio es cero
- con `fecha_pago > fecha_vencimiento + dias_gracia`, se calcula desde
  `fecha_vencimiento`
- pagos antes o en `fecha_vencimiento` no cortan el tramo de punitorio
- pagos posteriores al vencimiento cortan el tramo; el siguiente calculo parte
  desde la ultima fecha de pago posterior al vencimiento
- la base es saldo morable pendiente, definida por
  `concepto_financiero.aplica_punitorio = true`
- no se calcula punitorio sobre `PUNITORIO` ni sobre accesorios no marcados
- la base morable no depende de hardcodes por codigo de concepto
- el importe liquidado persiste como `composicion_obligacion` `PUNITORIO`
- la persistencia del `PUNITORIO` modifica `importe_total` y
  `saldo_pendiente` mediante composicion y triggers
- cada liquidacion positiva queda trazada en `liquidacion_punitorio`
- si no se paga completo, queda `saldo_componente` pendiente
- puede revertirse solo bajo las reglas de Reversion V1 de pago agrupado

## Evolución prevista

En versiones futuras (Mora V2), se evaluará:

- generación de obligaciones accesorias de mora
- liquidación formal de intereses
- parametrización por contrato/concepto

## Operaciones de pago agrupadas

La vista `GET /api/v1/financiero/pagos/{codigo_pago_grupo}/recibo` es una
constancia interna de pago agrupado. Es una proyeccion read-only basada en
`movimiento_financiero`, `aplicacion_financiera`, `codigo_pago_grupo` y
`uid_pago_grupo`.

La constancia actual:

- no recalcula saldos
- no crea entidad persistida de recibo o comprobante
- no genera comprobante oficial
- no reserva numeracion fiscal
- no tiene validez fiscal
- expone el estado `BORRADOR/CONSULTA` o `ANULADO` si el pago agrupado fue
  revertido

La reversion V1 se realiza con
`POST /api/v1/financiero/pagos/{codigo_pago_grupo}/revertir`. La operacion:

- actua siempre sobre el grupo completo
- solo se permite si no existen operaciones posteriores activas sobre las
  obligaciones o composiciones afectadas por el grupo
- devuelve `PAGO_TIENE_OPERACIONES_POSTERIORES` con HTTP 409 si existen
  movimientos `PAGO`, aplicaciones activas o `liquidacion_punitorio` `ACTIVA`
  posteriores
- marca movimientos `PAGO` como `ANULADO`
- soft-deletea aplicaciones para excluirlas de saldos
- anula las filas `liquidacion_punitorio` del grupo
- reduce la composicion `PUNITORIO` por el importe trazado en esas
  liquidaciones
- recalcula estados de obligaciones luego de los triggers de saldo
- no genera comprobante fiscal ni modifica cronogramas
- no recomputa historia de punitorio ni recalcula tramos moratorios
- si el grupo ya fue revertido, la repeticion conserva comportamiento
  idempotente como `YA_ANULADO`

El modelo queda preparado para una futura entidad formal, por ejemplo
`comprobante_pago` o `comprobante_financiero`, con numeracion, estado fiscal,
anulacion, emision PDF e integracion fiscal si corresponde.

El modelo financiero expone lectura de pagos agrupados por
`uid_pago_grupo/codigo_pago_grupo` para consulta por persona y detalle por
codigo, sin efectos en saldos ni cronograma. El detalle por codigo informa
`estado_pago_grupo = ANULADO` cuando todos los movimientos `PAGO` del grupo
estan anulados.
