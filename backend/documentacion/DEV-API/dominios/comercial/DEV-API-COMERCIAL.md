# DEV-API-COMERCIAL - Dominio Comercial

## Estado del documento

- version: `1.3`
- estado: `contrato oficial vigente (v1)`
- fuente: `DER comercial adaptado + SQL real + convenciones vigentes del backend`
- ultima actualizacion: `2026-04-23`
- caracter: `normativo para el surface publico actual del dominio comercial`

## 1. Alcance

Este documento define el contrato oficial vigente de API `v1` del dominio `comercial`, correspondiente al surface realmente materializado hoy en backend, tomando como base:

- `backend/documentacion/DER/DER-COMERCIAL.md`
- `backend/database/schema_inmobiliaria_20260418.sql`
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`
- `backend/documentacion/DEV-SRV/dominios/comercial`
- patrones vigentes de `personas` e `inmobiliario`

El alcance del contrato queda limitado a los bloques que existen estructuralmente en SQL y que hoy tienen surface backend expuesto o lectura materializada. Todo lo que no figure aqui debe considerarse fuera del contrato oficial vigente:

- `reserva_venta`
- `venta`
- `instrumento_compraventa`
- `cesion`
- `escrituracion`

Quedan fuera de este documento:

- `rescision_venta`
- `cliente_comprador` como API propia
- API documental comercial propia
- reportes y consultas consolidadas de corte analitico

## 2. Fuente de verdad y criterio operativo

Orden de prioridad para este contrato:

- SQL real
- DER comercial adaptado
- arquitectura vigente del dominio
- `DEV-SRV` como fuente funcional complementaria
- patrones de naming, errores y headers observables en `personas` e `inmobiliario`

Criterios aplicados:

- no se inventan entidades fuera de DB
- `reserva_venta` materializa su relacion multiobjeto por `reserva_venta_objeto_inmobiliario`
- no se exponen como recursos autonomos `venta_objeto_inmobiliario` ni `instrumento_objeto_inmobiliario`
- `venta` es la operacion comercial principal
- `instrumento_compraventa` es formalizacion documental o juridica de una `venta`
- `cesion` y `escrituracion` dependen de `venta`
- cuando una necesidad funcional existe en `DEV-SRV` pero no tiene soporte estructural en SQL, el contrato no la eleva a payload write

## 3. Criterios de diseno

- no debe existir un prefijo `/api/v1/comercial/...`; el proyecto expone recursos por dominio semantico en la raiz de `/api/v1`
- el naming publico usa plural kebab-case:
  - `reservas-venta`
  - `ventas`
  - `instrumentos-compraventa`
  - `cesiones`
  - `escrituraciones`
- los recursos hijos de `venta` se crean y listan anidados bajo la venta padre
- en esta `v1` real no se documentan endpoints no materializados
- los estados no deben tratarse como texto libre
- `cesion` y `escrituracion` no exponen `estado_*` en write porque hoy no existe columna persistente para ese dato
- los intervinientes comerciales siguen resueltos hoy por soporte transversal y no forman parte del payload write local de estos recursos

## 4. Ownership

- `comercial` es dueno semantico de:
  - `reserva_venta`
  - `venta`
  - `instrumento_compraventa`
  - `cesion`
  - `escrituracion`
  - `cliente_comprador` como rol funcional, aunque no tenga API propia en este contrato
- `personas` provee identidad base e infraestructura de relacion persona-contexto hoy materializada por `relacion_persona_rol`
- `inmobiliario` provee `inmueble` y `unidad_funcional`
- `financiero` puede consumir origenes comerciales, pero no absorbe la semantica de compraventa
- `documental` sigue siendo soporte transversal y no redefine el ownership de `instrumento_compraventa`

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

Headers write observables:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id` es requerido en:
  - `PUT /api/v1/reservas-venta/{id_reserva_venta}`
  - `PATCH /api/v1/reservas-venta/{id_reserva_venta}/baja`
  - transiciones de `reserva_venta`: `activar`, `cancelar`, `vencer`, `confirmar`
  - `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`
  - `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales`
  - `PATCH /api/v1/ventas/{id_venta}/confirmar`
  - `POST /api/v1/ventas/{id_venta}/instrumentos-compraventa`
  - `POST /api/v1/ventas/{id_venta}/cesiones`
  - `POST /api/v1/ventas/{id_venta}/escrituraciones`
- `POST /api/v1/reservas-venta` no exige hoy `X-Instalacion-Id`
- `If-Match-Version` es requerido en:
  - `PUT /api/v1/reservas-venta/{id_reserva_venta}`
  - `PATCH /api/v1/reservas-venta/{id_reserva_venta}/baja`
  - transiciones de `reserva_venta`: `activar`, `cancelar`, `vencer`, `confirmar`
  - `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`
  - `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales`
  - `PATCH /api/v1/ventas/{id_venta}/confirmar`

### Reglas operativas transaccionales

- las operaciones criticas que produzcan transicion de estado comercial o actualicen efectos acoplados del dominio deben ejecutarse de forma transaccional
- si falla cualquier paso de la operacion, debe aplicarse rollback completo
- no deben quedar estados intermedios inconsistentes entre la entidad principal, sus relaciones materializadas y los efectos integrados con otros dominios
- cuando una operacion comercial dependa de verificaciones o mutaciones en `inmobiliario` o en soporte transversal, la persistencia final solo debe confirmarse si el conjunto completo de pasos resulta consistente
- este criterio aplica especialmente a confirmaciones, cierres funcionales y operaciones que modifiquen simultaneamente estado comercial y trazabilidad operativa

