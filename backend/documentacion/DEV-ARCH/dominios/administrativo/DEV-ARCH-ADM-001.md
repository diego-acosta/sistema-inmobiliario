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

`parametro_sistema` define identidad, tipo y alcance. `valor_parametro` conserva el valor y su contexto. Los únicos alcances admitidos contractualmente son `GLOBAL`, `SUCURSAL` e `INSTALACION`.

Cuando exista resolución contextual, la precedencia será `INSTALACION > SUCURSAL > GLOBAL`. Esta regla está congelada, pero el query service que la ejecutará permanece pendiente y no se declara implementado.

Las vigencias de un mismo parámetro y contexto no pueden solaparse. El SQL actual sólo comprueba el orden entre `fecha_desde` y `fecha_hasta`; la exclusión de solapamientos permanece pendiente. La inclusividad de `fecha_hasta` está **NO CONFIRMADA**.

Las claves contractuales del sistema no tendrán alta ni baja dinámica en el primer incremento runtime: se administrarán mediante migraciones versionadas. Editabilidad, visibilidad y sensibilidad deben ser metadata explícita de la definición y nunca inferirse del código, tipo, nombre o valor. El SQL actual de `parametro_sistema` todavía no contiene esa metadata: su forma física es pendiente.

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

Permanecen pendientes para #425 y sus incrementos de implementación: patch SQL CORE-EF; seeds de las dos claves; constraints de rango 1–31; read; write; versionado; idempotencia; outbox; historial; rollback; query service interno y tests PostgreSQL. Esta lista no declara nombres de endpoints ni comportamiento runtime existente.

Quedan **NO CONFIRMADOS** hasta contar con evidencia: códigos/nombres exactos de las claves, defaults, cifrado/secret manager, autorización, caché, inclusividad de `fecha_hasta`, reactivación o reutilización de claves y taxonomía final de eventos.

## 6. Deuda física CORE-EF de `valor_parametro`

El SQL real no provee a `valor_parametro` la infraestructura CORE-EF completa. Quedan pendientes, sin declararlos implementados: UID, versión, timestamps, soft delete, metadata de instalación, op IDs, idempotencia, outbox e historial alineado al valor/contexto. También quedan pendientes las restricciones de contexto y de no solapamiento, y la frontera transaccional de futuros commands.

## 7. Decisión CORE-EF del freeze

- Endpoints: **NO APLICA**; no se agregan ni modifican rutas.
- Clasificación de command/read-like: **NO APLICA**; el incremento es documental.
- Headers, `If-Match-Version`, idempotencia, outbox, lock, versionado, transacción y rollback ejecutables: **NO APLICA** en este incremento.
- Tests CORE-EF y reset PostgreSQL: **NO APLICA**; no se modifica SQL ni runtime.

El `GET /api/v1/administrativo/configuracion/parametros` de #407/PR #414 se preserva como `QUERY_READLIKE`: inventaría definiciones, pero no lee valores ni resuelve precedencia. #408 documenta este freeze y no agrega endpoints.
