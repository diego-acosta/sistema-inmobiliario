# Auditoria de soporte catastral y registral de inmuebles

## 1. Resumen ejecutivo

Este PR es exclusivamente documental. No implementa backend, no modifica SQL, no modifica endpoints, no modifica frontend, no toca Wizard Venta Completa V3, no toca el prototipo de alta de inmueble y no cambia logica de negocio.

La documentacion historica/DER preveia para el activo inmobiliario base atributos de identificacion externa, ubicacion, nomenclatura catastral, medidas, superficie total, linderos, observaciones fisicas y situacion posesoria/dominial. Tambien dejo como pendientes `idSector`, `idManzana` e `idParcela` en el modelo conceptual de terreno/inmueble base. En desarrollo se preveian `ubicacionGeneral` y `datosCatastralesGenerales`.

El schema/API/backend vigente de `inmueble` soporta solo un nucleo acotado: `id_desarrollo`, `codigo_inmueble`, `nombre_inmueble`, `superficie`, `estado_administrativo`, `estado_juridico` y `observaciones`, mas campos transversales CORE-EF/auditoria tecnica (`uid_global`, `version_registro`, timestamps, instalacion y op_id). No se detectaron campos especificos para nomenclatura catastral, lote, manzana, parcela, partida inmobiliaria, matricula, folio real, medidas, linderos, superficie segun titulo/mensura, situacion dominial o situacion posesoria.

La brecha principal es que el alta actual de inmueble puede crear un registro operativo minimo, pero no captura la identidad territorial, catastral, registral y fisica necesaria para una ficha inmobiliaria completa. Integrar el alta actual como definitiva sin decidir este modelo podria producir inmuebles con identificacion incompleta, duplicacion futura de campos, migraciones correctivas y UI que luego deba partir datos ya cargados entre `inmueble` y tablas especializadas.

Clasificacion preliminar del concepto auditado:

- **Nucleo del dominio inmobiliario:** identidad territorial/fisica del inmueble y su relacion con el activo inmobiliario.
- **Soporte transversal:** campos CORE-EF, versionado, vigencia, trazabilidad y baja logica.
- **Compatibilidad heredada:** aliases/documentacion historica como `terreno`, `inmueble_base`, `idSector`, `idManzana`, `idParcela` o naming camelCase del DER previo. No deben convertirse automaticamente en contrato vigente sin migracion/documentacion tecnica.

## 1.1 Implementacion SQL inicial aplicada

Se incorpora una primera estructura SQL separada llamada `inmueble_dato_catastral_registral`, vinculada a `inmueble`, para preparar la persistencia futura de datos catastrales, registrales y fisicos avanzados sin modificar el contrato vigente de alta de inmueble.

Esta implementacion inicial cubre nomenclatura catastral, partida inmobiliaria, matricula, folio real, circunscripcion, seccion, chacra, quinta, fraccion, manzana, lote, parcela, subparcela, superficies segun titulo/mensura, medidas, situacion posesoria/dominial, organismo de origen, vigencia e historial basico.

No incluye `linderos`, excluido deliberadamente de esta primera version. Tampoco implementa endpoints, schemas Pydantic, services, repositories especificos, tests funcionales de API ni cambios de frontend.

## 2. Evidencia documental

### 2.1 DER / documentacion historica

En `backend/documentacion/DER/_tmp_locativo_extract/TRX-DER-001 — DER Dominio Transaccional.txt`, el bloque conceptual `DESARROLLO` incluia `ubicacionGeneral` y `datosCatastralesGenerales`. El mismo documento definia `TERRENO / INMUEBLE_BASE` con `identificacionExterna`, `ubicacion`, `nomenclaturaCatastral`, `medidas`, `superficieTotal`, `linderos`, `observacionesFisicas`, `situacionPosesoriaDominial`, estados fisicos/administrativos/comerciales/locativos/juridicos y pendientes `idSector`, `idManzana`, `idParcela`.

En el modelo relacional preliminar del mismo DER, `DESARROLLO` mantenia `ubicacion_general` y `datos_catastrales_generales`, y `TERRENO` mantenia `identificacion_externa`, `ubicacion`, `nomenclatura_catastral`, `medidas`, `superficie_total`, `linderos`, `observaciones_fisicas`, `situacion_posesoria_dominial`, `id_sector`, `id_manzana`, `id_parcela` y `observaciones`.

