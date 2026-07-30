# INT-FIN-005 — Contrato de indexación PPV2 por períodos mensuales

## 1. Estado y autoridad

- Issue de diseño: `#424` (no se cierra con este documento).
- Estado: **decisión contractual cerrada; implementación pendiente**.
- Fecha: 2026-07-30.
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

- **Período mensual:** par `(año, mes)`, representable físicamente como ambos
  componentes o como una fecha normalizada al primer día del mes. El día no posee
  semántica financiera.
- **Período base:** período mensual común desde el que se referencia toda la venta
  indexada.
- **Valor base:** valor publicado del índice para el período base. Puede estar
  pendiente aunque el período base ya esté definido.
- **Vencimiento sugerido original:** fecha calculada una sola vez a partir de la
  fecha de venta y la configuración general; sirve de ancla para una edición.
- **Período objetivo:** período mensual propio y persistido de cada obligación
  indexada, independiente de su fecha de vencimiento.
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

No es obligatorio persistir `id_indice_financiero_valor` para el valor base si el
período y el valor congelados permiten reproducir y auditar el cálculo. La decisión
física definitiva de conservar además ese id queda para `#427`.

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

La fecha sugerida es editable antes de confirmar. La política para `V` cuando el
día no existe en el mes (por ejemplo, 31 de febrero) queda `NO CONFIRMADA`; `#426`
debe cerrarla con evidencia funcional antes de implementar.

### 4.5 Período objetivo por obligación

Cada obligación indexada posee un período objetivo explícito y persistido. Con el
vencimiento sugerido sin editar, la primera cuota usa el período inmediatamente
posterior al período base y las siguientes avanzan un mes por cada mes del
cronograma. Los bloques no indexados no interrumpen el calendario global.

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
índice común y válidos según las reglas contractuales.

| Disponibilidad | Resultado contractual |
| --- | --- |
| Base publicada + objetivo exacto publicado | coeficiente y ajuste; `definitive_amount_materialized=True`; `EMITIDA`; trazabilidad aplicada |
| Base pendiente | capital provisional; `False`; `PROYECTADA`; sin ajuste ni trazabilidad aplicada |
| Objetivo pendiente | capital provisional; `False`; `PROYECTADA`; sin ajuste ni trazabilidad aplicada |
| Solo existe un valor anterior al objetivo | igual a objetivo pendiente; puede mostrarse únicamente como estimación explícita |

La fórmula vigente continúa siendo `valor_objetivo / valor_base`; este incremento
no reabre fórmula, redondeo ni estados. `determine_initial_obligation_state()` no se
modifica: recibe el hecho de materialización y conserva `EMITIDA`/`PROYECTADA`.

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

| Secuencia | Método | Período objetivo / efecto |
| --- | --- | --- |
| tramo A, cuotas 1–2 | indexado | 09/2026, 10/2026 |
| tramo B, cuotas 3–4 | no indexado | no aplica índice, pero ocupa 11/2026 y 12/2026 en el cronograma |
| tramo C, cuotas 5–6 | indexado | 01/2027, 02/2027 |

A y C usan el mismo índice y base común 08/2026. C no reinicia en 09/2026.

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

Un mismo plan puede contener legítimamente obligaciones `EMITIDA` y `PROYECTADA`.

## 6. Propuesta física futura (no implementada)

### 6.1 SQL

Propuesta para resolver en `#427` y `#429`, sin DDL en `#424`:

1. Ubicar la cabecera/base común a nivel venta o plan de venta, nunca como una
   base semánticamente independiente por bloque. La tabla exacta queda
   `NO CONFIRMADA` hasta auditar cardinalidades y migración.
2. Persistir `id_indice_financiero`, `periodo_base` normalizado y
   `valor_base_indice NULL`. `id_indice_financiero_valor_base` sería opcional.
3. Persistir en cada obligación indexada `periodo_objetivo` normalizado y el origen
   de vencimiento (`SUGERIDO`/`EDITADO`) o datos equivalentes que conserven el
   vencimiento sugerido original.
4. Considerar `CHECK` de normalización al primer día del mes, valor base positivo
   cuando no sea nulo, unicidad de una base activa por venta/plan y coherencia del
   índice entre cabecera y trazabilidad.
5. Considerar índices por `(id_indice_financiero, periodo_objetivo)` para pendientes
   y por venta/plan para consumir la base común.

La ubicación exacta, nombres, nulabilidad de campos auxiliares, FK y estrategia de
backfill son propuestas, no contratos físicos implementados.

### 6.2 Compatibilidad y migración

- Los actuales `fecha_base_indice` y `valor_base_indice` por bloque son
  compatibilidad heredada; no se expanden como núcleo.
- Antes del backfill, verificar que todos los bloques indexados de una venta tengan
  el mismo índice/base. Divergencias deben marcarse para saneamiento, no resolverse
  eligiendo silenciosamente una fila.
- Normalizar solo períodos mensuales con evidencia inequívoca. Registros ambiguos
  quedan `NO CONFIRMADOS` y requieren decisión de migración.
- Mantener lectura compatible durante una transición, pero toda venta nueva luego
  del corte deberá usar la base común.
- No deducir períodos objetivo históricos únicamente desde vencimientos si se
  perdió el ancla sugerida original.

