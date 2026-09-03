# Sistema Inmobiliario — Guía técnica de incorporación

Revisión documental: 2026-09-03  
Base verificada: `main` en `01fdce84ef488f1d2a1c432bd33302684e438e9f`

Este documento explica el estado implementado y las reglas prácticas para
incorporarse al proyecto. No reemplaza los contratos arquitectónicos ni los
issues vigentes. Ante contradicción, aplicar la precedencia definida en
[`AGENTS.md`](AGENTS.md) y [`CODEX-WORKFLOW.md`](CODEX-WORKFLOW.md).

## 1. Qué es el sistema

El repositorio contiene una aplicación de gestión inmobiliaria con:

- frontend desktop en Flet;
- backend HTTP en FastAPI;
- persistencia SQLAlchemy/PostgreSQL;
- dominios para personas, inmuebles, compraventa, alquileres, finanzas,
  operación y administración;
- arquitectura multiinstalación/offline;
- sincronización mediante outbox, inbox y procesamiento de envelopes.

El sistema tiene runtime funcional amplio, pero su madurez no es uniforme.
Conviven código moderno con componentes históricos todavía productivos. Una
capacidad documentada, una columna `uid_global` o un evento en outbox no prueban
por sí solos que exista un circuito funcional o distribuido completo.

## 2. Stack comprobado

- Python.
- FastAPI y Pydantic.
- SQLAlchemy.
- PostgreSQL.
- Pytest.
- Ruff.
- Flet para la aplicación desktop.

Las dependencias y comandos de arranque se mantienen en
[`backend/README.md`](backend/README.md),
[`frontend/README.md`](frontend/README.md) y
[`frontend/flet_app/README.md`](frontend/flet_app/README.md).

## 3. Arquitectura general

El patrón vigente para código nuevo es:

```text
Frontend Flet
→ FastAPI router
→ Application Service / Orchestrator
→ Repository
→ PostgreSQL
```

Intervienen transversalmente:

```text
Administrativo / autenticación y autorización
CORE-EF
operacion_idempotente
outbox / inbox
Sync
```

El application service gobierna el caso de uso y la transacción. El repository
consulta y persiste, pero un repository nuevo no debe decidir `commit()` o
`rollback()`. El código histórico no siempre cumple esta separación: verificar
router, service, repository, SQL y tests antes de reutilizarlo.

## 4. Mapa de dominios

El dictamen global del sistema es **AVANZADO**, no por promedio, sino porque
existen circuitos funcionales integrados y una infraestructura transversal
materializada. La adopción de seguridad, CORE-EF y Sync todavía es desigual.

| Dominio | Responsabilidad | Estado | Qué está estable | Principal pendiente |
| --- | --- | --- | --- | --- |
| Técnico / CORE-EF / Sync | Identidad técnica transversal, idempotencia, outbox/inbox y protocolo Sync | **AVANZADO** | Ledger #469/#470 e inbox/retry #511/#512 | #522 y migración de consumers legacy |
| Administrativo | Usuarios, autenticación humana, autorización y configuración | **AVANZADO** | Bearer/principal, Usuario portable y calendario comercial | #461 y adopción uniforme de autorización/scope |
| Personas | Identidad de personas y datos relacionados | **INTERMEDIO** | CRUD, documentos estructurados, domicilios, contactos y relaciones | Lifecycle, deduplicación, CAS y representación efectiva |
| Inmobiliario | Inmuebles, UF, disponibilidad, ocupación y servicios | **INTERMEDIO** | Modelo SQL, XOR y APIs operativas | Seguridad, lifecycle y Sync portable |
| Comercial | Reservas, ventas, participantes y plan comercial | **AVANZADO** | Venta directa completa y PPV2 actual | Base común/indexación futura y portabilidad del grafo |
| Locativo | Solicitudes, reservas, contratos y actos de entrega/restitución | **INTERMEDIO** | Flujo principal y cronograma financiero | Garantías, lifecycle y protocolo portable #519 |
| Financiero | Obligaciones, pagos, imputaciones, saldos e índices | **AVANZADO** | Obligaciones, cronogramas, pagos y estado de cuenta | PPV2 definitivo, seguridad y reversión |
| Operativo | Sucursales, instalaciones y caja física | **INTERMEDIO** | Sucursal, instalación, configuración y caja básica | Arqueo, jornada, fecha operativa e integración financiera |
| Gestión Operativa / GOP | Tareas y seguimiento interno | Diseño **LISTO_PARA_IMPLEMENTACIÓN**; runtime **NO INICIADO** | DEV-ARCH y DER del MVP humano | DEV-SRV GOP |
| Documental | Futura gestión transversal de documentos y archivos | **INICIAL** | Diseño y SQL preparatorio disperso | Storage, upload/download, seguridad y Sync de archivos |
| Analítico | Futuras métricas, proyecciones y reportes read-only | **NO INICIADO** | Documentación y queries fuente operativas | MVP, ownership, scope y consolidación |

