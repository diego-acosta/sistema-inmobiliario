# PROJECT-STATUS — Estado operativo del proyecto

Actualizado: 2026-09-03
**Repositorio:** `diego-acosta/sistema-inmobiliario`

## 1. Propósito

Este documento resume el estado operativo verificable del proyecto para retomar trabajo desde un chat nuevo, Codex Web u otro agente sin depender de memoria conversacional. No reemplaza la arquitectura formal ni los issues/PRs de GitHub: orienta qué revisar primero y qué no asumir.

## 2. Regla de prevalencia

Ante cualquier duda o contradicción, aplicar este orden:

1. `AGENTS.md`.
2. Arquitectura formal en `backend/documentacion/DEV-ARCH/`.
3. SQL real en `backend/database/`.
4. Implementación real: routers, schemas, services y repositories en `backend/app/`.
5. Tests reales en `backend/tests/`.
6. Issues y PRs vigentes en GitHub.
7. Documentación histórica o de diseño, solo si coincide con lo anterior.

Todo dato no verificado debe marcarse como `NO CONFIRMADO`.

## 3. Resumen general

| Frente | Estado verificable | Issue/epic principal | Último PR relevante verificado | Próximo foco |
| --- | --- | --- | --- | --- |
| A — Comercial / Financiero | Activo. #425 y #426 están completados; PR #531 materializó la consulta read-like del primer vencimiento sugerido. Venta directa, PPV2 actual y materialización financiera tienen runtime; PR #422 conserva la fuente de `EMITIDA`/`PROYECTADA`. | #427–#429, #423 y #430/#431 conforman el roadmap restante; #423 sigue bloqueado por los incrementos de soporte. #534 coordina las dependencias portables del grafo PPV2. | PR #531 mergeado (#426); PR #526 mergeado (#486); #425 cerrado. | Continuar #427 → #428/#429 → #423 → #430/#431, preservando #534 como coordinación portable. |
| B — Administrativo | #407–#412 y #482–#486 implementados. PR #526 completó el Sync portable del calendario comercial; #508/PR #509 materializó `usuario.uid_global` y #510/PR #521 su replicación portable. | #461 mantiene la migración de identidad humana; roles/scope conservan adopción parcial. | PR #526 mergeado (#486); PR #506 mergeado (#485); PR #521 mergeado (#510). | Preservar el calendario como owner Administrativo y extender Bearer/autorización sin ampliar legacy. |
| Personas | Runtime amplio para Persona, documentos estructurados, domicilios, contactos y relaciones; conserva adopción parcial de seguridad, lifecycle, CAS e idempotencia. | Deuda legacy transversal y lifecycle/deduplicación pendientes. | Verificar PRs por capacidad antes de retomar. | No confundir Persona con Usuario; migrar incrementalmente sin ampliar `X-Usuario-Id`. |
| Inmobiliario | Runtime amplio para Inmueble/UF, edificación, disponibilidad, ocupación y servicios. Sync portable, lifecycle y seguridad siguen parciales. | Pendientes de consistencia, portabilidad y migración legacy. | Verificar PRs por capacidad antes de retomar. | Mantener ownership de disponibilidad/ocupación y no usar `terreno` como aggregate nuevo. |
| Locativo | Existe el flujo solicitud/reserva/contrato, activación financiera y entrega/restitución básica. Garantías, lifecycle y Sync portable siguen parciales. | #519 abierto para entrega/restitución portable; #282 conserva el patrón contextual de partes. | Verificar PRs por capacidad antes de retomar. | Migrar la frontera Locativo–Inmobiliario sin transportar PK locales. |
| Operativo | Existen sucursal, instalación, configuración local y caja básica; #456 incorporó el resolver local read-only. Arqueo, jornada, fecha operativa e integración financiera no están completos. | #248, #256–#258 y #365 abiertos. | #456 completado. | `LOCAL_INSTALLATION_CODE` es default-deny; completar caja/jornada sin absorber ownership Financiero. |
| Transversal — CORE-EF / Técnico | #469/#470 están completados. #511 está cerrado y PR #512 mergeado: `PENDING_DEPENDENCY`, retry, retained envelope, operation scope y fencing están materializados; no incorporan scheduler productivo definitivo. #510/PR #521 reutiliza esa infraestructura para `administrativo.usuario`. | #402 y #507 están cerrados/completados; #461 permanece abierto y separado. #522 está abierto: no bloquea el MVP humano de Tarea y es requerido antes de automatización. | PR #512 mergeado (#511); PR #521 mergeado (#510). | Integrar consumers futuros mediante sus dominios dueños; resolver #522 antes de origen `SISTEMA`. |
| Gestión Operativa — Tareas | DEV-ARCH y DER del MVP humano están cerrados: #523/PR #524 y #528/PR #529 mergeados. No existen SQL, API, runtime ni tests GOP. | #527 conserva el backlog post-MVP. #522 no bloquea el MVP humano y sí es requerido antes de `origen = SISTEMA`. | PR #529 mergeado (#528); PR #524 mergeado (#523). | Producir DEV-SRV GOP; DEV-API y SQL/runtime/tests son posteriores. |
| Documental | Existen diseño, numeración/datos estructurados y SQL preparatorio disperso; no existe un subsistema de archivos. | Sin storage, upload/download, autorización documental ni Sync binario. | Sin PR de runtime documental integral. | Definir un contrato mínimo antes de implementar; dato estructurado no equivale a documento digital. |
| Analítico | DEV-ARCH/DEV-SRV documentan un dominio read-only; no existen router, SQL analítico, views/marts, KPIs ni tests propios. | Sólo hay queries operativas reutilizables en dominios productores. | Sin PR de runtime analítico integral. | Definir MVP, ownership, scope y corte; query agregada no equivale a Analítico. |

## 4. Reglas para trabajo paralelo

- Mantener PRs pequeños y trazables a un issue.
- No mezclar dominios en un mismo incremento salvo orquestación explícita y verificada.
- Separar `Comercial` de `Financiero`: Comercial gobierna compraventa; Financiero gobierna deuda, pagos, imputación, índices e indexación.
- Separar `Administrativo` de `Operativo`: Administrativo gobierna usuarios, seguridad, configuración y auditoría; Operativo gobierna sucursales, instalaciones y caja operativa.
- Mantener explícito: `USUARIO` ≠ `PERSONA`, `SUCURSAL` ≠ `INSTALACION`, rol de seguridad ≠ rol de participación, caja operativa ≠ movimiento financiero.
- Todo endpoint write nuevo o modificado debe nacer con decisión CORE-EF según `AGENTS.md`.

