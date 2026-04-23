# EVT-ADM — Eventos del dominio Administrativo

## Objetivo
Catalogar los eventos administrativos relevantes del dominio para implementación, trazabilidad y observabilidad funcional.

## Alcance
Este catálogo cubre eventos de usuarios y acceso, seguridad y autorización, auditoría administrativa, configuración y parámetros, y catálogos maestros, sin reemplazar eventos técnicos de sincronización ni historiales especializados.

---

## A. Eventos de usuarios y acceso

### EVT-ADM-001 — Usuario creado
- codigo: usuario_creado
- descripcion: se registró un nuevo usuario administrativo.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-002 — Usuario modificado
- codigo: usuario_modificado
- descripcion: se actualizaron datos o estado de un usuario administrativo.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-003 — Usuario desactivado
- codigo: usuario_desactivado
- descripcion: un usuario administrativo fue desactivado o dado de baja lógica.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-004 — Usuario reactivado
- codigo: usuario_reactivado
- descripcion: un usuario administrativo volvió a estar activo.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-005 — Usuario bloqueado
- codigo: usuario_bloqueado
- descripcion: un usuario administrativo fue bloqueado para operar o autenticarse.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-006 — Usuario desbloqueado
- codigo: usuario_desbloqueado
- descripcion: un usuario administrativo bloqueado recuperó su capacidad operativa.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-007 — Usuario asociado a persona
- codigo: usuario_asociado_a_persona
- descripcion: se vinculó un usuario administrativo con una persona del sistema.
- origen_principal: ADM-DER
- entidad_principal: usuario
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-008 — Usuario asociado a sucursal
- codigo: usuario_asociado_a_sucursal
- descripcion: se habilitó o vinculó un usuario a una sucursal operativa.
- origen_principal: SRV-ADM-001
- entidad_principal: usuario_sucursal
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-009 — Credencial creada
- codigo: credencial_creada
- descripcion: se registró una credencial de usuario.
- origen_principal: SRV-ADM-001
- entidad_principal: credencial_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-010 — Credencial modificada
- codigo: credencial_modificada
- descripcion: se actualizó una credencial de usuario.
- origen_principal: SRV-ADM-001
- entidad_principal: credencial_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-011 — Credencial revocada
- codigo: credencial_revocada
- descripcion: una credencial dejó de ser válida por revocación.
- origen_principal: SRV-ADM-001
- entidad_principal: credencial_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-012 — Credencial restablecida
- codigo: credencial_restablecida
- descripcion: una credencial fue reseteada o restablecida.
- origen_principal: SRV-ADM-001
- entidad_principal: credencial_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-013 — Credencial bloqueada
- codigo: credencial_bloqueada
- descripcion: una credencial fue bloqueada para impedir autenticación.
- origen_principal: SRV-ADM-001
- entidad_principal: credencial_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-014 — Acceso validado
- codigo: acceso_validado
- descripcion: un intento de acceso fue validado.
- origen_principal: SRV-ADM-001
- entidad_principal: historial_acceso
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad_administrativa: sí
- observaciones: historial_acceso registra eventos de acceso; no reemplaza evento_auditoria.

### EVT-ADM-015 — Acceso rechazado
- codigo: acceso_rechazado
- descripcion: un intento de acceso fue rechazado.
- origen_principal: SRV-ADM-001
- entidad_principal: historial_acceso
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad_administrativa: sí
- observaciones: historial_acceso registra eventos de acceso; no reemplaza evento_auditoria.

### EVT-ADM-016 — Sesión iniciada
- codigo: sesion_iniciada
- descripcion: se abrió una nueva sesión administrativa.
- origen_principal: SRV-ADM-001
- entidad_principal: sesion_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-017 — Sesión cerrada
- codigo: sesion_cerrada
- descripcion: una sesión administrativa fue cerrada.
- origen_principal: SRV-ADM-001
- entidad_principal: sesion_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-018 — Sesión expirada
- codigo: sesion_expirada
- descripcion: una sesión administrativa expiró por política o inactividad.
- origen_principal: SRV-ADM-001
- entidad_principal: sesion_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

### EVT-ADM-019 — Login exitoso
- codigo: login_exitoso
- descripcion: se registró una autenticación exitosa de usuario.
- origen_principal: SRV-ADM-001
- entidad_principal: historial_acceso
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad_administrativa: sí
- observaciones: historial_acceso registra eventos de acceso; no reemplaza evento_auditoria.

