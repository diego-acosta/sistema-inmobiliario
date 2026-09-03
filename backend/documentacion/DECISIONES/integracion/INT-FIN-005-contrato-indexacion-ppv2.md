# INT-FIN-005 — Contrato de indexación PPV2 por períodos mensuales

## 1. Estado y autoridad

- Issue de diseño: `#424` (no se cierra con este documento).
- Estado: **decisión contractual cerrada; implementación pendiente**.
- Fecha: 2026-07-30; reconciliación física/API de `#427`: 2026-09-02.
- Dominio responsable: Financiero, con integración contractual desde Comercial y
  configuración general desde Administrativo.
- Entidad raíz conceptual: configuración contractual de indexación de una venta y
  su aplicación sobre obligaciones financieras PPV2.
- Alcance temporal confirmado: periodicidad mensual. Otras periodicidades quedan
  `NO CONFIRMADAS`.

Este documento es la fuente contractual única para los incrementos `#423` y
`#425` a `#431`. Ante una diferencia con auditorías anteriores, prevalece esta
decisión para el diseño futuro. No describe campos, endpoints o comportamiento ya
implementados salvo cuando lo indica expresamente.

## 2. Evidencia y clasificación

La decisión fue contrastada con DEV-ARCH Comercial, DEV-SRV y DEV-API Comercial y
Financiero, SQL, schemas, services, calculators, repositories y tests vigentes de
PPV2, índices, bloques, preview, generación, venta completa e histórica.

| Concepto | Clasificación | Ownership |
| --- | --- | --- |
| Venta, cláusula pactada, plan y bloques | núcleo | Comercial |
| Base común seleccionada para la venta | núcleo contractual | Comercial selecciona; Financiero consume |
| Catálogo, valores, coeficiente, ajuste, obligación, estado y trazabilidad | núcleo | Financiero |
| Día de cierre y día de vencimiento predeterminado | soporte transversal de configuración | Administrativo |
| Campos actuales por bloque y selector `<= fecha_vencimiento` | compatibilidad heredada | No son el modelo contractual futuro |

No se traslada lógica financiera a Comercial: Comercial conserva la cláusula y
los datos pactados; Financiero resuelve valores y materializa deuda. La ubicación
física futura de la base común no cambia este ownership.

## 3. Vocabulario contractual

- **Período mensual:** par `(año, mes)`. Su representación canónica futura debe ser
  una fecha normalizada al primer día del mes o una columna equivalente que no
  admita ambigüedad de día. El día original de `fecha_valor` no diferencia dos
  valores contractuales dentro de un mismo período mensual.
- **Período base:** período mensual común desde el que se referencia toda la venta
  indexada.
- **Valor base:** valor publicado del índice para el período base. Puede estar
  pendiente aunque el período base ya esté definido.
- **Vencimiento sugerido original:** fecha calculada una sola vez a partir de la
  fecha de venta y la configuración general; sirve de ancla para una edición.
- **Período objetivo:** período mensual propio y persistido de cada obligación
  indexada. Es distinto del vencimiento, pero se relaciona con él mediante el
  vencimiento sugerido original y las reglas de desplazamiento contractual.
- **Valor objetivo:** valor publicado del índice exactamente correspondiente al
  período objetivo.
- **Materialización definitiva:** cálculo y persistencia de coeficiente, ajuste,
  importe definitivo, estado y trazabilidad aplicada.

El período base no es `fecha_venta`, `fecha_base_indice` histórica,
`fecha_vencimiento`, `fecha_publicacion` ni `fecha_valor`. El valor base tampoco es
el período base.

## 4. Decisiones funcionales cerradas

### 4.1 Base común de la venta

Toda venta indexada posee una sola base común. Todos sus tramos indexados comparten
`id_indice_financiero`, período base y valor base cuando esté disponible. Un nuevo
tramo indexado no crea otra base. Un tramo no indexado intermedio no reinicia la
referencia ni la secuencia temporal.

La identidad del valor base publicado se conserva mediante
`id_indice_financiero_valor_base` nullable. Período, identidad y valor congelados
permiten reproducir y auditar el cálculo. Si el valor todavía no existe, tanto la
identidad como el valor permanecen nulos; no se persiste un estado intermedio
incompleto.

### 4.2 Sugerencia del período base

Con fecha de venta `F` y día de cierre comercial configurable `C`:

```text
si día(F) <= C: período_base_sugerido = mes(F)
si día(F) >  C: período_base_sugerido = mes(F) + 1 mes
```

La regla incluye el día de cierre. Se calcula dinámicamente con la fecha de negocio
recibida; no usa `date.today()` dentro de la política financiera ni requiere un job
mensual. Antes de confirmar, el usuario puede modificar el mes y el año.

### 4.3 Valor base pendiente

La publicación del valor no es precondición para registrar la venta. Si el período
base existe y el valor aún no fue publicado:

- se congela el período base;
- el valor base queda nulo/pendiente;
- no se calcula coeficiente ni ajuste definitivo;
- la obligación indexada conserva capital provisional;
- `definitive_amount_materialized=False`;
- el estado financiero es `PROYECTADA`;
- no se crea trazabilidad aplicada en `obligacion_financiera_indexacion`.

La publicación posterior habilitará la materialización de `#428`; no autoriza a
usar otro período ni el último valor anterior.

### 4.4 Vencimiento sugerido

Con día de vencimiento predeterminado `V`:

```text
si día(F) <= C: primer vencimiento = día V del mes(F) + 1 mes
si día(F) >  C: primer vencimiento = día V del mes(F) + 2 meses
```

La fecha sugerida es editable antes de confirmar. Política confirmada por `#426`:
si el día de vencimiento configurado no existe en el mes destino, se utiliza el
último día válido de dicho mes (por ejemplo, 31 en febrero resulta en 28 o 29).

