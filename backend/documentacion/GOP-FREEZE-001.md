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

### 1.1 Trazabilidad de este cierre

Para cerrar las seis decisiones se respetó la precedencia vigente: `AGENTS.md` y
la arquitectura formal DEV-ARCH —en especial `DEV-ARCH-OPE-001`— prevalecen;
después se contrastaron SQL real, implementación y tests reales, seguidos por
issues y PR vigentes. Como fuentes operativas se consultaron
`PROJECT-STATUS.md` y `CODEX-WORKFLOW.md`. Este freeze, `SYS-MAP-002`, los
DEV-SRV relevantes y el CAT-CU vigente se leyeron subordinados a esas fuentes de
verdad; su bloque histórico `CU-OPER-*` se utilizó sólo como evidencia histórica.
Los patrones de fechas y baja lógica en SQL, backend y tests aportan evidencia
transversal: no prueban una implementación GOP ni fuerzan su futuro diseño.

También se revisó la historia integrada de PR #474, que originó este freeze, y
PR #479, que lo alineó con CORE-EF. Se conserva su corrección: en futuros writes
Bearer la identidad humana procede exclusivamente de
`AuthenticatedPrincipal.id_usuario`; `X-Usuario-Id` no se adopta; identidad del
actor y clasificación de sync son dimensiones independientes; y #412/PR #478 es
sólo patrón transversal, no plantilla literal de Tareas.

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

### Decisión

Los **estados definitivos del MVP** son `PENDIENTE`, `EN_CURSO`, `COMPLETADA` y
`CANCELADA`:

- `PENDIENTE`: trabajo válido todavía no iniciado o devuelto deliberadamente a
  espera; es el único estado inicial.
- `EN_CURSO`: existe una decisión humana o sistémica explícita de comenzar el
  trabajo y éste continúa abierto. Aporta la distinción funcional entre cola y
  ejecución; no implica porcentaje de avance ni SLA.
- `COMPLETADA`: el trabajo esperado fue realizado. Es terminal para las
  transiciones ordinarias, aunque admite la operación explícita de reapertura
  definida en la sección 9.1.
- `CANCELADA`: se decidió que el trabajo ya no debe realizarse. Es terminal y no
  admite reapertura en el MVP.

Las transiciones ordinarias congeladas son:

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

Invariantes: `VENCIDA` continúa siendo una condición derivada y nunca un estado;
una tarea terminal no acepta transiciones ordinarias; completar expresa trabajo
realizado y cancelar expresa abandono decidido, sin equivalencia entre ambos. No
se incorporan `BLOQUEADA`, `PAUSADA`, `ARCHIVADA`, `PROGRAMADA` ni `DELEGADA`:
no existe evidencia vigente que exija esos workflows y bloqueo/archivo no deben
inventarse como estados para suplir filtros o baja técnica.

### Evidencia

- **Repositorio:** el freeze ya proponía los cuatro valores y el legado
  `CU-OPER-*` distingue alta, cierre, cancelación, cambio de estado e inicio de
  proceso. Ese legado prueba intención histórica, no un contrato vigente.
- **Repositorio:** `SYS-MAP-002` reserva tareas y seguimiento para
  `gestion_operativa`, mientras `DEV-ARCH-OPE-001` los excluye de `operativo`.
- **Inferencia:** separar `PENDIENTE` de `EN_CURSO` permite representar cola
  frente a ejecución sin introducir avance porcentual ni un workflow adicional.
- **Decisión de diseño nueva:** se congela este conjunto y su semántica exacta.

### Alternativas descartadas y justificación

Se descarta eliminar `EN_CURSO` porque perdería una distinción funcional ya
contemplada; se descarta agregar estados sin evidencia; y se descarta persistir
`VENCIDA` porque depende del tiempo y puede derivarse. El conjunto mínimo conserva
intención histórica sin convertir el catálogo legado en contrato nuevo.

### Impacto en artefactos posteriores

