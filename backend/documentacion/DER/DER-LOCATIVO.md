# DER Locativo (Consolidado)

## Alcance y criterio

Este DER consolida el nucleo contractual del dominio `locativo` a partir de la evidencia disponible hoy en el workspace.

Fuente de verdad usada:

- SQL real: `backend/database/schema_inmobiliaria_20260418.sql`
- DER de origen aportado por negocio:
  - `TRX-DER-001 - DER Dominio Transaccional`
  - `SYS-DER-001 - DER Global Unificado`
- servicios y catalogos vigentes: `backend/documentacion/DEV-SRV/dominios/locativo`
- delimitacion arquitectonica observable en:
  - `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`
  - `backend/documentacion/DEV-ARCH/dominios/analitico/DEV-ARCH-ANA-001.md`
  - `backend/documentacion/DEV-ARCH/DB-CHANGELOG-INM-002.md`

Criterio aplicado:

- el SQL vigente prevalece sobre el PDF y sobre formulaciones conceptuales de `DEV-SRV` cuando exista drift
- este DER no define endpoints ni implica backend locativo ya materializado
- se modela `contrato_alquiler` como raiz juridica del dominio locativo
- se conservan solo entidades fisicamente materializadas en SQL
- las relaciones transversales se documentan como soporte, no como ownership local del dominio
- cuando `DEV-SRV` usa naming conceptual distinto del SQL, el DER fija el nombre persistido vigente y deja trazabilidad del alias funcional

Alcance de este documento:

- `contrato_alquiler`
- `contrato_objeto_locativo`
- `condicion_economica_alquiler`
- `ajuste_alquiler`
- `modificacion_locativa`
- `rescision_finalizacion_alquiler`
- `entrega_restitucion_inmueble`

Entidades relacionadas pero fuera del foco central de este DER:

- `cartera_locativa`
- `solicitud_alquiler`
- `reserva_locativa`
- `relacion_persona_rol`
- `documento_entidad`
- `emision_numeracion`
- `relacion_generadora`
- `disponibilidad`
- `ocupacion`

## Drifts consolidados

### `condicion_locativa` -> `condicion_economica_alquiler`

`DEV-SRV` usa varias veces la expresion `condicion_locativa` como nombre funcional del bloque, pero la tabla real materializada en SQL es `condicion_economica_alquiler`.

Decision de este DER:

- el nombre estructural valido para futura `DEV-API` es `condicion_economica_alquiler`
- `condicion_locativa` queda solo como alias funcional heredado de `DEV-SRV`

### `id_terreno` -> `id_inmueble`

Los PDFs base todavia muestran variantes del patron `id_terreno | id_unidad_funcional` para `contrato_objeto_locativo`.

Decision de este DER:

- el modelo vigente usa `id_inmueble | id_unidad_funcional`
- no se conserva `id_terreno` como atributo vigente del nucleo locativo actual

### renovacion y rescision conceptual vs estructura actual

`DEV-SRV` menciona `contrato_renovacion` y `contrato_rescision` como artefactos funcionales. Esas entidades no existen como tablas propias en SQL.

Decision de este DER:

- la renovacion sustancial se materializa hoy por autorrelacion de `contrato_alquiler.id_contrato_anterior`
- la rescision o finalizacion anticipada se materializa por `rescision_finalizacion_alquiler`
- no se crean entidades adicionales mientras no existan en SQL

### PDF historico mas rico que SQL actual

Los PDFs describen variantes mas ricas para varias entidades locativas. El SQL vigente hoy es mas compacto.

Casos relevantes:

- `contrato_alquiler` en PDF incluye campos como `plazo_contractual` o `destino_contrato`; el SQL vigente no los materializa
- `ajuste_alquiler` en PDF incluye FK a condicion, indices y estados; el SQL vigente solo persiste el ajuste basico sobre contrato
- `modificacion_locativa`, `rescision_finalizacion_alquiler` y `entrega_restitucion_inmueble` tienen en PDF mas detalle operativo que el SQL actual no persiste

