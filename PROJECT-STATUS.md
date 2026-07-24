# PROJECT-STATUS — Estado operativo del proyecto

**Actualizado:** 2026-07-24
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
| A — Comercial / Financiero | Activo. #390 corrigió emisión PPV2; #392 alineó reservas; #394 auditó la brecha de #374; #397 expuso queries read-only de índices. | #346, #348, #349, #365 y #374 abiertos; #395 cerrado. | #397 mergeado el 2026-07-24. | #374: integrar catálogo y valor aplicable reales en Venta completa V3, sin cálculo financiero en frontend. |
| B — Administrativo | Activo incremental. Usuarios, roles, permisos, asignaciones y alcance operativo tienen incrementos completados; configuración general y auditoría básica siguen abiertas. Catálogos continúa activo: ya completó lectura read-only, preparación CORE-EF y SQL, CRUD write de `catalogo_maestro` y freeze físico del ciclo de vida de ítems; falta el CRUD write de `item_catalogo`. | #249, #263, #264 y #265 abiertos. | #396 mergeado (commit `7d0d4c5dc2c90e7de11ee550c8eb17d974ed77ab`); #370 fue el incremento inmediatamente anterior. | CRUD write de `item_catalogo`. |
| Operativo | En espera relativa para este documento. Caja operativa tuvo PRs recientes, pero no es parte del trabajo Comercial/Financiero ni Administrativo actual. | #248 abierto. | #331 y #327 mergeados el 2026-07-10. | No confundir caja operativa con movimiento financiero ni con administrativo. |

## 4. Reglas para trabajo paralelo

- Mantener PRs pequeños y trazables a un issue.
- No mezclar dominios en un mismo incremento salvo orquestación explícita y verificada.
- Separar `Comercial` de `Financiero`: Comercial gobierna compraventa; Financiero gobierna deuda, pagos, imputación, índices e indexación.
- Separar `Administrativo` de `Operativo`: Administrativo gobierna usuarios, seguridad, configuración y auditoría; Operativo gobierna sucursales, instalaciones y caja operativa.
- Mantener explícito: `USUARIO` ≠ `PERSONA`, `SUCURSAL` ≠ `INSTALACION`, rol de seguridad ≠ rol de participación, caja operativa ≠ movimiento financiero.
- Todo endpoint write nuevo o modificado debe nacer con decisión CORE-EF según `AGENTS.md`.

## 5. Frente A — Comercial / Financiero

### 5.1 Estado

Activo. El ciclo inicial de indexación V2 y venta histórica manual quedó completado. Los merges recientes dejaron disponible el contrato read-only que necesitaba #374:

- PR #390 corrigió la emisión PPV2: los importes definitivos nacen `EMITIDA`; una cuota indexada sin importe materializado nace `PROYECTADA`; la aplicación posterior la pasa de `PROYECTADA` a `EMITIDA`. La demo PPV2 quedó aislada transaccionalmente en tests.
- PR #392 alineó la suite de reservas con el contrato vigente, eliminó el patch DDL heredado de los tests y corrigió los fixtures de roles. Cerró #391.
- PR #394 incorporó la auditoría contractual de #374; no implementó ni cerró #374.
- PR #397 expuso catálogo de índices y valor publicado aplicable por fecha como queries read-only. Cerró #395 y desbloqueó #374.
- El último baseline backend verificable informado para este corte es `1740 passed`; no se reejecutó la suite completa en este cambio exclusivamente documental.
- #346, #348, #349, #365 y #374 permanecen abiertos.

Implementación relevante verificada:

- Routers: `backend/app/api/routers/comercial_router.py`, `backend/app/api/routers/financiero_router.py`.
- Schemas: `backend/app/api/schemas/comercial.py`, `backend/app/api/schemas/financiero.py`.
- Services: `backend/app/application/comercial/services/`, `backend/app/application/financiero/services/`.
- Repositories: `backend/app/infrastructure/persistence/repositories/`.
- SQL: Plan Pago Venta V2, bloques, indexación y corridas en `backend/database/`.
- Tests: venta completa, Plan Pago Venta V2, preview, preparación, aplicación de indexación V2 y E2E comercial-financiero en `backend/tests/`.

### 5.2 Issues activos

- #346 — integración con importación de ventas históricas.
- #348 — frente amplio de frontend de indexación y corridas.
- #349 — corrección y reversión avanzada.
- #365 — definición transversal de fecha operativa.
- #374 — mejorar configuración de tramos indexados en Venta completa V3; abierto y desbloqueado por #397.
- #59 continúa abierto como issue histórico y amplio de confirmación desde reserva; revisar su vigencia antes de usarlo como próximo incremento.

### 5.3 Últimos PR relevantes

