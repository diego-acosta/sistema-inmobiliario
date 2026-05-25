# ROADMAP MAESTRO — DOMINIOS PENDIENTES

Fecha de auditoría: 2026-05-25  
Alcance auditado: `backend/documentacion`, `backend/app`, `backend/tests`, `backend/database`.

## Criterios de lectura del estado

- **implementado**: existe cobertura funcional visible en routers + servicios + persistencia + tests.
- **parcial**: existe implementación utilizable, pero incompleta en casos de uso, contratos o cobertura.
- **pendiente**: hay diseño/documentación, pero implementación insuficiente o nula.
- **no auditado**: no se confirmó evidencia suficiente en esta pasada.

---

## 1) Comercial / ventas

**Estado actual:** **parcial (alto avance en núcleo de ventas)**.

### Evidencias del repo
- Documentación de arquitectura y servicios comerciales (`DEV-ARCH-COM-001`, `SRV-COM-*`, decisiones COM/INT).
- Implementación fuerte en `backend/app/application/comercial/commands/*` y `.../services/*`.
- Router y esquemas en `backend/app/api/routers/comercial_router.py` y `backend/app/api/schemas/comercial.py`.
- Persistencia dedicada en `backend/app/infrastructure/persistence/repositories/comercial_repository.py` y `plan_pago_venta_v2_repository.py`.
- Cobertura de tests amplia en reservas, venta directa, confirmaciones, plan pago V2, instrumentos, cesiones y escrituración (`backend/tests/test_reservas_venta_*`, `test_ventas_*`, `test_plan_pago_venta_v2_*`, `test_ventas_directa_*`).

### Brechas principales
- Endurecer consistencia entre contratos API/documentación y edge cases multiobjeto.
- Completar trazabilidad integral de ciclo comercial completo (reserva → venta → escritura → eventos).
- Uniformar validaciones transversales para no depender de compatibilidad heredada.

### Riesgos
- Regresiones en flujos ya productivos por cambios de contratos sin matriz de compatibilidad.
- Inconsistencias de estado si se toca confirmación sin preservar secuencia de eventos.

### Dependencias
- CORE-EF (outbox/inbox, idempotencia).
- Inmobiliario (disponibilidad/ocupación post eventos comerciales).
- Financiero (obligaciones desde venta confirmada).

### Próximos issues sugeridos
1. Matriz de contratos API comerciales vs tests actuales (gap report).
2. Endpoints de auditoría funcional por venta (timeline de eventos).
3. Cierre de edge cases de venta directa con validación jerárquica extendida.

### Orden recomendado de implementación
1. Auditoría de contratos.
2. Hardening de validaciones/estados.
3. Trazabilidad avanzada.

### Qué NO tocar todavía
- Replanteos de modelo de dominio comercial ya consolidado.
- Reescritura de Plan Pago V2 sin necesidad de bug concreto.

### Prioridad
**alta**.

---

## 2) Inmobiliario / disponibilidad / ocupación

**Estado actual:** **parcial (núcleo implementado con buena cobertura)**.

### Evidencias del repo
- Diseño en `DEV-API-INM-001`, `SRV-INM-*`, decisiones de integración comercial-inmobiliario.
- Implementación robusta en `backend/app/application/inmuebles/commands/*` y `.../services/*`.
- Router/schemas en `backend/app/api/routers/inmuebles_router.py` y `backend/app/api/schemas/inmuebles.py`.
- Consumidores de eventos: `consume_venta_confirmada_service.py`, `consume_entrega_locativa_service.py`, `consume_restitucion_locativa_service.py`, `consume_escrituracion_registrada_service.py`.
- Tests de disponibilidades/ocupaciones/unidades funcionales/integración (`test_disponibilidades_*`, `test_ocupaciones_*`, `test_unidades_funcionales_*`, `test_inmobiliario_*_consumer.py`).

### Brechas principales
- Consolidar reglas de ocupación/disponibilidad para escenarios excepcionales.
- Profundizar observabilidad de cambios de estado por eventos externos.
- Cerrar huecos de contratos de consulta integral en UI selector/reporting.

### Riesgos
- Doble actualización de estado por reprocesamiento de eventos.
- Divergencia entre estado operativo real y estado comercial si fallan consumers.

