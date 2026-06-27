# AUDIT-275 — Issues abiertos de Partes/Personas contra implementación real

## Objetivo

Auditar los issues abiertos vinculados a Partes/Personas/Clientes/Compradores/Frontend contra el estado real del repositorio y contra la decisión vigente de alta contextual de Partes/Personas.

Esta auditoría no implementa cambios funcionales, no retira el botón **Nueva parte** y no modifica lógica de negocio. Su objetivo es separar:

- trabajo viejo ya implementado y cerrable;
- pendientes reales todavía no implementados;
- issues que quedaron conceptualmente desalineados por alta contextual;
- trabajo nuevo que debe tratarse en issues específicos posteriores.

## Decisión base

Se adopta **alta contextual de Partes/Personas**:

- `persona` permanece como maestro único de identidad.
- La UI operativa no debe promover el alta de una persona/parte como fin en sí mismo.
- Toda creación funcional debe originarse desde un contexto: venta, reserva, contrato, locatario, garante, locador, representante, relación entre personas, obligado financiero, usuario vinculado, importación histórica o regularización autorizada.
- Si la persona ya existe, se reutiliza.
- Si no existe, se crea y se vincula al contexto en la misma operación funcional.
- No deben quedar personas nuevas sin vínculo contextual, salvo procesos explícitos de importación histórica o regularización autorizada.

## Validación de arquitectura

- Dominio `personas`: núcleo del sujeto base, identidad, documentación, domicilios, contactos, relaciones entre personas y representación. `rol_participacion` y `relacion_persona_rol` son soporte transversal, no semántica de negocio contextual. `cliente_comprador` es compatibilidad heredada, no núcleo de `personas`.
- Dominio `comercial`: dueño de compraventa, reservas de venta, compradores, cliente en contexto comercial y roles comerciales dentro de operaciones. `personas` provee identidad; `comercial` define la semántica de comprador/cliente.
- Dominio `financiero`: consume personas como obligados o referencias, pero no convierte `persona` en una condición financiera por sí misma.
- Dominio `analitico`: read-only, sin endpoints write ni ownership de semántica primaria.

## Evidencia implementada revisada

### Frontend Flet — Partes/Personas

- Existe listado desktop de **Partes** con navegación, búsqueda, filtros, paginación, acción **Abrir ficha** y botón **Nueva parte** que navega a `persona_create`.
- Existe ruta `persona_create` en el shell y sincronización de navegación bajo la sección **Partes**.
- Existe formulario `PersonaCreateForm` con copy visible de parte, validaciones de alta aislada, armado de payload y llamada a `ApiClient.crear_persona()`.
- Existe helper `persona_alta_helpers.py` para validación y payload del alta.
- Existen tests frontend específicos de alta aislada y copy de partes/personas.

### Backend — Personas

- Existe router de `personas` con endpoints CRUD/consulta del maestro persona y recursos asociados: documentos, contactos, domicilios, relaciones, representación y participaciones.
- Existe schema `PersonaCreateRequest` para alta directa de persona.
- Existen tests backend para crear, listar, obtener, actualizar, bajar y administrar documentos/contactos/domicilios/relaciones/participaciones de personas.

### Comercial / Ventas / Compradores

- Existen comandos, schemas y rutas para reservas, ventas, confirmación de venta completa desde reserva y confirmación directa completa.
- La confirmación directa completa acepta `compradores` por `id_persona`: resuelve compradores existentes, pero no implementa todavía un patrón de resolver/crear persona contextual desde el flujo.
- Plan Pago V2 y financiero ya exigen comprador financiero resoluble asociado a la venta en varios flujos.
- Existen prototipos/frontend de wizard de venta completa y tests backend de venta directa/desde reserva, pero el resolver contextual de comprador/persona no está consolidado como componente reusable.

### Importadores

- Existe infraestructura reusable de importación Excel y un importador implementado para inmuebles/lotes.
- No se encontró importador específico de clientes/personas ni flujo Excel productivo para Partes/Personas.

## Tabla de auditoría

