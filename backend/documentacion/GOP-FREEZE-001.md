# GOP-FREEZE-001 — Gestión Operativa — Tareas y Seguimiento Interno

**Estado:** freeze funcional previo a diseño técnico

**Dominio:** `gestion_operativa`

**Módulo:** `tareas_y_seguimiento_interno`

## 1. Propósito y alcance

Este documento congela el contrato funcional de tareas y seguimiento interno antes de producir DEV-ARCH, DER, DEV-SRV, DEV-API, SQL, implementación y tests. Los conceptos funcionales definidos por este freeze se clasifican así:

- **Núcleo del dominio:** el concepto funcional `Tarea`.
- **Núcleo del dominio:** comentarios de tarea, como parte del seguimiento funcional de `gestion_operativa`.
- **Núcleo del dominio:** historial funcional de tarea.
- **Soporte transversal:** identidad y autorización provistas por Administrativo.
- **Soporte transversal:** metadata, versionado, idempotencia, procedencia técnica, outbox, sync y demás capacidades CORE-EF/Técnico cuando correspondan.
- **Compatibilidad heredada:** ninguna estructura heredada se adopta como modelo principal de Tareas.

Esta clasificación es semántica y funcional. No implica que `Tarea`, comentarios o historial estén ya materializados como entidades, aggregates, tablas o fronteras transaccionales. La clasificación técnica permanece pendiente de `DEV-ARCH-GOP` y del diseño posterior.

Este freeze no confirma implementación existente. En particular, todavía no define SQL físico, endpoints definitivos, schemas, eventos concretos, frontend ni automatizaciones específicas. Todo ello queda pendiente de los artefactos técnicos posteriores y de su validación contra SQL, backend y tests reales.

## 2. Ownership y límites

Queda congelada esta frontera, sin equivalencia ni solapamiento:

```text
gestion_operativa
→ dominio canónico reservado para la semántica funcional
  de tareas y seguimiento interno

operativo
→ dominio externo distinto
→ conserva su ownership sobre sucursales, instalaciones, caja y sus operaciones
```

`gestion_operativa != operativo`. Esta reserva semántica no implica todavía la existencia de una entidad técnica `tarea`, un aggregate root, una tabla ni una frontera transaccional consolidada. El uso futuro de referencias a objetos de `operativo` no transfiere ownership. Se mantienen además las separaciones:

```text
comentario_tarea != historial_tarea
historial_tarea != auditoria_administrativa
fecha_objetivo != evento_agenda
tarea != incidencia
tarea != observacion
tarea != novedad
cancelacion_tarea != eliminacion_tecnica
instalacion_origen != scope_funcional_tarea
```

Los antiguos `CU-OPER-*` del catálogo global que describen tareas, pendientes, asignaciones o historial se clasifican como **compatibilidad heredada / documentación histórica desalineada**. No constituyen contratos vigentes de `operativo` ni de `gestion_operativa`. El catálogo específico `CAT-CU/dominios/operativo/CU-OPE.md` debe interpretarse subordinado a `DEV-ARCH-OPE-001` y al catálogo autoritativo `DEV-SRV/dominios/operativo/catalogos/CU-OPE.md`; la futura numeración de casos de uso de Gestión Operativa deberá definirse en un catálogo específico posterior, sin crear ni reutilizar automáticamente IDs `CU-GOP-*` en este freeze.

## 3. Concepto funcional principal

`Tarea` es el concepto funcional principal propuesto para `tareas_y_seguimiento_interno` y su semántica pertenece a `gestion_operativa`. Representa una unidad de trabajo pendiente, en ejecución, completada o cancelada que Gestión Operativa debe seguir.

Todavía no existe implementación que consolide una entidad persistente, una frontera de aggregate, una frontera transaccional ni una estructura SQL. La eventual clasificación de `Tarea` como aggregate root deberá decidirse en el futuro DEV-ARCH de `gestion_operativa` (`DEV-ARCH-GOP`) y validarse después contra DER, DEV-SRV, SQL, backend y tests.

Una tarea puede ser manual o generada por sistema, estar asignada o no tener responsable, y ser puramente interna.

## 4. Identidad

- `id_tarea`: identificador interno conceptual.
- `uid_global`: condicionado por la decisión de sincronización; no se congela su incorporación hasta resolverla.
- Código visible de tarea: fuera del MVP, salvo necesidad funcional posterior expresamente aprobada.

## 5. Origen y autoría

Toda tarea tiene `origen = USUARIO | SISTEMA`.

