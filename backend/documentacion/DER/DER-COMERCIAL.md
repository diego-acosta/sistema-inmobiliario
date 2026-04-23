# DER Comercial (Adaptado)

## Alcance y criterio

Este DER adapta el modelo original del dominio Comercial a la implementacion real del sistema.

Fuente de verdad usada:

- SQL real: `backend/database/schema_inmobiliaria_20260418.sql`
- backend real: routers, services y repositories existentes
- arquitectura y servicios vigentes: `DEV-ARCH-COM-001.md` y `DEV-SRV` del dominio

Criterio aplicado:

- el DER original se usa solo como referencia conceptual
- el SQL define la estructura valida
- el backend define el contrato operativo hoy disponible
- no se incorporan entidades no materializadas en DB
- no se eleva una tabla de relacion a entidad de negocio si su funcion real es solo vincular objetos

## Entidades

### `reserva_venta`

Descripcion:
- etapa comercial previa y opcional a la venta

Atributos clave:
- `id_reserva_venta`
- `codigo_reserva`
- `fecha_reserva`
- `estado_reserva`
- `fecha_vencimiento`
- `observaciones`

Observaciones:
- incluye metadatos `CORE-EF`
- se vincula con inmuebles o unidades funcionales por `reserva_venta_objeto_inmobiliario`
- puede existir sin que luego se materialice una venta

### `venta`

Descripcion:
- operacion comercial principal del circuito de compraventa

Atributos clave:
- `id_venta`
- `id_reserva_venta` nullable
- `codigo_venta`
- `fecha_venta`
- `estado_venta`
- `monto_total`
- `observaciones`

Observaciones:
- incluye metadatos `CORE-EF`
- es la raiz comercial efectiva del modelo
- puede existir con o sin reserva previa
- concentra la semantica de la operacion, los sujetos contextuales y los objetos comercializados

### `instrumento_compraventa`

Descripcion:
- instrumento juridico o documental emitido en el contexto de una venta

Atributos clave:
- `id_instrumento_compraventa`
- `id_venta`
- `tipo_instrumento`
- `numero_instrumento`
- `fecha_instrumento`
- `estado_instrumento`
- `observaciones`

Observaciones:
- depende de `venta`
- no reemplaza a la venta como entidad principal
- formaliza, documenta o instrumenta la operacion, pero no la constituye por si mismo

### `cesion`

Descripcion:
- evento comercial que transfiere o reorganiza posicion sobre una venta existente

Atributos clave:
- `id_cesion`
- `id_venta`
- `fecha_cesion`
- `tipo_cesion`
- `observaciones`

Observaciones:
- el SQL real la modela como entidad simple dependiente de `venta`
- no existen hoy FKs a instrumentos ni tablas detalle por objeto

### `escrituracion`

Descripcion:
- evento de cierre formal o registral asociado a una venta

Atributos clave:
- `id_escrituracion`
- `id_venta`
- `fecha_escrituracion`
- `numero_escritura`
- `observaciones`

Observaciones:
- el SQL real la modela como entidad simple dependiente de `venta`
- no existe hoy FK a `instrumento_compraventa`

### `rescision_venta`

Descripcion:
- evento de cierre anomalo o terminacion anticipada de una venta

Atributos clave:
- `id_rescision_venta`
- `id_venta`
- `fecha_rescision`
- `motivo`
- `observaciones`

Observaciones:
- depende de `venta`
- no existe hoy FK a instrumentos ni capa backend implementada

### `cliente_comprador`

Descripcion:
- rol comercial persistido que identifica a una `persona` habilitada o reconocida en contexto de compraventa

Atributos clave:
- `id_cliente_comprador`
- `id_persona`
- `codigo_cliente_comprador`
- `fecha_alta`
- `estado_cliente_comprador`
- `observaciones`

Observaciones:
- existe fisicamente en SQL
- no tiene hoy API propia
- no debe leerse como entidad base de `personas`
- su semantica pertenece a `comercial`, aunque su persistencia actual sea heredada y referencie a `persona`

### `documento_logico`

Descripcion:
- documento transversal del dominio Documental reutilizado por Comercial

Atributos clave:
- `id_documento_logico`
- `id_tipo_documental`
- `codigo_documento`
- `titulo_documento`
- `estado_documento`
- `origen_documento`

Observaciones:
- no es entidad propia de Comercial
- se incluye porque hoy es el soporte documental real disponible

### `documento_entidad`

Descripcion:
- asociacion polimorfica entre `documento_logico` y entidades del sistema

