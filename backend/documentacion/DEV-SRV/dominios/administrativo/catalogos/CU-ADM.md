# CU-ADM — Casos de uso del dominio Administrativo

## Objetivo
Catalogar los casos de uso del dominio administrativo como apoyo a implementación, trazabilidad funcional y alineación con los servicios administrativos definidos en DEV-SRV.

## Alcance del dominio
Este dominio cubre gestión de usuarios y acceso, seguridad y autorización, auditoría administrativa, configuración y parámetros, catálogos maestros y consulta administrativa consolidada, sin mezclar lógica operativa de otros dominios.

## Bloques del dominio
- Usuarios y acceso
- Seguridad, roles, permisos y autorización
- Auditoría administrativa
- Configuración y parámetros
- Catálogos maestros
- Consulta y reporte administrativo

---

## A. Usuarios y acceso

### CU-ADM-001 — Alta de usuario
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: registrar un nuevo usuario administrativo del sistema.
- entidades: usuario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-002 — Modificación de usuario
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: actualizar datos identificatorios o de estado de un usuario existente.
- entidades: usuario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-003 — Baja lógica o desactivación de usuario
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: invalidar o desactivar un usuario sin eliminarlo físicamente.
- entidades: usuario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-004 — Reactivación de usuario
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: volver a habilitar un usuario previamente desactivado cuando el proceso lo permita.
- entidades: usuario
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-005 — Asociación de usuario con persona
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: vincular un usuario administrativo con la persona correspondiente cuando aplique el modelo.
- entidades: usuario, persona
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-006 — Gestión de habilitación de usuario por sucursal
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: administrar la habilitación operativa de un usuario en una o más sucursales.
- entidades: usuario, sucursal, usuario_sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-007 — Alta o gestión de credencial de usuario
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: registrar o administrar la credencial asociada a un usuario.
- entidades: usuario, credencial_usuario
- criticidad: crítica
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-ADM-008 — Revocación o bloqueo de credencial
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: bloquear o revocar una credencial para impedir su uso.
- entidades: credencial_usuario, usuario
- criticidad: crítica
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-ADM-009 — Cambio o reseteo de credencial
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: modificar o resetear una credencial de usuario dentro del proceso autorizado.
- entidades: credencial_usuario, usuario
- criticidad: crítica
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-ADM-010 — Inicio de sesión
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: registrar la apertura de una sesión válida de usuario.
- entidades: sesion_usuario, usuario, credencial_usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-011 — Cierre de sesión
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: registrar el cierre de una sesión activa de usuario.
- entidades: sesion_usuario, usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: sí

### CU-ADM-012 — Registro de historial de acceso
- servicio_origen: SRV-ADM-001
- tipo: write
- objetivo: registrar eventos de acceso vinculados a autenticación y uso de sesiones.
- entidades: historial_acceso, usuario, sesion_usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-013 — Consulta de usuario administrativo
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar información básica de un usuario administrativo.
- entidades: usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-014 — Consulta integral de usuario
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar usuario con su contexto administrativo relacionado.
- entidades: usuario, usuario_sucursal, credencial_usuario, sesion_usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-015 — Consulta de credenciales de usuario
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar credenciales asociadas a un usuario y su estado.
- entidades: credencial_usuario, usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-016 — Consulta de sesiones activas
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar sesiones vigentes o activas del sistema o de un usuario.
- entidades: sesion_usuario, usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-017 — Consulta de historial de acceso
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar el historial de accesos registrado por usuario o contexto.
- entidades: historial_acceso, usuario, sesion_usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-018 — Consulta de usuarios por sucursal
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar usuarios habilitados o vinculados a una sucursal.
- entidades: usuario, usuario_sucursal, sucursal
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-019 — Consulta de usuarios por estado
- servicio_origen: SRV-ADM-001
- tipo: read
- objetivo: consultar usuarios según su estado administrativo u operativo.
- entidades: usuario
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## B. Seguridad, roles, permisos y autorización