Para `origen = USUARIO`:

```text
id_usuario_creador
→ obligatorio
→ tomado de AuthenticatedPrincipal.id_usuario
```

El cliente no puede elegir libremente al usuario creador.

Para `origen = SISTEMA`:

```text
id_usuario_creador = NULL
generador_sistema IS NOT NULL
```

`generador_sistema` identifica el proceso funcional que originó la tarea. `CONTROL_MORA` es un caso futuro conocido, pero este freeze no define un catálogo completo. No se debe crear un usuario ficticio `SYSTEM`, `BOT`, `SISTEMA` ni equivalente.

Invariantes conceptuales:

```text
origen = USUARIO
→ id_usuario_creador IS NOT NULL
→ generador_sistema IS NULL

origen = SISTEMA
→ id_usuario_creador IS NULL
→ generador_sistema IS NOT NULL
```

## 6. Creador versus responsable

Creador y responsable son roles distintos. El creador registra autoría; el responsable identifica a quien tiene asignado el trabajo. Son válidos:

```text
creador = usuario A; responsable = usuario A
creador = usuario A; responsable = usuario B
creador = usuario A; responsable = NULL
origen = SISTEMA; generador_sistema = CONTROL_MORA; responsable = NULL
origen = SISTEMA; generador_sistema = CONTROL_MORA; responsable = usuario B
```

## 7. Responsable

Para el MVP se congela `0..1 responsable`:

```text
id_usuario_responsable
→ nullable
→ referencia a usuario administrativo
```

Una tarea sin responsable es válida. Múltiples responsables, equipos, sectores, grupos, observadores y responsables secundarios quedan fuera del MVP.

## 8. Contenido

- `titulo`: obligatorio y no vacío.
- `descripcion`: opcional.
- Adjuntos: fuera del MVP.

## 9. Estados

**CANDIDATOS / NO CONGELADOS:** `PENDIENTE`, `EN_CURSO`, `COMPLETADA` y `CANCELADA`. Dentro de esta propuesta preliminar, `PENDIENTE` sería el estado inicial y `COMPLETADA` y `CANCELADA` serían terminales.

Las siguientes transiciones son únicamente una propuesta preliminar y no constituyen un contrato cerrado:

```text
PENDIENTE
├── EN_CURSO
├── COMPLETADA
└── CANCELADA

EN_CURSO
├── PENDIENTE
├── COMPLETADA
└── CANCELADA
```

La reapertura queda fuera del MVP salvo decisión expresa. No se incluyen inicialmente `VENCIDA`, `BLOQUEADA`, `PAUSADA`, `ARCHIVADA`, `PROGRAMADA` ni `DELEGADA`. Los estados definitivos permanecen bloqueantes antes del DER, según la sección 30.

## 10. Prioridad

**CANDIDATOS / NO CONGELADOS:** `BAJA`, `NORMAL`, `ALTA`, `URGENTE`, con `NORMAL` como default candidato. Tanto el catálogo como el default permanecen **NO CONGELADOS**; las prioridades definitivas siguen abiertas y son bloqueantes antes del DER.

## 11. Fecha objetivo

`fecha_objetivo` es opcional y `fecha_objetivo != evento_agenda`. Asignarla no crea evento, recordatorio, alerta ni notificación.

La representación `DATE` versus `TIMESTAMP` es una decisión pendiente previa al DER. Se recomienda inicialmente `DATE` si sólo se requiere un día objetivo.

## 12. Vencimiento

`VENCIDA` no es un estado persistido. Es una condición derivada conceptualmente:

```text
vencida =
  fecha_objetivo < fecha_corte
  AND estado NOT IN (<estados terminales definitivos>)
```

La semántica exacta de `fecha_corte` permanece **NO CONGELADA**. Antes del DER debe definirse, conjuntamente con la decisión `DATE` versus `TIMESTAMP`:

- fuente temporal;
- zona horaria;
- granularidad;
- regla de comparación;
- comportamiento consistente entre instalaciones.

No se asumen todavía UTC, reloj del cliente, reloj de instalación, hora local de sucursal ni zona del usuario.

## 13. Finalización

Al completar una tarea debe conservarse conceptualmente `fecha_finalizacion`, generada por el servidor.

## 14. Scope funcional

Como propuesta preliminar se considera `id_sucursal` opcional:

```text
id_sucursal = NULL → tarea global
id_sucursal = <id> → tarea asociada funcionalmente a una sucursal
```