Atributos clave:
- `id_documento_entidad`
- `id_documento_logico`
- `tipo_entidad`
- `id_entidad`
- `tipo_relacion`
- `fecha_asociacion`

Observaciones:
- para Comercial, el trigger SQL admite `venta`, `cesion` y `escrituracion`
- no admite hoy `reserva_venta`, `rescision_venta` ni `instrumento_compraventa`

## Relaciones

### Entre entidades comerciales

- `reserva_venta` `0..1 -> 0..N` `venta`
  Nota: la FK esta en `venta.id_reserva_venta`. El SQL no impone unicidad 1:1.
  Nota de implementacion actual: la conversion operativa `reserva_venta -> venta` valida en backend que no exista mas de una `venta` no eliminada para la misma reserva, aunque esa unicidad no este materializada como constraint SQL.

- `venta` `1 -> 0..N` `instrumento_compraventa`
  Cardinalidad inversa: cada `instrumento_compraventa` pertenece a exactamente `1` `venta`.

- `venta` `1 -> 0..N` `cesion`
  Cardinalidad inversa: cada `cesion` pertenece a exactamente `1` `venta`.

- `venta` `1 -> 0..N` `escrituracion`
  Cardinalidad inversa: cada `escrituracion` pertenece a exactamente `1` `venta`.

- `venta` `1 -> 0..N` `rescision_venta`
  Cardinalidad inversa: cada `rescision_venta` pertenece a exactamente `1` `venta`.

### Relaciones materializadas con Inmobiliario

Estas tablas existen en SQL, pero su funcion real es vincular una entidad comercial con uno o mas objetos inmobiliarios. No se modelan aqui como entidades de negocio autonomas.

#### `reserva_venta_objeto_inmobiliario`

Rol:
- materializa la relacion `reserva_venta -> inmueble | unidad_funcional`

Atributos clave:
- `id_reserva_venta_objeto`
- `id_reserva_venta`
- `id_inmueble` nullable
- `id_unidad_funcional` nullable
- `observaciones`

Reglas:
- aplica regla XOR: debe informar `id_inmueble` o `id_unidad_funcional`, nunca ambos
- no debe repetirse el mismo objeto dentro de una misma reserva activa, ni por `id_inmueble` ni por `id_unidad_funcional`
- representa el detalle multiobjeto de una reserva
- su semantica depende de `reserva_venta`; no define un proceso comercial independiente

Cardinalidad:
- `reserva_venta` `1 -> 1..N` `reserva_venta_objeto_inmobiliario`
- cada fila de `reserva_venta_objeto_inmobiliario` refiere a exactamente `1` `reserva_venta`
- cada fila de `reserva_venta_objeto_inmobiliario` refiere a exactamente `1` objeto inmobiliario efectivo:
  - `1` `inmueble`, o
  - `1` `unidad_funcional`

#### `venta_objeto_inmobiliario`

Rol:
- materializa la relacion `venta -> inmueble | unidad_funcional`

Atributos clave:
- `id_venta_objeto`
- `id_venta`
- `id_inmueble` nullable
- `id_unidad_funcional` nullable
- `precio_asignado`
- `observaciones`

Reglas:
- aplica regla XOR: debe informar `id_inmueble` o `id_unidad_funcional`, nunca ambos
- representa el detalle multiobjeto de una venta
- su semantica depende de `venta`; no define un proceso comercial independiente

Cardinalidad:
- `venta` `1 -> 0..N` `venta_objeto_inmobiliario`
- cada fila de `venta_objeto_inmobiliario` refiere a exactamente `1` `venta`
- cada fila de `venta_objeto_inmobiliario` refiere a exactamente `1` objeto inmobiliario efectivo:
  - `1` `inmueble`, o
  - `1` `unidad_funcional`

#### `instrumento_objeto_inmobiliario`

Rol:
- materializa la relacion `instrumento_compraventa -> inmueble | unidad_funcional`

Atributos clave:
- `id_instrumento_objeto`
- `id_instrumento_compraventa`
- `id_inmueble` nullable
- `id_unidad_funcional` nullable
- `observaciones`

Reglas:
- aplica regla XOR igual que `venta_objeto_inmobiliario`
- en SQL real apunta directo a `inmueble` o `unidad_funcional`
- su semantica depende de `instrumento_compraventa`; no constituye entidad comercial principal

Cardinalidad:
- `instrumento_compraventa` `1 -> 0..N` `instrumento_objeto_inmobiliario`
- cada fila de `instrumento_objeto_inmobiliario` refiere a exactamente `1` `instrumento_compraventa`
- cada fila de `instrumento_objeto_inmobiliario` refiere a exactamente `1` objeto inmobiliario efectivo:
  - `1` `inmueble`, o
  - `1` `unidad_funcional`

