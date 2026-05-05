# MODELO-FINANCIERO-FIN - Modelo financiero implementado

## Estado del documento

- estado: `IMPLEMENTADO PARCIAL / ALINEADO A BACKEND`
- dominio: `financiero`
- ultima revision: `2026-04-30`
- alcance implementado: `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `concepto_financiero`, `movimiento_financiero`, `aplicacion_financiera`, consulta de deuda consolidada y generacion de mora diaria.
- no modifica SQL
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

Implementado:

- `POST /api/v1/financiero/imputaciones`
- una imputacion crea un movimiento tipo `PAGO`
- una imputacion puede generar una o varias aplicaciones
- cada aplicacion puede apuntar a una composicion
- `orden_aplicacion` refleja el orden de distribucion aplicado

No implementado:

- endpoint autonomo de pagos
- reversion de imputaciones
- estado persistido de aplicacion

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
- tasa diaria default centralizada: `TASA_DIARIA_MORA_DEFAULT = Decimal("0.001")`
- dias de gracia fijos iniciales: `5`
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

Limitacion:

- tasa default centralizada hasta que exista parametro formal persistido/administrado.
- dias de gracia fijo hasta que exista politica parametrizable.

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
- dias de gracia fijos iniciales para mora: 5
- `total_con_mora = (saldo_pendiente + mora_calculada) * porcentaje_responsabilidad / 100`
- resumen: `saldo_pendiente_total`, `saldo_vencido`, `saldo_futuro`, `mora_calculada`, `total_con_mora`

Reglas:

- excluye obligaciones con estado `ANULADA` o `REEMPLAZADA`
- incluye `EMITIDA` y `VENCIDA` por defecto
- mora solo si `saldo_pendiente > 0` y
  `fecha_corte > fecha_vencimiento + 5 dias de gracia`
- `fecha_corte = date.today()` — no configurable en V1
- mora no se persiste

Filtros opcionales:

- `estado`: filtra por `estado_obligacion`
- `tipo_origen`: filtra por `relacion_generadora.tipo_origen`
- `id_origen`: filtra por `relacion_generadora.id_origen`
- `vencidas=True`: solo obligaciones con `fecha_vencimiento < hoy AND saldo_pendiente > 0`
- `fecha_vencimiento_desde`, `fecha_vencimiento_hasta`

Devuelve 404 si la persona no existe.

Devuelve resumen en cero y lista vacia si existe pero no tiene obligaciones.

Nota: la pertenencia de una obligacion a una persona se determina exclusivamente por `obligacion_obligado`. No se infiere desde el contrato de alquiler ni desde la venta. Si `obligacion_obligado` no tiene una fila para esa persona, la obligacion no aparece en esta vista.

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
- el calculo de mora aplica 5 dias de gracia no persistidos
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
- la mora dinamica respeta 5 dias de gracia no persistidos
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
- orden de aplicación: obligaciones vencidas primero (por `fecha_vencimiento ASC`), luego futuras
- mora dinámica incluida en `total_a_cubrir`; la porción de mora consume del monto pero no se persiste como componente
- la mora dinamica respeta 5 dias de gracia no persistidos
- la porción aplicada a saldo (`monto_a_saldo`) se registra en `aplicacion_financiera` y actualiza `saldo_pendiente` vía trigger
- si saldo llega a 0 → `CANCELADA`; si reduce parcialmente → `PARCIALMENTE_CANCELADA`
- operación transaccional: si alguna escritura falla, se hace rollback de todas
- con `X-Op-Id`, si ya existen movimientos `PAGO` asociados al mismo `op_id_alta`
  para la persona, se devuelve el resultado persistido sin crear nuevos
  movimientos ni volver a reducir saldos
- idempotencia V1 evita duplicados, pero no garantiza equivalencia del request;
  V2 deberá validar hash o campos clave del payload
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

- Las obligaciones elegibles (futuras sin pagos) cambian a `estado_obligacion = REEMPLAZADA`.
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

### Estados que protegen una obligacion del reemplazo

| Estado | Motivo |
|---|---|
| `CANCELADA` | Saldo = 0; no hay nada que regenerar |
| `PARCIALMENTE_CANCELADA` | Tiene pagos; no se puede reescribir |
| Cualquier estado con `aplicacion_financiera` activa | Pago real aplicado; no modificable |
| `ANULADA` | Ya fuera de ciclo activo |
| `REEMPLAZADA` | Ya fue reemplazada por una corrida anterior |

Estados reemplazables (sin pagos): `EMITIDA`, `VENCIDA`, `PENDIENTE_AJUSTE`.

### Objetivo del mecanismo

- **Trazabilidad historica**: las obligaciones reemplazadas permanecen en la base con `deleted_at` seteado y son consultables directamente en SQL.
- **Consistencia contable**: los pagos ya realizados no quedan sin referencia; la obligacion sobre la que se imputaron permanece intacta.
- **Idempotencia**: una nueva llamada a regenerar con la misma `fecha_corte` produce el mismo resultado final (exactamente 1 obligacion activa por periodo).

### Pendientes de implementacion

- Los campos `id_obligacion_reemplazada` e `id_obligacion_reemplazante` existen
  en el esquema SQL de `obligacion_financiera` pero no se vinculan aun.
  El vinculo bidireccional queda pendiente para una version futura que requiera
  trazabilidad explicita de la cadena de reemplazo.
- No existe endpoint de consulta historica de reemplazos (solo acceso directo via SQL).
- No hay regeneracion automatica por cambios de condiciones economicas; requiere
  llamada explicita al endpoint.
- La logica de generacion nueva reutiliza internamente
  `create_cronograma_obligaciones` del flujo de activacion (acoplamiento tecnico
  entre regeneracion y evento `contrato_alquiler_activado`).

---

## 9. Pendientes reales

- transiciones de `relacion_generadora`
- reversion de imputaciones
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
- el monto surge de `condicion_economica_alquiler.monto_base`
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
- Prorratea cambios de condición dentro del mes (RN-LOC-FIN-005): genera una obligación por segmento con importe proporcional a días reales del mes.
- Si dos condiciones aplican al mismo `periodo_desde`, gana la condicion con
  `fecha_desde` mas reciente.
- La prevencion de solapamientos depende de validaciones de condiciones
  economicas; debe mantenerse alineada con el dominio locativo.
- La politica de moneda no esta normalizada.
- La regla real de vencimiento queda pendiente; dias de gracia para mora usa
  valor fijo inicial de 5 hasta parametrizacion formal.

## Mora — Estado actual (V1)

La mora V1 es dinámica y de lectura. No representa aún deuda accesoria persistida.

Esto implica:

- No se generan obligaciones financieras de tipo INTERES_MORA.
- No se modifica el saldo de la obligación base.
- No se altera la composición de la obligación.
- La mora se calcula dinámicamente en consultas (estado de cuenta, deuda).
- El único efecto persistido es el cambio de estado EMITIDA → VENCIDA.

## Punitorio por pago - Regla funcional implementada

Estado: `IMPLEMENTADO` en `POST /api/v1/financiero/pagos`.

Al registrar pagos, cuando corresponde mora persistida, el cargo por mora se
modela como `PUNITORIO` dentro de la obligacion base. No se usa `INTERES_MORA`
como componente separado en V1 para esta liquidacion.

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
- si no se paga completo, queda `saldo_componente` pendiente

## Evolución prevista

En versiones futuras (Mora V2), se evaluará:

- generación de obligaciones accesorias de mora
- liquidación formal de intereses
- parametrización por contrato/concepto
