# AUD-001 — Auditoría integral documentación / schema / backend

## 1. Alcance

Auditoría de consistencia entre:

- `backend/documentacion`
- `backend/database/schema_inmobiliaria_20260418.sql`
- `backend/app`
- `backend/tests`

La auditoría fue de solo lectura, salvo la creación de este reporte. No se modificó código backend, SQL existente, tests ni documentación funcional previa.

Fuentes revisadas:

- Documentación relevante por dominio: inmobiliario, personas, comercial, locativo, financiero, integración, `DEV-API`, `DEV-SRV`, `CAT-CU`, `DER`, `DECISIONES`.
- Schema SQL: tablas, constraints, índices, triggers y FKs principales.
- Backend: routers, schemas, commands, services y repositories.
- Tests: cobertura por endpoints, transacciones, integraciones y tablas críticas.

Estado de verificación:

- IMPLEMENTADO: existe evidencia en schema/backend/tests.
- DOCUMENTADO: existe en documentación, sin implicar implementación.
- CONCEPTUAL: documentado como diseño o decisión futura.
- NO IMPLEMENTADO: documentado expresamente como pendiente o no existe en backend.
- NO VERIFICADO: no se pudo confirmar con evidencia suficiente en esta auditoría.

## 2. Resumen ejecutivo

| Severidad | Cantidad |
|---|---:|
| CRÍTICO | 3 |
| ALTO | 6 |
| MEDIO | 5 |
| BAJO | 3 |

Conclusión ejecutiva:

- El backend real está más avanzado que parte de la documentación en locativo y comercial.
- `factura_servicio` ya existe en SQL; al momento de la auditoría varias fuentes aún afirmaban ausencia de entidad/tabla formal.
- Financiero tiene schema y documentación funcional amplia, pero no tiene router/service/repository propio materializado.
- La regla SQL documentada para conflicto activo de `reserva_locativa_objeto` no coincide con el soporte físico real: la validación cross-reserva está en aplicación, no en constraint SQL.
- No se detectó que `factura_servicio` genere `relacion_generadora` u `obligacion_financiera` automáticamente.

## 3. Hallazgos críticos

### AUD-CRIT-001

