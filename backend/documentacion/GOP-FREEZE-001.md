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
- `uid_global`: identidad distribuida conceptual, inmutable y obligatoria para la
  futura Tarea sincronizable; coexistirá con el ID local técnico, que no podrá
  usarse como identidad entre instalaciones.
- Código visible de tarea: fuera del MVP, salvo necesidad funcional posterior expresamente aprobada.

La materialización física de ambos identificadores queda para DEV-ARCH-GOP, DER
y SQL. #492 congela en la sección 30 la identidad conceptual portable de Tarea
y sus referencias, sin decidir PK/FK concretas ni un DTO/payload físico; no
reabre la sincronizabilidad congelada por #491.

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
  su relación funcional habilitante se define en la sección 20.2, mientras el
  mecanismo técnico de autorización permanece pendiente.

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

### Decisión

`id_sucursal` es **opcional** en el contrato funcional del MVP:

```text
id_sucursal = NULL
→ tarea global
→ no pertenece funcionalmente a ninguna sucursal específica

id_sucursal = <id>
→ tarea de sucursal
→ pertenece funcionalmente a esa única sucursal
```

Ambas clases son válidas. El valor no identifica al creador, al responsable, a
la sucursal desde la que se consulta ni a la instalación que originó el cambio.
En particular, `id_instalacion_origen` conserva exclusivamente procedencia
técnica CORE-EF: una operación puede originarse en una instalación distinta de
la sucursal funcional de la tarea, y una tarea global también puede tener
procedencia técnica. `id_instalacion_origen != scope_funcional_tarea`.

El scope funcional se define al crear la tarea y es **inmutable** durante todo
el MVP. Por lo tanto, `id_sucursal` no puede cambiar después de la creación: no
se admite convertir una tarea global en tarea de sucursal, convertir una tarea
de sucursal en global ni trasladarla entre sucursales. Si el scope fue definido
incorrectamente, la corrección no se realiza mutando `id_sucursal`; requiere una
nueva Tarea en el scope correcto, con la trazabilidad que determine el diseño
posterior. Este freeze no incorpora una operación de cambio de scope ni impone
una acción automática sobre la tarea anterior.

### Evidencia

- **Repositorio:** `DEV-ARCH-OPE-001` asigna a `operativo` el ownership de
  sucursal e instalación, excluye tareas y exige separación con
  `gestion_operativa`; el freeze ya distingue procedencia técnica de scope.
- **Repositorio:** no existen SQL, backend ni tests runtime de Tarea que impongan
  pertenencia obligatoria a sucursal. El alcance admite tareas puramente internas
  y futuras tareas de sistema, sin demostrar una sucursal funcional única.
- **Inferencia:** el seguimiento administrativo de toda la organización y los
  procesos transversales son casos legítimos que se perderían forzando una
  sucursal; usar la instalación de origen produciría un scope accidental.
- **Decisión de diseño nueva:** `NULL` se congela como scope global y un valor
  como scope de exactamente una sucursal.

### Alternativas descartadas y justificación

Se descarta `id_sucursal NOT NULL` porque fuerza una pertenencia funcional no
demostrada a tareas globales. Se descarta un discriminador o modelo de scope
separado porque el MVP sólo necesita las dos alternativas inequívocas anteriores
y no hay evidencia que justifique otra estructura. No se inventa una tabla ni
una relación multi-sucursal.

### Impacto en artefactos posteriores

DEV-ARCH-GOP y los artefactos posteriores deberán preservar ambos scopes y su
semántica, pero decidirán recién entonces FK, nulabilidad física, constraints,
índices, filtros y contratos. Esta decisión no diseña SQL ni convierte a
`operativo` en dueño de Tarea.

## 15. Comentarios

```text
Tarea
└── Comentarios 0..N
```

Cada comentario conserva tarea, autor, texto e instante. Para autor humano se usa `AuthenticatedPrincipal.id_usuario`, que identifica al actor local en la instalación donde ocurre la operación. Si esa referencia viaja mediante sync, usa el contrato conceptual de identidad administrativa portable congelado en la sección 30; su materialización sigue pendiente y este freeze no presupone columnas de UID.

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

Cada entrada conserva como mínimo tipo, instante, tarea, actor si existe y valor
anterior/nuevo cuando corresponda. Tarea es sincronizable por #491; la
representación portable del actor y de las demás referencias del historial se
resuelve conceptualmente en #492. Este freeze no presupone columnas concretas de
UID, PK/FK ni payload físico.

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
JSON, evento, `command_code` ni payload de outbox. La estrategia sincronizable
ya congelada para Tarea deberá preservar también este dato cuando corresponda a
la operación distribuible; esta regla no convierte el historial funcional en
outbox o inbox ni define el evento o payload físico. Las referencias portables
siguen sujetas a la materialización posterior del contrato #492; la granularidad de comentario/versionado queda congelada por #493.

```text
REABIERTA → historial_funcional
historial_funcional
!= comentario
!= auditoria_administrativa
!= log_tecnico
!= outbox
!= inbox
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

La futura generación debe ser idempotente frente a reintentos y al mismo hecho
fuente para impedir duplicados. Esto exige dos garantías complementarias:

```text
op_id         -> idempotencia técnica de una operación distribuida concreta
hecho fuente  -> idempotencia funcional de la generación automática
```

Un mismo hecho fuente procesado después con un `op_id` nuevo no debe crear una
segunda Tarea funcional equivalente. Quedan pendientes para los artefactos
técnicos la clave funcional exacta, columnas, constraint, índice, tabla, hash,
natural key, combinación de identificadores, algoritmo, eventual ventana
temporal y repository/command. Este freeze no inventa esa clave ni diseña SQL o
API.

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
relación no sustituye la decisión funcional de la sección 14.

Administrativo conserva ownership de usuarios, autenticación, autorización,
roles y permisos, y proveerá el mecanismo que materialice el alcance. La política
siguiente es funcional: no crea roles, permisos, scopes HTTP ni una ACL GOP.

### 20.A Habilitación funcional y autorización efectiva

Las capacidades de `usuario_sucursal` son habilitaciones funcionales necesarias,
pero ninguna constituye por sí sola autorización suficiente:

```text
habilitación por sucursal != autorización efectiva

operación humana protegida
→ habilitación funcional requerida
  AND autorización efectiva de Administrativo
```

Administrativo conserva ownership de la autorización efectiva y compone roles,
permisos, contexto y denegaciones explícitas conforme a su contrato vigente.
`gestion_operativa` sólo declara qué habilitación funcional consume para cada
acción; no crea permisos, roles, ACL, claims, scopes HTTP ni un motor paralelo.

Para una tarea de sucursal, `puede_consultar` vigente es necesario para consultar
por scope, `puede_operar` vigente es necesario para ser responsable y
`puede_administrar` vigente es necesario para crear o gestionar por scope. La
capa administrativa puede denegar igualmente una operación humana protegida.
Para tareas globales, las habilitaciones equivalentes de consulta, operación y
administración también deben componerse con autorización efectiva; su
representación técnica permanece pendiente en Administrativo.

#### Vigencia de `usuario_sucursal`

Los registros relacionados se consideran vigentes únicamente bajo estos
predicados completos:

```text
usuario vigente
= estado_usuario = ACTIVO
  AND usuario.deleted_at IS NULL
  AND usuario.fecha_baja IS NULL

sucursal vigente
= estado_sucursal = ACTIVA
  AND sucursal.deleted_at IS NULL
  AND sucursal.fecha_baja IS NULL
```

Un vínculo `usuario_sucursal` está vigente únicamente cuando, para un mismo
`instante_corte_utc`, se cumplen simultáneamente:

```text
usuario_sucursal.deleted_at IS NULL
AND estado_vinculo = ACTIVO
AND fecha_desde_utc <= instante_corte_utc
AND (fecha_hasta_utc IS NULL OR instante_corte_utc < fecha_hasta_utc)
AND usuario vigente
AND sucursal vigente
```

El intervalo es `[fecha_desde, fecha_hasta)`: inclusivo al inicio y exclusivo al
final. `instante_corte_utc` se captura una sola vez por caso de uso desde el reloj
confiable del servidor en UTC; no procede del cliente, navegador, instalación ni
sucursal. El mecanismo de inyección del reloj se decidirá después.

`fecha_desde` y `fecha_hasta` representan instantes absolutos cuyo canon temporal
es UTC. Todo contrato futuro que materialice estas fronteras debe exigir un
timestamp con offset explícito; son ejemplos válidos `2026-08-15T13:00:00Z` y
`2026-08-15T10:00:00-03:00`, mientras `2026-08-15T10:00:00` sin offset es
inválido. Esta decisión no modifica ahora schemas administrativos existentes.

La conversión y comparación canónicas son:

```text
input con offset
→ convertir a UTC
→ comparar como instante UTC

2026-08-15T10:00:00-03:00
→ 2026-08-15T13:00:00Z

fecha_desde_utc <= instante_corte_utc
AND (
  fecha_hasta_utc IS NULL
  OR instante_corte_utc < fecha_hasta_utc
)
```

Si una persistencia futura usa `timestamp without time zone`, el valor sólo puede
considerarse UTC canónico cuando la escritura recibió un offset explícito,
convirtió el instante a UTC y persistió esa representación normalizada. El
timezone de la sesión PostgreSQL no es autoridad semántica.

Los valores legacy naïve requieren tratamiento separado:

```text
timestamp legacy sin offset
→ no permite determinar por sí solo la zona original
→ no puede reinterpretarse silenciosamente como UTC
```

La normalización UTC del contrato futuro no es retroactiva. Antes de usar un
registro legacy ambiguo como frontera temporal autoritativa para visibilidad,
elegibilidad, asignación o mutación GOP, debe resolverse explícitamente su
semántica mediante una migración/backfill explícito **o** una regla legacy
documentada y validada. Este freeze no elige la estrategia, no supone un timezone
histórico y no diseña SQL, script, heurística ni job correctivo.

Cuando Administrativo materialice capacidades globales con vigencia temporal,
deberá respetar los mismos instantes UTC canónicos e intervalos inequívocos, sin
que este freeze diseñe su estructura.

Una capacidad está vigente sólo cuando el vínculo anterior está vigente y su
flag correspondiente vale `true`:

```text
puede_consultar vigente   = vínculo vigente AND puede_consultar = true
puede_operar vigente      = vínculo vigente AND puede_operar = true
puede_administrar vigente = vínculo vigente AND puede_administrar = true
```

Esta semántica es el contrato funcional completo; no se reduce a una consulta
runtime que pudiera omitir una parte del intervalo o de la vigencia relacionada.

### 20.0 Decisión de creación manual por scope

Antes de que exista la Tarea, la creación manual depende del alcance funcional
del actor humano sobre el scope propuesto:

```text
Crear tarea de sucursal
→ requiere capacidad administrativa vigente sobre esa sucursal
→ equivalente funcional a puede_administrar = true
→ requiere además autorización efectiva de Administrativo

