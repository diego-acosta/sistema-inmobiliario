# DEV-API-FIN-001 — Dominio Financiero

## Estado del documento

- version: `1.1`
- estado: `DOCUMENTADO / NO IMPLEMENTADO EN BACKEND`
- fuente: `DER-FINANCIERO + SQL real + DEV-SRV-FIN + CAT-CU-FIN + INT-FIN-002`
- ultima actualizacion: `2026-04-28`
- caracter: `contrato de referencia normativo; ningun endpoint existe en backend vigente`

---

## 1. Alcance

Este documento define el contrato de API `v1` del dominio `financiero`, tomando como base:

- `backend/documentacion/DER/DER-FINANCIERO.md`
- `backend/database/schema_inmobiliaria_20260418.sql`
- `backend/documentacion/DEV-SRV/dominios/financiero/`
- `backend/documentacion/CAT-CU/dominios/financiero/CU-FIN.md`
- `backend/documentacion/DECISIONES/integracion/INT-FIN-002-resolucion-obligado-financiero.md`

El dominio financiero gestiona el ciclo economico completo del sistema: generacion de obligaciones, registro de movimientos, imputacion de pagos, ajustes y consultas financieras. Es un dominio transversal desacoplado de los dominios de negocio.

### Bloques documentados en este contrato

1. relaciones generadoras
2. obligaciones financieras
3. composicion de obligaciones
4. obligados financieros
5. pagos y movimientos financieros
6. imputaciones financieras
7. consultas financieras
8. servicios trasladados / `factura_servicio`
9. resolucion de obligado financiero (INT-FIN-002)

### Quedan fuera de este documento

- `indice_financiero` — gestion de indices financieros (SRV-FIN-004/005); PENDIENTE
- `cuenta_financiera` y `movimiento_tesoreria` — caja y tesoreria (SRV-FIN-011); PENDIENTE
- `conciliacion_bancaria` — conciliacion (SRV-FIN-011); PENDIENTE
- cronogramas de pago (SRV-FIN-006); PENDIENTE
- mora, creditos y debitos (SRV-FIN-009); PENDIENTE
- emision financiera (SRV-FIN-010); PENDIENTE
- reporting financiero consolidado (SRV-FIN-012); PENDIENTE
- integracion documental del dominio financiero
- reportes y consultas analiticas de corte gerencial

### Estado de implementacion

Existe un MVP backend acotado para `relacion_generadora`:

- `POST /api/v1/financiero/relaciones-generadoras`
- `GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}`
- `GET /api/v1/financiero/relaciones-generadoras`

El resto de endpoints documentados aqui sigue como contrato de referencia no operable.

### Nota MVP relacion generadora

En este MVP:

- `estado_relacion_generadora` NO se devuelve en la API.
- `estado_relacion_generadora` sigue siendo conceptual, no persistido y fuera del alcance MVP.
- No debe agregarse todavia ninguna columna SQL `estado_relacion_generadora`.
- Las transiciones `activar`, `cancelar` y `finalizar` quedan pendientes.
- No se implementa activacion ni generacion de `obligacion_financiera` o `composicion_obligacion`.
- Los errores usan codigos transversales basicos: `NOT_FOUND`, `APPLICATION_ERROR` e `INTERNAL_ERROR`.
- La migracion de errores del MVP a codigos `ERR-FIN-XXX` queda pendiente para una iteracion posterior.
- `tipo_origen` se acepta como input en uppercase, se persiste en lowercase porque el trigger SQL vigente lo espera asi, y se devuelve en uppercase como contrato API.

---

## 2. Fuente de verdad y criterio operativo

Orden de prioridad para este contrato:

- SQL real (`schema_inmobiliaria_20260418.sql`)
- `DER-FINANCIERO`
- `DEV-SRV-FIN` como fuente funcional
- `CAT-CU-FIN` como fuente de casos de uso
- `INT-FIN-002` para resolucion de obligado
- `ERR-FIN` y `EST-FIN` como catalogos normativos del dominio

Criterios aplicados:

- no se inventan entidades fuera de SQL
- cuando el DEV-SRV documenta columnas o estados que no existen aun en SQL, se marca PENDIENTE
- `relacion_generadora` no tiene columna `estado_relacion_generadora` en SQL vigente; en el MVP el estado sigue conceptual, no se devuelve por API y no debe agregarse columna todavia
- `composicion_obligacion` referencia `id_concepto_financiero`; `concepto_financiero` existe como tabla en SQL
- `aplicacion_financiera` no tiene columna `estado_aplicacion` en SQL vigente — ERR-FIN y EST-FIN documentan estados de imputacion; su almacenamiento fisico queda PENDIENTE
- `movimiento_financiero` no tiene FK explicita a `relacion_generadora` ni a `obligacion_financiera` en SQL; la asociacion se materializa exclusivamente a traves de `aplicacion_financiera` — ver ATENCION en seccion 7.3
- para `factura_servicio` como origen financiero: la tabla SQL existe, pero NO existe API backend, evento ni consumer — se documenta como CONCEPTUAL / NO IMPLEMENTADO

---

## 3. Criterios de diseno

- el dominio financiero usa prefijo `/api/v1/financiero/` para evitar colision con recursos de otros dominios con nombres comunes (`pagos`, `obligaciones`)
- los recursos usan plural kebab-case:
  - `relaciones-generadoras`
  - `obligaciones`
  - `pagos`
  - `imputaciones`
  - `servicios-trasladados`
- los recursos hijos de `relacion_generadora` se listan anidados bajo la relacion padre cuando corresponde
- `composicion_obligacion` no tiene endpoint autonomo de alta; es un efecto interno de la activacion de la relacion generadora
- `obligacion_obligado` no tiene endpoint autonomo de alta; la resolucion del obligado es efecto de la generacion financiera (INT-FIN-002)
- las transiciones de estado de `relacion_generadora` son endpoints PATCH independientes: `activar`, `cancelar`, `finalizar`
- no se expone `indice_financiero`, `cuenta_financiera`, `movimiento_tesoreria` ni `conciliacion_bancaria` en esta version
- `simulacion de pago` es una operacion de solo lectura de calculo; no persiste datos
- todos los writes exigen control de idempotencia por `X-Op-Id`
- `If-Match-Version` es requerido en transiciones de estado y en operaciones que muten entidades existentes