### Dependencias
- CORE-EF mínimo completo (idempotencia y sincronización).
- Comercial y locativo como productores de eventos.

### Próximos issues sugeridos
1. Auditoría de idempotencia en consumers inmobiliarios.
2. Tablero de consistencia disponibilidad vs ocupación.
3. Cobertura de tests de carreras concurrentes.

### Orden recomendado de implementación
1. Hardening idempotencia.
2. Reglas de consistencia de estado.
3. Observabilidad/reportes operativos de consistencia.

### Qué NO tocar todavía
- Cambios masivos de nomenclatura de estados sin migración validada.

### Prioridad
**alta**.

---

## 3) Financiero

**Estado actual:** **parcial (avance relevante, dominio sensible aún en cierre)**.

### Evidencias del repo
- Diseño extenso en `DEV-API-FIN-001`, `API-FIN-001.yaml`, `SRV-FIN-*`, decisiones `INT-FIN-*`.
- Implementación en `backend/app/application/financiero/commands/*` y `.../services/*`.
- Router/schemas en `backend/app/api/routers/financiero_router.py` y `backend/app/api/schemas/financiero.py`.
- SQL/patches financieros múltiples en `backend/database/patch_*fin*`, `patch_*impuesto*`, `patch_*mora*`, `patch_*pago*`.
- Tests existentes para obligaciones, mora, deuda consolidada, estado de cuenta, pagos, eventos (`test_fin_*`, `test_impuesto_trasladado_api.py`, `test_fin_comercial_financiero_e2e.py`).

### Brechas principales
- Cerrar diseño definitivo de caja/pagos en frontera operativo-financiero.
- Estabilizar contratos de liquidaciones (recupero/impuestos/punitorios) en escenarios borde.
- Completar cobertura e2e de reconciliación financiera.

### Riesgos
- Corrupción de saldos por errores de imputación/regeneración.
- Riesgo alto de regresión por acoplamiento entre SQL patches y servicios.

### Dependencias
- CORE-EF (eventos confiables).
- Comercial y locativo (origen de obligaciones).
- Operativo para delimitación de caja física vs financiera.

### Próximos issues sugeridos
1. Especificación y test contract de frontera caja operativa/caja financiera.
2. Suite e2e de reconciliación saldo-obligación-imputación.
3. Checklist de release para migraciones SQL financieras.

### Orden recomendado de implementación
1. Congelar contrato de caja y pagos.
2. Fortalecer e2e y regresión financiera.
3. Optimizar auditoría y trazabilidad contable técnica.

### Qué NO tocar todavía
- Refactors estructurales de tablas financieras sin plan de migración + pruebas de composición.

### Prioridad
**alta**.

---

## 4) Locativo

**Estado actual:** **parcial**.

### Evidencias del repo
- Documentación de dominio en `DEV-API-LOCATIVO.md`, `SRV-LOC-*`, `LOC-DEC-*`.
- Router/schemas en `backend/app/api/routers/locativo_router.py` y `backend/app/api/schemas/locativo.py`.
- Repositorio dedicado `backend/app/infrastructure/persistence/repositories/locativo_repository.py`.
- Tests de solicitudes, reservas, contratos, condiciones y ciclo operativo locativo (`test_solicitudes_alquiler_*`, `test_reservas_locativas_*`, `test_contratos_alquiler_*`, `test_condiciones_economicas_alquiler_*`).

### Brechas principales
- Cerrar ciclo locativo-financiero extremo a extremo con cobertura homogénea.
- Completar gestión documental locativa con consistencia de numeración/trazabilidad.
- Validar casos excepcionales de rescisión/renovación en integración con ocupación.

### Riesgos
- Inconsistencias entre entrega/restitución y ocupación si hay eventos fuera de orden.
- Regresiones contractuales por reglas de negocio heterogéneas entre endpoints.

### Dependencias
- Inmobiliario (ocupación).
- Financiero (obligaciones de canon/recuperos).
- CORE-EF para mensajería interna.

### Próximos issues sugeridos
1. Matriz de estados de contrato locativo + transición permitida.
2. E2E solicitud→reserva→contrato→entrega→restitución con asserts financieros.
3. Gap analysis de documentación locativa vs implementación.

