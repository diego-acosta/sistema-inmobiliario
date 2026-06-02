# UX-WIZARD-VENTA-COMPLETA-UNICO - Wizard unico de venta completa

## 1. Objetivo

Definir el diseno UX/tecnico del unico wizard de venta completa para el dominio
`comercial`, reutilizable para dos origenes de entrada:

1. venta desde una reserva de venta existente;
2. venta directa sin reserva previa.

La regla principal es que el wizard es uno solo. El origen no crea otro wizard,
no duplica pasos y no duplica componentes: solo define el contexto inicial y el
adapter final que confirma contra el endpoint compuesto correspondiente.

## 2. Alcance y restricciones

Este documento es exclusivamente documental/tecnico para frontend Flet.

Incluye:

- flujo UX del wizard unico;
- estado canonico compartido;
- adaptadores finales de payload para reserva y venta directa;
- reglas CORE-EF que la UI debe respetar al confirmar;
- validaciones UX previas al submit;
- limites explicitos de lo que el wizard no hace.

No incluye:

- cambios backend;
- cambios SQL;
- cambios en tests backend;
- implementacion UI productiva;
- endpoints nuevos.

Incluye como referencia tecnica el prototipo limpio no productivo
`frontend/flet_app/prototypes/venta_completa_unica_wizard_prototype.py`.

## 3. Clasificacion y dominio

- Dominio correcto: `comercial`, porque reservas de venta, ventas, condiciones
  comerciales, partes comerciales, objetos de venta y confirmacion de venta
  completa pertenecen al ciclo de compraventa.
- Clasificacion del concepto `wizard de venta completa`: soporte UX/tecnico del
  flujo comercial; no redefine entidades de dominio ni ownership semantico.
- `reserva_venta`, `venta`, objetos de venta y condiciones comerciales se tratan
  como nucleo del dominio `comercial`.
- Los sujetos/personas se consumen como identidad base provista por `personas`;
  el rol de comprador/vendedor se interpreta solo en contexto comercial.
- El Plan Pago V2 se carga como condicion comercial de la venta y origen de
  obligaciones; la UI no ejecuta pagos, caja, imputaciones ni recibos.
- La consulta posterior `GET /api/v1/ventas/{id_venta}/plan-pago-v2` es lectura
  sobre la venta confirmada; no reemplaza el command de confirmacion.

## 4. Contratos backend existentes que guian el diseno

El wizard debe adaptarse a los endpoints compuestos reales existentes:

```text
POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa
POST /api/v1/ventas/directa/confirmar-venta-completa
```

Ambos endpoints reciben `plan_pago_v2` con bloques y propagan los metodos de
liquidacion:

```text
SIN_INTERES
INTERES_DIRECTO
INDEXACION
```

Diferencias contractuales relevantes:

| Origen | Endpoint final | `If-Match-Version` | Body |
| --- | --- | --- | --- |
| `RESERVA` | `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa` | Requerido, corresponde a `reserva_venta.version_registro`. | `generar_venta`, `condiciones_comerciales`, `plan_pago_v2`, `confirmacion`. |
| `DIRECTA` | `POST /api/v1/ventas/directa/confirmar-venta-completa` | No expuesto/requerido por el contrato actual. | `generar_venta`, `objetos`, `compradores`, `condiciones_comerciales`, `plan_pago_v2`, `confirmacion`. |

Ambos endpoints requieren headers CORE-EF al confirmar:

```text
X-Op-Id
X-Usuario-Id
X-Sucursal-Id
X-Instalacion-Id
```

## 5. Regla principal de producto

Debe existir un unico wizard de venta completa con los mismos pasos y los mismos
componentes. No debe existir un wizard para reserva y otro wizard para venta
directa.

La variacion permitida es esta:

- `origen = RESERVA`: el estado del wizard incluye una reserva vigente
  seleccionada o precargada, y el adapter final llama al endpoint desde reserva.
- `origen = DIRECTA`: el estado del wizard no incluye reserva, exige carga de
  objetos/compradores, y el adapter final llama al endpoint de venta directa.

El origen es contexto de entrada y estrategia de confirmacion; no es un fork de
UX ni de logica de negocio.

## 6. Entradas posibles al mismo wizard

### 6.1 Desde listado de reservas

Cada reserva vigente puede exponer una accion `Vender` o `Confirmar venta`.
Esa accion abre el mismo wizard unico con:

- `origen = RESERVA` preseleccionado;
- `id_reserva_venta` ya informado;
- `version_registro` de la reserva disponible para `If-Match-Version`;
- datos precargables de la reserva disponibles para los pasos siguientes.

El usuario no vuelve a elegir origen, salvo que el producto habilite una accion
explicita de cambio de origen. Si se permite cambiar el origen, la UI debe
limpiar los datos dependientes de reserva para evitar payloads mixtos.

Endpoint final:

```text
POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa
```

### 6.2 Desde listado de ventas

El boton `Nueva venta` abre el mismo wizard unico sin origen preseleccionado.
El primer paso pregunta:

- `Desde reserva existente`;
- `Venta directa`.

Si el usuario elige `Desde reserva existente`, la UI muestra un selector/listado
de reservas vigentes y continua con `origen = RESERVA`.

Si el usuario elige `Venta directa`, la UI continua con `origen = DIRECTA` y no
solicita reserva.

Endpoints finales posibles:

```text
POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa
POST /api/v1/ventas/directa/confirmar-venta-completa
```

## 7. Estado canonico unico del wizard

El wizard debe mantener un unico estado interno independiente del origen. Los
adaptadores finales leen ese estado y construyen el contrato requerido por cada
endpoint.

Modelo conceptual de estado:

```text
WizardVentaCompletaState
├─ origen: RESERVA | DIRECTA | NO_SELECCIONADO
├─ reserva
│  ├─ id_reserva_venta
│  ├─ version_registro
│  └─ datos_precargados
├─ venta
│  ├─ codigo_venta
│  ├─ fecha_venta
│  ├─ moneda
│  ├─ monto_total
│  └─ observaciones
├─ partes
│  ├─ compradores[]
│  ├─ vendedores[] (si aplica al contrato/flujo vigente)
│  └─ representaciones[] (si corresponde)
├─ objetos[]
│  ├─ id_inmueble
│  ├─ id_unidad_funcional
│  ├─ precio_asignado
│  └─ observaciones
├─ condiciones_comerciales
│  ├─ monto_total
│  ├─ tipo_plan_financiero
│  ├─ moneda
│  ├─ anticipo/saldo/cuotas legacy si aplica al contrato
│  └─ objetos para adapter RESERVA si el contrato los requiere alli
├─ plan_pago_v2
│  ├─ tipo_pago
│  ├─ monto_total_plan
│  ├─ moneda
│  ├─ bloques[]
│  └─ observaciones
├─ confirmacion
│  └─ observaciones
└─ core_ef
   ├─ x_op_id
   ├─ x_usuario_id
   ├─ x_sucursal_id
   └─ x_instalacion_id
```

Reglas del estado:

- No existe `id_venta` manual, porque la venta todavia no existe antes de
  confirmar.
- `plan_pago_v2` es el mismo subestado para ambos origenes.
- Los datos precargados desde reserva alimentan el mismo estado; no crean un
  modelo paralelo.
- El estado puede tener campos visuales auxiliares, pero el submit debe filtrar
  solo campos aceptados por el contrato backend vigente.

## 8. Pasos del wizard unico

### Paso 1 - Origen

Objetivo: definir el contexto de entrada sin crear otro wizard.

Reglas:

- Valores permitidos: `RESERVA` o `DIRECTA`.
- Si viene desde boton de una reserva: `RESERVA` queda preseleccionado y la
  reserva queda precargada.
- Si viene desde `Nueva venta`: permitir elegir `RESERVA` o `DIRECTA`.
- Si `RESERVA`: seleccionar reserva vigente o usar la reserva precargada.
- Si `DIRECTA`: continuar sin reserva.
- No pedir `id_venta` manual.

### Paso 2 - Datos de venta

Campos base:

- `codigo_venta` si el contrato/operacion lo requiere;
- `fecha_venta`;
- `moneda`;
- `monto_total`;
- `observaciones`.

La pantalla puede adaptar textos y ayudas al origen, pero no cambia de wizard ni
de componente. Los campos finales deben mapear a `generar_venta` y a
`condiciones_comerciales` segun el adapter correspondiente.

### Paso 3 - Partes

Campos/conceptos:

- comprador/es;
- vendedor/es si aplica al contrato/flujo vigente;
- roles comerciales;
- representacion si corresponde.

Reglas:

- Mismo componente para ambos origenes.
- Si viene de reserva y algunos datos ya existen, se precargan y quedan sujetos
  a validacion/edicion segun reglas del flujo vigente.
- Para venta directa, `compradores[]` es requerido por el contrato actual del
  endpoint directo.
- Los roles no se modelan como atributos base de `persona`; son contexto de la
  operacion comercial.

### Paso 4 - Objetos

Campos/conceptos:

- inmuebles;
- unidades funcionales;
- precio asignado;
- observaciones cuando el contrato lo permite.

Reglas:

- Mismo componente para ambos origenes.
- Si viene de reserva, los objetos reservados pueden venir precargados.
- Si es venta directa, el usuario debe cargar objetos.
- La suma/precio de objetos debe ser coherente con monto total y condiciones
  comerciales antes de confirmar.

### Paso 5 - Plan Pago V2 — carga comercial de forma de pago

Objetivo UX: el usuario debe cargar una forma de pago comercial, clara y
usable. La pantalla no debe presentarse como editor tecnico de bloques. El
sistema debe traducir la carga comercial al payload interno
`plan_pago_v2.bloques` requerido por los endpoints compuestos.

Debe usarse el mismo paso para ambos origenes (`RESERVA` y `DIRECTA`). La forma
de pago y sus componentes pertenecen al contexto de venta del dominio
`comercial`; el frontend no ejecuta pagos, no emite recibos, no calcula deuda y
no reemplaza la generacion oficial de obligaciones del backend.

#### 5.1 Forma de pago principal

El usuario primero elige la forma de pago principal:

- `Contado`;
- `Financiado`.

La eleccion gobierna que secciones comerciales se muestran y que estructura se
construye internamente.

#### 5.2 Si la forma de pago es Contado

Mostrar un formulario simple con:

- importe total;
- fecha de pago/vencimiento;
- observaciones opcionales.

Reglas UX:

- No permitir anticipo.
- No permitir cuotas principales/tramos.
- No permitir refuerzos.
- No permitir saldo final.
- No mostrar acciones de armado de componentes financiados.

Construccion interna del payload:

```text
plan_pago_v2.tipo_pago = CONTADO
plan_pago_v2.bloques = [
  {
    tipo_bloque = CONTADO
    importe_total_bloque = importe total
    fecha_vencimiento = fecha de pago/vencimiento
  }
]
```

#### 5.3 Si la forma de pago es Financiado

Mostrar secciones comerciales, no una lista tecnica de bloques:

1. Anticipo opcional.
2. Cuotas principales / tramos.
3. Refuerzos opcionales.
4. Saldo final opcional.

Reglas UX:

- No usar `Agregar bloque` como concepto principal del usuario.
- Usar acciones comerciales como `Agregar tramo de cuotas` o
  `Agregar refuerzo`.
- La palabra `bloque` puede aparecer solo en modo tecnico/debug o en vistas de
  diagnostico del payload, nunca como modelo mental principal del operador.
- El payload interno final si debe ser `plan_pago_v2.bloques`.

#### 5.4 Anticipo opcional

UI:

- switch/toggle `Tiene anticipo`;
- importe anticipo;
- vencimiento anticipo.

Construccion interna:

```text
tipo_bloque = ANTICIPO
importe_total_bloque = importe anticipo
fecha_vencimiento = vencimiento anticipo
```

Si el switch esta apagado, no se debe enviar un componente de anticipo vacio.

#### 5.5 Cuotas principales / tramos

UI:

- lista de tramos de cuotas;
- boton `Agregar tramo de cuotas`.

Campos por tramo:

- capital del tramo;
- cantidad de cuotas;
- primer vencimiento;
- periodicidad, fijada por UX en `MENSUAL` para este flujo;
- metodo de actualizacion:
  - `Cuotas fijas / sin interes`;
  - `Interes directo`;
  - `Indexado por indice`.

Construccion interna comun del tramo:

```text
tipo_bloque = TRAMO_CUOTAS
importe_total_bloque = capital del tramo
cantidad_cuotas = cantidad de cuotas
fecha_primer_vencimiento = primer vencimiento
periodicidad = MENSUAL
metodo_liquidacion = SIN_INTERES | INTERES_DIRECTO | INDEXACION
```

Reglas:

- `INTERES_DIRECTO` e `INDEXACION` son excluyentes dentro del mismo tramo.
- Distintos tramos pueden usar metodos de liquidacion distintos.
- `SIN_INTERES` no muestra campos de interes directo ni de indexacion.
- Al cambiar el metodo, la UI debe limpiar campos incompatibles del tramo antes
  de construir el payload.

#### 5.6 Interes directo

Cuando el tramo usa `Interes directo`, mostrar:

- tasa periodica;
- cantidad de periodos;
- ayuda: `Interes simple sobre capital inicial del tramo.`

Construccion interna adicional completa:

```text
metodo_liquidacion = INTERES_DIRECTO
tasa_interes_directo_periodica = tasa periodica ingresada
cantidad_periodos = cantidad de periodos ingresada
base_calculo_interes = CAPITAL_INICIAL_BLOQUE
```

`tasa_interes_directo_periodica` y `cantidad_periodos` vienen de inputs
visibles de la UI comercial del tramo. `base_calculo_interes` se completa
internamente con el valor fijo `CAPITAL_INICIAL_BLOQUE`.

Reglas:

- No calcular interes localmente.
- No generar cronograma local.
- No mezclar campos de indexacion en el mismo tramo.

#### 5.7 Indexacion

Cuando el tramo usa `Indexado por indice`, mostrar:

- indice;
- fecha base;
- valor base;
- ayuda: `El ajuste se calcula contra el indice publicado aplicable. No se
  inventan valores futuros.`

No mostrar como campos editables normales:

- `modo_indexacion`;
- `base_calculo_indexacion`;
- `tipo_generacion_indexada`;
- `politica_valor_no_disponible`;
- `conserva_capital_original`;
- `genera_ajuste_por_diferencia`.

Construccion interna adicional completa:

```text
metodo_liquidacion = INDEXACION
id_indice_financiero = indice seleccionado
fecha_base_indice = fecha base cargada
valor_base_indice = valor base cargado
modo_indexacion = POR_COEFICIENTE
base_calculo_indexacion = CAPITAL_INICIAL_BLOQUE
tipo_generacion_indexada = DEFINITIVA
politica_valor_no_disponible = ERROR_SI_NO_EXISTE
conserva_capital_original = true
genera_ajuste_por_diferencia = true
```

`id_indice_financiero`, `fecha_base_indice` y `valor_base_indice` vienen de
la seleccion/carga de indice visible en la UI comercial del tramo. Los defaults
tecnicos (`modo_indexacion`, `base_calculo_indexacion`,
`tipo_generacion_indexada`, `politica_valor_no_disponible`,
`conserva_capital_original` y `genera_ajuste_por_diferencia`) se completan
internamente y no son campos principales del usuario.

Reglas:

- No calcular indexacion localmente.
- No inventar valores futuros del indice.
- No mezclar campos de interes directo en el mismo tramo.

#### 5.8 Refuerzos opcionales

UI:

- boton `Agregar refuerzo`;
- importe;
- vencimiento;
- etiqueta.

Construccion interna:

```text
tipo_bloque = REFUERZO
importe_total_bloque = importe
fecha_vencimiento = vencimiento
etiqueta_bloque = etiqueta
```

#### 5.9 Saldo final opcional

UI:

- switch/toggle `Tiene saldo final`;
- importe saldo;
- vencimiento saldo.

Construccion interna:

```text
tipo_bloque = SALDO
importe_total_bloque = importe saldo
fecha_vencimiento = vencimiento saldo
```

Si el switch esta apagado, no se debe enviar un componente de saldo vacio.

#### 5.10 Resumen del plan

El paso debe mostrar un resumen comercial antes de permitir avanzar:

- monto total de venta;
- monto total del plan;
- suma cargada;
- diferencia;
- cantidad estimada de obligaciones;
- alertas de campos faltantes.

Reglas del resumen:

- La suma de componentes debe coincidir con `monto_total_plan`.
- La diferencia debe quedar en cero antes de confirmar.
- La cantidad de obligaciones es estimada/indicativa, no cronograma oficial.
- No mostrar un cronograma local calculado.
- No calcular interes localmente.
- No calcular indexacion localmente.

#### 5.11 Multi-comprador

La distribucion por compradores no cambia la carga del plan de pago:

- el plan se carga por el total de la venta;
- la responsabilidad por comprador se toma desde los porcentajes definidos en
  partes/compradores mediante `porcentaje_responsabilidad`;
