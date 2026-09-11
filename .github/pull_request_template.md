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
- Identidad humana/técnica:
- Autorización:
- Contexto de sucursal:
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

### Alcance

### Fuera de alcance

### Riesgos / NO CONFIRMADO

### Checklist PROJECT-STATUS

- [ ] Evalué si este PR cambia el estado operativo del proyecto.
- [ ] El body contiene exactamente una decisión `PROJECT-STATUS impact`.
- [ ] La decisión no está vacía ni conserva placeholders.
- [ ] Actualicé `PROJECT-STATUS.md`, si corresponde.
- [ ] Preservé las secciones de otros frentes.
- [ ] Verifiqué issues y PRs citados el mismo día.
- [ ] Releí `PROJECT-STATUS.md` después del paso aplicable a este PR:
  rebase contra `origin/main` para PR normal;
  rebase contra `origin/transition/central-authority` para PR incremental de transición;
  merge de `main` en la rama de trabajo para PR de sincronización hacia la transición;
  o sincronización final y verificación de gates ya definidas en `CODEX-WORKFLOW.md` §6.1 y `DEV-ARCH-GEN-002` §11 para el PR final hacia `main`, sin rebase de la rama compartida.
- [ ] Si no corresponde actualizarlo, documenté `NO APLICA` con motivo.
