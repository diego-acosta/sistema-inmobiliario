# PROJECT-STATUS — Estado operativo del proyecto

**Actualizado:** 2026-07-30
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
| A — Comercial / Financiero | Activo. PR #432 está mergeado y #424 cerrado como completado: `INT-FIN-005` es la fuente contractual vigente para la indexación PPV2 mensual; la implementación runtime permanece pendiente. PR #422 conserva la materialización como fuente de `EMITIDA`/`PROYECTADA`. Baseline anterior verificable: `1763 passed`; no hubo nueva ejecución de la suite backend por el PR documental #432. | #425–#431 y #423 conforman el roadmap de implementación; #423 sigue bloqueado por los incrementos de soporte. #345 y #365 conservan alcance relacionado. | #432 mergeado (cierra #424); #422 permanece como fuente vigente para `EMITIDA`/`PROYECTADA`. | #425; luego #426 → #427 → #428/#429 → #423 → #430/#431. |
| B — Administrativo | Activo incremental. Usuarios, roles, permisos, asignaciones y alcance operativo tienen incrementos completados; configuración y auditoría básica siguen abiertas. Catálogos ya cuenta con CRUD write de maestros e ítems. #407/PR #414 implementó sólo el inventario read-only de definiciones; #408 congela documentalmente la fuente canónica sin runtime nuevo. | #249, #263, #264 y #265 abiertos. | #414 mergeado (commit `b8d4ccb`); #408 es el freeze documental actual. | #425 sobre `parametro_sistema`/`valor_parametro` GLOBAL; implementación completa pendiente. |
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

- #425 — próximo incremento: configuración general requerida por el contrato
  mensual vigente en `INT-FIN-005`.
- #426–#429 — vencimiento, base común, materialización pendiente y período
  objetivo; incrementos de soporte posteriores a #425.
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

Para el roadmap contractual de indexación PPV2, el próximo foco inmediato es #425.
El orden recomendado es `#425 → #426 → #427 → #428/#429 → #423 → #430/#431`.
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

- #425: implementar primero la configuración general definida en `INT-FIN-005`.
- #426 → #427 → #428/#429: continuar con vencimiento, base común, valor pendiente,
  materialización y período objetivo, sin combinar alcances.
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
2. comenzar por #425 y continuar `#426 → #427 → #428/#429`, sin combinar alcances;
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
- #407 implementa el primer incremento de #263: inventario read-only de
  definiciones de parámetros. PR #414/commit `b8d4ccb` conserva ese GET. #408 congela documentalmente `parametro_sistema` como definición y `valor_parametro` como fuente de valores; no agrega endpoints. Los valores y writes siguen pendientes y #263 no se considera completado.
- #264 `Administrativo: catálogos maestros e ítems configurables` abierto.
- #265 `Administrativo: auditoría administrativa básica` abierto.
- #368 `CRUD write de catálogos maestros` cerrado/completado.
- #393 `Definir y congelar el ciclo de vida físico de item_catalogo` cerrado/completado.

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

Dentro de #264, el CRUD write de ítems quedó implementado por #399. En configuración, #408 deja #425 como próximo incremento arquitectónicamente habilitado, todavía sin runtime.

### 6.4 Decisiones vigentes

- `usuario` pertenece a Administrativo y no es `persona`.
- El vínculo usuario-persona, si se implementa, es asociación explícita; no fusiona identidades.
- `rol_seguridad` y `permiso` no son `rol_participacion` ni roles de negocio.
- `usuario_sucursal` referencia alcance operativo, pero no convierte Administrativo en dueño de `sucursal` o `instalacion`.
- La documentación API vigente indica que todavía no hay login real, passwords, OAuth/SSO, middleware de autorización real ni menú dinámico salvo evidencia posterior.
- `catalogo_maestro` ya tiene CRUD write mínimo.
- `item_catalogo` tiene lectura y CRUD write implementados; jerarquías e historial funcional permanecen fuera de alcance.
- Los únicos estados físicos permitidos de `item_catalogo` son `ACTIVO` e `INACTIVO`; su estado inicial es `ACTIVO`.
- `INACTIVO` no equivale a baja lógica: la baja lógica se representa mediante `deleted_at`.
- La transición `INACTIVO → ACTIVO` queda permitida para un futuro comando; la reactivación de una baja lógica sigue `NO CONFIRMADA`.
- El código de ítem no se reutiliza después de baja.
- Los dominios consumidores deciden sus reglas particulares de aceptación de ítems inactivos.
- No migrar enums de otros dominios incidentalmente.
- Todo write administrativo nuevo debe cumplir CORE-EF desde el inicio.
- `parametro_sistema` es la definición canónica y `valor_parametro` la fuente canónica de valores; `configuracion_general` es compatibilidad heredada y `configuracion_local` pertenece a Operativo.
- #425 queda arquitectónicamente habilitado sólo para valores GLOBAL (`id_sucursal` e `id_instalacion` nulos), pero todo su runtime, SQL CORE-EF y tests PostgreSQL continúa pendiente.

### 6.5 Próximo foco recomendado

El CRUD write de `item_catalogo` quedó implementado por #399. Para configuración, el freeze #408 desbloquea arquitectónicamente #425, que es el próximo incremento del roadmap Comercial/Financiero: deberá comenzar por el patch SQL CORE-EF y los valores GLOBAL, sin mezclar `configuracion_general`, `configuracion_local` ni catálogos. #263 permanece abierto hasta implementar y validar valores y writes. #265 conserva su alcance independiente.

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
