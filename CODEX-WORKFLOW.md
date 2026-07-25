# CODEX-WORKFLOW — Flujo estándar de trabajo con Codex

## 1. Propósito

Estandarizar cómo preparar, ejecutar y cerrar tareas con Codex en este repositorio. Este documento complementa `AGENTS.md`; no lo reemplaza ni relaja sus reglas.

## 2. Prevalencia de `AGENTS.md`

`AGENTS.md` prevalece sobre este archivo. Si hay conflicto, seguir `AGENTS.md` y corregir este workflow en un PR documental separado.

Orden operativo de verdad:

1. `AGENTS.md`.
2. Arquitectura formal en `backend/documentacion/DEV-ARCH/`.
3. SQL real.
4. Implementación real: routers, schemas, services y repositories.
5. Tests reales.
6. Issues y PR vigentes.
7. `PROJECT-STATUS.md`, como orientación operativa.
8. `CODEX-WORKFLOW.md`, como procedimiento de trabajo.
9. Documentación histórica o de diseño no validada.

`PROJECT-STATUS.md` orienta qué frente revisar primero, pero no puede contradecir arquitectura, SQL, implementación ni tests.

## 3. Lectura obligatoria antes de trabajar

Antes de modificar código, documentación contractual o SQL, Codex debe leer:

- `AGENTS.md`.
- `PROJECT-STATUS.md`.
- `CODEX-WORKFLOW.md`.
- Issue objetivo, epic, dependencias y PRs relacionados.
- DEV-ARCH correspondiente.
- DEV-SRV y DEV-API del dominio afectado.
- SQL, routers, schemas, services, repositories y tests existentes.

Si detecta contradicción, ambigüedad o falta de evidencia, debe informarla antes de implementar.

## 4. Principios de trabajo

- No diseñar libremente: todo cambio debe estar respaldado por arquitectura, implementación real o issue explícito.
- Clasificar cada concepto como núcleo del dominio, soporte transversal o compatibilidad heredada.
- No mezclar dominios ni mover ownership semántico.
- No afirmar implementación sin evidencia en SQL/backend/tests.
- No declarar tests ejecutados si no se ejecutaron.
- Mantener PRs incrementales y revisables.
- Para documentación, distinguir implementado, documentado, pendiente, en auditoría, fuera de alcance y `NO CONFIRMADO`.

## 5. Ciclo estándar

1. **Orientación**
   - Verificar rama y working tree.
   - Leer instrucciones y estado del proyecto.
   - Identificar dominio, entidad raíz y clasificación CORE-EF.
2. **Auditoría**
   - Revisar arquitectura, SQL, backend y tests.
   - Revisar issue/epic/PRs relacionados.
   - Registrar contradicciones o faltantes.
3. **Definición del incremento**
   - Delimitar alcance y fuera de alcance.
   - Confirmar qué archivos pueden tocarse.
4. **Creación o revisión del issue**
   - Si no hay issue, no inventar alcance funcional; pedir/crear issue según permisos del flujo humano.
   - Si hay issue, validar que no contradiga arquitectura ni implementación.
5. **Implementación**
   - Modificar solo lo necesario.
   - Mantener CORE-EF desde el primer commit cuando aplique.
6. **Evaluación de impacto en `PROJECT-STATUS`**
   - Evaluar impacto; actualizar el archivo o resolver la decisión `NO APLICA` con motivo.
   - Verificar que se preservan los otros frentes y que la decisión es única, no está vacía ni conserva placeholders.
7. **Validación**
   - Ejecutar suite mínima relacionada.
   - Ejecutar `git diff --check`.
   - Revisar el diff completo, incluida la actualización de `PROJECT-STATUS.md` cuando corresponda.
8. **Commit**
   - Confirmar que el diff corresponde al alcance.
   - Usar mensaje claro y trazable.
9. **Push**
   - Subir la rama acordada.
10. **PR draft**
   - Abrir o actualizar el PR draft con descripción, decisión CORE-EF, la decisión de impacto ya resuelta y tests reales.
   - Copiar al body exactamente una línea activa `PROJECT-STATUS impact:`.