### EVT-ADM-020 — Login fallido
- codigo: login_fallido
- descripcion: se registró un intento fallido de autenticación.
- origen_principal: SRV-ADM-001
- entidad_principal: historial_acceso
- tipo_evento: historizacion
- sincronizable: no
- genera_trazabilidad_administrativa: sí
- observaciones: historial_acceso registra eventos de acceso; no reemplaza evento_auditoria.

### EVT-ADM-021 — Logout manual
- codigo: logout_manual
- descripcion: se registró el cierre manual de una sesión por parte del usuario o administración.
- origen_principal: SRV-ADM-001
- entidad_principal: sesion_usuario
- tipo_evento: negocio
- sincronizable: no
- genera_trazabilidad_administrativa: sí

## B. Eventos de seguridad, roles, permisos y autorización

### EVT-ADM-022 — Rol de seguridad creado
- codigo: rol_seguridad_creado
- descripcion: se registró un nuevo rol de seguridad.
- origen_principal: SRV-ADM-002
- entidad_principal: rol_administrativo
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-023 — Rol de seguridad modificado
- codigo: rol_seguridad_modificado
- descripcion: se actualizaron datos o estado de un rol de seguridad.
- origen_principal: SRV-ADM-002
- entidad_principal: rol_administrativo
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-024 — Rol de seguridad desactivado
- codigo: rol_seguridad_desactivado
- descripcion: un rol de seguridad fue desactivado.
- origen_principal: SRV-ADM-002
- entidad_principal: rol_administrativo
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-025 — Permiso creado
- codigo: permiso_creado
- descripcion: se registró un nuevo permiso de seguridad.
- origen_principal: SRV-ADM-002
- entidad_principal: permiso
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-026 — Permiso modificado
- codigo: permiso_modificado
- descripcion: se actualizó un permiso existente.
- origen_principal: SRV-ADM-002
- entidad_principal: permiso
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-027 — Permiso desactivado
- codigo: permiso_desactivado
- descripcion: un permiso fue desactivado.
- origen_principal: SRV-ADM-002
- entidad_principal: permiso
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-028 — Permiso asignado a rol
- codigo: permiso_asignado_a_rol
- descripcion: un permiso fue asociado a un rol de seguridad.
- origen_principal: SRV-ADM-002
- entidad_principal: rol_permiso
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-029 — Permiso desasignado de rol
- codigo: permiso_desasignado_de_rol
- descripcion: un permiso fue removido de un rol de seguridad.
- origen_principal: SRV-ADM-002
- entidad_principal: rol_permiso
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-030 — Rol asignado a usuario
- codigo: rol_asignado_a_usuario
- descripcion: un rol de seguridad fue asignado a un usuario.
- origen_principal: SRV-ADM-002
- entidad_principal: usuario_rol
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-031 — Rol revocado de usuario
- codigo: rol_revocado_de_usuario
- descripcion: una asignación de rol fue revocada o dejada sin efecto.
- origen_principal: SRV-ADM-002
- entidad_principal: usuario_rol
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-032 — Rol asignado a usuario por sucursal
- codigo: rol_asignado_a_usuario_por_sucursal
- descripcion: un rol de seguridad fue asignado a un usuario con alcance de sucursal.
- origen_principal: SRV-ADM-002
- entidad_principal: usuario_rol
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-033 — Denegación explícita registrada
- codigo: denegacion_explicita_registrada
- descripcion: se registró una denegación explícita en un contexto de autorización.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-034 — Denegación explícita modificada
- codigo: denegacion_explicita_modificada
- descripcion: se modificó una denegación explícita existente.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-035 — Denegación explícita revocada
- codigo: denegacion_explicita_revocada
- descripcion: se revocó una denegación explícita previamente registrada.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-036 — Autorización evaluada
- codigo: autorizacion_evaluada
- descripcion: se resolvió una evaluación de autorización en un contexto administrativo.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: cuando_corresponda
- genera_trazabilidad_administrativa: sí

### EVT-ADM-037 — Acceso denegado por autorización
- codigo: acceso_denegado_por_autorizacion
- descripcion: una operación fue denegada por la política de autorización efectiva.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: cuando_corresponda
- genera_trazabilidad_administrativa: sí