- Severidad: CRÍTICO
- Dominio: inmobiliario / integración financiera
- Archivo(s):
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/documentacion/DEV-SRV/dominios/inmobiliario/SRV-INM-005-gestion-de-servicios-e-infraestructura.md`
  - `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/RN-INM.md`
  - `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/CU-INM.md`
  - `backend/documentacion/DECISIONES/integracion/INT-FIN-002-resolucion-obligado-financiero.md`
- Descripción: `factura_servicio` está implementada como tabla SQL, pero la documentación vigente al momento de la auditoría aún afirmaba ausencia de entidad/tabla formal o que el registro era completamente no implementado.
- Evidencia:
  - SQL: `CREATE TABLE public.factura_servicio` en `schema_inmobiliaria_20260418.sql`.
  - SQL: índices `idx_factura_servicio_*`, unique parcial `ux_factura_servicio_activa_proveedor_numero`, FKs y trigger `trg_biu_factura_servicio_validar_asociacion`.
  - Docs: `SRV-INM-005` afirmaba ausencia de tabla formal.
  - Docs: `RN-INM` marcaba registro de `factura_servicio` como completamente `NO IMPLEMENTADO`.
  - Docs: `CU-INM-047` afirmaba ausencia de entidad.
  - Docs: `INT-FIN-002` dice que `factura_servicio` no existe como tabla formal documentada e implementada.
- Impacto: genera ambigüedad de estado. El concepto ya no es puramente conceptual a nivel de schema, aunque sigue sin API/backend/evento/consumer financiero.
- Recomendación: actualizar documentación para separar estados: `SQL estructural IMPLEMENTADO`, `API/backend NO IMPLEMENTADO`, `evento/consumer financiero NO IMPLEMENTADO`.
- Fix sugerido: corregir `SRV-INM-005`, `RN-INM`, `CU-INM`, `INT-FIN-002` y `DER-FINANCIERO` con estado granular.
- Estado sugerido: PENDIENTE

### AUD-CRIT-002

- Severidad: CRÍTICO
- Dominio: locativo
- Archivo(s):
  - `backend/documentacion/DEV-API/dominios/locativo/DEV-API-LOCATIVO.md`
  - `backend/documentacion/DER/DER-LOCATIVO.md`
  - `backend/documentacion/ROADMAP_MAESTRO_ACTUALIZADO.md`
  - `backend/app/api/routers/locativo_router.py`
  - `backend/app/api/schemas/locativo.py`
  - `backend/app/application/locativo`
  - `backend/app/infrastructure/persistence/repositories/locativo_repository.py`
  - `backend/tests/test_*locativ*.py`, `backend/tests/test_contratos_alquiler_*.py`, `backend/tests/test_solicitudes_alquiler_*.py`
- Descripción: documentación relevante marcaba locativo como pendiente de materialización o sin router/tests, pero existe implementación backend y cobertura de tests.
- Evidencia:
  - `DEV-API-LOCATIVO.md`: antes indicaba carácter pendiente de materialización backend.
  - `DER-LOCATIVO.md`: antes indicaba ausencia de backend locativo propio y tests locativos versionados.
  - `ROADMAP_MAESTRO_ACTUALIZADO.md`: antes indicaba ausencia de router, schemas, services y tests propios.
  - Backend real: `locativo_router.py` expone contratos, condiciones, reservas locativas, solicitudes, entrega y restitución.
  - Tests reales: existen tests para contratos, reservas locativas, solicitudes, entrega, restitución y condiciones económicas.
- Impacto: un lector o agente podría omitir backend real, duplicar diseño o clasificar mal cambios locativos.
- Recomendación: actualizar documentos locativos y roadmap para reflejar implementación real y dejar pendientes solo los subflujos no implementados.
- Fix sugerido: cambiar estado de `DEV-API-LOCATIVO`, `DER-LOCATIVO` y roadmap a “implementado parcial/materializado” con lista exacta de endpoints existentes.
- Estado sugerido: CORREGIDO DOCUMENTALMENTE. Seguimiento pendiente: mantener `DEV-API-LOCATIVO`, `DER-LOCATIVO` y roadmap sincronizados con futuros subflujos locativos.

### AUD-CRIT-003

- Severidad: CRÍTICO
- Dominio: comercial
- Archivo(s):
  - `backend/documentacion/DER/DER-COMERCIAL.md`
  - `backend/app/api/routers/comercial_router.py`
  - `backend/app/api/schemas/comercial.py`
  - `backend/app/application/comercial`
  - `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
  - `backend/tests/test_reservas_venta_*.py`, `backend/tests/test_ventas_*.py`, `backend/tests/test_cesiones_*.py`, `backend/tests/test_escrituraciones_*.py`
- Descripción: `DER-COMERCIAL.md` contenía una afirmación obsoleta indicando que no existía router, schema, service ni repository comercial, aunque el backend comercial existe y está probado.
- Evidencia:
  - `DER-COMERCIAL.md`: antes indicaba “no existe hoy router, schema, service ni repository del dominio Comercial”.
  - Backend real: `comercial_router.py`, schemas, services y repository implementados.
  - Tests reales: reservas de venta, generación de venta, venta multiobjeto, condiciones comerciales, instrumentos, cesiones y escrituraciones.
- Impacto: contradicción documental directa con implementación vigente. Puede inducir decisiones inválidas o duplicación de módulos.
- Recomendación: mantener el bloque corregido del DER comercial y revisarlo ante nuevos subflujos comerciales.
- Fix sugerido: reemplazar la nota histórica por estado backend vigente con implementado real y pendientes reales.
- Estado sugerido: CORREGIDO DOCUMENTALMENTE. Seguimiento pendiente: mantener `DER-COMERCIAL` sincronizado con backend real y distinguir subflujos pendientes.

