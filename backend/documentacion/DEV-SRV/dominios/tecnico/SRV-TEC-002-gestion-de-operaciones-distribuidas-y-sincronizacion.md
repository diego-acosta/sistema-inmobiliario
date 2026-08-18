# SRV-TEC-002 — Gestión de operaciones distribuidas y sincronización

## Objetivo
Gestionar operaciones distribuidas y sincronización entre instalaciones, permitiendo preparar, emitir, recibir, aplicar y consultar cambios sincronizables de forma controlada, preservando consistencia técnica, idempotencia y trazabilidad.

## Alcance
Este servicio cubre:
- preparación de operaciones distribuibles
- emisión de cambios locales sincronizables
- recepción de cambios remotos
- aplicación controlada de operaciones remotas
- clasificación de resultados de sincronización
- consulta de estado y trazabilidad de sincronización

No cubre:
- lógica funcional de commands de negocio
- resolución manual o avanzada de conflictos
- importación/exportación técnica por lotes complejos
- respaldo, recuperación o integridad técnica profunda

## Entidades principales
- sync_outbox
- sync_inbox
- sincronizacion_operacion
- sincronizacion_recepcion
- entidad_sincronizable cuando corresponda

## Modos del servicio

### Preparación y emisión
Permite tomar operaciones locales sincronizables y dejarlas listas para envío o marcarlas como emitidas.

### Recepción
Permite registrar la llegada de una operación remota.

### Aplicación controlada
Permite procesar una operación remota y clasificar su resultado técnico.

### Consulta técnica
Permite visualizar estado de operaciones distribuidas y su trazabilidad.

## Política transversal de dependencia portable pendiente (#492)

### Decisión y estado contractual

Se congela `PENDIENTE_DEPENDENCIA` como nombre lógico del estado retryable de
inbox para una operación remota estructuralmente válida que todavía no puede
aplicarse porque al menos una referencia portable requerida no se resuelve en la
instalación receptora. El nombre distingue espera de ejecución (`PROCESSING` en
el runtime actual), rechazo terminal (`REJECTED`) y divergencia material
(`CONFLICTO`). Es soporte transversal de Técnico/sync y puede ser usado por
cualquier consumidor; no pertenece a Gestión Operativa ni agrega semántica de
Tarea.

Esta es una **política contractual documentada, no implementada**. El SQL real de
`inbox_event` sólo conserva identidad básica y estados libres; no conserva
payload, `op_id`, huella, intentos ni elegibilidad. `InboxRepository.claim()`
inserta `PROCESSING` con `ON CONFLICT (event_id, consumer) DO NOTHING`, no posee
reclaim, y `mark_as_rejected()` documenta `REJECTED` como no retryable. Ningún
worker auditado agenda pendientes de dependencia. Por ello ningún consumidor
puede declarar esta capacidad hasta materializar transversalmente persistencia,
repository, worker y tests; el contrato permite hacerlo incrementalmente sin
cambiar la conducta de consumidores existentes.

### Entrada, retención e idempotencia

El consumidor clasifica como `PENDIENTE_DEPENDENCIA` únicamente la ausencia
temporal de una referencia portable válida y requerida. La aplicación funcional
y el cambio de estado técnico deben compartir una frontera transaccional: si no
se resuelven **todas** las referencias, se revierte cualquier efecto funcional y
sólo queda persistida la espera técnica. Quedan prohibidos aplicación parcial,
placeholder, mapping específico del consumidor y copia de PK remota.

El registro retenido conserva el evento original: `op_id`, `event_id`,
`consumer`, `uid_global`/identidad portable, `version_registro`, payload íntegro,
huella estable y procedencia, además de motivo sanitizado, cantidad de intentos,
instantes de intento y próximo instante elegible. No se crea otro `op_id` ni se
reingesta como un evento nuevo. La unicidad de `(event_id, consumer)` continúa
deduplicando recepción; `op_id` y la huella controlan identidad de operación y
contenido. Mismo evento/op_id y misma huella retoma el registro; mismo `op_id`
con contenido material distinto se clasifica como conflicto de idempotencia, no
como retry.

### Claim y transiciones

```text
recepción válida + referencia requerida ausente
  -> PENDIENTE_DEPENDENCIA (no terminal)

PENDIENTE_DEPENDENCIA elegible
  -> claim atómico por un único worker técnico
  -> EN_PROCESO / PROCESSING
     -> referencias completas + aplicación atómica -> APLICADO / PROCESSED
     -> dependencia aún ausente -> PENDIENTE_DEPENDENCIA
     -> payload inválido o imposibilidad permanente -> RECHAZADO / REJECTED
     -> divergencia material demostrada -> CONFLICTO
```

El worker técnico transversal puede retomar automáticamente registros cuyo
`next_attempt_at` venció; un operador/job técnico puede habilitar reproceso
manual cuando verificó que la dependencia existe. Ambos usan el mismo claim
condicional y atómico. Un worker caído no debe dejar ejecución eterna: la futura
materialización debe usar lease/reclaim de `EN_PROCESO` vencido, conservando
contador y trazabilidad. Dos workers, un retry duplicado o una nueva entrega del
mismo evento no pueden obtener simultáneamente el claim ni duplicar el efecto.

Cada nueva espera aplica backoff creciente con cota y registra el intento. No se
congela cron, duración ni máximo numérico sin evidencia operativa. Alcanzar el
límite configurado pausa el retry automático y exige revisión/reanudación
técnica manual, pero conserva el estado retryable y el payload: no transforma
una ausencia temporal en `REJECTED` o `CONFLICTO`. Así se evitan loops sin perder
la operación.

### Clasificación de resultados