Su opcionalidad definitiva queda abierta antes del DER. No se usa `id_instalacion` como scope funcional. `id_instalacion_origen` representa exclusivamente procedencia técnica CORE-EF; por tanto, `id_instalacion_origen != scope_funcional_tarea`.

## 15. Comentarios

```text
Tarea
└── Comentarios 0..N
```

Cada comentario conserva tarea, autor, texto e instante. Para autor humano se usa `AuthenticatedPrincipal.id_usuario`, que identifica al actor local en la instalación donde ocurre la operación. Si esa referencia debe viajar mediante sync, será necesaria la identidad canónica interinstalación pendiente; este freeze no diseña su mecanismo concreto ni presupone columnas de UID.

Se congela la propuesta de comentario **append-only** para el MVP: no se edita, no se borra físicamente y se corrige mediante un nuevo comentario. Agregarlo no cambia automáticamente el estado.

## 16. Historial funcional

El historial funcional es estructurado y está separado de comentarios y auditoría. Puede representar conceptualmente:

```text
CREADA
ASIGNADA
DESASIGNADA
REASIGNADA
CAMBIO_ESTADO
CAMBIO_PRIORIDAD
CAMBIO_FECHA_OBJETIVO
CAMBIO_TITULO
CAMBIO_DESCRIPCION
```

Cada entrada conserva como mínimo tipo, instante, tarea, actor si existe y valor anterior/nuevo cuando corresponda. El actor humano local deberá poder resolverse mediante la estrategia canónica interinstalación pendiente si el historial resulta sincronizable; este freeze no presupone columnas concretas de UID.

```text
historial_funcional
!= comentario
!= auditoria_administrativa
!= log_tecnico
!= outbox
```

## 17. Generación automática

El modelo debe admitir generación automática, aunque su ejecución queda fuera del primer MVP. Caso futuro conocido:

```text
Financiero
→ detecta mora
→ solicita/genera una tarea
→ gestion_operativa conserva ownership de la tarea
```

La regla para determinar mora pertenece a Financiero; la tarea resultante pertenece a `gestion_operativa`. Financiero no administra directamente estado, prioridad, comentarios, historial ni asignación de esa tarea.

La futura generación debe ser idempotente frente a reintentos y al mismo hecho fuente para impedir duplicados.

## 18. Relaciones con objetos externos

Una tarea puede ser puramente interna y el MVP no requiere relación externa. En el futuro podría relacionarse con persona, inmueble, unidad funcional, venta, reserva, contrato, alquiler, obligación financiera, documento o incidencia.

No se implementa ni se congela una FK genérica `tipo_entidad` + `id_entidad`.

## 19. Cancelación, baja y archivo

```text
CANCELADA → estado funcional
deleted_at → eliminación técnica
```

La eliminación no se expone como flujo normal del MVP. `ARCHIVADA` no integra los estados iniciales. La presencia física de `deleted_at` desde el inicio queda abierta antes del DER.

## 20. Identidad y autorización

Para operaciones manuales:

```text
Authorization: Bearer
→ AuthenticatedPrincipal.id_usuario
```

`X-Usuario-Id` no debe utilizarse como autoridad de identidad humana en endpoints nuevos; representa metadata/contexto CORE-EF cuando el contrato aplicable lo requiera, pero no autentica.

Administrativo conserva ownership de usuarios, autenticación, autorización, roles y permisos, y provee sus mecanismos. `gestion_operativa` consume la identidad de usuario y debe definir qué acciones funcionales sobre Tareas requieren autorización y qué relación o scope habilita cada acción, sin redefinir el modelo administrativo.

La política funcional de autorización y visibilidad permanece **NO CONGELADA / BLOQUEANTE**. Antes del DER y DEV-API debe decidir, sin inventar todavía permisos, roles, códigos ni autorización contextual:

- si un usuario puede consultar sólo tareas asignadas a él o también las creadas por él;
- quién puede consultar tareas sin responsable o tareas de otros usuarios;
- cómo incide `id_sucursal`, si finalmente se incorpora, y quién puede consultar tareas globales;
- cómo se comporta **Mis tareas**;
- quién puede modificar título/descripción, asignar, reasignar, desasignar, cambiar prioridad, cambiar fecha objetivo, cambiar estado, completar, cancelar y comentar.

El ownership de autorización de Administrativo no elimina la necesidad de que `gestion_operativa` defina esta política funcional de acceso. Los códigos y mecanismos concretos se diseñarán posteriormente junto con Administrativo y DEV-API.

