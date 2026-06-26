# SRV-INM-009 - Gestion de identificacion catastral

## Estado del servicio
- clasificacion: `API_BACKEND_Y_UI_INICIAL`
- SQL actual: existe soporte estructural en `inmueble_dato_catastral_registral`, vinculado a `inmueble`
- backend actual: existen routers, schemas Pydantic, service, repository y tests funcionales de API para esta capacidad

## Modelo implementado
- tabla separada `inmueble_dato_catastral_registral`
- vinculacion obligatoria con `inmueble` mediante `id_inmueble`
- campos catastrales/registrales/fisicos avanzados: nomenclatura catastral, nomenclatura madre, partida inmobiliaria, matricula, folio real, circunscripcion, seccion, chacra, quinta, fraccion, manzana, lote, parcela, subparcela, superficies de titulo/mensura, medidas, situacion posesoria/dominial y organismo de origen
- dato catastral/registral principal actual del inmueble; `fecha_desde`, `fecha_hasta` y `estado_dato` se conservan por compatibilidad y son informativos mientras no exista historial formal
- trazabilidad tecnica CORE-EF transversal: `uid_global`, `version_registro`, timestamps, instalacion y `op_id`

## Decisiones de alcance de esta implementacion
- este cambio es solo soporte SQL inicial
- no modifica el contrato vigente de alta, edicion, baja, listado ni detalle de `inmueble`
- no implementa endpoints, schemas Pydantic, services, repositories ni frontend
- no incluye `linderos` en esta primera version
- adopta la decision funcional "Sin historial formal por ahora": cada inmueble opera con un unico dato catastral/registral principal no eliminado
- no elimina columnas existentes ni hace migraciones destructivas
- no implementa cierre automatico de vigencias, consulta por fecha ni historial formal
- no impone unicidad global sobre nomenclatura, partida o matricula porque puede depender de jurisdiccion u organismo

## Funcionalidad disponible
- estructura SQL para persistir datos catastrales, registrales y fisicos avanzados asociados a inmuebles
- constraints SQL minimas para vigencia, superficies positivas y estados `ACTIVO`, `INACTIVO`, `HISTORICO`
- indices activos por inmueble, nomenclatura catastral, partida inmobiliaria, matricula y estado del dato
- indice unico parcial `ux_inmueble_dcr_unico_no_eliminado` sobre `id_inmueble` con condicion `deleted_at IS NULL`, que garantiza atomicamente un unico dato principal no eliminado por inmueble
- politica funcional de alta API: `POST /datos-catastrales-registrales` permite crear solo si el inmueble no tiene un dato catastral/registral no eliminado; si ya existe, debe editarse el existente

## Funcionalidad pendiente
- contrato API de lectura/escritura
- schemas Pydantic
- services y repositories especificos
- comandos CORE-EF write e idempotencia si se incorporan endpoints sincronizables
- tests funcionales de backend/API
- definicion futura de historial formal, reglas de unicidad/vigencia/no solapamiento por jurisdiccion u organismo y consultas por fecha
- UI/frontend de carga y consulta

## Modelo conceptual futuro
- la identificacion catastral sigue siendo una expansion del dominio inmobiliario vinculada al activo `inmueble`
- cuando se implemente en backend debe usar naming canonico nuevo y no reutilizar aliases obsoletos
- cualquier endpoint write futuro debera nacer con decision CORE-EF explicita, headers comunes, versionado, transaccion, idempotencia/outbox/lock si aplican y cobertura de tests minima

## Fuera de alcance
- interpretaciones geograficas o registrales que pertenezcan a otro dominio o integracion externa
- contratos API o schemas de frontend
- `linderos`, excluido deliberadamente de esta version SQL inicial

## Referencias
- [[00-INDICE-INMOBILIARIO]]
- [[RN-INM]]

## Avance backend API inicial

- Ya existe soporte SQL y API backend inicial para `public.inmueble_dato_catastral_registral`.
- La API permite listar, crear, actualizar y dar de baja logica registros no borrados asociados a un `inmueble` existente.
- El endpoint de creacion estandar no crea multiples datos no eliminados para el mismo inmueble: valida previamente y ademas mapea la violacion concurrente del indice `ux_inmueble_dcr_unico_no_eliminado` a `INMUEBLE_DATO_CATASTRAL_YA_EXISTE`, solicitando editar el existente.
- No se modifico el contrato vigente de `POST /api/v1/inmuebles`.
- Frontend permite cargar el dato principal al crear/editar inmueble, editar el existente y mostrar un principal en detalle sin gestion historica.
- No existe campo `linderos` en SQL, request ni response.

## Decision CORE-EF

- `GET /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales`: `QUERY_READLIKE`; NO APLICA headers write porque no modifica estado.
- `POST /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales`: `COMMAND_WRITE_NEGOCIO`; requiere `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; NO APLICA `If-Match-Version` por ser alta; rechaza la creacion si ya existe un dato no eliminado para el inmueble y queda protegido atomicamente por indice unico parcial.
- `PUT /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato_catastral_registral}`: `COMMAND_WRITE_NEGOCIO`; requiere headers CORE-EF e `If-Match-Version`; valida `version_registro`.
- `PATCH /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato_catastral_registral}/baja`: `COMMAND_WRITE_NEGOCIO`; requiere headers CORE-EF e `If-Match-Version`; valida `version_registro` y marca `deleted_at`.
- Idempotencia: NO APLICA persistencia especifica de idempotencia en esta primera API; `op_id` queda trazado en campos CORE-EF.
- Outbox: NO APLICA; no se declara evento de dominio para esta primera API.
- Lock logico: NO APLICA; no hay operaciones incompatibles adicionales definidas.
- Versionado: aplica `version_registro` en update y baja.
- Transaccion/rollback: frontera por metodo repository, con commit de la escritura y rollback ante error o mismatch concurrente.