DEV-ARCH-GOP y los artefactos posteriores deberán preservar estas semánticas e
invariantes. Este freeze no decide representación física, comandos ni contratos
de API.

## 9.1 Reapertura

### Decisión

- `COMPLETADA`: **reapertura permitida**, exclusivamente mediante una operación
  funcional explícita y diferenciada, con destino `PENDIENTE`.
- `CANCELADA`: **reapertura prohibida** en el MVP. Si vuelve a existir necesidad
  de trabajo, corresponde una tarea nueva, trazable respecto de la anterior en
  un diseño posterior si se demuestra esa necesidad.
- Reabrir exige un motivo funcional obligatorio, conserva íntegramente el
  historial previo y agrega una entrada estructurada de reapertura con actor,
  instante y motivo. No borra la finalización histórica.
- La reapertura no es una transición ordinaria ni decide quién puede ejecutarla;
  esa autorización permanece en el blocker 11.

### Evidencia

- **Repositorio:** el bloque histórico incluye reapertura de pendiente
  (`CU-OPER-008`) y consulta de histórico, pero no es contrato vigente ni define
  reapertura de una cancelación.
- **Repositorio:** el freeze ya exige historial funcional estructurado y separa
  cancelación de eliminación técnica.
- **Inferencia:** un cierre puede resultar prematuro y requerir retomar trabajo;
  una cancelación expresa que el trabajo dejó de corresponder.
- **Decisión de diseño nueva:** sólo `COMPLETADA` se reabre, a `PENDIENTE`, con
  motivo e historial completos.

### Alternativas descartadas y justificación

Se descarta reabrir a `EN_CURSO` porque reabrir no prueba que la ejecución haya
comenzado nuevamente; se descarta reabrir `CANCELADA` porque diluiría la decisión
de abandono; y se descarta prohibir toda reapertura porque la evidencia histórica
reconoce esa necesidad funcional.

### Impacto en artefactos posteriores

Los artefactos posteriores deberán modelar la reapertura como capacidad explícita
y auditable, sin deducir permisos en este freeze ni reutilizar un ID histórico.

## 10. Prioridad

### Decisión

Las **prioridades definitivas del MVP**, de menor a mayor, son `BAJA < NORMAL <
ALTA < URGENTE`; `NORMAL` es el default.

- `BAJA`: puede atenderse después del trabajo ordinario sin que la prioridad por
  sí sola implique incumplimiento.
- `NORMAL`: atención ordinaria esperada y ausencia de señal excepcional.
- `ALTA`: requiere adelantarse respecto del trabajo ordinario.
- `URGENTE`: requiere atención inmediata frente a las demás prioridades activas.

La prioridad sólo afecta ordenación, filtros y señalización visual. No modifica
estado, vencimiento, permisos, locks, SLA ni genera automatizaciones. Puede
cambiarse mientras la tarea esté en `PENDIENTE` o `EN_CURSO`; queda inmutable en
`COMPLETADA` y `CANCELADA`. Una tarea reabierta vuelve a estar activa y entonces
puede cambiarse.

### Evidencia

- **Repositorio:** estos cuatro candidatos y `NORMAL` como default ya estaban en
  el freeze; el historial contempla conceptualmente `CAMBIO_PRIORIDAD`.
- **Repositorio:** no hay Tarea implementada ni SLA de GOP que otorgue efectos
  adicionales a la prioridad.
- **Inferencia:** `BAJA` permite despriorizar trabajo válido y `URGENTE` distingue
  atención inmediata de mero adelantamiento.
- **Decisión de diseño nueva:** se congelan valores, orden, default y alcance.

### Alternativas descartadas y justificación

Se descartan tres niveles porque fusionar `ALTA` y `URGENTE` pierde la señal de
atención inmediata, y eliminar `BAJA` impide expresar postergación relativa. Se
descartan SLA o reglas automáticas por carecer de evidencia.

### Impacto en artefactos posteriores