## 5. Ownership obligatorio

| Concepto | Owner |
| --- | --- |
| Persona | Personas |
| Usuario | Administrativo |
| Sucursal | Operativo |
| Instalación | Operativo |
| Inmueble / Unidad Funcional | Inmobiliario |
| Disponibilidad / Ocupación | Inmobiliario |
| Reserva de venta / Venta | Comercial |
| Plan comercial PPV2 | Comercial |
| Obligación / Pago / Imputación | Financiero |
| Contrato de alquiler | Locativo |
| Caja física | Operativo |
| Tarea | GOP |
| Documento / archivo | Documental futuro |
| Métrica / proyección | Analítico futuro |
| Sync, outbox, inbox y delivery | Técnico |
| Autenticación humana | Administrativo |
| Autenticación de `SISTEMA` | Técnico / Seguridad, pendiente #522 |

Mantener explícitas estas diferencias:

```text
Persona != Usuario
Sucursal != Instalación
Gestión Operativa != Operativo
Caja Operativa != Pago Financiero
Plan Comercial != Obligación Financiera
Dato estructurado != Documento digital
Query operativa != Analítico
```

## 6. Contratos técnicos obligatorios para código nuevo

### 6.1 Identidad humana

```text
Authorization: Bearer
→ sesión válida
→ AuthenticatedPrincipal
→ autorización
```

Todo command nuevo o modificado autenticado con Bearer deriva la identidad humana
del principal. No debe requerir, usar, comparar ni parsear `X-Usuario-Id` como
identidad o autorización.

### 6.2 CORE-EF

Clasificar primero el endpoint con una categoría de `AGENTS.md`. Todo write
sincronizable usa el helper común CORE-EF de headers y exige `X-Op-Id`,
`X-Sucursal-Id` y `X-Instalacion-Id`. Si modifica una entidad
existente/versionada, también exige `If-Match-Version`; este header no se fuerza
en creaciones.

Además, el command debe declarar y documentar explícitamente, según corresponda:

- `uid_global` como identidad portable y el uso de `version_registro`;
- idempotencia, outbox y lock lógico;
- frontera de transacción y rollback;
- tests de headers, versión, idempotencia, rollback y outbox.

No declarar cumplimiento profundo porque existan columnas: debe haber evidencia
en router, service, repository, SQL y tests.

### 6.3 Idempotencia

Reutilizar `operacion_idempotente` y el flujo:

```text
claim → EXECUTE | REPLAY | CONFLICT → complete
```

El `payload_hash` se calcula de forma determinista sobre el payload canónico, pero
la equivalencia no depende sólo de ese hash. El mismo `op_id` produce `REPLAY`
únicamente cuando `command`, `target` y payload canónico son compatibles; las
diferencias se clasifican como `ConflictKind.COMMAND`, `ConflictKind.TARGET` o
`ConflictKind.PAYLOAD`. El target se declara en el claim y no se esconde
accidentalmente dentro del payload. No crear un ledger paralelo por dominio o
entidad.

### 6.4 Transacción

```text
Application Service / Orchestrator
→ owner de commit y rollback
```

Cuando corresponda, efecto de negocio, outbox y receipt comparten una única
transacción. Los repositories nuevos no hacen commits parciales.

### 6.5 Sync

Mantener separadas estas identidades:

```text
event_id  != op_id
Delivery  = (event_id, consumer)
Operation = (consumer, op_id)
Attempt   = attempt_id
```

