# AUDITORIA — valor asignado por objeto de venta

## 1. Objetivo

Auditar el modelo vigente de ventas multiobjeto y diseñar, sin modificar implementación, cómo incorporar `valor_asignado` por cada objeto vendido.

El objetivo funcional es conservar `venta.monto_total` como monto total general de la operación y mantener Plan Pago V2 por ese total, agregando una trazabilidad comercial/patrimonial por activo vendido.

## 2. Alcance documental

Este documento es una auditoría documental/técnica del dominio `comercial`.

No modifica:

- código backend;
- SQL / migraciones;
- tests;
- contratos API vigentes.

Debe leerse como diseño pendiente para un PR posterior de implementación.

## 3. Clasificación de dominio

| Concepto | Clasificación | Dominio dueño | Motivo |
| --- | --- | --- | --- |
| `venta` | núcleo del dominio | comercial | entidad principal del ciclo de compraventa. |
| `venta_objeto_inmobiliario` | núcleo del dominio | comercial | representa los activos alcanzados por una venta. |
| `reserva_venta_objeto_inmobiliario` | núcleo del dominio | comercial | representa los activos reservados para una eventual venta. |
| `valor_asignado` por objeto vendido | núcleo del dominio | comercial | distribuye comercial/patrimonialmente el precio de la operación por activo. |
| `plan_pago_venta` / Plan Pago V2 | núcleo comercial con efectos financieros derivados | comercial como regla comercial; financiero como deuda/obligación | el plan comercial se define sobre la venta y sus obligaciones derivadas pertenecen a financiero. |
| reportes por activo | lectura/agregación | comercial o analítico según uso | si agrega/reporta transversalmente debe ser read-only y no redefinir ownership. |

No se propone mover lógica al dominio financiero ni operativo. El valor por objeto es trazabilidad comercial/patrimonial; no divide deuda, pagos, imputaciones ni obligaciones financieras.

## 4. Fuentes revisadas

### 4.1 Arquitectura y documentación

- `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-001-gestion-de-reserva-de-venta.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-002-gestion-de-venta.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/SRV-COM-008-consulta-y-reporte-comercial.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/MODELO-PLANES-PAGO-VENTA-BLOQUES.md`
- `backend/documentacion/DEV-SRV/dominios/comercial/AUDITORIA-MULTI-COMPRADOR-VENTA-COMPLETA.md`
- `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`

### 4.2 SQL / persistencia

- `backend/database/schema_inmobiliaria_20260418.sql`
- `backend/database/patch_reserva_venta_multiobjeto_20260421.sql`
- `backend/database/patch_plan_pago_venta_cronograma_v2_20260514.sql`
- `backend/database/patch_plan_pago_venta_bloques_v2_20260515.sql`
- `backend/database/patch_plan_pago_venta_metodo_plan_por_bloques_v2_20260515.sql`
- `backend/database/patch_plan_pago_venta_bloque_metodo_liquidacion_20260527.sql`
- `backend/database/patch_plan_pago_venta_bloque_indexacion_20260528.sql`

### 4.3 Backend revisado

