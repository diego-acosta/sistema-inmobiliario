# ROADMAP_MAESTRO_ACTUALIZADO

## 1. Estado actual del sistema

El proyecto ya no tiene solo `personas` e `inmobiliario` como backend API real. Hoy existen tres bloques operativos con surface HTTP materializado, documentado y cubierto por tests:

- `personas`
- `inmobiliario`
- `comercial`

Estado global verificable al 2026-04-23:

- esquema SQL amplio y consistente para multiples dominios
- arquitectura vigente en `DEV-ARCH`
- backend implementado en routers, schemas, services y repositories para `personas`, `inmobiliario` y `comercial`
- contratos `DEV-API` vigentes y normativos para esos tres dominios
- integracion `comercial -> inmobiliario` materializada con outbox, consumidores y reads de trazabilidad
- convenciones transversales visibles en codigo: headers tecnicos write, envelope `{ ok, data }`, errores tipados, `If-Match-Version`, soft delete, metadatos `CORE-EF` y observabilidad minima de outbox

Lo que hoy esta solido:

- DB real y dump vigente del sistema
- arquitectura por dominios y ownership semantico
- backend del dominio `personas`
- backend del dominio `inmobiliario`
- backend operativo `v1` del dominio `comercial`
- cobertura de tests sobre los bloques materializados
- `DEV-API-PER-001.md`
- `DEV-API-INM-001.md`
- `DEV-API-COMERCIAL.md`

## 2. Dominios cerrados hoy

### Personas

Debe considerarse cerrado para su alcance vigente:

- backend implementado
- contratos publicos alineados
- tests presentes
- soporte transversal de identidad y participaciones ya reutilizado por `comercial`

### Inmobiliario

Debe considerarse cerrado a nivel backend, tests y documentacion API.

Incluye hoy:

- desarrollos
- inmuebles
- unidades funcionales
- edificaciones
- servicios y asociaciones servicio <-> inmueble / unidad funcional
- disponibilidad
- ocupacion
- trazabilidad de integracion por activo

Tambien incluye el consumo de eventos comerciales hoy materializados:

- `venta_confirmada` como no-op explicito e idempotente
- `escrituracion_registrada` con efecto operativo sobre disponibilidad

### Comercial

Debe considerarse cerrado como bloque operativo `v1` para el surface hoy materializado.

Incluye hoy:

- `reserva_venta`
  - `POST`
  - `PUT` escalar
  - `PATCH /baja`
  - `GET detalle`
  - `GET listado`
  - `POST /activar`
  - `POST /cancelar`
  - `POST /vencer`
  - `POST /confirmar`
  - `POST /generar-venta`
- `venta`
  - `GET detalle`
  - `POST /definir-condiciones-comerciales`
  - `PATCH /confirmar`
- recursos hijos de `venta`
  - `POST /instrumentos-compraventa`
  - `GET /instrumentos-compraventa`
  - `POST /cesiones`
  - `GET /cesiones`
  - `POST /escrituraciones`
  - `GET /escrituraciones`
- lectura de integracion `comercial -> inmobiliario` por venta
- outbox e integracion materializados para `venta_confirmada` y `escrituracion_registrada`

No debe considerarse cerrado fuera de ese `v1`. Sigue teniendo backlog explicito fuera del alcance actual:

- `rescision_venta`
- alta directa `POST /api/v1/ventas`
- `GET /api/v1/ventas` global
- detalles individuales de `instrumento_compraventa`, `cesion` y `escrituracion`
- `PUT` y `PATCH /baja` de `venta`, `instrumento_compraventa`, `cesion` y `escrituracion`
- documental comercial propia
- reportes consolidados o busquedas amplias de corte analitico
- integracion con financiero

## 3. Tabla de dominios del sistema

| Dominio | Estado | Nivel de implementacion real | Nivel de documentacion | Siguiente paso recomendado |
| --- | --- | --- | --- | --- |
| Personas | cerrado | Alto: router, schemas, services, repositories y tests alineados con el alcance vigente | Alto: `DEV-ARCH`, `DEV-SRV` y `DEV-API` alineados | Mantener congelado salvo correcciones de drift |
| Inmobiliario | cerrado | Alto: backend, trazabilidad operativa e integracion con comercial materializadas | Alto: `DEV-ARCH`, `DEV-SRV` y `DEV-API` alineados | Mantener congelado salvo correcciones de drift |
| Comercial | cerrado v1 | Alto para el scope vigente: reservas, venta derivada, condiciones comerciales, instrumentos, cesiones, escrituraciones, reads e integracion materializados | Alto: `DEV-API` oficial vigente y `DEV-SRV` con pequenos pendientes de ajuste conceptual | Mantener cerrado en `v1`; todo lo nuevo entra como backlog post-`v1` |
| Locativo | parcial | Bajo: hay soporte SQL real para `contrato_alquiler`, pero no hay router, schemas, services ni tests propios | Medio/alto: `DEV-ARCH`, `DEV-SRV`, `CAT-CU`; sin `DEV-API` aterrizado | Abrir como siguiente bloque funcional |
| Financiero | parcial | Bajo: hay soporte SQL real, pero no hay router, schemas, services ni tests propios | Medio/alto: `DEV-ARCH`, `DEV-SRV`, `CAT-CU`; sin `DEV-API` aterrizado | Esperar origenes reales desde `comercial` o `locativo` |
| Documental | parcial | Bajo: existe soporte SQL, pero no hay API propia vigente | Medio/alto: `DEV-ARCH`, `DEV-SRV`, `CAT-CU` | Posponer hasta tener entidades concretas que lo necesiten |
| Operativo | parcial | Bajo: existen `sucursal` e `instalacion` en SQL, pero no hay API propia vigente | Medio/alto: `DEV-ARCH`, `DEV-SRV`, `CAT-CU` | Implementar solo si un flujo real lo necesita |
| Administrativo | parcial | Bajo: existen usuarios, roles y configuracion en SQL, pero no hay API propia vigente | Medio/alto: `DEV-ARCH`, `DEV-SRV`, `CAT-CU` | Dejar para cuando haga falta autenticar o autorizar el sistema real |
| Analitico | pendiente | Nulo en backend API; sin routers ni capa read-only propia materializada | Medio: `DEV-ARCH`, `DEV-SRV`, `CAT-CU` | Dejar para el final |
| Tecnico / sincronizacion | parcial | Parcial: existen outbox, observabilidad y patrones transversales reales, pero no dominio tecnico expuesto como API propia | Medio/alto: `CORE-EF`, `DECISIONES`, `DEV-SRV`, `CAT-CU` | Activarlo solo si la complejidad cross-domain lo exige |