### Orden recomendado de implementación
1. Estabilizar transición de estados.
2. Cerrar integración financiera.
3. Completar documental locativo.

### Qué NO tocar todavía
- Re-diseñar modelo semántico locativo sin cerrar primero la transición de estados implementada.

### Prioridad
**media-alta**.

---

## 5) Administrativo / usuarios / sucursales / instalación

**Estado actual:** **parcial / no auditado en profundidad**.

### Evidencias del repo
- Diseño en `SRV-ADM-*` y `SRV-OPE-001` (sucursales), `SRV-OPE-002` (instalaciones).
- En código, la presencia de routers se concentra en dominios de negocio principales; no se verificó una superficie equivalente de administración completa en esta pasada.
- Existen rutas técnicas/health, pero no reemplazan administración funcional.

### Brechas principales
- Confirmar implementación real de usuarios/roles/permisos/autorizaciones vs diseño DEV-SRV.
- Completar administración de sucursales/instalaciones con evidencia de tests dedicados.

### Riesgos
- Controles de acceso incompletos o implícitos.
- Operación multi-sucursal sin gobierno administrativo consistente.

### Dependencias
- Definición de seguridad transversal.
- Operativo para sucursales/instalaciones.

### Próximos issues sugeridos
1. Auditoría de implementación ADM/OPE administrativa (doc vs código vs tests).
2. Plan incremental de usuarios/roles/permisos por contratos API explícitos.
3. Tests de autorización por endpoint crítico.

### Orden recomendado de implementación
1. Auditoría técnica de estado real.
2. Cierre mínimo de seguridad funcional.
3. Gobierno multi-sucursal/instalación.

### Qué NO tocar todavía
- Introducir IAM externo complejo sin cerrar primero el modelo interno mínimo.

### Prioridad
**media**.

---

## 6) Documental / numeración

**Estado actual:** **parcial**.

### Evidencias del repo
- Diseño documental en `SRV-DOC-*`, `SRV-COM-007`, `SRV-ANA-006`.
- Implementaciones comerciales relacionadas (instrumentos/escrituración) visibles en comandos/servicios comerciales.
- Tests de instrumentos/escrituraciones (`test_instrumentos_compraventa_*`, `test_escrituraciones_*`).

### Brechas principales
- Numeración/documento lógico transversal consolidado (sin invadir dominios).
- Plantillas y asociaciones documentales con contrato unificado.

### Riesgos
- Duplicidad de numeraciones o documentos huérfanos.
- Acoplar semántica documental en dominios que no son documental.

### Dependencias
- Comercial y locativo como emisores de documentos.
- Financiero para comprobantes específicos.

### Próximos issues sugeridos
1. Modelo mínimo de numeración documental transversal (acotado).
2. Contrato de asociación documental por dominio productor.
3. Tests de unicidad y trazabilidad documental.

### Orden recomendado de implementación
1. Definir numeración mínima.
2. Integrar productores prioritarios (comercial/financiero).
3. Expandir a locativo/operativo.

### Qué NO tocar todavía
- Centralizar todo documento en un mega-servicio sin límites de ownership.

### Prioridad
**media**.

---

## 7) Operativo

**Estado actual:** **pendiente/parcial (según subárea)**.

### Evidencias del repo
- Diseño en `DEV-ARCH-OPE-001` y `SRV-OPE-*` (caja operativa, cierres, sucursales, instalaciones).
- En app no se observó una superficie equivalente completa en routers/services para caja operativa y cierre con el mismo nivel de madurez que comercial/financiero.

### Brechas principales
- Materializar SRV-OPE-003/004/005 en implementación verificable.
- Separación estricta operativo (caja física) vs financiero (obligaciones/saldos).

### Riesgos
- Mezcla de responsabilidades caja operativa/caja financiera.
- Falta de trazabilidad de cierres operativos.

### Dependencias
- Administrativo (usuarios/sucursales).
- Financiero (interfaz de registración contable).

### Próximos issues sugeridos
1. Diseño técnico API+servicios mínimos de caja operativa.
2. Implementación de cierre de caja con invariantes y auditoría.
3. Tests de frontera operativo-financiero.