En `backend/documentacion/DER/_tmp_locativo_extract/SYS-DER-001 — DER Global Unificado.txt`, existia una tabla historica `terreno` con `nomenclatura_interna`, `partida_inmobiliaria`, `nomenclatura_catastral`, `matricula`, `direccion_referencia`, `superficie_total`, `superficie_util`, `estado_terreno`, `condicion_urbanistica`, `fecha_alta`, `fecha_baja` y `observaciones`. Ese mismo extracto proponia indices sobre `partida_inmobiliaria` y `nomenclatura_catastral`.

### 2.2 DEV-SRV inmobiliario

`backend/documentacion/DEV-SRV/dominios/inmobiliario/SRV-INM-009-gestion-de-identificacion-catastral.md` declara la gestion de identificacion catastral como `NO IMPLEMENTADO`. Explicita que el SQL actual no tiene tablas ni campos catastrales especificos en el nucleo inmobiliario vigente y que el backend actual no tiene routers, services ni tests para esta capacidad. Tambien deja pendientes la definicion de datos catastrales, reglas de vigencia/unicidad, endpoints y cobertura de tests.

`backend/documentacion/DEV-SRV/dominios/inmobiliario/00-INDICE-INMOBILIARIO.md` referencia `SRV-INM-009-gestion-de-identificacion-catastral` como `NO IMPLEMENTADO`. `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/CU-INM.md` lista `CU-INM-040 | Gestion de identificacion catastral | NO IMPLEMENTADO | Sin soporte actual en SQL ni backend`. `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/RN-INM.md` tambien marca `identificacion catastral` como `NO IMPLEMENTADO` y sin tablas ni backend.

### 2.3 DEV-API inmobiliario

`backend/documentacion/DEV-API/dominios/inmobiliario/DEV-API-INM-001.md` documenta que los items de inmueble agregan `direccion` y `ubicacion` como nulos cuando corresponde porque no existen como campos vigentes en `inmueble`. En la seccion `8.4 Identificacion catastral`, el estado actual indica que no hay tablas especificas del nucleo inmobiliario vigente para ese bloque y que no hay router, schema, service ni tests. Por lo tanto, la API vigente no ofrece contrato para datos catastrales/registrales avanzados.

### 2.4 SYS-MAP

`backend/documentacion/SYS-MAP-002.md` advierte sobre decisiones de nomenclatura que corrigen desalineaciones historicas. Para esta auditoria implica que nombres historicos (`terreno`, `inmueble_base`, camelCase) no deben asumirse como nombres finales si el contrato vigente usa `inmueble` y naming canonico snake_case.

### 2.5 Seeds y frontend documental

`backend/database/seed_minimo.sql` y `backend/database/seed_demo_ui.sql` cargan inmuebles demo con el modelo actual; no se detecto carga de partida, matricula, nomenclatura catastral, lote/manzana/parcela ni datos dominiales especificos. `frontend/flet_app/documentacion/AUDITORIA-INMUEBLES-FRONTEND.md` y `frontend/flet_app/documentacion/UX-INMUEBLES.md` describen el alta/listado actual con campos minimos (`codigo_inmueble`, estados, `id_desarrollo`, `nombre_inmueble`, `superficie`, `observaciones`) y no documentan captura catastral/registral.

## 3. Estado actual del backend

### 3.1 Tabla `inmueble` actual

La tabla fisica `public.inmueble` en `backend/database/schema_inmobiliaria_20260418.sql` contiene:

- Identidad tecnica/transversal: `id_inmueble`, `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.
- Relacion inmobiliaria: `id_desarrollo`.
- Datos de negocio minimos: `codigo_inmueble`, `nombre_inmueble`, `superficie`, `estado_administrativo`, `estado_juridico`, `fecha_alta`, `fecha_baja`, `observaciones`.

No contiene `nomenclatura_catastral`, `partida_inmobiliaria`, `matricula`, `folio_real`, `circunscripcion`, `seccion`, `chacra`, `quinta`, `fraccion`, `manzana`, `lote`, `parcela`, `subparcela`, `superficie_titulo`, `superficie_mensura`, `medidas`, `linderos`, `situacion_posesoria` ni `situacion_dominial`.

### 3.2 Schemas Pydantic actuales

`backend/app/api/schemas/inmuebles.py` define `InmuebleCreateRequest` e `InmuebleUpdateRequest` con `id_desarrollo`, `codigo_inmueble`, `nombre_inmueble`, `superficie`, `estado_administrativo`, `estado_juridico` y `observaciones`. `InmuebleDetailData` y `InmuebleListItem` exponen el mismo nucleo; `InmuebleListItem` agrega campos read-like derivados (`nombre`, `descripcion`, `tipo_inmueble`, `direccion`, `ubicacion`, disponibilidad/ocupacion y cantidad de unidades funcionales), pero `direccion` y `ubicacion` no provienen de columnas vigentes de `inmueble`.

No hay schemas Pydantic especificos para datos catastrales, registrales o fisicos avanzados.

### 3.3 Endpoints actuales

`backend/app/api/routers/inmuebles_router.py` expone actualmente, entre otros:

- `POST /api/v1/inmuebles` para crear inmueble minimo con headers CORE-EF obligatorios.
- `GET /api/v1/inmuebles` para listar con filtros actuales (`q`, estados, desarrollo, disponibilidad, ocupacion, servicio, paginacion).
- `PUT /api/v1/inmuebles/{id_inmueble}` para actualizar inmueble minimo con headers CORE-EF e `If-Match-Version`.
- `PATCH /api/v1/inmuebles/{id_inmueble}/baja` para baja logica con headers CORE-EF e `If-Match-Version`.

No se detectaron endpoints para crear/editar/consultar datos catastrales o registrales del inmueble.

### 3.4 Comandos, servicios y repositorios actuales

En `backend/app/application/inmuebles/services/create_inmueble_service.py`, el payload de creacion replica los campos minimos de negocio y agrega trazabilidad CORE-EF. En `backend/app/application/inmuebles/services/update_inmueble_service.py` ocurre lo mismo para actualizacion. El repositorio `backend/app/infrastructure/persistence/repositories/inmueble_repository.py` persiste y consulta esos campos minimos; cuando arma detalle/listado puede devolver `ubicacion` como `None`, coherente con la documentacion API que indica que no existe como columna vigente en `inmueble`.

No se detectaron comandos, services ni metodos de repositorio dedicados a nomenclatura catastral, partida, matricula, lote/manzana/parcela, medidas, linderos o datos dominiales.

## 4. Brecha detectada

| Aspecto | DER/documentacion historica | Schema fisico actual | API/backend actual | Frontend actual | Estado |
| --- | --- | --- | --- | --- | --- |
| Identificacion externa | Prevista en `TERRENO / INMUEBLE_BASE` | No existe en `inmueble` | No existe schema/endpoint | No se captura | Brecha |
| Ubicacion/direccion | Prevista | No existe como columna de `inmueble` | Puede exponerse `ubicacion`/`direccion` nulas en listados/detalles derivados | Se muestra si viene, no se captura en alta actual | Brecha parcial |
| Nomenclatura catastral | Prevista historicamente y en tabla `terreno` historica | No existe | DEV-SRV/DEV-API: no implementado | No se captura | Brecha |
| Partida inmobiliaria | Prevista en `SYS-DER` historico | No existe | No existe | No se captura | Brecha |
| Matricula / folio real | `matricula` prevista en `SYS-DER`; folio real no confirmado en schema vigente | No existe | No existe | No se captura | Brecha / pendiente |
| Lote, manzana, parcela, subparcela | `idSector`, `idManzana`, `idParcela` pendientes; manzana/parcela/lote buscados no soportados | No existe | No existe | No se captura | Brecha / pendiente de decision |
| Circunscripcion, seccion, chacra, quinta, fraccion | No confirmado como contrato vigente | No existe | No existe | No se captura | Pendiente de decision |
| Medidas y linderos | Previstas | No existe | No existe | No se captura | Brecha |
| Superficie total/titulo/mensura | `superficieTotal` prevista; schema actual solo `superficie` | Solo `superficie numeric(14,2)` generica | Solo `superficie` | Solo `superficie` | Brecha semantica |
| Situacion posesoria/dominial | Prevista como `situacionPosesoriaDominial` | No existe | No existe | No se captura | Brecha |
| Historial/vigencia catastral | DEV-SRV lo deja pendiente | No existe | No existe | No existe | Pendiente de decision |
| Separacion catastral vs registral | DEV-SRV exige definicion futura, no implementada | No existe | No existe | No existe | Pendiente de decision |

Datos claramente no soportados hoy: nomenclatura catastral, partida inmobiliaria, matricula, folio real, circunscripcion, seccion catastral, chacra, quinta, fraccion, manzana, lote, parcela, subparcela, medidas, linderos, superficie segun titulo, superficie segun mensura, situacion posesoria, situacion dominial, organismo de origen, vigencia historica de esos datos y estado propio del dato catastral/registral.

## 5. Opciones de modelado

### Opcion A — Campos directos en `inmueble`

Agregar columnas catastrales/registrales directamente a `inmueble`.

Ventajas:

- Modelo simple para altas y consultas basicas.
- Menos joins para listado/ficha simple.
- Menor cantidad inicial de endpoints/schemas.

Desventajas:

- Infla `inmueble` con datos heterogeneos provinciales/municipales/registrales.
- Dificulta historial y vigencia (`fecha_desde`/`fecha_hasta`) si cambia una partida, matricula o nomenclatura.
- Mezcla identidad operativa (`codigo_inmueble`, estados) con identificacion territorial/registral avanzada.
- Puede forzar nullable masivo y campos ambiguos para jurisdicciones distintas.
- Complica multiples nomenclaturas o coexistencia de dato catastral municipal y provincial.

Impacto en API/frontend:

- Requiere ampliar `InmuebleCreateRequest`, `InmuebleUpdateRequest`, detalle/listado y formularios.
- El alta actual deberia crecer significativamente y podria volverse dificil de validar.
- Los filtros por partida/nomenclatura/matricula se acoplarian al endpoint principal de inmuebles.

Cuando convendria:

- Solo si negocio confirma que habra un unico dato vigente, sin historial, sin multiples organismos y sin distincion relevante entre catastro y registro.
- No parece la opcion mas robusta para el alcance solicitado.

### Opcion B — Tabla separada catastral/registral

Crear tablas dedicadas, por ejemplo:

- `inmueble_dato_catastral`
- `inmueble_dato_registral`

O una tabla unificada inicial:

- `inmueble_identificacion_territorial`
- `inmueble_dato_catastral_registral`

Evaluacion:

- **Cardinalidad 1:1:** sirve si se decide un unico dato vigente por inmueble. Permite mantener `inmueble` liviano, pero limita historial.
- **Cardinalidad 1:N:** permite historial, multiples organismos, cambios de nomenclatura, coexistencia de registros municipales/provinciales y carga de datos historicos. Requiere reglas de unicidad para dato vigente.
- **Historial:** favorece `fecha_desde`, `fecha_hasta`, `estado_dato`, `version_registro` y baja logica. Debe definirse si se permite solapamiento de vigencias.
- **Multiples nomenclaturas:** una tabla 1:N permite distinguir origen/organismo y tipo de identificacion.
- **Datos provinciales/municipales:** conviene incluir `organismo_origen` o clasificacion equivalente para no interpretar todas las nomenclaturas igual.
- **Separacion catastral vs registral:** dos tablas separadas expresan mejor el ownership semantico de catastro vs registro; una tabla unificada reduce complejidad inicial pero puede mezclar campos. Si se unifica, debe dejar claros grupos catastrales y registrales.

Ventajas:

- Preserva `inmueble` como nucleo operativo minimo.
- Permite evolucionar sin migrar constantemente el contrato principal.
- Facilita historial, vigencia, multiples fuentes y trazabilidad.
- Alinea con DEV-SRV, que hoy declara identificacion catastral como expansion no implementada.

Desventajas:

- Mayor complejidad SQL/API/repositorio.
- Requiere endpoints o subrecursos nuevos.
- Requiere definir reglas de unicidad, vigencia y versionado antes de implementar.

### Opcion C — Modelo mixto

Mantener en `inmueble` datos minimos operativos y mover datos avanzados a tabla separada.

Posible distribucion:

- En `inmueble`: `codigo_inmueble`, `nombre_inmueble`, `superficie` generica si se conserva, estados, observaciones.
- En tabla separada: nomenclatura, partida, matricula, lote/manzana/parcela, medidas, linderos, superficies de titulo/mensura, situacion posesoria/dominial, organismo, vigencia e historial.

Ventajas:

- No rompe el contrato actual de alta/listado minimo.
- Permite que la ficha integral consuma datos avanzados cuando existan.
- Evita inflar el alta operativa inicial, pero habilita un paso/seccion avanzada.

Desventajas:

- Debe resolver duplicidad semantica entre `inmueble.superficie` y `superficie_titulo`/`superficie_mensura`.
- Requiere UX clara para no presentar `superficie` como dato dominial si solo es una superficie operativa.

## 6. Recomendacion tecnica

Recomendacion preliminar: **Opcion B con tendencia a modelo mixto controlado**. Mantener `inmueble` liviano y crear en un PR tecnico posterior una tabla separada para datos catastrales/registrales. Salvo decision documentada contraria, conviene priorizar tabla separada para evitar inflar `inmueble`, permitir historial/vigencia y soportar multiples fuentes.

Propuesta tentativa no implementada para discusion:

Tabla: `inmueble_dato_catastral_registral`

Campos tentativos:

- `id_dato_catastral_registral`
- `id_inmueble`
- `nomenclatura_catastral`
- `partida_inmobiliaria`
- `matricula`
- `folio_real` (pendiente de confirmacion documental/negocio)
- `circunscripcion`
- `seccion`
- `chacra`
- `quinta`
- `fraccion`
- `manzana`
- `lote`
- `parcela`
- `subparcela`
- `superficie_titulo`
- `superficie_mensura`
- `medidas`
- `linderos`
- `situacion_posesoria`
- `situacion_dominial`
- `organismo_origen`
- `fecha_desde`
- `fecha_hasta`
- `estado_dato`
- `observaciones`
- Campos CORE-EF transversales si corresponde: `uid_global`, `version_registro`, `created_at`, `updated_at`, `deleted_at`, `id_instalacion_origen`, `id_instalacion_ultima_modificacion`, `op_id_alta`, `op_id_ultima_modificacion`.

Decisiones pendientes antes de implementar:

- Tabla unificada vs dos tablas (`inmueble_dato_catastral` e `inmueble_dato_registral`).
- Cardinalidad 1:1 o 1:N.
- Regla de unico dato vigente por inmueble y organismo.
- Si `superficie` actual queda como superficie operativa o se deriva/mapea desde `superficie_mensura` o `superficie_titulo`.
- Catalogos para `estado_dato`, `situacion_posesoria`, `situacion_dominial` y `organismo_origen`.
- Reglas de obligatoriedad por jurisdiccion.

## 7. Impacto en backend futuro

PRs posteriores deberian incluir, no en este PR:

- SQL/migracion o actualizacion controlada de schema completo con tabla(s), indices, constraints, FK a `inmueble`, `deleted_at`, versionado y campos CORE-EF.
- Seeds minimos/demo solo si se define dato demo catastral/registral y sin contaminar datos existentes.
- Schemas Pydantic para request/response de dato catastral/registral.
- Endpoints read/write como subrecurso de inmueble, por ejemplo `GET /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales` y commands de create/update/baja logica. Los nombres exactos quedan pendientes de DEV-API.
- Servicios de aplicacion para crear, listar, obtener vigente, actualizar y dar de baja datos.
- Repositorio con transacciones, locks y validaciones de vigencia/unicidad.
- Tests de headers CORE-EF, happy path, `If-Match-Version`, mismatch real de version, idempotencia si aplica, rollback, outbox si aplica y reglas de vigencia/unicidad.
- Actualizacion de DEV-SRV/DEV-API con contratos reales antes o junto con backend.

## 8. Impacto en frontend futuro

El frontend deberia evolucionar despues de decidir el modelo:

- **Prototipo de alta de inmueble:** agregar una seccion avanzada o paso separado para datos catastrales/registrales solo cuando exista contrato backend. Hasta entonces no integrar el alta actual como definitiva para ficha completa.
- **Listado:** evaluar columnas/filtros por nomenclatura, partida, matricula, lote/manzana/parcela, pero evitar sobrecargar el listado principal si los datos son 1:N/historicos.
- **Ficha integral:** mostrar bloque catastral/registral con dato vigente, historial y fuente/organismo.
- **Edicion:** separar edicion de datos minimos del inmueble de edicion/versionado de datos catastrales/registrales.
- **Busqueda/filtros:** planificar busqueda por `nomenclatura_catastral`, `partida_inmobiliaria`, `matricula`, `manzana`, `lote`, `parcela` y quizas `organismo_origen`, con contrato API explicito.

Recomendacion UX: no presentar el prototipo actual de alta como alta integral definitiva. Es valido como alta minima/operativa, pero no como carga completa inmobiliaria mientras falten datos catastrales, registrales y fisicos avanzados.

## 9. CORE-EF / sincronizacion

Determinacion preliminar para futuro PR tecnico:

- Crear/editar datos catastrales/registrales seria `COMMAND_WRITE_NEGOCIO`, porque modifica identidad territorial/registral del activo inmobiliario.
- Headers para writes sincronizables: aplicar helper comun CORE-EF y exigir `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
- `If-Match-Version`: requerido al modificar o dar de baja una fila existente/versionada.
- Versionado: la tabla nueva deberia tener `version_registro`; cada update incrementa version y valida concurrencia.
- Baja logica: recomendable con `deleted_at` y no borrado fisico.
- Historial/vigencia: recomendable incluir `fecha_desde`/`fecha_hasta` para no perder cambios historicos de partida/nomenclatura/matricula o fuente.
- Idempotencia: pendiente de decision; si es command sincronizable, deberia definirse criterio `mismo op_id + mismo payload` y comportamiento ante payload distinto.
- Outbox: pendiente de decision. Si otros dominios/instalaciones reaccionan a cambios catastrales/registrales, deberia existir evento en la misma transaccion. No declarar cumplimiento sin tabla/evento verificable.
- Lock logico: pendiente de decision; podria bloquearse por `id_inmueble` o por fila de dato vigente durante operaciones incompatibles de edicion/baja.
- Rollback/transaccion: frontera probable en el caso de uso de crear/actualizar dato y registrar version/outbox en una unica transaccion.