- `worker_id` sirve para observabilidad; no demuestra ownership.
- El ownership se prueba mediante lease/fencing y generación vigente.
- Dependencia portable temporalmente ausente → `PENDING_DEPENDENCY`.
- Payload inválido o semántica prohibida ≠ pending.
- Una PK local nunca es identidad remota.
- Parser, allowlist y dispatcher aplican default-deny.
- No usar timestamps como last-write-wins.

## 7. NO COPIAR ESTOS PATRONES

- `X-Usuario-Id` en código nuevo.
- Endpoints nuevos sin Bearer y autorización explícita.
- `commit()` o `rollback()` dentro de un repository nuevo.
- PK local en payloads como identidad remota.
- Consumers payload-less que dependen de la DB del emisor.
- `op_id` guardado en una entidad como sustituto del ledger transversal.
- `str(exc)` en respuestas HTTP.
- Timestamps como política de resolución LWW.
- `date.today()` como fecha operativa contractual.
- Suponer que `uid_global` implica portabilidad completa.
- Suponer que outbox implica replicación completa.
- Suponer que una allowlist implica consumer implementado.
- Usar `terreno` como aggregate nuevo; es terminología histórica.
- Confundir `persona_documento` con un archivo digital.
- Confundir estado de cuenta, deuda consolidada o un detalle integral con
  Analítico.

Estos paths pueden seguir activos por compatibilidad. La prohibición es ampliar
el patrón, no romper callers históricos fuera de un issue de migración.

## 8. Buenas referencias de código

| Archivo | Patrón que demuestra |
| --- | --- |
| [`backend/app/api/authentication.py`](backend/app/api/authentication.py) | Dependencia HTTP Bearer → principal |
| [`backend/app/application/administrativo/authentication.py`](backend/app/application/administrativo/authentication.py) | Sesión, usuario activo y `AuthenticatedPrincipal` |
| [`backend/app/application/administrativo/authorization.py`](backend/app/application/administrativo/authorization.py) | Autorización administrativa default-deny |
| [`backend/app/application/common/idempotency.py`](backend/app/application/common/idempotency.py) | Claim, fingerprint, replay y conflicto |
| [`backend/app/infrastructure/persistence/repositories/operacion_idempotente_repository.py`](backend/app/infrastructure/persistence/repositories/operacion_idempotente_repository.py) | Persistencia del ledger sin ownership transaccional propio |
| [`backend/app/infrastructure/persistence/repositories/inbox_repository.py`](backend/app/infrastructure/persistence/repositories/inbox_repository.py) | Delivery, operation scope, lease y fencing |
| [`backend/app/application/integration/inbox_retry.py`](backend/app/application/integration/inbox_retry.py) | Entry point reusable para retry de pending |
| [`backend/app/application/administrativo/services/usuario_sync_service.py`](backend/app/application/administrativo/services/usuario_sync_service.py) | Aggregate portable y parser default-deny |
| [`backend/app/application/administrativo/services/calendario_comercial_sync_service.py`](backend/app/application/administrativo/services/calendario_comercial_sync_service.py) | Consumer portable, continuidad, CAS y singleton |
| [`backend/app/application/comercial/services/confirm_venta_directa_completa_service.py`](backend/app/application/comercial/services/confirm_venta_directa_completa_service.py) | Orquestación multientidad y frontera transaccional |
| [`backend/app/application/common/local_installation.py`](backend/app/application/common/local_installation.py) | Resolver local read-only y default-deny |
| [`backend/app/config/settings.py`](backend/app/config/settings.py) | Validación de `LOCAL_INSTALLATION_CODE` |

Copiar la invariante demostrada, no un archivo completo ni detalles accidentales
de su dominio.

## 9. Estado de Sync

### Baseline canónico

- **#512:** retained envelope, delivery, operation scope, retry,
  `PENDING_DEPENDENCY`, lease y fencing.
- **Usuario:** `uid_global`, resolver, producer y consumer de alta/desactivación;
  las credenciales no se sincronizan.
- **Calendario comercial:** singleton, CAS, idempotencia, outbox y aplicación
  remota portable.

### Legacy o parcial