## 4. Hallazgos altos

### AUD-ALTO-001

- Severidad: ALTO
- Dominio: financiero
- Archivo(s):
  - `backend/documentacion/DEV-API/FINANCIERO/API-FIN-001.yaml`
  - `backend/documentacion/DEV-SRV/dominios/financiero`
  - `backend/app/api/routers`
  - `backend/app/application`
  - `backend/app/infrastructure/persistence/repositories`
- Descripción: existe contrato/documentación financiera y schema financiero, pero no existe router financiero ni services/repositories propios para `relacion_generadora` u `obligacion_financiera`.
- Evidencia:
  - `API-FIN-001.yaml` documenta `/financiero/relaciones-generadoras`.
  - `main.py` incluye routers de health, desarrollos, edificaciones, inmuebles, personas, servicios, comercial y locativo; no incluye router financiero.
  - No se observan módulos `backend/app/application/financiero` ni `repositories/financiero_repository.py`.
- Impacto: endpoint documentado sin backend real. Riesgo de consumo de API inexistente.
- Recomendación: marcar `API-FIN-001` como conceptual/propuesto o implementar router mínimo.
- Fix sugerido: corregir estado documental antes de exponerlo como contrato vigente.
- Estado sugerido: PENDIENTE

### AUD-ALTO-002

- Severidad: ALTO
- Dominio: locativo
- Archivo(s):
  - `backend/documentacion/DECISIONES/locativo/LOC-DEC-002-cartera-reserva-impacto-operativo.md`
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/app/infrastructure/persistence/repositories/locativo_repository.py`
- Descripción: la documentación declara una validación SQL cross-reserva para `reserva_locativa_objeto` mediante `has_conflicting_active_reserva_locativa`, pero el schema no implementa esa función/constraint; la función existe en repository de aplicación.
- Evidencia:
  - Doc: indica “SQL | Índice único parcial implementado: validación a nivel de `has_conflicting_active_reserva_locativa` vía join”.
  - SQL real: solo existen índices únicos parciales por `(id_reserva_locativa, id_inmueble)` y `(id_reserva_locativa, id_unidad_funcional)`.
  - Backend real: `locativo_repository.py` contiene `has_conflicting_active_reserva_locativa`.
- Impacto: la regla crítica no está protegida por DB ante escrituras fuera de la aplicación.
- Recomendación: corregir documentación para decir “validación en aplicación” o implementar trigger/constraint SQL específico en una tarea futura.
- Fix sugerido: abrir backlog para constraint/trigger SQL si se requiere integridad fuera de backend.
- Estado sugerido: PENDIENTE

### AUD-ALTO-003

- Severidad: ALTO
- Dominio: inmobiliario / financiero
- Archivo(s):
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/app`
  - `backend/tests`
  - `backend/documentacion/DEV-SRV/dominios/inmobiliario/SRV-INM-005-gestion-de-servicios-e-infraestructura.md`
- Descripción: `factura_servicio` existe en SQL, pero no existe router, schema Pydantic, service, repository ni tests dedicados.
- Evidencia:
  - SQL: tabla y triggers existen.
  - `rg factura_servicio backend/app backend/tests` no muestra API/backend/tests para el recurso.
  - Docs aún lo tratan como pendiente/no implementado.
- Impacto: estado mixto: estructura lista, circuito funcional no expuesto. Si no se documenta con precisión, puede parecer implementado funcionalmente.
- Recomendación: documentar explícitamente “soporte SQL inicial implementado; API/backend/evento/consumer NO IMPLEMENTADO”.
- Fix sugerido: agregar estado granular en documentación y crear tests SQL cuando se decida validar constraints por suite.
- Estado sugerido: PENDIENTE

### AUD-ALTO-004

- Severidad: ALTO
- Dominio: financiero / integración
- Archivo(s):
  - `backend/documentacion/DER/DER-FINANCIERO.md`
  - `backend/database/schema_inmobiliaria_20260418.sql`