## 6. Writes

### 6.1 `reserva_venta`

#### `POST /api/v1/reservas-venta`

Objetivo:
- alta de reserva de venta

Request:

```json
{
  "codigo_reserva": "RV-0001",
  "fecha_reserva": "2026-04-21T10:00:00",
  "fecha_vencimiento": "2026-04-30T23:59:59",
  "observaciones": "Reserva inicial",
  "objetos": [
    {
      "id_inmueble": 100,
      "observaciones": "Objeto principal"
    }
  ]
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_reserva_venta": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "codigo_reserva": "RV-0001",
    "fecha_reserva": "2026-04-21T10:00:00",
    "estado_reserva": "borrador",
    "fecha_vencimiento": "2026-04-30T23:59:59",
    "observaciones": "Reserva inicial",
    "objetos": [
      {
        "id_reserva_venta_objeto": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "observaciones": "Objeto principal"
      }
    ],
    "created_at": "2026-04-21T10:00:00",
    "updated_at": "2026-04-21T10:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- `codigo_reserva` requerido y unico
- `fecha_reserva` requerida
- `objetos` requerido con al menos un elemento
- `fecha_vencimiento` debe ser nula o mayor o igual a `fecha_reserva`
- cada item de `objetos` debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- cada objeto referenciado debe existir
- no deben repetirse objetos dentro del mismo payload, ni por `id_inmueble` ni por `id_unidad_funcional`
- cada objeto debe estar disponible y sin conflicto de ocupacion
- no debe existir venta activa incompatible sobre ninguno de los objetos
- no debe existir reserva vigente incompatible sobre ninguno de los objetos
- la regla de conflicto se evalua por objeto materializado: si un solo objeto entra en conflicto, falla toda la reserva
- en alta, `estado_reserva` no se recibe por request; se asigna internamente con un estado inicial valido del ciclo, recomendado `borrador`

Reglas de negocio:

- `objetos` representa el detalle tecnico de `reserva_venta_objeto_inmobiliario` y no un recurso autonomo
- este contrato no expone vinculacion directa de `reserva_venta` con `persona` o `cliente_comprador` porque no existe FK local; los intervinientes solo pueden resolverse hoy por soporte transversal
- si falla la validacion o persistencia de cualquiera de los objetos, falla toda la reserva
- el alta se ejecuta de forma transaccional sobre `reserva_venta`, `reserva_venta_objeto_inmobiliario` y soporte transversal asociado
- en v1 la reserva valida elegibilidad contra `disponibilidad` y `ocupacion`, pero no muta esos recursos
- si una reserva ya se encuentra asociada a una `venta` vigente, no debe admitirse una mutacion que rompa la coherencia reserva -> venta

#### `PUT /api/v1/reservas-venta/{id_reserva_venta}`

Objetivo:
- actualizar datos comerciales escalares de una reserva existente

Request:

```json
{
  "codigo_reserva": "RV-0001-EDIT",
  "fecha_reserva": "2026-04-25T15:30:00",
  "fecha_vencimiento": "2026-05-02T10:00:00",
  "observaciones": "Reserva actualizada"
}
```

Response:
- mismo shape que `POST /api/v1/reservas-venta`

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- `codigo_reserva` requerido y unico
- `fecha_reserva` requerida
- `fecha_vencimiento` debe ser nula o mayor o igual a `fecha_reserva`
- la reserva solo puede actualizarse si esta en estado `borrador`, `activa` o `confirmada`
- no debe existir `venta` no dada de baja vinculada a la misma reserva

Reglas de negocio:

- este endpoint actualiza solo datos comerciales escalares de `reserva_venta`
- en esta `v1` real no actualiza `objetos` ni `participaciones`
- la actualizacion no modifica `estado_reserva`
- la actualizacion no modifica `disponibilidad`
- la actualizacion no modifica `ocupacion`
- la actualizacion no genera ni modifica `venta`
- si la reserva ya se encuentra vinculada a una `venta`, la mutacion debe rechazarse para preservar coherencia reserva -> venta

#### `PATCH /api/v1/reservas-venta/{id_reserva_venta}/baja`

Objetivo:
- aplicar baja logica sobre una reserva que aun no produjo efectos operativos incompatibles

Request:
- sin body

Response:

```json
{
  "ok": true,
  "data": {
    "id_reserva_venta": 1,
    "version_registro": 2,
    "deleted": true
  }
}
```

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- la reserva solo puede darse de baja si esta en estado `borrador` o `activa`
- no debe existir `venta` no dada de baja vinculada a la misma reserva

Reglas de negocio:

- la baja es logica, materializada por `deleted_at`
- la baja no modifica `objetos` ni `participaciones`
- la baja no modifica `disponibilidad`
- la baja no modifica `ocupacion`
- una reserva `confirmada` no puede darse de baja por este endpoint porque requeriria liberar el bloqueo `RESERVADA`; ese caso sigue resolviendose por `cancelar` o `vencer`
- una reserva vinculada a `venta` no puede darse de baja para no romper la trazabilidad reserva -> venta

#### `POST /api/v1/reservas-venta/{id_reserva_venta}/activar`

Objetivo:
- activar una reserva de venta para habilitar su continuidad comercial

Request:
- sin body

Response:
- mismo shape que `POST`

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- el estado actual debe admitir activacion; en este contrato el unico estado origen valido es `borrador`
- la reserva debe mantener al menos un objeto inmobiliario asociado
- todos los objetos asociados deben seguir existiendo
- todos los objetos asociados deben seguir siendo elegibles por `disponibilidad`
- no debe existir `ocupacion` incompatible vigente sobre los objetos asociados
- no debe existir conflicto con `venta` activa incompatible sobre los objetos asociados
- no debe existir conflicto con otra `reserva_venta` vigente incompatible sobre los objetos asociados

Reglas de negocio:

- este endpoint es el mecanismo explicito de transicion hacia `estado_reserva = activa`
- `PUT` no debe utilizarse para activar una reserva
- la activacion revalida elegibilidad comercial de los objetos pero no muta `disponibilidad`
- la activacion no genera por si sola una `ocupacion`
- es una operacion transaccional; si falla cualquier validacion o persistencia, debe hacerse rollback completo
- la confirmacion mantiene su propia transicion `activa -> confirmada`

#### `POST /api/v1/reservas-venta/{id_reserva_venta}/cancelar`

Objetivo:
- cancelar funcionalmente una reserva de venta

Request:
- sin body

Response:
- mismo shape que `POST /api/v1/reservas-venta`

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- el estado actual debe ser cancelable; en este contrato se consideran validos `borrador`, `activa` y `confirmada`
- si la reserva esta `confirmada`, debe mantener una `disponibilidad` vigente en estado `RESERVADA` por cada objeto asociado

Reglas de negocio:

- este endpoint es el mecanismo explicito de transicion hacia `estado_reserva = cancelada`
- la cancelacion funcional no se resuelve por baja logica en esta `v1`
- `borrador -> cancelada` y `activa -> cancelada` no generan efectos operativos adicionales
- `confirmada -> cancelada` debe liberar la `disponibilidad` previamente reservada, reemplazando la disponibilidad vigente `RESERVADA` por una nueva disponibilidad `DISPONIBLE`
- la cancelacion de reserva no genera por si sola una `ocupacion`
- la cancelacion de reserva no crea, modifica ni elimina `venta`
- es una operacion transaccional; si falla cualquier validacion o cualquier liberacion de disponibilidad, debe hacerse rollback completo

#### `POST /api/v1/reservas-venta/{id_reserva_venta}/vencer`

Objetivo:
- cerrar una reserva de venta por vencimiento funcional

Request:
- sin body

Response:
- mismo shape que `POST /api/v1/reservas-venta`

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- el estado actual debe ser vencible; en este contrato se consideran validos `activa` y `confirmada`
- si la reserva esta `confirmada`, debe mantener una `disponibilidad` vigente en estado `RESERVADA` por cada objeto asociado

Reglas de negocio:

- este endpoint es el mecanismo explicito de transicion hacia `estado_reserva = vencida`
- `activa -> vencida` no genera efectos operativos adicionales
- `confirmada -> vencida` debe liberar la `disponibilidad` previamente reservada, reemplazando la disponibilidad vigente `RESERVADA` por una nueva disponibilidad `DISPONIBLE`
- el vencimiento de reserva no genera por si sola una `ocupacion`
- el vencimiento de reserva no crea, modifica ni elimina `venta`
- es una operacion transaccional; si falla cualquier validacion o cualquier liberacion de disponibilidad, debe hacerse rollback completo

#### `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar`

Objetivo:
- confirmar una reserva de venta y consolidar su estado comercial

Request:
- sin body

Response:
- mismo shape que `POST`

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- el estado actual debe admitir confirmacion; en este contrato el unico estado origen valido es `activa`
- la reserva debe mantener al menos un objeto inmobiliario asociado
- todos los objetos asociados deben seguir existiendo
- todos los objetos asociados deben seguir siendo elegibles por `disponibilidad`
- no debe existir `ocupacion` incompatible vigente sobre los objetos asociados
- no debe existir conflicto con `venta` activa incompatible sobre los objetos asociados
- no debe existir conflicto con otra `reserva_venta` vigente incompatible sobre los objetos asociados

Reglas de negocio:

- este endpoint es el mecanismo explicito de transicion hacia `estado_reserva = confirmada`
- `PUT` no debe utilizarse para confirmar una reserva
- la confirmacion reemplaza la `disponibilidad` vigente de cada objeto asociado por una nueva disponibilidad en estado `RESERVADA`, reutilizando el patron transaccional vigente de `inmobiliario`
- la confirmacion de reserva no genera por si sola una `ocupacion`
- es una operacion transaccional; si falla cualquier validacion o cualquier reemplazo de disponibilidad, debe hacerse rollback completo
- la confirmacion debe preservar coherencia entre `reserva_venta`, `reserva_venta_objeto_inmobiliario` y los efectos requeridos sobre `disponibilidad`

#### `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`

Objetivo:
- generar una `venta` a partir de una `reserva_venta` previamente `confirmada`

Request:

```json
{
  "codigo_venta": "V-0001",
  "fecha_venta": "2026-04-22T11:00:00",
  "monto_total": 150000.00,
  "observaciones": "Venta generada desde reserva"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_venta": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_reserva_venta": 10,
    "codigo_venta": "V-0001",
    "fecha_venta": "2026-04-22T11:00:00",
    "estado_venta": "borrador",
    "monto_total": 150000.00,
    "observaciones": "Venta generada desde reserva",
    "objetos": [
      {
        "id_venta_objeto": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "precio_asignado": null,
        "observaciones": "Objeto reservado"
      }
    ],
    "created_at": "2026-04-22T11:00:00",
    "updated_at": "2026-04-22T11:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- requiere `If-Match-Version`
- la reserva debe existir y no estar dada de baja
- la reserva debe encontrarse en estado `confirmada`
- no debe existir ya una `venta` no dada de baja asociada a la misma `id_reserva_venta`
- `codigo_venta` requerido y unico
- `fecha_venta` requerida
- la reserva debe mantener al menos un objeto inmobiliario asociado
- todos los objetos asociados deben seguir existiendo
- el detalle multiobjeto persistido de la reserva debe seguir siendo coherente
- cada objeto debe mantener una `disponibilidad` vigente en estado `RESERVADA`
- no debe existir conflicto con otra `venta` vigente incompatible sobre los objetos asociados
- no debe existir conflicto con otra `reserva_venta` vigente incompatible sobre los objetos asociados

Reglas de negocio:

- este endpoint es el mecanismo explicito de conversion `reserva_venta -> venta`
- la `venta` generada queda inicialmente en estado `borrador`
- la `venta` resultante conserva trazabilidad explicita a la reserva por `venta.id_reserva_venta`
- el detalle de `venta_objeto_inmobiliario` se materializa 1:1 desde `reserva_venta_objeto_inmobiliario`
- las participaciones vigentes de la reserva se replican a `relacion_persona_rol` con `tipo_relacion = venta`
- la reserva origen debe pasar de `confirmada` a `finalizada` dentro de la misma transaccion
- la conversion no crea por si sola registros de `ocupacion`
- la conversion no dispara en esta etapa logica financiera ni `relacion_generadora`
- la conversion valida consistencia del bloqueo ya existente, pero no reemplaza ni libera la `disponibilidad` `RESERVADA` generada por la confirmacion de la reserva

### 6.2 `venta`

Observacion:

- en esta `v1` real no se expone `POST /api/v1/ventas`; la creacion de `venta` hoy se materializa por `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`

#### `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales`

Objetivo:
- definir las condiciones comerciales basicas de una `venta` en estado `borrador`

Request:

```json
{
  "monto_total": 150000.00,
  "objetos": [
    {
      "id_inmueble": 100,
      "id_unidad_funcional": null,
      "precio_asignado": 100000.00
    },
    {
      "id_inmueble": 101,
      "id_unidad_funcional": null,
      "precio_asignado": 50000.00
    }
  ]
}
```

Response:
- mismo shape que el detalle write de `venta`

Validaciones:

- requiere `If-Match-Version`
- la venta debe existir y no estar dada de baja
- la venta debe encontrarse en estado `borrador`
- la venta debe mantener al menos un objeto inmobiliario asociado
- `objetos` debe representar el conjunto completo y vigente de `venta_objeto_inmobiliario`
- cada item de `objetos` debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- no deben repetirse objetos dentro del mismo payload
- `precio_asignado` debe ser mayor que cero en todos los objetos
- la suma exacta de `precio_asignado` debe coincidir con `monto_total`
- el detalle multiobjeto persistido de la venta debe seguir siendo coherente

Reglas de negocio:

- este endpoint no crea nuevas filas de `venta_objeto_inmobiliario`; actualiza las ya materializadas para la venta
- en la implementacion basica actual, las condiciones comerciales se materializan en `venta.monto_total` y `venta_objeto_inmobiliario.precio_asignado`
- la operacion no modifica `disponibilidad`
- la operacion no modifica `ocupacion`
- la operacion no dispara logica financiera ni `relacion_generadora`
- la actualizacion de `venta` y de todos sus objetos debe ejecutarse de forma transaccional; si falla un solo objeto, debe hacerse rollback completo

#### `PATCH /api/v1/ventas/{id_venta}/confirmar`

Objetivo:
- confirmar una venta y consolidar su estado comercial

Request:

```json
{
  "observaciones": "Venta confirmada comercialmente"
}
```

Response:
- mismo shape que el detalle write de `venta`

Validaciones:

- requiere `If-Match-Version`
- la venta debe existir y no estar dada de baja
- el estado actual debe admitir confirmacion; en este contrato se consideran estados origen validos `borrador` y `activa`
- la venta debe mantener al menos un objeto inmobiliario asociado
- no debe existir conflicto con otra `venta` vigente sobre los mismos objetos
- no debe existir `ocupacion` incompatible vigente sobre los objetos asociados
- si existe `id_reserva_venta`, la reserva vinculada debe existir, no estar dada de baja y encontrarse en estado `confirmada` o `finalizada`

Reglas de negocio:

- este endpoint es el mecanismo explicito de transicion hacia `estado_venta = confirmada`
- en esta `v1` real no existe `PUT /api/v1/ventas/{id_venta}` y la confirmacion no debe inferirse por otra operacion
- la confirmacion emite `venta_confirmada` a `outbox_event` y no muta por si misma `disponibilidad` ni `ocupacion`
- la confirmacion de venta no genera por si sola una `ocupacion`
- la confirmacion debe preservar coherencia con reserva, objetos e instrumentos posteriores
- es una operacion de transicion de estado y debe ejecutarse de forma transaccional
- si falla cualquier paso de validacion, persistencia o integracion requerida, debe hacerse rollback completo
- no debe dejar estados intermedios inconsistentes entre `venta`, `venta_objeto_inmobiliario`, `reserva_venta` y el `outbox_event` emitido

### 6.3 `instrumento_compraventa`

#### `POST /api/v1/ventas/{id_venta}/instrumentos-compraventa`

Objetivo:
- alta de instrumento de compraventa asociado a una venta

Request:

```json
{
  "tipo_instrumento": "boleto",
  "numero_instrumento": "BC-2026-001",
  "fecha_instrumento": "2026-04-22T09:00:00",
  "estado_instrumento": "generado",
  "observaciones": "Boleto inicial",
  "objetos": [
    {
      "id_inmueble": 100,
      "observaciones": "Objeto alcanzado por el instrumento"
    }
  ]
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_instrumento_compraventa": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_venta": 1,
    "tipo_instrumento": "boleto",
    "numero_instrumento": "BC-2026-001",
    "fecha_instrumento": "2026-04-22T09:00:00",
    "estado_instrumento": "generado",
    "observaciones": "Boleto inicial",
    "objetos": [
      {
        "id_instrumento_objeto": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "observaciones": "Objeto alcanzado por el instrumento"
      }
    ],
    "created_at": "2026-04-22T09:00:00",
    "updated_at": "2026-04-22T09:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- la `venta` padre debe existir y no estar dada de baja
- `tipo_instrumento` requerido
- `fecha_instrumento` requerida
- `estado_instrumento` requerido y controlado por catalogo o enum
- `numero_instrumento` puede ser null segun SQL
- si se informa `objetos`, cada elemento debe informar exactamente uno entre `id_inmueble` e `id_unidad_funcional`
- cada objeto referenciado debe existir
- no deben repetirse objetos dentro del mismo payload
- la `venta` padre debe encontrarse en estado compatible con instrumentacion comercial

Reglas de negocio:

- `instrumento_compraventa` formaliza documental o juridicamente una `venta`
- no reemplaza a la `venta` como entidad comercial principal
- `objetos` representa `instrumento_objeto_inmobiliario` y no un recurso de negocio autonomo

### 6.4 `cesion`

#### `POST /api/v1/ventas/{id_venta}/cesiones`

Objetivo:
- alta de cesion asociada a una venta

Request:

```json
{
  "fecha_cesion": "2026-04-23T10:00:00",
  "tipo_cesion": "total",
  "observaciones": "Cesion registrada"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_cesion": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_venta": 1,
    "fecha_cesion": "2026-04-23T10:00:00",
    "tipo_cesion": "total",
    "observaciones": "Cesion registrada",
    "created_at": "2026-04-23T10:00:00",
    "updated_at": "2026-04-23T10:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- la `venta` padre debe existir y no estar dada de baja
- `fecha_cesion` requerida
- `tipo_cesion` opcional segun SQL, pero si se informa debe respetar el catalogo funcional cuando exista
- la `venta` padre debe encontrarse en estado comercial compatible con cesion
- no debe existir `rescision_venta` no dada de baja sobre la `venta`
- no debe existir `escrituracion` no dada de baja incompatible con una nueva cesion
- no debe existir una cesion vigente incompatible sobre la misma `venta`

Reglas de negocio:

- `cesion` siempre depende de una `venta`
- esta version del contrato no expone `estado_cesion` en write porque el SQL actual no lo persiste
- esta version del contrato no expone cedente ni cesionario dentro del payload local; esa informacion hoy requiere soporte transversal en `personas`
- la cesion no debe alterar el conjunto de objetos de la venta
- la cesion no produce por si sola cambios en `disponibilidad`
- la cesion no crea ni cierra `ocupacion`; solo exige que el estado operativo de los objetos no contradiga la continuidad comercial
- si la registracion de cesion actualiza intervinientes o trazabilidad comercial asociada, la operacion debe ejecutarse de forma transaccional
- si falla cualquier paso del registro o de la actualizacion asociada, debe hacerse rollback completo
- no deben quedar estados intermedios inconsistentes entre `cesion`, `venta` y la trazabilidad de soporte transversal

### 6.5 `escrituracion`

#### `POST /api/v1/ventas/{id_venta}/escrituraciones`

Objetivo:
- alta de escrituracion asociada a una venta

Request:

```json
{
  "fecha_escrituracion": "2026-04-24T11:00:00",
  "numero_escritura": "ESC-2026-001",
  "observaciones": "Escrituracion iniciada"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "id_escrituracion": 1,
    "uid_global": "uuid",
    "version_registro": 1,
    "id_venta": 1,
    "fecha_escrituracion": "2026-04-24T11:00:00",
    "numero_escritura": "ESC-2026-001",
    "observaciones": "Escrituracion iniciada",
    "created_at": "2026-04-24T11:00:00",
    "updated_at": "2026-04-24T11:00:00",
    "deleted_at": null
  }
}
```

Validaciones:

- la `venta` padre debe existir y no estar dada de baja
- `fecha_escrituracion` requerida
- `numero_escritura` opcional segun SQL
- la `venta` padre debe encontrarse en estado comercial compatible con escrituracion
- no debe existir `rescision_venta` no dada de baja sobre la `venta`
- no debe existir otra `escrituracion` no dada de baja incompatible con la misma `venta`

Reglas de negocio:

- `escrituracion` siempre depende de una `venta`
- esta version del contrato no expone `estado_escrituracion` en write porque el SQL actual no lo persiste
- esta version del contrato no expone hitos adicionales del proceso porque no existen hoy como estructura materializada
- la escrituracion no modifica por si sola `ocupacion`
- cualquier ajuste de `disponibilidad` posterior a la escrituracion debe resolverse por integracion con `inmobiliario`, no como ownership local de `comercial`
- la implementacion vigente materializa esa integracion de forma asincronica: al consumirse `escrituracion_registrada`, `inmobiliario` debe reemplazar `RESERVADA -> NO_DISPONIBLE` sin crear ni cerrar `ocupacion`
- si la registracion de escrituracion dispara cierre comercial, integracion documental o efectos operativos asociados, la operacion debe ejecutarse de forma transaccional
- si falla cualquier paso del registro o de la integracion requerida, debe hacerse rollback completo
- no deben quedar estados intermedios inconsistentes entre `escrituracion`, `venta` y los efectos asociados que formen parte de la misma operacion

## 7. Reads

### 7.1 `reserva_venta`

#### `GET /api/v1/reservas-venta/{id_reserva_venta}`

Objetivo:
- detalle de reserva de venta

Response:
- mismo shape que el detalle write de `reserva_venta`

#### `GET /api/v1/reservas-venta`

Objetivo:
- listado de reservas de venta

Filtros permitidos:

- `codigo_reserva`
- `estado_reserva`
- `fecha_desde`
- `fecha_hasta`
- `vigente`

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

### 7.2 `venta`

#### `GET /api/v1/ventas/{id_venta}`

Objetivo:
- consulta integral de una `venta` como read model enriquecido
- exponer datos persistidos de la `venta` y su trazabilidad comercial asociada
- incluir origen desde `reserva_venta` cuando exista
- incluir objetos inmobiliarios asociados con su `disponibilidad` y `ocupacion` actualmente conocidas
- incluir instrumentos de compraventa, cesiones y escrituraciones asociados
- incluir el estado de integracion `comercial -> inmobiliario` por evento emitido y por objeto alcanzado
- incluir un resumen de lectura derivado solo de hechos persistidos o lecturas reales disponibles

Naturaleza del endpoint:
- operacion `read only`
- sin efectos persistentes
- sin mutacion de `venta`, `disponibilidad` ni `ocupacion`
- sin `outbox`
- sin `locks`
- sin `If-Match-Version`
- sin `X-Op-Id`
- sin `X-Usuario-Id`
- sin `X-Sucursal-Id`
- sin `X-Instalacion-Id`

Response `200`:

```json
{
  "ok": true,
  "data": {
    "id_venta": 1,
    "version_registro": 3,
    "codigo_venta": "V-0001",
    "fecha_venta": "2026-04-22T10:00:00",
    "estado_venta": "confirmada",
    "monto_total": 150000.00,
    "deleted_at": null,
    "origen": {
      "venta_directa": false,
      "con_reserva": {
        "id_reserva_venta": 10,
        "estado_reserva_venta": "finalizada"
      }
    },
    "objetos": [
      {
        "id_venta_objeto_inmobiliario": 1,
        "id_inmueble": 100,
        "id_unidad_funcional": null,
        "precio_asignado": 150000.00,
        "observaciones": "Objeto principal",
        "disponibilidad_actual": "RESERVADA",
        "ocupacion_actual": null
      }
    ],
    "instrumentos_compraventa": [],
    "cesiones": [],
    "escrituraciones": [],
    "integracion_inmobiliaria": {
      "eventos": [
        {
          "id_evento_outbox": 101,
          "nombre_evento": "venta_confirmada",
          "estado": "PENDING",
          "ocurrido_en": "2026-04-23T15:00:00Z",
          "publicado_en": null,
          "objetos": [
            {
              "id_inmueble": 100,
              "id_unidad_funcional": null,
              "efecto_inmobiliario": {
                "disponibilidad": "SIN_CAMBIO",
                "ocupacion": "SIN_CAMBIO"
              }
            }
          ]
        }
      ]
    },
    "resumen": {
      "venta_cerrada_logica": false,
      "estado_operativo_conocido_del_activo": "RESERVADA"
    }
  }
}
```

Errores posibles:
- `404 NOT_FOUND`: la `venta` no existe o se encuentra dada de baja logica
- `500 INTERNAL_ERROR`: error inesperado al construir la vista de lectura

Shape publico real del response:
- `data` expone solo:
  - `id_venta`
  - `version_registro`
  - `codigo_venta`
  - `fecha_venta`
  - `estado_venta`
  - `monto_total`
  - `deleted_at`
  - `origen`
  - `objetos`
  - `instrumentos_compraventa`
  - `cesiones`
  - `escrituraciones`
  - `integracion_inmobiliaria`
  - `resumen`
- `data` no expone en el nivel superior:
  - `id_reserva_venta`
  - `uid_global`
  - `observaciones`
  - `created_at`
  - `updated_at`
- `origen` tiene exactamente:
  - `venta_directa: bool`
  - `con_reserva: { id_reserva_venta, estado_reserva_venta } | null`
- cada item de `objetos` tiene exactamente:
  - `id_venta_objeto_inmobiliario`
  - `id_inmueble`
  - `id_unidad_funcional`
  - `precio_asignado`
  - `observaciones`
  - `disponibilidad_actual`
  - `ocupacion_actual`
- `resumen` tiene exactamente:
  - `venta_cerrada_logica`
  - `estado_operativo_conocido_del_activo`
- `integracion_inmobiliaria` tiene exactamente:
  - `eventos: []`
- cada item de `integracion_inmobiliaria.eventos` tiene exactamente:
  - `id_evento_outbox`
  - `nombre_evento`
  - `estado`
  - `ocurrido_en`
  - `publicado_en`
  - `objetos`
- cada item de `integracion_inmobiliaria.eventos[].objetos` tiene exactamente:
  - `id_inmueble`
  - `id_unidad_funcional`
  - `efecto_inmobiliario`
- `efecto_inmobiliario` tiene exactamente:
  - `disponibilidad`
  - `ocupacion`
- `instrumentos_compraventa`, `cesiones` y `escrituraciones` reutilizan los mismos shapes publicos ya expuestos por sus writes y listados por venta

Reglas de construccion del response:
- `data` se construye como proyeccion de lectura enriquecida; no reutiliza el shape write de `venta`
- `origen` unifica la trazabilidad de procedencia de la `venta`
- `origen.venta_directa = true` cuando `venta.id_reserva_venta` es `null`
- `origen.venta_directa = false` cuando la `venta` referencia una `reserva_venta`
- `origen.con_reserva` se informa solo si la `reserva_venta` referenciada puede resolverse en lectura; en caso contrario se devuelve `null`
- `estado_reserva_venta` es el naming publico del valor persistido en `reserva_venta.estado_reserva`
- `objetos` surge de `venta_objeto_inmobiliario` activo para la `venta`
- `id_venta_objeto_inmobiliario` es el naming publico del identificador fisico `venta_objeto_inmobiliario.id_venta_objeto`
- `disponibilidad_actual` se lee desde `disponibilidad` como dato del dominio `inmobiliario`; no es gobernada por `comercial`
- `ocupacion_actual` se lee desde `ocupacion` como dato del dominio `inmobiliario`; no es gobernada por `comercial`
- si para un objeto existe una unica `disponibilidad` vigente para el instante de consulta, `disponibilidad_actual` debe devolver solo `estado_disponibilidad`
- si para un objeto existen cero o mas de una `disponibilidad` vigentes para el instante de consulta, `disponibilidad_actual` debe devolverse como `null`
- si para un objeto existe una unica `ocupacion` vigente para el instante de consulta, `ocupacion_actual` debe devolver solo `tipo_ocupacion`
- si para un objeto existen cero o mas de una `ocupacion` vigentes para el instante de consulta, `ocupacion_actual` debe devolverse como `null`
- las colecciones `instrumentos_compraventa`, `cesiones` y `escrituraciones` no usan wrappers `items/total` dentro de `GET /ventas/{id_venta}`; se exponen como arrays directos
- `instrumentos_compraventa` reutiliza el shape publico de `InstrumentoCompraventaData`
- `cesiones` reutiliza el shape publico de `CesionData`
- `escrituraciones` reutiliza el shape publico de `EscrituracionData`
- `integracion_inmobiliaria.eventos` surge de `outbox_event` filtrado por `aggregate_type = venta`, `aggregate_id = id_venta` y por los eventos contractuales `venta_confirmada` y `escrituracion_registrada`
- `integracion_inmobiliaria.eventos[].estado` expone el estado persistido del outbox y debe limitarse a `PENDING`, `PUBLISHED` o `REJECTED`
- `integracion_inmobiliaria.eventos[].objetos` se construye desde `payload.objetos` del evento emitido; no recalcula el universo de objetos por inferencia
- `integracion_inmobiliaria` no expone en este read `processing_reason` ni `processing_metadata`; esa observabilidad tecnica pertenece al outbox persistido y no forma parte del shape publico de `venta`
- `integracion_inmobiliaria.eventos[].objetos[].efecto_inmobiliario` expone el efecto contractual esperado por `INT-CONS-001`, no un nuevo ownership operativo de `comercial`
- para `venta_confirmada`, el efecto contractual por objeto es `disponibilidad = SIN_CAMBIO` y `ocupacion = SIN_CAMBIO`
- para `escrituracion_registrada`, el efecto contractual por objeto es `disponibilidad = RESERVADA->NO_DISPONIBLE` y `ocupacion = SIN_CAMBIO`
- `venta_cerrada_logica` se expone como `true` cuando la `venta` esta en `estado_venta = confirmada` y existe al menos una `escrituracion` asociada; en cualquier otro caso se expone `false`
- `estado_operativo_conocido_del_activo` solo debe informarse cuando todos los objetos de la `venta` tienen una `disponibilidad_actual` conocida y comparten el mismo valor; si no hay coincidencia total o falta informacion, debe devolverse `null`
- este endpoint no expone `moneda`; el SQL real de `venta` no materializa ese atributo y la implementacion actual no lo devuelve

Observaciones de alineacion con arquitectura:
- este endpoint pertenece a la capa de consulta del dominio `comercial` y se alinea con `SRV-COM-008`
- la inclusion de `disponibilidad_actual` y `ocupacion_actual` no traslada ownership desde `inmobiliario` hacia `comercial`; son datos consumidos en modo lectura
- la inclusion de `integracion_inmobiliaria` tampoco traslada ownership a `comercial`; expone observabilidad read-only sobre eventos ya emitidos y sus efectos contractuales
- la consulta no debe interpretarse como cierre operativo del activo ni como mutacion del estado inmobiliario
- la presencia de `instrumento_compraventa`, `cesion` o `escrituracion` no redefine por si sola `estado_venta`
- este contrato no expone `requiere_definicion_operativa`

### 7.3 `instrumento_compraventa`

#### `GET /api/v1/ventas/{id_venta}/instrumentos-compraventa`

Objetivo:
- listado de instrumentos de una venta

Filtros permitidos:

- `tipo_instrumento`
- `estado_instrumento`
- `fecha_desde`
- `fecha_hasta`

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

- no se define en v1 un `GET /api/v1/instrumentos-compraventa` global para no mezclar este contrato operativo con consultas amplias o reportes

### 7.4 `cesion`

#### `GET /api/v1/ventas/{id_venta}/cesiones`

Objetivo:
- listado de cesiones de una venta

Filtros permitidos:

- `tipo_cesion`
- `fecha_desde`
- `fecha_hasta`

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

- no se define en v1 un `GET /api/v1/cesiones` global

### 7.5 `escrituracion`

#### `GET /api/v1/ventas/{id_venta}/escrituraciones`

Objetivo:
- listado de escrituraciones de una venta

Filtros permitidos:

- `fecha_desde`
- `fecha_hasta`
- `numero_escritura`

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

- no se define en v1 un `GET /api/v1/escrituraciones` global

## 8. Reglas visibles del contrato

- `venta` es negocio u operacion comercial.
- `instrumento_compraventa` es formalizacion documental o juridica de una `venta`.
- `reserva_venta` expone sus objetos como detalle embebido por `reserva_venta_objeto_inmobiliario`.
- `venta_objeto_inmobiliario` e `instrumento_objeto_inmobiliario` se consumen solo como detalle embebido en los recursos principales.
- `estado_reserva`, `estado_venta` y `estado_instrumento` deben validarse contra catalogo o enum controlado.
- `cesion` y `escrituracion` no exponen estado persistido en write mientras el SQL no materialice ese dato.
- los intervinientes comerciales no forman parte del payload write local de estos recursos en v1; su resolucion sigue hoy por soporte transversal.
- toda operacion critica de transicion o cierre funcional debe ejecutarse de forma transaccional, sin dejar estados intermedios inconsistentes.
- estados cerrados en este contrato:
  - `reserva_venta`: `cancelada`, `vencida`
  - `venta`: `cancelada`, `finalizada`
- transiciones validas de referencia para `reserva_venta`:
  - `borrador -> activa`
  - `borrador -> cancelada`
  - `activa -> confirmada`
  - `activa -> cancelada`
  - `activa -> vencida`
  - `confirmada -> cancelada`
  - `confirmada -> finalizada`
  - `confirmada -> vencida`
- transiciones validas de referencia para `venta`:
  - `borrador -> confirmada`
  - `activa -> confirmada`
- aunque `DEV-SRV` describe estados para `cesion` y `escrituracion`, este contrato no expone transiciones persistidas de esos bloques porque el SQL actual no materializa columna de estado propia
- los objetos de `venta` deben validarse contra `disponibilidad` y contra `ocupacion` incompatible, pero `comercial` no es dueno de esos registros
- la confirmacion de `venta` debe ejecutarse por endpoint especifico y no por mutacion implicita

## 9. Bloques pendientes o explicitamente fuera de alcance

- `rescision_venta` queda fuera de este contrato porque no fue solicitada en este bloque de implementacion
- `cliente_comprador` no recibe API propia en este documento
- la documentacion comercial asociada no recibe API propia en esta version
- las consultas y reportes comerciales consolidados quedan fuera de este contrato operativo
- no se expone alta directa `POST /api/v1/ventas`; la venta nace hoy desde `reserva_venta` confirmada por `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`
- no se exponen `PUT` ni `PATCH /baja` para `venta`, `instrumento_compraventa`, `cesion` o `escrituracion`
- no se expone `GET /api/v1/ventas` ni detalles individuales de `instrumento_compraventa`, `cesion` o `escrituracion`
- no se incorpora `PATCH /api/v1/ventas/{id_venta}/rescindir` en esta version:
  - la rescision tiene entidad SQL propia `rescision_venta`
  - modelarla como simple cambio de estado sobre `venta` ocultaria trazabilidad y mezclaria operacion con evento de cierre anomalo
  - si se incorpora, debe hacerse en un bloque propio de `rescision_venta`

## 10. Notas de implementacion

- este documento queda congelado como contrato oficial vigente `v1` para el surface efectivamente materializado en router, schemas, services, repositories y tests del workspace
- para el dominio `comercial`, este documento debe leerse como fuente publica de verdad del contrato HTTP actual
- si se incorporan nuevos endpoints o payloads, primero debe materializarse backend y luego actualizarse este contrato
- si durante una futura implementacion aparece una necesidad no soportada por SQL actual, debe ajustarse antes el modelo o reducirse el alcance; no corresponde ampliar el contrato por inferencia
