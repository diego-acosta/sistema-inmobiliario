# DEV-SRV Administrativo — Replicación portable de `usuario` (#510)

## 1. Estado materializado

Este documento registra el contrato runtime implementado por #510 sobre el lifecycle que existe realmente en `main`.

Eventos materializados:

- `usuario_creado`;
- `usuario_desactivado`.

Eventos documentados en EVT-ADM pero todavía no materializados porque no existe command runtime correspondiente:

- `usuario_modificado`;
- `usuario_reactivado`.

Fuera de alcance de #510:

- `usuario_bloqueado`;
- `usuario_desbloqueado`;
- credenciales;
- sesiones;
- autenticación/tokens.

No se crea lifecycle Administrativo nuevo para completar contratos históricos.

## 2. Identidad y ownership

Identidad distribuida autoritativa:

```text
usuario.uid_global
```

`id_usuario` conserva naturaleza de PK local y no forma parte del payload portable. El destino genera su propia PK.

No existen fallbacks por:

- `id_usuario` remoto;
- `codigo_usuario`;
- `login`;
- email;
- `persona.uid_global`;
- `usuario_sucursal.uid_global`.

`codigo_usuario` y `login` son atributos funcionales. Una colisión con otro `uid_global` se clasifica como conflicto; nunca dispara merge.

Consumer dueño del efecto remoto:

```text
administrativo.usuario
```

La autoridad técnica de replay/conflicto continúa en `inbox_operation_scope` por:

```text
(consumer, op_id)
```

No existe ledger específico de usuario.

## 3. Producer y frontera transaccional local

Los commands HTTP ya existentes conservan su contrato observable:

```text
POST  /api/v1/administrativo/usuarios
PATCH /api/v1/administrativo/usuarios/{id_usuario}/baja
```

El repository coordina el commit de esos dos writes y sólo esos callers reales fueron encontrados para el lifecycle de usuario. Los commands consumen el claim/receipt global de `operacion_idempotente` materializado por #469/#470; el lock transaccional estable del claim serializa un mismo `op_id` incluso entre usuarios y commands distintos. #510 incorpora el `outbox_event` y el receipt antes de ese mismo commit:

```text
claim global de op_id
mutación usuario
→ resolver provenance portable de instalación
→ construir snapshot portable
→ INSERT outbox_event
→ complete_operation
→ commit
```

Si falla la resolución de provenance o el outbox:

```text
rollback usuario + outbox + receipt
```

Los replays locales nuevos se resuelven por el receipt global y no emiten un segundo evento. Un mismo `op_id` no puede identificar dos operaciones funcionales distintas, aunque apunten a usuarios diferentes. `op_id_alta` y `op_id_ultima_modificacion` conservan provenance row-local y sirven como evidencia compatible para datos legacy, pero no son la autoridad concurrente global. Para writes nuevos ejecutados bajo #510, si la mutación original existe, su outbox y receipt fueron confirmados en la misma transacción.

La garantía es prospectiva desde el despliegue de #510. Filas u operaciones históricas anteriores pueden conservar `op_id` sin un outbox de usuario asociado. Un retry histórico no repara ni reemite implícitamente ese outbox; backfill, reemisión y convergencia histórica pertenecen a un follow-up separado.

Los métodos destinados a aplicación remota no hacen `commit()` ni `rollback()`. La frontera exterior pertenece al processor de #512.

## 4. Envelope portable

El outbox de usuario transporta únicamente:

```json
{
  "aggregate_uid": "<usuario.uid_global>",
  "version_registro": 1,
  "op_id": "<X-Op-Id original>",
  "provenance": {
    "installation_uid": "<instalacion.uid_global del write origen>",
    "op_id_alta": "<mismo op_id del usuario_creado>"
  },
  "snapshot": {
    "codigo_usuario": "...",
    "login": "...",
    "email": null,
    "estado_usuario": "ACTIVO",
    "usuario_sistema_interno": false,
    "observaciones": null,
    "fecha_alta": "...",
    "fecha_baja": null,
    "deleted": false
  }
}
```

El `event_type` y `aggregate_type=usuario` pertenecen a la cabecera del outbox/inbox y no se duplican dentro del snapshot funcional.