## 4.1 Infraestructura transversal CORE-EF

#469 quedó implementado y validado mediante los PR #471 (merge commit
`ba0b13f1443ec119f527eeb69cd559971148800d`) y #472 (merge commit
`731db8c562168dca925d76b90d0ebb278b715ed8`). La persistencia durable ya
existe en `public.operacion_idempotente`: es un ledger local, inmutable y no
sincronizable de receipts completados, con `UNIQUE(op_id)` global y contrato
físico de 17 columnas.

La evidencia técnica de cierre registrada para #469 comprende:

- PostgreSQL 16.14: reset DEV/TEST exitoso, suite focal y regresión relacionada
  verdes; el PR #472 reportó `120 passed, 3 skipped, 1 warning`.
- PostgreSQL 18 real: suite focal con `122 passed, 1 skipped, 0 failed`; el único
  skip corresponde a `test_pg16_sin_conenforced_reejecuta_patch`. La inspección
  física confirmó 8 CHECK, 10 NOT NULL, 1 PRIMARY KEY y 1 UNIQUE; el conteo
  contractual `contype IN ('c','f','p','u')` es 13. La regresión relacionada
  reportó `102 passed`.
- Auditoría adversarial posterior al merge de #472: sin blockers ni findings
  materiales adicionales dentro del threat model y sin false negatives
  materiales demostrados del preflight.

#470 incorpora sobre ese contrato físico el runtime reusable de
`claim → EXECUTE | REPLAY | CONFLICT → complete`: canonicalización RFC 8785 v1,
SHA-256, lock transaccional por `op_id`, lookup exacto, replay del snapshot
durable y persistencia mediante la misma `Session`, sin commits ni rollbacks
internos. La decisión de conflicto queda ordenada como `COMMAND → TARGET →
PAYLOAD`, y `UNIQUE(op_id)` permanece como defensa técnica final.

#402 está cerrado/completado. El recorrido completado es `#469 ✅ → #470 ✅
→ #412 ✅`. #412 implementa el primer consumidor productivo: usa directamente `claim_operation` y
`complete_operation`, replay durable desde el ledger y una sola transacción para CAS,
outbox y receipt. #461 permanece abierto como migración transversal separada.

## 4.2 Gestión Operativa — Tareas y seguimiento interno

Estado documental verificable: #489 y la etapa pre-DER están cerrados/completados.
`Tarea` es el concepto principal del dominio `gestion_operativa`, separado de
`operativo`. #523 está cerrado/completado y PR #524 mergeado; #528 está
cerrado/completado y PR #529 mergeado, materializando el DER del MVP inicial.
No existen todavía SQL, migrations, API,
router, schema, service, repository, frontend ni tests runtime de Tarea.

#491 está completado por PR #494. `GOP-FREEZE-001` congela que toda
mutación funcional compartida de Tarea es `COMMAND_WRITE_NEGOCIO +
SINCRONIZABLE`, incluida la creación manual o `origen = SISTEMA`, cambios de
contenido, asignación, prioridad, fecha objetivo, estados, completar, cancelar,
reabrir y agregar comentario. Una eventual baja lógica futura se clasifica
`COMMAND_WRITE_TECNICO + SINCRONIZABLE`, sin crear la operación. No se identificó
un command funcional `LOCAL / NO SINCRONIZABLE`; las consultas son
`QUERY_READLIKE` y leer no genera outbox.

La estrategia congelada exige los headers técnicos comunes `X-Op-Id`,
`X-Sucursal-Id` y `X-Instalacion-Id` para los futuros commands sincronizables.
Los dos últimos expresan contexto/procedencia y no definen `Tarea.id_sucursal`;
ninguno autentica personas. Los commands humanos derivan identidad únicamente de
Bearer → `get_authenticated_principal` → `AuthenticatedPrincipal.id_usuario` y
no usan `X-Usuario-Id`. La autenticación/autorización técnica de procesos
`origen = SISTEMA` permanece no congelada y no se inventa en #491 ni #492.

Las creaciones no usan `If-Match-Version`; toda mutación ordinaria del snapshot
de Tarea existente/versionada sí debe exigirlo. #493 congela la excepción
específica: agregar comentario es un append independiente, no requiere
`If-Match-Version` de Tarea y no incrementa `Tarea.version_registro`.
Idempotencia durable reutiliza #469/#470 y el patrón
productivo validado por #412/PR #478: mismo `op_id` compatible hace replay del
snapshot durable, diferencias materiales producen conflicto y un error previo al
commit permite reejecución. GOP no crea ledger paralelo.

Mutación funcional, historial transaccional aplicable, outbox y receipt durable
comparten una transacción local. La recepción remota usa inbox o equivalente,
deduplica por `op_id`, valida `uid_global`, compara `version_registro`, aplica la
baja lógica y persiste rechazos/conflictos sin sobrescritura silenciosa. No se
adopta LWW por timestamps. `deleted_at` sigue siendo distinto de `CANCELADA` y
una eventual baja debe propagarse, sin endpoint DELETE ni purga. Snapshot,
historial, outbox, inbox y ledger continúan separados.

Blockers internos de `GOP-FREEZE-001`:

- #6 — estrategia de sync: resuelto documentalmente por #491 / PR #494.
- #7 — comentario / `version_registro`: resuelto documentalmente y cerrado/completado por #493 / PR #505.
- #10 — identidad canónica interinstalación: documentalmente resuelto por #492;
  #511 materializa el runtime Técnico de la política retryable transversal y #510
  lo reutiliza para `administrativo.usuario`. #492 está cerrado/completado
  y #507 cerró la auditoría transversal previa a DEV-ARCH-GOP.

#492 congela `uid_global` de Tarea como identidad distribuida y reserva el futuro
ID local sólo para joins/FKs. Creador, responsable y actores de
historial/comentario deben viajar por una identidad global de usuario provista
por Administrativo. #508/PR #509 materializó `usuario.uid_global` y su resolver
local; #510/PR #521 materializó su replicación portable para altas y bajas, sin
transportar la PK local. Sucursal
e instalación ya poseen `uid_global`: la primera referencia scope funcional y
las segundas expresan procedencia técnica, sin confundir `Tarea.id_sucursal` con
`X-Sucursal-Id` ni convertir instalación en scope.