| Issue | Título | Estado real en repo | Clasificación | Evidencia | Acción recomendada |
|---|---|---|---|---|---|
| #8 | UI V1 desktop Flet: shell, navegación y nomenclatura de Partes | Implementado en lo sustancial para shell/navegación/nomenclatura de Partes. Persisten elementos a reencuadrar por alta contextual, especialmente el acceso a alta aislada desde listado. | Implementado + contradictorio parcial con alta contextual | `frontend/flet_app/app/shell.py`, `frontend/flet_app/app/pages/partes_list_page.py`, `frontend/flet_app/tests/test_parte_detail_page.py`, `frontend/flet_app/tests/test_persona_create_form.py` | Cerrar el alcance original si el issue era shell/navegación/nomenclatura. No modificarlo como pendiente. Usar #277 para retirar/reencuadrar alta aislada desde listado. |
| #206 | [Epic] Clientes y partes | Parcial. El maestro persona y la UI de partes existen; documentos/contactos/domicilios existen en backend y ficha de parte muestra detalle, pero la épica como “Clientes y partes” debe reencuadrarse porque cliente/comprador no es núcleo de personas. | Parcial + reencuadrar/reemplazar | `backend/app/api/routers/personas_router.py`, `backend/app/api/schemas/personas.py`, `backend/tests/test_personas_create.py`, `backend/tests/test_persona_contacto_create.py`, `backend/tests/test_persona_documento_create.py`, `backend/tests/test_persona_domicilio_create.py`, `frontend/flet_app/app/pages/parte_detail_page.py` | Reemplazar/reencuadrar con #278 bajo alta contextual. Cerrar subalcances ya implementados mediante issues específicos, no extender la épica vieja. |
| #242 | Clientes/personas: buscador reutilizable para ventas | Parcial. Existe API/frontend para listar/buscar personas y `ApiClient.buscar_personas()` delega en `get_personas()`. No existe componente reusable tipo `ResolverParte` para flujos contextuales de venta. | Parcial + pendiente real contextual | `frontend/flet_app/app/api_client.py`, `frontend/flet_app/app/pages/partes_list_page.py`, `backend/app/api/routers/personas_router.py` | Mantener abierto solo si se reescribe como resolver contextual. Preferible reemplazar por #280 y #281. |
| #243 | Clientes/personas: edición de datos básicos | Implementado en backend para persona; no confirmado como edición frontend completa desde ficha. No debe convertirse en edición de “cliente” como atributo base. | Parcial/implementado backend + reencuadrar UI | `backend/app/api/routers/personas_router.py`, `backend/app/api/schemas/personas.py`, `backend/tests/test_persona_update.py`, `frontend/flet_app/app/pages/parte_detail_page.py` | Cerrar o marcar implementado backend si el alcance era API. Crear/mantener issue frontend específico si falta edición UI, con alta contextual y sin modelar cliente como base. |
| #244 | Clientes/personas: documentos, contactos y domicilios desde frontend | Backend implementado con endpoints y tests para documentos, contactos y domicilios. En frontend la ficha consume detalle integral; no se confirma CRUD frontend completo para esos recursos. | Parcial | `backend/tests/test_persona_documento_create.py`, `backend/tests/test_persona_contacto_create.py`, `backend/tests/test_persona_domicilio_create.py`, `frontend/flet_app/app/pages/parte_detail_page.py` | Mantener abierto si el alcance era frontend CRUD. Separar de cliente contextual; no mezclar con refactor de alta contextual. |
| #245 | Importador Excel: clientes/personas | Pendiente real. Hay infraestructura Excel y un importador de inmuebles, pero no importador productivo de personas/clientes. Además, la nueva decisión exige definir si será importación histórica/regularización autorizada o importación contextual. | Pendiente + reencuadrar | `frontend/flet_app/app/importers/`, `frontend/flet_app/app/importers/inmuebles_excel_importer.py`, `frontend/flet_app/tests/test_inmuebles_excel_importer.py` | Reemplazar/reencuadrar por #279 antes de implementar. No copiar el patrón de alta aislada sin contexto. |
| #246 | Clientes/personas: detección de duplicados y normalización | Pendiente real. Se observan validaciones de formulario y normalización básica de texto en frontend, pero no motor explícito de duplicados/normalización de personas ni tests de deduplicación. | Pendiente | `frontend/flet_app/app/persona_alta_helpers.py`, `backend/tests/test_personas_create.py` | Mantener como pendiente, pero vincularlo al resolver contextual (#280/#281) para evitar crear duplicados desde flujos funcionales. |
| #51 | Diseñar flujo UI de alta guiada de venta completa con Plan Pago V2 | Parcial/prototipo. Existe prototipo de wizard de venta completa y página V3; el paso compradores trabaja con `id_persona`/demo y no con resolver contextual consolidado. | Parcial | `frontend/flet_app/prototypes/venta_completa_wizard_prototype.py`, `frontend/flet_app/app/pages/venta_completa_wizard_v3_page.py`, `frontend/flet_app/app/pages/ventas_page.py` | Mantener abierto si el alcance era diseño/productivización. Reencuadrar compradores con #280/#281. |
| #56 | Implementar alta guiada incremental de venta BORRADOR | Parcial. Hay flujos backend de ventas/reservas y wizard frontend, pero la creación incremental contextual de comprador/persona no aparece completa. | Parcial | `backend/app/api/routers/comercial_router.py`, `backend/tests/test_ventas_directa_create_tx.py`, `frontend/flet_app/app/pages/venta_create_wizard_page.py`, `frontend/flet_app/app/pages/venta_completa_wizard_v3_page.py` | Mantener abierto para venta BORRADOR si falta productivo; no resolverlo creando alta aislada de parte. Coordinar con #281. |
| #69 | Implementar `_create_venta_directa_tx` y validaciones comerciales | Implementado en backend para venta directa transaccional según tests existentes. El alcance actual resuelve compradores por `id_persona`, no alta contextual de persona. | Implementado + nuevo refactor separado | `backend/tests/test_ventas_directa_create_tx.py`, `backend/tests/test_ventas_directa_confirmar_venta_completa.py`, `backend/app/api/routers/comercial_router.py` | Proponer cierre del issue original si su objetivo era la transacción/validaciones. Crear/reforzar #281 para comprador contextual; no reabrir #69 como si no existiera. |
| #207 | [Epic] Ventas e importación comercial | Parcial. Ventas, reservas, confirmaciones y Plan Pago V2 tienen implementación amplia; importación comercial y resolución contextual de compradores siguen pendientes/no confirmadas. | Parcial | `backend/tests/test_ventas_list.py`, `backend/tests/test_ventas_get.py`, `backend/tests/test_reservas_venta_create.py`, `backend/tests/test_plan_pago_venta_v2_bloques_preview.py`, `backend/app/api/routers/comercial_router.py` | Mantener como épica si sigue activa, pero extraer alta contextual de comprador a #281 y no mezclarla con cierre de issues viejos. |
| #208 | [Epic] Pagos y estado de cuenta | Implementado parcialmente/ampliamente para estado de cuenta, obligaciones, pagos y relación persona-financiero. No es un issue de alta de persona; debe consumir personas/obligados ya resueltos contextualmente. | Parcial/implementado según subalcance financiero | `backend/app/api/routers/financiero_router.py`, `backend/tests/test_fin_estado_cuenta_persona.py`, `backend/tests/test_fin_registrar_pago_persona.py`, `backend/tests/test_fin_comercial_financiero_e2e.py` | No mezclar con Partes/Personas. Mantener/cerrar según checklist financiero propio. Coordinar obligado financiero contextual con #283. |

