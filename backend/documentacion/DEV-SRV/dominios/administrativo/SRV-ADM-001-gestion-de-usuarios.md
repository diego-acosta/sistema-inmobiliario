# SRV-ADM-001 — Gestión de usuarios

## Objetivo
Gestionar usuarios del sistema, permitiendo su alta, modificación, baja lógica y consulta, preservando consistencia, identidad operativa y trazabilidad.

## Alcance
Este servicio cubre:
- alta de usuarios
- modificación de usuarios
- baja lógica de usuarios
- consulta de usuarios
- definición de datos identificatorios

No cubre:
- gestión de roles y permisos
- autenticación (login, tokens)
- autorización de operaciones
- auditoría

## Prerrequisito de autorización central

El permiso activo `ADMIN.USUARIO.ADMINISTRAR` (`Administrar usuarios`) es una
capacidad D1 `GLOBAL` para crear y dar de baja usuarios del sistema. Su receptor
canónico inicial es el rol activo `ADMINISTRADOR_SISTEMA`, sin convertir ese
código de rol en condición de autorización runtime.

Este incremento sólo materializa permiso y grant. Los endpoints de alta y baja
continúan con su runtime legacy hasta la migración posterior. En particular, no
se declara todavía Bearer/D1 productivo y sigue abierta la frontera de los
eventos Sync `usuario_creado` y `usuario_desactivado`.

El permiso independiente `ADMIN.USUARIO_SUCURSAL.ADMINISTRAR` (`Administrar
alcance de usuarios por sucursal`) es una capacidad D1 `GLOBAL` para asignar
sucursales y capacidades operativas a usuarios. La sucursal asignada es dato
funcional del vínculo y no convierte el command administrativo en autorización
contextual. También recibe grant inicial el rol activo
`ADMINISTRADOR_SISTEMA`; el endpoint productivo conserva por ahora su contrato
legacy.

## Entidades principales
- usuario

## Modos del servicio

### Alta
Permite registrar un nuevo usuario.

### Modificación
Permite actualizar datos de un usuario.

### Baja lógica
Permite invalidar un usuario.

### Consulta
Permite visualizar usuarios.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de usuario
- nombre
- datos de contacto cuando corresponda
- estado
- observaciones

### Parámetros de consulta
- identificador de usuario
- estado
- nombre

## Resultado esperado

### Para operaciones write
- identificador de usuario
- estado resultante
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- listado de usuarios
- nombre
- estado
- datos identificatorios

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar datos de usuario
3. registrar usuario
4. persistir con metadatos transversales
5. registrar outbox
6. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar usuario existente
3. validar versión esperada
4. validar modificabilidad
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Baja lógica
1. validar contexto técnico
2. cargar usuario
3. validar condiciones de baja
4. aplicar invalidación
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar usuarios
3. devolver vista de lectura

## Validaciones clave
- consistencia de datos identificatorios
- unicidad cuando corresponda
- no duplicidad indebida
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de usuario
- aplicación de borrado lógico
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-ADM]]

## Dependencias

### Hacia arriba
- contexto técnico válido
- permisos sobre gestión administrativa

### Hacia abajo
- [[SRV-ADM-002-gestion-de-roles-y-permisos]]
- [[SRV-ADM-003-gestion-de-autorizaciones]]
- [[SRV-ADM-004-gestion-de-auditoria]]
- todos los dominios operativos

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-ADMINISTRATIVO]]
- [[CU-ADM]]
- [[RN-ADM]]
- [[ERR-ADM]]
- [[EVT-ADM]]
- [[EST-ADM]]
- DER administrativo

## Pendientes abiertos
- catálogo final de estados de usuario
- definición de atributos obligatorios
- integración con autenticación externa
- políticas de activación/inactivación
- relación con personas del sistema

## Incremento #448 — Credenciales de usuario sólo SQL

`credencial_usuario` queda preparada físicamente como soporte del núcleo administrativo de seguridad para credenciales `PASSWORD`, con metadata CORE-EF, versionado por trigger, soft delete técnico, FKs nullable a instalación, constraints de hash/algoritmo/estado/fechas/contador y unicidad parcial para credenciales activas y principales.

Este servicio todavía no autentica: no crea credenciales, no genera hashes, no valida Argon2id/PHC, no implementa login/logout/tokens/sesiones, no crea principal autenticado, no emite outbox y no escribe historial runtime. `hash_credencial` es dato sensible; no debe exponerse en APIs, logs, errores, eventos genéricos ni documentación con valores reales. La ausencia de credencial implica default-deny para autenticación futura.

#449 (primitivas Argon2id) y #450 (bootstrap/sincronización segura) permanecen pendientes. #446 continúa bloqueado por esos incrementos y no queda implementado por #448.

## Incremento #449 — Primitivas Argon2id internas