Este PR documental no crea endpoints write; por lo tanto no requiere tests CORE-EF de write en este cambio.

## 10. Recomendacion de proximos PRs

- **PR 1:** Auditar soporte catastral y registral de inmuebles. Este PR.
- **PR 2:** Disenar/implementar schema SQL para datos catastrales/registrales, incluyendo decisiones de cardinalidad, vigencia, versionado, unicidad e indices.
- **PR 3:** Implementar backend API read/write con schemas, routers, services, repositorios y tests CORE-EF.
- **PR 4:** Ampliar prototipo de alta de inmueble para capturar datos catastrales/registrales segun contrato backend.
- **PR 5:** Integrar alta completa al listado real/ficha integral, con busquedas/filtros definidos.

## 11. Checklist para proximo PR tecnico

### Archivos a tocar probablemente

- `backend/database/schema_inmobiliaria_20260418.sql` o migracion/schema canonico que corresponda.
- `backend/database/seed_minimo.sql` y `backend/database/seed_demo_ui.sql`, solo si se definen datos demo.
- `backend/app/api/schemas/inmuebles.py` o nuevo modulo de schemas del subrecurso.
- `backend/app/api/routers/inmuebles_router.py` o router dedicado del subrecurso.
- `backend/app/application/inmuebles/commands/**`.
- `backend/app/application/inmuebles/services/**`.
- `backend/app/infrastructure/persistence/repositories/inmueble_repository.py` o repositorio especializado.
- `backend/tests/**` relacionados con inmuebles y CORE-EF.
- `backend/documentacion/DEV-SRV/dominios/inmobiliario/**`.
- `backend/documentacion/DEV-API/dominios/inmobiliario/**`.

