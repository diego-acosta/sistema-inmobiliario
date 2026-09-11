# DEV-ARCH-GEN-002 — Autoridad central y contrato de transición

## 1. Estado y objetivo

- Estado: **contrato arquitectónico objetivo de la transición; runtime pendiente de migración**.
- Decisión de producto: FastAPI central y PostgreSQL central como única autoridad persistente, conservando inicialmente Flet.
- Rama de integración: `transition/central-authority`.
- Corte inicial verificado: `main` y transición en `e51e1f50cc51b39856a43480d3005a34526808d1` (2026-09-11).
- Alcance de PR 01: arquitectura y gobernanza; no cambia SQL, runtime, frontend ni tests funcionales.

Este contrato habilita PRs incrementales sin seguir imponiendo replicación
multiinstalación. Complementa [DEV-ARCH-GEN-001](DEV-ARCH-GEN-001.md) y no
transfiere ownership ni redefine casos de uso o decisiones económicas.

## 2. Arquitectura anterior y objetivo

| Plano | Modelo anterior / heredado | Arquitectura objetivo |
| --- | --- | --- |
| Cliente | Flet por instalación | Múltiples clientes Flet iniciales |
| Backend | FastAPI local por instalación | FastAPI central autoritativo, accesible por HTTPS |
| Persistencia | PostgreSQL local por instalación escribible | PostgreSQL central: única autoridad persistente del sistema |
| Negocio compartido | Replicación entre instalaciones y convergencia | Lectura y escritura contra la misma autoridad central |
| Sucursal | Contexto operativo dentro del modelo distribuido | Contexto funcional/operativo autorizado, sin DB autoritativa propia |
| Offline | Diseño de escrituras locales y sincronización posterior | Operación normal online; sin escritura definitiva offline |

Los clientes acceden por red al backend; no escriben directamente en PostgreSQL.
No habrá bases de negocio autoritativas por sucursal, múltiples bases escribibles
concurrentes por instalación, replicación bidireccional de entidades de negocio
ni resolución de conflictos entre réplicas como flujo normal del producto.
Los conflictos CAS entre usuarios sobre la DB central siguen existiendo y deben
resolverse como concurrencia, no como Sync.

Flet se conserva como cliente inicial. Migrarlo a web es una decisión posterior
independiente, fuera de esta transición. Este contrato no afirma que el Flet
actual ya gestione sesión, Bearer, sucursal y red conforme al objetivo.

## 3. Sucursal, instalación y actores

`SUCURSAL` sigue siendo una unidad funcional/operativa del negocio. Conserva,
según contratos de dominio, alcance operativo, autorización, numeración, caja,
contexto comercial/administrativo, reportes y parametrización. Centralización
no elimina multi-sucursal ni cambia el ownership de Operativo.

`SUCURSAL ≠ INSTALACION` sigue siendo una separación válida.
`INSTALACION = nodo autoritativo con DB propia` deja de ser una premisa objetivo.
No se elimina ni renombra físicamente `INSTALACION` en PR 01. Su eventual valor
como cliente, dispositivo, estación, origen técnico, auditoría o diagnóstico
debe demostrarse y cerrarse en un PR posterior; esta lista no asigna nuevas
semánticas simultáneas a la entidad existente.

Debe definirse una identidad técnica canónica del deployment central y cómo se
representa; no se presupone que cada cliente ni cada sucursal sea una instalación
de persistencia. Quedan pendientes la relación con `INSTALACION`, sus FKs,
origen/última modificación, settings y headers. La metadata enviada por un
cliente no puede conferir identidad del servidor ni autorización funcional.

Los commands humanos centrales se basan en usuario autenticado mediante
`AuthenticatedPrincipal`, permisos y alcance autorizado. `USUARIO ≠ PERSONA`
y roles de seguridad ≠ roles de participación. La autenticación técnica de jobs
o integraciones requiere su contrato propio; no se inventa ni implementa aquí.
No se exige Bearer humano al login ni se usa como sustituto de identidad técnica.

## 4. CORE-EF conservado

| Elemento | Principio que permanece |
| --- | --- |
| `uid_global` | Identidad estable e inmutable; no se convierte en PK física |
| IDs locales | Se conservan para PK, joins y FKs; no se eliminan |
| `version_registro` / CAS | Concurrencia optimista y rechazo explícito de versiones incompatibles según el agregado/operación |
| `created_at`, `updated_at`, `deleted_at` | Temporalidad y baja lógica donde corresponda funcionalmente |
| UTC | Timestamps consistentes; no redefine fechas económicas ni fecha operativa |
| Transacción por caso de uso | Efectos coordinados, commit y rollback atómicos |
| Idempotencia | Seguridad de comandos reintentables o económicamente críticos |
| Trazabilidad y auditoría | Actor, operación y evidencia de cambio según el contrato |
| Errores tipados | Conflictos funcionales, técnicos y de concurrencia explícitos |
| Separaciones de dominio | Usuario/persona, sucursal/instalación y ownership vigente |