### Con Personas

- `cliente_comprador` `N -> 1` `persona`

- `relacion_persona_rol` referencia polimorficamente:
  - `reserva_venta`
  - `venta`
  - `cesion`
  - `escrituracion`

Observacion:
- esta relacion existe hoy en backend desde `personas`, no desde una API comercial propia
- semanticamente los roles comerciales pertenecen a `comercial`, aunque hoy se persistan por soporte transversal
- `reserva_venta` no tiene hoy FK directa a `persona` ni a `cliente_comprador`
- si una reserva necesita sujetos intervinientes, hoy solo pueden leerse de forma indirecta por `relacion_persona_rol`
- `cliente_comprador` es una condicion o rol comercial de la persona, no un segundo sujeto base

### Con Inmobiliario

- `reserva_venta` se vincula con `inmueble` o `unidad_funcional` a traves de `reserva_venta_objeto_inmobiliario`
- `venta` se vincula con `inmueble` o `unidad_funcional` a traves de `venta_objeto_inmobiliario`
- `instrumento_compraventa` se vincula con `inmueble` o `unidad_funcional` a traves de `instrumento_objeto_inmobiliario`
- `reserva_venta` no tiene hoy una relacion materializada con `inmueble` o `unidad_funcional`

Observacion:
- ambos detalles usan patron XOR y no una superentidad abstracta `objeto_inmobiliario`
- por eso no puede declararse hoy una cardinalidad estructural `reserva_venta <-> objeto inmobiliario`; esa asociacion no existe en SQL

### Con Documental

- `documento_entidad` `N -> 1` `documento_logico`
- `documento_entidad.tipo_entidad` puede apuntar a:
  - `venta`
  - `cesion`
  - `escrituracion`

### Con Financiero

- `relacion_generadora` admite `venta` como `tipo_origen`

Observacion:
- no forma parte del nucleo comercial, pero es una dependencia real del modelo fisico

## Modelo logico

### Venta vs instrumento de compraventa

`venta` y `instrumento_compraventa` no son equivalentes.

Rol de `venta`:
- es la operacion comercial principal
- define el contexto semantico de la compraventa
- concentra estado comercial, monto total, sujetos contextuales y relacion con objetos inmobiliarios

Rol de `instrumento_compraventa`:
- documenta, formaliza o instrumenta una venta ya existente
- puede haber varios instrumentos para una misma venta
- su alcance sobre inmuebles o unidades se detalla por `instrumento_objeto_inmobiliario`

Conclusion:
- la venta gobierna la operacion
- el instrumento gobierna la formalizacion documental o juridica de partes de esa operacion

### Organizacion general

El modelo comercial real se organiza alrededor de `venta`.

Secuencia estructural:

1. `reserva_venta` puede existir como etapa previa opcional.
2. `reserva_venta_objeto_inmobiliario` resuelve el caracter multiobjeto de la reserva como relacion materializada.
3. `venta` es la raiz comercial efectiva del circuito.
4. `venta_objeto_inmobiliario` resuelve el caracter multiobjeto de la operacion como relacion materializada.
5. `instrumento_compraventa` documenta juridica o comercialmente la venta.
6. `instrumento_objeto_inmobiliario` define sobre que inmueble o unidad impacta cada instrumento.
7. `cesion`, `escrituracion` y `rescision_venta` son eventos o subprocesos posteriores que dependen de `venta`.

Conexiones transversales:

- las personas intervinientes no cuelgan de FKs directas en `venta`; hoy se vinculan por `relacion_persona_rol`
- los objetos comerciales se resuelven contra `inmueble` o `unidad_funcional`
- la documentacion asociada se resuelve con `documento_logico` + `documento_entidad`

## Modelo de estados

Esta seccion refleja el estado operativamente esperable segun `DEV-SRV`, sin afirmar que hoy exista enforcement completo en backend o restricciones SQL mas alla de la persistencia del valor.

Regla general:

- los estados no deben interpretarse como texto libre
- deben resolverse mediante catalogo controlado o enum equivalente en la futura capa API
- el SQL actual persiste valores de estado, pero el contrato operativo deberia restringirlos a vocabulario gobernado por el dominio

### `reserva_venta`

Campo SQL:
- `estado_reserva`

Estados documentados relevantes:
- `borrador`
- `activa`
- `confirmada`
- `cancelada`
- `vencida`
- `finalizada`