---

## 4. Ownership

- `financiero` es dueno semantico de:
  - `relacion_generadora`
  - `obligacion_financiera`
  - `composicion_obligacion`
  - `obligacion_obligado`
  - `movimiento_financiero`
  - `aplicacion_financiera`
- `comercial` genera el origen `VENTA` que da lugar a `relacion_generadora`; no crea estructuras financieras
- `locativo` genera el origen `CONTRATO_ALQUILER`; no crea estructuras financieras
- `inmobiliario` registra `factura_servicio` que conceptualmente origina `SERVICIO_TRASLADADO`; no crea estructuras financieras
- `personas` provee la identidad base para `obligacion_obligado`; no define roles financieros
- `financiero` no inventa sujetos fuera de los dominios origen (ver INT-FIN-002)

---

## 5. Convencion de errores y headers

### Formato de respuesta exitosa

```json
{
  "ok": true,
  "data": {}
}
```

### Formato de error

```json
{
  "ok": false,
  "error_code": "CODIGO",
  "error_message": "Mensaje descriptivo",
  "details": {
    "errors": []
  }
}
```

### Jerarquia de codigos de error

El dominio financiero prioriza los codigos de `ERR-FIN` sobre los codigos transversales. Los codigos transversales se usan como fallback unicamente cuando no existe un equivalente especifico en el catalogo financiero.

Equivalencias entre codigos transversales y ERR-FIN:

| Codigo transversal | Equivalente ERR-FIN | Descripcion |
|--------------------|---------------------|-------------|
| `CONCURRENCY_ERROR` | `version_esperada_invalida` (ERR-FIN-035) | Version de `If-Match-Version` no coincide |
| `LOCK_ACTIVE` | `lock_logico_activo` (ERR-FIN-036) | Lock logico activo sobre la entidad |
| `IDEMPOTENT_DUPLICATE` | `op_id_duplicado` (ERR-FIN-038) | Operacion ya ejecutada con mismo `X-Op-Id` |
| `TECHNICAL_INCONSISTENCY` | `inconsistencia_financiera_global` (ERR-FIN-045) | Inconsistencia global en el estado financiero |

Codigos transversales sin equivalente FIN (se mantienen como fallback):

- `NOT_FOUND` — entidad no encontrada o dada de baja
- `APPLICATION_ERROR` — validacion de negocio sin equivalente FIN especifico
- `SYNC_CONFLICT` — conflicto de sincronizacion entre instalaciones
- `INTERNAL_ERROR` — error tecnico no controlado

### Codigos especificos del dominio financiero (ERR-FIN)

**relacion_generadora:**
- `relacion_generadora_no_encontrada` (ERR-FIN-001)
- `relacion_generadora_inactiva` (ERR-FIN-002)
- `relacion_generadora_cancelada` (ERR-FIN-003)
- `relacion_generadora_finalizada` (ERR-FIN-004)
- `relacion_generadora_duplicada` (ERR-FIN-005)
- `estado_relacion_invalido` (ERR-FIN-006)
- `transicion_estado_relacion_invalida` (ERR-FIN-007)

**obligacion_financiera:**
- `obligacion_no_encontrada` (ERR-FIN-008)
- `obligacion_inactiva` (ERR-FIN-009)
- `obligacion_duplicada` (ERR-FIN-010)
- `estado_obligacion_invalido` (ERR-FIN-012)
- `saldo_negativo` (ERR-FIN-013)
- `monto_obligacion_invalido` (ERR-FIN-016)

**aplicacion_financiera:**
- `imputacion_no_encontrada` (ERR-FIN-017)
- `imputacion_invalida` (ERR-FIN-018)
- `imputacion_excede_saldo` (ERR-FIN-021)
- `reversion_imputacion_invalida` (ERR-FIN-025)

**transversales financieros:**
- `version_esperada_invalida` (ERR-FIN-035)
- `lock_logico_activo` (ERR-FIN-036)
- `op_id_duplicado` (ERR-FIN-038)
- `inconsistencia_financiera_global` (ERR-FIN-045)

### Headers write

- `X-Op-Id` — UUID de operacion; requerido en todos los writes; base de idempotencia
- `X-Usuario-Id` — ID de usuario; requerido en todos los writes
- `X-Sucursal-Id` — ID de sucursal; requerido en todos los writes
- `X-Instalacion-Id` — ID de instalacion; requerido en todos los writes financieros
- `If-Match-Version` — requerido en:
  - `PATCH /api/v1/financiero/relaciones-generadoras/{id}/activar`
  - `PATCH /api/v1/financiero/relaciones-generadoras/{id}/cancelar`
  - `PATCH /api/v1/financiero/relaciones-generadoras/{id}/finalizar`
  - `PATCH /api/v1/financiero/imputaciones/{id}/reversar`

Regla de idempotencia de `X-Op-Id`:

- `X-Op-Id` debe ser unico por operacion logica de negocio, no por request HTTP individual
- si el mismo request se reintenta con el mismo `X-Op-Id`, el sistema debe devolver el resultado de la ejecucion original sin ejecutar la operacion nuevamente
- un `X-Op-Id` distinto representa una operacion de negocio distinta; nunca reutilizar el mismo UUID para reintentar con payload diferente

### Reglas operativas transaccionales