Soft delete no equivale a cancelar, restaurar ni purgar una entidad: se conservan
las distinciones y exclusiones funcionales existentes. No se agrega metadata a
entidades que tengan excepciones formales, ni se fusionan versiones de agregados.

La retirada de Sync no elimina constraints, locks SQL, exclusión funcional o
protecciones de concurrencia justificadas por el caso. Un lock lógico persistido
no es obligatorio por defecto: debe tener una necesidad demostrada adicional a
CAS/transacciones. Locks motivados exclusivamente por operación distribuida
quedan sujetos a la revisión de compatibilidad del apartado siguiente.

## 5. Infraestructura distribuida en transición

Las siguientes piezas dejan de ser requisitos de nuevas funcionalidades centrales
por su justificación distribuida. **No se borran ni desactivan en PR 01**:

| Pieza o contrato | Estatus y revisión posterior |
| --- | --- |
| Outbox requerido exclusivamente para réplica | Obligatoriedad retirada; revisar productores y consumidores antes de reducirlo |
| Inbox de réplica / `inbox_operation_scope` | Compatibilidad transicional, no requisito de commands centrales |
| Delivery/event consumer distribuido | Revisar identidad de entrega y consumidores todavía existentes |
| Lease, fencing y takeover de aplicación remota | Mantener garantías mientras se ejecute el protocolo; no trasladarlas por defecto a nuevos writes |
| `PENDING_DEPENDENCY` y retry remoto | Sólo protocolo heredado; no modelar FKs centrales como esperas de réplica |
| Conflictos entre copias autoritativas | Fuera del objetivo; mantener sólo el tratamiento del runtime heredado hasta su retiro |
| Consumers de replicación | Congelados para expansión; retiro posterior con evidencia de consumidores/callers |
| Producers exclusivamente portables | Revisar su necesidad; no crear otros para cumplir documentos heredados |
| Paquetes y transporte Sync | En retirada arquitectónica, sin promesa de nuevas réplicas |
| Instalación origen/última por requisito universal Sync | Revisar metadata técnica; no eliminar columnas ni contratos aquí |

Compatibilidad no habilita nuevas bases autoritativas ni expansión funcional de
replicación. Sí permite correcciones necesarias para conservar caminos existentes
mientras se migran. Cualquier futura decisión de volver a replicar negocio
requeriría cambiar explícitamente esta arquitectura, fuera de esta serie.

Antes de retirar una pieza, el PR responsable debe identificar producers,
consumers, callers, tablas, tests y efectos de negocio afectados. Si sostiene un
efecto funcional, debe conservarlo o reemplazarlo con comportamiento equivalente
y validado. La ausencia de datos útiles no demuestra ausencia de consumidores.

## 6. `op_id` e idempotencia

`op_id` no equivale a Sync. Se conserva; puede aportar idempotency key,
correlación, trazabilidad de comandos y auditoría de operación. Cuando identifica
una operación idempotente, debe mantenerse estable en sus reintentos: no se
reinterpreta como un identificador efímero distinto por request ni se confunde
correlación con garantía de efectos únicos.

La idempotencia se justifica por seguridad del comando, especialmente en pagos,
movimientos financieros, emisión, requests reintentables, duplicación económica
e integraciones externas futuras. Se reutiliza la infraestructura útil existente
en vez de crear ledgers paralelos. El contrato específico conserva fingerprint
semántico, replay durable, conflicto ante payload material distinto, retry tras
fallo sin completion y atomicidad entre receipt y efecto cuando corresponda.
CAS e idempotencia siguen siendo controles distintos.

La centralización no elimina autenticación ni autorización en un replay. El PR
de contexto deberá cerrar su composición con los contratos existentes de
claim/replay/complete, sin alterar incidentalmente fingerprints o receipts.
Este documento no modifica el orden de ejecución runtime actual.

## 7. Outbox e integración

Outbox deja de exigirse por replicación entre instalaciones. El patrón puede
seguir siendo útil para eventos internos, integración externa, jobs,
notificaciones, desacoplamiento y procesamiento asíncrono si se implementan.
Estas posibilidades no se declaran capacidades existentes.

Cada PR posterior decidirá conservación, reducción o reemplazo según efectos y
consumidores. Cuando el caso requiera publicación durable, cambio de negocio y
outbox deben seguir compartiendo transacción; no se permite perder un efecto
funcional mediante una declaración genérica de `NO APLICA`.

