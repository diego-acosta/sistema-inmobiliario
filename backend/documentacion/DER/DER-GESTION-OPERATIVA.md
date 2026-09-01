# GOP-DER-001 — DER Gestión Operativa — MVP inicial de Tarea

## 1. Metadatos

| Dato | Valor |
| --- | --- |
| Identificador documental | `GOP-DER-001` |
| Dominio | `gestion_operativa` |
| Versión | `1.0` |
| Estado | Propuesto para revisión formal |
| Incremento | Issue #528 |
| Baseline | `main` — `56a60341916d8c7d7151566783f015d7d7452f29` |
| Dependencia normativa | `DEV-ARCH-GOP-001` |

## 2. Propósito y alcance

Este DER materializa la estructura conceptual del MVP inicial de Tarea definida
por `DEV-ARCH-GOP-001`. El dominio contiene exactamente tres entidades propias:
`Tarea`, `ComentarioTarea` e `HistorialTarea`.

El documento habilita el diseño posterior de servicios (`DEV-SRV`). No implementa
SQL, migrations, endpoints, DTO, runtime, tests ni frontend; tampoco fija nombres
físicos definitivos ni amplía el MVP.

## 3. Fuentes y prevalencia

Fuentes principales:

1. `AGENTS.md`.
2. `backend/documentacion/DEV-ARCH/dominios/gestion_operativa/DEV-ARCH-GOP-001.md`.
3. SQL real, sólo como evidencia de owners, relaciones y convenciones CORE-EF.
4. Implementación y tests reales, cuando materializan contratos vigentes.
5. Issues y PR vigentes: #528, #523, PR #524, #527 y #522.
6. `PROJECT-STATUS.md` y `CODEX-WORKFLOW.md`.
7. `GOP-FREEZE-001` y documentación histórica como contexto subordinado.

Ante contradicción rige el orden: `AGENTS.md` → `DEV-ARCH-GOP-001` → SQL →
implementación → tests → issues/PR → `PROJECT-STATUS.md` →
`CODEX-WORKFLOW.md` → documentación histórica. No se detectó una contradicción
material que obligue a reabrir la arquitectura. El estado desactualizado de #523
en documentos operativos es una diferencia de seguimiento, no de diseño.

## 4. Clasificación y ownership

| Dominio owner | Responsabilidad |
| --- | --- |
| Gestión Operativa | `Tarea`, `ComentarioTarea`, `HistorialTarea` y lifecycle funcional de Tarea |
| Administrativo | `usuario`, autenticación/autorización humana, roles y permisos |
| Operativo | `sucursal` e `instalacion` |
| Técnico / CORE-EF / Sync | `op_id`, `operacion_idempotente`, outbox, inbox, retry, fencing, lease y operation scope |

Las estructuras transversales no son entidades GOP ni trasladan ownership. El
DER no crea ledger, outbox, inbox, dependencia pendiente o conflicto propios.

## 5. Diagrama DER

```mermaid
erDiagram
    USUARIO ||--o{ TAREA : crea
    USUARIO o|--o{ TAREA : responsable
    SUCURSAL o|--o{ TAREA : scope
    TAREA ||--o{ COMENTARIO_TAREA : recibe
    USUARIO ||--o{ COMENTARIO_TAREA : escribe
    TAREA ||--o{ HISTORIAL_TAREA : registra
    USUARIO o|--o{ HISTORIAL_TAREA : actua
```

Cardinalidades y condiciones:

- el creador es obligatorio cuando `origen = USUARIO`; queda nullable en la
  estructura exclusivamente para el futuro `origen = SISTEMA`;
- el responsable es opcional y existe como máximo uno;
- la sucursal funcional es opcional y existe como máximo una; `NULL` significa
  alcance global;
- todo comentario pertenece a una Tarea y tiene autor humano obligatorio;
- toda entrada de historial pertenece a una Tarea;
- el actor del historial es condicional por tipo de hecho y obligatorio para
  `REABIERTA`;
- instalación no es scope funcional y por eso no aparece como relación funcional
  del diagrama; interviene sólo en procedencia CORE-EF de las entidades
  sincronizables.

El diagrama expresa cardinalidad estructural. La regla condicional creador/origen
no puede expresarse completamente mediante la cardinalidad Mermaid.

## 6. Tarea

### 6.1 Rol estructural