- todas las operaciones criticas deben ejecutarse de forma atomica
- si falla cualquier paso de la operacion, debe aplicarse rollback completo
- no deben quedar estados intermedios inconsistentes entre la entidad principal y sus efectos acoplados
- la activacion de una `relacion_generadora` debe ser atomica con la generacion de `obligacion_financiera` y `composicion_obligacion` cuando corresponda
- el registro de un pago debe ser atomico con la generacion de `aplicacion_financiera`
- registro de outbox obligatorio en operaciones sincronizables

---

## 6. Writes

### 6.1 `relacion_generadora`

#### `POST /api/v1/financiero/relaciones-generadoras`

Objetivo:
- alta de relacion generadora como raiz formal del circuito financiero
- se crea en estado inicial `borrador`

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`

Request:

```json
{
  "tipo_origen": "CONTRATO_ALQUILER",
  "id_origen": 42,
  "descripcion": "Relacion generadora para contrato de alquiler CA-0042"
}
```

Valores validos de `tipo_origen`:
- `VENTA` — origen en dominio comercial
- `CONTRATO_ALQUILER` — origen en dominio locativo
- `SERVICIO_TRASLADADO` — origen en dominio inmobiliario via `factura_servicio`; PENDIENTE / NO IMPLEMENTADO como tipo operativo hasta que exista contrato de integracion

Response `201`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "descripcion": "Relacion generadora para contrato de alquiler CA-0042",
    "fecha_alta": "2026-04-28T10:00:00",
    "created_at": "2026-04-28T10:00:00",
    "updated_at": "2026-04-28T10:00:00",
    "deleted_at": null
  }
}
```

Nota MVP sobre `estado_relacion_generadora`: el campo no existe en SQL vigente, no se devuelve en la API y su almacenamiento fisico queda fuera del MVP.

Nota MVP sobre `tipo_origen`: la API acepta valores en uppercase; la persistencia usa lowercase por compatibilidad con el trigger SQL vigente; las responses devuelven uppercase.

Validaciones:
- `tipo_origen` requerido y valor valido del catalogo
- `id_origen` requerido y mayor que cero
- el origen referenciado debe existir en su dominio correspondiente
- no debe existir una relacion generadora activa e incompatible para el mismo `tipo_origen` e `id_origen`
- `X-Op-Id` evaluado para idempotencia; si ya fue ejecutado con mismo op_id, responder con el resultado anterior

Reglas de negocio:
- `borrador` es el unico estado inicial valido
- en alta, `estado_relacion_generadora` no se recibe por request; se asigna internamente
- una misma combinacion `tipo_origen` + `id_origen` puede generar mas de una relacion generadora segun regla financiera; la politica exacta de duplicidad queda PENDIENTE

Errores posibles:
- `400 APPLICATION_ERROR` — validacion de negocio sin equivalente FIN especifico (fallback transversal)
- `404 NOT_FOUND` — origen no encontrado o dado de baja
- `500 INTERNAL_ERROR`

La migracion de errores de este MVP a codigos `ERR-FIN-XXX` queda pendiente.

---

#### `PATCH /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/activar`

> **CONCEPTUAL / NO IMPLEMENTADO EN BACKEND**
>
> Este endpoint queda pendiente hasta definir e implementar una estrategia de activacion por `tipo_origen`. Una implementacion directa sin estrategia por origen es invalida.

Objetivo:
- transicion de `borrador` a `activa`
- habilita la relacion generadora para producir efecto financiero
- puede generar obligaciones iniciales y composiciones de forma atomica cuando corresponda

##### Comportamiento de generacion de obligaciones

La activacion de una relacion generadora NO tiene comportamiento unico.

La generacion de obligaciones depende del `tipo_origen`. `financiero` NO define la cantidad de obligaciones; ejecuta la materializacion segun condiciones del dominio origen.

Ver `INT-FIN-003-politica-generacion-obligaciones.md`.

Politica por `tipo_origen`:

- `VENTA`:
  - contado -> 1 `obligacion_financiera`
  - financiada -> multiples `obligacion_financiera`
  - anticipo/saldo -> combinacion de obligaciones
- `CONTRATO_ALQUILER`:
  - generacion periodica
- `SERVICIO_TRASLADADO`:
  - 1 `factura_servicio` -> 1 `obligacion_financiera`

Advertencia: `activar relacion_generadora` requiere estrategia por `tipo_origen`; implementar una logica unica para todos los origenes contradice INT-FIN-003.

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`, `If-Match-Version`

Request:
- sin body obligatorio
- puede incluir parametros de configuracion de activacion segun regla financiera (PENDIENTE de definicion fina)

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 2,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "descripcion": "Relacion generadora para contrato de alquiler CA-0042",
    "estado_relacion_generadora": "activa", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
    "fecha_alta": "2026-04-28T10:00:00",
    "obligaciones_generadas": [
      {
        "id_obligacion_financiera": 10,
        "codigo_obligacion": "OBL-0010",
        "importe_original": 15000.00,
        "fecha_emision": "2026-04-28",
        "fecha_vencimiento": "2026-05-10",
        "estado_obligacion": "pendiente"
      }
    ],
    "updated_at": "2026-04-28T10:05:00"
  }
}
```

Validaciones:
- `id_relacion_generadora` debe existir y no estar dada de baja
- version de `If-Match-Version` debe coincidir con `version_registro` vigente
- estado actual debe ser `borrador`
- no debe existir lock logico activo
- el origen asociado debe estar en estado compatible con la activacion
- deben cumplirse las condiciones minimas de activacion definidas en SRV-FIN-001

Reglas de negocio:
- la activacion es atomica con la generacion de obligaciones y composiciones iniciales cuando corresponda
- si falla la generacion de alguna obligacion, falla toda la activacion con rollback completo
- se registra evento en outbox para sincronizacion
- la politica exacta de generacion de obligaciones al activar (inmediata vs habilitacion previa) queda PENDIENTE de definicion fina