Los diseños posteriores deberán conservar orden y restricciones, pero decidirán
recién entonces su representación técnica. No se define enum ni catálogo SQL.

## 11. Fecha objetivo

### Decisión

`fecha_objetivo` es opcional y tiene semántica funcional **DATE**: representa un
día calendario completo, sin hora ni offset. La tarea puede cumplirse durante
todo el día objetivo y sólo pasa a vencida al comenzar el día calendario local
siguiente. Entre tareas del mismo día no existe orden horario contractual.

`fecha_objetivo != evento_agenda`: asignarla no crea evento, recordatorio, alerta
ni notificación.

### Evidencia

- **Repositorio:** el alcance vigente habla de tareas internas, pendientes y
  vencimientos, y no confirma agenda horaria, recordatorios ni orden por hora.
- **Repositorio:** existen comparaciones de fechas de negocio en Financiero, pero
  pertenecen a otro dominio y sólo evidencian que el sistema distingue fechas de
  timestamps; no fuerzan el diseño GOP.
- **Inferencia:** una hora agregaría ambigüedad de zona y precisión inexistente
  para el MVP multiinstalación.
- **Decisión de diseño nueva:** la granularidad funcional queda congelada como
  fecha calendario.

### Alternativas descartadas y justificación

Se descarta TIMESTAMP porque no existe evidencia de hora límite ni agenda horaria
y porque introduciría conversiones y casos de borde innecesarios. No se adopta
otra representación.

### Impacto en artefactos posteriores

DER y contratos posteriores deberán materializar `fecha_objetivo` como DATE,
preservando su semántica de día calendario completo, sin hora ni offset. El DER
no podrá reabrir la elección entre DATE y TIMESTAMP; permanecen pendientes sólo
los demás detalles técnicos, sin definir aquí columna, índice, constraint,
migración, schema HTTP ni serialización.

## 12. Vencimiento

### Decisión

`VENCIDA` no es un estado persistido. `fecha_corte` es la fecha calendario local
obtenida una sola vez por caso de uso desde el reloj confiable del servidor,
proyectado en la zona IANA `America/Argentina/Buenos_Aires`. No proviene del
cliente, de un query param, de la instalación ni de la sesión de PostgreSQL. API,
servicio y tests deberán compartir esa misma fecha capturada; los tests usarán un
reloj controlable equivalente.

La fórmula exacta es:

```text
vencida =
  deleted_at ausente
  AND fecha_objetivo no nula
  AND estado IN (PENDIENTE, EN_CURSO)
  AND fecha_objetivo < fecha_corte_local
```

La comparación tiene granularidad DATE y operador estricto `<`. Por ello,
`fecha_objetivo = fecha_corte_local` no está vencida durante ningún instante de
ese día; `COMPLETADA` y `CANCELADA` nunca están vencidas; una tarea sin fecha no
está vencida; y una tarea reabierta puede volver a estar vencida si su fecha
objetivo es anterior al corte. La prioridad no interviene.

Ejemplos de borde, para `fecha_corte_local = 2026-08-20`:

- `fecha_objetivo = 2026-08-20`, activa: no vencida durante todo el día 20.
- `fecha_objetivo = 2026-08-19`, `PENDIENTE`: vencida.
- misma fecha anterior, `COMPLETADA` o `CANCELADA`: no vencida.
- `fecha_objetivo = NULL`: no vencida.
- fecha anterior y reapertura de `COMPLETADA` a `PENDIENTE`: vencida nuevamente.
- fecha anterior con baja técnica: fuera de consultas ordinarias, incluida la de
  vencidas.

### Evidencia

- **Repositorio:** la fórmula candidata ya usa comparación estricta y excluye
  terminales, pero dejaba sin cerrar fuente, zona y granularidad.
- **Repositorio:** el backend usa UTC para instantes técnicos y una prueba
  transversal usa `America/Argentina/Buenos_Aires`; esa evidencia no convierte
  un día objetivo en instante UTC.