`Tarea` es el aggregate root, snapshot funcional versionado, entidad
sincronizable y autoridad del lifecycle. La creación nace en versión 1 y no usa
versión esperada. Toda mutación material posterior avanza exactamente
`Vn → Vn+1`; la estrategia física de CAS se difiere.

### 6.2 Matriz estructural

| Campo conceptual | Obligatorio | Mutable | Relación / naturaleza |
| --- | --- | --- | --- |
| PK local | Sí | No | Identidad local para joins y FK |
| `uid_global` | Sí | No | Identidad portable propia |
| `version_registro` | Sí | Incremental | Versión del snapshot; nace en 1 |
| `origen` | Sí | No | `USUARIO`; `SISTEMA` reservado |
| creador | Condicional | No | FK local a `usuario` |
| `generador_sistema` | Condicional | No | Descriptor funcional, no credencial |
| título | Sí | Sí | Texto funcional obligatorio |
| descripción | No | Sí | Texto funcional |
| prioridad | Sí | Sí | `BAJA` / `NORMAL` / `ALTA` / `URGENTE` |
| responsable | No | Sí | FK local a `usuario`; máximo uno |
| `fecha_objetivo` | No | Sí | `DATE` funcional |
| estado | Sí | Transición válida | `PENDIENTE` / `EN_CURSO` / `COMPLETADA` / `CANCELADA` |
| `fecha_finalizacion` | No | Derivada | Resultado del lifecycle |
| sucursal | No | No en MVP | FK local a `sucursal`; `NULL` global |
| `deleted_at` | No | Baja futura | Soft delete técnico, distinto del lifecycle |
| metadata CORE-EF | Según contrato | Según mutación | Identidad, causalidad y procedencia técnica |

No se congelan longitudes ni tipos SQL; `DATE` para `fecha_objetivo` es una
decisión funcional ya cerrada. `VENCIDA` se calcula a partir de estado, fecha
objetivo y fecha de corte; no se persiste como estado.

### 6.3 Metadata CORE-EF

Tarea requiere conceptualmente el bloque aplicable completo:

- `uid_global`;
- `version_registro`;
- `created_at`;
- `updated_at`;
- `deleted_at`;
- instalación de origen;
- instalación de última modificación;
- `op_id_alta`;
- `op_id_ultima_modificacion`.

Los nombres físicos de las FK de instalación permanecen sujetos a la convención
CORE-EF que se confirme al diseñar SQL. La instalación conserva ownership
Operativo y no define visibilidad ni scope funcional de Tarea.

## 7. ComentarioTarea

### 7.1 Rol estructural

`ComentarioTarea` es un append funcional y sincronizable independiente. Tiene
identidad distribuida, versión e idempotencia propias; no es parte del snapshot
mutable de Tarea.

### 7.2 Matriz estructural

| Campo conceptual | Obligatorio | Mutable | Relación / naturaleza |
| --- | --- | --- | --- |
| PK local | Sí | No | Identidad local |
| `uid_global` | Sí | No | Identidad portable propia |
| `version_registro` | Sí | No ordinariamente | Versión propia; normalmente 1 en MVP |
| Tarea | Sí | No | FK local obligatoria a Tarea |
| autor | Sí | No | FK local obligatoria a `usuario` |
| texto | Sí | No | Contenido funcional append-only |
| instante funcional | Sí | No | Instante de ocurrencia |
| metadata CORE-EF | Según contrato | No ordinariamente | Bloque de entidad sincronizable |

Su metadata CORE-EF comprende conceptualmente `uid_global`,
`version_registro`, `created_at`, `updated_at`, `deleted_at`, instalaciones de
origen y última modificación, `op_id_alta` y `op_id_ultima_modificacion`. Esto no
habilita edición ni borrado funcional en el MVP.

Agregar un comentario:

- no incrementa `Tarea.version_registro`;
- no participa del CAS de Tarea;
- no usa versión esperada de Tarea;
- no se edita ni se borra funcionalmente;
- no genera un historial duplicado de comentarios.

## 8. HistorialTarea

### 8.1 Rol estructural

`HistorialTarea` es append funcional interno, no root y no sincronizable de
manera autónoma. Se genera atómicamente por la operación de Tarea y converge como
parte de su efecto causal. No es un event store ni la autoridad para reconstruir
el snapshot.

### 8.2 Matriz estructural