Errores posibles:
- `404 NOT_FOUND` — relacion no encontrada
- `409 version_esperada_invalida (ERR-FIN-035)` — version de `If-Match-Version` no coincide
- `409 lock_logico_activo (ERR-FIN-036)` — lock logico activo
- `409 transicion_estado_relacion_invalida (ERR-FIN-007)` — estado actual no admite activacion
- `409 op_id_duplicado (ERR-FIN-038)` — op_id ya ejecutado
- `500 INTERNAL_ERROR`

---

#### `PATCH /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/cancelar`

Objetivo:
- transicion a estado `cancelada`
- la relacion no admite nuevas obligaciones ni operaciones incompatibles con ese estado
- `cancelada` es estado final

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`, `If-Match-Version`

Request:

```json
{
  "motivo": "Cancelacion por rescision del contrato locativo"
}
```

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 3,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "estado_relacion_generadora": "cancelada", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
    "updated_at": "2026-04-28T11:00:00"
  }
}
```

Validaciones:
- debe existir y no estar dada de baja
- `If-Match-Version` debe coincidir
- estado actual debe ser `borrador` o `activa`
- no debe existir lock logico activo
- la cancelabilidad puede requerir validacion de obligaciones pendientes no saldadas; regla exacta PENDIENTE

Errores posibles:
- `404 NOT_FOUND`
- `409 version_esperada_invalida (ERR-FIN-035)`
- `409 lock_logico_activo (ERR-FIN-036)`
- `409 transicion_estado_relacion_invalida (ERR-FIN-007)`
- `409 relacion_generadora_finalizada (ERR-FIN-004)` — si ya estaba finalizada
- `409 op_id_duplicado (ERR-FIN-038)`
- `500 INTERNAL_ERROR`

---

#### `PATCH /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/finalizar`

Objetivo:
- transicion a estado `finalizada`
- cierre funcional completo cuando todas las obligaciones estan saldadas
- `finalizada` es estado final

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`, `If-Match-Version`

Request:
- sin body obligatorio

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 4,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "estado_relacion_generadora": "finalizada", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
    "updated_at": "2026-04-28T12:00:00"
  }
}
```

Validaciones:
- debe existir y no estar dada de baja
- `If-Match-Version` debe coincidir
- estado actual debe ser `activa`
- no debe existir lock logico activo
- no debe existir ninguna obligacion con saldo pendiente asociada a esta relacion
- no deben existir operaciones financieras futuras incompatibles con el cierre

Errores posibles:
- `404 NOT_FOUND`
- `409 version_esperada_invalida (ERR-FIN-035)`
- `409 lock_logico_activo (ERR-FIN-036)`
- `409 transicion_estado_relacion_invalida (ERR-FIN-007)`
- `409 relacion_generadora_cancelada (ERR-FIN-003)` — si ya estaba cancelada
- `409 obligacion_inactiva (ERR-FIN-009)` — si existen obligaciones con saldo pendiente
- `409 op_id_duplicado (ERR-FIN-038)`
- `500 INTERNAL_ERROR`

---

### 6.2 `pagos`

#### `POST /api/v1/financiero/pagos/simular`

Objetivo:
- calculo sin persistencia de la distribucion de un pago sobre obligaciones pendientes
- permite al operador conocer el resultado esperado antes de registrar el pago
- no crea ninguna entidad; es una operacion de solo lectura de calculo

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`

Request:

```json
{
  "id_relacion_generadora": 1,
  "importe": 15000.00,
  "fecha_pago": "2026-04-28",
  "observaciones": "Simulacion previo al cobro"
}
```

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "importe_simulado": 15000.00,
    "fecha_pago": "2026-04-28",
    "saldo_total_pendiente": 15000.00,
    "resultado": "cancela_total",
    "distribucion": [
      {
        "id_obligacion_financiera": 10,
        "codigo_obligacion": "OBL-0010",
        "estado_obligacion": "pendiente",
        "saldo_pendiente": 15000.00,
        "importe_a_aplicar": 15000.00,
        "estado_resultante": "cancelada"
      }
    ],
    "saldo_remanente": 0.00
  }
}
```

Valores posibles de `resultado`:
- `cancela_total` — el importe cubre la totalidad del saldo
- `cancela_parcial` — el importe cubre parte del saldo
- `excede_saldo` — el importe supera el saldo total pendiente

Validaciones:
- `id_relacion_generadora` debe existir y estar en estado `activa`
- `importe` debe ser mayor que cero
- `fecha_pago` requerida

Reglas de negocio:
- la simulacion no persiste datos
- orden de distribucion del importe entre obligaciones pendientes (politica base):
  1. `fecha_vencimiento ASC` — primero las obligaciones mas proximas a vencer o ya vencidas
  2. `fecha_emision ASC` como desempate — primero las mas antiguas dentro del mismo vencimiento
  - este criterio es la politica base y puede extenderse en versiones futuras sin romper el contrato
- **la simulacion no garantiza el mismo resultado en el registro real del pago si el estado financiero cambia entre ambas operaciones** — entre la simulacion y el registro real pueden crearse nuevas obligaciones, aplicarse pagos concurrentes o vencer plazos; la simulacion es una herramienta de calculo orientativo, no un bloqueo de estado

Errores posibles:
- `400 APPLICATION_ERROR` — validacion sin equivalente FIN especifico (fallback transversal)
- `404 relacion_generadora_no_encontrada (ERR-FIN-001)`
- `409 relacion_generadora_inactiva (ERR-FIN-002)`
- `500 INTERNAL_ERROR`

---

#### `POST /api/v1/financiero/pagos`

