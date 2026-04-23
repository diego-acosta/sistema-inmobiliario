# DEV-API-PER-001 - Dominio Personas

## 1. Alcance

Este documento define la version Markdown, auditable y versionable del contrato de API del dominio `personas`, tomando como base el DEV-API historico del dominio, la documentacion `DEV-SRV`, `SYS-MAP-002` y la implementacion backend actualmente existente.

El alcance vigente del dominio `personas` queda centrado en:

- persona base
- identificacion documental
- domicilios
- contactos
- relaciones entre personas
- representacion y poderes
- participacion contextual cuando exista implementacion real
- consultas del dominio

Este documento no consolida a `personas` como dueno semantico de logica comercial, locativa o administrativa ajena.

## 2. Criterios de diseno

- `personas` define al sujeto base del sistema y sus atributos propios.
- `personas` no debe fusionarse con `administrativo` ni con la entidad `usuario`.
- Las participaciones contextuales se documentan solo porque ya existen en documentacion e implementacion, pero no deben interpretarse como identidad base de la persona.
- Las clasificaciones funcionales heredadas del DEV-API historico no se consolidan aqui como nucleo estable del dominio.
- El contrato prioriza compatibilidad con endpoints realmente implementados.
- Cuando el DEV-API historico expone semantica dudosa no implementada, se conserva solo como referencia heredada y pendiente de revision.

## 3. Convencion de errores

El dominio utiliza respuestas de error estructuradas con el formato general:

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

Convenciones visibles en implementacion:

- `NOT_FOUND` para entidades inexistentes o dadas de baja logica
- `APPLICATION_ERROR` para validaciones de dominio o errores de contrato
- `CONCURRENCY_ERROR` para versionado mediante `If-Match-Version`
- `INTERNAL_ERROR` para errores no controlados

Headers transversales observables en operaciones write:

- `X-Op-Id`
- `X-Usuario-Id`
- `X-Sucursal-Id`
- `X-Instalacion-Id`
- `If-Match-Version` cuando la operacion requiere control de concurrencia

## 4. Endpoints del dominio

### 4.1 Persona base

#### `POST /api/v1/personas`
- estado: vigente
- objetivo: alta de persona base

#### `PUT /api/v1/personas/{id_persona}`
- estado: vigente
- objetivo: modificacion de persona base

#### `PATCH /api/v1/personas/{id_persona}/baja`
- estado: vigente
- objetivo: baja logica de persona

#### `GET /api/v1/personas/{id_persona}`
- estado: vigente
- objetivo: consulta de detalle de persona

Observacion:
- no existe hoy en implementacion un endpoint general `GET /api/v1/personas` de busqueda o listado, aunque si aparece en el DEV-API historico.

### 4.2 Documentos identificatorios

#### `POST /api/v1/personas/{id_persona}/documentos`
- estado: vigente
- objetivo: alta de documento identificatorio

#### `PUT /api/v1/personas/{id_persona}/documentos/{id_persona_documento}`
- estado: vigente
- objetivo: modificacion de documento identificatorio

#### `PATCH /api/v1/personas/{id_persona}/documentos/{id_persona_documento}/baja`
- estado: vigente
- objetivo: baja logica de documento identificatorio

#### `GET /api/v1/personas/{id_persona}/documentos`
- estado: vigente
- objetivo: consulta de documentos identificatorios de una persona

### 4.3 Domicilios

#### `POST /api/v1/personas/{id_persona}/domicilios`
- estado: vigente
- objetivo: alta de domicilio

#### `PUT /api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}`
- estado: vigente
- objetivo: modificacion de domicilio

#### `PATCH /api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}/baja`
- estado: vigente
- objetivo: baja logica de domicilio

#### `GET /api/v1/personas/{id_persona}/domicilios`
- estado: vigente
- objetivo: consulta de domicilios

### 4.4 Contactos

#### `POST /api/v1/personas/{id_persona}/contactos`
- estado: vigente
- objetivo: alta de contacto

#### `PUT /api/v1/personas/{id_persona}/contactos/{id_persona_contacto}`
- estado: vigente
- objetivo: modificacion de contacto

#### `PATCH /api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja`
- estado: vigente
- objetivo: baja logica de contacto

#### `GET /api/v1/personas/{id_persona}/contactos`
- estado: vigente
- objetivo: consulta de contactos

### 4.5 Relaciones entre personas

#### `POST /api/v1/personas/{id_persona}/relaciones`
- estado: vigente
- objetivo: alta de relacion entre personas

