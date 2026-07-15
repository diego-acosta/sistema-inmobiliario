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
6. **Validación**
   - Ejecutar suite mínima relacionada.
   - Ejecutar `git diff --check`.
   - Revisar diff completo.
7. **Commit**
   - Confirmar que el diff corresponde al alcance.
   - Usar mensaje claro y trazable.
8. **Push**
   - Subir la rama acordada.
9. **PR draft**
   - Abrir PR draft con descripción, decisión CORE-EF y tests reales.
10. **Cierre**
   - No cerrar issues funcionales salvo que el usuario lo indique.
   - Dejar pendientes y `NO CONFIRMADO` explícitos.

## 6. Plantilla estándar de issue

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

## 7. Plantilla estándar de prompt para Codex

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

## 8. Clasificación CORE-EF

Usar exactamente las clasificaciones vigentes indicadas por `AGENTS.md`:

- `COMMAND_WRITE_NEGOCIO`
- `COMMAND_WRITE_TECNICO`
- `SIMULACION_READLIKE`
- `PREVIEW_READLIKE`
- `QUERY_READLIKE`
- `NO_CONFIRMADO`

### 8.1 Writes sincronizables

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

### 8.2 Read-like, simulación y preview

Deben justificar explícitamente:

- Ausencia de headers write.
- Ausencia de outbox.
- Ausencia de locks.
- Ausencia de modificación de versiones.
- Ausencia de efectos laterales persistentes.

## 9. Reglas por tipo de archivo

### 9.1 SQL

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

### 9.2 Services

- Mantener reglas de negocio en el dominio dueño.
- No llamar lógica de otro dominio para redefinirla.
- Explicitar frontera transaccional.
- No ocultar errores de dominio como errores técnicos genéricos.

### 9.3 Repositories

- Reflejar SQL real y locks/versionado si aplican.
- No implementar reglas de negocio primarias que pertenecen al service, salvo validaciones de persistencia.
- Mantener consultas coherentes con soft delete y estados existentes.

### 9.4 Routers

- Mantener contratos DEV-API.
- Usar helpers CORE-EF comunes en writes sincronizables.
- No inventar endpoints.
- Preservar envelopes y `ErrorResponse` estándar.

### 9.5 Schemas

- No mezclar DTOs de dominios distintos.
- Validar enums/estados contra catálogos y SQL.
- No introducir campos no persistidos o no calculados sin marcarlos como derivados/documentales.

### 9.6 Tests

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

### 9.7 Documentación

- Actualizar solo documentación afectada por el incremento.
- No copiar arquitectura completa.
- Distinguir implementado, documentado, pendiente y `NO CONFIRMADO`.
- Referenciar issues/PRs reales si se citan estados.

## 10. Plantilla de descripción de PR

```markdown
### Motivation

### Description

### Decisión CORE-EF
- Clasificación:
- Headers:
- If-Match-Version:
- Idempotencia:
- Outbox:
- Lock lógico:
- Versionado:
- Transacción/Rollback:
- Tests CORE-EF:

Para cambios exclusivamente documentales: `NO APLICA`, indicando que no hay endpoints, writes, persistencia ni sincronización.

### Testing
- `comando ejecutado`
- revisión manual realizada

### Alcance

### Fuera de alcance

### Riesgos / NO CONFIRMADO
```

## 11. Checklist de cierre

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
