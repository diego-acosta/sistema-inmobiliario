# AUDITORIA-INMUEBLES-FRONTEND

## 1. Resumen ejecutivo

### Que existe hoy

- Existe un endpoint real de alta de inmueble: `POST /api/v1/inmuebles`, implementado en `backend/app/api/routers/inmuebles_router.py`.
- El alta usa el schema Pydantic `InmuebleCreateRequest` y responde con `InmuebleCreateResponse`, definidos en `backend/app/api/schemas/inmuebles.py`.
- El servicio `CreateInmuebleService` valida solo la existencia de `id_desarrollo` cuando viene informado y persiste el inmueble con `version_registro = 1`.
- El repositorio inserta en la tabla `inmueble` y hace `commit()` en `create_inmueble`.
- La tabla SQL `inmueble` permite `id_desarrollo` nullable y `superficie` nullable; exige `codigo_inmueble`, `estado_administrativo` y `estado_juridico` como `NOT NULL`.
- Existen endpoints read de detalle, detalle integral y listado/busqueda de inmuebles.
- El frontend Flet ya tiene pantalla de listado, busqueda y ficha integral de inmuebles en `frontend/flet_app/app/pages/inmuebles_page.py`.
- `ApiClient` ya tiene `get_inmuebles`, `listar_inmuebles` y `get_inmueble_detalle_integral`.

### Que falta para el alta frontend

- No se encontro metodo `crear_inmueble` / `create_inmueble` en `frontend/flet_app/app/api_client.py`.
- No se encontro pantalla/formulario Flet de alta de inmueble.
- Falta definir UX de captura de headers CORE-EF o estrategia tecnica para proveerlos desde el prototipo.
- Falta manejo frontend especifico de errores `ErrorResponse` para el alta.
- Falta documentar en UX que los valores recomendados para `estado_administrativo` y `estado_juridico` deben salir del catalogo DEV-SRV, aunque Pydantic no use enum y SQL no tenga `CHECK` detectado.

### Riesgos detectados

- Los estados administrativos/juridicos son `str` en Pydantic y `varchar(30)` en SQL. El catalogo DEV-SRV lista valores implementados para UI/documentacion (`ACTIVO`, `INACTIVO`, `REGULAR`, `OBSERVADO`), pero no se detecto enum Pydantic ni `CHECK` SQL que bloquee tecnicamente otros strings en el alta.
- El alta requiere headers CORE-EF obligatorios (`X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`). Si el prototipo no los envia, el backend responde error de validacion.
- `If-Match-Version` no aplica al alta porque el endpoint usa `_CORE_EF_REQUIRED_HEADERS_OPENAPI`, no la variante con `If-Match-Version`.
- El alta no genera disponibilidad u ocupacion inicial en el flujo revisado; solo inserta `inmueble`.
- La respuesta exitosa del alta no devuelve todos los campos enviados: devuelve identificadores/version y estados base.

## 2. Backend — endpoints de inmuebles

### `POST /api/v1/inmuebles`

