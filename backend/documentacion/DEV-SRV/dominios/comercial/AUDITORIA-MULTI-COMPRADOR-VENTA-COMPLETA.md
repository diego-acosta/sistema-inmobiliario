# AUDITORIA-MULTI-COMPRADOR-VENTA-COMPLETA

## 1. Objetivo y alcance

Auditar el soporte actual y definir el diseño técnico objetivo para múltiples compradores en el flujo único de venta completa del dominio `comercial`, antes de implementar UI o cambios funcionales.

Endpoints auditados:

- `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`
- `POST /api/v1/ventas/directa/confirmar-venta-completa`

Alcance de este documento:

- auditoría documental/técnica sobre implementación, SQL, contratos y tests existentes;
- diseño objetivo de backend para múltiples compradores;
- brechas y tests futuros.

Fuera de alcance de este PR:

- cambios de código;
- cambios SQL;
- cambios de tests;
- implementación de UI;
- migración de datos existentes.

## 2. Fuente de verdad y clasificación de conceptos

Documentos arquitectónicos obligatorios revisados:

- `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`
- `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`
- `backend/documentacion/DEV-ARCH/dominios/analitico/DEV-ARCH-ANA-001.md`

Clasificación obligatoria:

| Concepto | Clasificación | Dominio dueño / soporte | Decisión |
|---|---|---|---|
| `venta` | Núcleo del dominio | `comercial` | La venta es la operación comercial central. |
| Comprador en venta | Núcleo del dominio | `comercial` | La semántica de comprador pertenece a la operación comercial. |
| `persona` | Soporte transversal / identidad base | `personas` | `personas` provee identidad, no reglas comerciales. |
| `rol_participacion` | Soporte transversal | Soporte técnico/personas, semántica contextual en dominio origen | No debe usarse como núcleo semántico independiente. |
| `relacion_persona_rol` | Soporte transversal | Soporte técnico/personas, semántica contextual en dominio origen | Vincula persona-contexto; para `tipo_relacion='venta'` la semántica es comercial. |
| `obligacion_financiera` | Soporte financiero persistido | `financiero`, coordinado desde comercial para plan de venta | Comercial no absorbe pagos, mora, saldos ni caja. |
| `obligacion_obligado` | Soporte financiero de responsabilidad | `financiero` | Debe reflejar obligados derivados de compradores de la venta. |
| `plan_pago_venta` / bloques V2 | Núcleo/regla comercial con materialización financiera | `comercial` coordina regla comercial; `financiero` persiste obligación | Debe mantenerse la separación comercial/financiero. |

La solución objetivo no redefine ownership: `comercial` decide quiénes son compradores y sus porcentajes en la venta; `personas` solo valida existencia de persona; `financiero` materializa obligados y obligaciones.

## 3. Evidencia revisada

### 3.1 Arquitectura y documentación

- `DEV-ARCH-PER-001` establece que `persona` es sujeto base y que `rol_participacion` / `relacion_persona_rol` quedan como soporte transversal; la semántica de comprador no pertenece a `personas`.
- `DEV-ARCH-COM-001` establece que `comercial` gobierna la operación de compraventa y la semántica de comprador en ese contexto.
- `SRV-COM-002` documenta que la conversión desde reserva copia objetos y participaciones vigentes de la reserva, y que la integración financiera V1 crea un obligado `COMPRADOR` al 100% para el comprador canónico.
- `DEV-API-COMERCIAL` documenta para Plan Pago V2 que la venta debe tener exactamente un comprador financiero resoluble y que múltiples compradores quedan fuera de alcance.
- `MODELO-PLANES-PAGO-VENTA` documenta la regla V2 inicial: resolver comprador canónico, crear `obligacion_obligado` con `rol_obligado='COMPRADOR'` y `porcentaje_responsabilidad=100.00`; si hay múltiples compradores, la generación debe fallar o quedar pendiente hasta tener regla documentada.

### 3.2 Endpoints, schemas y commands

#### Venta completa desde reserva