### 4.5 Período objetivo por obligación

Cada obligación indexada posee un período objetivo explícito y persistido. Son dos
datos distintos: el vencimiento no determina por sí solo el índice aplicable, pero
el período objetivo sugerido se calcula usando el vencimiento sugerido original y
el calendario contractual común. Con el vencimiento sugerido sin editar, la
primera cuota usa el período inmediatamente posterior al período base y las
siguientes se ubican según el mes de sus respectivos vencimientos sugeridos.

Los bloques no indexados no tienen `periodo_objetivo`: no consumen períodos de
índice, no reinician el calendario y tampoco lo congelan. Cuando aparece un nuevo
tramo indexado, cada objetivo se deriva del calendario común respecto de la base y
del vencimiento sugerido original de esa obligación; nunca del conteo de cuotas
indexadas o no indexadas anteriores.

`fecha_vencimiento` no es fuente suficiente para reconstruir el período objetivo:
ambos datos se conservan y cumplen funciones distintas.

### 4.6 Edición del vencimiento

Sea `VS` el vencimiento sugerido original, `VE` el editado y `PO` el período
objetivo sugerido:

```text
desplazamiento = diferencia_en_meses(mes(VS), mes(VE))
período_objetivo_editado = PO + desplazamiento meses
```

- Cambiar solo el día dentro del mismo mes no desplaza el período objetivo.
- Mover el vencimiento uno o más meses desplaza el objetivo en igual cantidad.
- Adelantarlo retrocede el objetivo en igual cantidad.
- Siempre se recalcula contra `VS`, nunca encadenando ediciones previas.
- Si el resultado fuera anterior al período base, se rechaza: permitirlo requiere
  una decisión contractual posterior expresa.

### 4.7 Resolución y materialización

Financiero debe resolver el valor **exacto del período objetivo**. Para materializar
deben existir el valor base y el valor publicado del período objetivo, ambos del
índice común y válidos según las reglas contractuales, y debe cumplirse
`valor_objetivo >= valor_base`.

| Disponibilidad | Resultado contractual |
| --- | --- |
| Base publicada + objetivo exacto publicado y `objetivo >= base` | coeficiente y ajuste no negativo; `definitive_amount_materialized=True`; `EMITIDA`; trazabilidad aplicada |
| Base publicada + objetivo exacto publicado y `objetivo < base` | incompatibilidad `INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO`; no materializa por el modelo vigente y no crea componente negativo |
| Base pendiente | capital provisional; `False`; `PROYECTADA`; sin ajuste ni trazabilidad aplicada |
| Objetivo pendiente | capital provisional; `False`; `PROYECTADA`; sin ajuste ni trazabilidad aplicada |
| Solo existe un valor anterior al objetivo | igual a objetivo pendiente; puede mostrarse únicamente como estimación explícita |

La fórmula vigente continúa siendo `valor_objetivo / valor_base`; este incremento
no reabre fórmula, redondeo ni estados. `determine_initial_obligation_state()` no se
modifica: recibe el hecho de materialización y conserva `EMITIDA`/`PROYECTADA`.

Si `valor_objetivo < valor_base`, no corresponde afirmar que la obligación queda
simplemente `PROYECTADA`: el flujo debe devolver o conservar la incompatibilidad
funcional vigente `INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO`, sin crear un
`AJUSTE_INDEXACION` negativo. SQL exige importes no negativos en
`composicion_obligacion` y en las estructuras de corrida, y los tests vigentes
esperan ese rechazo. Resolver la disminución requiere un modelo futuro explícito
de bonificación, crédito o ajuste compensatorio; no se diseña en #424.

El código anterior corresponde a preview/generación comercial PPV2. Las corridas
financieras posteriores conservan hoy su incompatibilidad específica
`AJUSTE_NEGATIVO_NO_SOPORTADO`; #424 no unifica ni cambia contratos ejecutables.

El último valor conocido nunca puede convertirse automáticamente en aplicado,
materializar deuda, crear ajuste definitivo, crear trazabilidad aplicada ni emitir
una obligación. Un valor estimado debe estar rotulado como tal y separado del
contrato definitivo.

## 5. Matrices de aceptación

### 5.1 Venta antes del cierre

Configuración: cierre 20, vencimiento 10, venta 15/07/2026.

| Caso | Base sugerida | Primer vencimiento | Objetivos | Resultado |
| --- | --- | --- | --- | --- |
| base julio publicada | 07/2026 | 10/08/2026 | 08, 09, 10/2026 | cada cuota se materializa solo si su objetivo exacto está publicado |
| base julio pendiente | 07/2026 | 10/08/2026 | 08, 09, 10/2026 | indexadas `PROYECTADA`, sin ajuste aplicado |

### 5.2 Venta después del cierre

Configuración: cierre 20, vencimiento 10, venta 25/07/2026.

| Base sugerida | Primer vencimiento | Cuota 1 | Cuota 2 | Cuota 3 |
| --- | --- | --- | --- | --- |
| 08/2026 | 10/09/2026 | objetivo 09/2026 | 10/2026 | 11/2026 |

La primera cuota usa el período siguiente a la base, no julio ni el último índice
disponible al confirmar.

### 5.3 Varios tramos

Base común: 08/2026. Cada fila conserva su vencimiento sugerido original.

| Tramo / cuota | Método | Vencimiento sugerido | Período objetivo |
| --- | --- | --- | --- |
| A / 1 | indexado | 10/09/2026 | 09/2026 |
| A / 2 | indexado | 10/10/2026 | 10/2026 |
| B / 3 | no indexado | 10/11/2026 | no aplica |
| B / 4 | no indexado | 10/12/2026 | no aplica |
| C / 5 | indexado | 10/01/2027 | 01/2027 |
| C / 6 | indexado | 10/02/2027 | 02/2027 |

