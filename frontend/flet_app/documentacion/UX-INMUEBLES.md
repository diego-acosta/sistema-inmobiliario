# UX-INMUEBLES

## Alta de inmueble integrada

La pantalla real `frontend/flet_app/app/pages/inmuebles_page.py` incorpora el botón **Nuevo inmueble** en el listado de inmuebles y reutiliza los helpers compartidos de alta para crear el inmueble y, opcionalmente, su dato catastral/registral inicial.

El formulario integrado mantiene el alcance validado: no envía linderos, no edita ni elimina datos catastrales/registrales, no implementa ficha/detalle completa y refresca el listado real después de un alta exitosa. Después de un alta creada, el formulario deshabilita Guardar inmueble y exige usar Nueva alta para limpiar campos y evitar doble guardado accidental.

## Prototipo aislado de alta de inmueble

El prototipo Flet independiente `frontend/flet_app/prototypes/inmueble_alta_prototype.py` valida el alta real de inmuebles contra el backend existente y permite, opcionalmente, cargar un dato catastral/registral inicial inmediatamente después de crear el inmueble.

Ejecución prevista:

```bash
cd frontend/flet_app
python prototypes/inmueble_alta_prototype.py
```

El prototipo se mantiene como prueba visual aislada. El flujo validado se integró al listado real de inmuebles sin modificar backend, SQL ni contratos API.

## Endpoints usados

### Alta básica de inmueble

- Método: `POST`.
- Path: `/api/v1/inmuebles`.
- Cliente Flet: `ApiClient.crear_inmueble(...)`.

### Alta opcional de dato catastral/registral

- Método: `POST`.
- Path: `/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales`.
- Cliente Flet: `ApiClient.crear_dato_catastral_registral_inmueble(...)`.

El backend de datos catastrales/registrales ya existe como subrecurso de inmueble. La UI del prototipo lo consume solo para crear un dato inicial; edición, baja, listado e historial visual quedan pendientes.

## Flujo UX

1. Desde la pantalla real de inmuebles, el usuario presiona **Nuevo inmueble** y carga los **Datos básicos del inmueble**. En esta sección se muestran también `manzana` y `lote` por ser datos de uso cotidiano.
2. `manzana` y `lote` no se envían en el payload de `POST /api/v1/inmuebles`; se guardan como parte del dato catastral/registral asociado.
3. El control `Mostrar datos catastrales/registrales avanzados` solo muestra u oculta campos avanzados; no significa por sí mismo que el dato catastral deba guardarse.
4. Si la sección avanzada está oculta y no informa `manzana` ni `lote`, el prototipo crea solo el inmueble.
5. Si la sección avanzada está oculta pero informa `manzana` o `lote`, el prototipo crea el inmueble y luego crea automáticamente un dato catastral/registral con `estado_dato: ACTIVO` más esos campos. Los valores residuales que hubiera en campos avanzados no se envían mientras la sección esté oculta.
6. Si la sección avanzada está visible, el prototipo valida superficies positivas si fueron informadas y envía `manzana`/`lote` más los campos avanzados cargados.
7. Con el `id_inmueble` devuelto por el backend, el prototipo invoca el alta del dato catastral/registral asociado cuando corresponde.
8. En modo técnico se muestran payloads, responses y errores backend, destacando que `manzana`/`lote` no pertenecen al payload de inmueble.
9. Si el alta es exitosa, la pantalla real refresca el listado de inmuebles y permite cerrar el formulario o usar **Nueva alta** para limpiar campos, ocultar avanzados y volver a habilitar el guardado.

## Payload mínimo confirmado de inmueble

```json
{
  "codigo_inmueble": "INM-FLET-001",
  "estado_administrativo": "ACTIVO",
  "estado_juridico": "REGULAR"
}
```

## Payload completo posible de inmueble

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

El prototipo construye un payload limpio: no envía campos vacíos, recorta textos, convierte `id_desarrollo` a entero positivo cuando se informa y mantiene `superficie` como decimal compatible con el backend. Aunque se muestran visualmente en datos básicos, `manzana` y `lote` no se agregan a este payload.

## Payload opcional de dato catastral/registral

Campos soportados por el formulario del prototipo:

- `nomenclatura_catastral`.
- `partida_inmobiliaria`.
- `matricula`.
- `folio_real`.
- `circunscripcion`.
- `seccion`.
- `manzana`.
- `lote`.
- `parcela`.
- `superficie_titulo`.
- `superficie_mensura`.
- `medidas`.
- `situacion_posesoria`.
- `situacion_dominial`.
- `estado_dato` con default `ACTIVO` y opciones `ACTIVO`, `INACTIVO`, `HISTORICO`.
- `observaciones`.

No se agregan `linderos` en este PR. Visualmente, `manzana` y `lote` se capturan en **Datos básicos del inmueble**, pero técnicamente se incluyen solo en este payload catastral/registral. Los campos avanzados se envían únicamente cuando la sección avanzada está visible; ocultarla conserva lo escrito en pantalla, pero evita enviar esos campos.

Ejemplo:

```json
{
  "estado_dato": "ACTIVO",
  "nomenclatura_catastral": "NC-001",
  "partida_inmobiliaria": "PI-001",
  "matricula": "MAT-001",
  "folio_real": "FR-001",
  "circunscripcion": "C1",
  "seccion": "S1",
  "manzana": "M1",
  "lote": "L1",
  "parcela": "P1",
  "superficie_titulo": "120.50",
  "superficie_mensura": "118.75",
  "medidas": "10 x 12",
  "situacion_posesoria": "Sin observaciones",
  "situacion_dominial": "Regular",
  "observaciones": "Carga inicial desde prototipo"
}
```

## Headers CORE-EF para altas

Las dos altas usadas por el prototipo son endpoints write sincronizables clasificados como `COMMAND_WRITE_NEGOCIO` para esta UI.

Headers enviados por `ApiClient.crear_inmueble(...)` y `ApiClient.crear_dato_catastral_registral_inmueble(...)`:

- `X-Op-Id`: UUID válido generado por el cliente cuando no se provee uno válido.
- `X-Usuario-Id`: `"1"`.
- `X-Sucursal-Id`: `"1"`.
- `X-Instalacion-Id`: `"1"`.

No se envía `If-Match-Version` porque ambas operaciones del prototipo son altas y no modifican una entidad existente/versionada.

## Validaciones frontend mínimas

El backend sigue siendo la fuente de verdad. El prototipo solo bloquea errores básicos de captura:

- `codigo_inmueble` requerido.
- `estado_administrativo` requerido.
- `estado_juridico` requerido.
- `superficie` debe ser decimal positivo si se informa.
- `id_desarrollo` debe ser entero positivo si se informa.
- `superficie_titulo` debe ser decimal positivo si se informa.
- `superficie_mensura` debe ser decimal positivo si se informa.

No se exige `nomenclatura_catastral`, `partida_inmobiliaria` ni `matricula`. No se agregan validaciones de dominio no confirmadas.

## Opciones DEV-SRV usadas para estados

Aunque Pydantic usa `str` y no se detectó `CHECK` SQL para los estados básicos del inmueble, la UI usa las opciones recomendadas por DEV-SRV:

- `estado_administrativo`: `ACTIVO`, `INACTIVO`.
- `estado_juridico`: `REGULAR`, `OBSERVADO`.

Para el dato catastral/registral se usan las opciones confirmadas por el schema backend:

- `estado_dato`: `ACTIVO`, `INACTIVO`, `HISTORICO`.

## Mensajes esperados

En éxito de alta básica:

- `Inmueble creado correctamente`.

En éxito de alta básica más dato catastral/registral:

- `Inmueble creado correctamente`.
- `Datos catastrales/registrales creados correctamente`.

En éxito de alta básica más dato automático solo por manzana/lote:

- `Inmueble creado correctamente`.
- `Datos de manzana/lote guardados correctamente`.

Si se muestra la sección avanzada sin informar ningún dato útil, incluyendo manzana/lote:

- `Cargá al menos un dato catastral/registral o ocultá la sección avanzada`.

Si falla la segunda llamada:

- `El inmueble fue creado, pero no se pudieron guardar los datos catastrales/registrales`.
- Detalle técnico del error backend.

El prototipo no oculta el `id_inmueble` en modo técnico.

## Modo técnico

El panel técnico muestra:

- payload de inmueble enviado, sin `manzana` ni `lote`.
- response de inmueble.
- payload catastral enviado, con `manzana` y/o `lote` cuando fueron informados.
- response catastral.
- errores backend.

## Alcance funcional

- Alta inicial de inmueble.
- Alta opcional de un dato catastral/registral inicial.
- No genera disponibilidad inicial.
- No genera ocupación inicial.
- Integra el alta en el listado real de inmuebles.
- No implementa edición, baja, listado ni historial visual de datos catastrales/registrales.
- No toca backend, SQL, endpoints, Wizard Venta Completa V3, ventas, reservas ni financiero.
- No agrega linderos.

## Decisión CORE-EF

- Naturaleza de los endpoints write usados: `COMMAND_WRITE_NEGOCIO`.
- Headers: aplica; se envían `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` desde el cliente Flet.
- `If-Match-Version`: NO APLICA; las operaciones del prototipo son creación de registros nuevos sin versión previa a comparar.
- Idempotencia: aplica por `X-Op-Id` a nivel de contrato CORE-EF del endpoint; el prototipo genera/reutiliza un UUID válido, pero no implementa persistencia local de reintentos.
- Outbox: NO CONFIRMADO en frontend; no se declara cumplimiento profundo sin evidencia de router/service/repository/SQL en este PR.
- Lock lógico: NO APLICA en frontend; no se bloquea una entidad existente desde el prototipo de alta.
- Versionado: la respuesta puede incluir `version_registro`; las altas no envían versión de entrada.
- Rollback/transacción: cada llamada mantiene su frontera backend. Si falla la segunda llamada, el inmueble queda creado y la UI informa el fallo parcial.
- Tests del PR: compileall, diff check, prueba inline de payload/headers sin backend vivo y, si el entorno lo permite, test backend específico del subrecurso.