### 6.3 API y schemas futuros

Sin modificar contratos vigentes, los issues posteriores deberán evaluar:

- request/response comercial: `periodo_base` (año/mes), vencimiento sugerido,
  vencimiento elegido y origen automático/editado;
- valor base nullable y estado explícito `PENDIENTE` sin simular publicación;
- response por obligación: `periodo_objetivo`, valor objetivo y condición
  definitiva/proyectada;
- configuración administrativa: día de cierre y día de vencimiento predeterminado;
- preview con los mismos datos derivados, sin efectos laterales.

Los nombres finales, endpoints exactos y envelopes quedan pendientes de `#425`,
`#426`, `#429` y `#430`; no se inventan aquí.

### 6.4 Services futuros

- Administrativo provee la configuración general vigente.
- Comercial calcula la sugerencia de período base y vencimiento con fecha de venta
  explícita, conserva la selección/edición y arma la cláusula pactada.
- Financiero desplaza el período objetivo a partir del ancla original, resuelve el
  valor exacto publicado, calcula coeficiente/ajuste y materializa pendientes.
- La materialización de `#428` debe ser transaccional e idempotente y no crear
  trazabilidad aplicada hasta tener ambos valores válidos.
- Ninguna política financiera debe leer el reloj global con `date.today()`.

### 6.5 Repository/selector futuro

Para deuda definitiva no es suficiente ni válido:

```text
fecha_valor <= fecha_vencimiento
ORDER BY fecha_valor DESC
LIMIT 1
```

`#423` debe consultar el índice común y el período objetivo exacto, exigir estado
publicado y aplicar las validaciones contractuales. La consulta heredada puede
seguir existiendo hasta su reemplazo, pero un resultado anterior solo sirve como
información/estimación explícita.

## 7. Responsabilidades por issue

| Issue | Habilitación proporcionada por #424 |
| --- | --- |
| `#425` | define los dos días configurables, su ownership administrativo y cálculo dinámico |
| `#426` | fija algoritmo y editabilidad del vencimiento sugerido; deja explícito el día inexistente como `NO CONFIRMADO` |
| `#427` | fija una única base por venta y la migración desde bases heredadas por bloque |
| `#428` | fija cuándo una base pendiente puede materializar obligaciones y qué no debe persistirse antes |
| `#429` | fija período objetivo persistido, secuencia global y desplazamiento contra el ancla original |
| `#423` | reemplaza fallback abierto por selección exacta del período objetivo |
| `#430` | define qué datos puede editar/presentar frontend sin calcular deuda |
| `#431` | provee invariantes para la integración completa Comercial–Financiero–Administrativo |

`#345`, `#365`, `#418` y `#421` conservan su alcance propio. Esta decisión no
resuelve fecha operativa transversal, no reabre la temporalidad corregida en
`#420` y no revierte el estado/materialización alineado por `#422`.

## 8. Matriz mínima de tests para incrementos dependientes

| Issue | Aceptaciones ejecutables futuras mínimas |
| --- | --- |
| `#425` | límites de días; venta en/antes/después del cierre; cambio de mes/año; ausencia de job |
| `#426` | primer/segundo mes; edición permitida; fin de mes una vez cerrada su regla |
| `#427` | varios bloques comparten base; bloque no indexado no reinicia; rechazo de divergencias |
| `#428` | base pendiente no materializa; publicación exacta materializa una vez; rollback e idempotencia |
| `#429` | secuencia mensual; tramo intermedio; ediciones 0/+1/+N/-1; rechazo anterior a base |
| `#423` | exacto publicado; exacto ausente; anterior disponible no aplicado; índice/estado incompatibles |
| `#430` | sugerencia visible/editable; pendiente explícito; frontend no calcula coeficiente ni deuda |
| `#431` | plan mixto; transacción completa; retry; outbox/lock/versionado según commands modificados |

Cada PR write deberá completar la checklist CORE-EF y sus tests reales. Esta matriz
no declara cobertura existente.

## 9. Decisión CORE-EF de este incremento

- Clasificación: documentación/diseño, sin command ejecutable.
- Preview PPV2 vigente: `PREVIEW_READLIKE`; no cambia headers ni produce efectos.
- Generación PPV2 vigente: `COMMAND_WRITE_NEGOCIO`; sin cambios.
- Headers, `If-Match-Version`, idempotencia, outbox, lock, versionado y frontera
  transaccional/rollback: **sin cambios**.
- Tests CORE-EF ejecutables: **NO APLICA**, porque no se modifica ningún endpoint.

## 10. Fuera de alcance y NO CONFIRMADO

No se implementan SQL, backend, frontend, selector `#423`, jobs, ni los issues
`#425` a `#431`. No se modifica pago, imputación, mora, recibos, caja,
`determine_initial_obligation_state()`, fórmula, redondeo ni lógica temporal de
`#420/#422`.

Continúa `NO CONFIRMADO`:

- política para un día de vencimiento inexistente en el mes;
- tabla y nombres físicos definitivos de la base común;
- necesidad de persistir el id del valor base además de período y valor;
- tratamiento migratorio de ventas cuyos bloques heredados discrepen;
- reglas para periodicidades distintas de la mensual;
- endpoints/envelopes definitivos de los incrementos futuros.