La recepción identifica Tarea y referencias sólo por identidades portables y las
resuelve a PK locales antes de persistir. Una referencia requerida temporalmente
no resoluble no genera placeholders ni copia PK remota: Técnico congela
`PENDING_DEPENDENCY` como espera retryable del mismo registro, con claim
atómico, backoff controlado y trazabilidad, sin aplicación parcial. `REJECTED`
permanece terminal y la mera ausencia temporal no es `CONFLICTO`. **Estado
histórico previo a #511:** el runtime entonces auditado no reabría el mismo
`(event_id, consumer)` ni tenía lease o payload retenido. Desde #511 existen el
lifecycle, claim/reclaim y entry point reusable, pero no un scheduler productivo
definitivo ni integración automática de consumers GOP futuros. #492 está
cerrado/completado; su cierre documental no diseñó DTO, evento, DER, SQL, API ni
runtime GOP. La autoría portable sigue el contrato #492. #493
congela `Comentario.uid_global` propio, único, inmutable y no reutilizable, y su
`version_registro` CORE-EF, que nace en 1 y normalmente permanece en 1 durante el
MVP append-only. La autorización funcional se resuelve en origen; el receptor no
la reevalúa contra relaciones mutables posteriores y preserva contexto causal
suficiente para RN-TEC-012. Un comentario confirmado antes de una baja lógica
converge aunque la baja llegue primero al receptor, sin restaurar la Tarea ni
limpiar `deleted_at`; un intento posterior a la baja no queda habilitado por esa
regla. Si comentario y baja son concurrentes sin relación causal, ambos efectos
convergen a Tarea dada de baja más comentario presente, sin LWW ni conflicto
automático. Agregarlo no incrementa `Tarea.version_registro` ni requiere
`If-Match-Version` de Tarea; la atomicidad futura abarca comentario/outbox/receipt.
La etapa pre-DER, arquitectura y DER están cerradas: #489, #490–#493, #507,
#523 y #528 están cerrados/completados; PR #524 y PR #529 están mergeados,
`DEV-ARCH-GOP-001` y el DER GOP están vigentes. #527 conserva el backlog
post-MVP. El siguiente incremento es DEV-SRV GOP; DEV-API y SQL/API/runtime/tests
permanecen en incrementos posteriores. #522 continúa abierto, no bloquea el MVP
humano y debe resolverse antes de automatización.

## 5. Frente A — Comercial / Financiero

### 5.1 Estado

Activo. La integración de venta histórica de #406 y la corrección transaccional
de #415 están integradas. Los cambios de #418/#420 y la alineación de #421/#422
también están presentes en `main`:

- PR #432 está mergeado y cerró #424 como completado. El documento `INT-FIN-005`
  es la fuente contractual vigente para #423 y #425–#431: una base común por
  venta, valor base nullable, período objetivo persistido por obligación y
  selección exacta sin fallback materializable. La implementación runtime de ese
  contrato permanece pendiente.
- PR #422 está mergeado y mantiene `definitive_amount_materialized` como fuente de
  verdad de `EMITIDA`/`PROYECTADA`; #424 no reabre ni modifica esa lógica.

- PR #390 corrigió la emisión PPV2: los importes definitivos nacen `EMITIDA`; una cuota indexada sin importe materializado nace `PROYECTADA`; la aplicación posterior la pasa de `PROYECTADA` a `EMITIDA`. La demo PPV2 quedó aislada transaccionalmente en tests.
- PR #392 alineó la suite de reservas con el contrato vigente, eliminó el patch DDL heredado de los tests y corrigió los fixtures de roles. Cerró #391.
- PR #394 incorporó la auditoría contractual de #374; no implementó ni cerró #374.
- PR #397 expuso catálogo de índices y valor publicado aplicable por fecha como queries read-only. Cerró #395 y desbloqueó #374.
- #404 implementó dentro de #406 la integración del catálogo y del valor aplicable
  para los tramos indexados; #374 permanece abierto y no se considera cerrado por
  esa integración.
- PR #406 está mergeado. Su validación funcional posterior a la integración de
  #415 descubrió #418, cuya corrección está integrada en el historial de `main`.
- Issue #416, ahora cerrado, documentó el defecto observado: el command podía responder `200`
  después de liberar sólo un savepoint y la sesión revertía luego silenciosamente
  la venta al cerrarse.
- PR #415 está mergeado y corrige tanto la confirmación directa como la confirmación desde reserva:
  el application service orquestador conserva el savepoint cuando existe una
  transacción previa y realiza un commit exterior explícito antes de completar la
  respuesta exitosa. Venta, plan, obligaciones, disponibilidad y outbox comparten
  la misma transacción.
- La suite backend completa ejecutada sobre el cambio runtime de #415 informó
  `1763 passed, 1 warning`; éste es el baseline verificable de este corte.
- La validación transaccional quedó aprobada. #422 corrigió la regresión temporal
  posterior y restauró la materialización como fuente de verdad.
- #346, #348, #349, #365, #374 y #405 conservan frentes previos; verificar su
  estado actual en GitHub antes de retomarlos.
- #424 está cerrado como completado por el merge de PR #432. #423 y #425–#431
  conservan la implementación runtime pendiente; #425 es el próximo incremento y
  #423 sigue bloqueado hasta contar con los incrementos de soporte.

Implementación relevante verificada:

- Routers: `backend/app/api/routers/comercial_router.py`, `backend/app/api/routers/financiero_router.py`.
- Schemas: `backend/app/api/schemas/comercial.py`, `backend/app/api/schemas/financiero.py`.
- Services: `backend/app/application/comercial/services/`, `backend/app/application/financiero/services/`.
- Repositories: `backend/app/infrastructure/persistence/repositories/`.
- SQL: Plan Pago Venta V2, bloques, indexación y corridas en `backend/database/`.
- Tests: venta completa, Plan Pago Venta V2, preview, preparación, aplicación de indexación V2 y E2E comercial-financiero en `backend/tests/`.

### 5.2 Issues activos

- #425 — completado; calendario comercial Administrativo materializado y
  sincronizado por #486/PR #526.
- #426 — cerrado/completado por PR #531: vencimiento inicial sugerido Comercial.
- #427–#429 — base común, materialización pendiente y período objetivo;
  incrementos posteriores a #426.
- #423 — selector financiero definitivo por período objetivo exacto; permanece
  bloqueado hasta que existan los incrementos de soporte.
- #430/#431 — frontend e integración completa, posteriores a los incrementos base.