- Metodo: `POST`.
- Path: `/api/v1/inmuebles`.
- Proposito: alta de inmueble.
- Request: body `InmuebleCreateRequest`.
- Response: status `201`, body `InmuebleCreateResponse`.
- Headers: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` obligatorios.
- Errores declarados: `400` y `500` con `ErrorResponse`.
- Errores observados en flujo: headers invalidos/faltantes generan `VALIDATION_ERROR`; fallo de aplicacion genera `APPLICATION_ERROR`; excepcion genera `INTERNAL_ERROR`.

### `GET /api/v1/inmuebles`

- Metodo: `GET`.
- Path: `/api/v1/inmuebles`.
- Proposito: listado/busqueda de inmuebles.
- Request: query params `q`, `estado_administrativo`, `estado_juridico`, `id_desarrollo`, `disponibilidad_actual`, `ocupacion_actual`, `id_servicio`, `limit`, `offset`.
- Response: `InmuebleListResponse` con `data`, `items`, `total`, `limit`, `offset`.
- Headers: no se detectan headers CORE-EF en el router para este GET.
- Errores declarados: `400` y `500` con `ErrorResponse`.

### `GET /api/v1/inmuebles/{id_inmueble}`

- Metodo: `GET`.
- Path: `/api/v1/inmuebles/{id_inmueble}`.
- Proposito: detalle base de inmueble.
- Request: path param `id_inmueble`.
- Response: `InmuebleDetailResponse`.
- Headers: no se detectan headers CORE-EF en el router para este GET.
- Errores declarados: `404` y `500` con `ErrorResponse`; el codigo tambien puede devolver `400` si el servicio falla con error distinto de `NOT_FOUND`.

### `GET /api/v1/inmuebles/{id_inmueble}/detalle-integral`

- Metodo: `GET`.
- Path: `/api/v1/inmuebles/{id_inmueble}/detalle-integral`.
- Proposito: ficha integral read-only de inmueble para UI.
- Request: path param `id_inmueble`.
- Response: `InmuebleDetalleIntegralResponse` con `data: dict[str, Any]`.
- Headers: no se detectan headers CORE-EF en el router para este GET.
- Errores declarados: `404` y `500` con `ErrorResponse`.

### `PUT /api/v1/inmuebles/{id_inmueble}`

- Metodo: `PUT`.
- Path: `/api/v1/inmuebles/{id_inmueble}`.
- Proposito: modificacion de inmueble existente.
- Request: path param `id_inmueble`, body `InmuebleUpdateRequest`.
- Response: `InmuebleUpdateResponse`.
- Headers: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version` obligatorios.
- Errores declarados: `404`, `409`, `400`, `500` con `ErrorResponse`.

### `PATCH /api/v1/inmuebles/{id_inmueble}/baja`

- Metodo: `PATCH`.
- Path: `/api/v1/inmuebles/{id_inmueble}/baja`.
- Proposito: baja logica de inmueble.
- Request: path param `id_inmueble`.
- Response: `InmuebleBajaResponse`.
- Headers: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version` obligatorios.
- Errores declarados: `404`, `409`, `400`, `500` con `ErrorResponse`.

### `PATCH /api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`

- Metodo: `PATCH`.
- Path: `/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo`.
- Proposito: asociar inmueble a desarrollo.
- Request: path param `id_inmueble`, body `InmuebleAsociarDesarrolloRequest` con `id_desarrollo`.
- Response: `InmuebleAsociarDesarrolloResponse`.
- Headers: el router acepta `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version`, pero en este endpoint no usa el helper comun CORE-EF ni declara `openapi_extra`. Pendiente de confirmacion si deben considerarse estrictamente obligatorios para UI.
- Errores declarados: `404`, `409`, `400`, `500` con `ErrorResponse`.

### `PATCH /api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`

- Metodo: `PATCH`.
- Path: `/api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo`.
- Proposito: desasociar inmueble de desarrollo.
- Request: path param `id_inmueble`.
- Response: `InmuebleDesasociarDesarrolloResponse`.
- Headers: el router acepta `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` e `If-Match-Version`, pero en este endpoint no usa el helper comun CORE-EF ni declara `openapi_extra`. Pendiente de confirmacion si deben considerarse estrictamente obligatorios para UI.
- Errores declarados: `404`, `409`, `400`, `500` con `ErrorResponse`.

## 3. Alta de inmueble

### Endpoint exacto

`POST /api/v1/inmuebles`

### Payload minimo confirmado

Segun `InmuebleCreateRequest`, los campos sin default son obligatorios:

```json
{
  "codigo_inmueble": "INM-FLET-001",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR"
}
```

### Payload completo posible confirmado

```json
{
  "id_desarrollo": 1,
  "codigo_inmueble": "INM-FLET-001",
  "nombre_inmueble": "Inmueble Flet auditoria",
  "superficie": "100.00",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR",
  "observaciones": "Ejemplo documental; no ejecutar como dato productivo."
}
```

### Campos obligatorios

- `codigo_inmueble`: `str`; SQL `varchar(50) NOT NULL`.
- `estado_administrativo`: `str`; SQL `varchar(30) NOT NULL`.
- `estado_juridico`: `str`; SQL `varchar(30) NOT NULL`.

### Campos opcionales

- `id_desarrollo`: `int | None`; SQL nullable. El servicio valida existencia si se informa.
- `nombre_inmueble`: `str | None`; SQL nullable.
- `superficie`: `Decimal | None`; SQL `numeric(14,2)` nullable.
- `observaciones`: `str | None`; SQL `text` nullable.

### Valores permitidos

#### 1. Fuente contractual/documental DEV-SRV

El catalogo `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/EST-INM.md` lista como valores implementados para `inmueble`:

- `estado_administrativo`: `ACTIVO`, `INACTIVO`.
- `estado_juridico`: `REGULAR`, `OBSERVADO`.

Para el proximo PR frontend, estas opciones DEV-SRV deben ser la fuente principal para dropdowns/opciones sugeridas.

#### 2. Fuente tecnica revisada

- Pydantic usa `str` para `estado_administrativo` y `estado_juridico`; no se detecto enum en `InmuebleCreateRequest`.
- SQL usa `varchar(30)` para ambos campos; no se detecto `CHECK` junto a la definicion de la tabla `inmueble`.
- Por lo anterior, el backend podria no impedir tecnicamente otros strings si no existe validacion adicional fuera de las fuentes revisadas. Esto no convierte esos strings en valores contractuales recomendados para UI.

#### 3. Seeds observados

Valores observados en seeds, solo como evidencia de datos cargados y no como lista cerrada ni guia principal de dropdown/validacion:

- `ACTIVO`.
- `REGULAR`.
- `EN_TRAMITE`, observado en seed de demo UI.

#### 4. Inconsistencia detectada

- `EN_TRAMITE` aparece en seeds pero no figura en el catalogo DEV-SRV revisado para `inmueble.estado_juridico`.
- `OBSERVADO` figura en DEV-SRV para `inmueble.estado_juridico`, aunque puede no aparecer en los seeds revisados.
- El proximo PR frontend debe priorizar DEV-SRV para opciones sugeridas y no considerar seeds como lista cerrada.

#### 5. Recomendacion para frontend

Dropdown inicial recomendado:

- `estado_administrativo`: `ACTIVO`, `INACTIVO`.
- `estado_juridico`: `REGULAR`, `OBSERVADO`.

Hasta que backend formalice enum/CHECK u otra validacion verificable, el frontend solo debe presentar estas opciones como recomendadas por DEV-SRV; no debe afirmar que son la unica validacion contractual aplicada por backend. Si se decide permitir texto libre temporalmente, debe quedar documentado explicitamente como decision UX provisional y no como regla del dominio.

### Ejemplo realista de request

```http
POST /api/v1/inmuebles HTTP/1.1
Content-Type: application/json
X-Op-Id: 11111111-1111-4111-8111-111111111111
X-Usuario-Id: 1
X-Sucursal-Id: 1
X-Instalacion-Id: 1