- `backend/app/api/schemas/comercial.py`
- `backend/app/application/comercial/commands/confirm_venta_directa_completa.py`
- `backend/app/application/comercial/commands/confirm_venta_completa_desde_reserva.py`
- `backend/app/application/comercial/commands/generate_venta_from_reserva_venta.py`
- `backend/app/application/comercial/services/generate_venta_from_reserva_venta_service.py`
- `backend/app/application/comercial/services/define_condiciones_comerciales_venta_service.py`
- `backend/app/application/comercial/services/confirm_venta_directa_completa_service.py`
- `backend/app/application/comercial/services/confirm_venta_completa_desde_reserva_service.py`
- `backend/app/application/comercial/services/get_venta_detalle_integral_service.py`
- `backend/app/application/comercial/services/get_plan_pago_venta_v2_integral_service.py`
- `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
- `backend/app/infrastructure/persistence/repositories/plan_pago_venta_v2_repository.py`

### 4.4 Tests revisados

- `backend/tests/test_ventas_directa_create_tx.py`
- `backend/tests/test_ventas_directa_confirmar_venta_completa.py`
- `backend/tests/test_reservas_venta_generate_venta.py`
- `backend/tests/test_reservas_venta_confirmar_venta_completa.py`
- `backend/tests/test_ventas_definir_condiciones_comerciales.py`
- `backend/tests/test_ventas_get.py`
- `backend/tests/test_ventas_detalle_integral.py`
- `backend/tests/test_plan_pago_venta_v2_consulta_integral.py`

## 5. Auditoría del modelo actual

### 5.1 Persistencia de venta y objetos vendidos

La venta persiste el monto general en `venta.monto_total`.

Los objetos vendidos se persisten en `venta_objeto_inmobiliario`, con:

- `id_venta_objeto`;
- `id_venta`;
- `id_inmueble`;
- `id_unidad_funcional`;
- `precio_asignado`;
- `observaciones`;
- columnas transversales de trazabilidad, versionado y baja lógica.

La tabla incluye `chk_vo_xor`, que exige exactamente uno entre `id_inmueble` e `id_unidad_funcional`.

Conclusión: hoy ya existe una columna equivalente a valor por objeto en venta, llamada `precio_asignado`, pero no está documentada ni tratada con el nombre objetivo `valor_asignado`.

### 5.2 Persistencia de reserva y objetos reservados

La reserva de venta persiste sus objetos en `reserva_venta_objeto_inmobiliario`, con:

- `id_reserva_venta_objeto`;
- `id_reserva_venta`;
- `id_inmueble`;
- `id_unidad_funcional`;
- `observaciones`;
- columnas transversales de trazabilidad, versionado y baja lógica.

La tabla incluye `chk_rvo_xor`, que exige exactamente uno entre `id_inmueble` e `id_unidad_funcional`.

Conclusión: `reserva_venta_objeto_inmobiliario` no tiene `precio_asignado`, `valor_asignado` ni columna equivalente. La reserva captura el conjunto de objetos, pero no su asignación económica por activo.

### 5.3 Venta desde reserva: generación simple

El flujo `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta` materializa una `venta` en estado `borrador` desde una reserva confirmada.

La implementación copia los objetos de la reserva a `venta_objeto_inmobiliario` 1:1 y asigna `precio_asignado = None`.

Conclusión: la generación simple desde reserva no copia ni resuelve valor por objeto porque la reserva no lo contiene. La asignación económica queda pendiente de una definición posterior de condiciones comerciales.

### 5.4 Definición de condiciones comerciales de venta

El endpoint de definición de condiciones comerciales exige un payload `objetos` que representa el conjunto completo vigente de `venta_objeto_inmobiliario`.

La implementación valida:

- la venta existe y está en `borrador`;
- la venta tiene objetos;
- cada objeto informa XOR entre `id_inmueble` e `id_unidad_funcional`;
- el payload tiene la misma cardinalidad y el mismo conjunto de objetos que la venta;
- `precio_asignado > 0`;
- no hay duplicados;
- la suma de `precio_asignado` coincide exactamente con `monto_total`.

Conclusión: para la definición de condiciones comerciales ya existe una regla implementada compatible con el diseño objetivo, usando el nombre vigente `precio_asignado`.

### 5.5 Venta directa completa

El endpoint compuesto de venta directa completa recibe `objetos` en el request principal y cada objeto exige `precio_asignado`.

La validación de repository para venta directa completa verifica:

- al menos un objeto;
- XOR entre inmueble y unidad funcional;
- no duplicados exactos;
- existencia del inmueble o unidad funcional;
- disponibilidad y ausencia de conflictos de ocupación, venta y reserva;
- conflicto jerárquico inmobiliario;
- `precio_asignado` no nulo;
- suma total de precios mayor que cero;
- si `monto_total` viene informado, debe coincidir con la suma de objetos.

Conclusión: la venta directa completa acepta precio por objeto y lo persiste. Sin embargo, hoy `precio_asignado` es obligatorio en el schema del objeto; no existe default documentado para venta directa de un solo objeto sin valor informado.

### 5.6 Venta completa desde reserva

El endpoint compuesto `confirmar-venta-completa` desde reserva genera la venta, define condiciones comerciales, genera Plan Pago V2 y confirma la venta en una única transacción.

En el request, los valores por objeto aparecen dentro de `condiciones_comerciales.objetos`, usando `precio_asignado`.

Conclusión: la venta completa desde reserva no toma valores por objeto desde la reserva. Los completa en el momento de confirmar venta completa, dentro de condiciones comerciales. Esto es consistente con el SQL actual, porque la reserva no persiste valor por objeto.

### 5.7 Consulta integral de venta

La consulta integral comercial incluye objetos y condiciones comerciales. En condiciones comerciales expone los objetos con `precio_asignado`.

Conclusión: la consulta integral ya tiene un lugar natural para mostrar el valor por objeto, aunque con el nombre vigente `precio_asignado`. Un cambio futuro debería definir si se renombra externamente a `valor_asignado`, se agrega alias compatible o se mantiene `precio_asignado` como persistencia heredada/documentada.

### 5.8 Plan Pago V2

Plan Pago V2 usa `monto_total_plan` y estructura el acuerdo en `plan_pago_venta` y `plan_pago_venta_bloque`. No usa `venta_objeto_inmobiliario.precio_asignado` para dividir obligaciones por objeto.

Los endpoints compuestos comparan `condiciones_comerciales.monto_total` contra `plan_pago_v2.monto_total_plan` antes de ejecutar la transacción compuesta.

Conclusión: incorporar `valor_asignado` por objeto no debe dividir Plan Pago V2. Plan Pago V2 debe seguir siendo por el total de la venta.

## 6. Respuestas a las preguntas obligatorias

### 6.1 ¿Dónde se persisten hoy los objetos de una venta?

En `venta_objeto_inmobiliario`, vinculados a `venta.id_venta` mediante `id_venta`.

La reserva usa otra tabla: `reserva_venta_objeto_inmobiliario`, vinculada a `reserva_venta.id_reserva_venta`.

### 6.2 ¿Existe ya valor/precio por objeto?

Sí, para ventas: existe `venta_objeto_inmobiliario.precio_asignado numeric(14,2)`.

No existe una columna llamada `valor_asignado`.

### 6.3 ¿`reserva_venta_objeto` tiene valor asignado o equivalente?

No. `reserva_venta_objeto_inmobiliario` solo registra inmueble o unidad funcional y observaciones. No tiene `precio_asignado`, `valor_asignado` ni equivalente económico.

### 6.4 ¿Venta directa completa acepta precio por objeto?

Sí. El request/command de venta directa completa exige `precio_asignado` por objeto y el repository lo persiste en `venta_objeto_inmobiliario.precio_asignado`.

No implementa el default objetivo de “un solo objeto sin valor asignado defaulta a `monto_total`”, porque el schema actual exige el campo.

### 6.5 ¿Venta desde reserva copia datos por objeto?

Sí, copia `id_inmueble`, `id_unidad_funcional` y `observaciones` desde `reserva_venta_objeto_inmobiliario` hacia `venta_objeto_inmobiliario`.

No copia valores económicos por objeto, porque la reserva no los persiste. En generación simple, `precio_asignado` queda `None`; en confirmación completa desde reserva, el valor por objeto se completa mediante `condiciones_comerciales.objetos`.

### 6.6 ¿Qué impacto tiene en Plan Pago V2?

No debe dividirse Plan Pago V2 por objeto.

Regla objetivo:

- `venta.monto_total` conserva el total comercial de la operación;
- `plan_pago_v2.monto_total_plan` debe seguir coincidiendo con `venta.monto_total` / `condiciones_comerciales.monto_total`;
- `valor_asignado` solo distribuye trazabilidad comercial/patrimonial por activo;
- las obligaciones financieras derivadas se generan por el total del plan y no por cada activo.

### 6.7 ¿Qué validaciones deberían aplicarse?

Validaciones objetivo:

1. Cada objeto debe cumplir XOR: exactamente uno entre `id_inmueble` e `id_unidad_funcional`.
2. No puede repetirse el mismo inmueble o la misma unidad funcional dentro de la venta.
3. No puede venderse un inmueble completo y una unidad funcional contenida en ese mismo inmueble en la misma venta.
4. `valor_asignado > 0`.
5. Si hay un solo objeto y `valor_asignado` no viene, puede defaultar a `monto_total`.
6. Si hay varios objetos, `valor_asignado` es obligatorio en cada objeto.
7. `sum(valor_asignado)` debe coincidir exactamente con `monto_total`.
8. Para ventas paquete, el criterio de asignación puede ser manual, siempre que cumpla suma y positividad.
9. En venta desde reserva, debe definirse si el valor nace en la reserva o se completa al confirmar venta.
10. Plan Pago V2 debe validar coherencia por total, no por objeto.

### 6.8 ¿Qué consultas/reportes se benefician?

Se benefician:

- reporte de ventas por activo;
- trazabilidad patrimonial por inmueble o unidad funcional;
- análisis de rentabilidad por activo;
- análisis de paquetes y composición de precio;
- reportes comerciales por desarrollo, inmueble o unidad funcional;
- soporte documental de boleto/escritura/anexos por objeto;
- cálculo o auditoría de comisiones cuando dependan de objetos específicos;
- modificaciones parciales de una venta multiobjeto;
- conciliación entre venta total y activos transferidos;
- consulta integral de venta con desglose por objeto.

### 6.9 ¿Qué cambios SQL serían necesarios?

Depende de la decisión de naming y del momento en que nace el valor.

#### Opción A — mantener columna vigente y documentar alias semántico

- Mantener `venta_objeto_inmobiliario.precio_asignado` como persistencia física.
- Documentar que `precio_asignado` representa el concepto semántico `valor_asignado`.
- Agregar constraints/checks si se decide endurecer SQL:
  - `precio_asignado > 0` cuando la venta esté en estado que exige condiciones completas;
  - suma por venta no puede resolverse solo con `CHECK` simple, requeriría trigger o validación transaccional de aplicación.

Ventaja: menor impacto SQL.

Riesgo: naming divergente entre diseño (`valor_asignado`) y DB/API (`precio_asignado`).

#### Opción B — renombrar/agregar `valor_asignado` en venta

- Agregar `venta_objeto_inmobiliario.valor_asignado numeric(14,2)` o renombrar `precio_asignado`.
- Migrar datos desde `precio_asignado`.
- Definir compatibilidad API si `precio_asignado` ya es contrato público.
- Actualizar consultas, schemas, repositorios y tests.

Ventaja: alinea nombre físico con concepto objetivo.

Riesgo: mayor impacto y posible ruptura de contratos existentes.

#### Opción C — agregar valor en reserva y copiar a venta

- Agregar `reserva_venta_objeto_inmobiliario.valor_asignado numeric(14,2)` o equivalente.
- Definir si es opcional u obligatorio según cantidad de objetos.
- En conversión `reserva -> venta`, copiar el valor hacia `venta_objeto_inmobiliario`.
- Mantener posibilidad de completar valores al confirmar venta si la reserva no los trae.

Ventaja: permite trazabilidad temprana desde reserva.

Riesgo: obliga a decidir reglas económicas antes de la venta, cuando en algunos procesos la reserva puede ser solo bloqueo/manifestación de interés.

Recomendación inicial: implementar Opción A como transición documental/API controlada si no se requiere cambiar SQL inmediatamente; si negocio exige valor económico desde reserva, diseñar Opción C como cambio SQL explícito posterior.

### 6.10 ¿Qué tests futuros se requieren?

Tests futuros mínimos:

1. Venta directa con un objeto sin `valor_asignado` defaulta a `monto_total`.
2. Venta directa con dos objetos exige `valor_asignado` en cada objeto.
3. Suma distinta entre objetos y `monto_total` falla.
4. `valor_asignado <= 0` falla.
5. Objeto duplicado falla.
6. Inmueble completo + unidad funcional contenida en el mismo inmueble falla.
7. Venta desde reserva copia valores si existen en reserva.
8. Venta desde reserva exige completar valores si hay varios objetos y no existen valores en reserva.
9. Venta desde reserva con un solo objeto puede defaultar a `monto_total` si no hay valor en reserva.
10. Plan Pago V2 sigue usando `monto_total_plan` total y no genera obligaciones por objeto.
11. Consulta integral muestra valor por objeto.
12. Rollback de endpoint compuesto no deja venta/objetos/plan parcial si falla validación de valores por objeto.

## 7. Diseño objetivo propuesto

### 7.1 Principios

- `venta.monto_total` sigue siendo la fuente del total de la operación.
- Cada objeto vendido debe tener `valor_asignado` para trazabilidad por activo.
- `valor_asignado` no reemplaza Plan Pago V2.
- Plan Pago V2 sigue por `monto_total` / `monto_total_plan`.
- La asignación por objeto puede ser manual en ventas paquete.
- No se debe inferir reparto automático para varios objetos salvo decisión futura explícita.

### 7.2 Regla de default para un solo objeto

Si la venta tiene un solo objeto:

- si `valor_asignado` viene informado, debe ser `> 0` e igual a `monto_total`;
- si `valor_asignado` no viene informado, puede defaultar a `monto_total`.

Esta regla no existe actualmente en venta directa completa porque el request exige `precio_asignado`.

### 7.3 Regla para múltiples objetos

Si la venta tiene dos o más objetos:

- `valor_asignado` es obligatorio en cada objeto;
- cada valor debe ser `> 0`;
- la suma exacta debe coincidir con `monto_total`;
- el criterio de asignación es manual, especialmente en ventas paquete.

### 7.4 Regla XOR por objeto

Cada objeto debe cumplir exactamente una de estas formas:

```json
{ "id_inmueble": 10, "id_unidad_funcional": null }
```

```json
{ "id_inmueble": null, "id_unidad_funcional": 20 }
```

No son válidos objetos con ambos IDs nulos ni ambos IDs informados.

### 7.5 Regla de solapamiento jerárquico

No debe permitirse vender en la misma operación:

- un inmueble completo; y
- una unidad funcional contenida en ese mismo inmueble.

Estado auditado: la venta directa completa ya valida conflictos jerárquicos contra ocupación/venta/reserva/disponibilidad; debe confirmarse o extenderse una validación explícita intra-payload para impedir el solapamiento dentro del mismo request.

### 7.6 Reserva: decisión pendiente

Existen dos alternativas válidas, pero debe elegirse explícitamente antes de implementar.

#### Alternativa 1 — valor nace en la reserva

La reserva captura `valor_asignado` por objeto, opcional u obligatorio según reglas de cantidad de objetos.

Al confirmar/generar venta:

- se copia `valor_asignado` desde reserva a venta;
- si falta y hay un solo objeto, puede defaultar a `monto_total`;
- si falta y hay varios objetos, debe exigirse completar valores.

#### Alternativa 2 — valor nace al confirmar venta

La reserva sigue siendo solo selección/bloqueo de objetos.

Al confirmar venta completa:

- `condiciones_comerciales.objetos` debe traer `valor_asignado` por objeto;
- si la reserva tiene un único objeto y no se informa valor, se puede defaultar a `monto_total`;
- si la reserva tiene múltiples objetos, se exige valor por cada objeto.

Recomendación inicial: mantener Alternativa 2 si no hay requerimiento de valoración económica en reservas, porque reduce impacto SQL y mantiene la reserva como bloqueo comercial. Adoptar Alternativa 1 solo si negocio necesita cotización por objeto desde reserva.

## 8. Errores propuestos

| Error | Cuándo aplicar | HTTP sugerido |
| --- | --- | --- |
| `VALOR_ASIGNADO_OBJETO_REQUERIDO` | falta valor en un objeto cuando la regla lo exige. | 400 |
| `VALOR_ASIGNADO_OBJETO_INVALIDO` | valor nulo no permitido, `<= 0`, o no normalizable a monto válido. | 400 |
| `SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA` | la suma de valores por objeto no coincide con `monto_total`. | 400 |
| `OBJETO_VENTA_DUPLICADO` | se repite el mismo inmueble o unidad funcional. | 400 |
| `OBJETO_VENTA_JERARQUIA_SOLAPADA` | se informa un inmueble completo y una unidad funcional contenida en él en la misma venta. | 400 |

Mapeo con errores vigentes observados:

- `INVALID_PRECIO_ASIGNADO` ≈ `VALOR_ASIGNADO_OBJETO_INVALIDO`.
- `INVALID_MONTO_TOTAL` / `MONTO_TOTAL_OBJECTS_MISMATCH` ≈ `SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA` según contexto.
- `DUPLICATE_OBJECT` / `DUPLICATE_VENTA_OBJECTS` ≈ `OBJETO_VENTA_DUPLICADO`.
- `CONFLICTING_JERARQUIA_INMOBILIARIA` no equivale exactamente a `OBJETO_VENTA_JERARQUIA_SOLAPADA`; el nuevo error debería representar solapamiento intra-venta.

## 9. Impacto por endpoint

### 9.1 `POST /api/v1/ventas/directa/confirmar-venta-completa`

Naturaleza CORE-EF: `COMMAND_WRITE_NEGOCIO` en implementación futura; este PR es documental y no modifica endpoint.

Impacto futuro:

- permitir que `valor_asignado` sea opcional solo cuando hay un objeto;
- defaultar a `monto_total` si hay un único objeto sin valor;
- exigir valores para múltiples objetos;
- validar suma contra `condiciones_comerciales.monto_total` y `plan_pago_v2.monto_total_plan`;
- persistir en `venta_objeto_inmobiliario` bajo la decisión SQL/naming elegida.

### 9.2 `POST /api/v1/reservas-venta/{id_reserva_venta}/generar-venta`

Naturaleza CORE-EF: `COMMAND_WRITE_NEGOCIO` en implementación futura; este PR es documental y no modifica endpoint.

Impacto futuro:

- si la reserva persiste valores, copiarlos a venta;
- si no persiste valores, mantener `NULL` hasta condiciones comerciales o aplicar default solo si hay un objeto y `monto_total` está disponible;
- no generar Plan Pago V2 en este endpoint simple.

### 9.3 `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`

Naturaleza CORE-EF: `COMMAND_WRITE_NEGOCIO` en implementación futura; este PR es documental y no modifica endpoint.

Impacto futuro:

- resolver valores desde reserva o desde `condiciones_comerciales.objetos` según decisión;
- exigir completar valores para reservas multiobjeto sin valores previos;
- mantener transacción única para venta, objetos, condiciones, Plan Pago V2, confirmación y efectos asociados;
- asegurar rollback si falla validación de valores por objeto.

### 9.4 `POST /api/v1/ventas/{id_venta}/definir-condiciones-comerciales`

Naturaleza CORE-EF: `COMMAND_WRITE_NEGOCIO` en implementación futura; este PR es documental y no modifica endpoint.

Impacto futuro:

- puede mantener la validación actual de conjunto completo, positividad y suma;
- debería incorporar default para venta de un solo objeto si se permite omitir el valor;
- debería emitir errores nuevos estándar en lugar de errores genéricos heredados.

### 9.5 `GET /api/v1/ventas/{id_venta}/detalle-integral`

Naturaleza CORE-EF: `QUERY_READLIKE` en implementación futura; no requiere headers write.

Impacto futuro:

- mostrar `valor_asignado` por objeto o alias documentado desde `precio_asignado`;
- no recalcular pagos ni obligaciones;
- mantener lectura de Plan Pago V2 por total.

## 10. Impacto en schemas / commands

### 10.1 Naming

Debe decidirse si el contrato público futuro usa:

- `precio_asignado` como nombre vigente; o
- `valor_asignado` como nombre objetivo; o
- ambos durante una transición, con uno como alias heredado.

Recomendación: documentar `valor_asignado` como concepto semántico y decidir compatibilidad API antes de cambiar el schema, porque `precio_asignado` ya aparece en contratos y tests existentes.

### 10.2 Venta directa completa

Cambio futuro posible:

```python
valor_asignado: Decimal | None = None
```

La obligatoriedad no debería depender solo del schema, sino de validación de negocio:

- obligatorio si `len(objetos) > 1`;
- default a `monto_total` si `len(objetos) == 1` y falta.

### 10.3 Venta desde reserva

Si el valor nace en reserva, los schemas de reserva deberían admitirlo.

Si el valor nace al confirmar venta, el schema de confirmación debe transportarlo en condiciones comerciales por objeto.

Estado actual: confirmar venta completa desde reserva ya transporta `precio_asignado` dentro de `condiciones_comerciales.objetos`.

## 11. Impacto en repository comercial

Cambios futuros esperados:

- normalizar `valor_asignado` / `precio_asignado` en un helper común para venta directa, venta desde reserva y definición de condiciones;
- aplicar default de único objeto antes de persistir;
- validar solapamiento jerárquico intra-payload;
- conservar validación de suma exacta contra `monto_total`;
- mantener transacciones compuestas sin persistencias parciales;
- si se agrega valor en reserva, copiarlo en `create_venta_from_reserva`.

No se recomienda duplicar reglas divergentes entre service y repository. La validación semántica debería ser común o al menos consistente entre endpoints.

## 12. Relación con Plan Pago V2

Plan Pago V2 debe seguir así:

```text
venta.monto_total == condiciones_comerciales.monto_total == plan_pago_v2.monto_total_plan
```

`valor_asignado` debe cumplir:

```text
sum(venta_objeto.valor_asignado) == venta.monto_total
```

Pero no debe generar esta relación:

```text
objeto.valor_asignado -> obligación financiera por objeto
```

Las obligaciones financieras permanecen derivadas del Plan Pago V2 total. Si a futuro se requiere trazabilidad financiera por activo, deberá diseñarse explícitamente sin invadir el ownership del dominio financiero.

## 13. Validación contra arquitectura

- Dominio correcto: `comercial`, porque el concepto pertenece al ciclo de compraventa y a sus objetos vendidos.
- No invasión de `personas`: no redefine compradores ni identidad.
- No invasión de `operativo`: no modifica disponibilidad física, ocupación ni entrega.
- No invasión de `financiero`: no divide deuda, pagos ni obligaciones por objeto.
- `analitico`: los reportes agregados deberán ser read-only si se implementan en ese dominio.
- Coherencia con SQL: existe `precio_asignado` en venta; no existe en reserva.
- Coherencia con endpoints existentes: los endpoints de condiciones y venta completa ya transportan precio por objeto; generación simple desde reserva no.
- Coherencia con tests existentes: hay cobertura de precio por objeto en definición de condiciones, venta directa completa, venta desde reserva completa, consulta integral y Plan Pago V2 por total; faltan tests de default y valores en reserva.

## 14. Decisión CORE-EF

Este PR es documental/auditoría. No crea ni modifica endpoints write.

- Clasificación del PR: documentación técnica.
- Endpoint write nuevo/modificado: NO APLICA.
- Headers CORE-EF: NO APLICA, no se modifica router ni contrato write.
- Idempotencia: NO APLICA en este PR documental.
- Outbox: NO APLICA en este PR documental.
- Lock lógico: NO APLICA en este PR documental.
- Versionado: NO APLICA en este PR documental.
- Rollback/transacción: NO APLICA en este PR documental.
- Tests mínimos CORE-EF write: NO APLICA porque no hay endpoint write nuevo/modificado.

Para un PR futuro que modifique endpoints compuestos o definición de condiciones, deberá incluir decisión CORE-EF completa y evidencia en router/service/repository/SQL/tests.

## 15. Plan de implementación futuro recomendado

1. Definir naming contractual: `valor_asignado`, `precio_asignado` o alias transicional.
2. Decidir si el valor nace en reserva o al confirmar venta.
3. Si se requiere valor en reserva, diseñar migración SQL explícita.
4. Incorporar helper común de normalización/validación de valores por objeto.
5. Implementar default para venta de un solo objeto.
6. Implementar validación intra-payload de jerarquía solapada.
7. Actualizar schemas/commands y mapeos repository.
8. Ajustar consulta integral para exponer el nombre acordado.
9. Mantener Plan Pago V2 por total.
10. Agregar tests futuros enumerados en este documento.

## 16. Estado final de auditoría

El sistema ya tiene soporte parcial para valor por objeto en ventas mediante `venta_objeto_inmobiliario.precio_asignado`.

Brechas principales:

- el nombre objetivo `valor_asignado` no existe en SQL/API;
- reserva no persiste valor por objeto;
- venta directa completa no permite omitir valor para un único objeto y defaultar a `monto_total`;
- falta una decisión explícita sobre si el valor nace en reserva o al confirmar venta;
- falta test futuro de solapamiento jerárquico intra-venta y default de único objeto;
- Plan Pago V2 debe permanecer por total y no debe dividirse por objeto.