- no se crean cuotas separadas por comprador;
- la consulta integral posterior puede mostrar obligados por obligacion, pero el
  wizard no duplica componentes del plan por cada comprador.

#### 5.12 Campos tecnicos soportados por el payload

Aunque la UX sea comercial, el adapter debe poder construir los campos tecnicos
que el backend soporta cuando correspondan:

```text
metodo_liquidacion
tasa_interes_directo_periodica
cantidad_periodos
base_calculo_interes
id_indice_financiero
fecha_base_indice
valor_base_indice
modo_indexacion
base_calculo_indexacion
tipo_generacion_indexada
politica_valor_no_disponible
conserva_capital_original
genera_ajuste_por_diferencia
```

Estos campos pertenecen al payload interno o a modo tecnico/debug. No deben
convertirse en la experiencia principal de carga para el usuario comercial.

### Paso 6 - Revision

Mostrar resumen de:

- origen;
- reserva seleccionada si aplica;
- datos de venta;
- partes;
- objetos;
- condiciones comerciales;
- `plan_pago_v2` completo;
- headers CORE-EF disponibles para la confirmacion.

La revision debe indicar que se ejecutara una operacion compuesta transaccional.
No debe mostrar un cronograma local falso ni prometer cuotas calculadas por el
frontend. Si se muestra algun resumen de bloques, debe rotularse como resumen de
payload, no como cronograma oficial.

### Paso 7 - Confirmar

La confirmacion construye el payload desde el mismo estado del wizard y llama al
adapter final segun `origen`.

Reglas comunes:

- Enviar `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
- Bloquear submit si falta algun header CORE-EF requerido.
- Preservar la respuesta/error estandar del backend; no traducir errores de
  contrato a mensajes que oculten el campo invalido.

Reglas por origen:

- `RESERVA`:
  - llamar a `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`;
  - enviar `If-Match-Version` con la version vigente de la reserva;
  - bloquear submit si falta reserva vigente o version.
- `DIRECTA`:
  - llamar a `POST /api/v1/ventas/directa/confirmar-venta-completa`;
  - no enviar ni exigir `If-Match-Version` mientras el contrato actual no lo
    exponga/requiera.

### Paso 8 - Resultado

Mostrar la respuesta del backend y un estado de exito/fallo comprensible.

En caso OK, mostrar:

- venta confirmada;
- identificador de venta si viene en response;
- plan generado;
- obligaciones generadas;
- estado de reserva si aplica;
- accion/link para consultar plan:

```text
GET /api/v1/ventas/{id_venta}/plan-pago-v2
```

La consulta se habilita solo si el response permite obtener `id_venta`.

## 9. Adaptadores finales de payload

Los adaptadores son la unica diferencia tecnica relevante entre origenes. No son
wizards separados.

### 9.1 Adapter RESERVA

Entrada:

- estado unico del wizard;
- `id_reserva_venta` seleccionado/precargado;
- `version_registro` de la reserva para `If-Match-Version`.

Headers:

```text
X-Op-Id
X-Usuario-Id
X-Sucursal-Id
X-Instalacion-Id
If-Match-Version
```

Endpoint:

```text
POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa
```

Body esperado:

```json
{
  "generar_venta": {
    "codigo_venta": "...",
    "fecha_venta": "YYYY-MM-DD",
    "monto_total": "...",
    "observaciones": "..."
  },
  "condiciones_comerciales": {
    "monto_total": "...",
    "tipo_plan_financiero": "...",
    "moneda": "ARS",
    "importe_anticipo": "...",
    "fecha_vencimiento_anticipo": "YYYY-MM-DD",
    "importe_saldo": "...",
    "fecha_vencimiento_saldo": "YYYY-MM-DD",
    "cuotas": [],
    "objetos": []
  },
  "plan_pago_v2": {
    "tipo_pago": "FINANCIADO",
    "monto_total_plan": "...",
    "moneda": "ARS",
    "bloques": [],
    "observaciones": "..."
  },
  "confirmacion": {
    "observaciones": "..."
  }
}
```

Notas:

- `id_reserva_venta` viaja en path, no dentro del body.
- `If-Match-Version` protege la reserva versionada.
- Los objetos pueden mapearse dentro de `condiciones_comerciales.objetos` si el
  contrato vigente del endpoint desde reserva lo requiere.

### 9.2 Adapter DIRECTA

Entrada:

- mismo estado unico del wizard;
- sin reserva.

Headers:

```text
X-Op-Id
X-Usuario-Id
X-Sucursal-Id
X-Instalacion-Id
```

Endpoint:

```text
POST /api/v1/ventas/directa/confirmar-venta-completa
```

Body esperado:

```json
{
  "generar_venta": {
    "codigo_venta": "...",
    "fecha_venta": "YYYY-MM-DD",
    "monto_total": "...",
    "observaciones": "..."
  },
  "objetos": [],
  "compradores": [],
  "condiciones_comerciales": {
    "monto_total": "...",
    "tipo_plan_financiero": "...",
    "moneda": "ARS",
    "importe_anticipo": "...",
    "fecha_vencimiento_anticipo": "YYYY-MM-DD",
    "importe_saldo": "...",
    "fecha_vencimiento_saldo": "YYYY-MM-DD",
    "cuotas": []
  },
  "plan_pago_v2": {
    "tipo_pago": "FINANCIADO",
    "monto_total_plan": "...",
    "moneda": "ARS",
    "bloques": [],
    "observaciones": "..."
  },
  "confirmacion": {
    "observaciones": "..."
  }
}
```

Notas:

- No se pide `id_venta` manual.
- No se envia `If-Match-Version` mientras el contrato actual directo no lo
  exponga.
- `objetos[]` y `compradores[]` viven en el nivel superior del body directo.

## 10. Payload `plan_pago_v2` comun

Ambos adaptadores deben incluir `plan_pago_v2` con la misma estructura.

Ejemplo minimo de bloque `TRAMO_CUOTAS` con interes directo:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "etiqueta_bloque": "Tramo con interes directo",
  "importe_total_bloque": "6000000.00",
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INTERES_DIRECTO",
  "tasa_interes_directo_periodica": "2.50",
  "cantidad_periodos": 6,
  "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE"
}
```