Objetivo:
- registro de un pago como `movimiento_financiero` y generacion de imputaciones (`aplicacion_financiera`) sobre las obligaciones correspondientes
- operacion transaccional y atomica

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`

Request:

```json
{
  "id_relacion_generadora": 1,
  "tipo_movimiento": "PAGO",
  "importe": 15000.00,
  "fecha_movimiento": "2026-04-28T10:30:00",
  "observaciones": "Pago mensual abril 2026",
  "imputaciones": [
    {
      "id_obligacion_financiera": 10,
      "importe_aplicado": 15000.00
    }
  ]
}
```

Valores validos de `tipo_movimiento`:
- `PAGO` — pago recibido
- `CREDITO` — acreditacion financiera

Response `201`:

```json
{
  "ok": true,
  "data": {
    "id_movimiento_financiero": 5,
    "uid_global": "uuid",
    "version_registro": 1,
    "tipo_movimiento": "PAGO",
    "importe": 15000.00,
    "signo": "HABER",
    "fecha_movimiento": "2026-04-28T10:30:00",
    "estado_movimiento": "registrado",
    "observaciones": "Pago mensual abril 2026",
    "imputaciones": [
      {
        "id_aplicacion_financiera": 1,
        "id_obligacion_financiera": 10,
        "importe_aplicado": 15000.00,
        "tipo_aplicacion": "DIRECTA",
        "origen_automatico_o_manual": "MANUAL",
        "fecha_aplicacion": "2026-04-28T10:30:00"
      }
    ],
    "created_at": "2026-04-28T10:30:00",
    "updated_at": "2026-04-28T10:30:00"
  }
}
```

Validaciones:
- `id_relacion_generadora` debe existir y estar en estado `activa`
- `importe` debe ser mayor que cero
- `fecha_movimiento` requerida
- cada `id_obligacion_financiera` en `imputaciones` debe existir, pertenecer a la relacion indicada y tener saldo pendiente
- la suma de `importe_aplicado` no puede superar el `importe` del movimiento
- `importe_aplicado` de cada imputacion no puede superar el `saldo_pendiente` de la obligacion
- `X-Op-Id` evaluado para idempotencia

Reglas de negocio:
- el registro es atomico: si falla la generacion de cualquier imputacion, falla todo el pago con rollback completo
- el pago actualiza `saldo_pendiente` en cada `obligacion_financiera` imputada
- si el request incluye `imputaciones` explicitas, se aplican en el orden informado
- si el request no incluye `imputaciones`, el motor distribuye automaticamente segun el orden base: `fecha_vencimiento ASC`, luego `fecha_emision ASC`; este criterio es la politica base y puede extenderse en versiones futuras sin romper el contrato
- se registra evento en outbox
- `signo` es determinado internamente segun `tipo_movimiento`

Errores posibles:
- `400 APPLICATION_ERROR` — validacion sin equivalente FIN especifico (fallback transversal)
- `400 imputacion_excede_saldo (ERR-FIN-021)` — alguna imputacion excede saldo de obligacion
- `400 saldo_negativo (ERR-FIN-013)` — resultado produciria saldo negativo
- `404 relacion_generadora_no_encontrada (ERR-FIN-001)`
- `404 obligacion_no_encontrada (ERR-FIN-008)` — alguna obligacion referenciada no existe
- `409 relacion_generadora_inactiva (ERR-FIN-002)`
- `409 op_id_duplicado (ERR-FIN-038)`
- `500 INTERNAL_ERROR`

---

### 6.3 `imputaciones`

#### `PATCH /api/v1/financiero/imputaciones/{id_aplicacion_financiera}/reversar`

Objetivo:
- reversion de una imputacion financiera existente
- restaura el saldo de la obligacion afectada al valor previo a la imputacion
- operacion transaccional y atomica

Headers requeridos:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`, `If-Match-Version`

Request:

```json
{
  "motivo": "Error en la asignacion de pago al periodo"
}
```

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_aplicacion_financiera": 1,
    "uid_global": "uuid",
    "version_registro": 2,
    "id_movimiento_financiero": 5,
    "id_obligacion_financiera": 10,
    "importe_aplicado": 15000.00,
    "estado_aplicacion": "revertida", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
    "updated_at": "2026-04-28T14:00:00"
  }
}
```

Validaciones:
- `id_aplicacion_financiera` debe existir y no estar dada de baja
- `If-Match-Version` debe coincidir con `version_registro` vigente
- el estado actual debe permitir reversion (no debe estar ya `anulada` o `revertida`)
- la obligacion afectada debe existir y no estar dada de baja
- la reversion no debe producir inconsistencia de saldo en la obligacion

Reglas de negocio:
- la reversion es atomica: revierte la imputacion y restaura el `saldo_pendiente` de la obligacion
- si la obligacion estaba en estado `cancelada` y la reversion la deja con saldo, debe volver a `pendiente` o `vencida` segun fecha
- se registra evento en outbox
- los estados de imputacion invalidos para reversion: `anulada`, `revertida` (ERR-FIN-025)

Errores posibles:
- `404 imputacion_no_encontrada (ERR-FIN-017)`
- `409 version_esperada_invalida (ERR-FIN-035)`
- `409 reversion_imputacion_invalida (ERR-FIN-025)` — estado actual no admite reversion
- `409 op_id_duplicado (ERR-FIN-038)`
- `500 INTERNAL_ERROR`

---

### 6.4 `servicios-trasladados`

#### `POST /api/v1/financiero/servicios-trasladados/generar-obligacion`

> **CONCEPTUAL / NO IMPLEMENTADO**
>
> Este endpoint es un contrato conceptual derivado de INT-FIN-002 y DER-FINANCIERO. No existe implementacion backend. No existe evento `factura_servicio_registrada`. No existe consumer financiero. La tabla SQL `factura_servicio` existe estructuralmente pero no tiene API backend en el dominio inmobiliario. Este endpoint no debe usarse hasta que exista contrato de integracion completo, API/backend de `factura_servicio` y consumer financiero.

Objetivo conceptual:
- recibir referencia a una `factura_servicio` existente en SQL
- generar o vincular una `relacion_generadora` de tipo `SERVICIO_TRASLADADO`
- generar una `obligacion_financiera` asociada
- resolver el obligado financiero segun las reglas de INT-FIN-002
- la operacion debe ser idempotente: una misma `factura_servicio` no puede generar mas de una obligacion financiera activa

Headers requeridos conceptualmente:
- `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`

Request conceptual:

```json
{
  "id_factura_servicio": 17,
  "observaciones": "Traslado de servicio de expensas — enero 2026"
}
```

Response conceptual `201`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 8,
    "tipo_origen": "SERVICIO_TRASLADADO",
    "id_origen": 17,
    "id_obligacion_financiera": 20,
    "codigo_obligacion": "OBL-0020",
    "importe_original": 1500.00,
    "fecha_emision": "2026-01-15",
    "fecha_vencimiento": "2026-02-15",
    "estado_obligacion": "pendiente",
    "obligados": [
      {
        "id_persona": 5,
        "rol_obligado": "LOCATARIO",
        "porcentaje_responsabilidad": 100.00
      }
    ]
  }
}
```