| Campo conceptual | Obligatorio | Mutable | Relación / naturaleza |
| --- | --- | --- | --- |
| PK local | Sí | No | Identidad exclusivamente local |
| Tarea | Sí | No | FK local obligatoria |
| tipo de hecho | Sí | No | Discriminador funcional |
| actor | Condicional | No | FK local a `usuario` |
| instante funcional | Sí | No | Instante del hecho |
| `op_id` causal | Sí | No | Correlación con la operación de Tarea |
| evidencia anterior | Según hecho | No | Representación física diferida |
| evidencia nueva | Según hecho | No | Representación física diferida |
| motivo | Para `REABIERTA` | No | Evidencia funcional obligatoria |
| finalización anterior | Cuando aplica | No | Evidencia de lifecycle previo |

Aplicabilidad explícita:

| Capacidad | HistorialTarea |
| --- | --- |
| `uid_global` propio | NO APLICA |
| `version_registro` propio | NO APLICA |
| bloque CORE-EF independiente | NO APLICA |
| sync autónomo | NO APLICA |
| outbox propio | NO APLICA |
| CAS, retry, consumer o conflicto propios | NO APLICA |
| soft delete propio | NO APLICA |

No se impone todavía unicidad sobre `op_id`: una operación indivisible puede
requerir una o más filas de evidencia y esa granularidad pertenece a DEV-SRV/SQL.

### 8.3 Catálogo conceptual mínimo

El historial debe soportar hechos funcionales equivalentes a:

- `CREADA`;
- `CONTENIDO_MODIFICADO`;
- `ASIGNADA`;
- `REASIGNADA`;
- `DESASIGNADA`;
- `PRIORIDAD_MODIFICADA`;
- `FECHA_OBJETIVO_MODIFICADA`;
- `ESTADO_MODIFICADO`;
- `COMPLETADA`;
- `CANCELADA`;
- `REABIERTA`.

No se fijan códigos físicos. Para `REABIERTA` la estructura debe permitir exigir
actor humano, instante, motivo, estado anterior `COMPLETADA`, estado nuevo
`PENDIENTE` y finalización anterior.

La representación de evidencia anterior/nueva queda deliberadamente abierta:
este DER no elige JSON libre, EAV, snapshots completos ni una tabla auxiliar de
valores.

## 9. Referencias externas y portabilidad

El patrón obligatorio es:

```text
GOP persiste FK local
→ entidad owner
→ owner.uid_global
→ producer serializa owner.uid_global
→ receptor resuelve uid_global → PK local
→ GOP persiste FK local resuelta
```

| Referencia GOP | Persistencia local | Identidad portable | Owner |
| --- | --- | --- | --- |
| creador | FK a `usuario` | `usuario.uid_global` | Administrativo |
| responsable | FK nullable a `usuario` | `usuario.uid_global` | Administrativo |
| autor de comentario | FK a `usuario` | `usuario.uid_global` | Administrativo |
| actor de historial | FK condicional a `usuario` | `usuario.uid_global` | Administrativo |
| sucursal funcional | FK nullable a `sucursal` | `sucursal.uid_global` | Operativo |
| instalación de procedencia | FK CORE-EF local | `instalacion.uid_global` en metadata/envelope | Operativo/Técnico |

GOP no duplica `usuario.uid_global`, `sucursal.uid_global` ni
`instalacion.uid_global`. Ninguna PK remota viaja. El soft delete del owner
conserva su fila e identidad portable para trazabilidad y resolución.

## 10. Invariantes estructurales congeladas

- Tarea y ComentarioTarea tienen UID propio; HistorialTarea no.
- Tarea y ComentarioTarea tienen versionado propio; HistorialTarea no.
- ComentarioTarea e HistorialTarea pertenecen siempre a una Tarea.
- El comentario tiene autor humano obligatorio.
- El historial conserva el `op_id` causal de la operación de Tarea.
- Responsable y sucursal admiten como máximo una referencia cada uno.
- Creador y generador son condicionales y excluyentes según origen.
- El título es obligatorio.
- Prioridad y estado pertenecen a catálogos conceptuales cerrados.
- `deleted_at` es independiente de `CANCELADA` y del lifecycle.
- `REABIERTA` exige actor y motivo, además de evidencia del estado/finalización
  anteriores.
- La metadata CORE-EF no duplica semántica funcional.
- Las referencias externas persisten FK local y no copian UID del owner.
- La sucursal funcional es nullable, inmutable en MVP y `NULL` significa global.
- Instalación expresa procedencia técnica, no scope funcional.
- Un comentario no versiona Tarea ni usa su CAS.
- Historial no tiene outbox, retry, consumer, CAS o conflicto autónomos.