Lectura de modelo:
- `borrador`: reserva aun editable o incompleta
- `activa`: reserva vigente dentro de su ventana comercial
- `confirmada`: reserva consolidada o absorbida por el flujo comercial esperado
- `cancelada`: reserva anulada antes de cierre
- `vencida`: reserva fuera de vigencia
- `finalizada`: reserva cerrada por conversion valida a venta

Regla de implementacion:
- `estado_reserva` debe mapearse a un catalogo o enum controlado; no corresponde aceptar strings arbitrarios

### `venta`

Campo SQL:
- `estado_venta`

Estados documentados relevantes:
- `borrador`
- `activa`
- `confirmada`
- `cancelada`
- `en_proceso`
- `finalizada`

Lectura de modelo:
- `borrador`: operacion iniciada sin consolidacion plena
- `activa`: venta vigente en tratamiento comercial
- `confirmada`: venta validada comercialmente
- `en_proceso`: venta con ejecucion operativa o documental en curso
- `finalizada`: venta cerrada segun politica del dominio
- `cancelada`: venta anulada

Regla de implementacion:
- `estado_venta` debe mapearse a un catalogo o enum controlado; no corresponde aceptar strings arbitrarios

### `cesion`

Campo SQL:
- no existe hoy columna de estado dedicada en la tabla

Estados documentados relevantes:
- `registrada`
- `activa`
- `cancelada`

Lectura de modelo:
- el servicio documentado supone estado de ciclo para la cesion
- el modelo fisico actual no lo materializa como atributo propio
- por eso el estado de `cesion` hoy es semantico y documental, no estructural

Regla de implementacion:
- si la API expone estado de `cesion`, debe hacerlo contra catalogo o enum controlado y no como texto libre

### `escrituracion`

Campo SQL:
- no existe hoy columna de estado dedicada en la tabla

Estados documentados relevantes:
- `pendiente`
- `en_proceso`
- `escriturada`

Lectura de modelo:
- el dominio distingue espera, tramitacion y formalizacion final
- el SQL actual solo persiste datos del acto, no un estado explicito

Regla de implementacion:
- si la API expone estado de `escrituracion`, debe hacerlo contra catalogo o enum controlado y no como texto libre

## Reglas temporales

### Vigencias y fechas base

- `reserva_venta.fecha_reserva` marca el inicio temporal de la reserva
- `reserva_venta.fecha_vencimiento` define su limite de vigencia cuando exista
- `venta.fecha_venta` marca la fecha operativa de la compraventa
- `instrumento_compraventa.fecha_instrumento` marca la fecha del acto documental o juridico
- `cesion.fecha_cesion` marca la fecha del evento de cesion
- `escrituracion.fecha_escrituracion` marca la fecha del acto escriturario
- `rescision_venta.fecha_rescision` marca la fecha del cierre anomalo o terminacion anticipada

### Restricciones temporales materializadas

- `reserva_venta` tiene una restriccion SQL explicita: `fecha_vencimiento` debe ser mayor o igual a `fecha_reserva`
- fuera de esa validacion, el SQL actual no materializa reglas de orden temporal entre reserva, venta, cesion, escrituracion y rescision

### Restricciones temporales no materializadas

- no existe hoy constraint SQL que impida vender fuera de una vigencia de reserva
- no existe hoy constraint SQL que fuerce correspondencia cronologica entre `fecha_venta` y `fecha_instrumento`
- no existe hoy constraint SQL que impida coexistencia temporal entre `escrituracion` y `rescision_venta`
- no existe hoy control de solapamiento temporal por objeto inmobiliario en el bloque comercial

### Observaciones para implementacion backend

- la futura API deberia tratar las fechas como parte del contrato semantico del flujo y no solo como campos informativos
- las transiciones de estado deberian validarse con criterio temporal consistente
- si el negocio requiere exclusiones temporales por objeto o por sujeto comercial, eso debera resolverse en reglas de aplicacion o en evolucion del esquema

## Ownership

- `comercial` es dueño semantico de:
  - `reserva_venta`
  - `venta`
  - `instrumento_compraventa`
  - `cesion`
  - `escrituracion`
  - `rescision_venta`
  - `cliente_comprador`
- `personas` provee la identidad base de `persona`, pero no define la semantica comercial de cliente ni de los roles de compraventa
- `inmobiliario` provee el objeto inmobiliario sobre el que recae la operacion: `inmueble` o `unidad_funcional`
- `financiero` puede recibir origenes comerciales, pero no debe absorber la semantica de reserva, venta, cesion o escrituracion
- `documental` provee soporte documental transversal; no redefine la operacion comercial