- #346 — integración con importación de ventas históricas.
- #348 — frente amplio de frontend de indexación y corridas.
- #349 — corrección y reversión avanzada.
- #365 — definición transversal de fecha operativa.
- #374 — mejorar configuración de tramos indexados en Venta completa V3; abierto y desbloqueado por #397.
- #405 — frente previo de venta histórica; verificar vigencia y dependencias antes
  de retomarlo frente al roadmap #423/#425–#431.
- #59 continúa abierto como issue histórico y amplio de confirmación desde reserva; revisar su vigencia antes de usarlo como próximo incremento.

### 5.3 Últimos PR relevantes

- #432 `[Docs] Cerrar contrato mensual de indexación PPV2 (#424)` — mergeado;
  cerró #424 como completado y estableció `INT-FIN-005` como fuente contractual
  vigente. Fue exclusivamente documental y no originó una nueva ejecución de la
  suite backend.
- #531 `feat(comercial): resolver vencimiento inicial sugerido (#426)` —
  mergeado; cerró #426 y materializó la consulta `QUERY_READLIKE` por
  `fecha_venta` explícita, con calendario Administrativo y clamping de mes corto.
- #415 `[Backend/CORE-EF] Persistir atómicamente confirmación completa de venta` —
  mergeado; corrigió la frontera transaccional backend de confirmación directa y
  desde reserva y permitió aprobar la validación transaccional.
- #406 — mergeado; integró en frontend el flujo de venta histórica. Su validación
  funcional descubrió #418.
- #397 `feat(financiero): exponer catálogo de índices y valor publicado aplicable por fecha` — mergeado 2026-07-24.
- #394 `docs(frontend): documentar brecha contractual de tramos indexados` — mergeado 2026-07-24.
- #392 `feat(comercial): restaurar contrato y suite de reservas de venta` — mergeado 2026-07-24.
- #390 `fix(financiero): alinear ciclo de obligaciones PPV2 con emisión` — mergeado 2026-07-23.
- #388 `docs(financiero): documentar semántica de estados en Plan Pago V2` — mergeado 2026-07-22.

### 5.4 Próximo foco recomendado

Para el roadmap contractual de indexación PPV2, #425 y #426 están completados.
El orden restante recomendado es
`#427 → #428/#429 → #423 → #430/#431`.
#423 permanece bloqueado hasta que sus incrementos de soporte estén disponibles.
Cada issue permanece separado y debe cumplir CORE-EF cuando incorpore commands.

#374 permanece como frente funcional y #365 como deuda transversal. El frontend
solo presenta respuestas y arma el command comercial: no calcula indexación, no
infiere valores y no duplica reglas financieras.

### 5.5 Decisiones vigentes

- Comercial conserva ownership de la venta.
- Financiero conserva ownership de obligaciones, índices, ajustes, saldos y corridas.
- La orquestación no traslada ownership financiero al dominio Comercial.
- El application service orquestador es dueño único del commit y rollback del
  command completo; los repositories no realizan commits parciales de sus etapas.
- La respuesta exitosa de confirmación completa sólo se emite después del commit
  exterior explícito.
- Venta, plan, obligaciones, disponibilidad y outbox se confirman o revierten en
  una única frontera transaccional.
- Una venta histórica puede generar obligaciones directamente indexadas si el valor aplicable ya está publicado.
- No se aplica una corrida inmediata sobre obligaciones que ya nacieron indexadas.
- Las obligaciones no indexadas y las indexadas con importe definitivo materializado nacen `EMITIDA`; las indexadas sin valor materializado nacen `PROYECTADA`.
- La aplicación posterior de una corrida pasa una obligación `PROYECTADA` a `EMITIDA` y no altera los demás estados contractuales.
- Las cuotas históricas exigibles sin índice válido bloquean toda la confirmación.
- Las cuotas futuras pueden persistirse como `PROYECTADA` sin ajuste materializado.
- `PROYECTADA_SIN_INDICE` es una clasificación de cálculo/preview, no un estado físico de `obligacion_financiera`.
- `fecha_corte` es un dato de negocio explícito.
- Mientras #365 siga abierto, la fecha de corte presentada por frontend conserva
  provisionalmente la referencia local vigente; no redefine la fecha operativa.
- El uso de `date.today()` para detectar historicidad es provisional hasta resolver #365.
- Publicación, preparación y aplicación de una corrida son operaciones separadas.
- El catálogo de índices y la resolución de valor aplicable pertenecen a Financiero y son `QUERY_READLIKE`: no requieren headers write, no escriben ni recalculan en frontend.
- Una respuesta de valor aplicable con `data: null` significa que el índice activo existe pero no tiene valor aplicable; no se infiere un valor.
- Toda venta indexada futura comparte una base común; un tramo nuevo o no indexado
  intermedio no reinicia índice, base ni calendario.
- Período base y valor base son conceptos distintos; la venta puede registrarse
  con período base y valor pendiente.
- Cada obligación indexada futura tendrá período objetivo mensual persistido,
  distinto del vencimiento.
- La materialización definitiva exige valor base y valor publicado exacto del
  período objetivo, con objetivo mayor o igual que base. Un valor menor devuelve
  `INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO`; no se materializa como componente
  negativo ni se clasifica simplemente como proyección.
- El contrato futuro exige un único valor publicado por índice y período mensual;
  duplicados históricos deben auditarse y sanearse, nunca desempatarse
  arbitrariamente.
- Los bloques no indexados no poseen ni consumen períodos objetivo; un tramo
  indexado posterior deriva los suyos del calendario común y sus vencimientos
  sugeridos originales.
- Vencimiento y período objetivo se persisten separados, pero se relacionan: el
  cambio de mes desplaza el objetivo y un cambio de día dentro del mes no lo hace.
- El último valor anterior solo puede ser informativo y no cambia `PROYECTADA` a
  `EMITIDA`.
- El selector vigente `fecha_valor <= fecha_vencimiento` es compatibilidad heredada
  hasta #423/#429; no es el contrato definitivo fijado por #424.
- La validación de disponibilidad y sus estados incompatibles no se relajan para
  permitir ventas históricas.
- No se calculan importes ni indexación en frontend.
- `cliente_comprador` es semántica funcional comercial aunque tenga persistencia heredada.
- `persona` es identidad base; no define condición de cliente ni comprador.
- `analitico` es read-only y no debe recalcular ni persistir lógica financiera.

### 5.6 Pendientes y orden sugerido

- #425 y #426: completados; no reabrir sus alcances dentro de los siguientes
  incrementos.
- #427 → #428/#429: continuar con base común, valor pendiente, materialización y
  período objetivo, sin combinar alcances.
- #423: reemplazar el selector heredado por resolución exacta después de contar con
  el soporte de período objetivo; hasta entonces permanece bloqueado.