A y C usan el mismo índice y base común. B no “consume” objetivos: sus obligaciones
no tienen `periodo_objetivo`. Los objetivos de C son enero y febrero porque se
derivan de sus vencimientos sugeridos originales dentro del calendario común, no
porque cuatro cuotas anteriores —indexadas o no— hayan sido contadas.

### 5.4 Vencimiento editado

Ancla: vencimiento sugerido 10/09/2026; objetivo sugerido 09/2026.

| Edición | Desplazamiento | Objetivo resultante |
| --- | --- | --- |
| 23/09/2026 | 0 | 09/2026 |
| 10/10/2026 | +1 | 10/2026 |
| 10/11/2026 | +2 | 11/2026 |
| 10/08/2026 | -1 | 08/2026, válido si no queda antes de la base |

Con base 09/2026, la última fila sería inválida por producir 08/2026.

### 5.5 Disponibilidad y plan mixto

| Obligación | Base | Objetivo | Valor anterior | Estado / materialización |
| --- | --- | --- | --- | --- |
| fija | no aplica | no aplica | no aplica | `EMITIDA`; importe definitivo no indexado |
| indexada A | publicada | exacto publicado | irrelevante | `EMITIDA`; ajuste y trazabilidad |
| indexada B | pendiente | publicado | disponible | `PROYECTADA`; sin ajuste ni trazabilidad |
| indexada C | publicada | pendiente | disponible | `PROYECTADA`; anterior solo informativo |
| indexada D | publicada | exacto menor que base | irrelevante | incompatibilidad `INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO`; no materializa ni crea componente negativo |

Un mismo plan puede contener legítimamente obligaciones `EMITIDA` y `PROYECTADA`.

## 6. Contrato físico y de aplicación de #427 (no implementado)

### 6.1 Entidad y campos

La única fuente contractual de la base será
`plan_pago_venta_indexacion`, entidad Comercial opcional y 1:1 con
`plan_pago_venta`. Se elige una tabla específica porque un plan no indexado no
posee base, la base tiene lifecycle y versión propios, y sus columnas nullable no
deben contaminar `venta` ni `plan_pago_venta`. Una venta puede conservar planes
eliminados lógicamente, pero cada plan vivo posee como máximo una base activa.

La entidad incorpora metadata CORE-EF completa y estos campos funcionales:

| Campo | Nulabilidad | Contrato |
| --- | --- | --- |
| `id_plan_pago_venta` | `NOT NULL` | FK al plan Comercial dueño |
| `id_indice_financiero` | `NOT NULL` | FK al catálogo Financiero |
| `periodo_base` | `NOT NULL` | `DATE` canónica con día `1` |
| `id_indice_financiero_valor_base` | `NULL` | FK al valor publicado exacto del mismo índice |
| `valor_base_indice` | `NULL` | snapshot positivo del valor publicado |

`periodo_base=2026-05-01` representa inequívocamente mayo de 2026. Ningún otro día
es válido. No se crean columnas de año/mes separadas.

El estado no se persiste: se deriva sin ambigüedad.

```text
id_indice_financiero_valor_base IS NULL AND valor_base_indice IS NULL
→ BASE_PENDIENTE

id_indice_financiero_valor_base IS NOT NULL AND valor_base_indice IS NOT NULL
→ BASE_DISPONIBLE
```

Los estados mixtos quedan prohibidos. `BASE_PENDIENTE` y `BASE_DISPONIBLE` son
proyecciones de lectura, no un nuevo lifecycle mutable.

### 6.2 Constraints y validaciones

SQL debe imponer:

- FK `id_plan_pago_venta → plan_pago_venta` con borrado restrictivo;
- FK `id_indice_financiero → indice_financiero` con borrado restrictivo;
- unicidad parcial de una base activa por `id_plan_pago_venta`;
- `CHECK` que exija día `1` en `periodo_base`;
- `CHECK valor_base_indice IS NULL OR valor_base_indice > 0`;
- `CHECK` de nulabilidad conjunta entre id y snapshot del valor base;
- FK compuesta que garantice que el valor base pertenece al mismo índice;
- metadata, checks temporales, UID único, índices y triggers CORE-EF equivalentes a
  las entidades Comerciales vigentes;
- soft delete mediante `deleted_at`; no se permite una segunda base activa.

Aplicación debe imponer, antes de cualquier persistencia:

- `base_indexacion` obligatoria si existe al menos un bloque `INDEXACION`;
- `base_indexacion` prohibida si no existe ningún bloque `INDEXACION`;
- `INDEXACION` continúa permitida sólo en `TRAMO_CUOTAS`;
- todos los tramos indexados consumen la misma entidad común;
- los bloques no reciben índice, período ni valor independientes;
- replay sólo con el mismo payload semántico canónico completo es idempotente;
  cualquier diferencia material, incluida pero no limitada a la base, es conflicto;
- preview y write ejecutan la misma validación funcional.

La obligación de que todo plan con tramos indexados posea base común es una
invariante transaccional de aplicación: una FK no puede expresar por sí sola esa
condición entre el método del bloque y una fila opcional del plan.

### 6.3 API y schemas de #427

Los requests PPV2 reciben en la raíz del plan:

```json
{
  "base_indexacion": {
    "id_indice_financiero": 1,
    "periodo_base": "2026-05-01"
  },
  "bloques": []
}
```

`periodo_base` usa string civil `YYYY-MM-01` y se rechaza si el día no es `01`.
El cliente no envía `valor_base_indice` ni
`id_indice_financiero_valor_base`: Financiero los resuelve.

