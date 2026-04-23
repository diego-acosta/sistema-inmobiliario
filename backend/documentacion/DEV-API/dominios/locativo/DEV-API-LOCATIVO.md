# DEV-API-LOCATIVO - Dominio Locativo

## Estado del documento

- version: `1.0`
- estado: `propuesto para implementacion (v1 minimo)`
- fuente: `DER-LOCATIVO + DEV-SRV locativo + SQL real`
- ultima actualizacion: `2026-04-23`
- caracter: `normativo para diseno v1; no materializado aun en backend`

## 1. Alcance

Este documento define el contrato minimo `v1` propuesto para el dominio `locativo`, validado contra:

- `backend/documentacion/DER/DER-LOCATIVO.md`
- `backend/documentacion/DEV-SRV/dominios/locativo/SRV-LOC-001-gestion-de-contratos-de-alquiler.md`
- `backend/documentacion/DEV-SRV/dominios/locativo/SRV-LOC-002-gestion-de-condiciones-locativas.md`
- catalogos `RN-LOC`, `ERR-LOC`, `EST-LOC`, `CU-LOC`
- `backend/database/schema_inmobiliaria_20260418.sql`

El objetivo de esta version es fijar un contrato operativo minimo para futura implementacion, sin inventar bloques que hoy no esten cerrados por DER y documentacion vigente.

El alcance queda limitado a:

- `contrato_alquiler` como recurso raiz
- `contrato_objeto_locativo` como detalle embebido del contrato
- `condicion_economica_alquiler` como recurso hijo del contrato

Quedan explicitamente fuera de `v1`:

- `ajuste_alquiler`
- `modificacion_locativa`
- `rescision_finalizacion_alquiler`
- `entrega_restitucion_inmueble`
- `solicitud_alquiler`
- `reserva_locativa`
- write local de intervinientes contractuales por `relacion_persona_rol`
- renovaciones por `id_contrato_anterior`
- exposicion de `cartera_locativa` como parte del contrato publico minimo

## 2. Fuente de verdad y criterio operativo

Orden de prioridad para este contrato:

- SQL real
- `DER-LOCATIVO.md`
- `SRV-LOC-001`
- `SRV-LOC-002`
- `RN-LOC`, `ERR-LOC`, `EST-LOC`, `CU-LOC`

Criterios aplicados:

- no se inventan entidades ni endpoints por fuera de los modos explicitados en `DEV-SRV`
- `contrato_alquiler` se expone como raiz juridica del dominio
- `contrato_objeto_locativo` no se expone como recurso autonomo en `v1`; se consume embebido dentro del contrato
- `condicion_locativa` se consolida al nombre persistido real `condicion_economica_alquiler`
- no se exponen en `v1` atributos SQL que pertenecen a flujos fuera de alcance:
  - `id_reserva_locativa`
  - `id_cartera_locativa`
  - `id_contrato_anterior`
- no se exponen write locales de personas mientras sigan dependiendo de soporte transversal por `relacion_persona_rol`
- la validacion de partes principales del contrato queda desacoplada del payload local y debe resolverse por soporte transversal antes de la activacion

## 3. Criterios de diseno

- no debe existir un prefijo `/api/v1/locativo/...`; el proyecto expone recursos por dominio semantico en la raiz de `/api/v1`
- el naming publico usa plural kebab-case:
  - `contratos-alquiler`
  - `condiciones-economicas-alquiler`
- `contrato_alquiler` es el recurso raiz
- `contrato_objeto_locativo` forma parte del payload del contrato y no tiene endpoint propio en `v1`
- `condicion_economica_alquiler` se expone anidada bajo su contrato padre
- este `v1` minimo no define contrato generico de cambio de estado; solo transiciones cerradas
- estados contractuales incluidos en `v1`:
  - `borrador`
  - `activo`
  - `cancelado`
  - `finalizado`
- estados catalogados pero fuera de `v1`:
  - `en_ejecucion`
  - `rescindido`
- las condiciones economicas no exponen `estado` persistido propio porque SQL no materializa columna de estado

## 4. Ownership

- `locativo` es dueno semantico de:
  - `contrato_alquiler`
  - `contrato_objeto_locativo`
  - `condicion_economica_alquiler`
- `personas` mantiene ownership de identidad base y del soporte `relacion_persona_rol`
- `inmobiliario` mantiene ownership de `inmueble`, `unidad_funcional`, `disponibilidad` y `ocupacion`
- `financiero` mantiene ownership de deuda, obligaciones, pagos y calculo economico derivado
- `documental` mantiene ownership de `documento_logico`, `documento_entidad` y numeracion documental

## 5. Convencion de errores y headers

Formato de error esperado:

```json
{
  "ok": false,
  "error_code": "CODIGO",
  "error_message": "Mensaje",
  "details": {
    "errors": []
  }
}
```