Para `usuario_creado`, `estado_usuario` admite exactamente `ACTIVO` o `INACTIVO`, igual que `UsuarioSistemaCreateRequest`, con `deleted=false`, `fecha_baja=null` y versión 1. Para `usuario_desactivado`, exige `INACTIVO`, `deleted=true`, `fecha_baja` no nula y versión 2 o superior.

`codigo_usuario` y `login` se recortan con la misma normalización del request local; `estado_usuario` además se canonicaliza a mayúsculas antes de validar el conjunto permitido. Esta canonicalización y la de timestamps ocurren antes del claim, fingerprint y comparación material.

`provenance.installation_uid` conserva la identidad portable de la instalación que produjo el write. La PK `id_instalacion` del origen no viaja. El receptor no transforma esa procedencia en una FK local ni bloquea el usuario esperando que exista una fila de instalación equivalente: el dato queda retenido como procedencia técnica y participa del fingerprint de #512.

`provenance.op_id_alta` conserva exclusivamente la operación distribuida que creó la identidad. En `usuario_creado` es obligatorio, debe ser UUID válido y coincidir exactamente con el `op_id` del envelope. En `usuario_desactivado` puede ser un UUID distinto del `op_id` de baja o `null` cuando el origen no conoce la operación histórica de creación; la igualdad con el `op_id` de baja es payload inválido y nunca se sustituye por el `op_id` de una baja u operación posterior. `op_id_ultima_modificacion` conserva el `op_id` del evento aplicado.

Los timestamps portables usan una representación única compatible con las columnas `timestamp without time zone`: una entrada con timezone u offset se convierte al instante UTC, se elimina `tzinfo` después de esa conversión y se serializa como ISO UTC-naive. Una entrada naive se interpreta como ya expresada en esa convención. Para los writes locales cubiertos, el producer garantiza esa precondición en el write boundary: alta escribe `fecha_alta`/`updated_at` y baja escribe `fecha_baja`/`deleted_at`/`updated_at` mediante `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'`, independientemente del `TimeZone` de la sesión PostgreSQL. No se reinterpreta después una wall-time naive cuya zona ya se perdió. La canonicalización ocurre antes de claim, fingerprint y comparación de snapshots; no usa el reloj local del worker. Un datetime inválido o no representable al convertir su offset termina como `REJECTED / SYNC_PAYLOAD_INVALID`.

No viajan:

- `id_usuario`;
- `id_instalacion` remoto;
- `fecha_ultimo_acceso`;
- password;
- `hash_credencial`;
- tokens;
- bearer;
- cookies;
- refresh tokens;
- datos de `credencial_usuario`;
- datos de `sesion_usuario`;
- secretos equivalentes.

El DTO receptor es exacto/default-deny: campos extras invalidan el payload.

## 5. Registro en inbox y PK legacy

La registración portable reutiliza `InboxRepository.claim()` de #512.

Para el contrato de usuario:

- `event_id` = identidad de delivery;
- `op_id` = identidad distribuida de operación;
- `aggregate_uid` = `usuario.uid_global`;
- `version_registro` = versión autoritativa entrante;
- `provenance.installation_uid` = procedencia técnica portable;
- `consumer` = `administrativo.usuario`.

El campo `aggregate_id` heredado del inbox se registra con valor neutro `0`; la PK del origen no se transporta ni se usa para resolver/aplicar el usuario.

El estado técnico inicial que #512 usa para una delivery portable puede ser `PENDING_DEPENDENCY` como estado elegible de cola. El applicator de usuario **nunca** devuelve `PENDING_DEPENDENCY` por ausencia de persona, rol, sucursal o instalación origen: esas relaciones no son dependencia funcional del snapshot mínimo.

## 6. Aplicación remota

El applicator Administrativo:

1. revalida `event_type`, aggregate, UID, versión, provenance y snapshot;
2. resuelve exclusivamente por `UsuarioSistemaRepository.get_by_uid_global()`;
3. detecta colisiones de `codigo_usuario`/`login` con otro UID;
4. decide replay/conflicto/versionado;
5. persiste alta o CAS remoto;
6. devuelve `InboxOutcome` a #512;
7. no confirma ni revierte la transacción exterior.

## 7. Matriz de versionado remoto

Contrato congelado por #510:

```text
UID ausente + snapshot completo aplicable
→ crear preservando uid_global, incluso para `usuario_desactivado` fuera de orden
→ PK local independiente
→ conservar incoming version_registro

UID presente + local_version < incoming_version
→ aplicar snapshot completo mediante CAS

misma versión + mismo snapshot funcional
→ replay compatible; no mutar

misma versión + snapshot funcional distinto
→ CONFLICTO

incoming_version < local_version
→ operación obsoleta; no revertir estado

UID distinto + codigo_usuario/login en uso
→ CONFLICTO
```

No se usa timestamp como LWW y no existe merge automático.

### Saltos de versión

#510 adopta `version_registro` como versión autoritativa comparable de un snapshot completo y acepta un salto remoto, por ejemplo `V1 → V3`, cuando la versión entrante es mayor. Toda mutación local continúa incrementando exactamente `+1`; la recepción remota no exige `local_version + 1`.

Fundamento: CORE-EF exige que cada mutación **local** incremente en uno y que la comparación remota use `version_registro` como criterio primario, pero no exige recepción secuencial de todas las versiones intermedias. Rechazar saltos haría depender la convergencia de una entrega ordenada que el contrato de consistencia eventual no garantiza.

La aplicación sigue siendo CAS contra la versión local observada; no se realiza overwrite ciego.

## 8. Baja y reactivación

`usuario_desactivado` exige snapshot coherente:

```text
estado_usuario = INACTIVO
fecha_baja != null
deleted = true
```

Una versión superior desactiva por UID y conserva la baja lógica.

Si `usuario_desactivado` V2 o superior llega antes del alta y el UID no existe, el snapshot completo y coherente materializa una fila local ya inactiva, con el UID recibido, PK local propia e `incoming version_registro`. No es `PENDING_DEPENDENCY`. Un snapshot de baja exige `estado_usuario = INACTIVO`, `fecha_baja != null` y `deleted = true`; cualquier incoherencia termina `REJECTED`.

No existe command runtime de reactivación al momento de #510. Por lo tanto:

- no se habilita `usuario_reactivado`;
- `usuario_creado` no puede reutilizarse para revivir un usuario local ya dado de baja;
- cuando Administrativo materialice un lifecycle real de reactivación deberá agregarse un evento/policy explícito en otro incremento.

## 9. Credenciales y sesiones

Se preserva #455 sin excepciones:

```text
credencial_usuario = local por instalación / no sincronizable
sesion_usuario     = local por instalación / no sincronizable
```

#510 no crea, copia, reconstruye ni fusiona credenciales o sesiones en el destino.

## 10. Transporte

#510 materializa:

```text
producer
+ outbox portable
+ registración reusable outbox → inbox
+ retained envelope #512
+ applicator Administrativo
+ retry/replay/conflicto por #512
```

No existe todavía scheduler/broker productivo automático transversal para estos eventos. La función de registración es un entry point reusable/harness y no modifica el dispatcher financiero legacy.

Por lo tanto el alcance no debe describirse como "replicación automática productiva completa" hasta que exista el transporte productivo correspondiente.

## 11. CORE-EF

- UID distribuido: `usuario.uid_global`.
- `op_id`: mismo `X-Op-Id` del command origen.
- `event_id`: delivery, no operación.
- provenance: UID portable de la instalación productora; nunca PK remota.
- idempotencia remota: `(administrativo.usuario, op_id)` mediante #512.
- idempotencia local: `operacion_idempotente.op_id` global mediante #469/#470; el claim precede la mutación.
- local mutation + outbox: una transacción.
- remote effect + receipt + terminal delivery: commit coordinado de #512.
- optimistic remote apply: CAS por `uid_global + version_registro`.
- conflicto: divergencia material o colisión funcional; no merge.
- PENDING_DEPENDENCY funcional: no aplica al snapshot mínimo de usuario.
- locks/advisory locks adicionales al runtime de idempotencia #470 y al protocolo #512: no aplica.

## 12. Compatibilidad legacy

#510 no absorbe #520.

Se preservan:

- paths HTTP locales por `id_usuario`;
- response HTTP existente, que no se amplía sólo para exponer UID;
- receipts globales para writes nuevos y evidencia row-local legacy por op IDs;
- `aggregate_id` legacy del inbox como campo técnico neutro, sin autoridad distribuida.

La migración transversal de identidad HTTP sigue perteneciendo a #461.