- `REJECTED` continúa terminal y no retryable: corresponde a payload inválido,
  referencia portable inválida o inexistencia/imposibilidad comprobada como
  permanente según el contrato dueño de esa referencia.
- `CONFLICTO` requiere divergencia material, colisión incompatible de identidad,
  versión o `op_id`; una dependencia temporal, por sí sola, no lo genera.
- `PENDIENTE_DEPENDENCIA` es espera temporal no terminal y conserva la
  trazabilidad completa hasta aplicación o clasificación terminal.
- `PROCESSED`/`APLICADO` sólo se alcanza después del efecto funcional atómico.

### Alternativas auditadas

- Se elige el estado explícito de inbox porque separa espera de ejecución y
  extiende la infraestructura transversal mínima.
- Se descarta mantener `PROCESSING`: sin lease actual confunde trabajo activo con
  dependencia pendiente y puede quedar eterno.
- Se descarta reingesta: choca con `(event_id, consumer)`, arriesga cambiar la
  identidad de la misma operación y fragmenta trazabilidad.
- Se descarta una cola separada: no existe patrón transversal que justifique
  duplicar payload, idempotencia y lifecycle; queda prohibida una cola GOP.

## Entradas conceptuales

### Contexto técnico (write)
- instalacion_id_origen
- instalacion_id_destino cuando corresponda
- op_id
- uid_entidad
- tipo_entidad
- version_registro
- payload técnico
- hash de payload cuando corresponda
- timestamp técnico cuando corresponda

### Datos de negocio
- tipo_evento distribuido
- operación sincronizable origen
- estado técnico esperado
- relación con entidad afectada
- observaciones técnicas

### Parámetros de consulta
- op_id
- uid_entidad
- tipo_entidad
- instalación origen
- instalación destino
- estado técnico
- rango de fechas

## Resultado esperado

### Para operaciones write
- identificador de operación distribuida o recepción
- op_id procesado
- estado técnico resultante
- clasificación de resultado (aplicada, duplicada, rechazada, conflicto, etc.)
- entidad afectada cuando corresponda
- errores estructurados cuando corresponda

### Para consulta
- operaciones distribuidas emitidas
- recepciones registradas
- estado técnico de sincronización
- trazabilidad por entidad y op_id
- resultados de aplicación

## Flujo de alto nivel

### Preparación y emisión
1. validar contexto técnico de operación distribuible
2. cargar registro técnico local cuando corresponda
3. validar elegibilidad de emisión
4. preparar operación para sincronización
5. registrar o actualizar estado de outbox
6. persistir cambios técnicos
7. devolver resultado

### Recepción
1. validar contexto técnico de recepción
2. verificar estructura mínima de la operación remota
3. registrar recepción técnica
4. persistir entrada en inbox o estructura equivalente
5. devolver resultado

### Aplicación controlada
1. cargar operación remota recibida
2. verificar idempotencia por op_id
3. clasificar si aplica, duplica, rechaza o entra en conflicto
4. aplicar cambio remoto cuando corresponda
5. actualizar estado técnico final
6. persistir resultado en transacción controlada
7. devolver resultado

### Consulta técnica
1. validar parámetros
2. cargar operaciones y recepciones técnicas
3. resolver trazabilidad por op_id y entidad
4. devolver vista de lectura

## Validaciones clave
- presencia y validez de op_id
- consistencia de uid_entidad y tipo_entidad
- idempotencia de recepción y aplicación
- coherencia de version_registro cuando corresponda
- integridad mínima del payload técnico
- no reprocesamiento indebido de operaciones ya aplicadas
- clasificación explícita de duplicado, rechazo o conflicto

## Efectos transaccionales
- alta o actualización de sync_outbox
- alta o actualización de sync_inbox
- registro de sincronizacion_operacion y sincronizacion_recepcion cuando corresponda
- actualización de estados técnicos de emisión y recepción
- aplicación de cambios remotos cuando corresponda
- trazabilidad consistente por op_id y entidad

## Errores
- [[ERR-TEC]]

## Dependencias

### Hacia arriba
- [[CORE-EF-001-infraestructura-transversal]]
- existencia de operaciones sincronizables generadas por commands de negocio
- contexto técnico válido
- instalaciones técnicas válidas cuando corresponda

### Hacia abajo
- [[SRV-TEC-003-gestion-de-conflictos-de-sincronizacion]]
- [[SRV-TEC-004-gestion-de-estado-de-sincronizacion-y-jobs-tecnicos]]
- todos los dominios sincronizables del sistema

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-TECNICO]]
- [[CU-TEC]]
- [[RN-TEC]]
- [[ERR-TEC]]
- [[EVT-TEC]]
- [[EST-TEC]]
- [[SRV-TEC-001-aplicacion-transversal-de-core-ef-en-commands]]
- [[CORE-EF-001-infraestructura-transversal]]

## Pendientes abiertos
- definición exacta de estados técnicos de operación distribuida
- criterio final de segmentación por destino o alcance
- relación formal entre paquete técnico y operación individual
- materialización SQL/runtime/tests de `PENDIENTE_DEPENDENCIA`, claim/reclaim y
  reprocesamiento conforme a la política contractual congelada
- política de reintentos de emisión de outbox (separada del reproceso de inbox)
- estrategia exacta de payload técnico portable

## Guardrail #455

El ingreso a sincronización usa la allowlist única de aplicación y default-deny en repository, worker y dispatcher. Eventos/aggregates desconocidos y payloads sensibles fallan cerrados; credenciales y sesiones jamás son contratos permitidos. Los errores persistibles son códigos sanitizados, no `str(exc)` ni payloads.