Este DER consolida exclusivamente el shape realmente materializado en SQL.

## Entidades

### `contrato_alquiler`

Descripcion:

- entidad juridica principal del dominio locativo
- expresa el vinculo contractual de alquiler y ordena su ciclo de vida

Atributos clave:

- `id_contrato_alquiler`
- `id_reserva_locativa` nullable
- `id_cartera_locativa` nullable
- `id_contrato_anterior` nullable
- `codigo_contrato`
- `fecha_inicio`
- `fecha_fin`
- `estado_contrato`
- `observaciones`

Observaciones:

- incluye metadatos `CORE-EF`
- tiene `CHECK` de coherencia temporal: `fecha_fin >= fecha_inicio` cuando `fecha_fin` no es null
- `id_contrato_anterior` materializa continuidad historica entre contratos
- `id_reserva_locativa` permite trazabilidad desde reserva, pero no materializa por si solo unicidad 1:1
- `id_cartera_locativa` quedo alineado al modelo actual por `fk_ca_cartera`
- no materializa localmente partes contractuales; los intervinientes se resuelven por `relacion_persona_rol`
- no materializa localmente reglas economicas detalladas; eso se descompone en entidades hijas

### `contrato_objeto_locativo`

Descripcion:

- detalle multiobjeto del contrato de alquiler
- vincula `contrato_alquiler` con un `inmueble` o una `unidad_funcional`

Atributos clave:

- `id_contrato_objeto`
- `id_contrato_alquiler`
- `id_inmueble` nullable
- `id_unidad_funcional` nullable
- `observaciones`

Observaciones:

- incluye metadatos `CORE-EF`
- aplica regla XOR materializada por `chk_col_xor`
- no se modela como entidad de negocio autonoma; depende semanticamente de `contrato_alquiler`
- el PDF historico todavia arrastra `id_terreno`; ese drift queda cerrado a favor de `id_inmueble`
- `DEV-SRV` exige que un contrato valido tenga al menos un objeto, pero esa cardinalidad minima no esta forzada por SQL

### `condicion_economica_alquiler`

Descripcion:

- configuracion economica consolidada del contrato para una vigencia dada

Atributos clave:

- `id_condicion_economica`
- `id_contrato_alquiler`
- `monto_base`
- `periodicidad`
- `moneda`
- `fecha_desde`
- `fecha_hasta`
- `observaciones`

Observaciones:

- incluye metadatos `CORE-EF`
- el SQL vigente la mantiene como tabla unica y no la descompone en cabecera y detalle por conceptos
- tiene `CHECK` de vigencia: `fecha_hasta >= fecha_desde` cuando `fecha_hasta` no es null
- tiene trigger de no superposicion temporal por contrato:
  - `trg_biu_condicion_economica_alquiler_no_solapada`
- es la entidad fisica correcta para lo que `DEV-SRV` suele llamar `condicion_locativa`
- no sustituye al dominio financiero; solo configura parametros locativos

### `ajuste_alquiler`

Descripcion:

- ajuste operativo aplicado al contrato de alquiler

Atributos clave:

- `id_ajuste_alquiler`
- `id_contrato_alquiler`
- `tipo_ajuste`
- `valor_ajuste`
- `fecha_aplicacion`
- `descripcion`

Observaciones:

- incluye metadatos `CORE-EF`
- el SQL actual lo vincula solo a `contrato_alquiler`
- el PDF historico propone variantes con FK a condicion economica, indices y estados; esos campos no existen hoy en SQL
- en el modelo vigente el ajuste se registra como hecho operativo simple, no como submotor de calculo financiero

### `modificacion_locativa`

Descripcion:

- registro trazable de alteraciones relevantes sobre un contrato de alquiler

Atributos clave:

- `id_modificacion_locativa`
- `id_contrato_alquiler`
- `tipo_modificacion`
- `fecha_modificacion`
- `descripcion`