### CU-ADM-020 — Alta de rol de seguridad
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: registrar un nuevo rol de seguridad del sistema.
- entidades: rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-021 — Modificación de rol de seguridad
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: actualizar definición o estado de un rol de seguridad existente.
- entidades: rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-022 — Baja lógica de rol de seguridad
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: invalidar un rol de seguridad sin eliminarlo físicamente.
- entidades: rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-023 — Alta de permiso
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: registrar un permiso del sistema.
- entidades: permiso
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-024 — Modificación de permiso
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: actualizar un permiso existente.
- entidades: permiso
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-025 — Baja lógica de permiso
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: invalidar un permiso sin eliminarlo físicamente.
- entidades: permiso
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-026 — Asociación de permiso a rol
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: vincular permisos a un rol de seguridad.
- entidades: rol_permiso, rol_administrativo, permiso
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-027 — Desasociación o modificación de permiso por rol
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: ajustar la composición de permisos asignados a un rol.
- entidades: rol_permiso, rol_administrativo, permiso
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-028 — Asignación de rol de seguridad a usuario
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: asignar un rol de seguridad a un usuario.
- entidades: usuario_rol, usuario, rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-029 — Revocación o modificación de rol de usuario
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: revocar o ajustar la asignación de roles de seguridad sobre un usuario.
- entidades: usuario_rol, usuario, rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-030 — Asignación de rol por sucursal
- servicio_origen: SRV-ADM-002
- tipo: write
- objetivo: asignar un rol de seguridad en alcance acotado a sucursal cuando el modelo lo soporte.
- entidades: usuario_rol, usuario, rol_administrativo, sucursal
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-031 — Gestión de alcance de autorización
- servicio_origen: SRV-ADM-003
- tipo: write
- objetivo: registrar o ajustar el alcance contextual de una autorización administrativa.
- entidades: autorizacion, solicitud_autorizacion, usuario, rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-032 — Gestión de denegación explícita
- servicio_origen: SRV-ADM-003
- tipo: write
- objetivo: registrar una denegación explícita sobre una autorización o contexto de acceso.
- entidades: autorizacion, solicitud_autorizacion, usuario, rol_administrativo
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-033 — Consulta de roles de seguridad
- servicio_origen: SRV-ADM-002
- tipo: read
- objetivo: consultar roles de seguridad disponibles y su estado.
- entidades: rol_administrativo
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-034 — Consulta de permisos
- servicio_origen: SRV-ADM-002
- tipo: read
- objetivo: consultar permisos definidos en el sistema.
- entidades: permiso
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-035 — Consulta de permisos por rol
- servicio_origen: SRV-ADM-002
- tipo: read
- objetivo: consultar permisos asociados a un rol de seguridad.
- entidades: rol_permiso, rol_administrativo, permiso
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-036 — Consulta de roles y permisos de usuario
- servicio_origen: SRV-ADM-002
- tipo: read
- objetivo: consultar la composición de roles y permisos efectivos de un usuario.
- entidades: usuario_rol, rol_permiso, usuario, rol_administrativo, permiso
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-037 — Consulta de roles por sucursal
- servicio_origen: SRV-ADM-002
- tipo: read
- objetivo: consultar asignaciones de roles acotadas a sucursal.
- entidades: usuario_rol, rol_administrativo, usuario, sucursal
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-038 — Consulta de autorización efectiva
- servicio_origen: SRV-ADM-003
- tipo: read
- objetivo: consultar si un usuario cuenta con autorización efectiva en un contexto dado.
- entidades: autorizacion, solicitud_autorizacion, usuario, rol_administrativo
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-039 — Consulta de denegaciones explícitas
- servicio_origen: SRV-ADM-003
- tipo: read
- objetivo: consultar denegaciones explícitas registradas sobre accesos o autorizaciones.
- entidades: autorizacion, solicitud_autorizacion, usuario, rol_administrativo
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## C. Auditoría administrativa