En el corte inicial, `outbox_to_inbox_worker.py` y el dispatcher financiero
consumen `venta_confirmada` y `contrato_alquiler_activado` para efectos locales.
Por ello, outbox/inbox existentes no son sinónimos de réplica prescindible.
No se habilitan workers automáticamente por conservar sus archivos.

## 8. Offline y datos existentes

La operación normal es online contra la autoridad central. No se promete
escritura definitiva offline. Cache, drafts, cola temporal, retry de requests o
lectura degradada quedan fuera de este PR y requieren contratos futuros; ninguno
constituye una réplica autoritativa ni puede confirmar negocio por su cuenta.

**Dato de planificación confirmado por el responsable del proyecto:** la base
actual no contiene datos útiles cuya preservación condicione esta transición.
No es una conclusión obtenida consultando una DB productiva.

PRs posteriores pueden justificar reset estructural, reemplazo de tablas,
eliminación de infraestructura obsoleta, simplificación de constraints y
reconstrucción de DB de desarrollo. Deben preservar invariantes funcionales,
reglas económicas, integridad, seeds y creación reproducible del esquema.
No se exige consolidación ni backfill productivo de los datos actuales.
PR 01 no ejecuta reset. Si se incorporan datos útiles antes del corte final,
debe reevaluarse esta premisa antes de cualquier operación destructiva.

## 9. Precedencia documental acotada

Durante la transición y sus ramas derivadas, las decisiones explícitas de este
contrato, referenciado por `AGENTS.md`, prevalecen sobre las partes no migradas
de documentos anteriores **sólo** en topología, autoridad de persistencia,
Sync y contexto técnico asociado. Persistencia aquí no autoriza alterar
invariantes económicas o de integridad ajenas al modelo de réplicas.

Arquitectura objetivo es la documentación que adopta explícitamente esta decisión;
estar en la rama no convierte automáticamente un documento heredado en migrado.
Los documentos anteriores conservan reglas de negocio, decisiones económicas,
ownership, seguridad y restricciones no relacionadas con Sync. No se marcan
como obsoletos indiscriminadamente.

Toda discrepancia debe registrar fuente/sección, mandato distribuido sustituido,
decisión objetivo, evidencia de runtime y pendiente de migración. Una discrepancia
temporal así delimitada permite un PR documental previo al runtime; no autoriza
a declarar ese runtime implementado ni a ignorar sus contratos en ejecución.
Fuera de esta dimensión, se aplica la precedencia general de `AGENTS.md`.

### Matriz inicial de discrepancias y pendientes

Rutas documentales relativas a `backend/documentacion/`, salvo indicación.

| Fuente/sección o evidencia | Discrepancia con el objetivo | Tratamiento / siguiente incremento |
| --- | --- | --- |
| `CORE-EF/CORE-EF-001-infraestructura-transversal.md`, §§0, 3.2, 3.7, 4.8–4.10 y matriz §5 | Backend local, instalación con DB, operación distribuida y perfiles Sync | Aplicar §§2–7 de este contrato; migración documental CORE-EF posterior |
| `CORE-EF/CORE-EF-VALIDACION.md`, §§0, 4, 6, 13–14 | Negocio compartido implica Sync; write no Sync sin `op_id`; gates distribuidos | Sustituir sólo esos mandatos por clasificación central/idempotencia/eventos; actualizar checklist en PR posterior |
| `DEV-SRV/dominios/tecnico/SRV-TEC-001-aplicacion-transversal-de-core-ef-en-commands.md`, alcance/contexto | Contexto de instalación y coordinación outbox transversales | Contexto técnico y publicación según necesidad; contrato detallado posterior |
| `DEV-SRV/dominios/tecnico/SRV-TEC-002-gestion-de-operaciones-distribuidas-y-sincronizacion.md`, alcance/política pendiente | Aplicación remota, scope, retry, lease/fencing | Protocolo heredado preservado; inventario/retiro posterior |
| `DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`, headers write observables | `X-Instalacion-Id` requerido en commands existentes | API actual sin cambios; nueva obligatoriedad no se hereda, migración coordinada posterior |
| `DEV-ARCH-GEN-001.md`, §10; `backend/app/application/common/local_command_context.py` | Resolver local y relación instalación/sucursal | Compatibilidad actual; siguiente contrato de identidad/contexto |
| `backend/database/patch_inbox_pending_dependency_20260822.sql`; `backend/app/infrastructure/persistence/repositories/inbox_repository.py` | Tabla/scope y estados distribuidos materializados | No se alteran; invariantes vigentes mientras tengan callers |
| `backend/app/application/common/idempotency.py`; `backend/database/patch_operacion_idempotente_20260810.sql` | Ledger útil sin necesidad de réplica | Conservar seguridad del comando, sin generalizar scope de inbox |
| `backend/app/application/integration/outbox_to_inbox_worker.py`; `backend/app/application/financiero/services/inbox_event_dispatcher.py` | Eventos con efectos locales reales | Preservar efectos, auditar consumidores antes de retirar infraestructura |
| `backend/tests/test_inbox_pending_dependency_511.py`, `test_outbox_to_inbox_worker.py`, `test_local_command_context_536_api.py` | Tests del comportamiento actual | Evidencia leída, no ejecutada en PR 01; adaptación/regresión en PRs runtime |
| `PROJECT-STATUS.md`, frentes y cortes históricos | Próximos pasos distribuidos del roadmap anterior | §2.1 del status rige la transición; conservar estado funcional sin reescritura masiva |