- Descripción: `SERVICIO_TRASLADADO` está documentado como origen conceptual, pero `trg_relacion_generadora_polimorfica()` solo admite `venta` y `contrato_alquiler`.
- Evidencia:
  - SQL: `IF NEW.tipo_origen NOT IN ('venta', 'contrato_alquiler') THEN RAISE EXCEPTION`.
  - Docs: `DER-FINANCIERO` menciona origen conceptual `SERVICIO_TRASLADADO`.
- Impacto: correcto si sigue siendo conceptual, pero debe permanecer marcado como no soportado físicamente en `relacion_generadora`.
- Recomendación: reforzar documentación para evitar que `SERVICIO_TRASLADADO` se interprete como valor SQL válido actual.
- Fix sugerido: agregar nota explícita en `DER-FINANCIERO` y `RN-FIN`: “no admitido por trigger SQL actual”.
- Estado sugerido: PENDIENTE

### AUD-ALTO-005

- Severidad: ALTO
- Dominio: CORE-EF / sincronización
- Archivo(s):
  - `backend/documentacion/CORE-EF/CORE-EF-001-infraestructura-transversal.md`
  - `backend/database/schema_inmobiliaria_20260418.sql`
- Descripción: `factura_servicio` es nueva tabla sincronizable con metadatos CORE-EF, pero no aparece reflejada en la matriz documental CORE-EF de entidades sincronizables.
- Evidencia:
  - SQL: `factura_servicio` incluye `uid_global`, `version_registro`, timestamps, instalación y `op_id`.
  - Docs CORE-EF contienen matriz de entidades sincronizables, pero no se verificó entrada para `factura_servicio`.
- Impacto: omisión documental sobre una entidad que ya sigue el patrón técnico.
- Recomendación: agregar `factura_servicio` a matriz CORE-EF con estado “SQL implementado; API/evento pendiente”.
- Fix sugerido: actualizar CORE-EF en una tarea documental.
- Estado sugerido: PENDIENTE

### AUD-ALTO-006

- Severidad: ALTO
- Dominio: financiero
- Archivo(s):
  - `backend/documentacion/DEV-SRV/dominios/financiero`
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/app`
  - `backend/tests`
- Descripción: reglas financieras están muy desarrolladas documentalmente y el schema tiene tablas financieras, pero no hay capa de aplicación financiera propia ni tests de endpoints financieros.
- Evidencia:
  - SQL: `relacion_generadora`, `obligacion_financiera`, `composicion_obligacion`, `obligacion_obligado`, `movimiento_financiero`, `aplicacion_financiera`.
  - Backend: no hay router financiero ni application/repository financiero.
  - Tests: no hay tests de endpoints financieros; hay tests que verifican que comercial no crea obligaciones en ciertos flujos.
- Impacto: riesgo de asumir que el motor financiero está expuesto operativamente.
- Recomendación: marcar capa financiera como “schema implementado; backend API NO IMPLEMENTADO” o planificar implementación.
- Fix sugerido: crear estado documental por subcapa: SQL, API, services, consumers, tests.
- Estado sugerido: PENDIENTE

## 5. Hallazgos medios

### AUD-MED-001

- Severidad: MEDIO
- Dominio: inmobiliario
- Archivo(s):
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/tests`
- Descripción: no hay tests dedicados para constraints/triggers de `factura_servicio`.
- Evidencia:
  - No se encontraron tests con `factura_servicio`.
  - SQL contiene constraints de XOR, importe, fechas, unicidad activa y trigger de asociación servicio-objeto.
- Impacto: regresiones en integridad SQL podrían pasar sin cobertura específica.
- Recomendación: cuando se habilite la tabla en suite, agregar tests SQL o de repository para constraints.
- Fix sugerido: tests de inserción válida, XOR inválido, servicio no asociado, duplicado activo y fechas inválidas.
- Estado sugerido: PENDIENTE

### AUD-MED-002