11. **Cierre**
   - No cerrar issues funcionales salvo que el usuario lo indique.
   - Dejar pendientes y `NO CONFIRMADO` explícitos.

## 6. Control obligatorio de `PROJECT-STATUS` antes del merge

Antes de declarar un PR listo para merge, se debe evaluar si cambia alguno de estos elementos:

- estado operativo de un frente;
- issue o epic principal;
- próximo incremento recomendado;
- decisión funcional vigente;
- decisión arquitectónica vigente;
- contrato API relevante;
- baseline verificable de tests;
- bloqueo o dependencia entre issues;
- último PR relevante del frente.

### Regla de decisión

Si cambia alguno, el body del PR debe declarar:

```text
PROJECT-STATUS impact: UPDATED
```

Además, se debe actualizar `PROJECT-STATUS.md` dentro del mismo PR, limitar la modificación al frente afectado, preservar las secciones de otros frentes, verificar los estados de GitHub el mismo día, releer el archivo después de rebasear contra `origin/main` e incluir el cambio en el review final.

Si no cambia ninguno, el body del PR debe declarar:

```text
PROJECT-STATUS impact: NO APLICA — <motivo>
```

El motivo debe explicarse brevemente. Ningún PR se debe declarar listo para merge sin una de estas dos decisiones.

El body debe contener exactamente una línea activa `PROJECT-STATUS impact:`. La decisión no puede quedar vacía, conservar `<motivo>` ni presentar simultáneamente `UPDATED` y `NO APLICA`; si es vacía, contiene placeholders o resulta ambigua, el PR no está listo para merge.

### Cuándo corresponde actualizar

Normalmente corresponde actualizar ante nueva funcionalidad completa; cierre de un issue que era próximo foco; creación o eliminación de un bloqueo; nuevo contrato API relevante; cambio de regla de negocio u ownership; saneamiento de suite que cambia el baseline; cambio de roadmap; o auditoría que redefine el próximo incremento.

Normalmente no corresponde ante un refactor interno sin cambio observable; test adicional aislado; corrección tipográfica; cleanup; optimización sin impacto operativo; o fix menor que no cambia decisiones ni próximos pasos. Estos ejemplos no reemplazan la evaluación real de cada PR.

### Regla para trabajo paralelo y rebase

Cada PR solo puede modificar la fila resumen y la sección del frente que le pertenece, salvo orquestación interdominio explícita y justificada. Comercial/Financiero no debe reescribir Administrativo; Administrativo no debe reescribir Comercial/Financiero; Operativo no debe modificar ambos salvo un cambio transversal documentado.

Antes de editar `PROJECT-STATUS.md`, ejecutar:

```bash
git fetch origin
git rebase origin/main
```

Después del rebase se debe volver a leer `PROJECT-STATUS.md`, no aplicar una versión guardada anteriormente y resolver cualquier conflicto preservando los cambios ya mergeados de otros frentes.

## 7. Plantilla estándar de issue

```markdown
## Contexto

## Objetivo

## Alcance

## Fuera de alcance

## Arquitectura y ownership
- Dominio responsable:
- Entidad raíz:
- Clasificación del concepto: núcleo / soporte transversal / compatibilidad heredada
- Dependencias interdominio:

## Decisiones vigentes

## Clasificación CORE-EF
- Tipo: COMMAND_WRITE_NEGOCIO / COMMAND_WRITE_TECNICO / SIMULACION_READLIKE / PREVIEW_READLIKE / QUERY_READLIKE / NO_CONFIRMADO
- Headers:
- If-Match-Version:
- Idempotencia:
  - mismo op_id + mismo payload:
  - mismo op_id + payload distinto:
  - retry post-error:
- Outbox:
- Lock lógico:
- Versionado:
- Frontera transaccional:
- Rollback:

## Criterios de aceptación

## Tests esperados
- Happy path:
- Validaciones:
- Recurso inexistente:
- Estados incompatibles:
- Headers faltantes/inválidos:
- Versión faltante/inválida:
- Mismatch real:
- Idempotencia:
- Rollback:
- Outbox:
- Locks:
- Ausencia de efectos laterales:
- PostgreSQL real:

## Documentación

## Dependencias
```