## 21. CORE-EF preliminar

Clasificación conceptual futura:

| Operación | Clasificación |
| --- | --- |
| Crear tarea manual | `COMMAND_WRITE_NEGOCIO` |
| Crear tarea automática | `COMMAND_WRITE_NEGOCIO` |
| Modificar tarea | `COMMAND_WRITE_NEGOCIO` |
| Asignar, reasignar o desasignar | `COMMAND_WRITE_NEGOCIO` |
| Cambiar estado | `COMMAND_WRITE_NEGOCIO` |
| Agregar comentario | `COMMAND_WRITE_NEGOCIO` |
| Consultas | `QUERY_READLIKE` |

Los futuros DEV-API/DEV-SRV deben resolver y documentar, según la estrategia de sync, `X-Op-Id`, headers CORE-EF aplicables, `If-Match-Version`, versionado, idempotencia, instalación de procedencia, sucursal funcional, outbox, sync, locks y frontera de rollback/transacción. Este incremento no implementa endpoints ni afirma cumplimiento runtime.

Para las consultas `QUERY_READLIKE`, headers write, idempotencia command y `If-Match-Version` no aplican porque no mutan estado.

## 22. Versionado

Se adopta como estrategia objetivo la concurrencia optimista para las futuras modificaciones de `Tarea`. Los contratos técnicos posteriores deberán definir el mecanismo de versión compatible con CORE-EF y `If-Match-Version` cuando corresponda.

La materialización concreta —incluido si corresponde un campo `version_registro` en una futura entidad persistente— permanece pendiente de `DEV-ARCH-GOP`, DER y SQL.

Permanece abierta la decisión: **¿agregar comentario incrementa `version_registro` de tarea?** La recomendación preliminar es **NO** si el comentario es append-only y no modifica el estado funcional de `Tarea`.

## 23. Idempotencia

Debe aplicarse al menos a crear manual, crear automática, asignar/reasignar, cambiar estado y agregar comentario. Los contratos posteriores deberán definir criterio de payload, mismo `op_id` con mismo payload, mismo `op_id` con payload distinto y retry posterior a error.

La generación automática además debe deduplicar reintentos y el mismo hecho fuente.

## 24. Sync

**NO CONGELADO.** Las alternativas son `SINCRONIZABLE`, `LOCAL` o `MIXTO`. Se recomienda evaluar seriamente `SINCRONIZABLE` por la necesidad futura de consultar **Mis tareas** entre instalaciones.

La decisión debe tomarse antes del DER porque afecta `uid_global`, metadata CORE-EF, outbox, allowlist, conflictos, comentarios, historial, versiones e idempotencia. Este documento no crea eventos, productores, consumidores ni entradas de allowlist.

Si Tarea se define como `SINCRONIZABLE`, deberá existir además una estrategia canónica interinstalación para resolver toda referencia persistida a usuario dentro de `gestion_operativa`, como mínimo:

- usuario creador;
- usuario responsable;
- autor de comentario;
- actor del historial funcional;
- cualquier futura referencia humana persistida que participe de información sincronizable del módulo.

No debe asumirse que el `id_usuario` local es suficiente como identidad sincronizable.

La estrategia concreta —UID global de usuario, mapping u otro mecanismo autorizado— pertenece a Administrativo/Técnico y permanece **NO CONGELADA** en este documento. `gestion_operativa` consume esa identidad, no redefine el modelo administrativo de usuario, no inventa un UID, no crea aquí una tabla de mapping y no debe agregar por sí mismo metadata global a `usuario`. **Mis tareas** entre instalaciones no puede habilitarse de manera segura hasta resolver esta dependencia.

## 25. Locks

Para el MVP se propone no requerir lock lógico inicialmente. La estrategia objetivo es la concurrencia optimista; el mecanismo de versión y su materialización técnica quedan pendientes de `DEV-ARCH-GOP`, DER y SQL, manteniendo compatibilidad con `If-Match-Version` cuando corresponda.

```text
concurrencia optimista
→ mecanismo de versión pendiente
→ If-Match-Version cuando corresponda
```

## 26. Consultas mínimas

El contrato debe prever: obtener tarea, listar tareas, mis tareas, pendientes, vencidas y sin asignar.

Filtros mínimos: responsable, estado, prioridad, sucursal, vencida y fecha objetivo.

La existencia funcional de estas consultas no implica acceso irrestricto a sus resultados: su visibilidad queda condicionada a la política funcional de autorización pendiente.