Los freezes de dominio aún no migrados se evalúan con la misma regla acotada;
esta matriz no declara su migración completada. Si separar Sync exige una nueva
decisión funcional no autorizada, registrarla como bloqueo y detener ese cambio.

## 10. Estrategia de PRs y estado de trabajo

Los PRs incrementales de migración son pequeños, parten de ramas específicas y
tienen base `transition/central-authority`. El PR de sincronización de `main`
también tiene esa base: parte de una rama derivada de la transición e integra
`main` mediante merge, no mediante el rebase de los incrementos normales.
El PR final de integración queda exceptuado: incorpora `transition/central-authority`
con base `main`, conforme a los gates de §11.
No trabajar directamente sobre la rama compartida ni mezclar features ajenas.
El procedimiento y sincronización se definen en `CODEX-WORKFLOW.md`, §6.1.

| Estado | Significado |
| --- | --- |
| Arquitectura objetivo | Decisión aprobada para orientar la transición; no prueba ejecución |
| Runtime actual | Comportamiento evidenciado en código/SQL/tests, indicando qué se ejecutó |
| Compatibilidad transicional | Pieza heredada conservada por consumidores todavía existentes |
| Eliminado | Retiro efectivo verificado en un PR; no basta una intención documental |
| Pendiente de migración | Trabajo todavía necesario y su área responsable |

Después de PR 01: cerrar el contrato de identidad humana/técnica, permisos,
sucursal y deployment; reconciliar CORE-EF y documentación afectada; migrar
contexto/SQL/runtime por incrementos; adaptar Flet, bootstrap y deployment;
validar regresión y cerrar estado/documentación. Las dependencias concretas y
el paralelismo se fijan en cada PR, sin mezclar dominios por conveniencia.

PR #540 y #541 están cerrados sin merge: sus políticas propuestas no son norma
vigente y no se reincorporan automáticamente. PR #533 sigue abierto/Draft y no
se modifica: su contenido útil se reconciliará en el PR Comercial posterior,
preservando reglas económicas. Sus prerrequisitos portables/Sync no se trasladan
automáticamente al producto central; esto no implementa ni cierra #427/#534.

## 11. Definición de terminado de la migración

El PR final hacia `main` sólo procede cuando se verifique:

1. Norma coherente: documentos vigentes migrados o delimitados sin contradicción
   activa; ninguna feature central obligada a replicarse.
2. Identidad/contexto: usuario, permisos, sucursal e identidad técnica definidos
   e implementados; un backend puede atender sucursales autorizadas sin réplicas.
3. Backend: dominios ya implementados compatibles con autoridad única y sin
   blockers de seguridad, concurrencia, integridad o integración funcional.
4. Flet: operación remota por HTTPS con auth real, contexto y errores de red.
5. Regresión: suites pertinentes ejecutadas y compatibilidad necesaria preservada;
   infraestructura retenida no habilita bases de negocio autoritativas paralelas.
6. Datos/deployment: creación limpia de DB, seeds y configuración reproducibles;
   recuperación definida según la presencia efectiva de datos útiles al corte.
7. Estado final: documentación/roadmap/runtime alineados y pendientes funcionales
   restantes explícitos; no se declara completado el producto por centralizarlo.

Antes del cierre, incorporar los cambios relevantes de `main`, resolver conflictos
semánticos, repetir gates afectados y retirar la excepción temporal de workflow
una vez que deje de ser necesaria. La arquitectura central permanece vigente
tras el merge final; no depende del nombre de la rama. Eliminar la rama temporal
después de integrar y verificar el resultado.

Antes del merge final, abandonar la transición deja `main` intacto. Después,
recuperación de código/configuración y reconstrucción de DB sólo son suficientes
mientras no existan datos útiles; si los hay, el rollback requiere preservarlos.
No reactivar múltiples autoridades escribibles como mecanismo de recuperación.