## 8. Plantilla estándar de prompt para Codex

```markdown
Trabajá sobre `diego-acosta/sistema-inmobiliario`.

## Lectura obligatoria
- `AGENTS.md`
- `PROJECT-STATUS.md`
- `CODEX-WORKFLOW.md`
- Issue: #...
- Epic/dependencias/PRs relacionados: ...
- DEV-ARCH/DEV-SRV/DEV-API del dominio
- SQL/backend/tests reales

## Objetivo

## Alcance

## Fuera de alcance

## Dominio responsable

## Entidad raíz

## Restricciones arquitectónicas

## Decisión CORE-EF
- Clasificación:
- Headers:
- If-Match-Version:
- Idempotencia:
- Outbox:
- Lock:
- Versionado:
- Transacción/Rollback:

## Implementación esperada
- SQL:
- Router:
- Schema:
- Service:
- Repository:
- Tests:
- Documentación:

## Tests mínimos

## Flujo Git
- Crear rama específica.
- Verificar working tree limpio antes y después.
- Commit.
- Push.
- Abrir PR draft.

## Contenido obligatorio del PR
- Motivation
- Description
- Decisión CORE-EF
- Testing real
- Alcance
- Fuera de alcance
```

## 9. Clasificación CORE-EF

Usar exactamente las clasificaciones vigentes indicadas por `AGENTS.md`:

- `COMMAND_WRITE_NEGOCIO`
- `COMMAND_WRITE_TECNICO`
- `SIMULACION_READLIKE`
- `PREVIEW_READLIKE`
- `QUERY_READLIKE`
- `NO_CONFIRMADO`

### 9.1 Writes sincronizables

Deben documentar y probar, según aplique:

- Headers obligatorios: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`.
- `If-Match-Version` cuando modifica entidad existente/versionada.
- Uso del helper común CORE-EF; no parsear headers manualmente.
- ErrorResponse estándar; no devolver `{"detail": "..."}` desde errores de headers del handler.
- Idempotencia: criterio de payload, mismo `op_id` + mismo payload, mismo `op_id` + payload distinto, retry post-error.
- Outbox: evento y misma transacción que negocio, o `NO APLICA` con justificación.
- Lock lógico: entidad bloqueada y operaciones incompatibles, o `NO APLICA`.
- Versionado: entidad versionada y uso de `version_registro`.
- Frontera transaccional y rollback.
- Tests mínimos exigidos por `AGENTS.md`.

### 9.2 Read-like, simulación y preview

Deben justificar explícitamente:

- Ausencia de headers write.
- Ausencia de outbox.
- Ausencia de locks.
- Ausencia de modificación de versiones.
- Ausencia de efectos laterales persistentes.

## 10. Reglas por tipo de archivo

### 10.1 SQL

Cuando corresponda:

- Usar patches incrementales.
- Integrar reset Windows con `backend/scripts/reset_db.bat`.
- Integrar reset Linux/Codex Cloud con `backend/scripts/reset_db.sh`.
- Mantener el mismo orden de scripts en ambos resets.
- Validar en PostgreSQL real si el cambio toca persistencia.
- Definir constraints, índices y triggers necesarios.
- Agregar tests SQL o de integración si aplica.
- Documentar rollback o reversión funcional.
- No modificar scripts históricos sin justificación explícita.

### 10.2 Services

- Mantener reglas de negocio en el dominio dueño.
- No llamar lógica de otro dominio para redefinirla.
- Explicitar frontera transaccional.
- No ocultar errores de dominio como errores técnicos genéricos.

### 10.3 Repositories

- Reflejar SQL real y locks/versionado si aplican.
- No implementar reglas de negocio primarias que pertenecen al service, salvo validaciones de persistencia.
- Mantener consultas coherentes con soft delete y estados existentes.

### 10.4 Routers

- Mantener contratos DEV-API.
- Usar helpers CORE-EF comunes en writes sincronizables.
- No inventar endpoints.
- Preservar envelopes y `ErrorResponse` estándar.

### 10.5 Schemas

- No mezclar DTOs de dominios distintos.
- Validar enums/estados contra catálogos y SQL.
- No introducir campos no persistidos o no calculados sin marcarlos como derivados/documentales.

### 10.6 Tests

Según el cambio, cubrir:

- Happy path.
- Validaciones.
- Recurso inexistente.
- Estados incompatibles.
- Headers faltantes e inválidos.
- Versión faltante o inválida.
- Mismatch real.
- Idempotencia.
- Mismo `op_id` con payload diferente.
- Rollback.
- Outbox.
- Locks.
- Ausencia de efectos laterales.
- Tests PostgreSQL.
- Suite relacionada.
- Compilación.
- `git diff --check`.

No declarar tests como ejecutados sin salida real de terminal.

### 10.7 Documentación

- Actualizar solo documentación afectada por el incremento.
- No copiar arquitectura completa.
- Distinguir implementado, documentado, pendiente y `NO CONFIRMADO`.
- Referenciar issues/PRs reales si se citan estados.

## 11. Plantilla de descripción de PR

```markdown
### Motivation