- **Inferencia:** una fecha civil necesita un único calendario funcional para dar
  el mismo resultado en todas las instalaciones.
- **Decisión de diseño nueva:** reloj del servidor, zona indicada, captura única y
  fórmula completa.

### Alternativas descartadas y justificación

Se descartan reloj del cliente, zona de usuario/instalación/sucursal y timezone de
sesión porque producirían resultados distintos para la misma tarea. Se descarta
UTC como calendario funcional porque puede cambiar de día respecto de Argentina,
y PostgreSQL como autoridad obligatoria porque la regla requiere una fuente
funcional única testeable, no acoplamiento a una tecnología. Se descarta `<=`
porque haría vencer la tarea al comenzar su propio día objetivo.

### Impacto en artefactos posteriores

DEV-SRV, DEV-API y tests posteriores deberán usar literalmente esta captura y
fórmula. El mecanismo de inyección del reloj y la consulta física se decidirán
después; este freeze no crea parámetros ni SQL.

## 13. Finalización

`Tarea.fecha_finalizacion` representa únicamente la finalización vigente del
ciclo actual:

```text
PENDIENTE / EN_CURSO → COMPLETADA
→ fecha_finalizacion = instante de esa finalización generado por el servidor

COMPLETADA → PENDIENTE mediante reapertura
→ fecha_finalizacion corriente = NULL

nueva transición PENDIENTE / EN_CURSO → COMPLETADA
→ fecha_finalizacion = nuevo instante de la nueva finalización
```

Limpiar el valor corriente al reabrir no elimina la evidencia de la finalización
anterior: el historial funcional conserva todas las finalizaciones y reaperturas
previas. Los artefactos posteriores deberán preservar esa trazabilidad sin que
este freeze defina tipo SQL de `fecha_finalizacion`, columnas o tabla de
historial, payload, endpoint, DTO, evento ni outbox.

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
REABIERTA
CAMBIO_PRIORIDAD
CAMBIO_FECHA_OBJETIVO
CAMBIO_TITULO
CAMBIO_DESCRIPCION
```

Cada entrada conserva como mínimo tipo, instante, tarea, actor si existe y valor anterior/nuevo cuando corresponda. El actor humano local deberá poder resolverse mediante la estrategia canónica interinstalación pendiente si el historial resulta sincronizable; este freeze no presupone columnas concretas de UID.

`REABIERTA` representa exclusivamente la operación funcional explícita
`COMPLETADA → PENDIENTE` definida en la sección 9.1; no es un estado persistido ni
se utiliza para transiciones ordinarias. Toda entrada `REABIERTA` debe conservar
conceptualmente:

```text
tarea
actor
instante
estado_anterior = COMPLETADA
estado_nuevo = PENDIENTE
motivo obligatorio
```

Esta entrada conserva además la evidencia histórica de la finalización anterior
aunque la reapertura deje `Tarea.fecha_finalizacion` corriente en `NULL`; no se
crea un segundo historial ni una entidad adicional.

El motivo es parte estructurada y obligatoria de esa entrada funcional: no puede
quedar como texto libre opcional, inferirse desde un comentario ni sustituirse
por éste. Los artefactos posteriores definirán su representación sin que este
freeze establezca nombre de columna, tipo SQL, longitud, schema HTTP, DTO, tabla,
JSON, evento, `command_code` ni payload de outbox. Si la Tarea resultara
sincronizable, su estrategia todavía abierta deberá preservar también este dato;
esta regla no decide sync, evento ni outbox.

```text
REABIERTA → historial_funcional
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

### Decisión

```text
CANCELADA → estado funcional
deleted_at → eliminación técnica
```

