# PROJECT-STATUS — Estado operativo del proyecto

**Actualizado:** 2026-07-15
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
| A — Comercial / Financiero | Activo. Hay integración reciente de indexación V2 con ventas históricas y confirmación completa pendiente. | #358 abierto; #346 y #345 abiertos; #59 abierto. | #357 mergeado el 2026-07-15. | Integrar prevalidación histórica en confirmar venta completa sin mezclar ownership Comercial/Financiero. |
| B — Administrativo | Activo incremental. CRUD/base de usuarios, roles/permisos, asignaciones y alcance operativo tienen partes implementadas; configuración, catálogos y auditoría siguen abiertos. | #249 abierto. | #315 mergeado el 2026-07-03 para alcance operativo por sucursal. | Auditar modelo e implementación real antes de continuar configuración, catálogos o auditoría. |
| Operativo | En espera relativa para este documento. Caja operativa tuvo PRs recientes, pero no es parte del nuevo trabajo administrativo. | #248 abierto. | #331 y #327 mergeados el 2026-07-10. | No confundir caja operativa con movimiento financiero ni con administrativo. |

## 4. Reglas para trabajo paralelo

- Mantener PRs pequeños y trazables a un issue.
- No mezclar dominios en un mismo incremento salvo orquestación explícita y verificada.
- Separar `Comercial` de `Financiero`: Comercial gobierna compraventa; Financiero gobierna deuda, pagos, imputación, índices e indexación.
- Separar `Administrativo` de `Operativo`: Administrativo gobierna usuarios, seguridad, configuración y auditoría; Operativo gobierna sucursales, instalaciones y caja operativa.
- Mantener explícito: `USUARIO` ≠ `PERSONA`, `SUCURSAL` ≠ `INSTALACION`, rol de seguridad ≠ rol de participación, caja operativa ≠ movimiento financiero.
- Todo endpoint write nuevo o modificado debe nacer con decisión CORE-EF según `AGENTS.md`.

## 5. Frente A — Comercial / Financiero

### 5.1 Estado

Activo. Verificado contra GitHub y git local:

- #357 `feat(comercial): prevalidar indexación de ventas históricas` fue mergeado el 2026-07-15.
- #355 `docs(auditoria): diseñar indexación de ventas históricas` fue mergeado el 2026-07-14.
- #354, #353, #352 y #350 completaron incrementos de corridas de indexación V2.
- #358 está abierto para integrar la prevalidación histórica en confirmar venta completa.
- #356 está cerrado/completado.
- #346, #345 y #349 están abiertos y deben revisarse antes de nuevos cambios financieros.

Implementación local relevante verificada:

- Routers: `backend/app/api/routers/comercial_router.py`, `backend/app/api/routers/financiero_router.py`.
- Schemas: `backend/app/api/schemas/comercial.py`, `backend/app/api/schemas/financiero.py`.
- Services: `backend/app/application/comercial/services/`, `backend/app/application/financiero/services/`.
- Repositories: `backend/app/infrastructure/persistence/repositories/`.
- SQL: patches de Plan Pago Venta V2, bloques, indexación y corridas en `backend/database/`.
- Tests: suites de venta completa, Plan Pago Venta V2, preview/preparación/aplicación de indexación V2 y E2E comercial-financiero en `backend/tests/`.

### 5.2 Epic o issue principal

- #59 `Diseñar endpoint confirmar venta completa desde reserva`: abierto; histórico y amplio.
- #358 `[Comercial/Financiero] Integrar prevalidación histórica en confirmar venta completa`: abierto y más inmediato.

### 5.3 Últimos PR relevantes

- #357 `feat(comercial): prevalidar indexación de ventas históricas` — mergeado 2026-07-15.
- #355 `docs(auditoria): diseñar indexación de ventas históricas` — mergeado 2026-07-14.
- #354 `feat(financiero): preparar corridas V2 al publicar un índice` — mergeado 2026-07-14.
- #353 `feat(financiero): aplicar corridas de indexación V2` — mergeado 2026-07-14.
- #352 `feat(financiero): implementar preview de indexación V2` — mergeado 2026-07-13.
- #350 `feat(financiero): agregar SQL base de corridas de indexación V2` — mergeado 2026-07-13.
- #339 y #337 son diseño/auditoría previos de indexación V2.

### 5.4 Issue activo

Prioridad operativa actual: #358. También revisar #346, #345 y #349 para no duplicar ni contradecir trabajos pendientes.

### 5.5 Objetivo inmediato

Integrar la prevalidación histórica en el flujo de confirmación completa de venta, validando contra SQL, servicios, repositories y tests existentes. Debe conservarse la separación:

- Comercial decide y persiste la operación de compraventa.
- Financiero calcula/gobierna obligaciones, corridas, índices e indexación.
- La orquestación no traslada ownership financiero al dominio Comercial.

### 5.6 Decisiones vigentes

- `cliente_comprador` es semántica funcional comercial aunque tenga persistencia heredada.
- `persona` es identidad base; no define condición de cliente ni comprador.
- Plan Pago Venta V2 está respaldado por SQL, servicios y tests específicos; no asumir cobertura fuera de lo existente.
- Indexación V2 tiene SQL y endpoints/servicios recientes para preview, preparación y aplicación de corridas.
- `analitico` es read-only y no debe recalcular ni persistir lógica financiera.

### 5.7 Fuera de alcance