Se eliminan como input de cada bloque `id_indice_financiero`,
`fecha_base_indice` y `valor_base_indice`. No se aceptan como alias, compatibilidad
ni fallback. Las políticas propias del tramo (`modo_indexacion`,
`base_calculo_indexacion`, `tipo_generacion_indexada`,
`politica_valor_no_disponible`, `conserva_capital_original` y
`genera_ajuste_por_diferencia`) permanecen por bloque mientras conserven contrato
vigente.

El mismo shape raíz se usa en preview sin venta, preview con venta, generación
granular y los planes anidados en confirmación directa y desde reserva. No se crea
endpoint nuevo. La consulta integral PPV2 expone una sola `base_indexacion` a nivel
plan con los cinco campos funcionales y `estado_base`, mientras cada bloque expone
sólo su configuración de método y las obligaciones conservan su trazabilidad
financiera aplicada.

Para `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar`,
`If-Match-Version` es un header condicional, sin sentinel ni versión ficticia:

- si la venta no posee un `plan_pago_venta` vivo, el command crea el plan y el
  header no aplica;
- si existe un plan vivo y el command va a reutilizarlo o mutarlo, el header es
  obligatorio y contiene la versión esperada de ese plan;
- header ausente en el segundo caso, formato inválido o versión distinta producen
  error controlado; el mismatch devuelve `CONCURRENCY_ERROR` y no muta.

El service resuelve la condición dentro de la transacción: un plan existente se
actualiza mediante CAS contra `plan_pago_venta.version_registro`. Cada `UPDATE`
posterior del mismo command usa como versión esperada la versión retornada por el
CAS anterior. Así, la transición interna de `BORRADOR` a `GENERADO` no reutiliza
la versión inicial ya consumida.

Confirmación directa y confirmación desde reserva crean una venta nueva y luego su
primer plan dentro de la misma transacción; no aceptan ni reutilizan un plan previo
y por eso no requieren versión del plan. Desde reserva conserva además
`If-Match-Version` de `reserva_venta`. Un replay exacto completado se resuelve por
su receipt durable antes de reejecutar esas mutaciones.

### 6.4 Valor publicado al alta y frontera #428

`#427` aplica la alternativa A: Comercial recibe índice y período pactados y
consume un query service interno de Financiero que busca el valor `PUBLICADO`
exactamente correspondiente al período mensual. No usa HTTP interno ni consulta
SQL financiero desde el service Comercial.

Antes de contar coincidencias, el query preserva íntegramente el predicado de
validez semántica vigente de
`IndiceFinancieroRepository.get_valor_publicado_por_id_y_fecha` y sustituye sólo
su selección temporal `<= fecha` por el intervalo mensual exacto. Un valor puede
convertir `BASE_PENDIENTE` en `BASE_DISPONIBLE` únicamente si se cumplen todas
estas condiciones:

- el índice solicitado existe;
- `indice_financiero.estado_indice_financiero = ACTIVO`;
- `indice_financiero.deleted_at IS NULL`;
- el valor pertenece al índice solicitado;
- `indice_financiero_valor.deleted_at IS NULL`;
- `indice_financiero_valor.estado_valor_indice = PUBLICADO`;
- `indice_financiero_valor.fecha_publicacion IS NOT NULL`;
- `fecha_valor >= periodo_base` y
  `fecha_valor < periodo_base + 1 mes`.

Un índice inexistente, inactivo o dado de baja se rechaza como selección inválida.
Una fila marcada `PUBLICADO` pero sin `fecha_publicacion`, dada de baja o
perteneciente a otro índice no es un valor publicado válido y no cuenta en la
cardinalidad contractual.

La cardinalidad se calcula después de aplicar todos esos predicados:

- cero valores válidos en el mes: persiste `BASE_PENDIENTE`;
- exactamente un valor válido en el mes: persiste su id y snapshot como
  `BASE_DISPONIBLE`;
- más de un valor válido en el mes: `INCONSISTENCIA_TECNICA` controlada, sin
  desempate ni persistencia parcial.

No se reutiliza el selector objetivo `<= fecha`, no se introduce fallback
temporal y un valor anterior, aunque sea el último publicado, no es valor base
aplicable. La identidad y el snapshot resultantes se persisten en la misma
transacción del write Comercial. `#428` completa posteriormente sólo bases
pendientes y materializa sus efectos de manera idempotente.

#### 6.4.1 Guarda transitoria de materialización objetivo

El valor base exacto y el valor objetivo exacto son contratos distintos. Que la
cláusula quede `BASE_DISPONIBLE` no habilita por sí solo un importe definitivo:

```text
BASE_DISPONIBLE
+ selector objetivo exacto todavía no implementado
→ obligación indexada permanece PROYECTADA
```

Mientras `#429/#423` no estén implementados, `#427` debe incorporar una guarda
transitoria en preview/generación PPV2, confirmación directa, confirmación desde
reserva y preparación/materialización financiera. Para toda obligación que
requiera indexación y aún no tenga resolución contractual exacta del objetivo:

- permanece `PROYECTADA`;
- no usa `fecha_valor <= fecha_vencimiento` ni el último valor anterior;
- no calcula coeficiente con un valor de otro período;
- no persiste `obligacion_financiera_indexacion` como aplicación definitiva;
- no convierte una estimación del preview en deuda materializada.

La guarda es obligación funcional de `#427`, aunque su implementación concreta se
defina en el PR runtime. No implementa el selector completo: `#429` persiste y
resuelve el período objetivo mensual, y `#423` selecciona el valor publicado
exacto de ese período y reemplaza definitivamente el selector legacy. `#428`
completa bases pendientes y materializa efectos sólo cuando exista soporte
contractual completo de base y objetivo.

### 6.5 Migración estructural sin datos preservables

No existe backfill de filas. El entorno se recrea desde cero después del cambio.