La futura materialización técnica deberá **incluir `deleted_at` desde su primer
diseño**, aunque el MVP no exponga una operación funcional de eliminación. Su
ausencia significa registro vigente; su presencia significa baja lógica técnica.
Una tarea cancelada sigue visible en consultas ordinarias según sus filtros y
conserva seguimiento; una tarea con baja técnica queda excluida de consultas
ordinarias, incluida la de vencidas. Comentarios e historial deben sobrevivir y
seguir disponibles para trazabilidad técnica/administrativa autorizada futura;
no se define purga ni eliminación en cascada.

### Evidencia

- **Repositorio:** entidades de negocio y repositorios de varios dominios aplican
  de forma reiterada `deleted_at IS NULL`; esto evidencia un patrón transversal,
  no la existencia de Tarea.
- **Repositorio:** el freeze separa expresamente cancelación funcional de
  eliminación técnica y exige conservar historial y comentarios.
- **Inferencia:** reservar la baja lógica desde el primer diseño evita confundirla
  después con un estado y protege trazabilidad.
- **Decisión de diseño nueva:** se exige su presencia inicial sin habilitar delete.

### Alternativas descartadas y justificación

Se descarta omitirlo porque una incorporación tardía alteraría el contrato de
vigencia y filtros; se descarta usar `CANCELADA` como borrado porque una tarea
cancelada sigue siendo un hecho funcional consultable; y se descarta exponer una
operación de eliminación o diseñar purga por estar fuera de alcance.

### Impacto en artefactos posteriores

El DER deberá prever baja lógica y las lecturas ordinarias deberán excluirla. Los
artefactos posteriores decidirán mecanismos y acceso extraordinario sin crear en
este freeze una operación DELETE ni una política de permisos.

## 20. Identidad y autorización

Para operaciones manuales:

```text
Authorization: Bearer
→ get_authenticated_principal
→ AuthenticatedPrincipal.id_usuario
→ identidad humana efectiva
```

Para todo endpoint nuevo de `gestion_operativa` autenticado mediante Bearer:

```text
X-Usuario-Id
→ NO REQUERIR
→ NO PARSEAR
→ NO COMPARAR
→ NO USAR como identidad
→ NO USAR como autorización
```

GOP no tiene endpoints heredados y, por lo tanto, no debe nacer con el contrato
histórico de `X-Usuario-Id`. Esa compatibilidad puede permanecer temporalmente en
endpoints antiguos de otros dominios hasta su migración, pero no debe expandirse a
`gestion_operativa`.

Identidad humana y contexto técnico son responsabilidades distintas:

```text
Authorization / AuthenticatedPrincipal → identidad humana
X-Op-Id                           → identidad técnica de operación
X-Sucursal-Id                     → contexto según contrato del command
X-Instalacion-Id                  → contexto técnico de instalación
If-Match-Version                  → concurrencia optimista cuando corresponda
```

Ninguno de esos headers técnicos autentica a una persona. En particular,
`X-Sucursal-Id` no define automáticamente el scope funcional de `Tarea`; esa
relación depende de las decisiones funcionales todavía abiertas.

Administrativo conserva ownership de usuarios, autenticación, autorización, roles y permisos, y provee sus mecanismos. `gestion_operativa` consume la identidad de usuario y debe definir qué acciones funcionales sobre Tareas requieren autorización y qué relación o scope habilita cada acción, sin redefinir el modelo administrativo.

La política funcional de autorización y visibilidad permanece **NO CONGELADA / BLOQUEANTE**. Antes del DER y DEV-API debe decidir, sin inventar todavía permisos, roles, códigos ni autorización contextual:

- si un usuario puede consultar sólo tareas asignadas a él o también las creadas por él;
- quién puede consultar tareas sin responsable o tareas de otros usuarios;
- cómo incide `id_sucursal`, si finalmente se incorpora, y quién puede consultar tareas globales;
- cómo se comporta **Mis tareas**;
- quién puede modificar título/descripción, asignar, reasignar, desasignar, cambiar prioridad, cambiar fecha objetivo, cambiar estado, completar, cancelar y comentar.
- quién puede reabrir una tarea completada mediante la operación explícita de la sección 9.1.

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
| Reabrir tarea completada | `COMMAND_WRITE_NEGOCIO` |
| Agregar comentario | `COMMAND_WRITE_NEGOCIO` |
| Consultas | `QUERY_READLIKE` |