Validaciones conceptuales:
- `id_factura_servicio` debe existir en SQL y no estar dada de baja
- no debe existir una obligacion financiera activa para la misma `factura_servicio` (idempotencia por `id_factura_servicio`)
- el objeto afectado por la factura (inmueble o unidad funcional) debe ser resoluble
- la resolucion del obligado sigue las reglas de INT-FIN-002 (locatario > ocupante > propietario)
- si el obligado no puede resolverse, no se genera la obligacion exigible automaticamente

Restricciones del estado NO IMPLEMENTADO:
- no existe evento `factura_servicio_registrada`
- no existe consumer financiero que consuma dicho evento
- no existe API/backend para operar `factura_servicio` desde el dominio inmobiliario
- la resolucion de `propietario / responsable operativo` no tiene regla fisica final documentada
- el estado `PENDIENTE_RESOLUCION_OBLIGADO` es conceptual y no implementado

---

## 7. Reads

### 7.1 `relaciones-generadoras`

#### `GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}`

Objetivo:
- consulta integral de una relacion generadora con sus obligaciones activas y composiciones

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "uid_global": "uuid",
    "version_registro": 2,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "descripcion": "Relacion generadora para contrato de alquiler CA-0042",
    "fecha_alta": "2026-04-28T10:00:00",
    "obligaciones": [
      {
        "id_obligacion_financiera": 10,
        "codigo_obligacion": "OBL-0010",
        "fecha_emision": "2026-04-28",
        "fecha_vencimiento": "2026-05-10",
        "importe_original": 15000.00,
        "saldo_pendiente": 15000.00,
        "estado_obligacion": "pendiente",
        "obligados": [
          {
            "id_obligacion_obligado": 1,
            "id_persona": 5,
            "rol_obligado": "LOCATARIO",
            "porcentaje_responsabilidad": 100.00
          }
        ],
        "composicion": [
          {
            "id_composicion_obligacion": 1,
            "id_concepto_financiero": 3,
            "importe": 15000.00,
            "observaciones": "Capital mensual"
          }
        ]
      }
    ],
    "resumen": {
      "total_obligaciones": 1,
      "saldo_total_pendiente": 15000.00,
      "estado_deuda": "con_deuda"
    },
    "created_at": "2026-04-28T10:00:00",
    "updated_at": "2026-04-28T10:05:00",
    "deleted_at": null
  }
}
```

Errores posibles:
- `404 NOT_FOUND` — relacion no encontrada o dada de baja
- `500 INTERNAL_ERROR`

---

#### `GET /api/v1/financiero/relaciones-generadoras`

Objetivo:
- listado paginado de relaciones generadoras con filtros basicos

Filtros permitidos:
- `tipo_origen` — filtrar por tipo de origen (`VENTA`, `CONTRATO_ALQUILER`, `SERVICIO_TRASLADADO`)
- `id_origen` — filtrar por ID del origen en su dominio
- `vigente` — excluir dadas de baja cuando `true`

Paginacion basica:
- `limit`
- `offset`

Response `200`:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_relacion_generadora": 1,
        "uid_global": "uuid",
        "version_registro": 2,
        "tipo_origen": "CONTRATO_ALQUILER",
        "id_origen": 42,
        "descripcion": "Relacion generadora CA-0042",
        "fecha_alta": "2026-04-28T10:00:00",
        "saldo_total_pendiente": 15000.00,
        "deleted_at": null
      }
    ],
    "total": 1
  }
}
```

Errores posibles:
- `400 APPLICATION_ERROR` — filtros invalidos (fallback transversal)
- `500 INTERNAL_ERROR`

---

#### `GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/obligaciones`

Objetivo:
- listado de obligaciones financieras de una relacion generadora especifica

Filtros permitidos:
- `estado_obligacion` — `pendiente`, `vencida`, `parcialmente_cancelada`, `cancelada`
- `vigente`

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "items": [
      {
        "id_obligacion_financiera": 10,
        "uid_global": "uuid",
        "version_registro": 1,
        "codigo_obligacion": "OBL-0010",
        "fecha_emision": "2026-04-28",
        "fecha_vencimiento": "2026-05-10",
        "importe_original": 15000.00,
        "saldo_pendiente": 15000.00,
        "estado_obligacion": "pendiente",
        "observaciones": null,
        "deleted_at": null
      }
    ],
    "total": 1
  }
}
```

Errores posibles:
- `404 NOT_FOUND` — relacion no encontrada
- `500 INTERNAL_ERROR`

---

### 7.2 `obligaciones`

#### `GET /api/v1/financiero/obligaciones/{id_obligacion_financiera}`

Objetivo:
- consulta de una obligacion financiera con su composicion, obligados e imputaciones

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_obligacion_financiera": 10,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_relacion_generadora": 1,
    "codigo_obligacion": "OBL-0010",
    "fecha_emision": "2026-04-28",
    "fecha_vencimiento": "2026-05-10",
    "importe_original": 15000.00,
    "saldo_pendiente": 15000.00,
    "estado_obligacion": "pendiente",
    "observaciones": null,
    "obligados": [
      {
        "id_obligacion_obligado": 1,
        "id_persona": 5,
        "rol_obligado": "LOCATARIO",
        "porcentaje_responsabilidad": 100.00
      }
    ],
    "composicion": [
      {
        "id_composicion_obligacion": 1,
        "id_concepto_financiero": 3,
        "importe": 15000.00,
        "observaciones": "Capital mensual"
      }
    ],
    "imputaciones": [
      {
        "id_aplicacion_financiera": 1,
        "id_movimiento_financiero": 5,
        "importe_aplicado": 0.00,
        "tipo_aplicacion": null,
        "fecha_aplicacion": null,
        "estado_aplicacion": null // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
      }
    ],
    "created_at": "2026-04-28T10:05:00",
    "updated_at": "2026-04-28T10:05:00",
    "deleted_at": null
  }
}
```

