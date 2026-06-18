# UX-INMUEBLES

## Prototipo aislado de alta de inmueble

Se agrega un prototipo Flet independiente en `frontend/flet_app/prototypes/inmueble_alta_prototype.py` para validar el alta real de inmuebles contra el backend existente.

Ejecución prevista:

```bash
cd frontend/flet_app
python prototypes/inmueble_alta_prototype.py
```

El prototipo no se integra todavía al listado real de inmuebles ni al flujo productivo de la aplicación Flet. La integración al listado queda pendiente para un PR posterior.

## Endpoint usado

- Método: `POST`.
- Path: `/api/v1/inmuebles`.
- Cliente Flet: `ApiClient.crear_inmueble(...)`.

## Payload mínimo confirmado

```json
{
  "codigo_inmueble": "INM-FLET-001",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR"
}
```

## Payload completo posible

```json
{
  "id_desarrollo": 1,
  "codigo_inmueble": "INM-FLET-001",
  "nombre_inmueble": "Casa piloto Flet",
  "superficie": "120.50",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR",
  "observaciones": "Alta desde prototipo Flet"
}
```

El prototipo construye un payload limpio: no envía campos vacíos, recorta textos, convierte `id_desarrollo` a entero positivo cuando se informa y mantiene `superficie` como decimal compatible con el backend.

## Headers CORE-EF para alta

El alta es un endpoint write sincronizable clasificado como `COMMAND_WRITE_NEGOCIO` para la UI del prototipo.

Headers enviados por `ApiClient.crear_inmueble(...)`:

- `X-Op-Id`: UUID válido generado por el cliente cuando no se provee uno válido.
- `X-Usuario-Id`: `"1"`.
- `X-Sucursal-Id`: `"1"`.
- `X-Instalacion-Id`: `"1"`.

No se envía `If-Match-Version` porque el alta crea una entidad nueva y no modifica una entidad existente/versionada.

## Campos del formulario

### Obligatorios

- `codigo_inmueble`: código de inmueble.
- `estado_administrativo`: estado administrativo.
- `estado_juridico`: estado jurídico.

### Opcionales

- `nombre_inmueble`.
- `superficie`.
- `id_desarrollo`.
- `observaciones`.

## Validaciones frontend mínimas

El backend sigue siendo la fuente de verdad. El prototipo solo bloquea errores básicos de captura:

- `codigo_inmueble` requerido.
- `estado_administrativo` requerido.
- `estado_juridico` requerido.
- `superficie` debe ser decimal positivo si se informa.
- `id_desarrollo` debe ser entero positivo si se informa.

No se agregan validaciones de dominio no confirmadas.

## Opciones DEV-SRV usadas para estados

Aunque Pydantic usa `str` y no se detectó `CHECK` SQL para estos campos, la UI usa las opciones recomendadas por DEV-SRV:

- `estado_administrativo`: `ACTIVO`, `INACTIVO`.
- `estado_juridico`: `REGULAR`, `OBSERVADO`.

No se usa `EN_TRAMITE` como opción recomendada.

## Alcance funcional

- Alta inicial únicamente.
- Crea solo el inmueble.
- No genera disponibilidad inicial.
- No genera ocupación inicial.
- No integra todavía al listado de inmuebles.
- No toca backend, SQL, endpoints, Wizard Venta Completa V3, ventas, reservas ni financiero.

## Resultado visual esperado

En éxito, el prototipo muestra un mensaje verde y los datos devueltos por el backend cuando estén presentes:

- `id_inmueble`.
- `codigo_inmueble`.
- `estado_administrativo`.
- `estado_juridico`.
- `version_registro`.
- `uid_global` en una sección técnica secundaria.

En error, el prototipo muestra un mensaje legible con `status_code`, `error_code`, `error_message` y `error_details` cuando estén disponibles. Esto permite diagnosticar `VALIDATION_ERROR` por headers/campos y errores de aplicación como `APPLICATION_ERROR` o `NOT_FOUND_DESARROLLO` cuando se informa un `id_desarrollo` inexistente.

## Decisión CORE-EF

- Naturaleza del endpoint: `COMMAND_WRITE_NEGOCIO`.
- Headers: aplica; se envían `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` desde el cliente Flet.
- `If-Match-Version`: NO APLICA; creación de entidad nueva sin versión previa a comparar.
- Idempotencia: aplica por `X-Op-Id` a nivel de contrato CORE-EF del endpoint; el prototipo genera/reutiliza un UUID válido, pero no implementa persistencia local de reintentos.
- Outbox: NO CONFIRMADO en frontend; no se declara cumplimiento profundo sin evidencia de router/service/repository/SQL en este PR.
- Lock lógico: NO APLICA en frontend; no se bloquea una entidad existente desde el prototipo de alta.
- Versionado: la respuesta puede incluir `version_registro`; el alta no envía versión de entrada.
- Rollback/transacción: frontera backend del caso de uso; el prototipo solo invoca el endpoint.
- Tests del PR: compileall, diff check y prueba inline de payload/headers sin backend vivo.