### Archivos a no tocar sin necesidad explicita

- Wizard Venta Completa V3.
- Logica de negocio comercial/ventas.
- Dominio financiero.
- Dominio operativo fuera de la relacion estricta con inmueble.
- Prototipo/frontend antes de tener contrato backend si el PR es solo SQL/backend.

### Decisiones pendientes

- Tabla unificada o separacion catastral/registral.
- Cardinalidad 1:1 o 1:N.
- Regla de dato vigente y manejo de historial.
- Obligatoriedad minima para alta de inmueble vs carga posterior.
- Catalogos y validaciones por jurisdiccion.
- Tratamiento de `superficie` actual frente a `superficie_titulo` y `superficie_mensura`.
- Eventos/outbox y consumidores.
- Filtros API requeridos por frontend.

### Pruebas esperadas

- Tests de SQL/constraints si el stack los contempla.
- Tests de schemas Pydantic para payloads validos/invalidos.
- Tests de endpoints read.
- Tests de endpoints write con headers CORE-EF faltantes/invalidos.
- Happy path de create/update/baja.
- `If-Match-Version` faltante/invalido y mismatch real de version.
- Tests de vigencia/unicidad si se implementa historial.
- Tests de rollback si el caso de uso orquesta multiples escrituras.
- Tests de outbox si se declara evento.


## Nota de avance backend

- Ya existe soporte SQL y API backend inicial para datos catastrales/registrales de inmueble.
- Frontend queda pendiente y no se modifica en este avance.
- No se modifico `POST /api/v1/inmuebles`.
- No existe campo `linderos` en el contrato backend inicial.