Crear tarea global
→ requiere alcance global administrativo
→ requiere además autorización efectiva de Administrativo
```

El actor humano se identifica mediante `AuthenticatedPrincipal.id_usuario`.
Estas condiciones son reglas funcionales de `gestion_operativa`, no nombres de
permisos, roles, claims, scopes HTTP ni una ACL. `puede_administrar` es una
capacidad existente de `usuario_sucursal`; la representación técnica de la
capacidad global administrativa pertenece a Administrativo y queda para
artefactos posteriores. La habilitación no constituye el grant final.

La regla anterior no autentica ni autoriza técnicamente tareas con `origen =
SISTEMA`: para ellas se mantienen `id_usuario_creador = NULL` y
`generador_sistema` requerido. La generación automática futura deberá producir
el scope funcional correspondiente, pero su mecanismo técnico de autorización
permanece pendiente y no se inventa un usuario de sistema.

### 20.1 Decisión de visibilidad y consultas

Se reconocen bases funcionales independientes de visibilidad por autoría,
responsabilidad elegible, consulta por scope y administración por scope. Un
usuario puede ver una tarea si cumple al menos una de estas condiciones:

1. es su creador humano;
2. es su responsable actual y conserva elegibilidad vigente;
3. tiene `puede_consultar = true` vigente sobre la sucursal de una tarea de
   sucursal;
4. tiene `puede_administrar = true` vigente sobre esa sucursal;
5. para una tarea global, tiene alcance global de consulta o alcance global
   administrativo vigente; o
6. para una tarea de sucursal cuyo scope dejó de estar vigente, tiene alcance
   global administrativo vigente.

Estas bases son alternativas e independientes (`creador OR responsable elegible
OR consulta por scope OR administración por scope`); no se exige satisfacer más
de una. Toda consulta humana protegida requiere autorización efectiva de
Administrativo, pero la habilitación funcional adicional depende de la relación
que funda la visibilidad:

```text
creador humano + autorización efectiva
→ visibilidad por autoría
→ no requiere puede_consultar, puede_operar ni puede_administrar

responsable registrado + elegibilidad vigente + autorización efectiva
→ visibilidad por responsabilidad

capacidad de consulta vigente + autorización efectiva
→ visibilidad ordinaria por scope

capacidad administrativa vigente + autorización efectiva
→ visibilidad administrativa por scope
```

`puede_administrar` es una base propia de visibilidad porque el actor debe acceder
al objeto que administra; **no implica ni deriva `puede_consultar = true`**. Para
tareas globales se aplica el equivalente funcional con alcance global
administrativo, sin inventar su representación técnica.

Por lo tanto:

- **Mis tareas** significa exclusivamente tareas cuyo responsable registrado es
  el usuario y cuya elegibilidad continúa vigente. No incluye tareas sólo por
  haberlas creado ni conserva una tarea por una asignación devenida inelegible.
- **Tareas creadas por mí** es una consulta separada. El creador conserva
  visibilidad después de una asignación, reasignación o desasignación, aunque no
  sea responsable ni tenga actualmente alcance sobre el scope de la tarea.
- Las tareas sin responsable son visibles para su creador humano y por capacidad
  de consulta o administración del scope: los flags vigentes correspondientes
  para su sucursal o los alcances globales equivalentes para una tarea global.
- Una tarea asignada a otra persona es visible para su creador y por la capacidad
  de consulta o administración correspondiente. `puede_consultar` no habilita
  gestión por scope.
- Una tarea de sucursal entra en listados por scope sólo con `puede_consultar =
  true` vigente para visibilidad ordinaria o `puede_administrar = true` vigente
  para visibilidad administrativa. Una tarea global entra por alcance global de
  consulta o administrativo; no se replica como tarea de cada sucursal.
- La asignación individual mantiene la tarea en **Mis tareas** y visible para el
  responsable elegible según el scope, incluida una tarea global o de sucursal.

Las tareas `origen = SISTEMA` aplican las mismas reglas según responsable y
scope. Como no tienen creador humano, no obtienen visibilidad por autoría;
`generador_sistema` no es actor, usuario, rol ni alcance.

### 20.1.1 Elegibilidad del responsable

La elegibilidad del responsable es una invariante continua y compuesta: requiere
simultáneamente habilitación operativa vigente para el scope y autorización
efectiva vigente de Administrativo suficiente para ejercer las capacidades
funcionales del responsable:

```text
Tarea de sucursal
→ puede_operar = true vigente sobre esa sucursal
  AND autorización efectiva vigente suficiente

Tarea global
→ alcance global operativo vigente
  AND autorización efectiva vigente suficiente
```

`puede_operar` y el alcance global operativo son habilitaciones funcionales
necesarias, no autorización. Este freeze no crea un permiso GOP, código, rol,
claim, scope HTTP ni ACL para expresar la suficiencia; su materialización concreta
pertenece a Administrativo y a los artefactos posteriores.

La misma regla compuesta se aplica al usuario destino en la primera asignación y
en cada reasignación, incluidas las tareas `origen = SISTEMA`: no basta con
`puede_operar = true` ni con alcance global operativo. Separadamente, la persona
que asigna o reasigna necesita la habilitación administrativa de la matriz y su
propia autorización efectiva. La autorización del actor no sustituye la del
destino, ni viceversa. La asignación no permite eludir el scope y no usa
`id_instalacion_origen` para decidir elegibilidad.

Una asignación con elegibilidad compuesta vigente habilita las capacidades
funcionales del responsable.
Después de una reasignación, el nuevo responsable debe cumplir la elegibilidad y
el anterior pierde las capacidades derivadas de esa relación; el creador conserva
su visibilidad y comentario. Una tarea sin responsable sigue siendo válida, pero
su primera asignación debe cumplir esta regla antes de que pueda pasar a
`EN_CURSO` o `COMPLETADA`.

Estas son reglas funcionales, no permisos, roles, claims, ACL ni scopes HTTP. La
forma en que Administrativo materialice el alcance global y resuelva la
autorización efectiva queda para los artefactos posteriores.

Si el responsable registrado pierde luego la habilitación operativa **o** la
autorización efectiva suficiente, permanece registrado hasta una mutación
explícita, pero pasa a ser responsable inelegible. Deja de estar habilitado por
esa relación para **Mis tareas**, `PENDIENTE ↔ EN_CURSO`, completar o comentar, y
la mera referencia persistida no conserva visibilidad. Sólo puede mantener acceso
por otra relación independiente —creador, consulta o administración por scope—
si también conserva la autorización efectiva correspondiente a esa relación.

No hay desasignación automática, cambio automático de estado, job correctivo ni
otro side effect silencioso desde Administrativo. Una persona con capacidad
administrativa aplicable según el estado del scope y autorización efectiva debe
reasignar a un destino elegible o desasignar explícitamente. En una tarea
terminal, la pérdida de elegibilidad no habilita una mutación ordinaria del
snapshot.

#### Fallback ante sucursal no vigente

Si la sucursal del scope deja de cumplir su predicado de vigencia, todas las
capacidades locales derivadas de `usuario_sucursal` dejan de estar vigentes. La
tarea conserva sin cambios su scope, estado, responsable registrado y demás
datos: no se cancela, reasigna, desasigna, elimina ni convierte automáticamente en
global, y `id_sucursal` continúa inmutable.

El responsable registrado pierde elegibilidad, visibilidad y ejecución por la
relación de responsable, pero permanece referenciado para trazabilidad. Puede
conservar acceso únicamente por otra base independiente, como autoría, o por el
fallback siguiente:

```text
tarea de sucursal cuyo scope dejó de estar vigente
→ alcance global administrativo vigente
  AND autorización efectiva de Administrativo
→ visibilidad administrativa y gestión residual
```

Este actor global puede ejecutar las mismas operaciones administrativas de la
matriz cuando el ciclo de vida y las demás invariantes lo permitan: modificar
título/descripción, asignar, reasignar, desasignar, cambiar prioridad o
`fecha_objetivo`, cambiar estado o completar por gestión, cancelar, reabrir
`COMPLETADA` y comentar por relación administrativa. No obtiene operaciones
nuevas, no puede cambiar `id_sucursal`, trasladar la tarea ni convertirla en
global. Toda asignación o reasignación sigue exigiendo un destino elegible.

Para tareas de sucursal, las capacidades existentes se consumen sin fusionarlas:

```text
puede_consultar vigente   → visibilidad por scope
puede_operar vigente      → elegibilidad continua como responsable
puede_administrar vigente → visibilidad administrativa, creación y gestión por scope
```

Para tareas globales se requieren, respectivamente, alcance global de consulta,
alcance global operativo y alcance global administrativo. Este freeze no asigna
esa semántica global a flags de `usuario_sucursal` ni inventa su representación
técnica; Administrativo deberá definirla en artefactos posteriores.

### 20.2 Decisión de mutación

Para el MVP se distinguen **ejecución del trabajo** y **gestión por scope**:

| Acción | Creador humano | Responsable vigente/elegible | Habilitación administrativa aplicable |
| --- | --- | --- | --- |
| Modificar título o descripción | No | No | Sí |
| Asignar, reasignar o desasignar | No | No | Sí |
| Cambiar prioridad o fecha objetivo | No | No | Sí |
| Cambiar `PENDIENTE ↔ EN_CURSO` | No | Sí | Sí |
| Completar | No | Sí | Sí, sólo si existe responsable |
| Cancelar | No | No | Sí |
| Reabrir `COMPLETADA → PENDIENTE` | No | No | Sí |
| Comentar | Sí | Sí | Sí |

La columna administrativa se interpreta según el estado del scope:

```text
tarea global
→ alcance global administrativo vigente

tarea de sucursal con sucursal vigente
→ puede_administrar = true vigente sobre esa sucursal