Formato de exito esperado:

```json
{
  "ok": true,
  "data": {}
}
```

Codigos transversales a reutilizar:

- `NOT_FOUND`
- `APPLICATION_ERROR`
- `CONCURRENCY_ERROR`
- `INTERNAL_ERROR`

Marcadores de dominio esperables para `details.errors`:

- `contrato_no_encontrado`
- `contrato_duplicado`
- `contrato_sin_objeto`
- `contrato_sin_partes`
- `contrato_solapado`
- `vigencia_contrato_invalida`
- `estado_contrato_invalido`
- `transicion_estado_contrato_invalida`
- `condicion_economica_no_encontrada`
- `condicion_economica_invalida`
- `condicion_economica_duplicada`
- `vigencia_condicion_invalida`
- `inconsistencia_condicion_economica`

Headers write esperados para `v1`:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`
- `If-Match-Version` en update y transiciones

Uso esperado de versionado:

- `POST /api/v1/contratos-alquiler` no requiere `If-Match-Version`
- `PUT /api/v1/contratos-alquiler/{id_contrato_alquiler}` requiere `If-Match-Version`
- `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/activar` requiere `If-Match-Version`
- `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/cancelar` requiere `If-Match-Version`
- `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/finalizar` requiere `If-Match-Version`
- `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/baja` requiere `If-Match-Version`
- `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler` no requiere `If-Match-Version`
- `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler/{id_condicion_economica}/cerrar-vigencia` requiere `If-Match-Version`

## 6. Writes

### 6.1 `contrato_alquiler`

#### `POST /api/v1/contratos-alquiler`

Objetivo:

- alta de contrato de alquiler en estado inicial `borrador`

Request:

```json
{
  "codigo_contrato": "CA-0001",
  "fecha_inicio": "2026-05-01",
  "fecha_fin": "2027-04-30",
  "observaciones": "Contrato inicial",
  "objetos": [
    {
      "id_inmueble": 100,
      "observaciones": "Local principal"
    }
  ]
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_contrato_alquiler": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "codigo_contrato": "CA-0001",
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2027-04-30",
    "estado_contrato": "borrador",
    "observaciones": "Contrato inicial",
    "objetos": [
      {
        "id_contrato_objeto": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "observaciones": "Local principal"
      }
    ],
    "condiciones_economicas_alquiler": [],
    "created_at": "2026-04-23T10:00:00",
    "updated_at": "2026-04-23T10:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- `codigo_contrato` requerido y unico
- `fecha_inicio` requerida
- `fecha_fin` debe ser nula o mayor o igual a `fecha_inicio`
- `objetos` requerido con al menos un elemento
- cada item de `objetos` debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- cada objeto referenciado debe existir
- no deben repetirse objetos dentro del mismo payload
- no debe existir superposicion contractual incompatible sobre el mismo objeto locativo
- no se reciben en `v1`:
  - `id_reserva_locativa`
  - `id_cartera_locativa`
  - `id_contrato_anterior`
  - personas intervinientes
  - condiciones economicas en el mismo alta
- `estado_contrato` no se recibe por request; se asigna internamente como `borrador`

Reglas de negocio:

- `contrato_alquiler` es la raiz del agregado
- `objetos` representa `contrato_objeto_locativo` y no un recurso autonomo en `v1`
- el alta no genera por si sola deuda ni obligaciones financieras
- el alta no materializa por si sola ocupacion
- el alta se ejecuta de forma transaccional sobre contrato y objetos
- las personas intervinientes quedan fuera de este `v1` minimo porque hoy dependen de soporte transversal por `relacion_persona_rol`
- el contrato puede existir en `borrador` sin exponer aun sus partes en el payload local, pero no debe activarse sin locador y locatario resueltos por soporte transversal

#### `PUT /api/v1/contratos-alquiler/{id_contrato_alquiler}`

Objetivo:

- actualizar datos contractuales basicos y el conjunto completo de objetos de un contrato en `borrador`

Request:

```json
{
  "codigo_contrato": "CA-0001-EDIT",
  "fecha_inicio": "2026-05-01",
  "fecha_fin": "2027-05-31",
  "observaciones": "Contrato ajustado antes de activacion",
  "objetos": [
    {
      "id_unidad_funcional": 200,
      "observaciones": "Unidad definitiva"
    }
  ]
}
```

Response:

- mismo shape que `POST /api/v1/contratos-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato debe existir y no estar dado de baja
- el contrato debe estar en estado `borrador`
- `codigo_contrato` requerido y unico
- `fecha_inicio` requerida
- `fecha_fin` debe ser nula o mayor o igual a `fecha_inicio`
- `objetos` debe representar el conjunto completo vigente del contrato
- se revalidan todas las reglas de objetos del alta

Reglas de negocio:

- la modificacion de `v1` no expone cambio parcial de objetos; reemplaza el conjunto completo embebido
- la modificacion no cambia `estado_contrato`
- la modificacion no administra condiciones economicas
- la modificacion no genera efectos financieros
- la modificacion no materializa ocupacion
- si mas adelante se requiere cambiar un contrato ya activo sin sustituirlo, ese caso debe resolverse por `modificacion_locativa`, que queda fuera de `v1`

#### `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/activar`

Objetivo:

- activar un contrato para llevarlo a estado `activo`

Request:

- sin body

Response:

- mismo shape que `POST /api/v1/contratos-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato debe existir y no estar dado de baja
- el estado origen valido en `v1` es `borrador`
- el contrato debe conservar al menos un objeto asociado
- el contrato debe tener partes principales validamente resueltas por soporte transversal
- no debe existir superposicion contractual incompatible sobre los objetos asociados

Reglas de negocio:

- esta `v1` no define activacion generica hacia `en_ejecucion`
- la activacion solo explicita `borrador -> activo`
- la activacion no crea por si sola ocupacion
- la activacion no genera por si sola obligaciones financieras

#### `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/cancelar`

Objetivo:

- cancelar un contrato antes de su ejecucion operativa

Request:

- sin body

Response:

- mismo shape que `POST /api/v1/contratos-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato debe existir y no estar dado de baja
- el estado origen valido en `v1` es `borrador`

Reglas de negocio:

- esta `v1` usa `cancelar` solo para cierre previo a ejecucion
- no reemplaza rescision ni finalizacion
- la cancelacion no genera efectos financieros ni de ocupacion

#### `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/finalizar`

Objetivo:

- finalizar un contrato por cierre ordinario de vigencia

Request:

- sin body

Response:

- mismo shape que `POST /api/v1/contratos-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato debe existir y no estar dado de baja
- el estado origen valido en `v1` es `activo`

Reglas de negocio:

- esta `v1` no incorpora rescision anticipada
- la finalizacion expresa el cierre ordinario del contrato
- si se necesita cierre anticipado debe resolverse en el futuro por `rescision_finalizacion_alquiler`

#### `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/baja`

Objetivo:

- aplicar baja logica sobre un contrato aun invalido para operacion

Request:

- sin body

Response:

- mismo shape que `POST /api/v1/contratos-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato debe existir y no estar dado de baja
- el estado origen valido en `v1` es `borrador`

Reglas de negocio:

- la baja es logica y se materializa por `deleted_at`
- una vez cancelado o finalizado, el contrato se preserva como historia y no se baja por este endpoint en `v1`

### 6.2 `condicion_economica_alquiler`

#### `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler`

Objetivo:

- registrar una condicion economica para un contrato

Request:

```json
{
  "monto_base": 150000.00,
  "periodicidad": "mensual",
  "moneda": "ARS",
  "fecha_desde": "2026-05-01",
  "fecha_hasta": "2026-10-31",
  "observaciones": "Canon inicial"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_condicion_economica": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_contrato_alquiler": 1,
    "monto_base": 150000.00,
    "periodicidad": "mensual",
    "moneda": "ARS",
    "fecha_desde": "2026-05-01",
    "fecha_hasta": "2026-10-31",
    "observaciones": "Canon inicial",
    "created_at": "2026-04-23T10:10:00",
    "updated_at": "2026-04-23T10:10:00",
    "deleted_at": null
  }
}
```

Validaciones:

- el contrato padre debe existir y no estar dado de baja
- el contrato padre debe encontrarse en estado `borrador` o `activo`
- `monto_base` requerido y mayor que cero
- `fecha_desde` requerida
- `fecha_hasta` debe ser nula o mayor o igual a `fecha_desde`
- la vigencia de la condicion no debe solaparse invalidamente con otra condicion del mismo contrato
- la condicion debe ser coherente con `periodicidad` y `moneda` cuando se informen

Reglas de negocio:

- esta entidad es la forma persistida vigente de la configuracion economica del contrato
- la condicion economica no genera por si sola obligaciones financieras
- `v1` no incorpora `ajuste_alquiler`

#### `PATCH /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler/{id_condicion_economica}/cerrar-vigencia`

Objetivo:

- cerrar la vigencia de una condicion economica existente

Request:

```json
{
  "fecha_hasta": "2026-10-31"
}
```

Response:

- mismo shape que `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler`

Validaciones:

- requiere `If-Match-Version`
- el contrato padre debe existir y no estar dado de baja
- la condicion debe existir, pertenecer al contrato y no estar dada de baja
- `fecha_hasta` requerida
- `fecha_hasta` debe ser mayor o igual a `fecha_desde`

Reglas de negocio:

- `v1` no define update in-place de todos los campos de la condicion
- el cambio de canon o periodicidad se expresa cerrando una vigencia y creando una nueva condicion
- el cierre de vigencia debe preservarse historicamente

## 7. Reads

### 7.1 `contrato_alquiler`

#### `GET /api/v1/contratos-alquiler/{id_contrato_alquiler}`

Objetivo:

- detalle de contrato de alquiler

Response:

```json
{
  "ok": true,
  "data": {
    "id_contrato_alquiler": 1,
    "version_registro": 3,
    "codigo_contrato": "CA-0001",
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2027-04-30",
    "estado_contrato": "activo",
    "observaciones": "Contrato inicial",
    "objetos": [
      {
        "id_contrato_objeto": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "observaciones": "Local principal"
      }
    ],
    "condiciones_economicas_alquiler": [
      {
        "id_condicion_economica": 1,
        "monto_base": 150000.00,
        "periodicidad": "mensual",
        "moneda": "ARS",
        "fecha_desde": "2026-05-01",
        "fecha_hasta": "2026-10-31",
        "observaciones": "Canon inicial"
      }
    ],
    "deleted_at": null
  }
}
```

Shape publico real propuesto:

- `data` expone solo:
  - `id_contrato_alquiler`
  - `version_registro`
  - `codigo_contrato`
  - `fecha_inicio`
  - `fecha_fin`
  - `estado_contrato`
  - `observaciones`
  - `objetos`
  - `condiciones_economicas_alquiler`
  - `deleted_at`
- `data` no expone en `v1`:
  - `id_reserva_locativa`
  - `id_cartera_locativa`
  - `id_contrato_anterior`
  - intervinientes por `relacion_persona_rol`

#### `GET /api/v1/contratos-alquiler`

Objetivo:

- listado de contratos de alquiler

Filtros permitidos:

- `codigo_contrato`
- `estado_contrato`
- `id_inmueble`
- `id_unidad_funcional`
- `fecha_desde`
- `fecha_hasta`

Paginacion basica:

- `limit`
- `offset`

Response:

```json
{
  "ok": true,
  "data": {
    "items": [],
    "total": 0
  }
}
```

Observacion:

- en `v1` no se definen filtros por personas intervinientes

### 7.2 `condicion_economica_alquiler`

#### `GET /api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler`

Objetivo:

- listado de condiciones economicas vigentes e historicas de un contrato

Filtros permitidos:

- `vigente`
- `fecha_desde`
- `fecha_hasta`
- `moneda`
- `periodicidad`

Response:

```json
{
  "ok": true,
  "data": {
    "items": [],
    "total": 0
  }
}
```

Observacion:

- `v1` no define `GET` global de condiciones economicas fuera del contrato padre

## 8. Reglas visibles del contrato

- `contrato_alquiler` es la raiz del agregado locativo minimo
- `contrato_objeto_locativo` se consume embebido en el contrato
- `condicion_economica_alquiler` se expone solo bajo el contrato padre
- `v1` no expone `solicitud_alquiler` ni `reserva_locativa`
- `v1` no expone `ajuste_alquiler`, `modificacion_locativa`, `rescision_finalizacion_alquiler` ni `entrega_restitucion_inmueble`
- `v1` no expone write local de partes intervinientes porque esa semantica sigue dependiendo de soporte transversal
- la activacion del contrato debe revalidar que las partes principales ya existan por soporte transversal
- el contrato no debe superponerse invalidamente sobre el mismo objeto locativo
- la condicion economica debe respetar vigencias sin solapamiento incompatible
- el dominio locativo no calcula deuda ni pagos
- el dominio locativo no absorbe ownership de `disponibilidad` ni `ocupacion`

## 9. Bloques fuera de `v1`

- `POST /api/v1/solicitudes-alquiler`
- `POST /api/v1/reservas-locativas`
- `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/ajustes-alquiler`
- `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/modificaciones-locativas`
- `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/rescisiones-finalizaciones`
- `POST /api/v1/contratos-alquiler/{id_contrato_alquiler}/entregas-restituciones`
- gestion local de intervinientes por `relacion_persona_rol`
- renovaciones por `id_contrato_anterior`
- soporte de `en_ejecucion` y `rescindido` como transiciones de API cerradas

## 10. Notas de implementacion

- este documento define un contrato objetivo minimo para futura implementacion
- no debe leerse como contrato ya materializado en routers, schemas, services o tests
- si durante la implementacion aparece necesidad de exponer intervinientes, reserva, rescision o entrega, debe abrirse un bloque adicional y no ampliarse este `v1` por arrastre
- si el backend futuro decide exponer `contrato_objeto_locativo` como recurso autonomo, ese cambio debera justificarse contra `DER-LOCATIVO` porque hoy el modelo minimo lo trata como detalle embebido