- #430/#431: frontend e integración completa después de los incrementos backend.

- #405: verificar vigencia antes de retomarlo; no desplaza el roadmap específico
  definido por #424.
- #374: permanece abierto como frente funcional de Venta completa V3.
- #348: permanece como frente amplio; ordenar después la visualización read-only de indexación y corridas.
- #365: deuda transversal que debe avanzar antes de ampliar importaciones históricas, procesos batch o escenarios multiinstalación.
- #346: pendiente vigente, pero requiere auditoría específica del importador y posible relación con #365.
- #349: pendiente vigente de alto riesgo; debe auditarse y dividirse antes de implementar.

### 5.7 Fuera de alcance del próximo incremento

- Importación masiva.
- Calcular, interpolar, proyectar o inferir valores de índice en frontend.
- Preparar o aplicar corridas desde la UI.
- Publicar o editar índices.
- Reversión y corrección avanzada.
- Cuotas pagadas o parcialmente pagadas.
- Ajustes negativos.
- Rediseñar pagos, imputaciones, recibos o mora.
- Resolver #365 dentro del PR de frontend.
- Rediseñar el dominio Financiero.
- Crear caja operativa, recibos fiscales persistidos o documental real como parte de este frente.
- Mover lógica de cálculo financiero a Comercial o al frontend.

### 5.8 Documentos relevantes

- `backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`.
- `backend/documentacion/DEV-SRV/dominios/comercial/`.
- `backend/documentacion/DEV-SRV/dominios/financiero/`.
- `backend/documentacion/DEV-API/dominios/comercial/DEV-API-COMERCIAL.md`.
- `backend/documentacion/DEV-API/dominios/financiero/`.
- `frontend/flet_app/documentacion/AUDITORIA-ISSUE-374-TRAMOS-INDEXADOS.md`.
- `backend/documentacion/CORE-EF/`.
- `backend/documentacion/DECISIONES/integracion/INT-FIN-*.md`.
- `backend/documentacion/DECISIONES/integracion/INT-FIN-005-contrato-indexacion-ppv2.md`.

### 5.9 Regla de continuidad

Antes de continuar #405 o ampliar la venta histórica:

1. tomar `INT-FIN-005` como fuente contractual vigente de los incrementos PPV2 mensuales;
2. tratar #425/#426 como completados y continuar `#427 → #428/#429`, sin combinar alcances;
3. mantener #423 bloqueado hasta contar con ese soporte e implementarlo después
   sobre período objetivo persistido, sin fallback materializable;
4. mantener `INVALID_DISPONIBILIDAD_STATE` y conflictos vigentes;
5. no calcular indexación ni importes en frontend;
6. mantener #365 abierto hasta definir la fecha operativa transversal;
7. abordar #430/#431 solo después de contar con los contratos backend necesarios;
8. marcar `NO CONFIRMADO` cualquier dato sin evidencia.

## 6. Frente B — Administrativo

### 6.1 Estado

Activo incremental. GitHub muestra el epic #249 abierto: `[Epic] Administrativo: usuarios, roles, permisos y configuración`.

Sub-issues con estado verificable:

- #259 `Administrativo: usuarios del sistema — modelo y CRUD base` cerrado/completado.
- #260 `Administrativo: roles de seguridad y permisos base` cerrado/completado.
- #261 `Administrativo: asignación de roles a usuarios` cerrado/completado.
- #262 `Administrativo: alcance operativo por sucursal/instalación` cerrado/completado.
- #263 `Administrativo: configuración general del sistema` abierto.
- #407 implementó el inventario read-only y #408 congeló `parametro_sistema` como definición y `valor_parametro` como fuente canónica de valores. #409–#410 materializaron el soporte `ENTERO`/`GLOBAL` y CORE-EF físico; #411 implementó la consulta individual y #412 el command update-only. #413 es el cierre documental vigente; #263 continúa abierto hasta su review y merge.
- #409 incorpora sólo el tipo estructural `ENTERO` y el alcance estructural
  `GLOBAL`, con descripciones contractuales, reset DEV/TEST y tests PostgreSQL.
  No crea claves ni valores funcionales de #425.
- Estado histórico al cierre de #410: quedó preparada exclusivamente la infraestructura SQL CORE-EF. Estado vigente: #482/PR #487 dejó materializadas las dos definiciones y la raíz física; #483 agregó el GET y la resolución temporal; #484/PR #504 implementó bootstrap y `calendario_comercial_creado`; #485/PR #506 implementó programación append-only y `calendario_comercial_programado`; #486/PR #526 completó el consumer y sync portable.
- #469 y #470 completaron el ledger y runtime transversal de idempotencia durable; #412 es su primer consumidor productivo. PR #478 implementó endpoint, permiso, vínculo, seed técnico controlado y EVT-ADM-060. #402 está cerrado/completado.
- #438 agrega a `parametro_sistema` la metadata física `exponible_api_administrativa` y `es_sensible`, con política default-deny (`false`/`true`) y constraint que impide exposición en claro de definiciones sensibles. #411 implementa únicamente el GET individual del valor GLOBAL marcado vigente para definiciones exponibles y no sensibles, con 404 indistinguible para inexistente/no exponible/sensible, 409 para no GLOBAL, estado `SIN_VALOR` y tipado estricto `ENTERO`. #441 agrega `editable_administrativamente` como metadata física independiente, default-deny (`false`), no editable por API y habilitable sólo por migración versionada. Estado vigente: #412 está implementado, #482 habilita explícitamente la metadata de sus dos definiciones calendario, #484 creó sus valores funcionales iniciales y #485/PR #506 completó las nuevas vigencias append-only; la resolución agregada temporal queda implementada por #483, sin resolver #435.
- #264 `Administrativo: catálogos maestros e ítems configurables` abierto.
- #265 `Administrativo: auditoría administrativa básica` abierto.
- #368 `CRUD write de catálogos maestros` cerrado/completado.
- #393 `Definir y congelar el ciclo de vida físico de item_catalogo` cerrado/completado.
- #399 `CRUD write de item_catalogo` cerrado/completado por commit `e1efa0a`.
- #508 / PR #509 materializó `usuario.uid_global` como identidad portable propia,
  estable e inmutable y agregó su resolver local, manteniendo `id_usuario` como PK local.
- #510/PR #521 materializó `usuario_creado` y `usuario_desactivado` sobre el
  consumer `administrativo.usuario`, preservando UID y versión con PK local
  independiente. Credenciales y sesiones continúan locales/no sincronizables por #455.