### CU-ADM-040 — Registro de auditoría administrativa
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: registrar un evento auditable dentro del dominio administrativo.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-041 — Registro de evento de auditoría administrativa
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: registrar un evento administrativo relevante con su contexto técnico y funcional.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-042 — Registro de cambio administrativo relevante
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: auditar cambios administrativos con impacto funcional o de control.
- entidades: auditoria_evento, auditoria_contexto, entidad_auditada
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-043 — Registro de evento de seguridad administrativa
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: auditar eventos asociados a seguridad administrativa y control de acceso.
- entidades: auditoria_evento, auditoria_contexto, usuario
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-044 — Registro de cambio de configuración administrativa
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: auditar cambios sobre configuraciones y parámetros administrativos.
- entidades: auditoria_evento, configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-045 — Registro de cambio de roles, permisos o autorización
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: auditar cambios sobre seguridad administrativa y autorizaciones.
- entidades: auditoria_evento, rol_administrativo, permiso, autorizacion
- criticidad: crítica
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-046 — Registro de cambio de usuario, credencial o sesión
- servicio_origen: SRV-ADM-004
- tipo: write
- objetivo: auditar cambios administrativos sobre usuarios, credenciales o sesiones cuando corresponda.
- entidades: auditoria_evento, usuario, credencial_usuario, sesion_usuario
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-047 — Consulta de auditoría administrativa
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar eventos de auditoría administrativa registrados.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-048 — Consulta de eventos por usuario
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar eventos auditables filtrados por usuario actor o afectado.
- entidades: auditoria_evento, usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-049 — Consulta de eventos por entidad
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar auditoría asociada a una entidad determinada.
- entidades: auditoria_evento, entidad_auditada
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-050 — Consulta de eventos por sucursal
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar eventos auditables filtrados por sucursal.
- entidades: auditoria_evento, auditoria_contexto, sucursal
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-051 — Consulta de eventos por instalación
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar eventos auditables filtrados por instalación técnica.
- entidades: auditoria_evento, auditoria_contexto, instalacion
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-052 — Consulta de eventos por rango temporal
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar auditoría por período temporal.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-053 — Consulta de trazabilidad administrativa
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: reconstruir trazabilidad administrativa sobre acciones, usuarios y entidades.
- entidades: auditoria_evento, auditoria_contexto, usuario, entidad_auditada
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-054 — Consulta de eventos de seguridad administrativa
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar auditoría específica de seguridad administrativa.
- entidades: auditoria_evento, auditoria_contexto, usuario
- criticidad: crítica
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-055 — Consulta de auditoría integral de usuario administrativo
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar de forma integral la trazabilidad administrativa de un usuario.
- entidades: auditoria_evento, usuario, credencial_usuario, sesion_usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-056 — Emisión de reporte de auditoría administrativa
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir una vista consolidada y exportable de auditoría administrativa.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-057 — Consulta de cambios sobre roles y permisos
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar trazabilidad de cambios sobre roles y permisos.
- entidades: auditoria_evento, rol_administrativo, permiso, rol_permiso
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-058 — Consulta de cambios sobre usuarios y credenciales
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar trazabilidad de cambios sobre usuarios, credenciales y sesiones.
- entidades: auditoria_evento, usuario, credencial_usuario, sesion_usuario
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-059 — Consulta de cambios sobre configuración y parámetros
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar trazabilidad de cambios sobre configuración y parámetros.
- entidades: auditoria_evento, configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-060 — Consulta de cambios sobre catálogos administrativos
- servicio_origen: SRV-ADM-004
- tipo: read
- objetivo: consultar trazabilidad de cambios sobre catálogos maestros administrativos.
- entidades: auditoria_evento, catalogo_maestro, catalogo_item
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## D. Configuración y parámetros

### CU-ADM-061 — Alta de configuración general
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: registrar una configuración general del sistema.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-062 — Modificación de configuración general
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: actualizar una configuración general existente.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-063 — Baja lógica o desactivación de configuración
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: invalidar o desactivar una configuración general cuando corresponda.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-064 — Alta de parámetro del sistema
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: registrar un parámetro del sistema.
- entidades: configuracion_parametro
- criticidad: alta
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-065 — Modificación de parámetro del sistema
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: actualizar definición o atributos de un parámetro existente.
- entidades: configuracion_parametro
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-066 — Baja lógica de parámetro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: invalidar un parámetro sin eliminarlo físicamente.
- entidades: configuracion_parametro
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-067 — Alta de valor de parámetro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: registrar un valor concreto para un parámetro y alcance dado.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-068 — Modificación de valor de parámetro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: actualizar un valor de parámetro existente.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-069 — Cierre o reemplazo de vigencia de valor de parámetro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: cerrar una vigencia existente o reemplazarla por un nuevo valor.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-070 — Resolución de parámetro efectivo
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: resolver el valor efectivo de un parámetro según alcance y contexto.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-071 — Consulta de configuración general
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar configuraciones generales del sistema.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-072 — Consulta de parámetros del sistema
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar parámetros definidos en el sistema.
- entidades: configuracion_parametro
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-073 — Consulta de valores vigentes
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar valores vigentes de parámetros por alcance.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-074 — Consulta de historial de valores
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar histórico de valores asociados a parámetros.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-075 — Consulta consolidada de configuración y parámetros
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: consultar de forma consolidada configuraciones y parámetros del sistema.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## E. Catálogos maestros