- Rediseñar el dominio Financiero.
- Crear caja operativa, recibos fiscales persistidos o documental real como parte de este frente.
- Mover lógica de cálculo financiero a Comercial.
- Tratar documentos históricos como implementación si no aparecen en SQL/backend/tests.

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

Antes de tocar código, abrir #358 y los issues #346/#345/#349, leer el diff de #357 y validar qué quedó implementado contra SQL/backend/tests. Si falta evidencia, marcar `NO CONFIRMADO` en el PR.

## 6. Frente B — Administrativo

### 6.1 Estado

Activo incremental. GitHub muestra el epic #249 abierto: `[Epic] Administrativo: usuarios, roles, permisos y configuración`. Sub-issues verificados:

- #259 `Administrativo: usuarios del sistema — modelo y CRUD base` cerrado/completado.
- #260 `Administrativo: roles de seguridad y permisos base` cerrado/completado.
- #261 `Administrativo: asignación de roles a usuarios` cerrado/completado.
- #262 `Administrativo: alcance operativo por sucursal/instalación` cerrado/completado.
- #263 `Administrativo: configuración general del sistema` abierto.
- #264 `Administrativo: catálogos maestros e ítems configurables` abierto.
- #265 `Administrativo: auditoría administrativa básica` abierto.

Implementación local relevante verificada:

- Router: `backend/app/api/routers/administrativo_router.py`.
- Schema: `backend/app/api/schemas/administrativo.py`.
- Documentación API vigente: `backend/documentacion/DEV-API/dominios/administrativo/DEV-API-ADM-001.md`.
- Documentación SRV: `backend/documentacion/DEV-SRV/dominios/administrativo/`.
- SQL: patches `patch_usuario_core_ef_20260630.sql`, `patch_usuario_rol_seguridad_core_ef_20260630.sql`, `patch_usuario_sucursal_core_ef_20260702.sql`.
- Tests: `test_administrativo_usuarios.py`, `test_administrativo_roles_permisos.py`, `test_administrativo_usuario_roles_seguridad.py`, `test_administrativo_alcance_operativo.py`.

### 6.2 Epic o issue principal

- #249 `[Epic] Administrativo: usuarios, roles, permisos y configuración`: abierto.

### 6.3 Últimos PR relevantes

- #315 `Administrativo: alcance operativo por sucursal` — mergeado 2026-07-03.
- PRs asociados a #259/#260/#261 no se listan con número en este documento porque no fueron identificados de forma inequívoca en la primera página reciente de PRs; revisar GitHub antes de citarlos en un PR funcional.

### 6.4 Issue activo

El próximo trabajo debe partir de una auditoría del estado real. Issues abiertos verificables: #263, #264 y #265. Elegir uno por incremento.

### 6.5 Objetivo inmediato

Continuar Administrativo de forma incremental, auditando primero modelo e implementación real para configuración, catálogos o auditoría. No iniciar funcionalidades nuevas de seguridad sin validar SQL, router, schema, service/repository y tests existentes.

### 6.6 Decisiones vigentes

- `usuario` pertenece a Administrativo y no es `persona`.
- El vínculo usuario-persona, si se implementa, es asociación explícita; no fusiona identidades.
- `rol_seguridad` y `permiso` no son `rol_participacion` ni roles de negocio.
- `usuario_sucursal` referencia alcance operativo, pero no convierte Administrativo en dueño de `sucursal` o `instalacion`.
- La documentación API vigente indica que todavía no hay login real, passwords, OAuth/SSO, middleware de autorización real ni menú dinámico salvo evidencia posterior.
- Todo write administrativo nuevo debe cumplir CORE-EF desde el inicio.

### 6.7 Fuera de alcance

- Redefinir Personas.
- Implementar Operativo dentro de Administrativo.
- Usar `sucursal` e `instalacion` como si fueran entidades administrativas.
- Crear autenticación real, sesiones o credenciales persistidas sin issue y auditoría previa.
- Declarar outbox, locks o autorización real si no hay evidencia en repository/SQL/tests.

### 6.8 Documentos relevantes

- `backend/documentacion/DEV-API/dominios/administrativo/DEV-API-ADM-001.md`.
- `backend/documentacion/DEV-SRV/dominios/administrativo/`.
- `backend/documentacion/CORE-EF/CORE-EF-001.md` y matriz de cumplimiento.
- `backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md` para separar `usuario` de `persona`.
- `backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md` para separar alcance operativo de ownership operativo.

### 6.9 Regla de continuidad

Antes de tocar código administrativo, seleccionar un issue abierto (#263, #264 o #265), auditar SQL/backend/tests y documentar explícitamente lo implementado, pendiente y `NO CONFIRMADO`.

## 7. Dependencias entre frentes

- Comercial/Financiero puede requerir usuarios/sucursales/instalaciones solo como metadatos CORE-EF; eso no habilita cambios administrativos ni operativos dentro del mismo PR.
- Administrativo puede referenciar sucursales/instalaciones para alcance, pero Operativo mantiene ownership de esas entidades.
- Financiero puede consumir ventas y sujetos; no redefine compraventa ni persona.
- Analítico solo lee; cualquier necesidad de persistir o corregir datos pertenece al dominio dueño.

## 8. Frentes en espera

- Operativo: existen trabajos recientes de caja operativa (#325, #327, #331) y epic #248 abierto. No mezclar con Administrativo.
- Frontend de indexación V2: #348 está abierto; revisar antes de cambios de UI.
- Reversión/corrección avanzada de indexación V2: #349 abierto; no implementarlo incidentalmente dentro de #358.

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