## Flujo comercial

Flujo base hoy soportado por el modelo:

1. una `persona` puede asumir semantica comercial como `cliente_comprador`
2. opcionalmente se registra una `reserva_venta`
3. se crea una `venta`, con o sin referencia a reserva previa
4. la reserva se vincula con inmuebles o unidades funcionales por `reserva_venta_objeto_inmobiliario`
5. la venta se vincula con inmuebles o unidades funcionales por `venta_objeto_inmobiliario`
6. sobre la venta pueden emitirse uno o mas `instrumento_compraventa`
7. cada instrumento puede vincular los inmuebles o unidades alcanzados por `instrumento_objeto_inmobiliario`
8. como eventos posteriores de la venta pueden aparecer `cesion`, `escrituracion` o `rescision_venta`
9. los sujetos intervinientes del circuito hoy se asocian por `relacion_persona_rol`
10. la documentacion transversal disponible hoy se asocia por `documento_entidad` en los tipos admitidos por SQL

Lectura de implementacion:

- el flujo esta soportado estructuralmente en SQL
- no existe todavia API comercial propia que lo exponga como contrato operativo integral
- el backend actual solo toca parte del flujo de forma indirecta desde `personas`

## Ajustes realizados

### Diferencias con el DER original

- se normalizo naming al proyecto actual:
  - `terreno` del DER original se adapta a `inmueble`
  - donde aplica subdivision, el objeto tambien puede ser `unidad_funcional`

- se removieron entidades no materializadas en SQL:
  - `venta_condicion_comercial`
  - `esquema_financiamiento`
  - `documento_comercial`
  - `operacion_comercial`
  - `reserva_comercial`
  - `interaccion_comercial`

- se simplificaron relaciones que en el DER original estaban mas cargadas:
  - `cesion` no tiene hoy `id_instrumento_base` ni `id_instrumento_nuevo`
  - `escrituracion` no tiene hoy FK a `instrumento_compraventa`
  - `rescision_venta` no tiene hoy FK a `instrumento_compraventa`

- se corrigio una diferencia estructural importante:
  - en el DER original, `instrumento_objeto_inmobiliario` podia colgar de `venta_objeto_inmobiliario`
  - en SQL real cuelga directo de `inmueble` o `unidad_funcional`

- se ajusto cardinalidad de `reserva_venta -> venta`:
  - el DER original proponia 0..1 a 0..1
  - el SQL real solo define FK nullable en `venta`; no hay unicidad sobre `id_reserva_venta`

- `cliente_comprador` se conserva como rol comercial persistido, no como entidad base de `personas`

- `reserva_venta_objeto_inmobiliario` se incorpora como relacion materializada multiobjeto para que la reserva tenga trazabilidad estructural sobre el objeto reservado
- `venta_objeto_inmobiliario` e `instrumento_objeto_inmobiliario` se reinterpretan como relaciones materializadas y no como entidades de negocio autonomas

### Diferencias con el backend

- no existe hoy router, schema, service ni repository del dominio Comercial
- no existe `DEV-API` comercial implementado
- el unico uso operativo backend del nucleo comercial hoy visible es indirecto:
  - validacion desde `personas` sobre `reserva_venta`, `venta`, `cesion` y `escrituracion`
  - soporte de `relacion_generadora` para `venta`

## Notas importantes

- `venta` es la entidad comercial principal real del modelo fisico.
- `instrumento_compraventa` no reemplaza a `venta`; la instrumenta.
- `reserva_venta` ya cuenta con detalle multiobjeto por `reserva_venta_objeto_inmobiliario`.
- una venta valida, desde la semantica de dominio, deberia recaer sobre al menos un objeto; eso hoy no esta reforzado por una restriccion SQL directa.
- `documento_entidad` no cubre todo el bloque comercial:
  - si se necesita documentar `reserva_venta`, `rescision_venta` o `instrumento_compraventa`, hay que ajustar el modelo o el trigger polimorfico
- los sujetos comerciales siguen resueltos por soporte transversal:
  - `relacion_persona_rol`
  - `rol_participacion`
- `cliente_comprador` pertenece semanticamente a `comercial`, aunque hoy persista con referencia a `persona`
- los estados documentados de `cesion` y `escrituracion` no estan materializados como columna propia en SQL
- este DER describe el estado confiable actual del dominio Comercial, no el estado ideal o totalmente documentado en el DER original
- No todas las etapas del flujo son obligatorias.
El sistema debe soportar:
  - operaciones sin instrumento
  - ventas sin cesión
  - escrituración directa
