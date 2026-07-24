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
| A — Comercial / Financiero | Activo. El ciclo inicial de indexación V2 y venta histórica manual quedó completado. | #346, #348, #349 y #365 abiertos; #345 y #358 cerrados. | #361 mergeado el 2026-07-16. | Auditar y dividir #348 para una primera visualización read-only de indexación V2 en la ficha de venta. |
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

Activo. El ciclo inicial de indexación V2 y venta histórica manual quedó completado:

- #338, #342, #343 y #344 están cerrados/completados.
- #345 está cerrado/completado después de auditoría integral.
- #356 está cerrado/completado.
- #358 está cerrado/completado.
- PR #350 agregó la base SQL de corridas V2.
- PR #352 implementó preview efímero y persistido.
- PR #353 implementó aplicación de corridas V2.
- PR #354 implementó preparación por publicación de índice.
- PR #355 documentó la estrategia de ventas históricas.
- PR #357 implementó la prevalidación histórica read-like.
- PR #361 integró la prevalidación en la confirmación completa de venta.
- #346, #348, #349 y #365 permanecen abiertos.

Implementación relevante verificada:

- Routers: `backend/app/api/routers/comercial_router.py`, `backend/app/api/routers/financiero_router.py`.
- Schemas: `backend/app/api/schemas/comercial.py`, `backend/app/api/schemas/financiero.py`.
- Services: `backend/app/application/comercial/services/`, `backend/app/application/financiero/services/`.
- Repositories: `backend/app/infrastructure/persistence/repositories/`.
- SQL: Plan Pago Venta V2, bloques, indexación y corridas en `backend/database/`.
- Tests: venta completa, Plan Pago Venta V2, preview, preparación, aplicación de indexación V2 y E2E comercial-financiero en `backend/tests/`.

### 5.2 Issues activos

- #346 — integración con importación de ventas históricas.
- #348 — frontend de indexación y corridas.
- #349 — corrección y reversión avanzada.
- #365 — definición transversal de fecha operativa.
- #59 continúa abierto como issue histórico y amplio de confirmación desde reserva; revisar su vigencia antes de usarlo como próximo incremento.

### 5.3 Últimos PR relevantes

- #361 `feat(comercial): integrar prevalidación histórica al confirmar venta` — mergeado 2026-07-16.
- #357 `feat(comercial): prevalidar indexación de ventas históricas` — mergeado 2026-07-15.
- #355 `docs(auditoria): diseñar indexación de ventas históricas` — mergeado 2026-07-14.
- #354 `feat(financiero): preparar corridas V2 al publicar un índice` — mergeado 2026-07-14.
- #353 `feat(financiero): aplicar corridas de indexación V2` — mergeado 2026-07-14.
- #352 `feat(financiero): implementar preview de indexación V2` — mergeado 2026-07-13.
- #350 `feat(financiero): agregar SQL base de corridas de indexación V2` — mergeado 2026-07-13.

### 5.4 Próximo foco recomendado

Auditar y dividir #348 para implementar primero una visualización read-only de indexación V2 en la ficha de venta.

El primer incremento tentativo debe mostrar, usando datos reales del backend:

- capital original;
- ajuste de indexación;
- importe vigente;
- saldo;
- índice y valores aplicados;
- coeficiente;
- estado de indexación;
- corrida relacionada, si existe.

Antes de implementar se debe confirmar si el backend ya ofrece una query suficiente o si hace falta un contrato read-like mínimo. No duplicar cálculo financiero en Comercial ni en frontend.

### 5.5 Decisiones vigentes

- Comercial conserva ownership de la venta.
- Financiero conserva ownership de obligaciones, índices, ajustes, saldos y corridas.
- La orquestación no traslada ownership financiero al dominio Comercial.
- Una venta histórica puede generar obligaciones directamente indexadas si el valor aplicable ya está publicado.
- No se aplica una corrida inmediata sobre obligaciones que ya nacieron indexadas.
- Las cuotas históricas exigibles sin índice válido bloquean toda la confirmación.
- Las cuotas futuras pueden persistirse como `PROYECTADA` sin ajuste materializado.
- `PROYECTADA_SIN_INDICE` es una clasificación de cálculo/preview, no un estado físico de `obligacion_financiera`.
- `fecha_corte` es un dato de negocio explícito.
- El uso de `date.today()` para detectar historicidad es provisional hasta resolver #365.
- Publicación, preparación y aplicación de una corrida son operaciones separadas.
- `cliente_comprador` es semántica funcional comercial aunque tenga persistencia heredada.
- `persona` es identidad base; no define condición de cliente ni comprador.
- `analitico` es read-only y no debe recalcular ni persistir lógica financiera.

### 5.6 Pendientes y orden sugerido

- #348: mejor candidato inmediato, comenzando por lectura y visualización.
- #365: deuda transversal que debe avanzar antes de ampliar importaciones históricas, procesos batch o escenarios multiinstalación.
- #346: pendiente vigente, pero requiere auditoría específica del importador y posible relación con #365.
- #349: pendiente vigente de alto riesgo; debe auditarse y dividirse antes de implementar.

### 5.7 Fuera de alcance del próximo incremento

- Importación masiva.
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
- `backend/documentacion/CORE-EF/`.
- `backend/documentacion/DECISIONES/integracion/INT-FIN-*.md`.

### 5.9 Regla de continuidad

Antes de tocar código para #348:

1. abrir #348 y los PR #350, #352, #353, #354, #357 y #361;
2. revisar frontend real de ficha de venta;
3. verificar queries existentes;
4. validar SQL, routers, schemas, services, repositories y tests;
5. dividir #348 en incrementos pequeños;
6. no invadir #346, #349 ni #365;
7. marcar `NO CONFIRMADO` cualquier dato sin evidencia.

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
- Frontend de indexación V2: #348 abierto; próximo candidato, comenzando por lectura.
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