## Hallazgos principales

1. El repositorio ya tiene una implementación concreta de **alta aislada de Parte/Persona** en frontend y backend: formulario, helper, API client, ruta shell y tests. Esa implementación existe y debe registrarse como implementada, aunque ahora choque con la decisión de alta contextual.
2. La decisión nueva no invalida retroactivamente issues viejos que pedían shell, navegación, CRUD o API base de personas. Esos alcances deben cerrarse o marcarse implementados cuando corresponda, y el cambio conceptual debe tratarse en issues nuevos.
3. `persona` está correctamente ubicada como identidad base. La semántica de `cliente`, `comprador`, `locatario`, `garante` u `obligado financiero` no debe moverse al núcleo de personas.
4. El flujo comercial ya usa compradores asociados por `id_persona`, pero falta un patrón de **resolver persona contextual** que permita reutilizar o crear+vincular en una misma operación funcional.
5. El importador Excel de clientes/personas no está implementado. Antes de implementarlo debe definirse si corresponde a importación histórica, regularización autorizada o importación contextual.
6. No se detecta un componente frontend reusable `ResolverParte`; el buscador actual es listado/consulta de personas, no resolución contextual de una operación.

## Issues que deberían cerrarse

- **#8**: cerrar si el alcance era shell/navegación/nomenclatura de Partes. La deuda nueva de alta contextual debe vivir en #277.
- **#69**: cerrar si el alcance era `_create_venta_directa_tx` y validaciones comerciales ya cubiertas por implementación/tests. El comprador contextual corresponde a #281.