Existe una primitiva interna transversal para credenciales futuras basada en Argon2id v1 (`argon2id:v1`) con salida PHC. #449 no crea credenciales, no persiste `hash_credencial`, no escribe `algoritmo_hash`, no implementa login/logout/tokens/sesiones ni principal autenticado y no agrega endpoints.

Para consumidores futuros, `hash_credencial` deberá persistir el PHC Argon2id y `algoritmo_hash` deberá persistir `argon2id:v1`. #450 y #446 siguen pendientes.

## Bootstrap de credenciales — #454, actualizado a autoridad central

La CLI administrativa de bootstrap puede ejecutarse como proceso en el entorno del operador; su command opera contra la autoridad PostgreSQL central, sin depender de instalación ni persistir procedencia de instalación. Permite `init` cuando no hay credencial PASSWORD activa y `reset` cuando existe exactamente una activa y principal. El caso de uso es dueño del único commit/rollback; genera el hash antes de abrir la transacción, bloquea usuario y credenciales ordenadas, usa un único `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'`, revoca históricamente e inserta una fila nueva. El replay por `op_id_alta` exige mismo usuario y verificación Argon2id. Los nuevos resets registran `motivo_revocacion = RESET_ADMINISTRATIVO`, sin atribuir topología; no se reescriben motivos históricos.

Clasificación CORE-EF: `COMMAND_WRITE_TECNICO CENTRAL`, no sincronizable. La ejecución local del proceso CLI no convierte el command en una escritura local por instalación. Headers HTTP, `If-Match-Version`, outbox, eventos y lock lógico persistido: **NO APLICA**. El versionado se delega a los triggers SQL vigentes; la transacción revierte íntegramente ante fallos.

## Incremento histórico #455 — exclusión del transporte

En el corte histórico #455, credenciales y sesiones eran locales/no sincronizables en todos sus campos y aún no se implementaban login, logout, tokens, autorización ni sesiones runtime. En #544 son centrales y conservan la exclusión del transporte Sync. El contrato verificable está en `documentacion/SINCRONIZACION/SEGURIDAD-CREDENCIALES-455.md`.

## Incremento #447 — resolución read-only del principal

`get_authenticated_principal` reutiliza el parser bearer y el digest de #446, consulta una proyección explícita de `sesion_usuario` y `usuario`, y devuelve el value object inmutable `AuthenticatedPrincipal`. Toda sesión no utilizable o usuario no elegible colapsa públicamente a `401 INVALID_SESSION`; una falla técnica colapsa a `500 SESSION_TECHNICAL_ERROR`. No se revalida la credencial, no se hace commit, lock, outbox, sync, autorización ni actualización de actividad. El principal central ya no proyecta sucursal ni instalación; sólo los seis campos de identidad de GEN-003.

## Slice central posterior a #543

Login y bootstrap no reciben Settings ni llaman al resolver de instalación.
Preflight/execute de CLI reciben usuario, secreto y op_id; preview/result no
exponen instalación. Se conserva la frontera TTY administrativa, sin inventar
D1/D2. Init/reset persisten procedencia NULL; op_id sigue justificándose por
replay/conflicto de un command sensible. Las credenciales revocadas conservan
su origen histórico si lo tenían, y la nueva modificación central usa NULL.
Sesiones conservan token opaco/digest SHA-256, TTL absoluto de 8h y logout
idempotente; se revalida usuario/credencial bajo lock antes del insert.
El reloj real de sesión usa clock_timestamp AT TIME ZONE UTC; bootstrap usa
instante transaccional UTC. Defaults/triggers físicos acompañan esa convención.
No se modifican fechas económicas ni autorización GLOBAL/contextual.
Validación vigente externa sobre `3503ff2`, Windows/PostgreSQL 18.0:
83 passed sin DB (2 warnings); focal inicial 50 passed / 1 failed (1 warning),
con un fallo concurrente transitorio no reproducido: luego 10/10 PASS aislado
y 106 passed en el grupo PostgreSQL ampliado (1 warning), incluido ese caso.
Incluye `RESET_ADMINISTRATIVO` y la frontera HTTP UTC; detalle en GEN-003 §19.
`2d1ff2f` (48/106) es evidencia histórica del fix HTTP UTC, previa al cambio
final de semántica local/reset. `c70ea181` (29/104 y 149 unitarios) es evidencia histórica
anterior al fix HTTP UTC, conservada en GEN-003 §19.
DEV/TEST se reconstruyen sin preservar auth legacy. Primera aplicación: ambas tablas
auth vacías o rechazo atómico antes de cambios; reejecución con marker central:
filas preservadas. Bootstrap de credenciales y nuevos logins son posteriores.
No hay conversión, cierre ni rotación histórica. GEN-003 §19 define el marker y
registra la validación PostgreSQL final de la inicialización limpia, sin declarar el backend
completo centralizado. Si aparecen datos útiles, detener rebuild y definir migración específica.