### Orden recomendado de implementación
1. Contrato de frontera OPE-FIN.
2. Caja operativa mínima.
3. Cierre y reportes operativos.

### Qué NO tocar todavía
- Mezclar lógica de obligaciones financieras dentro de caja operativa.

### Prioridad
**alta** (por riesgo de dominio y operación diaria).

---

## 8) CORE-EF / infraestructura transversal / sincronización

**Estado actual:** **parcial (mínimo operativo, falta cierre integral)**.

### Evidencias del repo
- Documentos `CORE-EF-001*`, matriz de cumplimiento write, validación CORE-EF.
- Decisión de outbox transaccional (`CORE-DEC-OUTBOX-001`).
- Implementación `outbox_repository.py`, `inbox_repository.py`, worker `outbox_to_inbox_worker.py`, dispatcher inbox financiero.
- Tests `test_outbox_events.py`, `test_outbox_inbox.py`, `test_outbox_to_inbox_worker.py`.

### Brechas principales
- Gobernar retries, DLQ lógica, observabilidad y métricas de sincronización.
- Cerrar cobertura transversal para todos los comandos write críticos.
- Reglas de resolución de conflictos distribuidos (SRV-TEC-003/004).

### Riesgos
- Procesamiento duplicado o pérdida de eventos en escenarios de fallo.
- Divergencia entre dominios por sincronización incompleta.

### Dependencias
- Todos los dominios write (comercial, inmob., financiero, locativo).

### Próximos issues sugeridos
1. Checklist CORE-EF por endpoint write crítico (matriz ejecutable).
2. Métricas y alarmas de outbox/inbox.
3. Estrategia de reintentos y conflictos por tipo de evento.

### Orden recomendado de implementación
1. Cerrar checklist mínimo en write críticos.
2. Observabilidad y alertas.
3. Escalar a sincronización distribuida avanzada.

### Qué NO tocar todavía
- Sobrediseñar arquitectura distribuida avanzada sin cerrar confiabilidad mínima actual.

### Prioridad
**alta**.

---

## 9) Frontend Flet

**Estado actual:** **no auditado en esta pasada (foco backend/documentación)**.

### Evidencias del repo
- Existe `backend/database/README-demo-ui.md` y seed demo UI, pero la auditoría solicitada se concentró en backend/documentación.

### Brechas principales
- Inventario real de pantallas y cobertura de flujos backend.
- Estado de contratos API consumidos por UI.

### Riesgos
- Desalineación backend-frontend en contratos/validaciones.

### Dependencias
- Estabilización de contratos API en comercial, locativo, inmobiliario y financiero.

### Próximos issues sugeridos
1. Auditoría de frontend contra DEV-API vigente.
2. Matriz endpoint↔pantalla↔test e2e.
3. Plan de cierre de flujos críticos (venta directa, reservas, pagos, locativo).

### Orden recomendado de implementación
1. Auditoría de contratos.
2. Cierre de flujos críticos.
3. Endurecimiento UX/errores.

### Qué NO tocar todavía
- Refactor visual amplio sin antes congelar contratos API prioritarios.

### Prioridad
**media**.

---

## 10) Reportes / analítico

**Estado actual:** **pendiente/parcial (diseño amplio, implementación no confirmada integralmente)**.

### Evidencias del repo
- Arquitectura analítica explícita read-only (`DEV-ARCH-ANA-001`, `SRV-ANA-*`).
- Existe documentación extensa de consultas analíticas por dominio.
- En esta pasada no se verificó una superficie de routers/services analíticos equiparable al volumen documental.

### Brechas principales
- Materializar consultas analíticas prioritarias con contratos API verificables.
- Definir estrategia de consistencia de datos para reportes cross-domain.

### Riesgos
- Invadir dominios write al implementar reportes (violación de arquitectura).
- Métricas inconsistentes por fuentes no homologadas.

### Dependencias
- CORE-EF (sincronización confiable).
- Financiero/comercial/locativo/inmobiliario estables.

### Próximos issues sugeridos
1. MVP analítico read-only (top 10 consultas de negocio).
2. Contratos de consulta con filtros/paginación/corte temporal.
3. Tests de consistencia y no mutación (read-only enforcement).