Errores posibles:
- `404 NOT_FOUND` — obligacion no encontrada o dada de baja
- `500 INTERNAL_ERROR`

---

#### `GET /api/v1/financiero/obligaciones`

Objetivo:
- listado paginado de obligaciones financieras con filtros

Filtros permitidos:
- `id_relacion_generadora`
- `estado_obligacion` — `pendiente`, `vencida`, `parcialmente_cancelada`, `cancelada`
- `fecha_emision_desde`
- `fecha_emision_hasta`
- `fecha_vencimiento_desde`
- `fecha_vencimiento_hasta`
- `con_saldo_pendiente` — `true` para mostrar solo obligaciones con `saldo_pendiente > 0`
- `vigente`

Paginacion basica:
- `limit`
- `offset`

Response `200`:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id_obligacion_financiera": 10,
        "id_relacion_generadora": 1,
        "codigo_obligacion": "OBL-0010",
        "fecha_emision": "2026-04-28",
        "fecha_vencimiento": "2026-05-10",
        "importe_original": 15000.00,
        "saldo_pendiente": 15000.00,
        "estado_obligacion": "pendiente",
        "deleted_at": null
      }
    ],
    "total": 1
  }
}
```

Errores posibles:
- `400 APPLICATION_ERROR` — filtros invalidos (fallback transversal)
- `500 INTERNAL_ERROR`

---

### 7.3 `pagos`

> **ATENCION:** `movimiento_financiero` NO posee FK directa a `relacion_generadora` ni a `obligacion_financiera` en el SQL vigente. La relacion entre un pago y sus obligaciones se establece exclusivamente a traves de `aplicacion_financiera`. Cualquier consulta que requiera vincular movimientos con relaciones generadoras debe hacerse navegando por `aplicacion_financiera.id_obligacion_financiera` → `obligacion_financiera.id_relacion_generadora`.

#### `GET /api/v1/financiero/pagos/{id_movimiento_financiero}`

Objetivo:
- consulta de un movimiento financiero registrado con sus imputaciones

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_movimiento_financiero": 5,
    "uid_global": "uuid",
    "version_registro": 1,
    "tipo_movimiento": "PAGO",
    "importe": 15000.00,
    "signo": "HABER",
    "fecha_movimiento": "2026-04-28T10:30:00",
    "estado_movimiento": "registrado",
    "observaciones": "Pago mensual abril 2026",
    "imputaciones": [
      {
        "id_aplicacion_financiera": 1,
        "id_obligacion_financiera": 10,
        "id_composicion_obligacion": null,
        "importe_aplicado": 15000.00,
        "tipo_aplicacion": "DIRECTA",
        "orden_aplicacion": 1,
        "origen_automatico_o_manual": "MANUAL",
        "fecha_aplicacion": "2026-04-28T10:30:00",
        "observaciones": null
      }
    ],
    "created_at": "2026-04-28T10:30:00",
    "updated_at": "2026-04-28T10:30:00",
    "deleted_at": null
  }
}
```

Errores posibles:
- `404 NOT_FOUND` — movimiento no encontrado o dado de baja
- `500 INTERNAL_ERROR`

---

#### `GET /api/v1/financiero/pagos/{id_movimiento_financiero}/imputaciones`

Objetivo:
- listado de imputaciones de un movimiento financiero especifico

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_movimiento_financiero": 5,
    "items": [
      {
        "id_aplicacion_financiera": 1,
        "uid_global": "uuid",
        "version_registro": 1,
        "id_obligacion_financiera": 10,
        "id_composicion_obligacion": null,
        "importe_aplicado": 15000.00,
        "tipo_aplicacion": "DIRECTA",
        "orden_aplicacion": 1,
        "origen_automatico_o_manual": "MANUAL",
        "fecha_aplicacion": "2026-04-28T10:30:00",
        "estado_aplicacion": "aplicada", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
        "observaciones": null,
        "deleted_at": null
      }
    ],
    "total": 1
  }
}
```

Nota sobre `estado_aplicacion`: campo no existe en SQL vigente de `aplicacion_financiera`; se documenta como campo contractual esperado; su almacenamiento fisico es PENDIENTE.

Errores posibles:
- `404 NOT_FOUND` — movimiento no encontrado
- `500 INTERNAL_ERROR`

---

### 7.4 Consultas financieras

#### `GET /api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}/estado-deuda`

Objetivo:
- consulta del estado de deuda consolidado de una relacion generadora a fecha dada
- reconstruye el estado financiero dinamicamente segun SRV-FIN-012

Query params:
- `fecha_referencia` — fecha de corte para el calculo; si no se informa, se usa la fecha del sistema

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_relacion_generadora": 1,
    "tipo_origen": "CONTRATO_ALQUILER",
    "id_origen": 42,
    "estado_relacion_generadora": "activa", // CAMPO DERIVADO (NO PERSISTIDO EN SQL)
    "fecha_referencia": "2026-04-28",
    "estado_deuda": "con_deuda",
    "saldo_total_pendiente": 15000.00,
    "obligaciones_pendientes": 1,
    "obligaciones_vencidas": 0,
    "obligaciones_canceladas": 0,
    "detalle": [
      {
        "id_obligacion_financiera": 10,
        "codigo_obligacion": "OBL-0010",
        "fecha_vencimiento": "2026-05-10",
        "importe_original": 15000.00,
        "saldo_pendiente": 15000.00,
        "estado_obligacion": "pendiente",
        "dias_vencido": 0
      }
    ]
  }
}
```