Incrementos completados en catálogos:

- #360 / PR #362: consultas read-only de `catalogo_maestro` e `item_catalogo`.
- #363 / PR #364: soporte CORE-EF y restricciones SQL para catálogos.
- #368 / PR #370: alta, modificación y baja lógica de `catalogo_maestro`, con idempotencia, optimistic locking, outbox y errores tipados.
- #393 / PR #396: estados físicos `ACTIVO` e `INACTIVO`, estado inicial `ACTIVO`, `NOT NULL`, `CHECK`, diferenciación entre inactivación y baja lógica y código no reutilizable después de baja.
- #399: CRUD write de `item_catalogo` implementado.

### 6.2 Epic o issue principal

- #249 `[Epic] Administrativo: usuarios, roles, permisos y configuración`: abierto.

### 6.3 Issues activos

Los frentes activos verificables son:

- #263 — configuración general.
- #264 — catálogos maestros e ítems configurables.
- #265 — auditoría administrativa básica.

Dentro de #264, el CRUD write de ítems quedó implementado por #399. En configuración, #409 elimina el bloqueo físico de tipo/alcance, #410 prepara `valor_parametro` con CORE-EF SQL, #438/#441 preparan metadata segura, #411/#412 implementan read y write individual, y #482 materializa las dos definiciones calendario, su rango, permiso y raíz física. El GET agregado y el query service temporal están implementados por #483; #484 creó los valores funcionales iniciales y el write de bootstrap, #485/PR #506 completó las nuevas vigencias append-only y #486/PR #526 completó el consumer y sync portable. #425 está cerrado.

### 6.4 Decisiones vigentes

- `usuario` pertenece a Administrativo y no es `persona`.
- `usuario.uid_global` es la identidad distribuida autoritativa; `id_usuario`
  continúa siendo PK local. #510 replica únicamente `usuario_creado` y
  `usuario_desactivado`, sin inferir lifecycle Administrativo inexistente.