Observaciones:

- incluye metadatos `CORE-EF`
- depende de `contrato_alquiler`
- el SQL actual conserva una forma minima y no materializa flags de impacto o estados propios
- puede servir para prorrogas menores o cambios controlados sin crear un contrato nuevo

### `rescision_finalizacion_alquiler`

Descripcion:

- evento locativo de cierre anticipado o finalizacion contractual asociado a un contrato

Atributos clave:

- `id_rescision_locativa`
- `id_contrato_alquiler`
- `fecha_rescision`
- `motivo`
- `observaciones`

Observaciones:

- incluye metadatos `CORE-EF`
- el SQL vigente unifica en una sola tabla la rescision y la finalizacion operativa
- `DEV-SRV` y `EST-LOC` describen mayor granularidad de estados para este bloque, pero esa granularidad no esta persistida como columna propia en SQL
- el nombre estructural correcto es `rescision_finalizacion_alquiler`; `rescision` sola no alcanza para representar el recurso persistido vigente

### `entrega_restitucion_inmueble`

Descripcion:

- registro de entrega o restitucion material asociado a un contrato de alquiler

Atributos clave:

- `id_entrega_restitucion`
- `id_contrato_alquiler`
- `fecha_entrega`
- `estado_inmueble`
- `observaciones`

Observaciones:

- incluye metadatos `CORE-EF`
- depende de `contrato_alquiler`
- el SQL vigente no materializa detalle por objeto ni actas complejas
- el PDF historico describe un shape mas rico (`tipo_acta`, inventario, faltantes, conformidad); ese detalle no existe hoy en la tabla real
- aunque semanticamente la entrega y la restitucion se vinculan al uso del objeto, el ownership de `ocupacion` sigue fuera de esta entidad

## Relaciones

### Relacion contractual principal

- `cartera_locativa` `0..1 -> 0..N` `contrato_alquiler`
  Nota: la FK esta en `contrato_alquiler.id_cartera_locativa`.

- `reserva_locativa` `0..1 -> 0..N` `contrato_alquiler`
  Nota: la FK esta en `contrato_alquiler.id_reserva_locativa`.
  Nota de drift: el PDF global sugiere `0..1 -> 0..1`, pero esa unicidad no esta materializada hoy en SQL.

- `contrato_alquiler` `0..1 -> 0..N` `contrato_alquiler`
  Nota: la FK esta en `contrato_alquiler.id_contrato_anterior`.
  Nota semantica: se usa para continuidad historica, renovacion o reemplazo contractual.

### Detalle multiobjeto

- `contrato_alquiler` `1 -> 0..N` `contrato_objeto_locativo`
  Cardinalidad inversa: cada `contrato_objeto_locativo` pertenece a exactamente `1` `contrato_alquiler`.

- cada `contrato_objeto_locativo` refiere a exactamente `1` objeto inmobiliario efectivo:
  - `1` `inmueble`, o
  - `1` `unidad_funcional`

### Economica y ciclo locativo

- `contrato_alquiler` `1 -> 0..N` `condicion_economica_alquiler`
- `contrato_alquiler` `1 -> 0..N` `ajuste_alquiler`
- `contrato_alquiler` `1 -> 0..N` `modificacion_locativa`
- `contrato_alquiler` `1 -> 0..N` `rescision_finalizacion_alquiler`
- `contrato_alquiler` `1 -> 0..N` `entrega_restitucion_inmueble`

Observaciones:

- `DEV-SRV` sugiere relaciones operativas mas fuertes entre `ajuste_alquiler` y `condicion_economica_alquiler`, pero el SQL actual no materializa esa FK
- `DEV-SRV` tambien sugiere mayor profundidad operativa para `entrega` y `rescision`, pero esa profundidad no esta persistida hoy

## Soporte transversal materializado

Estas piezas no pertenecen al ownership semantico central del nucleo locativo, pero hoy existen como soporte real del modelo.

