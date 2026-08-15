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

Un vínculo `usuario_sucursal` está vigente únicamente cuando, para un mismo
`instante_corte`, se cumplen simultáneamente:

```text
usuario_sucursal.deleted_at IS NULL
AND estado_vinculo = ACTIVO
AND fecha_desde <= instante_corte
AND (fecha_hasta IS NULL OR instante_corte < fecha_hasta)
AND usuario vigente/activo
AND sucursal vigente/activa
```

El intervalo es `[fecha_desde, fecha_hasta)`: inclusivo al inicio y exclusivo al
final. `instante_corte` se captura una sola vez por caso de uso desde el reloj
confiable del servidor en UTC; no procede del cliente, navegador, instalación ni
sucursal. El mecanismo de inyección del reloj se decidirá después.

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

Se reconocen cuatro relaciones funcionales independientes: creador, responsable
vigente/elegible, capacidad de consulta sobre la sucursal y alcance global de
consulta. Un usuario puede ver una tarea si cumple al menos una de estas
condiciones:

1. es su creador humano;
2. es su responsable actual y conserva elegibilidad vigente;
3. tiene `puede_consultar = true` vigente sobre la sucursal de una tarea de
   sucursal; o
4. tiene alcance global de consulta para una tarea global.

Por lo tanto:

- **Mis tareas** significa exclusivamente tareas cuyo responsable registrado es
  el usuario y cuya elegibilidad continúa vigente. No incluye tareas sólo por
  haberlas creado ni conserva una tarea por una asignación devenida inelegible.
- **Tareas creadas por mí** es una consulta separada. El creador conserva
  visibilidad después de una asignación, reasignación o desasignación, aunque no
  sea responsable ni tenga actualmente alcance sobre el scope de la tarea.
- Las tareas sin responsable son visibles para su creador humano y por capacidad
  de consulta del scope: `puede_consultar` vigente para su sucursal o alcance
  global de consulta para una tarea global.
- Una tarea asignada a otra persona es visible para su creador y por la capacidad
  de consulta correspondiente. `puede_consultar` no habilita gestión por scope.
- Una tarea de sucursal entra en listados por scope sólo con `puede_consultar =
  true` vigente sobre esa sucursal. Una tarea global entra por scope sólo con
  alcance global de consulta; no se replica como tarea de cada sucursal.
- La asignación individual mantiene la tarea en **Mis tareas** y visible para el
  responsable elegible según el scope, incluida una tarea global o de sucursal.

Las tareas `origen = SISTEMA` aplican las mismas reglas según responsable y
scope. Como no tienen creador humano, no obtienen visibilidad por autoría;
`generador_sistema` no es actor, usuario, rol ni alcance.

Toda consulta humana protegida requiere además autorización efectiva de
Administrativo; la capacidad de consulta es necesaria, no suficiente.

### 20.1.1 Elegibilidad del responsable

La elegibilidad del responsable es una invariante continua determinada por el
scope funcional de la tarea:

```text
Tarea de sucursal
→ sólo admite como responsable a un usuario con puede_operar = true vigente
  sobre esa sucursal
→ el responsable actual debe conservar esa capacidad

Tarea global
→ sólo admite como responsable a un usuario con alcance global operativo vigente
→ el responsable actual debe conservar esa capacidad
```

La misma regla se aplica a la primera asignación y a cada reasignación, incluidas
las tareas `origen = SISTEMA`. La persona que asigna o reasigna continúa
necesitando la relación de gestión por scope de la matriz; el usuario destino
debe ser elegible para ese mismo scope. `puede_administrar` habilita la gestión,
pero no sustituye el `puede_operar` requerido al destino. La asignación no
permite eludirlo ni usa `id_instalacion_origen` para decidir elegibilidad.

Una asignación con elegibilidad vigente habilita las capacidades funcionales del
responsable.
Después de una reasignación, el nuevo responsable debe cumplir la elegibilidad y
el anterior pierde las capacidades derivadas de esa relación; el creador conserva
su visibilidad y comentario. Una tarea sin responsable sigue siendo válida, pero
su primera asignación debe cumplir esta regla antes de que pueda pasar a
`EN_CURSO` o `COMPLETADA`.

Estas son reglas funcionales, no permisos, roles, claims, ACL ni scopes HTTP. La
forma en que Administrativo materialice el alcance global y resuelva la
autorización efectiva queda para los artefactos posteriores.

Si el responsable registrado pierde luego `puede_operar` sobre la sucursal o el
alcance global operativo, permanece registrado hasta una mutación explícita,
pero deja de estar habilitado por la relación de responsable para
`PENDIENTE ↔ EN_CURSO`, completar o comentar. Tampoco obtiene visibilidad por la
mera referencia persistida: sólo la conserva si otra relación la habilita, como
ser creador, `puede_consultar` vigente o alcance global de consulta.

No hay desasignación automática, cambio automático de estado, job correctivo ni
otro side effect silencioso desde Administrativo. Una persona con capacidad
administrativa vigente sobre el scope y autorización efectiva debe reasignar a
un destino elegible o desasignar explícitamente. En una tarea terminal, la
pérdida de elegibilidad no habilita una mutación ordinaria del snapshot.

Para tareas de sucursal, las capacidades existentes se consumen sin fusionarlas:

```text
puede_consultar vigente   → visibilidad por scope
puede_operar vigente      → elegibilidad continua como responsable
puede_administrar vigente → creación y gestión por scope
```