- venta y escrituración;
- entrega y restitución locativa (#519);
- eventos Operativos;
- entidades que tienen `uid_global` pero carecen de producer, consumer o
  resolución portable autoritativa.

Reglas de lectura:

```text
uid_global != portabilidad completa
producer != Sync end-to-end
outbox != consumer remoto
```

## 10. Estado de seguridad

El núcleo Bearer, sesión, principal y autorización existe y debe ser el baseline.
Su adopción global todavía es parcial: Personas, Inmobiliario, Comercial,
Locativo, Financiero, Operativo y rutas administrativas históricas conservan
`X-Usuario-Id` o guards no uniformes.

- **#461:** migración transversal de identidad humana.
- **Scope por sucursal:** existen datos y helpers, pero no un predicado completo
  adoptado uniformemente por todos los dominios.
- **#522:** autenticación/autorización de procesos `origen=SISTEMA`.

```text
#522 NO bloquea el MVP humano de GOP
#522 SÍ bloquea origen=SISTEMA y automatizaciones autorizadas
```

No resolver #522 falsificando un Usuario humano.

## 11. Testing

El flujo de validación es:

1. PostgreSQL real activo.
2. Reset oficial cuando corresponda.
3. Suite focal.
4. Integración relacionada.
5. Regresión relevante.
6. Ruff sobre el alcance.
7. `compileall` cuando corresponda.
8. `git diff --check` y revisión del diff completo.

En Windows usar `backend/scripts/reset_db.bat`; en Linux/Codex Cloud,
`backend/scripts/reset_db.sh`. El reset debe finalizar correctamente antes de
declarar validada una suite PostgreSQL.

```text
skipped != passed
```

Leer la razón de cada skip. SQLite no reemplaza PostgreSQL para triggers, locks,
constraints, concurrencia ni tipos reales. No declarar una prueba ejecutada sin
salida real de terminal.

Suites transversales útiles como referencia:

- `backend/tests/test_operacion_idempotente_470_*.py`;
- `backend/tests/test_inbox_pending_dependency_511.py`;
- `backend/tests/test_administrativo_usuario_sync_510.py`;
- `backend/tests/test_administrativo_calendario_comercial_sync_486*.py`;
- `backend/tests/test_local_installation_resolver.py`;
- `backend/tests/test_local_installation_postgres.py`.

## 12. Workflow de desarrollo

```text
Issue
→ auditoría
→ contrato formal, si faltan decisiones
→ implementación focal
→ tests
→ review
→ corrección por invariante
→ merge
```

Seguir [`CODEX-WORKFLOW.md`](CODEX-WORKFLOW.md). Cada PR debe ser incremental,
explicitar alcance/fuera de alcance y decidir su impacto en
`PROJECT-STATUS.md`.

Si dos o más findings pertenecen a la misma dimensión conceptual, detener los
microparches: auditar la clase completa, construir la invariante o matriz y
clasificarla como `FINDING_PUNTUAL`, `INVARIANTE_ESTRUCTURAL_INCOMPLETA` o
`REDISENO_NECESARIO`. Sólo después corresponde implementar.

## 13. Estado de GOP

```text
DEV-ARCH GOP      → completo (#523 / PR #524)
DER GOP           → completo (#528 / PR #529)
DEV-SRV GOP       → siguiente incremento
DEV-API GOP       → posterior
SQL/runtime/tests → no iniciados
```

GOP es Gestión Operativa/Tareas, no el dominio Operativo. El MVP humano tiene
contrato de Tarea, Comentario e Historial, pero ninguna de esas entidades existe
en runtime. #527 conserva el backlog post-MVP. #522 sólo bloquea
`origen=SISTEMA`; no bloquea comenzar DEV-SRV del MVP humano.

## 14. Estado de PPV2

### Runtime actual

- PPV2 versionado por bloques;
- venta directa completa;
- materialización de obligaciones financieras;
- disponibilidad y outbox dentro de la orquestación moderna;
- vencimiento inicial sugerido implementado por #426 / PR #531.

### Contrato futuro

- #427: base común mensual 1:1 por venta;
- #428: materialización del valor base pendiente;
- #429: período de índice objetivo por obligación;
- #423: selector definitivo, posterior a los soportes anteriores;
- #534: dependencias portables del grafo PPV2.

Los PR exclusivamente documentales no materializan runtime. El selector/indexado
actual por bloque es compatibilidad vigente, no el patrón definitivo.

## 15. Estado Documental

```text
SQL preparatorio / campos / números / actas
!=
subsistema Documental
```

Hoy no hay storage canónico, upload/download, autorización documental ni Sync de
archivos. `persona_documento` representa identidad estructurada; una escritura
con número/fecha representa datos del acto; un recibo lógico no es un archivo
persistido.

## 16. Estado Analítico

```text
queries operativas reutilizables
!=
dominio Analítico
```

Estado de cuenta, deuda consolidada y detalles integrales pertenecen a sus
dominios productores. No existen views/marts, KPIs, dashboard analítico ni
consolidación multi-sucursal en runtime.

## 17. Primeras tareas para una incorporación

### Apto para incorporación temprana

- DEV-SRV GOP, respetando DEV-ARCH y DER cerrados.
- Migración Bearer muy focal dentro de #461.
- Tests focales de una capacidad ya implementada.
- Sanitización focal del error contract sin cambiar códigos ni semántica.

### Requiere contexto previo

- Lifecycle de Personas, Inmobiliario o Locativo.
- Caja, arqueo, jornada y fecha operativa.
- Scope/elegibilidad por sucursal.
- Idempotencia de commands compuestos.
- Venta desde reserva y garantías/representación.

### No recomendado como primer trabajo

- Núcleo concurrente #512.
- Grafo portable #534.
- Selector financiero #423.
- Autenticación técnica #522.
- Storage/offline Documental.
- Analítico multi-sucursal.
- Migración transaccional masiva de repositories.

## 18. Issues esenciales

Verificar siempre su estado actual en GitHub antes de trabajar.

| Issue | Estado en esta revisión | Por qué importa |
| --- | --- | --- |
| #461 | Abierto | Migración de `X-Usuario-Id` a identidad autenticada |
| #469 / #470 | Cerrados | Ledger físico y runtime canónico de idempotencia |
| #511 / PR #512 | Cerrado / mergeado | Protocolo de pending, retry, operation scope y fencing |
| #522 | Abierto | Identidad/autorización de procesos `SISTEMA` |
| #365 | Abierto | Proveedor transversal de fecha operativa |
| #534 | Abierto | Dependencias portables del grafo PPV2 |
| #423 | Abierto/bloqueado | Selector financiero definitivo |
| #427 | Abierto | Base común por venta |
| #428 | Abierto | Valor base pendiente |
| #429 | Abierto | Período objetivo persistido |
| #519 | Abierto | Entrega/restitución locativa portable |
| #248 | Abierta | Épica Operativo |
| #249 | Abierta | Épica Administrativo |
| #256 | Abierto | Arqueo/control de caja |
| #257 | Abierto | Jornada operativa |
| #258 | Abierto | Lectura Financiero–Caja |
| #527 | Abierto | Backlog GOP post-MVP |
| #523 / PR #524 | Cerrado / mergeado | Trazabilidad de DEV-ARCH GOP |
| #528 / PR #529 | Cerrado / mergeado | Trazabilidad del DER GOP |

## Antes de abrir un PR

- Verificar `main` y registrar el SHA base.
- Leer reglas globales y locales.
- Confirmar issue owner, alcance y exclusiones.
- Identificar DEV-ARCH, DER, DEV-SRV y DEV-API vigentes.
- Contrastar contrato con SQL, runtime y tests.
- Confirmar actor, autorización y scope.
- Confirmar CORE-EF, CAS e idempotencia.
- Confirmar owner de transacción.
- Si hay Sync, confirmar producer, payload portable, consumer y pending.
- Ejecutar validaciones acordes y no ampliar el scope.

## Fuentes que deben leerse primero

1. [`AGENTS.md`](AGENTS.md).
2. [`PROJECT-STATUS.md`](PROJECT-STATUS.md), como estado y no arquitectura.
3. [`backend/documentacion/CORE-EF/`](backend/documentacion/CORE-EF/), si el
   incremento escribe o sincroniza.
4. [`CODEX-WORKFLOW.md`](CODEX-WORKFLOW.md).
5. DEV-ARCH del dominio.
6. DER vigente.
7. DEV-SRV.
8. DEV-API.
9. Tests focales.
10. Issue, dependencias y PRs relacionados.
