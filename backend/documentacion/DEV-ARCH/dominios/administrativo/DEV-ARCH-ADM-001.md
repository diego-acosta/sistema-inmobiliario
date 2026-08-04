# DEV-ARCH-ADM-001 — Freeze de configuración administrativa

## 1. Propósito y estado

Este documento congela la fuente de verdad arquitectónica de configuración y parametrización del dominio `administrativo`. Es un incremento exclusivamente documental: no crea SQL, rutas, contratos ejecutables ni cobertura de tests.

Antes de este freeze no existía un DEV-ARCH Administrativo en la rama base. El material histórico del DER global describía un diseño más amplio que no coincide con el SQL real; desde este incremento, para configuración prevalecen este freeze, `DEV-ARCH-GEN-001` y la implementación verificable.

## 2. Ownership y clasificación

| Concepto | Clasificación | Decisión |
| --- | --- | --- |
| `parametro_sistema` | núcleo de Administrativo | Definición canónica de cada parámetro. |
| `valor_parametro` | núcleo de Administrativo | Fuente canónica de valores por contexto y vigencia. |
| `tipo_dato_parametro`, `alcance_parametro` | soporte de la definición | Describen tipo y alcance; no son valores. |
| `parametro_opcion` | soporte de la definición | Sólo expresa opciones válidas de un parámetro; no convierte parámetros en catálogos. |
| `historial_parametro` | soporte transversal de trazabilidad | Su estructura actual es incompleta; no prueba auditoría runtime. |
| `configuracion_general` | compatibilidad heredada | No admite nuevas claves ni consumidores; se migrará incrementalmente y su eliminación física queda para una evolución posterior. |
| `configuracion_local` | núcleo de Operativo | Queda fuera de la parametrización administrativa y de #425. |

Los parámetros no son catálogos. `catalogo_maestro`/`item_catalogo` conservan su modelo administrativo propio y no participan en la resolución de configuración.

## 3. Modelo canónico

`parametro_sistema` define identidad y referencia físicamente a `alcance_parametro`; `valor_parametro` conserva el valor y posee campos opcionales `id_sucursal` e `id_instalacion`. Esas columnas prueban capacidad física de contexto, pero no congelan por sí solas su semántica de resolución.

Para futuros parámetros contextuales quedan **NO CONFIRMADOS** el catálogo cerrado de alcances, el significado exacto de `alcance_parametro`, la posibilidad de overrides, la precedencia entre niveles, la obligatoriedad de un valor global base y las reglas de contexto y fallback. En particular, no se define una granularidad máxima de override ni una precedencia general.

Las vigencias de un mismo parámetro y contexto no pueden solaparse. El SQL actual sólo comprueba el orden entre `fecha_desde` y `fecha_hasta`; la exclusión de solapamientos permanece pendiente. La inclusividad de `fecha_hasta` está **NO CONFIRMADA**.

Las claves contractuales del sistema no tendrán alta ni baja dinámica en el primer incremento runtime: se administrarán mediante migraciones versionadas. La exposición administrativa y la sensibilidad ya son metadata física explícita de la definición mediante `exponible_api_administrativa` y `es_sensible`, con política restrictiva por defecto. No deben inferirse del código, tipo, nombre o valor.

La editabilidad continúa pendiente de definición física. La autorización real, el cifrado o secret manager y cualquier modelo adicional de visibilidad siguen **NO CONFIRMADOS**.

## 4. Consumo interdominio y secretos

Otros dominios consumirán parámetros mediante un query service interno del dominio Administrativo; no consultarán directamente las tablas. Ese servicio no está implementado todavía.

Un valor sensible nunca puede exponerse en claro por API, historial, outbox ni logs. El mecanismo de cifrado o secret manager, la autorización y la caché están **NO CONFIRMADOS**. Este freeze fija la prohibición de exposición, no afirma que exista hoy una solución runtime para secretos.

## 5. Freeze específico para #425

#425 se implementará exclusivamente sobre:

- `parametro_sistema`, como definición;
- `valor_parametro`, como valor `GLOBAL` vigente;
- `id_sucursal IS NULL` e `id_instalacion IS NULL`;
- sin `configuracion_general`;
- sin `configuracion_local`;
- sin catálogos.

Permanecen pendientes para #425 y sus incrementos de implementación: patch SQL funcional específico; seeds de las dos claves; constraints de rango 1–31; read; write; versionado; idempotencia; outbox; historial; rollback; query service interno y tests PostgreSQL. Esta lista no declara nombres de endpoints ni comportamiento runtime existente.

Quedan **NO CONFIRMADOS** hasta contar con evidencia: códigos/nombres exactos de las claves, defaults, cifrado/secret manager, autorización, caché, inclusividad de `fecha_hasta`, reactivación o reutilización de claves y taxonomía final de eventos.

## 6. Estado CORE-EF físico de `valor_parametro`

#410 implementó preparación física CORE-EF en `valor_parametro`: `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta` y `op_id_ultima_modificacion`. También implementó triggers de insert/update, versionado físico, integridad para definiciones cuyo alcance se resuelve por código `GLOBAL`, garantía concurrente de un único valor global vigente no eliminado, constraints físicas mínimas de vigencia, migración transaccional e integración en resets DEV/TEST.

Siguen pendientes, sin declararlos implementados: idempotencia HTTP, replay, `If-Match-Version` runtime, compare-and-swap en repository, outbox runtime, historial alineado al valor/contexto, autorización, cifrado o secret manager, no solapamiento temporal general, resolución contextual, overrides, precedencia, fallback y la frontera transaccional de commands de #412 y #425.