Para tareas globales se requieren, respectivamente, alcance global de consulta,
alcance global operativo y alcance global administrativo. Este freeze no asigna
esa semántica global a flags de `usuario_sucursal` ni inventa su representación
técnica; Administrativo deberá definirla en artefactos posteriores.

### 20.2 Decisión de mutación

Para el MVP se distinguen **ejecución del trabajo** y **gestión por scope**:

| Acción | Creador humano | Responsable vigente/elegible | Habilitación administrativa vigente sobre el scope |
| --- | --- | --- | --- |
| Modificar título o descripción | No | No | Sí |
| Asignar, reasignar o desasignar | No | No | Sí |
| Cambiar prioridad o fecha objetivo | No | No | Sí |
| Cambiar `PENDIENTE ↔ EN_CURSO` | No | Sí | Sí |
| Completar | No | Sí | Sí, sólo si existe responsable |
| Cancelar | No | No | Sí |
| Reabrir `COMPLETADA → PENDIENTE` | No | No | Sí |
| Comentar | Sí | Sí | Sí |

Para la columna de gestión, una tarea de sucursal exige `puede_administrar =
true` vigente sobre esa sucursal y una tarea global exige alcance global
administrativo. `puede_consultar` por sí solo nunca habilita estas acciones. La
matriz sólo aplica cuando la operación es funcionalmente válida según el ciclo de
vida; una relación marcada `Sí` no permite eludir la elegibilidad del responsable
ni la terminalidad. Cada `Sí` expresa una habilitación funcional y toda operación
humana protegida requiere además autorización efectiva de Administrativo.

Mientras `estado IN (COMPLETADA, CANCELADA)`, el snapshot funcional corriente es
inmutable: no pueden modificarse título, descripción, responsable, prioridad ni
`fecha_objetivo`; tampoco se permite asignar, reasignar, desasignar, ejecutar
`PENDIENTE ↔ EN_CURSO`, completar nuevamente ni cancelar nuevamente.
`id_sucursal` permanece además inmutable durante todo el MVP, con independencia
del estado.

Las únicas excepciones funcionales terminales son:

- `COMPLETADA` y `CANCELADA` pueden recibir comentarios conforme a las relaciones
  de la matriz. Esto no decide si comentar incrementa `version_registro`.
- Sólo `COMPLETADA` puede reabrirse explícitamente a `PENDIENTE`, con motivo,
  historial `REABIERTA` y `fecha_finalizacion` corriente en `NULL`, según las
  reglas ya congeladas. Reabrir exige habilitación administrativa vigente sobre
  el scope y autorización efectiva de Administrativo. `CANCELADA` no reabre.

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
contratos HTTP, SQL y tests. Esta decisión no resuelve sync, identidad
interinstalación ni el efecto de comentar sobre `version_registro`.

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
28. La visibilidad se obtiene por creador, responsable vigente/elegible o capacidad de consulta correspondiente; las mutaciones se rigen por ejecución como responsable elegible o capacidad administrativa del scope según la matriz de la sección 20.2.
29. La creación manual exige `puede_administrar` vigente sobre la sucursal propuesta o alcance global administrativo para una tarea global; el scope queda inmutable después de crear la Tarea durante el MVP.
30. La elegibilidad del responsable es continua: exige `puede_operar` vigente sobre la sucursal o alcance global operativo; asignar o reasignar no permite eludirla y su pérdida requiere gestión explícita, sin side effects automáticos.
31. `COMPLETADA` y `CANCELADA` congelan el snapshot funcional corriente; sólo admiten comentarios y, exclusivamente para `COMPLETADA`, la reapertura explícita ya definida.
32. Las capacidades por sucursal son habilitaciones necesarias, no autorización suficiente; toda operación humana protegida requiere además autorización efectiva de Administrativo.
33. La vigencia de `usuario_sucursal` usa el predicado completo y el intervalo `[fecha_desde, fecha_hasta)` de la sección 20.A, evaluados con un único `instante_corte` UTC del servidor.
34. Reabrir `COMPLETADA` conserva al responsable elegible o repara atómicamente al inelegible dejándolo nulo o reemplazándolo por otro elegible; nunca produce una tarea activa con responsable inelegible.

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
- El scope de sucursal/global limita consultas y gestión por alcance sin usar
  `id_instalacion_origen`; creador y responsable siguen siendo relaciones
  distintas.

## 30. Decisiones todavía abiertas

De la numeración original de blockers, los cierres acumulados comprenden **#1,
#2, #3, #4, #5, #8, #9 y #11**. Este segundo incremento cierra exclusivamente
**#1 y #11** mediante las secciones 14 y 20. Permanecen abiertos únicamente, con
su numeración original y sin resolución incidental:

6. Estrategia de sync: `SINCRONIZABLE`, `LOCAL` o `MIXTO`.
7. Si agregar comentario incrementa `version_registro` de la tarea.
10. Identidad canónica interinstalación de usuario para toda referencia humana persistida que deba sincronizarse en `gestion_operativa` —como creador, responsable, autor de comentario y actor del historial funcional—: mecanismo de resolución o mapping y dependencia con Administrativo/Técnico.

Estas decisiones deberán resolverse y validarse contra arquitectura, CORE-EF, autorización, sincronización, SQL, implementación y tests antes de afirmar un contrato técnico completo.