- El vínculo usuario-persona, si se implementa, es asociación explícita; no fusiona identidades.
- `rol_seguridad` y `permiso` no son `rol_participacion` ni roles de negocio.
- `usuario_sucursal` referencia alcance operativo, pero no convierte Administrativo en dueño de `sucursal` o `instalacion`.
- La autenticación mínima ya cuenta con login/sesión (#446) y principal `/seguridad/me` (#447); no hay autorización, OAuth/SSO ni menú dinámico. La migración transversal de endpoints permanece pendiente en #461.
- `catalogo_maestro` ya tiene CRUD write mínimo.
- `item_catalogo` tiene lectura y CRUD write implementados; jerarquías e historial funcional permanecen fuera de alcance.
- Los únicos estados físicos permitidos de `item_catalogo` son `ACTIVO` e `INACTIVO`; su estado inicial es `ACTIVO`.
- `INACTIVO` no equivale a baja lógica: la baja lógica se representa mediante `deleted_at`.
- El command vigente de cambio de estado soporta `ACTIVO` e `INACTIVO`, incluida la transición `INACTIVO → ACTIVO`; la reactivación de una baja lógica sigue `NO CONFIRMADA`.
- El código de ítem no se reutiliza después de baja.
- Los dominios consumidores deciden sus reglas particulares de aceptación de ítems inactivos.
- No migrar enums de otros dominios incidentalmente.
- Todo write administrativo nuevo debe cumplir CORE-EF desde el inicio. Si usa
  Bearer, deriva identidad exclusivamente de `AuthenticatedPrincipal`; no usa
  `X-Usuario-Id` como identidad. El header histórico permanece sólo en endpoints no
  migrados hasta sus incrementos específicos.
- `parametro_sistema` es la definición canónica y `valor_parametro` la fuente canónica de valores; `configuracion_general` es compatibilidad heredada y `configuracion_local` pertenece a Operativo.
- `ENTERO` y `GLOBAL` son datos estructurales contractuales no editables por API;
  sus consumidores resuelven IDs por código.
- #410 deja preparado el CORE-EF SQL reusable de `valor_parametro` para valores GLOBAL (`id_sucursal` e `id_instalacion` nulos). #482 materializa claves, metadata, rango, permiso y raíz física; #483 implementa la lectura agregada temporal; #484 materializa raíz/pareja iniciales y un único outbox `calendario_comercial_creado`; #485/PR #506 completó la programación append-only y su evento `calendario_comercial_programado`; #486/PR #526 completó el consumer y la integración remota.
- Exposición, sensibilidad y editabilidad son metadata separada de `parametro_sistema`: una lectura de valores sólo puede devolver definiciones explícitamente exponibles y no sensibles; la editabilidad administrativa es independiente, default-deny y no expuesta por #407/#411. #438/#441 no implementaron por sí solos autorización ni writes; #412 los implementa posteriormente y #482 excluye de ese command las dos claves calendario.

### 6.5 Próximo foco recomendado

El CRUD write de `item_catalogo` quedó implementado por #399. Para configuración,
#409 deja disponibles `ENTERO` y `GLOBAL`, #410 prepara el CORE-EF físico de `valor_parametro`, #438/#441 agregan metadata default-deny y #411 expone el read individual GLOBAL marcado vigente. #469/#470 proveen idempotencia durable y #412, implementado por PR #478, es su primer consumidor productivo. #413 cierra únicamente la alineación documental. #482/PR #487 prepara definiciones y raíz física; #483 implementa GET/resolución; #484/PR #504 implementa bootstrap y producer local `calendario_comercial_creado`; #485/PR #506 implementa programación append-only y `calendario_comercial_programado`; #486/PR #526 completa consumer, inbox, reentrega, aplicación remota y E2E. #425 está cerrado. No se mezclan `configuracion_general`, `configuracion_local` ni catálogos.

### 6.6 Fuera de alcance

- Redefinir Personas.
- Implementar Operativo dentro de Administrativo.
- Usar `sucursal` e `instalacion` como si fueran entidades administrativas.
- Crear autenticación real, sesiones o credenciales persistidas sin issue y auditoría previa.
- Declarar outbox, locks o autorización real si no hay evidencia en repository, SQL y tests.
- Implementar jerarquías o historial funcional de ítems; esas capacidades no forman parte del CRUD vigente.
- Implementar defaults avanzados, vigencias o UI de configuración sin incremento específico.

### 6.7 Documentos relevantes

- `backend/documentacion/DEV-API/dominios/administrativo/DEV-API-ADM-001.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/SRV-ADM-005-gestion-de-configuracion-y-parametrizacion.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/EST-ADM.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/RN-ADM.md`.
- `backend/documentacion/CORE-EF/CORE-EF-001.md` y matriz de cumplimiento.
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`.

### 6.8 Últimos PR relevantes

- PR #506: programación append-only del calendario comercial (#485), mergeado; producer transaccional `calendario_comercial_programado`.
- PR #475: runtime transversal reusable de claim/replay/complete (#470), mergeado.
- PR #473: cierre documental de persistencia idempotente (#469), mergeado.
- PR #471: persistencia idempotente transversal (#469), mergeado.
- PR #436 / commit `b11d095`: parametrización estructural #409, mergeado.
- PR #434 / commit `5cd883a`: freeze documental #408, mergeado.
- PR #414 / commit `b8d4ccb`: inventario read-only de definiciones de parámetros (#407), mergeado.
- Commit `e1efa0a`: CRUD write de `item_catalogo` (#399), mergeado.
- #396 `feat(administrativo): definir ciclo de vida de ítems de catálogo (#393)` — mergeado.
- #370 `feat(administrativo): CRUD write de catálogos maestros (#368)` — mergeado.
- #364 `feat(administrativo): preparar catálogos CORE-EF` — mergeado.
- #362 `feat(administrativo): consulta read-only de catálogos e ítems (#360)` — mergeado.

### 6.9 Regla de continuidad

Para continuar #425 después de #485:

1. revisar #263, #407, #408, #425, PR #414 y el estado materializado por #482;
2. releer el freeze Administrativo, DEV-API y SRV-ADM-005;
3. validar nuevamente SQL, implementación y tests reales;
4. mantener `configuracion_local` en Operativo y no usar catálogos como parámetros;
5. no declarar resuelta la semántica contextual futura;
6. preservar #484/PR #504 como bootstrap mergeado con producer local transaccional `calendario_comercial_creado`, #485/PR #506 como programación append-only completada/mergeada con producer `calendario_comercial_programado` y #486 como consumo/sync remoto implementado/validado en PR draft #526; mantener #425 abierto hasta verificar el merge de #486, sin revertir #482 ni la lectura agregada temporal de #483;
7. marcar `NO CONFIRMADO` todo lo no respaldado.

## 7. Dependencias entre frentes

- Comercial/Financiero puede requerir usuarios/sucursales/instalaciones solo como metadatos CORE-EF; eso no habilita cambios administrativos ni operativos dentro del mismo PR.
- Administrativo puede referenciar sucursales/instalaciones para alcance, pero Operativo mantiene ownership de esas entidades.
- Financiero puede consumir ventas y sujetos; no redefine compraventa ni persona.
- Analítico solo lee; cualquier necesidad de persistir o corregir datos pertenece al dominio dueño.

## 8. Frentes en espera

- Operativo: existen trabajos recientes de caja operativa (#325, #327, #331) y epic #248 abierto. No mezclar con Administrativo.
- Importación histórica: #346 abierto; auditar antes de implementar y revisar relación con #365.
- Frontend de indexación V2: #348 abierto; #374 es el incremento inmediato desbloqueado por las queries read-only de #397.
- Reversión/corrección avanzada de indexación V2: #349 abierto; requiere auditoría y división.
- Fecha operativa transversal: #365 abierto; no reabre #345 ni #358.

## 9. Instrucción para nuevos chats y agentes

1. Leer `AGENTS.md` completo.
2. Leer este `PROJECT-STATUS.md`.
3. Leer `CODEX-WORKFLOW.md`.
4. Abrir el issue objetivo y PRs relacionados en GitHub.
5. Validar arquitectura, SQL, routers, schemas, services, repositories y tests.
6. Informar contradicciones antes de implementar.
7. No modificar código si el objetivo es documental.

## 10. Reglas de mantenimiento

- Actualizar este archivo solo cuando cambien frentes activos, issue principal, PR relevante o decisión operativa.
- No convertirlo en copia de la arquitectura; enlazar documentos fuente.
- No declarar estados de GitHub sin verificarlos el mismo día.
- Marcar `NO CONFIRMADO` ante cualquier dato no verificable.
- Mantenerlo breve y apto para lectura inicial de un agente.


## 8. Incremento Administrativo #448 — credencial_usuario SQL

#448 prepara exclusivamente `public.credencial_usuario` mediante ALTER directo incremental: metadata CORE-EF física, constraints, FKs de instalación, índices parciales y triggers SQL. No crea credenciales reales, no modifica `usuario`, no agrega login, logout, sesiones, tokens, outbox ni historial runtime. `hash_credencial` es sensible y usuarios sin credencial no autentican porque no existe runtime de autenticación.

## 9. Incremento Administrativo #449 — primitivas Argon2id

#449 agrega únicamente el helper interno transversal Argon2id v1 para hashing, verificación y detección de rehash de secretos futuros. La política queda fija con `time_cost=3`, `memory_cost=65536`, `parallelism=2`, `hash_len=32`, `salt_len=16` y `type=argon2id`; el algoritmo persistible futuro es `argon2id:v1` y `hash_credencial` deberá ser PHC. No crea ni persiste credenciales, no modifica SQL, no agrega endpoints, no implementa autenticación, login, logout, sesiones, tokens, principal autenticado, outbox ni historial runtime. #450 y #446 siguen pendientes.


## 10. Incremento transversal/Operativo #456 — identidad local

#456 agrega el setting obligatorio `LOCAL_INSTALLATION_CODE` y un resolver reusable que lee una única vez `public.instalacion` por código exacto, clasifica elegibilidad y devuelve un DTO mínimo inmutable. Es soporte transversal read-only: no agrega SQL, endpoint, outbox, lock, credenciales, sucursal ni fallback. #454 y la integración productiva permanecen pendientes.

## 11. Incremento Administrativo #454 — bootstrap local de credenciales

#454 incorpora una CLI TTY-only para crear o resetear credenciales `PASSWORD` de usuarios elegibles. Reutiliza Argon2id y la identidad local existentes, conserva la fila revocada, asegura una única activa/principal mediante locks e índices y permite replay local por `op_id_alta`. No incorpora autenticación, endpoints, sesiones, tokens, outbox, eventos ni sincronización.

## 12. Incremento transversal Administrativo/Seguridad #455

#455 implementa exclusivamente el guardrail transversal de exclusión de credenciales/sesiones: política runtime allowlist/default-deny, rechazo profundo previo a outbox, cierre de worker/dispatcher y sanitización de errores. `credencial_usuario` y la tabla histórica `sesion_usuario` son locales por instalación y no sincronizables. No implementa autenticación, login/logout, sesiones o tokens runtime, autorización ni sincronización de hashes; #446 y los incrementos posteriores permanecen fuera de alcance.

## 13. Incremento Administrativo/Seguridad #446 — login y sesión local revocable

#446 implementa login por `usuario.login` y Argon2id, sesión persistida local con
bearer opaco (sólo digest SHA-256 en DB), TTL absoluto de ocho horas y logout
idempotente. No agrega historial de acceso, outbox, sync, rehash, contadores de
intentos, sucursal seleccionada, principal ni autorización. #447 permanece como
siguiente incremento para interpretar el bearer y construir el principal.


## 14. Incremento Administrativo/Seguridad #447 — principal autenticado mínimo

#445 y #446 están completados. #447 implementa exclusivamente `AuthenticatedPrincipal`, la dependency read-only `get_authenticated_principal` y `GET /api/v1/administrativo/seguridad/me` sobre el SQL existente. `Authorization` es la única fuente de identidad humana; `X-Usuario-Id` queda deprecado pero se conserva en endpoints heredados hasta #461. Sesiones y secretos continúan locales/no sincronizables. No se incorporan roles, permisos ni autorización: #443 permanece pendiente; #461 también permanece pendiente y no se declara autenticación transversal de endpoints.

## 15. Incremento Administrativo/Seguridad #443 — autorización GLOBAL reusable

#444 está completado. **Estado histórico al cierre de #443:** ese incremento incorpora únicamente infraestructura read-only reusable:
dependency sobre el principal canónico de #447, service default-deny, repository GLOBAL
y contratos sanitizados 403/500. No protege rutas productivas ni declara autorización
transversal. No agrega SQL, permisos funcionales, headers CORE-EF, writes, outbox, sync
o contexto de sucursal/instalación. En ese corte #461, #412 y #435 permanecían pendientes;
el estado vigente de #412 y #482 se documenta en el frente Administrativo anterior.
#463–#467 conservan la deuda Ruff histórica como frente técnico separado.

## 16. Incremento Técnico/Sync #511 — PENDING_DEPENDENCY

#511 está cerrado y PR #512 mergeado. Materializa el Frente B transversal de #507: `inbox_event` retiene envelope y procedencia, incorpora lifecycle `PENDING_DEPENDENCY`, claim atómico visible, backoff acotado, pausa automática y reanudación manual. `event_id` identifica delivery, `op_id` operación y un `attempt_id` UUID único identifica cada adquisición concreta; `worker_id` es sólo diagnóstico. `inbox_operation_scope` es la única autoridad consumer-scoped de equivalencia, exclusión y receipt, sin advisory lock ni leader por menor delivery. La expiración habilita takeover y el takeover exitoso avanza el fence e invalida al attempt anterior. Efecto, receipt y transición terminal comparten el commit exterior del processor; `REJECTED` sigue terminal. #510/PR #521 reutiliza este protocolo mediante el consumer portable `administrativo.usuario`, sin ledger ni mecanismo paralelo. #507 está cerrado/completado. No se implementó Tarea, GOP, heartbeat automático ni scheduler productivo.

## 17. Incremento Administrativo/Técnico #510 — replicación portable de usuario

#510/PR #521 materializó la replicación interinstalación del lifecycle de
`usuario` actualmente disponible: `usuario_creado` y `usuario_desactivado`.
Administrativo conserva ownership funcional y resuelve exclusivamente por
`usuario.uid_global`; cada instalación conserva su propia PK `id_usuario`.
Alta/baja local y outbox comparten transacción. La recepción revalida snapshots,
versiona por comparación autoritativa, admite saltos de versión y una baja V2+
coherente sobre UID ausente, y reutiliza retry, operation scope, fencing y retained
envelope de #511/#512. `op_id_alta` remoto permanece nullable, los timestamps se
canonicalizan a UTC-naive y credenciales/sesiones quedan fuera de sync por #455.
La replicación es prospectiva: no incorpora backfill ni reparación legacy de #520.
#507 está cerrado/completado. La autenticación técnica de procesos
`origen = SISTEMA` permanece separada y bajo #522.

## 18. Incremento Administrativo/Técnico #486 — sync de calendario comercial

PR #526, mergeado mediante `8fc23529d6c172c8baf829eee9c2d5bbe265cda2`,
integra los producers #484/#485 con el consumer portable
`administrativo.calendario_comercial` sobre #512/#521. El incremento conserva hashes
separados, continuidad estricta, singleton físico absoluto y una jerarquía común
de writers `advisory GLOBAL → raíz total → definiciones → historia`. El transporte
at-least-once exige sesiones origen/destino separadas, confirma primero la
delivery destino y sólo luego acredita el outbox origen; no agrega 2PC,
scheduler ni broker.

Validación estática focal: OK. Evidencia PostgreSQL local aportada: focal #486
`27 passed`; #512 `107 passed`; #510/fairness `63 passed`; #469/#470
`173 passed, 1 skipped`; outbox/transporte/policy `96 passed`; matriz avanzada
`19 passed` después del fix de clasificación CAS; focal + advanced juntas
`46 passed`. La hermeticidad quedó confirmada en ambos órdenes sin reset
intermedio (`19 → 27` y `27 → 19`): la matriz usa una base temporal exclusiva y
no deja contaminación funcional en `inmobiliaria_test`. La suite global informó
`2726 passed, 22 failed, 19 errors, 1 skipped`; ya no presenta contaminación de
#486 y sus fallos restantes corresponden a deuda histórica de rutas relativas
dependientes del cwd, ajena a este PR. La matriz confirma locks, concurrencia
local/remota, rollback inyectado, commit failure, fencing/takeover, transporte
entre dos bases y E2E. #486, #425 y #426 están completados; este último por
PR #531.

## 19. Incremento Comercial #426 — vencimiento inicial sugerido

#426 está cerrado/completado mediante PR #531, mergeado en
`65aec549bfebea6072f3e664a15b61778a1c0a58`. Comercial expone una consulta
`QUERY_READLIKE` por `fecha_venta` explícita, consume el query service
Administrativo del calendario y calcula una sugerencia efímera. Los writes de
venta y PPV2 continúan recibiendo y persistiendo una
`fecha_primer_vencimiento` explícita, sin recalcularla ni sobrescribirla. La
política de mes corto limita al último día existente; no hay SQL,
`configuracion_general`, HTTP interno, frontend ni cambios de indexación.