## 7. Decisión CORE-EF del freeze

- Endpoints: **NO APLICA**; no se agregan ni modifican rutas.
- Clasificación de command/read-like: **NO APLICA**; el incremento es documental.
- Headers, `If-Match-Version`, idempotencia, outbox, lock, versionado, transacción y rollback ejecutables: **NO APLICA** en este incremento.
- Tests CORE-EF y reset PostgreSQL: **NO APLICA**; no se modifica SQL ni runtime.

El `GET /api/v1/administrativo/configuracion/parametros` de #407/PR #414 se preserva como `QUERY_READLIKE`: inventaría definiciones, pero no lee valores ni ejecuta resolución contextual. #408 documenta este freeze y no agrega endpoints.

## 8. Incremento estructural #409

El patch incremental `patch_parametrizacion_estructural_20260802.sql` materializa
exclusivamente el tipo `ENTERO` y el alcance `GLOBAL`, resueltos siempre por sus
códigos y sin IDs contractuales. Sus nombres y descripciones son datos
estructurales no editables por API. El patch falla y revierte ante nombres o
descripciones incompatibles, variantes de mayúsculas/minúsculas y los sinónimos
`NUMERO`, `GENERAL` o `LOCAL`; su reejecución compatible no duplica filas.

#409 sólo elimina el bloqueo físico de tipo y alcance previo a #425. No crea
`parametro_sistema`, no crea `valor_parametro`, no define semántica contextual y
no implementa ninguna clave, valor, endpoint ni runtime de #425.

### Decisión CORE-EF

- Naturaleza: datos estructurales SQL.
- Endpoints, commands, headers, `If-Match`, idempotencia HTTP, outbox, locks y
  versionado: **NO APLICA**.
- Transacción, rollback, idempotencia SQL y reset reproducible DEV/TEST: aplican
  y forman parte del patch y de sus tests PostgreSQL.

## 9. Incremento SQL #410 — CORE-EF físico de `valor_parametro`

#410 prepara `valor_parametro` como infraestructura reusable del núcleo Administrativo: UID global, versión, timestamps, soft delete y metadata nullable de procedencia/op IDs. Los triggers fijan versión inicial 1, preservan metadata de alta e incrementan exactamente una vez cada `UPDATE` físico. Las filas heredadas no reciben procedencia ni op IDs inventados.

La integridad incorporada se limita a: contexto nulo para definiciones cuyo alcance se resuelve por código `GLOBAL`; fechas estrictamente ordenadas cuando ambas existen; y como máximo un valor global vigente no eliminado por definición. No se impone semántica a alcances no globales ni se resuelven overrides, precedencia, fallback, vigencias futuras o solapamientos temporales.

Es preparación SQL transaccional e idempotente. No existe todavía read de valores (#411), write (#412), runtime ni datos funcionales de #425. No se implementan API, outbox, historial, replay HTTP, CAS ni `If-Match-Version`.

## 10. Incremento #438 — Exposición segura de definiciones administrativas

#438 agrega metadata física mínima a `parametro_sistema` y mantiene separados dos conceptos del núcleo Administrativo: `exponible_api_administrativa` decide si una futura API administrativa puede considerar la definición para lectura de valor, y `es_sensible` clasifica si el valor de la definición no puede exponerse en claro. La política persistida es restrictiva por defecto: `exponible_api_administrativa = false` y `es_sensible = true`; ninguna definición heredada queda exponible automáticamente y cualquier habilitación futura debe realizarse mediante migración versionada explícita, sin inferir por código, nombre, tipo, alcance, descripción o valor.

La constraint `chk_parametro_sistema_exposicion_no_sensible` impide `exponible_api_administrativa AND es_sensible`: una definición sensible no puede quedar marcada como exponible en claro por la API administrativa. #438 no agrega niveles de sensibilidad, enum, catálogo, cifrado, secret manager, redacción parcial ni exposición enmascarada.

#438 no implementa autenticación ni autorización real. Los headers CORE-EF de write no equivalen a autorización, y la metadata física es una política mínima de exposición, no un reemplazo de autenticación. El futuro #411 no debe presentarse como endpoint público y deberá depender de autorización real cuando exista infraestructura verificable.

#438 no implementa el endpoint de #411, no modifica el inventario #407, no agrega commands, no genera outbox, no escribe historial runtime y no toca `valor_parametro`. El futuro #411 sólo podrá devolver un valor cuando `exponible_api_administrativa = true AND es_sensible = false`; para definiciones inexistentes o no exponibles se recomienda responder `404 Not Found` con el error estándar de parámetro no encontrado si el catálogo real lo permite, para no revelar existencia por enumeración. Futuros reads no deben registrar `valor_parametro`, secretos, op IDs, credenciales, payload SQL ni contenido sensible; pueden registrar identificador técnico, código cuando esté permitido, clasificación de error, correlación y stack trace interno.

#412 conserva pendiente la editabilidad, autorización, `If-Match-Version`, idempotencia, outbox e historial. #425 conserva pendientes sus definiciones funcionales, valores, rangos y runtime, y deberá declarar explícitamente `exponible_api_administrativa` y `es_sensible` en su propia migración. #435 no queda resuelto: overrides, precedencia, fallback, contexto, granularidad y vigencia temporal siguen pendientes.