### Description

### PROJECT-STATUS

<!-- Escribí exactamente una decisión:
PROJECT-STATUS impact: UPDATED
PROJECT-STATUS impact: NO APLICA — <motivo>
No dejes el campo vacío, no conserves <motivo> y no hagas coexistir ambas decisiones.
-->

PROJECT-STATUS impact:

### Decisión CORE-EF
<!-- Clasificaciones vigentes: COMMAND_WRITE_NEGOCIO, COMMAND_WRITE_TECNICO,
SIMULACION_READLIKE, PREVIEW_READLIKE, QUERY_READLIKE o NO_CONFIRMADO. -->
- Clasificación:
- Naturaleza del endpoint:
- Headers:
- If-Match-Version:
- Idempotencia:
- Outbox:
- Lock lógico:
- Versionado:
- Frontera transaccional / rollback:
- Tests CORE-EF ejecutados:

Para cambios exclusivamente documentales o cuando no corresponda: `NO APLICA — <justificación breve>`.

Para `SIMULACION_READLIKE`, `PREVIEW_READLIKE` y `QUERY_READLIKE`, explicar por qué no requiere headers write.

### Testing
- `comando ejecutado`
- revisión manual realizada

### Alcance

### Fuera de alcance

### Riesgos / NO CONFIRMADO
```

## 12. Checklist de cierre

- [ ] `AGENTS.md`, `PROJECT-STATUS.md` y `CODEX-WORKFLOW.md` leídos.
- [ ] Issue, epic y PRs relacionados revisados.
- [ ] Dominio y ownership validados.
- [ ] SQL/backend/tests auditados.
- [ ] CORE-EF documentado o marcado `NO APLICA` con justificación.
- [ ] Tests relacionados ejecutados o limitación explicitada.
- [ ] `git diff --check` ejecutado.
- [ ] Diff completo revisado.
- [ ] Solo se tocaron archivos dentro del alcance.
- [ ] Commit realizado.
- [ ] Push realizado.
- [ ] PR draft abierto con tests reales y fuera de alcance.
- [ ] Impacto en `PROJECT-STATUS` evaluado y decisión incluida en el body del PR.
- [ ] El body contiene exactamente una decisión `PROJECT-STATUS impact`.
- [ ] La decisión no está vacía ni conserva placeholders.
- [ ] `PROJECT-STATUS.md` actualizado o `NO APLICA` documentado con motivo.
- [ ] Otros frentes preservados al actualizar `PROJECT-STATUS.md`.

## 13. Review final obligatorio

Al preparar un PR, el entregable final de Codex debe incluir esta tabla:

| Verificación | Resultado |
| --- | --- |
| Impacto en PROJECT-STATUS evaluado | PASS/FAIL |
| PROJECT-STATUS actualizado | PASS/FAIL/NO APLICA |
| Otros frentes preservados | PASS/FAIL/NO APLICA |
| Estados GitHub verificados | PASS/FAIL/NO APLICA |
| Decisión incluida en body del PR | PASS/FAIL |
| Decisión de impacto única y no ambigua | PASS/FAIL |