Ejemplo minimo de bloque `TRAMO_CUOTAS` con indexacion:

```json
{
  "tipo_bloque": "TRAMO_CUOTAS",
  "etiqueta_bloque": "Tramo indexado",
  "importe_total_bloque": "6000000.00",
  "cantidad_cuotas": 6,
  "fecha_primer_vencimiento": "2026-07-10",
  "periodicidad": "MENSUAL",
  "metodo_liquidacion": "INDEXACION",
  "id_indice_financiero": 1,
  "fecha_base_indice": "2026-07-01",
  "valor_base_indice": "100.000000",
  "modo_indexacion": "POR_COEFICIENTE",
  "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
  "tipo_generacion_indexada": "DEFINITIVA",
  "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
  "conserva_capital_original": true,
  "genera_ajuste_por_diferencia": true
}
```

## 11. Validaciones UX previas al submit

Validaciones comunes:

- `origen` seleccionado.
- `fecha_venta` requerida.
- `moneda` requerida.
- `monto_total` requerido y mayor a cero.
- `condiciones_comerciales.monto_total` coherente con
  `plan_pago_v2.monto_total_plan`.
- Suma de bloques igual al monto total del plan.
- Campos requeridos por tipo de bloque.
- Campos requeridos por metodo de liquidacion.
- No mezclar `INTERES_DIRECTO` e `INDEXACION` en el mismo bloque.
- Limpiar campos incompatibles cuando cambia el metodo de liquidacion.
- Headers CORE-EF disponibles al confirmar.

Validaciones por origen:

- `RESERVA`:
  - reserva vigente requerida;
  - `id_reserva_venta` requerido;
  - `version_registro` requerido para `If-Match-Version`;
  - datos precargados no deben generar payload mixto si el usuario cambia origen.
- `DIRECTA`:
  - compradores requeridos;
  - objetos requeridos;
  - cada objeto debe tener `id_inmueble` o `id_unidad_funcional` segun contrato;
  - no enviar objetos duplicados en lugares no permitidos por el contrato directo.

## 12. Que NO hace el wizard

El wizard unico no hace:

- pagos;
- caja;
- recibos;
- recibos fiscales persistidos;
- emision posterior de cuota indexada;
- cronograma local calculado como fuente oficial;
- preview standalone con `id_venta_backend` manual;
- tester sobre venta existente;
- carga manual de `id_venta` antes de confirmar;
- venta confirmada sin plan/forma de pago;
- duplicacion de logica por origen;
- dos wizards separados;
- endpoints nuevos;
- documental real ni administrativo nuevo.