## Issues que deberían mantenerse abiertos

- **#244**: mantener si el alcance pendiente es CRUD frontend completo de documentos/contactos/domicilios.
- **#246**: mantener como pendiente real de duplicados/normalización, coordinado con resolver contextual.
- **#51**: mantener si falta productivizar el diseño/flujo completo de venta guiada.
- **#56**: mantener si falta alta guiada incremental de venta BORRADOR productiva.
- **#207**: mantener como épica si continúa agrupando ventas/importación comercial, pero sin absorber issues de alta contextual.
- **#208**: mantener/cerrar por criterios financieros propios; no mezclarlo con Partes/Personas salvo el patrón de obligado financiero contextual.

## Issues que deberían reencuadrarse o reemplazarse

- **#206**: reemplazar por épica reencuadrada bajo alta contextual (#278). El concepto “Clientes y partes” no debe expandir cliente como identidad base.
- **#242**: reemplazar por componente resolver contextual (#280) y aplicación comercial en venta (#281).
- **#243**: separar API/persona ya implementada de edición UI pendiente; no modelar cliente como atributo base.
- **#245**: reemplazar por #279 para decidir destino del importador Excel antes de implementar.

## Issues nuevos recomendados

- **#276** — ADR: Alta contextual de Partes/Personas.
- **#277** — Frontend: retirar alta aislada de Parte desde listado.
- **#278** — Reencuadrar épica Clientes/Partes bajo alta contextual.
- **#279** — Revisar destino del importador Excel de clientes/personas.
- **#280** — Frontend: componente ResolverParte para flujos contextuales.
- **#281** — Comercial: resolver comprador contextual en venta.
- **#282** — Locativo: definir patrón contextual para locatarios, garantes y locadores.
- **#283** — Financiero: definir patrón contextual para obligado financiero.

## Próximo paso recomendado

Después de cerrar #275, el siguiente paso recomendado es trabajar **#276** para congelar formalmente la ADR de alta contextual. Luego debería abordarse **#277** para retirar o bloquear el alta aislada desde el listado sin perder trazabilidad, y **#280/#281** para habilitar el patrón de resolución contextual en ventas.

## Decisión CORE-EF

- Naturaleza del cambio: documentación/auditoría, sin endpoints nuevos ni modificados.
- Clasificación CORE-EF: `QUERY_READLIKE` para la revisión documental; no aplica a runtime.
- Headers write: **NO APLICA**, no se agregan/modifican endpoints write.
- Idempotencia: **NO APLICA**, no hay comando de negocio.
- Outbox: **NO APLICA**, no hay transacción de negocio.
- Lock lógico: **NO APLICA**, no hay entidad bloqueada.
- Versionado: **NO APLICA**, no se modifica entidad versionada.
- Rollback/transacción: **NO APLICA**, no hay frontera transaccional.
- Tests CORE-EF: **NO APLICA**, cambio solo documental.