Valores posibles de `estado_deuda` (EST-FIN):
- `sin_deuda` — no hay deuda exigible
- `con_deuda` — existe deuda vigente
- `deuda_parcial` — deuda parcialmente cancelada con saldo remanente
- `deuda_vencida` — existe deuda con vencimiento superado
- `deuda_cancelada` — toda la deuda fue cancelada

Errores posibles:
- `404 NOT_FOUND` — relacion no encontrada
- `409 inconsistencia_calculo_deuda (ERR-FIN-033)` — resultado inconsistente
- `500 INTERNAL_ERROR`

---

## 8. Resolucion de obligado financiero (INT-FIN-002)

Esta seccion resume la decision documental INT-FIN-002 aplicada a los endpoints de este contrato.

### Principio rector

`financiero` genera la obligacion pero no inventa el obligado.

El obligado se resuelve desde los dominios origen:

- `comercial` → compradores de la venta
- `locativo` → locatarios del contrato
- `inmobiliario` → locatario > ocupante > propietario (segun periodo y estado)

### Resolucion por tipo de origen

**VENTA:**
- obligado = comprador o compradores de `cliente_comprador` o `relacion_persona_rol`
- politica de multiples compradores: PENDIENTE

**CONTRATO_ALQUILER:**
- obligado = locatario o locatarios vigentes de `relacion_persona_rol`
- garantes y codeudores como obligados complementarios: PENDIENTE

**SERVICIO_TRASLADADO:**
- si existe contrato locativo vigente sobre el objeto y periodo: obligado = locatario
- si existe ocupacion vigente sin contrato: obligado = ocupante responsable
- si no existe ocupacion vigente: obligado = propietario / responsable operativo
- si no puede resolverse: no generar obligacion exigible automaticamente; dejar en estado `PENDIENTE_RESOLUCION_OBLIGADO`
- `PENDIENTE_RESOLUCION_OBLIGADO` es un estado conceptual no implementado

### Estado de implementacion de la resolucion

Queda PENDIENTE de implementacion:

- servicio formal de resolucion de obligado
- endpoint o consumer de resolucion
- API/backend para operar `factura_servicio` desde inmobiliario
- evento `factura_servicio_registrada`
- reglas fisicas para propietario / responsable operativo
- estado fisico `PENDIENTE_RESOLUCION_OBLIGADO`
- politica de multiples obligados, solidaridad, porcentajes y prorrateo

---

## 9. Estado de implementacion por bloque

| Bloque | Entidad SQL | Router backend | Estado |
|--------|-------------|----------------|--------|
| Relaciones generadoras — alta | `relacion_generadora` | EXISTE MVP | IMPLEMENTADO MVP |
| Relaciones generadoras — reads basicos | `relacion_generadora` | EXISTE MVP | IMPLEMENTADO MVP |
| Relaciones generadoras — activar | `relacion_generadora` | NO EXISTE | PENDIENTE / FUERA MVP |
| Relaciones generadoras — cancelar | `relacion_generadora` | NO EXISTE | PENDIENTE / FUERA MVP |
| Relaciones generadoras — finalizar | `relacion_generadora` | NO EXISTE | PENDIENTE / FUERA MVP |
| Obligaciones — lectura | `obligacion_financiera` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Composicion — lectura | `composicion_obligacion` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Obligados — lectura | `obligacion_obligado` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Pagos — simulacion | `movimiento_financiero` (no persiste) | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Pagos — registro | `movimiento_financiero` + `aplicacion_financiera` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Imputaciones — reversion | `aplicacion_financiera` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Estado de deuda — consulta | derivado de `obligacion_financiera` | NO EXISTE | DOCUMENTADO / NO IMPLEMENTADO |
| Servicios trasladados — generar obligacion | `factura_servicio` (SQL existe; API no) | NO EXISTE | CONCEPTUAL / NO IMPLEMENTADO |
| Resolucion de obligado | multiples dominios | NO EXISTE | CONCEPTUAL / NO IMPLEMENTADO |

### Campos SQL con drift documental

| Campo | Entidad | Estado en SQL | Nota |
|-------|---------|--------------|------|
| `estado_relacion_generadora` | `relacion_generadora` | NO EXISTE en SQL | conceptual, no persistido y no devuelto por el MVP; no agregar columna todavia |
| `estado_aplicacion` | `aplicacion_financiera` | NO EXISTE en SQL | EST-FIN documenta estados de imputacion; almacenamiento fisico PENDIENTE |
| Columna FK directa a `relacion_generadora` en `movimiento_financiero` | `movimiento_financiero` | NO EXISTE | asociacion via `aplicacion_financiera` |

### Proximos pasos para implementacion

Para materializar este contrato en backend se requiere, en orden logico:

1. router financiero (`api/routers/financiero_router.py`)
2. schemas Pydantic para cada endpoint
3. servicios de aplicacion por caso de uso (SRV-FIN-001 a SRV-FIN-008)
4. repositorios de persistencia para cada entidad financiera
5. decision posterior sobre persistencia fisica de `estado_relacion_generadora`; no agregar columna en el MVP
6. columna `estado_aplicacion` en SQL para `aplicacion_financiera`
7. registro de outbox para eventos financieros
8. API backend para `factura_servicio` en dominio inmobiliario (prerequisito de SERVICIO_TRASLADADO)
9. evento `factura_servicio_registrada` y consumer financiero
10. servicio de resolucion de obligado (INT-FIN-002)