### `relacion_persona_rol`

Rol:

- resuelve la vinculacion de personas intervinientes del contrato

Observaciones:

- el SQL admite `contrato_alquiler` como `tipo_relacion`
- el dominio `personas` conserva ownership de la identidad base
- `locativo` define la semantica de locador, locatario, garante y otros roles contextuales

### `documento_entidad` y `emision_numeracion`

Rol:

- soporte documental y numeracion transversal sobre `contrato_alquiler`

Observaciones:

- el SQL valida existencia de `contrato_alquiler` desde ambos mecanismos
- no deben leerse como ownership locativo del dominio documental

### `relacion_generadora`

Rol:

- puente estructural hacia el dominio financiero

Observaciones:

- el SQL admite `contrato_alquiler` como origen
- esto no traslada a `locativo` el calculo de deuda, pagos o saldos

### `disponibilidad` y `ocupacion`

Rol:

- soporte operativo e inmobiliario consumido por el ciclo locativo

Observaciones:

- `DEV-SRV` establece que la disponibilidad depende de `inmobiliario`
- el contrato define uso y ocupacion, no propiedad
- este DER no absorbe el ownership de `ocupacion` ni de `disponibilidad`

## Reglas visibles consolidadas

- `contrato_alquiler` es la entidad juridica principal del dominio locativo
- el contrato es multiobjeto y su detalle se materializa por `contrato_objeto_locativo`
- no debe modelarse una "venta locativa" paralela a `contrato_alquiler`
- una renovacion sustancial se representa hoy como nuevo `contrato_alquiler` enlazado por `id_contrato_anterior`
- una prorroga menor puede representarse como `modificacion_locativa` mientras no exista una entidad mas rica materializada
- `condicion_economica_alquiler` es la forma persistida vigente de la configuracion economica del contrato
- `ajuste_alquiler` no reemplaza ni redefine el contrato base; ajusta su operacion
- `rescision_finalizacion_alquiler` conserva historial y no elimina el contrato
- `entrega_restitucion_inmueble` registra entrega o restitucion contractual, pero no sustituye por si sola el modelo de ocupacion
- el dominio locativo no calcula deuda ni pagos; esos efectos se delegan al dominio financiero

## Implicancias para futura DEV-API

Este DER deja el modelo listo para definir `DEV-API` con estas reglas base:

- el recurso raiz debe ser `contrato_alquiler`
- `contrato_objeto_locativo` debe exponerse como detalle embebido o hijo del contrato, no como recurso semantico independiente
- el naming publico debe partir de nombres fisicos vigentes:
  - `contrato_alquiler`
  - `condicion_economica_alquiler`
  - `ajuste_alquiler`
  - `modificacion_locativa`
  - `rescision_finalizacion_alquiler`
  - `entrega_restitucion_inmueble`
- si se quisiera usar naming funcional mas corto en API, debe dejarse trazabilidad explicita con el nombre SQL
- no deben inventarse recursos `contrato_renovacion`, `contrato_rescision` o `condicion_locativa` mientras no existan estructuras persistidas equivalentes
- las reglas funcionales de `DEV-SRV` que hoy no estan materializadas como FK, columnas o tablas deben tratarse como validacion de aplicacion futura, no como shape ya confirmado por SQL

## Estado de implementacion real

Estado actual del workspace:

- SQL locativo materializado: si
- `DEV-SRV` locativo modular: si
- backend locativo propio con router/schema/service/repository: no materializado
- tests locativos versionados en `backend/tests`: no materializados
- soporte transversal ya conectado a `contrato_alquiler`: si, en `relacion_persona_rol`, `documento_entidad`, `emision_numeracion` y `relacion_generadora`

Conclusion operativa:

- este DER queda apto como base estructural y semantica para definir `DEV-API-LOCATIVO`
- la futura API debe partir del SQL vigente y de este consolidado, no de los shapes mas ricos del PDF historico