tarea de sucursal con sucursal no vigente
→ alcance global administrativo vigente (fallback)
```

En los tres casos se requiere además autorización efectiva de Administrativo; el
fallback global no es un bypass. `puede_consultar` por sí solo nunca habilita
estas acciones. La matriz sólo aplica cuando la operación es funcionalmente
válida según el ciclo de vida; una relación marcada `Sí` no permite eludir la
elegibilidad del responsable ni la terminalidad. No se crean permisos, roles,
claims, scopes HTTP ni ACL GOP.

Mientras `estado IN (COMPLETADA, CANCELADA)`, el snapshot funcional corriente es
inmutable: no pueden modificarse título, descripción, responsable, prioridad ni
`fecha_objetivo`; tampoco se permite asignar, reasignar, desasignar, ejecutar
`PENDIENTE ↔ EN_CURSO`, completar nuevamente ni cancelar nuevamente.
`id_sucursal` permanece además inmutable durante todo el MVP, con independencia
del estado.

Las únicas excepciones funcionales terminales son:

- `COMPLETADA` y `CANCELADA` pueden recibir comentarios conforme a las relaciones
  de la matriz. Por #493, comentar no incrementa `Tarea.version_registro`.
- Sólo `COMPLETADA` puede reabrirse explícitamente a `PENDIENTE`, con motivo,
  historial `REABIERTA` y `fecha_finalizacion` corriente en `NULL`, según las
  reglas ya congeladas. Reabrir exige la habilitación administrativa aplicable
  según el estado del scope y autorización efectiva de Administrativo.
  `CANCELADA` no reabre.

Toda reapertura debe producir atómicamente un postestado válido. Si el responsable
registrado conserva elegibilidad, se mantiene. Si perdió elegibilidad, la misma
operación lógica debe dejar `responsable = NULL` o reemplazarlo por un nuevo
responsable con elegibilidad vigente. Nunca puede resultar una tarea activa con
responsable inelegible:

```text
COMPLETADA → PENDIENTE
→ fecha_finalizacion = NULL
→ responsable elegible conservado
   OR responsable = NULL
   OR nuevo responsable elegible