- El router expone `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa` con headers CORE-EF e `If-Match-Version`.
- `ConfirmVentaCompletaDesdeReservaRequest` contiene `generar_venta`, `condiciones_comerciales`, `plan_pago_v2` y `confirmacion`; no contiene un campo `compradores`.
- `ConfirmVentaCompletaDesdeReservaCommand` tampoco contiene lista explícita de compradores.
- El servicio `ConfirmVentaCompletaDesdeReservaService` genera la venta desde la reserva, define condiciones, genera Plan Pago V2 y confirma la venta dentro de una transacción.
- La lista de participaciones se toma de la reserva en `GenerateVentaFromReservaVentaService` y se copia a la venta como `relacion_persona_rol` con `tipo_relacion='venta'`.

Conclusión: el endpoint desde reserva no permite editar compradores en su request de confirmación completa; hereda participaciones existentes de la reserva. Si la reserva tiene varios compradores vigentes, la venta podría copiar varias participaciones, pero Plan Pago V2 falla por comprador múltiple no soportado.

#### Venta directa completa

- El router expone `POST /api/v1/ventas/directa/confirmar-venta-completa` con headers CORE-EF, sin `If-Match-Version` porque crea una venta nueva.
- `ConfirmVentaDirectaCompletaRequest` contiene `compradores: list[ConfirmVentaDirectaCompletaCompradorRequest]`.
- `ConfirmVentaDirectaCompletaCommand` contiene `compradores: list[ConfirmVentaDirectaCompletaCompradorInput]`.
- `ConfirmVentaDirectaCompletaCompradorRequest/Input` incluyen `id_persona`, `id_rol_participacion`, fechas y observaciones; no incluyen `porcentaje_responsabilidad`.

Conclusión: el contrato HTTP y el command de venta directa ya tienen forma de lista, pero la validación/repositorio exigen exactamente un comprador y no existe porcentaje.

### 3.3 Repositories y persistencia comercial

#### Venta directa completa

- `ConfirmVentaDirectaCompletaService` llama a `ComercialRepository._create_venta_directa_tx(...)` con `compradores`.
- `_validate_venta_directa_payload(...)` exige `len(compradores_values) == 1`; si no, retorna `INVALID_COMPRADOR_COUNT`.
- Luego valida existencia de persona y que el rol tenga código `COMPRADOR`.
- `_create_venta_directa_tx(...)` persiste solo `compradores_values[0]` en `relacion_persona_rol` con `tipo_relacion='venta'`.

Conclusión: venta directa completa no soporta múltiples compradores en backend aunque el request y command sean listas.

#### Venta completa desde reserva

- `create_reserva_venta(...)` persiste todas las participaciones recibidas en `relacion_persona_rol` con el contexto de reserva.
- `GenerateVentaFromReservaVentaService` arma `participaciones_payload` recorriendo `reserva.get("participaciones", [])` sin restringir cantidad.
- `_generate_venta_from_reserva_tx(...)` recorre todas las participaciones y las inserta en `relacion_persona_rol` con `tipo_relacion='venta'`.

Conclusión: la conversión reserva → venta puede transportar múltiples participaciones a la venta. La brecha aparece al generar Plan Pago V2, que exige comprador único.

### 3.4 Plan Pago V2 y obligaciones

- `GeneratePlanPagoVentaV2PorBloquesService` resuelve un único comprador con `_resolve_comprador(id_venta)` antes de crear obligaciones.
- `_resolve_comprador(...)` consulta `get_compradores_financieros_venta(...)`; si no hay compradores lanza `COMPRADOR_VENTA_NO_RESUELTO`; si hay más de una fila o más de una persona lanza `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO`.
- `_obligacion_payload(...)` recibe un solo `comprador` y setea `id_persona_obligado=comprador["id_persona"]`.
- `PlanPagoVentaV2Repository.create_obligacion_cronograma_v2_if_not_exists(...)` crea una obligación, sus composiciones y llama una sola vez a `_create_obligado(...)`.
- `_create_obligado(...)` inserta un solo `obligacion_obligado` con `porcentaje_responsabilidad = 100.00`.

Conclusión: Plan Pago V2 no soporta múltiples compradores al generar obligaciones. El error `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` es una limitación explícita actual, no un bug aislado.

### 3.5 SQL