### EVT-ADM-038 — Acceso habilitado por autorización
- codigo: acceso_habilitado_por_autorizacion
- descripcion: una operación fue habilitada tras la evaluación de autorización.
- origen_principal: SRV-ADM-003
- entidad_principal: autorizacion
- tipo_evento: negocio
- sincronizable: cuando_corresponda
- genera_trazabilidad_administrativa: sí

## C. Eventos de auditoría administrativa

### EVT-ADM-039 — Evento de auditoría registrado
- codigo: evento_auditoria_registrado
- descripcion: se registró un nuevo evento de auditoría administrativa.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: evento_auditoria es la entidad central; no se fusiona con historial_acceso.

### EVT-ADM-040 — Cambio administrativo registrado
- codigo: cambio_administrativo_registrado
- descripcion: se registró un cambio administrativo relevante con trazabilidad.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-041 — Cambio de usuario auditado
- codigo: cambio_usuario_auditado
- descripcion: se auditó un cambio relevante sobre un usuario administrativo.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-042 — Cambio de credencial auditado
- codigo: cambio_credencial_auditado
- descripcion: se auditó un cambio relevante sobre una credencial.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-043 — Cambio de sesión auditado
- codigo: cambio_sesion_auditado
- descripcion: se auditó un cambio relevante sobre una sesión administrativa.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-044 — Cambio de rol auditado
- codigo: cambio_rol_auditado
- descripcion: se auditó un cambio relevante sobre roles de seguridad.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-045 — Cambio de permiso auditado
- codigo: cambio_permiso_auditado
- descripcion: se auditó un cambio relevante sobre permisos.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-046 — Cambio de autorización auditado
- codigo: cambio_autorizacion_auditado
- descripcion: se auditó un cambio relevante sobre autorizaciones o denegaciones.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-047 — Cambio de configuración auditado
- codigo: cambio_configuracion_auditado
- descripcion: se auditó un cambio relevante sobre configuración general.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-048 — Cambio de parámetro auditado
- codigo: cambio_parametro_auditado
- descripcion: se auditó un cambio relevante sobre parámetros del sistema.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-049 — Cambio de catálogo auditado
- codigo: cambio_catalogo_auditado
- descripcion: se auditó un cambio relevante sobre catálogos maestros.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-050 — Evento de seguridad administrativa registrado
- codigo: evento_seguridad_administrativa_registrado
- descripcion: se registró un evento de auditoría asociado a seguridad administrativa.
- origen_principal: SRV-ADM-004
- entidad_principal: evento_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-051 — Objeto auditado vinculado
- codigo: objeto_auditado_vinculado
- descripcion: se vinculó un objeto auditado a un evento de auditoría administrativa.
- origen_principal: ADM-DER
- entidad_principal: objeto_auditado
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: objeto_auditado complementa el evento_auditoria.

### EVT-ADM-052 — Detalle de cambio de auditoría registrado
- codigo: detalle_cambio_auditoria_registrado
- descripcion: se registró un detalle específico de cambio dentro de un evento auditado.
- origen_principal: ADM-DER
- entidad_principal: detalle_cambio_auditoria
- tipo_evento: auditoria
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: detalle_cambio_auditoria complementa el evento_auditoria; no reemplaza historial_acceso.

## D. Eventos de configuración y parámetros

### EVT-ADM-053 — Configuración general creada
- codigo: configuracion_general_creada
- descripcion: se registró una nueva configuración general.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-054 — Configuración general modificada
- codigo: configuracion_general_modificada
- descripcion: se actualizó una configuración general existente.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-055 — Configuración general desactivada
- codigo: configuracion_general_desactivada
- descripcion: se desactivó una configuración general.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-056 — Parámetro de sistema creado
- codigo: parametro_sistema_creado
- descripcion: se registró un nuevo parámetro del sistema.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-057 — Parámetro de sistema modificado
- codigo: parametro_sistema_modificado
- descripcion: se actualizó un parámetro del sistema.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-058 — Parámetro de sistema desactivado
- codigo: parametro_sistema_desactivado
- descripcion: se desactivó un parámetro del sistema.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_parametro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-059 — Valor de parámetro creado
- codigo: valor_parametro_creado
- descripcion: se registró un nuevo valor de parámetro.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_contexto
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-060 — Valor de parámetro modificado
- codigo: valor_parametro_modificado
- descripcion: se actualizó un valor de parámetro existente.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_contexto
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-061 — Vigencia de valor de parámetro cerrada
- codigo: valor_parametro_vigencia_cerrada
- descripcion: se cerró la vigencia de un valor de parámetro.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_contexto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-062 — Valor de parámetro reemplazado
- codigo: valor_parametro_reemplazado
- descripcion: un valor de parámetro fue reemplazado por otro en nueva vigencia.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_contexto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-063 — Historial de parámetro registrado
- codigo: historial_parametro_registrado
- descripcion: se registró un hito de historización sobre un parámetro o su valor.
- origen_principal: SRV-ADM-005
- entidad_principal: configuracion_contexto
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: historial_parametro no reemplaza auditoría general; los cambios relevantes deben auditase también.