→ historial REABIERTA con motivo obligatorio
```

La reparación es parte de la invariante funcional de la reapertura, no una
mutación ordinaria previa del snapshot terminal. Si cambia el responsable, los
artefactos posteriores preservarán trazabilidad coherente sin que este freeze
decida si corresponde una o varias entradas de historial. No se diseñan endpoint,
DTO, payload, `command_code`, SQL ni repository.

Después de la reapertura, la tarea vuelve a estar activa y las mutaciones
ordinarias vuelven a aplicarse conforme a la misma matriz, la elegibilidad del
responsable y los demás invariantes; no se crea una matriz adicional.
Si la reapertura deja la tarea sin responsable, `PENDIENTE` sigue siendo válido y
no podrá pasar a `EN_CURSO` ni `COMPLETADA` hasta una asignación elegible.

Ser creador, por sí solo, otorga trazabilidad, consulta y capacidad de comentar,
pero **no** habilita las demás mutaciones. Si el creador también es responsable o
tiene alcance sobre el scope, actúa por esa otra relación. Después de una
reasignación, el anterior responsable pierde las capacidades derivadas de ser
responsable, mientras el creador conserva visibilidad y comentario.

Una tarea sin responsable continúa siendo válida. Puede ser editada, asignada,
desasignada, repriorizada, reprogramada, cancelada, reabierta cuando corresponda
y comentada por quien tiene capacidad administrativa sobre su scope. No puede
pasar a `EN_CURSO` ni `COMPLETADA` mientras siga sin responsable: primero debe
asignarse. Su creador sin esa capacidad puede verla y comentar, pero no asignarla
ni editarla.

### 20.3 Evidencia, alternativas e impacto

- **Repositorio:** creador y responsable ya son distintos, el responsable es
  `0..1`, una tarea sin responsable es válida y Administrativo conserva
  autorización. No existe implementación GOP ni evidencia de ACL, equipos,
  watchers o roles GOP.
- **Repositorio:** el catálogo histórico distingue asignación, reasignación,
  desasignación, estado y consultas, pero no es contrato vigente ni resuelve
  actores.
- **Inferencia:** el responsable necesita ejecutar el trabajo sin administrar su
  definición; la gestión completa corresponde a la relación con el scope. La
  autoría debe conservar consulta sin transformarse en propiedad mutable eterna.
- **Decisión de diseño nueva:** se congelan las reglas de las secciones 20.1 y
  20.2 como política funcional mínima del MVP.

Se descartan **Mis tareas = asignadas + creadas** porque mezcla trabajo vigente
con trazabilidad; mutación total por creador porque sobrevive indebidamente a una
reasignación; mutación total por responsable porque confunde ejecutar con
administrar; y acceso de cualquier usuario porque ignora el scope. También se
descartan ACL por tarea, equipos, sectores, watchers y políticas configurables
por falta de evidencia y por exceder el MVP.

DEV-ARCH-GOP, DEV-SRV y DEV-API deberán materializar estas relaciones junto con
Administrativo sin cambiar su ownership ni inventar equivalencias con roles o
permisos técnicos. Permanecen pendientes los mecanismos de autorización,
contratos HTTP, SQL y tests. Esta decisión funcional no modifica la estrategia
sync ya congelada por #491; #492 congela la identidad interinstalación y #493
congela el append independiente sin efecto sobre `Tarea.version_registro`.

## 21. Decisión CORE-EF y estrategia de sincronización (#491)

### 21.1 Alcance y clasificación

Este incremento resuelve el blocker interno **#6 — estrategia de sync**, trazado
por el issue #491, sin crear endpoints ni artefactos físicos. La decisión es:

```text
Tarea = concepto funcional sincronizable de gestion_operativa
mutación funcional compartida de Tarea = COMMAND_WRITE_NEGOCIO + SINCRONIZABLE
consulta humana = QUERY_READLIKE
recepción/aplicación remota = responsabilidad técnica, no command humano
```

Todas las operaciones funcionales del MVP que crean o alteran el snapshot
compartido deben converger entre instalaciones. Omitir cualquiera —contenido,
asignación, prioridad, fecha objetivo o estado— permitiría dos snapshots
funcionalmente distintos para el mismo trabajo. El origen y el actor no cambian
esa conclusión:

```text
actor humano != clasificación SINCRONIZABLE
origen = SISTEMA != LOCAL / NO SINCRONIZABLE
```

Crear una tarea automática también es sincronizable cuando crea ese estado
compartido. No exige Bearer humano, no materializa un usuario técnico y conserva
`id_usuario_creador = NULL` y `generador_sistema` requerido. Su mecanismo de
autenticación/autorización técnica sigue **NO CONGELADO**: no se inventan API
key, service account, technical bearer, M2M auth, rol ni permiso nuevo.

Agregar comentario es `COMMAND_WRITE_NEGOCIO + SINCRONIZABLE`: el comentario es
seguimiento funcional compartido y omitirlo divergiría la información de Tarea.
Por #493, el append es una operación independiente: no integra el snapshot
funcional mutable ni incrementa `Tarea.version_registro`.

Una eventual baja lógica es `COMMAND_WRITE_TECNICO + SINCRONIZABLE` porque cambia
la disponibilidad distribuida del concepto, pero **no implementa ni habilita**
una operación funcional, endpoint `DELETE` o purga. No se identificó un command
de Tarea puramente local, técnico o efímero dentro del alcance funcional
estudiado. `LOCAL / NO SINCRONIZABLE` queda, por tanto, sin operaciones en esta
matriz; las consultas no pertenecen a esa categoría, sino a `QUERY_READLIKE`.

### 21.2 Evidencia, inferencia y alternativas

- **Repositorio:** `DEV-ARCH-OPE-001` excluye tareas de `operativo`; por ello
  `gestion_operativa != operativo` y la sincronización transversal no traslada
  ownership. `Tarea`, comentario e historial continúan como núcleo funcional;
  outbox, inbox, ledger, conflictos, locks, IDs y metadata de sync son soporte
  transversal. No se adopta compatibilidad heredada como núcleo.
- **Especificación formal:** CORE-EF exige identidad local más `uid_global`
  inmutable, `version_registro`, `op_id`, outbox transaccional, inbox idempotente,
  baja lógica distribuible y persistencia de divergencias materiales. SRV-TEC-002
  separa recepción/aplicación técnica de los commands de negocio.
- **Implementación real:** #469/#470 materializan `operacion_idempotente` y el
  runtime reusable `claim_operation → EXECUTE | REPLAY | CONFLICT →
  complete_operation`; #412/PR #478 es el primer consumidor productivo validado
  con receipt, CAS y outbox en una sola transacción. El repositorio no contiene
  SQL, router, schema, service, repository ni tests runtime GOP/Tarea.
- **Inferencia:** contenido, asignación, prioridad, objetivo, estados,
  reapertura, comentarios y eventual baja deben converger porque todos alteran
  información funcional visible en más de una instalación. La inferencia se
  congela como **decisión de diseño nueva** de #491; no afirma runtime existente.
- **Alternativa descartada:** `LOCAL` haría imposible garantizar un snapshot
  compartido consistente; `MIXTO` por tipo de actor confundiría autoría con
  sincronizabilidad. Tampoco se copia mecánicamente otro dominio ni se declara
  local una creación `SISTEMA`.
- **Impacto posterior:** DEV-ARCH/DER/SQL/DEV-SRV/DEV-API GOP deberán materializar
  esta clasificación, pero dependen de materializar el contrato portable #492 y
  el `uid_global` propio del comentario congelado por #493. Este freeze no define
  nombres de endpoint, payload físico, evento concreto ni allowlist concreta.

### 21.3 Headers técnicos y actor

Todo futuro command `SINCRONIZABLE` exige el helper común CORE-EF y, de forma
conceptual:

```text
X-Op-Id          -> identidad técnica global de la operación
X-Sucursal-Id    -> contexto técnico/contractual del command
X-Instalacion-Id -> contexto y procedencia técnica
```

Los tres son obligatorios para el futuro contrato write sincronizable. Ninguno
autentica a una persona. `X-Sucursal-Id` **no** copia, infiere ni redefine
`Tarea.id_sucursal`; el scope funcional se recibe/valida según el caso de uso y
permanece inmutable. `X-Instalacion-Id` **no** es scope; identifica procedencia
técnica. `X-Usuario-Id` no se requiere, parsea, compara ni usa.

Un command humano protegido usa, por separado:

```text
Authorization: Bearer
-> get_authenticated_principal
-> AuthenticatedPrincipal.id_usuario
```

Un command de sistema conserva la misma infraestructura técnica de sync cuando
modifica estado compartido, pero su autenticación/autorización técnica continúa
pendiente y no se reemplaza por headers CORE-EF.

`If-Match-Version` no aplica a creaciones porque todavía no existe una versión
previa. Es obligatorio en toda mutación ordinaria de una Tarea existente y
versionada: título, descripción, asignación/reasignación/desasignación,
prioridad, fecha objetivo, cambios de estado, completar, cancelar, reabrir y una
eventual baja lógica. Debe expresar la versión esperada y un mismatch real debe
fallar explícitamente sin sobrescritura silenciosa. La frase «toda mutación de
Tarea existente requiere `If-Match-Version`» se refiere a mutaciones de ese
snapshot. Agregar comentario es la excepción específica: no modifica el
snapshot, no usa CAS contra Tarea y no requiere `If-Match-Version` de Tarea.

### 21.4 Versionado e identidad distribuida

Al ser sincronizable, la futura Tarea debe materializar simultáneamente ID local
técnico, `uid_global` inmutable y `version_registro`; el ID local no puede viajar
como identidad distribuida. Las altas nacen en versión 1 y las mutaciones
ordinarias del snapshot y la baja lógica incrementan una vez la versión. El
optimistic locking local y la comparación distribuida son problemas distintos.

#492 congela en la sección 30 la representación **conceptual** de las referencias
remotas de creador, responsable, sucursal e instalación y el tratamiento de
referencias aún desconocidas localmente. El DTO/payload físico permanece
pendiente. GOP consumirá la identidad canónica que materialicen
Administrativo/Técnico; no agrega UID a `usuario`, no crea mapping propio y no
usa IDs locales como identidad remota.

#493 congela que agregar comentario no incrementa `Tarea.version_registro`, no
requiere versión esperada de Tarea y, como pieza sincronizable independiente,
debe conservar su propio `version_registro` conforme a CORE-EF
REQ-SYNC-011/012/013. Su alta nace conceptualmente en versión 1 y, al no existir
edición ni borrado funcional en el MVP append-only, normalmente permanece en 1.
El comentario necesita además `uid_global` propio, único, inmutable y no
reutilizable como identidad canónica distribuida, conforme a CORE-EF
REQ-SYNC-004..009. Así puede reconocerse sin usar la PK local, `op_id`,
`event_id` ni `Tarea.uid_global`; su forma física queda pendiente.

## 22. Idempotencia durable, replay y transacción

Todos los commands sincronizables de la matriz usan `X-Op-Id` y deben reutilizar
la infraestructura transversal #469/#470; queda prohibido crear tabla, ledger o
implementación `claim/replay/complete` paralela en GOP. Cada contrato posterior
definirá `command_code`, target y payload material normalizado:

- mismo `op_id` + mismo command/target/payload: `REPLAY` del snapshot durable
  original, sin releer estado mutable, repetir negocio, incrementar versión ni
  emitir outbox;
- mismo `op_id` + command, target o payload material distinto: `CONFLICT` según
  el orden transversal vigente `COMMAND → TARGET → PAYLOAD`, sin efecto;
- error antes del commit: no queda receipt completado; el retry puede volver a
  `EXECUTE`;
- `complete_operation` sólo ocurre junto al resultado lógico exitoso dentro de
  la transacción exterior del caso de uso.

La generación automática debe combinar la idempotencia técnica por `op_id` con
la idempotencia funcional por el mismo hecho fuente. Son garantías obligatorias
y complementarias: un retry o job posterior puede usar otro `op_id`, pero no por
ello crear una segunda Tarea funcional equivalente para el mismo hecho. La
materialización concreta de la identidad del hecho fuente continúa pendiente
según la sección 17; no autoriza un ledger GOP paralelo. La frontera mínima es
atómica:

```text
mutación de negocio + historial funcional que corresponda
+ outbox distribuible + receipt durable
-> una Session / una transacción local / un commit exterior
```

Un fallo revierte todos esos efectos. El ledger es local, inmutable y no
sincronizable; no es historial, outbox, inbox ni auditoría.

## 23. Outbox, inbox y aplicación remota

Cada creación o modificación sincronizable del snapshot —contenido, asignación,
prioridad, fecha objetivo, estado, completar, cancelar y reabrir— debe registrar
su cambio distribuible en outbox en la misma transacción local. También debe
hacerlo la creación automática y una eventual baja lógica. Agregar comentario
registra su propio cambio distribuible en outbox en la misma transacción futura
que persista el comentario y complete el receipt idempotente, sin modificar el
snapshot de Tarea. No se congela schema ni payload de evento.

`REABIERTA` sigue siendo una marca del historial funcional conceptual, no un
estado y no un evento/outbox por sí misma. La reapertura cambia el snapshot a
`PENDIENTE` y ese cambio sí requiere propagación. Snapshot corriente, historial
funcional, outbox, inbox y ledger de idempotencia son estructuras y
responsabilidades distintas; no se presume que todo el historial viaje como una
única estructura.

La recepción remota pertenece al soporte Técnico y no es un command humano. Debe
registrar y consultar `op_id` mediante inbox o equivalente antes de comparar el
estado material. Encontrar el `op_id` no basta para aceptar un duplicado: primero
se compara el envelope o fingerprint entrante con la evidencia durable
disponible. La equivalencia comprende la semántica existente de identidad de
entidad/target, tipo de entidad/command, tipo de evento y versión cuando
correspondan, más payload material y su hash/fingerprint; no exige inventar
columnas ausentes.

Un `op_id` ya aplicado con envelope compatible es duplicado seguro o replay
equivalente y no vuelve a producir efectos. El mismo `op_id` con envelope
incompatible no es duplicado ni replay: siempre se clasifica y persiste como
conflicto, no genera efecto de negocio, conserva trazabilidad obligatoria y queda
sujeto al workflow transversal de resolución. `RECHAZADO` permanece disponible
para otras entradas inválidas o errores técnicos cuando lo disponga el contrato
transversal, pero no para reutilizar incompatiblemente un `op_id` ya aplicado.
Sólo para un `op_id` distinto se validan `uid_global`, `version_registro` y
payload material para decidir aplicación controlada, convergencia, obsolescencia
o conflicto. Nunca se inventa actor humano ni se usa Bearer humano como contrato
de réplica. Este freeze no crea un nuevo enum técnico, endpoint GOP de sync ni
formato ZIP/JSON alternativo.

## 24. Conflictos interinstalación

`Tarea` se clasifica con criticidad de sincronización **MEDIA**. Modifica trabajo
humano operativo/administrativo y conserva responsable, asignación, estado,
prioridad, fecha objetivo, completar/cancelar/reabrir, historial y posible origen
automático; una resolución genérica incorrecta puede perder o alterar trabajo
pendiente. No es criticidad BAJA porque una auto-resolución genérica destruiría
semántica funcional relevante. Tampoco es ALTA: Tarea no es por sí misma un
movimiento financiero, cobro, comprobante, tesorería, aplicación financiera ni
efecto económico irreversible.

Por CORE-EF, la criticidad MEDIA exige reglas explícitas. No existe auto-merge
genérico ni resolución automática campo por campo para Tarea. Toda divergencia
material que esas reglas no puedan resolver de forma segura debe persistirse
como conflicto y nunca sobrescribirse silenciosamente. Esta criticidad no cambia
la decisión de locks para ABM simples ni habilita LWW por timestamp.

La aplicación entrante sigue este orden conceptual. La clave primaria de
idempotencia es `op_id`, pero nunca funciona como bypass de la validación del
envelope durable:

1. Si el `op_id` ya fue aplicado, se compara el envelope/fingerprint durable:
   compatible significa `DUPLICADO` seguro o `REPLAY` equivalente, sin nuevo
   efecto; incompatible significa siempre `CONFLICTO` persistido y trazado, sin
   efecto de negocio y sujeto al workflow transversal de resolución, nunca
   duplicado, replay ni rechazado.
2. Sólo si el `op_id` es distinto se evalúan `uid_global`, `version_registro` y
   payload material. La operación distinta conserva su propia trazabilidad y no
   se convierte en replay aunque su resultado sea materialmente convergente.

Para un `op_id` distinto y el mismo `uid_global`, rige como mínimo esta matriz:

| Caso | Tratamiento congelado |
| --- | --- |
| Versión entrante mayor que la local | Candidata a aplicación controlada; validar continuidad, payload y referencias portables antes de persistir. Si la continuidad es válida pero una referencia portable requerida todavía no se resuelve, no aplicar parcialmente: conservar `op_id`, `event_id`, `consumer`, `uid_global`, `version_registro`, payload/fingerprint y trazabilidad, y retener la operación en `PENDING_DEPENDENCY` para el retry Técnico congelado; la mera ausencia temporal no es `REJECTED` ni `CONFLICTO`. Un gap o discontinuidad de `version_registro` impide la aplicación inmediata, pero es un problema transversal de continuidad distinto de una dependencia portable: su política técnica específica permanece pendiente fuera del alcance de #492, sin clasificarlo aquí como rechazo, conflicto, `PENDING_DEPENDENCY`, fetch, replay ni salto aceptado. |
| Misma versión y payload material igual | Operación distinta pero materialmente convergente; no se clasifica automáticamente como duplicado ni replay y se conserva la trazabilidad de ambas operaciones. |
| Misma versión y payload material distinto | Inconsistencia/conflicto material persistido; no sobrescribir. |
| Versión entrante menor que la local | Cambio atrasado u obsoleto; no retroceder ni sobrescribir el snapshot local y conservar trazabilidad. |

`op_id` identifica la operación cuya compatibilidad debe comprobarse; sólo un
envelope durable compatible permite clasificar duplicado/replay. Para operaciones
distintas, `uid_global` y `version_registro` gobiernan la comparación del estado
junto con el payload material.
`updated_at` y la instalación de origen sólo pueden ser criterios secundarios o
auxiliares: no se adopta LWW por timestamp. CORE-EF exige persistir la divergencia
no resoluble, pero no aporta una regla GOP segura de auto-merge; por ello no se
inventa resolución automática. Una resolución con impacto en datos requiere
trazabilidad y nuevo `op_id`. La validación concreta de referencias portables y
del payload deberá materializar el contrato de #492; la granularidad de
comentarios queda congelada por #493 y su forma física sigue pendiente.

## 25. Baja lógica y locks

`deleted_at != CANCELADA`. `CANCELADA` es un estado funcional terminal visible;
`deleted_at` representa una baja técnica. Si la futura operación técnica existe,
debe incrementar `version_registro`, registrar `op_id`, emitir baja lógica por
outbox en la misma transacción y aplicarse idempotentemente vía inbox. Este
incremento sólo congela su propagación eventual: no crea endpoint `DELETE`,
purga física, reactivación ni operación funcional MVP.

No hay evidencia para imponer en el MVP un lock lógico prolongado a los ABM
simples de Tarea. Se congela `lock lógico: NO APLICA por ahora`, porque optimistic
locking y transacción alcanzan para las mutaciones estudiadas; esto no usa
`version_registro` como sustituto universal de locks. Si un artefacto posterior
introduce edición prolongada, proceso crítico u operaciones incompatibles que
CORE-EF no pueda proteger con CAS, deberá justificar y diseñar lock persistido,
independiente del versionado y de la transacción SQL.


## 26. Consultas mínimas

El contrato debe prever: obtener tarea, listar tareas, **Mis tareas**, **Tareas
creadas por mí**, pendientes, vencidas y sin asignar. **Mis tareas** conserva
exclusivamente las tareas cuyo responsable registrado es el usuario y mantiene
elegibilidad vigente; **Tareas
creadas por mí** recupera separadamente aquellas cuyo creador humano es el
usuario, incluso cuando ya no sea responsable ni tenga alcance sobre su scope.
Las tareas `origen = SISTEMA` no pertenecen a esta última consulta porque no
tienen creador humano.

Filtros mínimos funcionales, cuando corresponda conceptualmente: creador,
responsable, estado, prioridad, sucursal, vencida y fecha objetivo.

Sus resultados se limitan por la política funcional de la sección 20.1; los
filtros nunca amplían visibilidad.

## 27. MVP funcional

El alcance funcional comprende:

- crear tarea manual;
- listar tareas y ver una tarea;
- consultar **Mis tareas** y, separadamente, **Tareas creadas por mí**;
- consultar pendientes, vencidas y sin asignar;
- modificar título/descripción;
- asignar, reasignar y desasignar;
- cambiar prioridad, fecha objetivo y estado;
- reabrir explícitamente una tarea completada según la sección 9.1;
- agregar comentario;
- consultar historial.

Las mutaciones se rigen por la matriz funcional de la sección 20.2 mientras el
ciclo de vida las permita. La terminalidad congela el snapshot salvo comentarios
y la reapertura explícita de `COMPLETADA`; el mecanismo técnico de autorización
permanece pendiente.

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
26. `id_sucursal` es opcional: `NULL` significa tarea global y un valor significa tarea de esa única sucursal; nunca representa procedencia técnica.
27. **Mis tareas** contiene sólo las tareas asignadas al usuario mientras su elegibilidad como responsable permanezca vigente; las creadas por él se consultan separadamente y continúan visibles por autoría.
28. La visibilidad se obtiene por creador, responsable vigente/elegible, capacidad de consulta o capacidad administrativa correspondiente; las mutaciones se rigen por ejecución como responsable elegible o capacidad administrativa del scope según la matriz de la sección 20.2.
29. La creación manual exige `puede_administrar` vigente sobre la sucursal propuesta o alcance global administrativo para una tarea global; el scope queda inmutable después de crear la Tarea durante el MVP.
30. La elegibilidad del responsable es continua y compuesta: exige `puede_operar` vigente sobre la sucursal o alcance global operativo, más autorización efectiva vigente suficiente; asignar o reasignar valida ambas dimensiones y perder cualquiera requiere gestión explícita, sin side effects automáticos.
31. `COMPLETADA` y `CANCELADA` congelan el snapshot funcional corriente; sólo admiten comentarios y, exclusivamente para `COMPLETADA`, la reapertura explícita ya definida.
32. Las capacidades por sucursal son habilitaciones necesarias, no autorización suficiente; toda operación humana protegida requiere además autorización efectiva de Administrativo.
33. La vigencia de `usuario_sucursal` exige usuario `ACTIVO` y sucursal `ACTIVA`, ambos sin `deleted_at` ni `fecha_baja`, y usa el intervalo `[fecha_desde, fecha_hasta)` normalizado a UTC de la sección 20.A, evaluado con un único `instante_corte_utc` del servidor.
34. Reabrir `COMPLETADA` conserva al responsable elegible o repara atómicamente al inelegible dejándolo nulo o reemplazándolo por otro elegible; nunca produce una tarea activa con responsable inelegible.
35. Creador, responsable elegible, capacidad de consulta y capacidad administrativa son bases alternativas de visibilidad sujetas a autorización efectiva; `puede_consultar` sólo se exige para visibilidad ordinaria por scope.
36. Las fronteras futuras exigen offset y normalización UTC; un timestamp legacy naïve no adquiere UTC retroactivamente y debe resolverse explícitamente antes de ser frontera autoritativa GOP.
37. `puede_administrar` vigente es una base independiente de visibilidad administrativa y no implica `puede_consultar`; para tareas globales aplica el alcance global administrativo equivalente.
38. Si una sucursal deja de estar vigente, no produce side effects sobre sus tareas: el responsable pierde elegibilidad local y el alcance global administrativo vigente, más autorización efectiva, preserva un camino residual de visibilidad y gestión sin cambiar el scope.
39. La habilitación administrativa aplicable es local para una sucursal vigente y global para una tarea global o una sucursal no vigente; todas requieren autorización efectiva y el fallback no es un bypass.
40. Toda consulta humana protegida de Tareas requiere Bearer y deriva su identidad exclusivamente de `AuthenticatedPrincipal.id_usuario`, nunca de `X-Usuario-Id` ni de contexto técnico.
41. Tarea es un concepto funcional sincronizable: toda mutación funcional compartida de la matriz es `COMMAND_WRITE_NEGOCIO + SINCRONIZABLE`, con independencia de actor humano u `origen = SISTEMA`; las consultas son `QUERY_READLIKE`.
42. Todo command sincronizable reutiliza `X-Op-Id`, contexto `X-Sucursal-Id`/`X-Instalacion-Id`, ledger durable transversal y outbox atómico; `If-Match-Version` aplica a mutaciones del snapshot de Tarea existente, no al append independiente de comentarios.
43. La aplicación remota usa inbox, `uid_global`, `version_registro` y `op_id`, persiste divergencias materiales y no adopta LWW por timestamps.
44. Un `op_id` ya aplicado sólo es duplicado seguro o replay si su envelope/fingerprint es materialmente compatible; una reutilización incompatible siempre es conflicto persistido y trazado, no genera efecto de negocio y queda sujeta al workflow transversal de resolución.
45. La generación automática combina obligatoriamente idempotencia técnica por `op_id` e idempotencia funcional por el mismo hecho fuente, cuya clave y materialización concretas permanecen pendientes.
46. `Tarea` tiene criticidad de sincronización MEDIA: sus conflictos se rigen por reglas explícitas, sin auto-merge genérico, y toda divergencia material no resoluble de forma segura se persiste como conflicto.
47. Agregar comentario es un append sincronizable independiente: no altera el snapshot ni `Tarea.version_registro`, no requiere `If-Match-Version` de Tarea, admite concurrencia entre comentarios y conserva terminalidad; usa `op_id`, outbox atómico, `Comentario.uid_global` propio, `version_registro` propio desde 1 y autoría portable conceptual.

## 29.1 Coherencia conjunta del primer cierre

- DATE y vencimiento usan la misma granularidad: el día objetivo completo sigue
  vigente y sólo una fecha estrictamente anterior al corte local queda vencida.
- `COMPLETADA` y `CANCELADA` quedan excluidas de vencimiento; la reapertura a
  `PENDIENTE` vuelve a habilitar su derivación sin persistir `VENCIDA`.
- Una baja técnica excluye la tarea de lecturas ordinarias, mientras una
  cancelación permanece como hecho funcional visible.
- La prioridad no altera vencimiento, estado, autorización ni SLA.
- Ninguna de estas decisiones traslada tareas a `operativo` ni materializa una
  entidad técnica. La sincronización general está resuelta documentalmente por
  #491; la identidad portable queda congelada conceptualmente por #492 y siguen
  pendientes su materialización técnica y los permisos; #493 congela el
  versionado y la concurrencia conceptual de comentarios sin crear runtime.
- El scope de sucursal/global limita consultas y gestión por alcance sin usar
  `id_instalacion_origen`; creador y responsable siguen siendo relaciones
  distintas.

## 30. Identidad canónica interinstalación y referencias portables (#492)

### 30.1 Alcance, clasificación y regla canónica

Este incremento completa documentalmente el blocker interno **#10**. La política
retryable transversal queda congelada por Técnico en `SRV-TEC-002`; su
materialización runtime permanece pendiente y no pertenece a GOP. `Tarea` sigue
siendo núcleo de
`gestion_operativa`; las identidades de usuario provistas
por Administrativo y la resolución distribuida provista por Técnico son soporte
transversal. `sucursal` e `instalacion` siguen bajo ownership de `operativo`:
referenciarlas no transfiere su semántica a GOP.

La regla canónica queda congelada sin diseñar almacenamiento ni transporte:

```text
id_tarea local
-> identidad técnica de la materialización local, joins y FKs