- `relacion_persona_rol` soporta múltiples filas por contexto (`tipo_relacion`, `id_relacion`) y no impone unicidad de persona/rol/contexto en el esquema base revisado.
- `obligacion_obligado` tiene PK propia y FK a `obligacion_financiera` y `persona`; no hay unicidad que limite una obligación a un solo obligado.
- `obligacion_obligado.porcentaje_responsabilidad` existe como `numeric(5,2)` y puede representar distribución por obligado, aunque en la tabla base no se observó `NOT NULL` ni `CHECK` específico para ese campo.

Conclusión: el SQL no bloquea múltiples obligados por obligación. La restricción actual es de servicio/repositorio.

### 3.6 Tests existentes

Tests relacionados revisados:

- `backend/tests/test_ventas_directa_confirmar_venta_completa.py`
- `backend/tests/test_ventas_directa_confirmar_venta_completa_contract.py`
- `backend/tests/test_reservas_venta_confirmar_venta_completa.py`
- `backend/tests/test_reservas_venta_confirmar_venta_completa_contract.py`
- `backend/tests/test_plan_pago_venta_v2_bloques_unificado.py`
- `backend/tests/test_plan_pago_venta_v2_anticipo_mas_cuotas.py`
- `backend/tests/test_plan_pago_venta_v2_bloques_preview.py`

Hallazgos:

- Los tests de venta directa completa ejercitan payload con un solo comprador y verifican que se persiste un comprador.
- Los tests de venta completa desde reserva crean reserva con un comprador.
- Los tests de Plan Pago V2 verifican `obligacion_obligado` asociado, pero no cubren varios obligados por obligación.
- Hay cobertura de rollback en venta directa completa, venta completa desde reserva y generación V2 ante fallas.
- Hay cobertura de no regresión para `INTERES_DIRECTO` e `INDEXACION` en preview/generación/venta completa.
- No se encontró cobertura existente que espere éxito con dos compradores ni distribución 50/50.

## 4. Respuestas de estado actual

| Pregunta | Estado actual |
|---|---|
| ¿Venta completa desde reserva permite uno o varios compradores? | Parcial. El endpoint de confirmación no recibe compradores; hereda participaciones de reserva. La conversión puede copiar varias participaciones, pero Plan Pago V2 falla si resuelve más de un comprador. |
| ¿Venta directa completa permite uno o varios compradores? | Solo uno en backend. El request/command son listas, pero repository valida exactamente uno. |
| ¿Dónde está la validación que exige uno solo? | En `ComercialRepository._validate_venta_directa_payload(...)` con `len(compradores_values) != 1 -> INVALID_COMPRADOR_COUNT`; y en `GeneratePlanPagoVentaV2PorBloquesService._resolve_comprador(...)` con `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO`. |
| ¿El schema HTTP permite lista de compradores? | Venta directa: sí, `compradores: list[...]`. Desde reserva: no en el request de confirmación; depende de participaciones de reserva. |
| ¿El command interno permite lista? | Venta directa: sí. Desde reserva: no contiene lista de compradores; usa la reserva como fuente. |
| ¿El repository persiste lista o solo uno? | Venta directa: solo uno. Reserva→venta: recorre y persiste todas las participaciones copiadas de la reserva. |
| ¿Plan Pago V2 soporta múltiples compradores al generar obligaciones? | No. Exige un comprador financiero único y crea un solo obligado al 100%. |
| ¿`obligacion_obligado` soporta múltiples obligados por obligación? | Sí a nivel SQL estructural: tiene PK propia y FK a obligación/persona sin unicidad observada que limite a un solo obligado. Falta regla de suma y validación de porcentajes en servicio. |

## 5. Modelo funcional deseado

Regla objetivo para venta completa:

1. Una `venta` puede tener uno o varios compradores.
2. Cada comprador debe participar en la venta con rol `COMPRADOR`.
3. Cada comprador puede tener `porcentaje_responsabilidad`.
4. Si hay un solo comprador y el porcentaje no se informa, el backend debe defaultar `porcentaje_responsabilidad = 100.00`.
5. Si hay varios compradores, cada porcentaje debe informarse explícitamente y la suma debe ser exactamente `100.00`.
6. No se permiten compradores duplicados por `id_persona` dentro de la misma venta.
7. No se permite comprador sin persona válida existente.
8. No se permite comprador con rol distinto de `COMPRADOR`.
9. No se permite `porcentaje_responsabilidad <= 0` ni mayor a `100.00`.
10. No se permite suma distinta de `100.00`.

