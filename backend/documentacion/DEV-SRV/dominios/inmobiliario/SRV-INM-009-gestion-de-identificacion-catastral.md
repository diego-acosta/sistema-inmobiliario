# SRV-INM-009 - Gestion de identificacion catastral

## Estado del servicio
- clasificacion: `IMPLEMENTACION SQL INICIAL`
- SQL actual: existe soporte estructural inicial en `inmueble_dato_catastral_registral`, vinculado a `inmueble`
- backend actual: no hay routers, schemas Pydantic, services, repositorios especificos ni tests funcionales de API para esta capacidad

## Modelo implementado
- tabla separada `inmueble_dato_catastral_registral`
- vinculacion obligatoria con `inmueble` mediante `id_inmueble`
- campos catastrales/registrales/fisicos avanzados: nomenclatura catastral, partida inmobiliaria, matricula, folio real, circunscripcion, seccion, chacra, quinta, fraccion, manzana, lote, parcela, subparcela, superficies de titulo/mensura, medidas, situacion posesoria/dominial y organismo de origen
- vigencia/historial mediante `fecha_desde`, `fecha_hasta` y `estado_dato`
- trazabilidad tecnica CORE-EF transversal: `uid_global`, `version_registro`, timestamps, instalacion y `op_id`

## Decisiones de alcance de esta implementacion
- este cambio es solo soporte SQL inicial
- no modifica el contrato vigente de alta, edicion, baja, listado ni detalle de `inmueble`
- no implementa endpoints, schemas Pydantic, services, repositories ni frontend
- no incluye `linderos` en esta primera version
- permite multiples registros por inmueble para habilitar historial; no impone unicidad global sobre nomenclatura, partida o matricula porque puede depender de jurisdiccion, organismo y vigencia
- no agrega restricciones complejas de no solapamiento temporal; queda pendiente definir esa regla funcional antes de implementar comandos de escritura

## Funcionalidad disponible
- estructura SQL para persistir datos catastrales, registrales y fisicos avanzados asociados a inmuebles
- constraints SQL minimas para vigencia, superficies positivas y estados `ACTIVO`, `INACTIVO`, `HISTORICO`
- indices activos por inmueble, nomenclatura catastral, partida inmobiliaria, matricula y estado del dato

## Funcionalidad pendiente
- contrato API de lectura/escritura
- schemas Pydantic
- services y repositories especificos
- comandos CORE-EF write e idempotencia si se incorporan endpoints sincronizables
- tests funcionales de backend/API
- definicion de reglas de unicidad/vigencia/no solapamiento por jurisdiccion u organismo
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
- No se modifico el contrato vigente de `POST /api/v1/inmuebles`.
- Frontend queda pendiente.
- No existe campo `linderos` en SQL, request ni response.

## Decision CORE-EF

- `GET /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales`: `QUERY_READLIKE`; NO APLICA headers write porque no modifica estado.
- `POST /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales`: `COMMAND_WRITE_NEGOCIO`; requiere `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; NO APLICA `If-Match-Version` por ser alta.
- `PUT /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato_catastral_registral}`: `COMMAND_WRITE_NEGOCIO`; requiere headers CORE-EF e `If-Match-Version`; valida `version_registro`.
- `PATCH /api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato_catastral_registral}/baja`: `COMMAND_WRITE_NEGOCIO`; requiere headers CORE-EF e `If-Match-Version`; valida `version_registro` y marca `deleted_at`.
- Idempotencia: NO APLICA persistencia especifica de idempotencia en esta primera API; `op_id` queda trazado en campos CORE-EF.
- Outbox: NO APLICA; no se declara evento de dominio para esta primera API.
- Lock logico: NO APLICA; no hay operaciones incompatibles adicionales definidas.
- Versionado: aplica `version_registro` en update y baja.
- Transaccion/rollback: frontera por metodo repository, con commit de la escritura y rollback ante error o mismatch concurrente.
