# DEV-ARCH-COM-001 — Freeze arquitectónico del dominio Comercial

## 1. Objetivo
Congelar el criterio arquitectónico vigente del dominio `comercial` para asegurar alineación entre `SYS-MAP-002`, `DEV-SRV`, `CAT-CU` del dominio comercial y la relación ya fijada con el dominio `personas` en `DEV-ARCH-PER-001`.

## 2. Alcance del dominio
El dominio `comercial` incluye:
- reservas de venta
- ventas
- condiciones comerciales de venta
- instrumentos de compraventa
- cesiones
- escrituración
- gestión documental comercial
- consultas y reportes comerciales operativos

El dominio `comercial` es responsable del ciclo de compraventa y de la semántica comercial de los sujetos que intervienen en ese ciclo.

No incluye:
- identidad base de las personas
- lógica locativa
- lógica financiera primaria
- workflow interno ajeno al circuito comercial

## 3. Responsabilidad del dominio
El dominio `comercial` es responsable de modelar la operación de compraventa como unidad funcional del negocio.

Su responsabilidad incluye:
- registrar y administrar reservas de venta
- registrar y administrar ventas
- definir condiciones comerciales de venta
- gestionar instrumentos de compraventa
- gestionar cesiones
- gestionar escrituración como cierre jurídico de la operación
- definir los roles comerciales de los sujetos en la operación
- definir la condición de cliente en contexto de compraventa

No le corresponde:
- definir identidad base de persona
- definir contratos locativos
- ejecutar lógica financiera de deuda, pago o imputación
- reemplazar el dominio documental general

## 4. Límites del dominio

### con personas
`personas` provee el sujeto base, su identidad, documentación, domicilios, contactos, relaciones y representación.

`comercial` define la semántica de ese sujeto dentro de una operación de compraventa.

Los roles comerciales como `comprador`, `vendedor` o `titular comercial` viven en el contexto de la operación y no como atributos base de `persona`.

`cliente_comprador` debe interpretarse como entidad funcional del dominio `comercial`, aunque su persistencia actual pueda existir en estructuras heredadas asociadas al dominio `personas`.

### con locativo
`comercial` y `locativo` son dominios separados.

`comercial` gobierna compraventa, reservas de venta, cesiones e instrumentos de compraventa.

`locativo` gobierna reservas locativas, contratos de alquiler, garantías y ciclo locativo.

Los roles y condiciones de un dominio no deben reinterpretarse automáticamente en el otro.

### con financiero
`comercial` puede originar condiciones o relaciones que luego deriven en obligaciones del dominio `financiero`.

`financiero` es el dueño de la semántica de deuda, pago, imputación, mora y estado financiero.

`comercial` no debe asumir lógica financiera ni recalcular resultados financieros como parte de su modelo.

### con documental
`comercial` puede producir instrumentos de compraventa y documentación comercial propia del proceso.

`documental` mantiene la semántica transversal de documento lógico, versionado, numeración y asociaciones documentales.

`comercial` no reemplaza el dominio documental general, aunque mantenga entidades documentales específicas del circuito comercial.

## 5. Modelo conceptual

### operación comercial
La operación comercial es la unidad semántica del dominio `comercial`.

En ella se articulan:
- reserva de venta
- venta
- condiciones comerciales
- instrumentos de compraventa
- cesión
- escrituración

La operación define el contexto en el que los sujetos adquieren semántica comercial.

### entidades principales
Entidades principales del dominio:
- `reserva_venta`
- `venta`
- `venta_objeto_inmobiliario`
- `venta_condicion_comercial`
- `esquema_financiamiento`
- `instrumento_compraventa`
- `cesion`
- `escrituracion`
- `documento_comercial`
- `documento_logico` cuando corresponda

Estas entidades integran el núcleo funcional del circuito de compraventa documentado en `DEV-SRV`.

### roles comerciales
Los roles comerciales son contextuales a la operación.

`comercial` es dueño de la semántica de:
- `comprador`
- `vendedor`
- `titular comercial`

La operación comercial define qué rol cumple cada sujeto y bajo qué trazabilidad se vincula a la reserva, venta, cesión o escrituración.

### cliente en contexto comercial
La condición de cliente es contextual al proceso de compraventa.

`comercial` define:
- qué es un cliente
- cuándo una persona es cliente
- en qué operación o relación comercial lo es

La condición de cliente no es estructural ni permanente en la persona por sí misma.

## 6. Reglas de modelado

### operaciones comerciales
- las reservas, ventas, cesiones e instancias de escrituración deben modelarse como entidades del dominio `comercial`
- la operación comercial es el contexto semántico donde se interpretan sujetos, objetos y estados de compraventa
- las condiciones comerciales pertenecen a la venta y no a la persona

### roles
- los roles comerciales son contextuales a la operación
- no son atributos base de la persona
- `comercial` define la semántica de esos roles dentro del proceso de compraventa
- las estructuras heredadas de asociación no trasladan ownership semántico fuera del dominio `comercial`

### cliente
- la condición de cliente en compraventa pertenece al dominio `comercial`
- `cliente_comprador` debe leerse como semántica funcional comercial, aun cuando la persistencia actual sea heredada
- `personas` no define por sí mismo qué es un cliente ni cuándo una persona adquiere esa condición

## 7. Decisiones congeladas
- `comercial` es dueño de la semántica de compraventa.
- `comercial` es dueño de la condición de cliente en contexto de venta.
- `comprador`, `vendedor` y `titular comercial` son roles contextuales a la operación.
- los roles comerciales no son atributos base de la persona.
- `personas` provee identidad, no semántica comercial.
- `cliente_comprador` se congela como entidad funcional del dominio `comercial`, aunque su persistencia actual sea heredada.
- `comercial` no define lógica financiera ni locativa.

## 8. Criterio de evolución
Toda evolución futura del dominio debe:
- preservar la operación comercial como contexto semántico principal
- mantener la separación explícita con `personas`, `locativo`, `financiero` y `documental`
- evitar trasladar roles o condición de cliente al núcleo de `personas`
- evitar incorporar lógica financiera o locativa como semántica propia del dominio
- respetar el alcance ya documentado en `DEV-SRV` y `CAT-CU`

## 9. Notas
- Este documento congela el criterio arquitectónico vigente del dominio `comercial`.
- No reemplaza la documentación detallada de servicios ni catálogos, pero fija el límite semántico del dominio.
- Debe mantenerse alineado con `SYS-MAP-002`, `DEV-SRV`, `CAT-CU` y con la relación congelada con `personas` en `DEV-ARCH-PER-001`.