{
  "codigo_inmueble": "INM-FLET-001",
  "nombre_inmueble": "Casa piloto Flet",
  "superficie": "120.50",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR",
  "observaciones": "Alta desde futuro prototipo Flet"
}
```

### Ejemplo realista de response

```json
{
  "ok": true,
  "data": {
    "id_inmueble": 123,
    "uid_global": "22222222-2222-4222-8222-222222222222",
    "version_registro": 1,
    "codigo_inmueble": "INM-FLET-001",
    "estado_administrativo": "ACTIVO",
    "estado_juridico": "REGULAR"
  }
}
```

## 4. CORE-EF / sincronizacion

Clasificacion del alta: `COMMAND_WRITE_NEGOCIO` para el PR posterior que implemente UI, porque crea una entidad de negocio del dominio inmobiliario. En este PR no se modifica endpoint write ni se implementa llamada write.

Para `POST /api/v1/inmuebles`:

- `X-Op-Id`: aplica. Obligatorio por helper comun CORE-EF y OpenAPI extra del endpoint.
- `X-Usuario-Id`: aplica. Obligatorio por helper comun CORE-EF y OpenAPI extra del endpoint.
- `X-Sucursal-Id`: aplica. Obligatorio por helper comun CORE-EF y OpenAPI extra del endpoint.
- `X-Instalacion-Id`: aplica. Obligatorio por helper comun CORE-EF y OpenAPI extra del endpoint.
- `If-Match-Version`: no aplica al alta, porque crea entidad nueva y el endpoint no usa la variante con `If-Match-Version`.
- Otro header: no se detecto otro header obligatorio especifico para el alta.

Aspectos CORE-EF profundos del alta:

- Idempotencia: pendiente de confirmacion. El endpoint registra `op_id_alta`, pero no se detecto logica de idempotencia por `op_id + payload` en el servicio/repositorio de alta.
- Outbox: pendiente/no confirmado. No se detecto emision de evento outbox en `CreateInmuebleService` ni en `create_inmueble` del repositorio.
- Lock logico: no confirmado para alta. No se detecto lock logico en el flujo de alta revisado.
- Versionado: aplica como version inicial; el servicio crea `version_registro = 1`.
- Rollback/transaccion: el repositorio hace `commit()` luego del insert; no se detecto orquestacion multi-repositorio para el alta.

## 5. Frontend existente

### Archivos Flet relacionados con inmuebles

- `frontend/flet_app/app/pages/inmuebles_page.py`: hub de inmuebles, listado/busqueda, listado de unidades funcionales y detalle integral.
- `frontend/flet_app/app/shell.py`: registra rutas `inmuebles`, `inmueble_detail` y `unidad_funcional_detail`.
- `frontend/flet_app/app/pages/home_page.py`: expone acceso a Inmuebles con descripcion de ficha inmobiliaria integral.
- `frontend/flet_app/app/pages/venta_create_wizard_page.py`: usa identificadores de inmueble/unidad en Wizard Venta Completa V3. No tocar en el PR posterior salvo requerimiento explicito.

### Listado/busqueda existente

- `InmueblesListView` llama a `self.api.get_inmuebles(...)` con filtros `q`, `estado_administrativo`, `estado_juridico`, `disponibilidad_actual` y `ocupacion_actual`.
- El detalle integral de inmueble usa `self.api.get_inmueble_detalle_integral(self.id_inmueble)`.

### Metodos de `ApiClient` existentes

- `get_inmuebles(...)`: existe y llama `GET /api/v1/inmuebles`.
- `listar_inmuebles(...)`: existe como wrapper de `get_inmuebles(...)`.
- `get_inmueble_detalle_integral(id_inmueble)`: existe y llama `GET /api/v1/inmuebles/{id_inmueble}/detalle-integral`.
- `get_unidades_funcionales(...)` y `listar_unidades_funcionales(...)`: existen para busqueda/listado de unidades funcionales.

### Metodo POST/crear inmueble

- No se encontro `crear_inmueble` ni `create_inmueble` en `frontend/flet_app/app/api_client.py`.
- `ApiClient` tiene helper interno `_post(...)`, por lo que el PR posterior podria agregar un metodo especifico sin inventar endpoint.

## 6. Brecha para prototipo de alta

En un PR posterior habria que agregar exactamente:

1. Metodo `ApiClient` faltante:
   - Nombre sugerido: `crear_inmueble` o `create_inmueble`.
   - Endpoint a usar: `POST /api/v1/inmuebles`.
   - Headers a enviar: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
   - No enviar `If-Match-Version` para alta.
2. Formulario Flet aislado:
   - Campos obligatorios: `codigo_inmueble`, `estado_administrativo`, `estado_juridico`.
   - Campos opcionales: `id_desarrollo`, `nombre_inmueble`, `superficie`, `observaciones`.
   - Sin modificar Wizard Venta Completa V3.
3. Validaciones frontend minimas:
   - `codigo_inmueble` no vacio.
   - `estado_administrativo` no vacio.
   - `estado_juridico` no vacio.
   - `id_desarrollo`, si se informa, debe ser entero.
   - `superficie`, si se informa, debe ser decimal valido; puede omitirse.
   - Para opciones iniciales, priorizar DEV-SRV: `estado_administrativo` con `ACTIVO`/`INACTIVO` y `estado_juridico` con `REGULAR`/`OBSERVADO`; no usar seeds como lista principal de dropdown/validacion.
4. Manejo de errores:
   - Mostrar `error_code`, `error_message` y `details` de `ErrorResponse`.
   - Tratar especialmente `VALIDATION_ERROR` por headers CORE-EF.
   - Tratar `APPLICATION_ERROR` con `NOT_FOUND_DESARROLLO` en details si se envia `id_desarrollo` inexistente.
5. Documentacion UX:
   - Aclarar que la pantalla es prototipo aislado.
   - Aclarar que no genera disponibilidad/ocupacion inicial.
   - Aclarar que `id_desarrollo` es opcional.
   - Aclarar que `superficie` es opcional.

## 7. Recomendacion de implementacion

Proximo PR recomendado: **“Agregar prototipo Flet aislado de alta de inmueble”**.

Alcance recomendado:

- Agregar metodo especifico de alta en `ApiClient` usando el endpoint confirmado.
- Agregar pantalla/formulario aislado bajo la seccion Inmuebles o una ruta nueva de prototipo claramente separada.
- Reutilizar `ErrorResponse` recibido por backend sin inventar estructura alternativa.
- No tocar backend, SQL, tests de backend ni Wizard Venta Completa V3 salvo que el alcance cambie explicitamente.

## 8. Checklist para el proximo PR

### Archivos a tocar

- `frontend/flet_app/app/api_client.py`: agregar metodo de alta con `POST /api/v1/inmuebles`.
- `frontend/flet_app/app/pages/inmuebles_page.py` o un archivo nuevo Flet aislado para el formulario.
- `frontend/flet_app/app/shell.py` solo si se agrega ruta nueva.
- Documentacion frontend del prototipo si se agrega una guia UX.

### Archivos a no tocar

- Backend completo (`backend/app/**`) salvo nuevo requerimiento explicito.
- SQL (`backend/database/**`) salvo nuevo requerimiento explicito.
- Tests backend salvo que el PR posterior modifique contratos backend, cosa no recomendada para el prototipo.
- `frontend/flet_app/app/pages/venta_create_wizard_page.py`.
- Wizard Venta Completa V3 y documentacion asociada.

### Endpoint a usar

`POST /api/v1/inmuebles`

### Payload a enviar

Minimo:

```json
{
  "codigo_inmueble": "...",
  "estado_administrativo": "...",
  "estado_juridico": "..."
}
```

Completo:

```json
{
  "id_desarrollo": 1,
  "codigo_inmueble": "...",
  "nombre_inmueble": "...",
  "superficie": "100.00",
  "estado_administrativo": "...",
  "estado_juridico": "...",
  "observaciones": "..."
}
```

### Headers a enviar

```http
X-Op-Id: <uuid>
X-Usuario-Id: <int/string parseable por backend>
X-Sucursal-Id: <int/string parseable por backend>
X-Instalacion-Id: <int/string parseable por backend>
```

No enviar `If-Match-Version` para alta.

### Validaciones minimas

- Requerir `codigo_inmueble`.
- Requerir `estado_administrativo`.
- Requerir `estado_juridico`.
- Validar `id_desarrollo` entero positivo si se informa.
- Validar `superficie` decimal positiva si se informa. Pendiente de confirmacion si el backend permite cero/negativo; no se detecto regla explicita en Pydantic/servicio.
- Las opciones sugeridas deben salir de DEV-SRV (`ACTIVO`/`INACTIVO`, `REGULAR`/`OBSERVADO`) y la inconsistencia seed/catalogo (`EN_TRAMITE` en seeds, no en DEV-SRV) debe permanecer documentada.

### Comandos de test

```bash
python -m compileall -q frontend/flet_app
git diff --check
```

## Fuentes revisadas

- `backend/documentacion/DEV-API/dominios/inmobiliario/DEV-API-INM-001.md`.
- `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/EST-INM.md`.
- `backend/app/api/routers/inmuebles_router.py`.
- `backend/app/api/schemas/inmuebles.py`.
- `backend/app/application/inmuebles/commands/create_inmueble.py`.
- `backend/app/application/inmuebles/services/create_inmueble_service.py`.
- `backend/app/infrastructure/persistence/repositories/inmueble_repository.py`.
- `backend/database/schema_inmobiliaria_20260418.sql`.
- `backend/database/seed_minimo.sql`.
- `backend/database/seed_demo_ui.sql`.
- `backend/tests/test_inmuebles_create.py` y tests de inmuebles existentes listados en `backend/tests/`.
- `frontend/flet_app/app/api_client.py`.
- `frontend/flet_app/app/pages/inmuebles_page.py`.
- `frontend/flet_app/app/shell.py`.
- `frontend/flet_app/app/pages/home_page.py`.
- `frontend/flet_app/app/pages/venta_create_wizard_page.py` solo como archivo a no tocar por dependencia con Wizard Venta Completa V3.