- #397 `feat(financiero): exponer catálogo de índices y valor publicado aplicable por fecha` — mergeado 2026-07-24.
- #394 `docs(frontend): documentar brecha contractual de tramos indexados` — mergeado 2026-07-24.
- #392 `feat(comercial): restaurar contrato y suite de reservas de venta` — mergeado 2026-07-24.
- #390 `fix(financiero): alinear ciclo de obligaciones PPV2 con emisión` — mergeado 2026-07-23.
- #388 `docs(financiero): documentar semántica de estados en Plan Pago V2` — mergeado 2026-07-22.

### 5.4 Próximo foco recomendado

#374 — Mejorar configuración de tramos indexados en Venta completa V3. #397 ya proporciona `GET /api/v1/financiero/indices` y `GET /api/v1/financiero/indices/valor-aplicable`, los contratos que la auditoría #394 identificó como faltantes.

El incremento debe cargar el catálogo real, resolver el valor aplicable para la fecha solicitada y ocultar IDs técnicos. También debe completar la edición y eliminación de tramos ya agregados, preservar el estado al avanzar, volver y editar, y cubrir validaciones visibles, resumen de pendientes y la habilitación coherente de Guardar tramo y Siguiente. El frontend sólo presenta las respuestas y arma el comando comercial válido: no calcula indexación, no infiere valores y no duplica reglas financieras. #348 se mantiene como issue más amplio para visualización de indexación y corridas.

### 5.5 Decisiones vigentes

- Comercial conserva ownership de la venta.
- Financiero conserva ownership de obligaciones, índices, ajustes, saldos y corridas.
- La orquestación no traslada ownership financiero al dominio Comercial.
- Una venta histórica puede generar obligaciones directamente indexadas si el valor aplicable ya está publicado.
- No se aplica una corrida inmediata sobre obligaciones que ya nacieron indexadas.
- Las obligaciones no indexadas y las indexadas con importe definitivo materializado nacen `EMITIDA`; las indexadas sin valor materializado nacen `PROYECTADA`.
- La aplicación posterior de una corrida pasa una obligación `PROYECTADA` a `EMITIDA` y no altera los demás estados contractuales.
- Las cuotas históricas exigibles sin índice válido bloquean toda la confirmación.
- Las cuotas futuras pueden persistirse como `PROYECTADA` sin ajuste materializado.
- `PROYECTADA_SIN_INDICE` es una clasificación de cálculo/preview, no un estado físico de `obligacion_financiera`.
- `fecha_corte` es un dato de negocio explícito.
- El uso de `date.today()` para detectar historicidad es provisional hasta resolver #365.
- Publicación, preparación y aplicación de una corrida son operaciones separadas.
- El catálogo de índices y la resolución de valor aplicable pertenecen a Financiero y son `QUERY_READLIKE`: no requieren headers write, no escriben ni recalculan en frontend.
- Una respuesta de valor aplicable con `data: null` significa que el índice activo existe pero no tiene valor aplicable; no se infiere un valor.
- `cliente_comprador` es semántica funcional comercial aunque tenga persistencia heredada.
- `persona` es identidad base; no define condición de cliente ni comprador.
- `analitico` es read-only y no debe recalcular ni persistir lógica financiera.

### 5.6 Pendientes y orden sugerido

- #374: candidato inmediato; completar catálogo, valor aplicable, edición/eliminación de tramos, navegación preservando estado y validaciones del wizard Venta completa V3.
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

### 5.9 Regla de continuidad

Antes de tocar código para #374:

1. abrir #374, la auditoría #394 y el PR #397;
2. revisar el wizard Venta completa V3 y el cliente HTTP real;
3. validar los contratos DEV-API Financiero y Comercial, router, schemas, service, repository y tests de índices;
4. integrar catálogo real, resolución de valor aplicable, estados de carga/error y ocultamiento de IDs técnicos;
5. implementar edición y eliminación de tramos ya agregados, preservando el estado durante la navegación;
6. agregar validaciones por campo, resumen de pendientes y habilitación coherente de Guardar tramo y Siguiente;
7. probar navegación, edición y eliminación sin pérdida ni duplicación de datos;
8. no calcular indexación ni duplicar reglas financieras;
9. no invadir #346, #349 ni #365;
10. marcar `NO CONFIRMADO` cualquier dato sin evidencia.

## 6. Frente B — Administrativo

### 6.1 Estado

Activo incremental. GitHub muestra el epic #249 abierto: `[Epic] Administrativo: usuarios, roles, permisos y configuración`.

Sub-issues con estado verificable:

- #259 `Administrativo: usuarios del sistema — modelo y CRUD base` cerrado/completado.
- #260 `Administrativo: roles de seguridad y permisos base` cerrado/completado.
- #261 `Administrativo: asignación de roles a usuarios` cerrado/completado.
- #262 `Administrativo: alcance operativo por sucursal/instalación` cerrado/completado.
- #263 `Administrativo: configuración general del sistema` abierto.
- #264 `Administrativo: catálogos maestros e ítems configurables` abierto.
- #265 `Administrativo: auditoría administrativa básica` abierto.
- #368 `CRUD write de catálogos maestros` cerrado/completado.
- #393 `Definir y congelar el ciclo de vida físico de item_catalogo` cerrado/completado.