Nota de ownership: el porcentaje es una regla comercial/financiera derivada de la venta, no un atributo base de `persona`. Puede persistirse en estructura comercial nueva o en soporte financiero al generar obligados; si se decide persistirlo antes del plan, debe documentarse SQL/API antes de implementar.

## 6. Impacto en Plan Pago V2

Regla objetivo:

- Cada `obligacion_financiera` generada por Plan Pago V2 debe tener un `obligacion_obligado` por cada comprador vigente de la venta.
- Cada obligado debe usar `rol_obligado = 'COMPRADOR'`.
- `porcentaje_responsabilidad` debe copiar el porcentaje definido/resuelto para ese comprador.
- El importe total de la obligación no debe duplicarse por comprador; la obligación conserva su `importe_total` y la responsabilidad se distribuye por `obligacion_obligado.porcentaje_responsabilidad`.
- Si reportes o saldos por persona requieren importe prorrateado, deben calcularlo desde `importe_total * porcentaje_responsabilidad / 100` o persistir composición adicional solo si existe diseño financiero aprobado.
- La generación debe ser idempotente: repetir el mismo request no debe duplicar obligados de obligaciones ya existentes.
- La creación de todos los obligados de una obligación debe ocurrir en la misma transacción que la obligación y sus composiciones.

Brechas actuales:

- `GeneratePlanPagoVentaV2PorBloquesService` resuelve un único comprador.
- `ObligacionCronogramaV2CreatePayload` transporta un solo `id_persona_obligado` y un solo `rol_obligado`.
- `PlanPagoVentaV2Repository._create_obligado(...)` inserta un único obligado al `100.00`.
- `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` bloquea el caso objetivo.

Decisión futura sobre errores:

- Al implementar múltiples compradores, `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` debe quedar obsoleto para Plan Pago V2 por bloques o reservado únicamente para endpoints/planes que sigan documentados como monocomprador.
- `COMPRADOR_VENTA_NO_RESUELTO` debe mantenerse para venta sin comprador resoluble.

## 7. Impacto por endpoint compuesto

### 7.1 `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`

Naturaleza: `COMMAND_WRITE_NEGOCIO`.

Cambios necesarios:

- Request: mantener sin `compradores` si la fuente de verdad seguirá siendo la reserva; o introducir override explícito solo con diseño documentado de cómo modifica participaciones de reserva. Recomendación inicial: no agregar override; confirmar venta completa desde reserva debe usar compradores vigentes de la reserva.
- Command: si no hay override, no requiere lista de compradores; sí debe transportar/resolver internamente compradores con porcentajes antes de Plan Pago V2.
- Service: validar que las participaciones heredadas tengan al menos un `COMPRADOR`, que no estén duplicadas y que sus porcentajes resuelvan a 100%.
- Repository: si el porcentaje no existe en `relacion_persona_rol`, se requiere definir dónde vive el porcentaje. Con SQL actual no hay columna de porcentaje en `relacion_persona_rol`; por lo tanto, multi comprador con porcentajes desde reserva requiere diseño persistente adicional o regla transitoria documentada.
- Plan Pago V2: debe recibir lista de compradores resueltos con porcentaje y generar múltiples `obligacion_obligado`.
- Tests: agregar casos de reserva con dos compradores si aplica, generación de obligados por comprador y rollback si falla la generación.
- Rollback: mantener una única transacción sobre generación de venta, condiciones, plan V2 y confirmación.
- Errores controlados: `COMPRADORES_REQUERIDOS`, `COMPRADOR_DUPLICADO`, `PORCENTAJE_COMPRADOR_INVALIDO`, `PORCENTAJE_COMPRADORES_NO_SUMA_100`, `COMPRADOR_NO_ENCONTRADO`.

Brecha crítica: el modelo actual de reserva/participación no expone porcentaje de responsabilidad; sin definir persistencia o contrato de porcentaje, el soporte multi comprador desde reserva queda incompleto.