- se crea `plan_pago_venta_indexacion` como fuente única;
- de `plan_pago_venta_bloque_indexacion` se eliminan
  `id_indice_financiero`, `fecha_base_indice` y `valor_base_indice`;
- `plan_pago_venta_bloque_indexacion` se conserva reducida a las políticas del
  método propias del tramo, sin FK duplicada a la base común;
- Financiero obtiene la base mediante
  `plan_pago_venta_bloque → plan_pago_venta → plan_pago_venta_indexacion`;
- `obligacion_financiera_indexacion` se conserva: es snapshot de la aplicación
  efectiva por obligación, no autoridad de la cláusula;
- `corrida_indexacion_financiera` y su detalle se conservan: son trazabilidad de
  ejecución; sus writers/readers se adaptan a la base común;
- seeds, bootstrap, demo, fixtures y helpers SQL se reescriben para el nuevo
  modelo; no se agrega compatibilidad de lectura de filas anteriores;
- los scripts documentados de reset/bootstrap deben construir exclusivamente el
  nuevo esquema.

### 6.6 Bloques

- Sólo `TRAMO_CUOTAS` puede declarar `metodo_liquidacion=INDEXACION` en este
  incremento.
- `ANTICIPO`, `CONTADO`, `SALDO` y `REFUERZO` independientes continúan no
  indexados.
- Un bloque no indexado no crea, cambia ni reinicia la base.
- Varios tramos indexados consumen la misma base del plan.
- Los refuerzos internos de un tramo indexado heredan la base de ese tramo; nunca
  crean una configuración de base propia.

### 6.7 Services

- Administrativo provee la configuración general vigente.
- Comercial calcula la sugerencia de período base y vencimiento con fecha de venta
  explícita, conserva la selección/edición y arma la cláusula pactada.
- Financiero resuelve el valor base exacto al alta mediante el query interno de
  `#427`. El desplazamiento del período objetivo, la resolución del valor objetivo
  y la materialización permanecen en `#429`, `#423` y `#428` respectivamente.
- Hasta implementar `#429/#423`, `#427` bloquea toda materialización definitiva de
  obligaciones indexadas: una base disponible sin objetivo exacto conserva
  `PROYECTADA` y no crea trazabilidad de aplicación.
- La materialización de `#428` debe ser transaccional e idempotente y no crear
  trazabilidad aplicada hasta tener ambos valores válidos.
- Ninguna política financiera debe leer el reloj global con `date.today()`.

### 6.8 Repository/selector futuro

Para deuda definitiva no es suficiente ni válido:

```text
fecha_valor <= fecha_vencimiento
ORDER BY fecha_valor DESC
LIMIT 1
```

`#423` debe consultar el índice común y el período objetivo exacto, exigir estado
publicado y aplicar las validaciones contractuales. La consulta heredada puede
seguir existiendo hasta su reemplazo sólo para información/estimación explícita:
la guarda de `#427` prohíbe que decida una materialización definitiva.

Contractualmente debe existir un único valor publicado por índice y período
mensual. Si se detectan varios, el selector futuro debe informar incompatibilidad:
no puede desempatar por día, fecha de publicación, id ni orden de inserción. La
normalización/unicidad global del catálogo y el selector objetivo continúan
fuera de `#427`. El query base de `#427` rechaza múltiples valores del mismo mes;
no desempata ni modifica el catálogo.

### 6.9 Outbox portable y recepción remota

La generación granular es `COMMAND_WRITE_NEGOCIO + SINCRONIZABLE`. El evento
contractual nuevo queda congelado como:

```text
event_type = plan_pago_venta_generado
aggregate_type = plan_pago_venta
owner/publicador = Comercial
```

El nombre sigue el catálogo `EVT-COM`, que usa hechos de negocio en pasado.
`#427` deberá incorporarlo formalmente al catálogo al implementar runtime.
Comercial publica el resultado causal del command y conserva ownership de
`plan_pago_venta` y `base_indexacion`; incluir snapshots financieros necesarios
para convergencia no transfiere a Comercial el ownership de obligaciones,
conceptos ni trazabilidad, que continúa en Financiero.

El evento usa el envelope portable y la canonicalización/hash Sync vigentes. Su
aggregate distribuido es `plan_pago_venta.uid_global`; cualquier `aggregate_id`
local de la fila técnica outbox no se transporta ni se interpreta como identidad
remota. El payload mínimo contiene:

- metadata: `uid_instalacion_origen` y `payload_hash` según el contrato
  transversal;
- raíz: `aggregate_uid`, `version_registro` final del plan y `op_id`;
- venta: `venta.uid_global`, sólo como referencia portable requerida;
- plan: snapshot contractual material completo, con su `uid_global`,
  `version_registro`, estado y campos del PPV2;
- base común, cuando existe: `plan_pago_venta_indexacion.uid_global`,
  `version_registro`, período, snapshot/estado y
  `indice_financiero.uid_global`; si existe valor base publicado, usa
  `indice_financiero_valor.uid_global`, nunca sus PK locales;
- bloques: `plan_pago_venta_bloque.uid_global`, `version_registro`, orden,
  importes, fechas, método y políticas materiales;
- relación generadora y generación: sus `uid_global`, `version_registro` y
  campos materiales necesarios para reconstrucción;
- obligaciones, composiciones y obligados/participantes generados: `uid_global`,
  `version_registro`, snapshots materiales y referencias por los `uid_global`
  de plan, bloque, concepto financiero y persona/rol que correspondan.

No se incluyen PK locales como identidad distribuida ni campos ajenos a la
reconstrucción del grafo. Los conceptos, participantes, índice y valor del índice
se referencian mediante la identidad portable definida por su owner; el consumer
no los redefine desde este evento.

La estrategia de emisión es única:

- generación granular exitosa: emite exactamente un
  `plan_pago_venta_generado`;
- confirmación directa: emite `persona_creada` y
  `documento_identificatorio_agregado` por cada dependencia inline nueva,
  `venta_confirmada` V2 y exactamente un `plan_pago_venta_generado`;
- confirmación desde reserva: conserva `venta_confirmada` y emite además
  exactamente un `plan_pago_venta_generado` por el plan creado.

`venta_confirmada` conserva su `event_type` y evoluciona al schema portable `2`
del envelope Sync vigente. Es el evento autoritativo Comercial que crea o converge
Venta donde aún no existe. Su snapshot contiene `venta.uid_global`,
`version_registro`, estado, fecha contractual, código, monto/moneda y demás campos
no derivados necesarios; referencia reserva y objetos sólo por identidades
portables de sus owners e incluye `op_id` y procedencia. No transporta
`id_venta`, `id_reserva_venta`, `id_inmueble`, `id_unidad_funcional` ni otra PK
de origen como identidad distribuida.

Se mantiene el nombre porque es el mismo hecho y owner; `schema_version = 2`
evita otra familia semántica. `#427` actualiza conjuntamente producers y todos
los consumers vigentes, incluidos Financiero e Inmuebles, con default-deny. Como
no hay deliveries productivos que preservar y la DB se recrea, V1 no es contrato
de recepción posterior al corte de `#427` ni se infieren sus campos locales.
`venta_confirmada` crea/converge Venta; `plan_pago_venta_generado` crea/converge
plan, base y efectos causales y sólo referencia `venta.uid_global`.

La directa que crea `compradores[].datos_persona` reutiliza los eventos Personas
ya catalogados `persona_creada` y `documento_identificatorio_agregado`. Personas
conserva ownership y publicación contractual aunque Comercial coordine el caso.
Se elige la estrategia A mediante el prerequisito transversal `#534`, que
materializa sus producers/consumers portables mínimos sobre Sync vigente. Luego
la directa de `#427` persiste ambos outbox, con snapshots Personas-owned,
UID, versión, referencias portables y envelope versionado, en la misma transacción
exterior. Venta y plan nunca redefinen Persona.

No se exige FIFO global. Si plan o venta llegan antes que Persona/documento u
otra dependencia, se registra `PENDING_DEPENDENCY` y `#511/#512` reintenta cuando
llega el evento del owner. Sólo se admite para dependencias con vía autoritativa
real, no como espera de una entidad que jamás se publica.

El futuro consumer reutiliza `#511/#512` y la infraestructura Sync vigente:
deduplica por delivery/operation, valida envelope y fingerprint, resuelve cada
`uid_global` a su PK local, devuelve `PENDING_DEPENDENCY` ante una dependencia
portable requerida ausente, respeta `version_registro`, aplica el grafo completo
atómicamente y no usa LWW por timestamps ni copia PK remotas. No crea inbox,
ledger, retry ni deduplicación paralelos.

### 6.10 Identidades portables y resolubilidad física

Toda identidad remota por `uid_global` debe ser `NOT NULL` y tener `UNIQUE`
físico antes de habilitar su consumer. Un índice ordinario no alcanza. La
auditoría del SQL vigente congela esta matriz:

| Entidad | Se transporta | UID portable | UNIQUE físico actual | Acción #427/prerequisito |
| --- | --- | --- | --- | --- |
| `venta` | raíz de venta; referencia del plan | `uid_global` | sí | conservar |
| `reserva_venta` | referencia opcional de Venta | `uid_global` | sí | conservar; resolver por owner |
| `inmueble` / `unidad_funcional` | referencias de Venta | `uid_global` | sí | conservar; resolver por owner |
| `plan_pago_venta` | raíz del plan | `uid_global` | **no: índice ordinario** | `UNIQUE NOT NULL` en #427, coordinado con #534 |
| `plan_pago_venta_indexacion` | hija del plan | `uid_global` nuevo | no existe aún | `UNIQUE NOT NULL` en #427 |
| `plan_pago_venta_bloque` | hija del plan | `uid_global` | **no: índice ordinario** | `UNIQUE NOT NULL` en #427, coordinado con #534 |
| política técnica de bloque | embebida, no entidad remota | no aplica | no aplica | no crear identidad paralela |
| `relacion_generadora` | hija financiera causal | `uid_global` | sí | conservar |
| `generacion_cronograma_financiero` | hija financiera causal | `uid_global` | **no: índice ordinario** | `UNIQUE NOT NULL` antes del consumer; coordinar #534/#427 |
| `obligacion_financiera` | hija financiera causal | `uid_global` | sí | conservar |
| `composicion_obligacion` | hija independiente | `uid_global` | sí | conservar |
| `obligacion_obligado` | relación independiente | `uid_global` | sí | conservar |
| `persona` | referencia/raíz Personas | `uid_global` | sí | publicar/resolver con `persona_creada` |
| `persona_documento` | hija Personas | `uid_global` | sí | publicar/resolver con `documento_identificatorio_agregado` |
| `indice_financiero` | referencia de base | `uid_global` | sí | resolver por owner Financiero |
| `indice_financiero_valor` | referencia de base disponible | `uid_global` | sí | resolver por owner Financiero |
| `concepto_financiero` | referencia de composición | `uid_global` | sí | resolver por catálogo owner |
| `rol_participacion` / `relacion_persona_rol` | referencia/participación | `uid_global` | sí | resolver por owner Personas |

Los `UNIQUE` faltantes son endurecimiento estructural focal de `#427`. Como no
hay datos productivos, no se diseña saneamiento histórico; resets, seeds y tests
nacen cumpliéndolos. El receiver hace lookup exacto por UID, obtiene cero o una
fila y jamás desempata duplicados.