### Orden recomendado de implementación
1. MVP consultas críticas.
2. Homologación de fuentes y métricas.
3. Escalar a reporting consolidado.

### Qué NO tocar todavía
- Acciones write disfrazadas en endpoints analíticos.

### Prioridad
**media-baja** (sube cuando operaciones core estén estables).

---

## Roadmap por fases

### Fase 1 — estabilización técnica/comercial inmediata
- Cerrar gaps de contratos y validaciones en comercial e inmobiliario.
- Reforzar regresión de flujos críticos ya implementados.
- Asegurar coherencia de eventos comerciales→inmobiliario→financiero.

### Fase 2 — cerrar CORE-EF mínimo
- Cumplimiento mínimo de outbox/inbox en todos los write críticos.
- Idempotencia y observabilidad operativa básica.
- Reglas de retry y manejo de fallos repetibles.

### Fase 3 — financiero/caja/pagos/documentos
- Congelar frontera operativo-financiero.
- Endurecer obligaciones, imputaciones y pagos con e2e.
- Definir núcleo documental/numeración mínimo integrado.

### Fase 4 — locativo completo
- Cerrar transición de estados y casos excepcionales.
- Integración completa locativo↔inmobiliario↔financiero.
- Cobertura e2e de ciclo locativo completo.

### Fase 5 — administrativo real
- Auditar y completar usuarios/roles/permisos/autorizaciones.
- Consolidar sucursales e instalaciones operativas.
- Endurecer controles de acceso por endpoint.

### Fase 6 — frontend completo
- Alinear contratos API y pantallas críticas.
- Cerrar flujos de punta a punta con criterios de UX y errores.
- Consolidar matriz endpoint↔pantalla↔tests.

### Fase 7 — reporting/analítico/sync distribuida avanzada
- MVP analítico read-only consolidado.
- Reportería cross-domain con fuentes homologadas.
- Evolución de sincronización distribuida avanzada.

---

## Criterios de prioridad aplicados

Se prioriza en este orden:
1. Evitar corrupción de datos.
2. Desbloquear flujos de negocio críticos.
3. Reducir deuda transversal (CORE-EF/contratos).
4. Aprovechar áreas con cobertura de tests existente.
5. Evitar expansión de pagos/caja sin diseño de frontera cerrado.

---

## Resumen ejecutivo de dominios

- **Alta prioridad inmediata**: Comercial, Inmobiliario, CORE-EF, Operativo (frontera OPE-FIN), Financiero.
- **Prioridad media**: Locativo, Administrativo, Documental/Numeración, Frontend.
- **Prioridad media-baja inicial**: Analítico/Reportes (sube al estabilizar core transaccional).

---

## Backlog sugerido de issues (lista consolidada)

1. **[CORE-EF]** Checklist de cumplimiento write crítico por endpoint + métricas outbox/inbox.
2. **[COM]** Auditoría de contratos comercial vs tests + cierre de edge cases venta directa.
3. **[INM]** Hardening idempotencia consumers y consistencia disponibilidad/ocupación.
4. **[FIN/OPE]** Diseño y test de frontera caja operativa vs financiera.
5. **[FIN]** Suite e2e de reconciliación obligación-imputación-pago-saldo.
6. **[LOC]** Matriz de estados de contrato locativo y transición permitida.
7. **[DOC]** Núcleo mínimo de numeración documental transversal.
8. **[ADM]** Auditoría implementación usuarios/roles/permisos/autorizaciones.
9. **[FLET]** Matriz contrato API ↔ pantalla ↔ caso de prueba.
10. **[ANA]** MVP top consultas read-only con criterios de consistencia.

---

## Próximos 5 pasos concretos

1. Ejecutar **auditoría rápida de contratos** (COM/INM/FIN) contra tests existentes y documentar gaps.
2. Implementar **checklist CORE-EF mínimo** en endpoints write críticos faltantes.
3. Definir y aprobar **frontera OPE-FIN** (caja operativa vs caja financiera) antes de nuevos features de pago.
4. Cerrar **e2e crítico de reconciliación financiera** con datos semilla reproducibles.
5. Publicar **matriz priorizada de issues** con responsables, dependencias y criterio de aceptación por dominio.