uid_global de Tarea
-> identidad canónica distribuida, global, única, inmutable y no reutilizable
-> identidad del payload sync, comparación remota y conflictos
```

Dos materializaciones compatibles con el mismo `uid_global` representan la
misma Tarea distribuida aunque sus IDs locales difieran. Dos Tareas distintas no
pueden compartirlo. Igual `uid_global` con contenido incompatible se trata según
las reglas de idempotencia, versión y conflicto de las secciones 23 y 24; nunca
autoriza sobrescritura silenciosa. El formato SQL de `uid_global` y la elección
UUID v4/v7 continúan pendientes de CORE-EF.

Se mantienen cinco dimensiones irreemplazables:

```text
uid_global de Tarea              -> identidad distribuida de la entidad
op_id                            -> identidad global de la operación
identidad portable de usuario    -> actor o referente humano
identidad portable de sucursal   -> scope funcional referenciado
identidad portable de instalación-> procedencia/contexto técnico
```

`AuthenticatedPrincipal.id_usuario` es identidad humana local, no identidad de
réplica. `id_instalacion_origen` es procedencia técnica, no scope. Ninguna de
estas dimensiones sustituye ni se deriva de otra.

### 30.2 Matriz conceptual de identidades

| Concepto | Identidad local al materializar | Identidad portable/remota | Uso | Prohibición |
| --- | --- | --- | --- | --- |
| Tarea | futuro `id_tarea` técnico | `uid_global` de Tarea | identidad distribuida y comparación remota | no transportar ni comparar la PK local como autoridad |
| Creador humano | `id_usuario_creador`, derivado localmente de `AuthenticatedPrincipal.id_usuario` | identidad global administrativa de usuario — **CONTRATO REQUERIDO / PENDIENTE DE MATERIALIZACIÓN** | autoría humana de `origen = USUARIO` | no transportar `id_usuario` local ni inventar UID/usuario técnico |
| Responsable | `id_usuario_responsable` local, opcional | identidad global administrativa de usuario — **CONTRATO REQUERIDO / PENDIENTE DE MATERIALIZACIÓN** | asignación portable | no transportar PK local ni confundir resolución con elegibilidad/autorización |
| Sucursal funcional | `id_sucursal` local, opcional e inmutable en MVP | `sucursal.uid_global`, existente en SQL real | scope global o de una sucursal | no transportar `id_sucursal` local; no confundir con `X-Sucursal-Id` |
| Instalación de origen | `id_instalacion_origen` local | `instalacion.uid_global`, existente en SQL real | procedencia técnica del alta | no usar PK remota, código de deployment ni instalación como scope |
| Instalación de última modificación | `id_instalacion_ultima_modificacion` local | `instalacion.uid_global`, existente en SQL real | procedencia técnica del último cambio | no reemplaza `op_id`, versión ni scope |
| Actor humano de historial | futuro ID local de usuario, si el diseño lo materializa | misma identidad global administrativa requerida para usuario | atribución funcional portable | historial no es outbox ni inbox; no diseñar columna aquí |
| Autor humano de comentario | futuro ID local de usuario, si el diseño lo materializa | misma identidad global administrativa requerida para usuario | autoría portable, únicamente | no confundir autor con `Comentario.uid_global` |
| Generador de sistema | sin usuario creador; código funcional estable | el mismo código funcional estable que defina el futuro catálogo/contrato — **PENDIENTE DE MATERIALIZACIÓN** | identificar el proceso funcional generador | no es usuario, `op_id`, hecho fuente ni UID de Tarea |

La evidencia física distingue los casos: `sucursal` e `instalacion` ya poseen
`uid_global` con unicidad en el SQL real y CORE-EF las declara sincronizables.
En cambio, la tabla real `usuario` posee PK local y metadata de versión,
procedencia y operaciones, pero **no posee `uid_global`**. Aunque la matriz
normativa general de CORE-EF clasifica `usuario` como sincronizable con UID, esa
identidad todavía no está materializada ni expuesta por el runtime auditado.
Por ello GOP requiere que Administrativo formalice y materialice una identidad
global canónica de usuario antes del DER/SQL/API de Tarea; este freeze no inventa
una columna, un alias por `login`/email/código ni un mapping GOP.

Para instalación, la identidad distribuida es `instalacion.uid_global`. El
`LOCAL_INSTALLATION_CODE` y `codigo_instalacion` sirven para resolver de forma
default-deny la instalación local en su contexto documentado; no sustituyen el
UID dentro de información distribuida. Para sucursal, la referencia portable es
`sucursal.uid_global`; `codigo_sucursal` tampoco se eleva aquí a identidad de
réplica.

### 30.3 Creador, responsable, historial y comentarios

En una creación humana, Bearer se resuelve localmente a
`AuthenticatedPrincipal.id_usuario` y ese ID se persiste como referencia local.
Al distribuir la Tarea, el creador se expresa con la identidad global
administrativa requerida y el destino la resuelve a su propio `id_usuario`. El
mismo principio aplica al responsable inicial y a toda asignación o reasignación:
el cambio identifica al nuevo referente de forma portable; una desasignación
expresa ausencia, no un ID mágico. Las reglas de elegibilidad congeladas siguen
vigentes y no se reinterpretan en #492.

El actor humano de historial y el autor humano de comentario, si esos hechos
viajan, usan conceptualmente la misma identidad portable administrativa. Esto
sólo congela autoría portable. `historial != outbox`, `historial != inbox` y
ninguno reemplaza el snapshot. #493 congela que comentar no incrementa
`Tarea.version_registro`, no usa `If-Match-Version` de Tarea, requiere identidad
portable propia conceptual y comparte transacción con outbox/receipt; la forma
física permanece pendiente.

Resolver una identidad portable **no autoriza** al usuario. En destino, la
autorización efectiva y la vigencia de sus habilitaciones siguen perteneciendo
a Administrativo y a las reglas funcionales ya congeladas. La recepción técnica
no inventa permisos GOP ni reejecuta un command humano como si el receptor fuera
el actor original.

### 30.4 Sucursal funcional e instalaciones técnicas

`Tarea.id_sucursal` sigue representando exclusivamente scope funcional: `NULL`
para tarea global o una FK local para una única sucursal. En sync, ese referente
viaja por `sucursal.uid_global` y el destino resuelve su propia PK. El header
`X-Sucursal-Id` continúa siendo contexto técnico/contractual del command local;
no se copia al campo, no prueba el scope y no es la identidad remota de sucursal.

`id_instalacion_origen` e `id_instalacion_ultima_modificacion` son FKs técnicas
locales al materializarse. La procedencia distribuida correspondiente usa
`instalacion.uid_global` y se resuelve localmente en destino. Ni
`X-Instalacion-Id`, ni una instalación origen, ni una instalación de última
modificación convierten una Tarea en local o de sucursal:

```text
id_instalacion_origen != scope_funcional_tarea
id_instalacion_ultima_modificacion != scope_funcional_tarea
```

### 30.5 Payload conceptual y resolución en destino

Sin congelar JSON, DTO, evento ni nombres de campos físicos, la operación
distribuida debe contener las identidades portables necesarias:

```text
payload remoto
-> identifica Tarea por uid_global
-> identifica creador/responsable/actor por identidad administrativa portable
-> identifica sucursal e instalaciones por sus uid_global
-> destino resuelve cada referencia a su ID local
-> sólo entonces persiste relaciones locales válidas
```

Pueden viajar como autoridad conceptual: `uid_global` de Tarea,
`sucursal.uid_global`, `instalacion.uid_global`, la futura identidad global
administrativa de usuario, `op_id`, `version_registro` y el código funcional
estable de `generador_sistema` cuando su contrato posterior lo catalogue. El
hecho fuente de una generación automática conserva su propia identidad
funcional para deduplicación y no reemplaza el `uid_global` de Tarea.

No son autoridad remota y no deben usarse para resolver referencias:

```text
id_tarea
id_usuario / id_usuario_creador / id_usuario_responsable
id_sucursal
id_instalacion / id_instalacion_origen / id_instalacion_ultima_modificacion
cualquier otra PK local
X-Sucursal-Id / X-Instalacion-Id
```

Una implementación puede conservar IDs locales dentro de su base, ledger o
proyección después de una resolución válida; no puede persistir la PK recibida
del emisor como si fuera propia ni crear tablas de mapeo manual ad hoc en GOP.

### 30.6 Referencias todavía no resolubles y dependencias de sync

GOP sólo declara la necesidad funcional: si una referencia portable válida y
requerida todavía no se resuelve localmente, no se aplica la Tarea parcial ni se
crean placeholders o mappings. Técnico/sync es dueño de retención, estado, retry
y reproceso. `SRV-TEC-002` congela transversalmente el estado lógico
`PENDING_DEPENDENCY`, no terminal y retryable:

```text
referencia requerida temporalmente no resoluble
-> rollback de todo efecto funcional
-> mismo registro/evento queda PENDING_DEPENDENCY
-> conserva op_id, event_id, consumer, uid_global, version_registro,
   payload/huella, procedencia, motivo e historial de intentos