## E. Eventos de catálogos maestros

### EVT-ADM-064 — Catálogo maestro creado
- codigo: catalogo_maestro_creado
- descripcion: se registró un nuevo catálogo maestro.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_maestro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-065 — Catálogo maestro modificado
- codigo: catalogo_maestro_modificado
- descripcion: se actualizó un catálogo maestro existente.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_maestro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-066 — Catálogo maestro desactivado
- codigo: catalogo_maestro_desactivado
- descripcion: se desactivó un catálogo maestro.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_maestro
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-067 — Ítem de catálogo creado
- codigo: item_catalogo_creado
- descripcion: se registró un nuevo ítem de catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-068 — Ítem de catálogo modificado
- codigo: item_catalogo_modificado
- descripcion: se actualizó un ítem de catálogo existente.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-069 — Ítem de catálogo desactivado
- codigo: item_catalogo_desactivado
- descripcion: se desactivó un ítem de catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-070 — Ítem de catálogo habilitado por sucursal
- codigo: item_catalogo_habilitado_por_sucursal
- descripcion: un ítem de catálogo fue habilitado para uso en una sucursal.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: la disponibilidad por sucursal no redefine el ítem global.

### EVT-ADM-071 — Ítem de catálogo deshabilitado por sucursal
- codigo: item_catalogo_deshabilitado_por_sucursal
- descripcion: un ítem de catálogo fue deshabilitado para una sucursal.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: la disponibilidad por sucursal no redefine el ítem global.

### EVT-ADM-072 — Jerarquía de catálogo creada
- codigo: jerarquia_catalogo_creada
- descripcion: se registró una relación jerárquica de catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-073 — Jerarquía de catálogo modificada
- codigo: jerarquia_catalogo_modificada
- descripcion: se modificó una relación jerárquica de catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-074 — Jerarquía de catálogo desactivada
- codigo: jerarquia_catalogo_desactivada
- descripcion: se desactivó una relación jerárquica de catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-075 — Historial de catálogo registrado
- codigo: historial_catalogo_registrado
- descripcion: se registró un hito de historización sobre un catálogo o sus ítems.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_maestro
- tipo_evento: historizacion
- sincronizable: sí
- genera_trazabilidad_administrativa: sí
- observaciones: historial_catalogo no reemplaza auditoría general.

### EVT-ADM-076 — Ítem default asignado
- codigo: item_default_asignado
- descripcion: se asignó un ítem por defecto dentro de un catálogo cuando la política lo permite.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

### EVT-ADM-077 — Ítem default revocado
- codigo: item_default_revocado
- descripcion: se revocó la condición de ítem por defecto dentro de un catálogo.
- origen_principal: SRV-ADM-005
- entidad_principal: catalogo_item
- tipo_evento: negocio
- sincronizable: sí
- genera_trazabilidad_administrativa: sí

## F. Notas de compatibilidad transversal

- el dominio administrativo es compatible con op_id y trazabilidad distribuida
- una operación write sincronizable puede generar eventos observables en el dominio administrativo
- los eventos administrativos no reemplazan los eventos técnicos de sincronización
- sucursal e instalación participan como contexto de trazabilidad cuando corresponda

---

## Notas
- Este catálogo deriva del DEV-SRV y del DER administrativo.
- No reemplaza a la auditoría general ni a los historiales especializados.
- Debe mantenerse alineado con SRV-ADM-001 a SRV-ADM-006.
- Es base para trazabilidad, outbox y observabilidad administrativa del dominio.