## 27. MVP funcional

El alcance funcional comprende:

- crear tarea manual;
- listar tareas y ver una tarea;
- consultar mis tareas, pendientes, vencidas y sin asignar;
- modificar título/descripción;
- asignar, reasignar y desasignar;
- cambiar prioridad, fecha objetivo y estado;
- agregar comentario;
- consultar historial.

Los commands de modificación, asignación/reasignación/desasignación, cambios de prioridad, fecha objetivo o estado y comentarios quedan condicionados a la futura política funcional de autorización.

Debe implementarse en varios incrementos trazables, no como un único issue grande.

## 28. Fuera del MVP

Quedan fuera: agenda completa, recordatorios, alertas, notificaciones, recurrencia, subtareas, dependencias, múltiples responsables, equipos, sectores, Kanban, SLA, workflows configurables, adjuntos, generación automática efectiva, control de mora efectivo, relaciones polimórficas, incidencias, novedades, observaciones, frontend avanzado y dashboard analítico.

## 29. Decisiones congeladas

`GOP-FREEZE-001` congela expresamente:

1. `gestion_operativa` es el dominio canónico reservado para la semántica funcional de tareas y seguimiento interno; `operativo` es un dominio externo distinto. Esta decisión no congela todavía una entidad técnica `tarea`.
2. `Tarea` es el concepto funcional principal propuesto para `tareas_y_seguimiento_interno`, cuya semántica pertenece a `gestion_operativa`; su clasificación técnica eventual permanece pendiente de `DEV-ARCH-GOP` y validaciones posteriores.
3. El origen es `USUARIO | SISTEMA`.
4. Creador y responsable son roles distintos.
5. `id_usuario_creador` es obligatorio sólo para origen `USUARIO` y procede de `AuthenticatedPrincipal.id_usuario`.
6. `generador_sistema` es obligatorio sólo para origen `SISTEMA`; no existe usuario ficticio de sistema.
7. Hay cero o un responsable; una tarea sin responsable es válida.
8. Una tarea puramente interna es válida.
9. El título es obligatorio y no vacío; la descripción es opcional.
10. La fecha objetivo es opcional y no crea un evento de agenda.
11. `vencida` es una condición derivada, no un estado persistido.
12. Comentario, historial funcional y auditoría administrativa son conceptos distintos.
13. El comentario es append-only en el MVP.
14. Cancelación funcional y eliminación técnica son distintas.
15. Instalación de origen técnico y scope funcional son distintos; `id_instalacion` no es scope funcional.
16. La identidad humana procede de `AuthenticatedPrincipal`, no de `X-Usuario-Id`.
17. Relaciones externas y múltiples responsables quedan fuera del MVP.
18. La generación automática efectiva queda fuera del MVP, aunque el modelo debe admitirla.
19. La concurrencia optimista es la estrategia objetivo para futuras modificaciones de `Tarea`; su materialización técnica y mecanismo de versión deberán definirse en `DEV-ARCH-GOP` y los artefactos posteriores, manteniendo compatibilidad con `If-Match-Version` cuando corresponda.

## 30. Decisiones todavía abiertas

Son bloqueantes antes del DER y este freeze no las cierra:

1. Si `id_sucursal` es opcional o no.
2. Estados definitivos.
3. Reapertura.
4. Prioridades definitivas.
5. `DATE` versus `TIMESTAMP` para `fecha_objetivo`.
6. Estrategia de sync: `SINCRONIZABLE`, `LOCAL` o `MIXTO`.
7. Si agregar comentario incrementa `version_registro` de la tarea.
8. Presencia de `deleted_at` desde el inicio.
9. Semántica de `fecha_corte` utilizada para determinar vencimiento: fuente temporal, zona horaria, granularidad y regla de comparación.
10. Identidad canónica interinstalación de usuario para toda referencia humana persistida que deba sincronizarse en `gestion_operativa` —como creador, responsable, autor de comentario y actor del historial funcional—: mecanismo de resolución o mapping y dependencia con Administrativo/Técnico.
11. Política funcional de visibilidad y mutación de Tareas: alcance de Mis tareas, tareas creadas, tareas sin asignar, tareas de otros usuarios, scope de sucursal/global y reglas para editar, asignar, cambiar estado, cancelar y comentar.

Estas decisiones deberán resolverse y validarse contra arquitectura, CORE-EF, autorización, sincronización, SQL, implementación y tests antes de afirmar un contrato técnico completo.
