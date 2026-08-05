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