Incrementos completados en catálogos:

- #360 / PR #362: consultas read-only de `catalogo_maestro` e `item_catalogo`.
- #363 / PR #364: soporte CORE-EF y restricciones SQL para catálogos.
- #368 / PR #370: alta, modificación y baja lógica de `catalogo_maestro`, con idempotencia, optimistic locking, outbox y errores tipados.
- #393 / PR #396: estados físicos `ACTIVO` e `INACTIVO`, estado inicial `ACTIVO`, `NOT NULL`, `CHECK`, diferenciación entre inactivación y baja lógica, código no reutilizable después de baja y preparación del futuro CRUD write de ítems.

### 6.2 Epic o issue principal

- #249 `[Epic] Administrativo: usuarios, roles, permisos y configuración`: abierto.

### 6.3 Issues activos

Los frentes activos verificables son:

- #263 — configuración general.
- #264 — catálogos maestros e ítems configurables.
- #265 — auditoría administrativa básica.

Dentro de #264, el próximo incremento recomendado es `CRUD write de ítems de catálogo`.

### 6.4 Decisiones vigentes

- `usuario` pertenece a Administrativo y no es `persona`.
- El vínculo usuario-persona, si se implementa, es asociación explícita; no fusiona identidades.
- `rol_seguridad` y `permiso` no son `rol_participacion` ni roles de negocio.
- `usuario_sucursal` referencia alcance operativo, pero no convierte Administrativo en dueño de `sucursal` o `instalacion`.
- La documentación API vigente indica que todavía no hay login real, passwords, OAuth/SSO, middleware de autorización real ni menú dinámico salvo evidencia posterior.
- `catalogo_maestro` ya tiene CRUD write mínimo.
- `item_catalogo` tiene solo lectura y freeze físico de estado; no tiene CRUD write.
- Los únicos estados físicos permitidos de `item_catalogo` son `ACTIVO` e `INACTIVO`; su estado inicial es `ACTIVO`.
- `INACTIVO` no equivale a baja lógica: la baja lógica se representa mediante `deleted_at`.
- La transición `INACTIVO → ACTIVO` queda permitida para un futuro comando; la reactivación de una baja lógica sigue `NO CONFIRMADA`.
- El código de ítem no se reutiliza después de baja.
- Los dominios consumidores deciden sus reglas particulares de aceptación de ítems inactivos.
- No migrar enums de otros dominios incidentalmente.
- Todo write administrativo nuevo debe cumplir CORE-EF desde el inicio.

### 6.5 Próximo foco recomendado

Para dar continuidad coherente a #264, crear un sub-issue de #264 para el CRUD write de `item_catalogo` e implementar, en un incremento posterior, alta, modificación, cambio de estado y baja lógica. Debe respetar CORE-EF desde el inicio.

Mantener fuera de alcance jerarquías, historial, defaults avanzados, vigencias y UI. #263 y #265 siguen siendo candidatos válidos para otros incrementos paralelos, pero no deben desplazar el cierre coherente de #264 en este frente.

### 6.6 Fuera de alcance

- Redefinir Personas.
- Implementar Operativo dentro de Administrativo.
- Usar `sucursal` e `instalacion` como si fueran entidades administrativas.
- Crear autenticación real, sesiones o credenciales persistidas sin issue y auditoría previa.
- Declarar outbox, locks o autorización real si no hay evidencia en repository, SQL y tests.
- Implementar jerarquías, historial, defaults avanzados, vigencias o UI como parte del futuro CRUD write de ítems.

### 6.7 Documentos relevantes

- `backend/documentacion/DEV-API/dominios/administrativo/DEV-API-ADM-001.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/SRV-ADM-005-gestion-de-configuracion-y-parametrizacion.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/EST-ADM.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/catalogos/RN-ADM.md`.
- `backend/documentacion/CORE-EF/CORE-EF-001.md` y matriz de cumplimiento.
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md`.
- `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md`.

### 6.8 Últimos PR relevantes

- #396 `feat(administrativo): definir ciclo de vida de ítems de catálogo (#393)` — mergeado.
- #370 `feat(administrativo): CRUD write de catálogos maestros (#368)` — mergeado.
- #364 `feat(administrativo): preparar catálogos CORE-EF` — mergeado.
- #362 `feat(administrativo): consulta read-only de catálogos e ítems (#360)` — mergeado.

### 6.9 Regla de continuidad

Antes de tocar código para el futuro CRUD write de ítems:

1. abrir #264, #393 y PR #396;
2. revisar DEV-API Administrativo y DEV-SRV Administrativo;
3. validar SQL real de `item_catalogo`;
4. revisar router, schemas y repository actuales;
5. revisar tests read-only y CORE-EF;
6. estudiar el patrón implementado en `catalogo_maestro`;
7. no implementar jerarquías ni historial;
8. no migrar enums;
9. no mezclar #263 ni #265 dentro del mismo PR;
10. marcar `NO CONFIRMADO` todo lo no respaldado.

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