## 4. Prioridad recomendada

Orden sugerido para continuar:

1. Locativo
2. Financiero
3. Documental
4. Administrativo
5. Operativo
6. Tecnico / sincronizacion
7. Analitico

Razonamiento:

- `personas`, `inmobiliario` y `comercial` ya cubren el primer nucleo write del sistema.
- `locativo` es el siguiente dominio negocio con mejor base documental y SQL real sin abrir un cuarto frente transversal.
- `financiero` debe apoyarse en origenes reales ya cerrados, no en contratos hipoteticos.
- `documental` agrega valor cuando existan casos concretos que lo consuman.
- `administrativo` y `operativo` siguen sin ser el cuello de botella principal del negocio.
- `analitico` debe venir al final, cuando las fuentes write esten mas estables.

## 5. Estado final de comercial v1

El dominio `comercial` ya debe leerse como bloque operativo `v1` y no como dominio en construccion inicial.

Estado final del dominio para `v1`:

- contrato HTTP oficial vigente congelado en `DEV-API-COMERCIAL.md`
- writes materializados y con control de version para el alcance vigente
- reads operativos materializados para reservas, venta y listados hijos
- integracion asincronica `comercial -> inmobiliario` materializada y observable
- tests presentes sobre comportamiento, persistencia, contratos y trazabilidad
- backlog futuro explicitado fuera del contrato oficial vigente

Eso no significa dominio completo al 100% del modelo SQL. Significa dominio cerrado para el bloque funcional efectivamente comprometido como `v1`.

## 6. Backlog fuera de comercial v1

Queda explicitamente fuera de `v1` y no debe reintroducirse como drift contractual:

- `rescision_venta`
- venta directa fuera de `reserva_venta`
- cancelacion propia de `venta`
- mutaciones y bajas de instrumentos, cesiones y escrituraciones
- detalle individual de instrumentos, cesiones y escrituraciones
- listados globales amplios de `venta` y recursos hijos
- documental comercial propia
- reportes consolidados y consultas de corte analitico
- integracion financiera derivada

Todo eso debe tratarse como backlog de un bloque posterior, no como deuda oculta dentro del `v1` vigente.

## 7. Proximo bloque de trabajo

Dominio recomendado para empezar ahora:

- `locativo`

Slice inicial recomendado:

- `SRV-LOC-001 - gestion de contratos de alquiler`

Punto de entrada mas realista:

- auditar SQL de `contrato_alquiler` y relaciones inmediatas
- congelar `DEV-API` inicial del dominio locativo contra SQL real
- implementar alta minima, detalle y listado antes de abrir efectos mas complejos

## 8. Riesgos y dependencias

Dependencias principales:

- `locativo` depende de `personas` e `inmobiliario`
- `financiero` depende de origenes reales desde `comercial` o `locativo`
- `documental` depende de entidades negocio concretas para asociacion
- `analitico` depende de multiples dominios ya estables
- `tecnico` depende de que existan suficientes flujos write reales para justificar mas infraestructura

Riesgos si se avanza en mal orden:

- reabrir `comercial` sin delimitar backlog post-`v1` vuelve a introducir drift contractual
- implementar `financiero` antes de `locativo` fuerza origenes artificiales
- abrir `analitico` demasiado temprano congela vistas sobre contratos write todavia inmaduros
- abrir `documental` antes de tener casos concretos produce asociaciones vacias o ownership confuso

## 9. Recomendacion operativa

Para continuar sin perder alineacion:

1. mantener congelados `personas`, `inmobiliario` y `comercial` salvo correcciones de drift
2. no expandir `comercial` dentro del mismo `v1`; usar backlog explicito cuando aparezcan pedidos nuevos
3. abrir `locativo` con el mismo patron usado en `comercial`
4. repetir siempre la secuencia:
   - auditar SQL
   - alinear `DEV-API`
   - implementar backend
   - cerrar tests
   - volver a ajustar documentacion

## HANDOFF

Estado actual resumido:

- `personas` cerrado en su alcance vigente
- `inmobiliario` cerrado en su alcance vigente
- `comercial` cerrado como bloque operativo `v1`
- `DEV-API-COMERCIAL.md` es contrato oficial vigente del dominio comercial
- la integracion `comercial -> inmobiliario` ya existe y esta materializada
- el siguiente dominio recomendado es `locativo`

Terminado:

- backend de `personas`
- backend de `inmobiliario`
- backend operativo `v1` de `comercial`
- contratos `DEV-API` vigentes de esos tres dominios

Pendiente:

- backend de `locativo`
- backend de `financiero`
- backend de `documental`
- backend de `administrativo`
- backend de `operativo`
- backend de `tecnico`
- backend de `analitico`

Siguiente paso exacto:

- empezar `locativo`
- auditar `contrato_alquiler` en SQL
- congelar `DEV-API` inicial del dominio
- implementar alta minima + detalle + listado