La vía de resolución es finita: Venta por `venta_confirmada` V2;
Persona/documento inline por sus eventos Personas; plan, base, bloques,
relación/generación, obligaciones, composiciones y obligados por
`plan_pago_venta_generado`; índices, valores, conceptos, objetos y roles por el
estado/evento portable autoritativo de su owner. Si todavía no llegó, permanece
`PENDING_DEPENDENCY`; ningún consumer marca `APPLIED` ni crea placeholders.
`#427` reutiliza inbox, retry, fencing, retained envelope, operation scope y
default-deny de `#511/#512`; no crea plataforma Sync paralela.

## 7. Responsabilidades por issue

| Issue | Habilitación proporcionada por #424 |
| --- | --- |
| `#425` | define los dos días configurables, su ownership administrativo y cálculo dinámico |
| `#426` | fija algoritmo y editabilidad del vencimiento sugerido; confirma que un día inexistente se limita al último día válido del mes destino |
| `#427` | materializa una única base en `plan_pago_venta_indexacion`, elimina la autoridad por bloque e impide materialización legacy mientras no exista objetivo exacto |
| `#428` | completa bases pendientes y materializa los efectos correspondientes sólo con soporte contractual completo |
| `#429` | persiste/resuelve el período objetivo mensual, su secuencia global y desplazamiento contra el ancla original |
| `#423` | selecciona el valor publicado exacto del período objetivo y reemplaza definitivamente el fallback `<= fecha` |
| `#430` | define qué datos puede editar/presentar frontend sin calcular deuda |
| `#431` | provee invariantes para la integración completa Comercial–Financiero–Administrativo |

`#345`, `#365`, `#418` y `#421` conservan su alcance propio. Esta decisión no
resuelve fecha operativa transversal, no reabre la temporalidad corregida en
`#420` y no revierte el estado/materialización alineado por `#422`.

## 8. Matriz mínima de tests para incrementos dependientes

| Issue | Aceptaciones ejecutables futuras mínimas |
| --- | --- |
| `#425` | límites de días; venta en/antes/después del cierre; cambio de mes/año; ausencia de job |
| `#426` | primer/segundo mes; edición permitida; fin de mes con límite al último día válido |
| `#427` | varios bloques comparten base; bloque no indexado no reinicia; rechazo de divergencias; base disponible + objetivo exacto ausente + valor anterior publicado conserva `PROYECTADA`; el selector `<= fecha` no materializa; creación sin CAS y reutilización granular con CAS; outbox portable, rollback, replay sin duplicado, conflicto sin evento y recepción con `PENDING_DEPENDENCY` |
| `#428` | base pendiente no materializa; publicación exacta materializa una vez; rollback e idempotencia |
| `#429` | secuencia mensual; tramo intermedio; ediciones 0/+1/+N/-1; rechazo anterior a base |
| `#423` | exacto publicado; exacto ausente; anterior no aplicado; dos publicados del mismo índice/mes rechazados; normalización mensual |
| `#430` | sugerencia visible/editable; pendiente explícito; frontend no calcula coeficiente ni deuda |
| `#431` | plan mixto; transacción completa; retry; outbox/lock/versionado según commands modificados |

Casos transversales que no pueden omitirse en esos PRs: objetivo menor que base y
rechazo `INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO`; migración de duplicados
mensuales; nuevo tramo indexado después de uno no indexado; cambio de día dentro
del mismo mes sin desplazamiento; y cambio de mes con desplazamiento del objetivo.

Cada PR write deberá completar la checklist CORE-EF y sus tests reales. Esta matriz
no declara cobertura existente.

Para la portabilidad/outbox de `#427` son obligatorios, como mínimo:

1. granular exitoso genera exactamente un `plan_pago_venta_generado`;
2. outbox y grafo persistido confirman en la misma transacción;
3. fallo al persistir outbox revierte plan, base, bloques, relación/generación,
   obligaciones, composiciones, obligados y receipt;
4. replay exacto no duplica el evento;
5. conflicto idempotente no muta ni crea evento;
6. payload no usa PK remotas como identidad portable;
7. receiver resuelve todas las referencias portables a PK locales;
8. dependencia portable ausente produce `PENDING_DEPENDENCY` sin placeholders;
9. directa y reserva emiten `venta_confirmada` y
   `plan_pago_venta_generado` de forma atómica, con convergencia equivalente al
   granular;
10. ningún write sincronizable de PPV2 confirma sin evento distribuible.
11. `venta_confirmada` V2 crea Venta sin fila previa ni PK de origen y su replay
    converge por UID único;
12. directa inline publica `persona_creada` y
    `documento_identificatorio_agregado`; plan antes de Persona queda pendiente y
    pasa a `APPLIED` tras delivery y retry;
13. los eventos Comercial no redefinen Persona;
14. cada UID transportado tiene `NOT NULL UNIQUE`; insertar un duplicado falla en
    DB y el lookup del receiver retorna como máximo una fila;
15. venta y plan, o Persona, venta y plan, convergen ante cualquier orden de
    llegada mediante `PENDING_DEPENDENCY`/retry;
16. ninguna dependencia queda pendiente por falta de publicador contractual.

## 9. Decisión CORE-EF

- Esta reconciliación es documentación/diseño y no ejecuta commands.
- Preview PPV2 con y sin venta permanece `PREVIEW_READLIKE`: sin headers write,
  `If-Match-Version`, receipt, outbox, locks ni efectos persistentes.
- Generación granular, confirmación directa completa y confirmación completa desde
  reserva son `COMMAND_WRITE_NEGOCIO`.