## 13. Borrador futuro

Si en el futuro se permite guardar borrador, debe ser un flujo explicito
soportado por backend y debe guardar el estado completo del wizard:

```text
venta + partes + objetos + condiciones_comerciales + plan_pago_v2 + bloques
```

Reglas para ese futuro:

- No debe existir una venta confirmada sin forma/plan de pago.
- Un borrador no equivale a venta confirmada.
- El borrador debe tener estado, persistencia y contratos propios si el backend
  lo soporta.
- No se debe simular guardado de borrador con una venta real incompleta.


## 13.1 Prototipo limpio Flet vigente

El prototipo tecnico vigente del wizard unico es:

```text
frontend/flet_app/prototypes/venta_completa_unica_wizard_prototype.py
```

Este prototipo reemplaza el enfoque experimental que pedia
`id_venta_backend` manual para probar Plan Pago V2 sobre una venta ya existente.
La regla UX/tecnica vigente es que la venta no existe hasta confirmar el wizard
completo y, por lo tanto, la pantalla no debe pedir `id_venta` ni
`id_venta_backend` al usuario antes del submit.

El prototipo mantiene un unico flujo por pasos. La eleccion `RESERVA` o
`DIRECTA` solo cambia el adapter final:

- `RESERVA`: llama a
  `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`
  y envia `If-Match-Version` de la reserva.
- `DIRECTA`: llama a
  `POST /api/v1/ventas/directa/confirmar-venta-completa` y no envia
  `If-Match-Version` mientras el contrato actual no lo exija.

El paso Plan Pago V2 del prototipo es de carga comercial y construye
internamente `plan_pago_v2.bloques`. No es un editor tecnico de bloques para
el usuario final.

El prototipo no calcula cronograma local, no calcula interes directo local y no
calcula indexacion local. Solo muestra resumen de suma cargada, diferencia y
cantidad estimada de obligaciones; el cronograma y los ajustes dependen del
backend.

## 14. Decision CORE-EF

Naturaleza del endpoint de confirmacion:

- `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`:
  `COMMAND_WRITE_NEGOCIO`.
- `POST /api/v1/ventas/directa/confirmar-venta-completa`:
  `COMMAND_WRITE_NEGOCIO`.

Headers:

- Ambos requieren `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`,
  `X-Instalacion-Id`.
- Desde reserva requiere ademas `If-Match-Version` de `reserva_venta`.
- Directa no requiere `If-Match-Version` segun contrato actual.

Idempotencia:

- Aplica como command sincronizable con `X-Op-Id`.
- Criterio UX: la UI debe generar/conservar un `X-Op-Id` por intento de
  confirmacion y no cambiarlo durante reintentos del mismo submit.
- Misma operacion funcional con payload distinto debe tratarse como nuevo
  intento operativo desde UI, salvo que backend indique otra regla.
- No declarar cumplimiento profundo adicional sin evidencia del endpoint.

Outbox:

- No aplica a este documento UI salvo consumo de efectos/reportes devueltos por
  backend.
- No declarar eventos/outbox nuevos desde frontend.

Lock logico:

- No aplica a implementacion UI documental.
- Para `RESERVA`, la UI respeta concurrencia optimista mediante
  `If-Match-Version`; no inventa locks.

Versionado:

- `RESERVA`: usa `version_registro` de `reserva_venta` como
  `If-Match-Version`.
- `DIRECTA`: no usa version de entidad existente antes de crear la venta,
  mientras el contrato actual no lo requiera.

Rollback/transaccion:

- La confirmacion es una operacion compuesta transaccional ejecutada por
  backend.
- La UI debe mostrarlo en revision y no intentar compensaciones locales.

Tests ejecutados para este PR documental:

- No aplica `pytest`, porque no se modifica backend, SQL ni tests.
- Validacion requerida: `git diff --check`.

## 15. Validacion contra implementacion y tests existentes

- Los endpoints compuestos ya existen y son la fuente de verdad del submit.
- Los schemas backend actuales diferencian body desde reserva y body directo,
  pero comparten `plan_pago_v2`.
- Existen tests backend relacionados con ambos endpoints y con propagacion de
  `INTERES_DIRECTO` e `INDEXACION`; este PR no los modifica.
- Cualquier implementacion futura de UI debe volver a validar nombres de campos,
  headers y respuestas contra router/schema/tests vigentes antes de codificar.