#### `PUT /api/v1/personas/{id_persona}/relaciones/{id_persona_relacion}`
- estado: vigente
- objetivo: modificacion de relacion entre personas

#### `PATCH /api/v1/personas/{id_persona}/relaciones/{id_persona_relacion}/baja`
- estado: vigente
- objetivo: baja logica de relacion entre personas

#### `GET /api/v1/personas/{id_persona}/relaciones`
- estado: vigente
- objetivo: consulta de relaciones entre personas

### 4.6 Representacion y poderes

#### `POST /api/v1/personas/{id_persona}/representaciones-poder`
- estado: vigente
- objetivo: alta de representacion o poder

#### `PUT /api/v1/personas/{id_persona}/representaciones-poder/{id_representacion_poder}`
- estado: vigente
- objetivo: modificacion de representacion o poder

#### `PATCH /api/v1/personas/{id_persona}/representaciones-poder/{id_representacion_poder}/baja`
- estado: vigente
- objetivo: baja logica de representacion o poder

#### `GET /api/v1/personas/{id_persona}/representaciones-poder`
- estado: vigente
- objetivo: consulta de representaciones y poderes

### 4.7 Participacion contextual

Este bloque se mantiene por compatibilidad con documentacion, SQL e implementacion real, pero debe leerse como soporte transversal y no como nucleo puro del dominio `personas`.

Separacion contractual del bloque:

- `rol_participacion`: catalogo de soporte transversal
- `relacion_persona_rol`: asociacion persona-contexto materializada en SQL

#### Catalogo `rol_participacion`

- clasificacion: soporte transversal
- estado API: sin endpoint propio vigente en el router actual
- uso actual: validacion de FK, estado y lectura interna desde servicios de `relacion_persona_rol`
- criterio actual: mantenerlo como soporte interno mientras no exista una necesidad confirmada de exposicion externa
- nota de evolucion: si mas adelante requiere API, el primer paso consistente con el estado actual seria una API read-only separada del recurso de relacion; no hay base implementada hoy para asumir CRUD completo

#### Recurso `relacion_persona_rol`

#### `POST /api/v1/relaciones-persona-rol`
- estado: vigente
- objetivo: alta de `relacion_persona_rol`
- observacion: la implementacion usa `tipo_relacion` + `id_relacion` y valida referencias a contextos como `venta`, `contrato_alquiler`, `cesion`, `escrituracion`, `reserva_venta` y `reserva_locativa`
- dependencia explicita: la validacion del contexto consulta tablas materializadas de otros dominios porque la asociacion es polimorfica en SQL actual
- aclaracion contractual: actualmente este endpoint no esta anidado bajo `/personas/{id_persona}`; esto responde a la implementacion actual. Conceptualmente sigue perteneciendo al dominio `personas` y actua como punto de asociacion transversal.
- compatibilidad heredada: tambien acepta `POST /api/v1/roles-participacion`, pero ese path queda como alias legado porque induce confusion con el catalogo `rol_participacion`

#### `PUT /api/v1/relaciones-persona-rol/{id_relacion_persona_rol}`
- estado: vigente
- objetivo: modificacion de `relacion_persona_rol`
- aclaracion contractual: actualmente este endpoint no esta anidado bajo `/personas/{id_persona}`; esto responde a la implementacion actual. Conceptualmente sigue perteneciendo al dominio `personas` y actua como punto de asociacion transversal.
- compatibilidad heredada: tambien acepta `PUT /api/v1/roles-participacion/{id_relacion_persona_rol}`

#### `PATCH /api/v1/relaciones-persona-rol/{id_relacion_persona_rol}/baja`
- estado: vigente
- objetivo: baja logica de `relacion_persona_rol`
- aclaracion contractual: actualmente este endpoint no esta anidado bajo `/personas/{id_persona}`; esto responde a la implementacion actual. Conceptualmente sigue perteneciendo al dominio `personas` y actua como punto de asociacion transversal.
- compatibilidad heredada: tambien acepta `PATCH /api/v1/roles-participacion/{id_relacion_persona_rol}/baja`

#### `GET /api/v1/personas/{id_persona}/participaciones`
- estado: vigente
- objetivo: consulta de participaciones contextuales de la persona basada en `relacion_persona_rol`

Observaciones de diseno:

- `rol_participacion` no debe interpretarse como atributo base de persona.
- `relacion_persona_rol` actua hoy como soporte polimorfico entre `personas` y contextos de otros dominios.
- el write model del bloque corresponde a `relacion_persona_rol`; usar `roles-participacion` como nombre principal del recurso induce ambiguedad con el catalogo `rol_participacion`
- esta semantica requiere revision arquitectonica futura porque ya materializa referencias a `comercial` y `locativo`
- este modelo introduce acoplamiento entre `personas` y dominios como `comercial` y `locativo`
- su permanencia responde a una decision pragmatica basada en la implementacion actual
- no debe expandirse sin una decision arquitectonica explicita

### 4.8 Consultas y reportes

Endpoints de consulta efectivamente implementados:

- `GET /api/v1/personas/{id_persona}`
- `GET /api/v1/personas/{id_persona}/documentos`
- `GET /api/v1/personas/{id_persona}/domicilios`
- `GET /api/v1/personas/{id_persona}/contactos`
- `GET /api/v1/personas/{id_persona}/relaciones`
- `GET /api/v1/personas/{id_persona}/representaciones-poder`
- `GET /api/v1/personas/{id_persona}/participaciones`

Elementos heredados del DEV-API historico que no deben considerarse contrato vigente implementado:

- `GET /api/v1/personas`
  estado: heredado, no implementado actualmente
  aclaracion contractual: no forma parte del contrato vigente y no debe asumirse como disponible hoy
  nota de evolucion: podra redefinirse a futuro como endpoint de busqueda o consulta analitica, sin implicar disponibilidad actual
- bloque de reporte consolidado amplio del dominio
  estado: heredado, no confirmado en router actual

## 5. Reglas visibles del contrato

- La persona base y el usuario administrativo son conceptos distintos.
- Las operaciones write del dominio exigen contexto tecnico mediante headers transversales.
- Las operaciones write del dominio pueden utilizar `X-Op-Id` para control de idempotencia en contextos distribuidos.
- Las operaciones update y baja con versionado utilizan `If-Match-Version`.
- `id_persona` es generado por el sistema y constituye la referencia unica del sujeto dentro del dominio.
- Las consultas del dominio no generan efectos persistentes.
- La representacion y las relaciones entre personas pertenecen al dominio propio de `personas`.
- La participacion contextual no redefine la identidad base de la persona.
- Las referencias contextuales de participacion no convierten a `personas` en dueno semantico de `comercial` ni de `locativo`.

## 6. Notas de compatibilidad y decisiones pendientes

### 6.1 Clasificacion funcional

El DEV-API historico documenta endpoints de clasificacion o condicion como:

- `PATCH /api/v1/personas/{id_persona}/clasificacion`
- `GET /api/v1/personas/{id_persona}/clasificacion`

Con ejemplos de categorias como:

- `CLIENTE`
- `GARANTE`

Estado actual:

- heredado del contrato historico
- pendiente de revision arquitectonica
- no consolidado como nucleo puro del dominio `personas`
- no confirmado en la implementacion real observada

### 6.2 Cliente comprador

El DEV-API historico documenta:

- `POST /api/v1/clientes-compradores`
- `GET /api/v1/clientes-compradores/{id_persona}`

Estado actual:

- heredado del contrato historico
- semantica comercial o proyeccion funcional, no nucleo base de `personas`
- existe materializacion en SQL (`cliente_comprador`)
- no se observo implementacion real activa en router, schemas o services del backend actual

### 6.3 Roles de participacion

El contrato historico corrige que los roles no son atributos directos de persona, sino participaciones contextuales. Esa correccion se considera valida.

Sin embargo, su materializacion actual:

- ya existe en SQL
- ya existe en API implementada
- ya existe en codigo y tests

Por eso, el bloque se conserva en este documento como contrato vigente, pero marcado como soporte transversal con revision arquitectonica pendiente.

Aclaracion contractual vigente:

- el catalogo `rol_participacion` no tiene hoy API propia confirmada
- el recurso write vigente del bloque es `relacion_persona_rol`
- `/api/v1/roles-participacion` queda como compatibilidad heredada y no como naming recomendado del recurso

### 6.4 Compatibilidad con `SYS-MAP-002`

Este documento se alinea con `SYS-MAP-002` en que:

- `personas` es dominio transversal autonomo
- no depende de `comercial`
- no depende de `locativo`
- no debe absorber semantica funcional ajena como identidad base

Cuando exista tension entre el DEV-API historico y ese criterio, prevalece el criterio arquitectonico actual y se marca el legado como heredado o pendiente.

### 6.5 Naming actual de endpoints

Algunos nombres de endpoints reflejan la implementacion actual y no una normalizacion contractual definitiva.

Ejemplo:

- `representaciones-poder`

Estos nombres podran normalizarse en futuras versiones del contrato sin alterar la semantica vigente.