- Los tres writes preservan `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id` y
  `X-Instalacion-Id` según su contrato heredado vigente. `#427` no migra identidad
  humana ni introduce Bearer. Si un endpoint se migra a Bearer en otro incremento,
  deberá usar `AuthenticatedPrincipal` y prohibir `X-Usuario-Id` como identidad.
- Confirmación desde reserva conserva `If-Match-Version` sobre la reserva. Directa
  y desde reserva crean una venta y su primer plan dentro de la transacción, no
  reutilizan un plan anterior y no requieren una versión adicional del plan.
- Generación granular acepta `If-Match-Version` condicional: no aplica al crear un
  plan inexistente y es obligatorio al reutilizar/mutar un plan vivo. El primer
  `UPDATE` usa CAS contra la versión recibida; cada mutación posterior encadena la
  versión retornada por la anterior. Cero filas afectadas produce
  `CONCURRENCY_ERROR` y rollback completo.
- `plan_pago_venta_indexacion` posee `version_registro` y metadata CORE-EF. Su alta
  y replay quedan incluidos en la idempotencia del command dueño, no crean un
  receipt paralelo.
- `#427` extiende el payload material de cada command vigente para incluir
  `base_indexacion`; no redefine idempotencia ni compara ad hoc sólo contra las
  columnas de la base.
- Se reutiliza el contrato transversal vigente de `#469/#470/#412`:
  canonicalización, `canonical_payload_hash`/fingerprint, claim y completion en
  `public.operacion_idempotente`, receipt durable y el orden de conflictos
  `COMMAND`, `TARGET`, `PAYLOAD` que corresponda. No se crea ledger, receipt
  ni mecanismo paralelo.
- El payload semántico canónico completo comprende todos los campos materiales del
  command vigente después de su normalización: tipo de pago, monto total, moneda,
  cantidad y orden contractual material de bloques, tipo y método de cada bloque,
  importes, fechas, cuotas, periodicidad, redondeo, liquidación, tasa, períodos,
  base de cálculo, políticas de indexación, refuerzos, observaciones materiales,
  `base_indexacion` y cualquier otro campo que el command incluya en su
  fingerprint/canonical payload.
- Mismo `op_id` y mismo payload semántico canónico completo produce
  `REPLAY`/reutilización del snapshot durable, sin repetir efectos ni outbox.
  Mismo `op_id` con cualquier diferencia material del payload produce
  `CONFLICTO` y no muta, aunque la `base_indexacion` coincida.
- Idempotencia por `op_id` y concurrencia por `version_registro` son controles
  independientes: el fingerprint no sustituye el CAS. Un `REPLAY` exacto ya
  completado devuelve el receipt durable sin volver a ejecutar CAS; un claim
  `EXECUTE` que muta un plan existente debe validar su versión esperada.
- Si un intento anterior falló antes de completion/commit y no dejó receipt
  durable, el mismo `op_id` puede reintentarse conforme al contrato vigente y
  vuelve a `EXECUTE`; la mera existencia de un intento abortado no constituye
  conflicto. Si el receipt ya fue completado, un payload distinto produce
  conflicto. Se conservan las claves vigentes de generación y
  `clave_funcional_origen` para obligaciones.
- La generación granular persiste exactamente un `plan_pago_venta_generado`.
  Directa agrega los eventos Personas de cada comprador inline nuevo,
  `venta_confirmada` V2 y exactamente un evento de plan; desde reserva agrega
  `venta_confirmada` V2 y exactamente un evento de plan. Venta no duplica PPV2.
- En granular, plan, base común, bloques, relación/generación, obligaciones,
  composiciones, obligados, receipt/completion y outbox comparten la transacción
  exterior. En directa se suman Personas/documentos inline, venta y todos sus
  outbox; desde reserva se suman reserva, venta y sus outbox. No hay commits
  internos.
- Cualquier fallo, incluido persistir cualquiera de los eventos, produce rollback
  completo. Está prohibido un commit funcional sincronizable sin outbox.
- Mismo `op_id` y payload completo en `REPLAY` devuelve el snapshot durable y
  no duplica eventos; payload distinto produce conflicto, no muta y no emite un
  nuevo evento. Completion/receipt y outbox quedan en la misma transacción.
- No se agrega lock nuevo. La unicidad física, el replay y el CAS focal sobre el
  plan versionado son las protecciones requeridas; una carrera distinta que no
  quede cubierta deberá demostrarse antes de introducir otro lock.

`#427` queda bloqueado por `#534`: una declaración documental de evento no prueba
un lifecycle portable runtime, y hoy faltan la Venta V2, los producers/consumers
Personas inline y una vía end-to-end verificada para dependencias externas del
plan. `#534` implementa ese prerequisito transversal reutilizando Sync vigente;
`#427` conserva las constraints y la emisión propia del grafo PPV2. No se habilita
`plan_pago_venta_generado` hasta que `#534` demuestre que toda espera puede
resolverse eventualmente.

## 10. Fuera de alcance y NO CONFIRMADO

No se implementan SQL, backend, frontend, selector `#423`, jobs, ni los issues
`#425` a `#431`. No se modifica pago, imputación, mora, recibos, caja,
`determine_initial_obligation_state()`, fórmula, redondeo ni lógica temporal de
`#420/#422`.

Para `#427` quedan confirmados tabla, campos, nulabilidad, estado derivado, API,
consulta exacta inicial, reducción de la tabla por bloque, ausencia de backfill,
constraints y comportamiento CORE-EF. Continúa fuera de alcance o `NO CONFIRMADO`:

- constraint/índice único mensual global del catálogo y tratamiento general de
  fechas de valor no normalizadas, reservados para su incremento financiero;
- reglas para periodicidades distintas de la mensual;
- período objetivo y envelopes de `#429`;
- materialización posterior de `#428`;
- selector objetivo definitivo de `#423`;
- presentación e integración frontend de `#430/#431`.