-> worker/job técnico lo reclama atómicamente al vencer su elegibilidad
   o por habilitación manual
-> PROCESSING
   -> PROCESSED si todas las referencias se resuelven y aplica atómicamente
   -> PENDING_DEPENDENCY si la ausencia continúa
   -> REJECTED sólo ante invalidez o imposibilidad permanente
   -> CONFLICTO sólo ante divergencia material
```

Una referencia opcional explícitamente ausente no es una dependencia. Para
creador humano, sucursal presente, instalación requerida o responsable presente,
la identidad portable debe resolverse antes de persistir. El retry reutiliza el
mismo registro y no genera otro `op_id`; `(event_id, consumer)` deduplica la
recepción y `op_id` más huella preservan identidad/contenido. Claim atómico,
lease/reclaim de ejecución vencida y una única transacción controlan cada fila.
Antes del efecto, el aplicador debe además adquirir atómicamente
`inbox_operation_scope`, autoridad única del scope lógico `(consumer, op_id)`:
`op_id` conserva la identidad primaria
de la operación, mientras `event_id` sólo identifica la entrega y dos entregas con
distinto `event_id` pueden representar la misma operación. Con envelope
compatible, sólo una aplica y las demás reutilizan el resultado durable; con
envelope incompatible, se persiste `CONFLICTO` sin segunda aplicación. No existe
elección de leader por delivery: cada adquisición concreta usa un `attempt_id`
único y `worker_id` queda sólo como diagnóstico. Esta
garantía puede reutilizar directamente #469/#470 sólo si un único aplicador es
dueño del efecto completo del `op_id`. Si el flujo futuro define múltiples
consumers con efectos independientes, Técnico debe proveer idempotencia
consumer-scoped: el receipt global #469/#470 no basta para cada consumer y el
primero no debe bloquear ilegítimamente al segundo. Este freeze no decide esa
topología ni crea `UNIQUE(consumer, op_id)` o ledger GOP paralelo. Lease de fila
e idempotencia del efecto del consumer son controles complementarios.

La agenda puede ser automática y manual. Backoff creciente acotado y contador de
intentos evitan loops; agotar el límite operativo pausa sólo el retry automático
y deja revisión manual sin perder payload ni convertir la espera en terminal. No
se congela cron, intervalo ni máximo numérico.

**Estado histórico previo a #511:** el runtime entonces auditado todavía no
implementaba esta política: `InboxRepository.claim()` sólo insertaba
`PROCESSING` con `ON CONFLICT (event_id, consumer) DO NOTHING`, no reclamaba
filas existentes, y `mark_as_rejected()` conservaba `REJECTED` terminal/no
retryable. La tabla tampoco materializaba payload, `op_id`, huella, intentos,
lease o elegibilidad. Por ello el freeze requería un incremento Técnico
transversal de SQL/repository/worker/tests antes de ser capacidad runtime.

**Estado vigente desde #511:** Técnico/Sync materializa transversalmente
`PENDING_DEPENDENCY`, retención de envelope y procedencia, fingerprint canónico,
intentos, elegibilidad, claim/reclaim con `attempt_id`, backoff, entry point
automático reusable, reproceso manual/controlado, exclusión consumer-scoped por
operation scope y atomicidad con savepoint, manteniendo `REJECTED` terminal. La
expiración habilita takeover; el takeover exitoso avanza el fence e invalida al
attempt anterior. Esta infraestructura no pertenece a
GOP, no implementa Tarea y no implica que futuros consumers GOP estén
integrados. #511 tampoco incorpora un scheduler/daemon productivo definitivo.

Las alternativas se evaluaron contra ese runtime: conservar `PROCESSING` se
descarta porque confunde ejecución activa con espera y carece de lease; reingestar
se descarta porque colisiona con `(event_id, consumer)` y fragmenta identidad;
una cola separada se descarta porque duplica lifecycle e idempotencia sin patrón
existente. El estado explícito es la extensión mínima, transversal e incremental
que no cambia `REJECTED` ni rompe consumidores actuales mientras no opten por él.

### 30.7 Origen SISTEMA y conflictos de identidad

Para `origen = SISTEMA`, `id_usuario_creador = NULL` en toda instalación y
`generador_sistema` es obligatorio. Debe ser un código funcional estable y
portable definido por el contrato futuro del generador; no se inventa aquí un
catálogo físico. No es identidad humana, `op_id`, identidad del hecho fuente ni
identidad de la Tarea. No se crea usuario global `SYSTEM`.

El mismo `uid_global` conserva una única identidad distribuida de Tarea. Su
evolución remota se evalúa exclusivamente conforme a la matriz de la sección 24:
una versión entrante mayor es candidata a aplicación controlada, previa
validación de continuidad, payload y referencias portables; la misma versión con
payload material igual es una operación distinta materialmente convergente, no
conflicto, replay ni duplicado automático; la misma versión con payload material
distinto constituye conflicto material persistido y no se sobrescribe; y una
versión menor es atrasada u obsoleta, no retrocede ni sobrescribe el snapshot
local y conserva trazabilidad. Una falla de continuidad sólo deriva en conflicto
cuando además existe divergencia material que las reglas explícitas no pueden
resolver de forma segura. Nunca se crea una segunda Tarea con el mismo
`uid_global`, se reasigna el UID ni se adopta la PK local del emisor.

### 30.8 Evidencia, inferencia, decisión y efecto posterior

- **Repositorio / arquitectura:** DEV-ARCH General preserva ownership aunque un
  dominio referencie a otro; DEV-ARCH Administrativo mantiene `usuario` y
  autorización; DEV-ARCH Operativo mantiene `sucursal` e `instalacion`.
- **Especificación formal:** CORE-EF REQ-SYNC-002/003/004/007/008/009 exige ID
  local para joins y `uid_global` inmutable/no reutilizable para toda comparación
  distribuida; REQ-SYNC-067/071/072 exige trazabilidad de recepción, rechazo y
  conflicto. SRV-TEC mantiene inbox, aplicación idempotente y conflicto como
  soporte técnico separado del negocio.
- **Implementación real previa a #511:** SQL confirmaba UID en `sucursal` e `instalacion`, pero
  no en `usuario`; outbox real ya demuestra el patrón portable con
  `uid_instalacion_origen` y datos por `uid_global`. El worker/inbox entonces
  auditado era acotado a eventos allowlisted y no implementaba Tarea ni una espera genérica de
  referencias. `InboxRepository.mark_as_rejected` marca `REJECTED` no retryable
  y `claim` no reabre el mismo `(event_id, consumer)`. #469/#470 resuelven ledger
  local de operación, no identidad de entidades o usuarios. Ese diagnóstico del
  inbox quedó superado por la infraestructura transversal #511; Tarea continúa
  no implementada.
- **Inferencia:** toda FK funcional incluida en un estado replicado debe
  resolverse por identidad portable antes de persistirse; de otro modo una PK
  válida en el emisor podría apuntar a otra entidad en destino.
- **Decisión nueva #492:** Tarea viaja por su `uid_global`; sucursal e instalación
  por sus UID físicos; referencias humanas por un contrato global Administrativo
  requerido y aún no materializado; las dependencias irresolubles no se aplican
  silenciosa ni parcialmente y quedan trazadas mediante la política transversal
  `PENDING_DEPENDENCY` congelada por Técnico.
- **Alternativas descartadas:** PK remota, `login`, email, código de usuario,
  `codigo_sucursal`, `codigo_instalacion`, headers CORE-EF, placeholders y mappings
  GOP se descartan como identidad autoritativa. También se descarta resolver
  identidad como si concediera autorización.
- **Impacto posterior definido en #492:** antes de DER/SQL/API GOP, Administrativo debía cerrar la
  identidad global de usuario y Técnico/Operativo deben exponer resolución
  verificable de referencias. La materialización Técnica de retención/reproceso
  quedó resuelta por #511 sin reutilizar `REJECTED` ni forzar `CONFLICTO` sin
  divergencia; la integración de consumers futuros continúa pendiente.
  DEV-ARCH/DER/DEV-SRV/DEV-API GOP definirán física, DTO y
  transacción sin alterar este contrato. No se crean esos artefactos aquí.

## 31. Estado de blockers y criterio de #492

De la numeración original, quedan cerrados documentalmente **#1, #2, #3, #4,
#5, #6, #7, #8, #9, #10 y #11**. #491 resolvió la estrategia de sync y la política
Técnica de la sección 30.6 resuelve el último subpendiente de identidad canónica
interinstalación. El blocker #7 queda resuelto por la sección 32 / #493:
comentario append-only independiente, sin CAS ni incremento de versión de Tarea.
La replicación administrativa de identidad humana, los resolvers de referencias
y la integración de futuros consumers siguen como prerequisitos técnicos del
diseño físico GOP; el runtime transversal de `PENDING_DEPENDENCY` ya fue
materializado por #511 y no reabre el blocker documental #10. La
autenticación técnica para commands `origen = SISTEMA` continúa **NO CONGELADA**
y deberá resolverse antes de exponer runtime automático.

Criterio documental de #492:

- [x] Identidad canónica de Tarea congelada.
- [x] Referencias interinstalación relevantes definidas.
- [x] PK local y `uid_global` diferenciados.
- [x] Procedencia técnica y scope funcional diferenciados.
- [x] Interacción general con sync definida.
- [x] Política retryable para referencias no resolubles definida.
- [x] GOP-FREEZE-001 y PROJECT-STATUS alineados.
- [x] Sin DER, SQL, API, runtime ni tests GOP prematuros.

Por lo tanto, el blocker interno #10 queda **documentalmente resuelto** y #492
queda **documentalmente listo para cierre después del merge**. Este incremento no
cierra #492, #493 ni la épica #489 y no declara implementado el runtime Técnico.

## 32. Versionado y concurrencia de comentarios (#493)

### 32.1 Decisión sobre snapshot, versión e identidad

Este incremento resuelve documentalmente el blocker interno **#7** sin crear
entidad técnica, tabla, endpoint, DTO ni evento. Se congela:

```text
agregar comentario
-> append funcional independiente
-> NO modifica el snapshot funcional mutable de Tarea
-> NO incrementa Tarea.version_registro
-> NO requiere If-Match-Version de Tarea
```

`Tarea.version_registro` versiona exclusivamente su snapshot funcional mutable:
estado, responsable, prioridad, fechas, título, descripción, scope y baja lógica
cuando ésta exista. No versiona la colección append-only de comentarios. Agregar
un comentario tampoco cambia por sí mismo `estado`, responsable, prioridad,
`fecha_objetivo`, `fecha_finalizacion`, scope ni `deleted_at`.

Como pieza sincronizable independiente, el comentario debe conservar su propio
`version_registro` conforme a CORE-EF REQ-SYNC-011/012/013. Su alta nace
conceptualmente con `version_registro = 1`; como en el MVP no se edita ni se
borra funcionalmente y una corrección se expresa con otro append, normalmente
permanece en 1. Esto no es una excepción al versionado CORE-EF ni crea una
operación posterior sobre el comentario.

El comentario requiere además `uid_global` propio, único, inmutable y no
reutilizable como identidad canónica distribuida, conforme a CORE-EF
REQ-SYNC-004..009. Las dimensiones quedan separadas:

```text
Tarea.uid_global                    -> identidad distribuida de la Tarea padre
Tarea.version_registro              -> versión de su snapshot funcional mutable
Comentario.uid_global               -> identidad distribuida propia del comentario
Comentario.version_registro         -> versión CORE-EF propia; inicia en 1
op_id                               -> identidad de la operación distribuida
event_id                            -> identidad/correlación de entrega
```

Ninguna sustituye a otra. No se congela PK, columna, UUID v4/v7, FK, tabla,
payload ni exposición física del comentario.

### 32.2 Concurrencia y estados

- **Comentario/comentario:** dos comentarios concurrentes válidos pueden
  coexistir y no se rechazan sólo por simultaneidad. No compiten por
  `Tarea.version_registro`. Por ejemplo, `Comentario A.uid_global = A` y
  `Comentario B.uid_global = B` pueden nacer ambos con versión propia 1 mientras
  `Tarea.version_registro = 8`, sin producir `Tarea 8 -> 9 -> 10`. El orden
  físico o total definitivo no se congela.
- **Comentario/mutación del snapshot:** la edición conserva su CAS y debe usar la
  versión esperada de Tarea. El comentario es otra operación; un cambio
  concurrente de `Tarea.version_registro` no lo vuelve conflicto optimista. La
  autorización funcional se valida en origen, no se reevalúa en recepción contra
  relaciones mutables posteriores.
- **Comentario/transición terminal:** `PENDIENTE`, `EN_CURSO`, `COMPLETADA` y
  `CANCELADA` admiten comentarios con autorización válida. En `COMPLETADA` el
  comentario nace con su versión propia, no reabre, no cambia estado ni
  `fecha_finalizacion`. En `CANCELADA` también nace con su versión propia, no
  reabre ni cambia estado. Sólo la operación explícita ya congelada puede
  reabrir `COMPLETADA`; `CANCELADA` continúa sin reapertura.
- **Baja lógica:** `CANCELADA != deleted_at`. Un comentario válido, autorizado y
  confirmado en origen **causalmente antes** de la baja lógica sigue siendo un
  hecho válido y debe converger aunque el receptor reciba primero la baja. Puede
  materializarse sobre la Tarea ya dada de baja, pero sólo conserva el append: no
  restaura la Tarea, no limpia `deleted_at`, no reabre ni cambia estado,
  responsable, prioridad, `fecha_objetivo`, `fecha_finalizacion`, scope o
  `Tarea.version_registro`.
- Una Tarea con `deleted_at != NULL` conserva un `uid_global` resoluble; por ese
  solo hecho no falta una referencia portable y `PENDING_DEPENDENCY` **NO
  APLICA** automáticamente. En cambio, un intento originado **causalmente
  después** de una baja ya efectiva no queda validado por la regla anterior y no
  es una mutación GOP ordinaria válida. La auditoría de CORE-EF/Técnico no halló
  clasificación terminal específica para ese caso; queda para el contrato
  transversal posterior, sin inventar `PENDIENTE`, `PENDING_DEPENDENCY`,
  `CONFLICTO` ni `REJECTED` en #493.
- **Comentario/baja realmente concurrentes:** si ambas operaciones fueron
  válidas en sus respectivos orígenes, tienen `op_id` distintos y ninguna
  observa causalmente a la otra, se conservan ambos hechos. El resultado
  convergente es `Tarea.deleted_at != NULL` más el comentario presente y asociado
  a la misma Tarea. El comentario no restaura ni muta el snapshot de Tarea; la
  baja tampoco elimina el comentario ni modifica
  `Comentario.version_registro`.

### 32.3 Sync, idempotencia, autoría y transacción

Agregar comentario permanece `COMMAND_WRITE_NEGOCIO + SINCRONIZABLE`. Exige el
helper y los headers CORE-EF sync, incluido `X-Op-Id`, pero no
`If-Match-Version` de Tarea. La futura persistencia del comentario, su outbox
distribuible y el receipt durable comparten una única transacción local y commit exterior.
Un error previo al commit revierte todos esos efectos y permite retry según el
contrato transversal.

La idempotencia se aplica a la operación independiente, nunca a la versión de
Tarea ni a la versión propia del comentario:

- mismo `op_id` + envelope materialmente compatible: replay/duplicado seguro,
  sin crear un segundo comentario ni un segundo outbox;
- mismo `op_id` + envelope incompatible: `CONFLICTO`, sin segundo comentario;
- `event_id` identifica la entrega y no sustituye `op_id`, que identifica la
  operación distribuida.

La aplicación remota combina `Comentario.uid_global` y `version_registro`
propios, `op_id` y `Tarea.uid_global` para aplicar, comparar, reproducir o
registrar conflicto conforme a CORE-EF y #491/#492. No se congela el payload ni
la estructura de evento. `Comentario.version_registro`
sirve al contrato de entidad sincronizable y comparación remota; no sustituye
`op_id` para la idempotencia del alta.

No se inventa un `If-Match-Version` propio del comentario: no existe una
modificación lógica posterior en el MVP append-only. Si en el futuro se habilita
edición o borrado lógico, su concurrencia propia deberá evaluarse conforme a
CORE-EF, fuera de #493.

#### Autorización en origen y aplicación remota

En origen, la operación humana valida identidad mediante
`AuthenticatedPrincipal`, autorización efectiva, elegibilidad o relación
funcional, scope, vigencia, estado y posibilidad de comentar en el instante de
la operación. Si se acepta y confirma junto con outbox, constituye un hecho
funcional válido.

El receptor remoto no reevalúa esa autorización histórica contra relaciones
mutables actuales. En particular, no rechaza el comentario sólo porque después
cambió el responsable, una capacidad por sucursal, la autorización efectiva o
alguna otra relación que hubiera habilitado la operación en origen. Sí valida
`Comentario.uid_global`, `Tarea.uid_global`, resolución de referencias,
integridad estructural, `op_id`, envelope/fingerprint, idempotencia,
`Comentario.version_registro`, conflictos materiales y reglas técnicas de sync.

Caso explícito: un comentario confirmado cuando el responsable era A sigue
siendo válido y debe converger aunque una reasignación posterior a B llegue antes
al receptor; `responsable actual != autor` no basta para rechazarlo. Del mismo
modo, una transición a `COMPLETADA` o `CANCELADA` recibida primero no invalida el
comentario, porque ambos estados admiten comentarios; el append no reabre ni
cambia el estado.

#### Causalidad con la Tarea padre

El comentario conserva relación causal con el snapshot/contexto de Tarea sobre
el cual fue autorizado en origen. Su futura representación sincronizada debe
conservar contexto causal suficiente para que Técnico respete RN-TEC-012:
ordenar, diferir o aplicar correctamente mensajes dependientes y evitar rechazos
debidos sólo a entrega fuera de orden. Como mínimo debe permitir distinguir un
comentario confirmado antes de la baja lógica de un intento originado después de
que la baja ya era efectiva, y diferenciar ambos casos de operaciones realmente
concurrentes sin relación causal.

| Relación comentario / baja | Tratamiento |
| --- | --- |
| Comentario causalmente anterior a baja | Conservar comentario y aplicar baja; resultado: `Tarea.deleted_at != NULL` + comentario presente. |
| Baja causalmente anterior a comentario | El intento posterior no es una mutación GOP ordinaria válida; la clasificación terminal exacta queda fuera de #493 sin inventarla. |
| Comentario y baja concurrentes | Conservar ambos efectos; resultado: `Tarea.deleted_at != NULL` + comentario presente. |

Para el primer caso, el receptor valida `Comentario.uid_global`,
`Comentario.version_registro`, `Tarea.uid_global`, integridad del payload,
`op_id`, envelope/fingerprint, idempotencia, causalidad y conflictos materiales
reales, pero no rechaza el hecho sólo porque encuentra `Tarea.deleted_at !=
NULL`. La baja lógica no invalida retroactivamente un comentario confirmado con
anterioridad ni convierte otra operación en duplicado.

Para el caso concurrente, un receptor que recibe `comentario -> baja` y otro que
recibe `baja -> comentario` deben alcanzar el mismo resultado. No se impone orden
total por timestamp, `updated_at`, `event_id`, instalación, UUID o llegada a
inbox; no se adopta LWW ni “gana” una operación. Tampoco se clasifica
automáticamente como `CONFLICTO` o `PENDING_DEPENDENCY`: son dos operaciones
compatibles con `op_id` distintos y trazabilidad propia. Esta preservación de
ambos efectos es una regla explícita para esta combinación, no auto-merge
genérico ni cambio de la criticidad MEDIA de Tarea.

Esta garantía no es CAS de `Tarea.version_registro` ni vuelve a exigir
`If-Match-Version` de Tarea. Tampoco congela una columna o marcador físico como
`tarea_version_origen`, `parent_version`, `causal_version` o `depends_on_op_id`;
esa representación corresponde a DEV-ARCH/DER/DEV-SRV/DEV-API posteriores.

El autor humano procede de Bearer → `AuthenticatedPrincipal` y viaja mediante el
contrato portable Administrativo requerido por #492. No se usa login, email,
PK remota, `X-Usuario-Id` ni un usuario `SYSTEM` ficticio. La autoría portable no
sustituye la autorización funcional evaluada en origen.

Comentario, historial funcional y auditoría administrativa permanecen conceptos
distintos. El comentario es texto funcional append-only; el historial es el
registro estructurado de cambios funcionales; la auditoría pertenece a
Administrativo. Ninguno sustituye al otro, a outbox, inbox o ledger.

### 32.4 Pendientes físicos y criterio de cierre

Quedan para DEV-ARCH-GOP y artefactos posteriores —después de satisfacer las
dependencias administrativas/técnicas— la entidad/agregado físico, PK e identidad
portable concreta del comentario, persistencia, constraints, relación, orden,
payload/evento, endpoint, DTO, autorización materializada, transacción y tests.
No se inventan aquí SQL, IDs de CU, API ni runtime.

Criterio documental de #493:

- [x] Efecto sobre `Tarea.version_registro` congelado.
- [x] `version_registro` propio del comentario alineado con CORE-EF y alta en 1.
- [x] `Comentario.uid_global` propio alineado con CORE-EF REQ-SYNC-004..009.
- [x] No requerimiento de `If-Match-Version` de Tarea definido.
- [x] Concurrencia comentario/comentario y comentario/mutación definida.
- [x] Autorización en origen y no reevaluación remota posterior definidas.
- [x] Causalidad y orden lógico alineados con RN-TEC-012 sin marcador físico.
- [x] Comentario anterior a baja lógica converge sin restaurar Tarea; caso
  posterior diferenciado sin inventar clasificación técnica.
- [x] Comentario y baja concurrentes conservan ambos efectos sin LWW, conflicto
  automático ni orden total artificial.
- [x] Sync e idempotencia identificados sin confundir `op_id` y `event_id`.
- [x] Comportamiento en estados terminales preservado.
- [x] `deleted_at` no confundido con `CANCELADA` ni habilitado incidentalmente.
- [x] `GOP-FREEZE-001` y `PROJECT-STATUS.md` alineados.
- [x] Sin SQL/API/runtime GOP prematuros.

Por lo tanto, el blocker interno #7 queda **documentalmente resuelto** y #493
permanece abierto durante el PR, **listo para cierre después del merge**. La
épica #489 no se cierra: después del merge/cierre de #493 queda lista para
evaluar la siguiente etapa, condicionada aún por los pendientes físicos y las
dependencias administrativas/técnicas expresas.

## 33. Matriz final por operación

Los headers abreviados como **CORE-EF sync** significan `X-Op-Id +
X-Sucursal-Id + X-Instalacion-Id`; son contexto técnico y nunca identidad humana
ni scope funcional. No se definen nombres de endpoint.

| Operación | CORE-EF | Sync | Headers técnicos conceptuales | If-Match | Dependencia |
| --- | --- | --- | --- | --- | --- |
| Crear tarea manual | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync; Bearer separado para actor humano | No: no existe versión previa | Materializar contrato #492 |
| Crear tarea automática / `origen = SISTEMA` | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync; no se presume Bearer humano | No: no existe versión previa | Materializar #492; auth técnica no congelada |
| Modificar título | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar payload portable #492 |
| Modificar descripción | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar payload portable #492 |
| Asignar | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar identidad administrativa requerida |
| Reasignar | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar identidad administrativa requerida |
| Desasignar | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar contrato portable #492 |
| Cambiar prioridad | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Sin dependencia funcional adicional |
| Cambiar `fecha_objetivo` | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Sin dependencia funcional adicional |
| `PENDIENTE -> EN_CURSO` | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Sin dependencia funcional adicional |
| `EN_CURSO -> PENDIENTE` | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Sin dependencia funcional adicional |
| Completar | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar referencias #492 |
| Cancelar | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar referencias #492 |
| Reabrir `COMPLETADA -> PENDIENTE` | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | Sí | Materializar responsable portable #492 |
| Agregar comentario | `COMMAND_WRITE_NEGOCIO` | `SINCRONIZABLE` | CORE-EF sync | No: append independiente del snapshot | `Comentario.uid_global`, autor portable y versión propia desde 1; física pendiente |
| Eventual baja lógica técnica | `COMMAND_WRITE_TECNICO` | `SINCRONIZABLE` | CORE-EF sync | Sí, sobre Tarea existente | No crea operación; materializar payload #492 |
| Consultas humanas de Tarea | `QUERY_READLIKE` | `NO APLICA` | Headers write: `NO APLICA`; Bearer humano separado | No | Auth técnica de una eventual lectura sync queda separada |