Cada futuro `COMMAND_WRITE_NEGOCIO` deberá declarar expresamente
`SINCRONIZABLE` o `LOCAL / NO SINCRONIZABLE`; la clasificación no puede quedar
implícita.

La presencia de `Authorization: Bearer` depende de que el command tenga un actor
humano autenticado. Para commands manuales o ejecutados por una persona:

```text
Authorization: Bearer
→ get_authenticated_principal
→ AuthenticatedPrincipal.id_usuario
→ identidad humana efectiva
```

En esos commands se mantiene además:

```text
X-Usuario-Id
→ NO REQUERIR
→ NO PARSEAR
→ NO COMPARAR
→ NO USAR como identidad
→ NO USAR como autorización
```

Todo `COMMAND_WRITE_NEGOCIO` clasificado como `SINCRONIZABLE` deberá aplicar los
headers técnicos CORE-EF que correspondan, independientemente de que tenga actor
humano o `origen = SISTEMA`:

```text
X-Op-Id
X-Sucursal-Id
X-Instalacion-Id
If-Match-Version cuando modifica un recurso existente/versionado
```

`X-Op-Id`, `X-Sucursal-Id` y `X-Instalacion-Id` aportan contexto técnico, no
identidad humana. `If-Match-Version` depende de la naturaleza del recurso y del
command, no del tipo de actor. `X-Sucursal-Id` no define el scope funcional de
`Tarea`. Los detalles concretos de cada header deberán cerrarse en DEV-ARCH,
DEV-SRV y DEV-API del command correspondiente.

Para commands automáticos con `origen = SISTEMA` no se exigen ni se asumen
`Authorization: Bearer`, `AuthenticatedPrincipal`, un usuario ficticio ni un
`id_usuario_creador` artificial. Se mantiene:

```text
id_usuario_creador = NULL
generador_sistema = requerido
```

El mecanismo concreto mediante el cual un proceso técnico o sistema queda
autorizado para ejecutar un command GOP permanece **NO CONGELADO** y deberá
resolverse posteriormente en DEV-ARCH-GOP, DEV-SRV, DEV-API o la infraestructura
transversal correspondiente, sin definirlo en este freeze.

La clasificación `SINCRONIZABLE` o `LOCAL / NO SINCRONIZABLE` es independiente de
la existencia de actor humano o de `origen = SISTEMA`: no se infiere que todo
command sincronizable requiera Bearer ni que un command de sistema sea local/no
sincronizable.

Su DEV-SRV/DEV-API deberá resolver UID/identidad global cuando aplique,
versionado, idempotencia, fingerprint, replay, outbox, allowlist de sync, misma
transacción, rollback, conflictos, procedencia e historial funcional cuando
corresponda. Si es local/no sincronizable, deberá declarar `sync = NO`, justificar
qué componentes CORE-EF aplican y cuáles no, y no copiar automáticamente outbox,
UID global, allowlist o sync.

La implementación de #412 mediante PR #478 constituye el primer patrón
productivo validado de un `COMMAND_WRITE_NEGOCIO` autenticado mediante Bearer y
consumidor del runtime transversal de idempotencia. Debe utilizarse como
referencia arquitectónica para futuros commands GOP, sin copiar mecánicamente
requisitos propios de `valor_parametro`. Por ejemplo, crear tarea no debe asumir
automáticamente `If-Match-Version`; modificar, reasignar, cambiar estado, reabrir
o cambiar fecha objetivo deberán evaluarlo si la futura `Tarea` resulta
versionada.

Para las consultas `QUERY_READLIKE`:

```text
headers write       → NO APLICA
X-Op-Id             → NO APLICA
If-Match-Version    → NO APLICA
idempotencia command → NO APLICA
outbox              → NO APLICA
```

Bearer y autorización podrán aplicar según la futura política funcional de
acceso. Este incremento no implementa endpoints ni afirma cumplimiento runtime
para GOP.

## 22. Versionado

Se adopta como estrategia objetivo la concurrencia optimista para las futuras modificaciones de `Tarea`. Los contratos técnicos posteriores deberán definir el mecanismo de versión compatible con CORE-EF y `If-Match-Version` cuando corresponda.

La materialización concreta —incluido si corresponde un campo `version_registro` en una futura entidad persistente— permanece pendiente de `DEV-ARCH-GOP`, DER y SQL.

Permanece abierta la decisión: **¿agregar comentario incrementa `version_registro` de tarea?** La recomendación preliminar es **NO** si el comentario es append-only y no modifica el estado funcional de `Tarea`.

## 23. Idempotencia

Debe aplicarse al menos a crear manual, crear automática, asignar/reasignar,
cambiar estado, reabrir y agregar comentario. Los contratos posteriores deberán
definir criterio de payload, mismo `op_id` con mismo payload, mismo `op_id` con
payload distinto y retry posterior a error. La futura reapertura deberá evaluar
el runtime transversal #469/#470 como los demás commands GOP, sin que este freeze
defina `command_code`, target, fingerprint, snapshot ni proyección de respuesta.

La generación automática además debe deduplicar reintentos y el mismo hecho fuente.

#469/#470 ya proveen el ledger durable y el runtime transversal reusable, y la
implementación productiva de #412 en PR #478 validó su consumo. Cuando un command
GOP requiera idempotencia durable y replay compatible con el modelo transversal
vigente, deberá evaluar y preferir el runtime común antes de diseñar un
ledger/replay propio. Las referencias conceptuales vigentes son:

```text
canonical_payload_hash(...)
claim_operation(...)
complete_operation(...)
```

Este freeze no define para GOP `command_code`, `target_type`, `target_uid`,
`target_key`, fingerprint concreto, snapshot concreto ni códigos de error
propios. Cada DEV-SRV/DEV-API deberá resolverlos para su command.

El runtime transversal no decide la semántica de negocio. Cada command GOP
conserva responsabilidad sobre autorización funcional, `command_code`, target
lógico, proyección idempotente, reglas de negocio, CAS/concurrencia, historial
funcional, outbox funcional, response projection, errores de dominio,
clasificación de sync y rollback/transacción.

```text
ledger idempotente
!= outbox
!= historial funcional
!= auditoría
```

Para commands GOP que adopten el runtime transversal, el patrón objetivo a
evaluar es:

```text
BEGIN
→ autenticación/autorización
→ parsing CORE-EF
→ fingerprint / claim
→ REPLAY | CONFLICT | EXECUTE
→ si EXECUTE:
     validaciones DB
     lock/CAS si corresponde
     cambio funcional
     historial si aplica
     outbox si aplica
     complete_operation
→ COMMIT exterior
```

Cualquier fallo antes del commit debe revertir negocio, historial transaccional,
outbox y receipt idempotente. Este flujo no se impone a todos los commands GOP:
cada contrato deberá justificar su aplicabilidad y frontera transaccional.

```text
REPLAY compatible
→ devuelve el resultado lógico original
→ no relee estado actual para reconstruir la respuesta
→ no vuelve a ejecutar negocio
→ no genera nuevo outbox
```

El snapshot concreto de `Tarea` permanece pendiente.

## 24. Sync

**NO CONGELADO.** Las alternativas son `SINCRONIZABLE`, `LOCAL` o `MIXTO`. Se recomienda evaluar seriamente `SINCRONIZABLE` por la necesidad futura de consultar **Mis tareas** entre instalaciones.