- Severidad: MEDIO
- Dominio: integración / outbox
- Archivo(s):
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/app/infrastructure/persistence/repositories/outbox_repository.py`
  - `backend/app/application`
- Descripción: `factura_servicio_registrada` está documentado como evento pendiente y SQL lo menciona en comentario, pero no existe contrato de evento, producer ni consumer.
- Evidencia:
  - SQL: comentario indica evento pendiente y sin patrón SQL genérico.
  - App: outbox existe para otros flujos, no para `factura_servicio`.
- Impacto: correcto como pendiente, pero debe permanecer fuera de contratos implementados.
- Recomendación: mantenerlo como `CONCEPTUAL / NO IMPLEMENTADO` hasta definir contrato.
- Fix sugerido: crear decisión INT/EVT específica antes de implementar producer.
- Estado sugerido: PENDIENTE

### AUD-MED-003

- Severidad: MEDIO
- Dominio: comercial
- Archivo(s):
  - `backend/documentacion/DER/DER-COMERCIAL.md`
  - `backend/database/schema_inmobiliaria_20260418.sql`
  - `backend/app/infrastructure/persistence/repositories/comercial_repository.py`
- Descripción: el DER comercial mezclaba afirmaciones actuales con notas históricas; algunas contradecían el estado real.
- Evidencia:
  - El documento iniciaba declarando backend real como fuente, pero más adelante afirmaba que no existía backend comercial.
- Impacto: no rompe implementación, pero reduce confiabilidad del documento.
- Recomendación: separar “estado histórico” de “estado vigente”.
- Fix sugerido: sección “Notas obsoletas reemplazadas” o limpieza directa.
- Estado sugerido: CORREGIDO DOCUMENTALMENTE. Seguimiento pendiente: mantener separadas las notas históricas del estado backend vigente.

### AUD-MED-004

- Severidad: MEDIO
- Dominio: locativo
- Archivo(s):
  - `backend/documentacion/DEV-API/dominios/locativo/DEV-API-LOCATIVO.md`
  - `backend/app/api/routers/locativo_router.py`
- Descripción: el contrato locativo documentado como “v1 mínimo” no refleja todo el surface real actual: solicitudes, reservas, generación de contrato, entrega y restitución están implementadas.
- Evidencia:
  - Router real expone `solicitudes-alquiler`, `reservas-locativas`, `generar-contrato`, `entregar`, `restituir`.
  - Documento se presentaba como pendiente de materialización y con alcance mínimo.
- Impacto: clientes pueden desconocer endpoints existentes.
- Recomendación: actualizar DEV-API locativo como contrato vigente o crear anexo de endpoints implementados.
- Fix sugerido: sincronizar DEV-API con router real.
- Estado sugerido: CORREGIDO DOCUMENTALMENTE. Seguimiento pendiente: revisar endpoints/subflujos locativos nuevos en futuras auditorias.

### AUD-MED-005

- Severidad: MEDIO
- Dominio: tests / cobertura
- Archivo(s):
  - `backend/tests`
  - `backend/app/api/routers`
- Descripción: la cobertura de tests es amplia para personas, inmobiliario, comercial y locativo, pero no hay matriz documental de endpoint vs test mantenida automáticamente.
- Evidencia:
  - Existen múltiples tests por dominio, pero la trazabilidad endpoint-test está dispersa por nombre de archivo y no por reporte.
- Impacto: dificultad para detectar drift documental de forma temprana.
- Recomendación: mantener una matriz de cobertura por endpoint en auditorías o generar reporte automático.
- Fix sugerido: script de solo lectura que extraiga rutas y tests asociados por patrón.
- Estado sugerido: PENDIENTE

## 6. Hallazgos bajos

### AUD-BAJO-001

- Severidad: BAJO
- Dominio: documentación
- Archivo(s):
  - `backend/documentacion/DEV-API/dominios/locativo/DEV-API-LOCATIVO.md`
- Descripción: hay caracteres con mojibake en texto visible (`gestiÃ³n`, `explÃ­citamente`).
- Evidencia: bloque “Quedan explícitamente fuera de v1”.
- Impacto: legibilidad documental.
- Recomendación: normalizar encoding del documento.
- Fix sugerido: corrección textual sin cambio funcional.
- Estado sugerido: PENDIENTE

### AUD-BAJO-002

- Severidad: BAJO
- Dominio: documentación / roadmap
- Archivo(s):
  - `backend/documentacion/ROADMAP_MAESTRO_ACTUALIZADO.md`
- Descripción: roadmap mezcla estado de implementación antiguo con estado actual.
- Evidencia: locativo figuraba sin routers/tests pese a implementación real.
- Impacto: planificación desactualizada.
- Recomendación: actualizar después de corregir documentos de dominio.
- Fix sugerido: usar resultado de esta auditoría como input.
- Estado sugerido: PENDIENTE

### AUD-BAJO-003

- Severidad: BAJO
- Dominio: documentación / naming
- Archivo(s):
  - `backend/documentacion/DEV-SRV/dominios/inmobiliario/catalogos/RN-INM.md`
- Descripción: se mantiene la frase “terreno/inmueble” para `factura_servicio`, pero el schema/backend canónico usa `inmueble`.
- Evidencia: `RN-INM` menciona “terreno/inmueble”; SQL real usa `id_inmueble`.
- Impacto: menor, porque aclara que backend vigente usa `inmueble`.
- Recomendación: eliminar “terreno” salvo como referencia histórica.
- Fix sugerido: reemplazar por “inmueble o unidad funcional”.
- Estado sugerido: PENDIENTE

## 7. Matriz dominio vs estado

| Dominio | Documentación | Schema | Backend | Tests | Estado |
|---|---|---|---|---|---|
| Personas | Alta, alineada en general | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | OK con auditoría puntual pendiente |
| Inmobiliario | Alta, con drift en `factura_servicio` | IMPLEMENTADO + `factura_servicio` SQL | IMPLEMENTADO salvo `factura_servicio` | IMPLEMENTADO salvo `factura_servicio` | DESAJUSTE PARCIAL |
| Comercial | Alta, DER corregido documentalmente | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | CORREGIDO DOCUMENTALMENTE |
| Locativo | Desactualizada en DEV-API/DER/roadmap | IMPLEMENTADO parcial/amplio | IMPLEMENTADO | IMPLEMENTADO | DESAJUSTE DOCUMENTAL CRÍTICO |
| Financiero | Alta funcional, estado físico/API difuso | IMPLEMENTADO SQL | NO IMPLEMENTADO como API propia | NO IMPLEMENTADO como endpoints | DESAJUSTE API/DOC |
| Integración | Decisiones existentes | outbox/inbox IMPLEMENTADO | Producers/consumers parciales | Tests parciales | PARCIAL |
| Documental | Documentado amplio | IMPLEMENTADO SQL | NO VERIFICADO como API propia | NO VERIFICADO | PARCIAL |
| Operativo | Documentado | sucursal/instalacion SQL | NO VERIFICADO como API propia | NO VERIFICADO | PARCIAL |
| Técnico/sincronización | CORE-EF/outbox documentado | IMPLEMENTADO parcial | IMPLEMENTADO parcial | IMPLEMENTADO parcial | PARCIAL |
| Analítico | Conceptual | NO VERIFICADO | NO IMPLEMENTADO | NO VERIFICADO | PENDIENTE |

## 8. Auditoría de endpoints

| Endpoint documentado | Router real | Schema request | Service | Tests | Estado |
|---|---|---|---|---|---|
| `POST /api/v1/personas` | `personas_router.py` | `personas.py` | `create_persona_service.py` | `test_personas_create.py` | IMPLEMENTADO |
| `POST /api/v1/desarrollos` | `desarrollos_router.py` | `desarrollos.py` | `create_desarrollo_service.py` | `test_desarrollos_create.py` | IMPLEMENTADO |
| `POST /api/v1/inmuebles` | `inmuebles_router.py` | `inmuebles.py` | `create_inmueble_service.py` | `test_inmuebles_create.py` | IMPLEMENTADO |
| `POST /api/v1/servicios` | `servicios_router.py` | `servicios.py` | `create_servicio_service.py` | `test_servicios_create.py` | IMPLEMENTADO |
| `POST /api/v1/reservas-venta` | `comercial_router.py` | `comercial.py` | `create_reserva_venta_service.py` | `test_reservas_venta_create.py` | IMPLEMENTADO |
| `POST /api/v1/reservas-venta/{id}/generar-venta` | `comercial_router.py` | `comercial.py` | `generate_venta_from_reserva_venta_service.py` | `test_reservas_venta_generate_venta.py` | IMPLEMENTADO |
| `PATCH /api/v1/ventas/{id}/confirmar` | `comercial_router.py` | `comercial.py` | `confirm_venta_service.py` | `test_ventas_confirm.py` | IMPLEMENTADO |
| `POST /api/v1/contratos-alquiler` | `locativo_router.py` | `locativo.py` | `create_contrato_alquiler_service.py` | `test_contratos_alquiler_create.py` | IMPLEMENTADO, DOC DESACTUALIZADA |
| `POST /api/v1/reservas-locativas` | `locativo_router.py` | `locativo.py` | `create_reserva_locativa_service.py` | `test_reservas_locativas_create.py` | IMPLEMENTADO, DOC DESACTUALIZADA |
| `POST /api/v1/solicitudes-alquiler` | `locativo_router.py` | `locativo.py` | `create_solicitud_alquiler_service.py` | `test_solicitudes_alquiler_create.py` | IMPLEMENTADO, DOC DESACTUALIZADA |
| `POST /api/v1/contratos-alquiler/{id}/entregar` | `locativo_router.py` | `locativo.py` | `registrar_entrega_locativa_service.py` | `test_contratos_alquiler_entregar.py` | IMPLEMENTADO |
| `POST /api/v1/contratos-alquiler/{id}/restituir` | `locativo_router.py` | `locativo.py` | `registrar_restitucion_locativa_service.py` | tests de restitución/integración | IMPLEMENTADO |
| `/financiero/relaciones-generadoras` | No existe router financiero | No verificado | No existe service financiero | No verificado | DOCUMENTADO / NO IMPLEMENTADO |
| `factura_servicio` API | No existe endpoint | No existe schema Pydantic | No existe service/repository | No existen tests | SQL IMPLEMENTADO / API NO IMPLEMENTADA |

## 9. Auditoría de tablas críticas

| Tabla | Documentada | Existe en SQL | Usada en backend | Tests | Estado |
|---|---|---|---|---|---|
| `persona` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `persona_documento` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `persona_domicilio` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `inmueble` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `unidad_funcional` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `servicio` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `inmueble_servicio` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `unidad_funcional_servicio` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `factura_servicio` | Sí, pero desactualizada | Sí | No | No | SQL IMPLEMENTADO / API NO IMPLEMENTADA |
| `reserva_venta` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `venta` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `venta_objeto_inmobiliario` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `reserva_venta_objeto_inmobiliario` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `solicitud_alquiler` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `reserva_locativa` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `reserva_locativa_objeto` | Sí | Sí | Sí | Sí | IMPLEMENTADO, regla SQL documentada no coincide |
| `contrato_alquiler` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `contrato_objeto_locativo` | Sí | Sí | Sí | Sí | IMPLEMENTADO |
| `relacion_generadora` | Sí | Sí | No como API propia | Tests indirectos | SQL IMPLEMENTADO / API NO IMPLEMENTADA |
| `obligacion_financiera` | Sí | Sí | No como API propia | Tests indirectos de no creación | SQL IMPLEMENTADO / API NO IMPLEMENTADA |
| `obligacion_obligado` | Sí | Sí | No verificado | No verificado | SQL IMPLEMENTADO |
| `composicion_obligacion` | Sí | Sí | No verificado | No verificado | SQL IMPLEMENTADO |
| `movimiento_financiero` | Sí | Sí | No verificado | No verificado | SQL IMPLEMENTADO |
| `aplicacion_financiera` | Sí | Sí | No verificado | No verificado | SQL IMPLEMENTADO |
| `outbox_event` | Sí | Sí | Sí | Sí | IMPLEMENTADO |

## 10. Auditoría de cambios recientes

### `factura_servicio`

- Existe en SQL.
- Tiene CORE-EF, constraints, índices, FKs y trigger de asociación.
- No tiene router/schema/service/repository/tests.
- No genera obligación financiera.
- No emite outbox real desde SQL ni backend.
- Documentación debe pasar de “ausencia de entidad/tabla” a “SQL estructural implementado; circuito funcional pendiente”.

### `SERVICIO_TRASLADADO`

- Documentado como tipo_origen conceptual.
- No está admitido por `trg_relacion_generadora_polimorfica()`.
- No existe consumer financiero.
- Estado correcto sugerido: CONCEPTUAL / NO IMPLEMENTADO físicamente.

### `INT-FIN-002`

- Existe como documento conceptual.
- Debe actualizar su sección de estado de implementación porque `factura_servicio` ya existe como tabla SQL.
- El resto continúa pendiente: resolución formal de obligado, evento, consumer, contrato de integración y reglas de propietario/responsable operativo.

### `relacion_generadora`

- Existe en SQL.
- Trigger polimórfico solo permite `venta` y `contrato_alquiler`.
- No existe API financiera propia.
- Comercial mantiene pruebas de no creación automática de obligaciones en generación de venta.

### `reserva_locativa_objeto`

- Existe en SQL, backend y tests.
- La documentación afirma una validación SQL cross-reserva que no se observa en schema.
- Validación de conflicto activo se observa en aplicación (`locativo_repository.py`).

### `contrato_alquiler` desde `reserva_locativa`

- Existe endpoint real `POST /api/v1/reservas-locativas/{id_reserva_locativa}/generar-contrato`.
- Existe service y repository.
- Existen tests.
- Documentación locativa general debe actualizar estado.

### `venta multiobjeto`

- Existe `reserva_venta_objeto_inmobiliario`.
- Existe `venta_objeto_inmobiliario`.
- Backend y tests cubren creación, generación de venta y condiciones por objeto.
- `DER-COMERCIAL` tenía una nota obsoleta sobre ausencia de backend; estado: CORREGIDO DOCUMENTALMENTE.

### `outbox_event`

- Existe tabla SQL.
- Existe repository outbox.
- Existen tests.
- Se usa en flujos comercial/locativo e integraciones inmobiliarias.
- No existe emisión para `factura_servicio_registrada`; está correctamente pendiente.

## 11. Recomendaciones de orden de corrección

1. Fixes críticos:
   - Actualizar estado documental de `factura_servicio` diferenciando SQL implementado vs API/evento/consumer pendientes.
   - Actualizar `DEV-API-LOCATIVO`, `DER-LOCATIVO` y roadmap con backend/tests reales.
   - Mantener seguimiento de `DER-COMERCIAL` tras la corrección documental del estado backend comercial.

2. Fixes altos:
   - Marcar `API-FIN-001` como no implementado o crear backend financiero mínimo.
   - Corregir documentación de `reserva_locativa_objeto`: validación cross-reserva está en aplicación, no en SQL.
   - Agregar `factura_servicio` a matriz CORE-EF con estado granular.
   - Reforzar que `SERVICIO_TRASLADADO` no es valor SQL actual de `relacion_generadora`.

3. Tests faltantes:
   - Tests SQL/repository para constraints de `factura_servicio`.
   - Tests futuros para producer `factura_servicio_registrada` cuando se implemente.
   - Tests financieros solo cuando exista API/service/consumer financiero real.

4. Documentación menor:
   - Corregir encoding/mojibake en `DEV-API-LOCATIVO`.
   - Actualizar roadmap como vista de estado real.
   - Normalizar naming `inmueble` en vez de “terreno/inmueble” para `factura_servicio`.