### 7.2 `POST /api/v1/ventas/directa/confirmar-venta-completa`

Naturaleza: `COMMAND_WRITE_NEGOCIO`.

Cambios necesarios:

- Request: extender `ConfirmVentaDirectaCompletaCompradorRequest` con `porcentaje_responsabilidad: Decimal | None`.
- Command: extender `ConfirmVentaDirectaCompletaCompradorInput` con `porcentaje_responsabilidad`.
- Service: default `100.00` solo si hay un comprador y no se informó porcentaje; para varios compradores exigir porcentajes explícitos.
- Repository comercial: reemplazar `INVALID_COMPRADOR_COUNT` por validaciones de al menos un comprador, duplicados, persona existente, rol `COMPRADOR` y suma de porcentajes.
- Persistencia comercial: definir dónde guardar el porcentaje de comprador de venta. El SQL actual de `relacion_persona_rol` no tiene `porcentaje_responsabilidad`; no debe inventarse persistencia sin diseño SQL. Opciones futuras: tabla comercial específica de comprador de venta, extensión controlada de relación contextual, o resolución directa a obligados si el porcentaje solo vive en Plan Pago V2.
- Plan Pago V2: generar múltiples obligados según la lista resuelta.
- Tests: agregar happy path 1 comprador, 2 compradores 50/50, duplicados, suma inválida, persona inexistente, porcentaje inválido, rollback.
- Rollback: mantener la transacción compuesta actual.
- Errores controlados: mapear errores de validación a `ErrorResponse` estándar y evitar `detail` crudo.

## 8. Códigos de error propuestos

| Código | Uso esperado | HTTP sugerido |
|---|---|---|
| `COMPRADORES_REQUERIDOS` | La venta no tiene comprador resoluble. Reemplaza o especializa `INVALID_COMPRADOR_COUNT` para lista vacía. | 400 |
| `COMPRADOR_DUPLICADO` | La misma `id_persona` aparece más de una vez como comprador vigente de la venta/request. | 400 |
| `PORCENTAJE_COMPRADOR_INVALIDO` | Porcentaje ausente cuando es obligatorio, `<= 0`, `> 100` o con escala no soportada. | 400 |
| `PORCENTAJE_COMPRADORES_NO_SUMA_100` | La suma normalizada de porcentajes no es `100.00`. | 400 |
| `COMPRADOR_NO_ENCONTRADO` | `id_persona` no existe o está dada de baja. Puede reemplazar `NOT_FOUND_PERSONA` en este flujo compuesto si se quiere semántica comercial. | 404 o 400 según contrato actual |
| `INVALID_ROL_COMPRADOR` | El rol informado/resuelto no tiene código `COMPRADOR`. Ya existe como estado de validación. | 400 |
| `COMPRADOR_VENTA_NO_RESUELTO` | Plan Pago V2 no puede resolver ningún comprador vigente desde la venta. | 400 |
| `COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO` | Debe quedar obsoleto al implementar multi comprador para V2 por bloques, o reservado para planes/endpoints monocomprador explícitos. | 400 mientras siga vigente |

## 9. Tests futuros mínimos

### Venta directa completa

1. Venta directa con un comprador sin porcentaje sigue funcionando y genera `obligacion_obligado` al `100.00`.
2. Venta directa con un comprador con porcentaje `100.00` funciona.
3. Venta directa con dos compradores `50.00/50.00` funciona.
4. Venta directa con compradores duplicados falla con `COMPRADOR_DUPLICADO`.
5. Venta directa con suma de porcentajes `99.99` o `100.01` falla con `PORCENTAJE_COMPRADORES_NO_SUMA_100`.
6. Venta directa con porcentaje `0`, negativo o mayor a `100` falla con `PORCENTAJE_COMPRADOR_INVALIDO`.
7. Venta directa con persona inexistente falla con `COMPRADOR_NO_ENCONTRADO` o código equivalente documentado.
8. Venta directa con rol distinto de `COMPRADOR` falla con `INVALID_ROL_COMPRADOR`.
9. Rollback completo si falla generación de obligaciones después de persistir venta, objetos, compradores y condiciones.
10. No regresión de venta directa simple.

### Venta completa desde reserva