### CU-ADM-076 — Alta de catálogo maestro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: registrar un catálogo maestro global del sistema.
- entidades: catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-077 — Modificación de catálogo maestro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: actualizar definición o estado de un catálogo maestro.
- entidades: catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-078 — Baja lógica de catálogo maestro
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: invalidar un catálogo maestro sin eliminarlo físicamente.
- entidades: catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-079 — Alta de ítem de catálogo
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: registrar un ítem dentro de un catálogo maestro.
- entidades: catalogo_item, catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: no

### CU-ADM-080 — Modificación de ítem de catálogo
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: actualizar un ítem existente de catálogo.
- entidades: catalogo_item, catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-081 — Baja lógica de ítem de catálogo
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: invalidar un ítem de catálogo sin eliminarlo físicamente.
- entidades: catalogo_item, catalogo_maestro
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-082 — Gestión de jerarquía de catálogo
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: administrar relaciones jerárquicas entre ítems de catálogo.
- entidades: catalogo_maestro, catalogo_item
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-083 — Gestión de disponibilidad por sucursal
- servicio_origen: SRV-ADM-005
- tipo: write
- objetivo: administrar disponibilidad de catálogos o ítems por sucursal cuando aplique.
- entidades: catalogo_maestro, catalogo_item, sucursal
- criticidad: media
- sincronizable: sí
- requiere_versionado: sí
- requiere_lock: no
- genera_op_id: sí
- genera_outbox: sí
- puede_entrar_en_conflicto: sí

### CU-ADM-084 — Consulta de catálogos maestros
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar catálogos maestros definidos en el sistema.
- entidades: catalogo_maestro
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-085 — Consulta de ítems de catálogo
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar ítems contenidos en catálogos maestros.
- entidades: catalogo_item, catalogo_maestro
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-086 — Consulta de jerarquías de catálogo
- servicio_origen: SRV-ADM-005
- tipo: read
- objetivo: consultar relaciones jerárquicas definidas entre ítems de catálogo.
- entidades: catalogo_maestro, catalogo_item
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-087 — Consulta de historial de catálogo
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: consultar histórico o trazabilidad funcional de cambios en catálogos maestros.
- entidades: catalogo_maestro, catalogo_item, auditoria_evento
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## F. Consulta y reporte administrativo

### CU-ADM-088 — Consulta operativa administrativa
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: consultar una vista operativa consolidada del dominio administrativo.
- entidades: usuario, rol_administrativo, permiso, autorizacion, auditoria_evento, configuracion_parametro
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-089 — Emisión de reporte de usuarios
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de usuarios administrativos.
- entidades: usuario, usuario_sucursal
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-090 — Emisión de reporte de accesos
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de accesos, sesiones e historial de acceso.
- entidades: sesion_usuario, historial_acceso, usuario
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-091 — Emisión de reporte de seguridad y autorización
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de roles, permisos, autorizaciones y denegaciones.
- entidades: rol_administrativo, permiso, usuario_rol, rol_permiso, autorizacion
- criticidad: alta
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-092 — Emisión de reporte de auditoría administrativa
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de auditoría administrativa.
- entidades: auditoria_evento, auditoria_contexto
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-093 — Emisión de reporte de parámetros
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de parámetros y configuraciones del sistema.
- entidades: configuracion_parametro, configuracion_contexto
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-094 — Emisión de reporte de catálogos
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir un reporte consolidado de catálogos maestros e ítems.
- entidades: catalogo_maestro, catalogo_item
- criticidad: baja
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

### CU-ADM-095 — Emisión de reporte administrativo consolidado
- servicio_origen: SRV-ADM-006
- tipo: read
- objetivo: emitir una vista consolidada del dominio administrativo para control y gestión.
- entidades: usuario, rol_administrativo, permiso, autorizacion, auditoria_evento, configuracion_parametro, catalogo_maestro
- criticidad: media
- sincronizable: no
- requiere_versionado: no
- requiere_lock: no
- genera_op_id: no
- genera_outbox: no
- puede_entrar_en_conflicto: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio administrativo.
- No reemplaza al catálogo maestro global de casos de uso del sistema.
- Los casos aquí listados se usan como apoyo a implementación y trazabilidad de servicios.
- Debe mantenerse alineado con SRV-ADM-001 a SRV-ADM-006 y con el DER administrativo.