## 11. Responsabilidades posteriores

### 11.1 SQL

Quedan para el diseño físico:

- nombres definitivos de tablas y columnas;
- tipos y longitudes finales;
- `CHECK`, enums físicos, FK, defaults y triggers;
- índices y unicidades definitivas;
- protección física de inmutabilidad;
- estrategia concreta de CAS;
- reglas físicas de timestamps y metadata CORE-EF.

### 11.2 Application layer / DEV-SRV

Quedan para servicios y contratos posteriores:

- lifecycle contextual y elegibilidad continua del responsable;
- autorización y visibilidad;
- idempotencia y frontera transaccional concreta;
- continuidad remota y representación de gaps;
- `PENDING_DEPENDENCY`, retry, replay y conflicto;
- causalidad de comentarios frente a baja;
- fecha de corte para `VENCIDA`;
- auth/authz antes de cualquier replay o conflicto observable;
- nombres y granularidad de commands/eventos.

## 12. Consultas que la estructura debe soportar

La futura persistencia debe permitir:

- obtener y listar Tareas;
- “Mis tareas” y “Tareas creadas por mí”;
- pendientes, vencidas derivadas y sin asignar;
- filtros por responsable, creador, estado, sucursal, prioridad y fecha objetivo;
- consultar comentarios;
- consultar historial.

Son candidatos para evaluar índices posteriormente: UID de Tarea y Comentario,
baja lógica, responsable, creador, estado, sucursal, prioridad, fecha objetivo y
las FK de comentario/historial a Tarea. Esta lista no congela índices.

## 13. Sync y portabilidad

- Tarea viaja por `Tarea.uid_global` y su continuidad de versión.
- ComentarioTarea viaja por `ComentarioTarea.uid_global` y su versión propia.
- Las referencias humanas viajan por `usuario.uid_global`.
- La sucursal funcional viaja por `sucursal.uid_global` cuando está presente.
- La instalación portable pertenece al envelope/metadata técnica.
- HistorialTarea no tiene UID propio; el descriptor causal suficiente viaja como
  parte de la operación de Tarea para materializarlo determinísticamente.
- No se transportan ni almacenan PK remotas.
- Se reutiliza la infraestructura transversal; no se crean tablas Sync GOP.

## 14. Origen SISTEMA reservado

El modelo permite proteger conceptualmente estas formas:

| Origen | Creador | `generador_sistema` |
| --- | --- | --- |
| `USUARIO` | Obligatorio | `NULL` |
| `SISTEMA` | `NULL` | Obligatorio |

El MVP habilita únicamente `USUARIO`. `SISTEMA` permanece reservado: #522 sigue
abierto, no bloquea el MVP humano y es prerequisito de cualquier automatización.
No se materializa una identidad humana ficticia para procesos técnicos ni se
crean credenciales, service accounts, API keys o claves de hecho fuente.

## 15. Fuera de alcance post-MVP

El conjunto de #527 permanece completo fuera del DER. No se agregan tablas ni
campos de preparación para agenda completa, recordatorios, alertas,
notificaciones, recurrencia, subtareas, dependencias, múltiples responsables,
equipos, sectores, Kanban, SLA, workflows configurables, adjuntos, generación
automática efectiva, control de mora, relaciones polimórficas, incidencias,
novedades, observaciones, frontend avanzado o dashboard analítico.

## 16. NO CONFIRMADO / DIFERIDO

Los siguientes puntos no bloquean el DER y no se deciden aquí:

- nombres físicos definitivos de tablas y columnas;
- tipos y longitudes de textos;
- `CHECK` frente a enum físico;
- representación física de evidencia anterior/nueva;
- catálogo físico de tipos de historial;
- unicidades de HistorialTarea relacionadas con `op_id`;
- índices finales;
- estrategia física de CAS;
- representación y tratamiento técnico de gaps de continuidad;
- clasificación terminal de un comentario causalmente posterior a baja;
- granularidad exacta entre una operación de Tarea y sus filas de historial.

## 17. Criterio de suficiencia

El DER queda estructuralmente suficiente para iniciar DEV-SRV cuando una revisión
formal confirme: exactamente tres entidades GOP propias; ownership preservado;
Tarea como root versionada; ComentarioTarea como append sincronizable
independiente; HistorialTarea interno sin identidad distribuida; referencias
externas sin UID duplicados; separación entre lifecycle, soft delete, scope y
procedencia; y ausencia de capacidades de #527, SQL, API o runtime anticipados.