1. Confirmar venta completa desde reserva con un comprador sigue funcionando.
2. Confirmar venta completa desde reserva con múltiples compradores funciona si el modelo de reserva define/resuelve porcentajes.
3. Si la reserva tiene múltiples compradores sin porcentajes y no existe regla de distribución, falla con error controlado.
4. Compradores duplicados heredados de reserva fallan con `COMPRADOR_DUPLICADO`.
5. Rollback completo si falla generación de obligaciones.

### Plan Pago V2

1. Por cada `obligacion_financiera` generada se crea un `obligacion_obligado` por cada comprador.
2. Los porcentajes en `obligacion_obligado` coinciden con los porcentajes de comprador.
3. La suma de `porcentaje_responsabilidad` por obligación es `100.00`.
4. Reintentar el mismo request no duplica obligados ni obligaciones.
5. No regresión de `INTERES_DIRECTO`.
6. No regresión de `INDEXACION`.
7. Rollback si falla la inserción de un obligado después de crear obligación/composición.

## 10. Decisión CORE-EF

Clasificación de endpoints:

- `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`: `COMMAND_WRITE_NEGOCIO`.
- `POST /api/v1/ventas/directa/confirmar-venta-completa`: `COMMAND_WRITE_NEGOCIO`.

Decisión operativa para implementación futura:

- Headers: mantener `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id` usando helper común CORE-EF; desde reserva mantener `If-Match-Version` sobre `reserva_venta` versionada.
- Idempotencia: no declarar idempotencia profunda nueva sin evidencia. Mantener criterios existentes; si se agrega distribución multi comprador, la idempotencia de Plan Pago V2 debe considerar obligaciones y obligados por clave funcional.
- Outbox: no agregar outbox nuevo salvo patrón existente en confirmación de venta.
- Lock lógico: mantener bloqueos/validaciones existentes de disponibilidad, reserva y venta; no introducir lock nuevo sin diseño explícito.
- Versionado: desde reserva usa `version_registro` de `reserva_venta`; venta directa crea entidad nueva y no requiere `If-Match-Version` inicial.
- Rollback/transacción: mantener una única frontera transaccional para venta, objetos, compradores, condiciones, Plan Pago V2 y confirmación.
- ErrorResponse: preservar errores estructurados; no devolver `{"detail": "..."}` para errores de headers ni validaciones de dominio.

## 11. Brechas y decisiones pendientes antes de implementar

1. Definir persistencia del `porcentaje_responsabilidad` de comprador en venta. El SQL actual de `relacion_persona_rol` no tiene columna de porcentaje.
2. Definir si la reserva de venta debe capturar porcentajes o si la distribución se informa solo al confirmar venta completa.
3. Definir si `COMPRADOR_NO_ENCONTRADO` reemplaza `NOT_FOUND_PERSONA` en estos endpoints o si se mantiene el código existente por compatibilidad.
4. Ajustar documentación DEV-API/DEV-SRV de Plan Pago V2 que hoy declara comprador único.
5. Cambiar `GeneratePlanPagoVentaV2PorBloquesService` de comprador único a lista de compradores responsables.
6. Cambiar payload/repository de obligación para crear múltiples `obligacion_obligado` en una misma transacción.
7. Asegurar idempotencia de obligados en obligaciones existentes.
8. Mantener no regresión de `INTERES_DIRECTO`, `INDEXACION` y venta directa simple.

## 12. Conclusión

El soporte multi comprador no está completo hoy:

- venta directa completa expone lista en HTTP/command, pero valida y persiste exactamente un comprador;
- venta completa desde reserva puede copiar múltiples participaciones desde la reserva, pero el endpoint no recibe porcentajes y Plan Pago V2 falla si hay más de un comprador financiero resoluble;
- Plan Pago V2 crea un único obligado `COMPRADOR` al `100.00` por obligación;
- SQL permite múltiples `obligacion_obligado`, pero falta regla de servicio, contrato y persistencia de porcentajes.

La implementación futura debe comenzar por una decisión de modelo para el porcentaje de comprador y luego actualizar request/command/service/repository/tests sin invadir `personas` ni absorber lógica financiera fuera de los límites ya documentados.