La alternativa `SINCRONIZABLE` obliga a resolver identidad global, procedencia,
versionado, conflictos, outbox, allowlist y replay coherente. La alternativa
`LOCAL` debe declarar `sync = NO` y justificar qué soporte transversal conserva,
sin incorporar infraestructura de sync por defecto. La alternativa `MIXTO`
exige clasificar cada command expresamente como sincronizable o local/no
sincronizable y delimitar qué información puede viajar. Estas consecuencias no
seleccionan una alternativa.

La decisión debe tomarse antes del DER porque afecta `uid_global`, metadata CORE-EF, outbox, allowlist, conflictos, comentarios, historial, versiones e idempotencia. Este documento no crea eventos, productores, consumidores ni entradas de allowlist.

```text
AuthenticatedPrincipal.id_usuario
→ identidad humana local efectiva
```

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
- reabrir explícitamente una tarea completada según la sección 9.1;
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
20. Los estados definitivos del MVP son `PENDIENTE`, `EN_CURSO`, `COMPLETADA` y `CANCELADA`; `PENDIENTE` es inicial, y los dos últimos son terminales para transiciones ordinarias.
21. Sólo `COMPLETADA` admite reapertura explícita a `PENDIENTE`, con motivo e historial íntegro; `CANCELADA` no admite reapertura en el MVP.
22. Las prioridades definitivas son `BAJA < NORMAL < ALTA < URGENTE`, con `NORMAL` como default y sin efecto automático sobre vencimiento o SLA.
23. `fecha_objetivo` tiene granularidad funcional DATE y conserva validez durante todo su día calendario.
24. La materialización inicial deberá prever `deleted_at` como baja lógica técnica, distinta de `CANCELADA`, sin que ello habilite una operación de eliminación en el MVP.
25. El vencimiento usa una única fecha local capturada del reloj del servidor en `America/Argentina/Buenos_Aires` y la fórmula exacta de la sección 12.

## 29.1 Coherencia conjunta del primer cierre

- DATE y vencimiento usan la misma granularidad: el día objetivo completo sigue
  vigente y sólo una fecha estrictamente anterior al corte local queda vencida.
- `COMPLETADA` y `CANCELADA` quedan excluidas de vencimiento; la reapertura a
  `PENDIENTE` vuelve a habilitar su derivación sin persistir `VENCIDA`.
- Una baja técnica excluye la tarea de lecturas ordinarias, mientras una
  cancelación permanece como hecho funcional visible.
- La prioridad no altera vencimiento, estado, autorización ni SLA.
- Ninguna de estas decisiones traslada tareas a `operativo`, materializa una
  entidad técnica ni resuelve sync, identidad portable, permisos o versionado de
  comentarios.

## 30. Decisiones todavía abiertas

De la numeración original de blockers, este incremento cierra exclusivamente
**#2, #3, #4, #5, #8 y #9** mediante las secciones 9, 9.1, 10, 11, 19 y 12,
respectivamente. Permanecen abiertos, con su numeración original y sin resolución
incidental:

1. Si `id_sucursal` es opcional o no.
6. Estrategia de sync: `SINCRONIZABLE`, `LOCAL` o `MIXTO`.
7. Si agregar comentario incrementa `version_registro` de la tarea.
10. Identidad canónica interinstalación de usuario para toda referencia humana persistida que deba sincronizarse en `gestion_operativa` —como creador, responsable, autor de comentario y actor del historial funcional—: mecanismo de resolución o mapping y dependencia con Administrativo/Técnico.
11. Política funcional de visibilidad y mutación de Tareas: alcance de Mis tareas, tareas creadas, tareas sin asignar, tareas de otros usuarios, scope de sucursal/global y reglas para editar, asignar, reasignar, desasignar, cambiar prioridad, cambiar fecha objetivo, cambiar estado, completar, cancelar, reabrir y comentar.

Estas decisiones deberán resolverse y validarse contra arquitectura, CORE-EF, autorización, sincronización, SQL, implementación y tests antes de afirmar un contrato técnico completo.
