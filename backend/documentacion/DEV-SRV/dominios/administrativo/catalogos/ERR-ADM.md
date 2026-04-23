# ERR-ADM — Errores del dominio Administrativo

## Objetivo
Estandarizar los errores funcionales, de validación, integridad y concurrencia relevantes del dominio administrativo para su uso consistente en servicios y capas de exposición.

## Alcance
Este catálogo cubre errores de usuarios y acceso, seguridad y autorización, auditoría administrativa, configuración y parámetros, catálogos maestros y errores transversales aplicados al dominio administrativo.

---

## A. Errores de usuarios y acceso

### ERR-ADM-001 — Usuario no encontrado
- codigo: usuario_no_encontrado
- descripcion: no existe un usuario administrativo para el criterio indicado.
- tipo: funcional
- aplica_a: usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-002 — Usuario inactivo
- codigo: usuario_inactivo
- descripcion: el usuario existe pero se encuentra inactivo y no puede operar.
- tipo: funcional
- aplica_a: usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-003 — Usuario bloqueado
- codigo: usuario_bloqueado
- descripcion: el usuario se encuentra bloqueado y no puede autenticarse ni operar.
- tipo: funcional
- aplica_a: usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-004 — Credencial inválida
- codigo: credencial_invalida
- descripcion: la credencial informada no es válida para autenticar al usuario.
- tipo: validacion
- aplica_a: credencial_usuario, autenticacion
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-ADM-005 — Credencial revocada
- codigo: credencial_revocada
- descripcion: la credencial fue revocada y ya no puede ser utilizada.
- tipo: funcional
- aplica_a: credencial_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-006 — Credencial vencida
- codigo: credencial_vencida
- descripcion: la credencial se encuentra fuera de vigencia.
- tipo: funcional
- aplica_a: credencial_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-007 — Credencial bloqueada
- codigo: credencial_bloqueada
- descripcion: la credencial se encuentra bloqueada y no puede usarse.
- tipo: funcional
- aplica_a: credencial_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-008 — Login inválido
- codigo: login_invalido
- descripcion: la autenticación falló por datos de acceso inválidos.
- tipo: validacion
- aplica_a: autenticacion, historial_acceso
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-ADM-009 — Usuario sin credencial
- codigo: usuario_sin_credencial
- descripcion: el usuario no dispone de una credencial utilizable para autenticarse.
- tipo: funcional
- aplica_a: usuario, credencial_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-010 — Sesión no encontrada
- codigo: sesion_no_encontrada
- descripcion: no existe una sesión para el criterio indicado.
- tipo: funcional
- aplica_a: sesion_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-011 — Sesión inactiva
- codigo: sesion_inactiva
- descripcion: la sesión existe pero no se encuentra activa.
- tipo: funcional
- aplica_a: sesion_usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-012 — Usuario no habilitado en sucursal
- codigo: usuario_no_habilitado_en_sucursal
- descripcion: el usuario no posee habilitación operativa válida para la sucursal indicada.
- tipo: funcional
- aplica_a: usuario_sucursal, usuario, sucursal
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-013 — Conflicto usuario-persona
- codigo: conflicto_usuario_persona
- descripcion: la relación entre usuario y persona presenta inconsistencia o conflicto de vigencia.
- tipo: integridad
- aplica_a: usuario, persona, vínculo usuario-persona
- origen: DER
- es_reintento_valido: no

### ERR-ADM-014 — Nombre de usuario duplicado
- codigo: nombre_usuario_duplicado
- descripcion: el nombre de login ya se encuentra asignado a otro usuario.
- tipo: integridad
- aplica_a: usuario, credencial_usuario
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores de seguridad, roles y permisos

### ERR-ADM-015 — Rol no encontrado
- codigo: rol_no_encontrado
- descripcion: no existe un rol de seguridad para el criterio indicado.
- tipo: funcional
- aplica_a: rol_administrativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-016 — Permiso no encontrado
- codigo: permiso_no_encontrado
- descripcion: no existe un permiso para el criterio indicado.
- tipo: funcional
- aplica_a: permiso
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-017 — Rol duplicado
- codigo: rol_duplicado
- descripcion: ya existe un rol de seguridad equivalente al que se intenta registrar.
- tipo: integridad
- aplica_a: rol_administrativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-018 — Permiso duplicado
- codigo: permiso_duplicado
- descripcion: ya existe un permiso equivalente al que se intenta registrar.
- tipo: integridad
- aplica_a: permiso
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-019 — Asignación de rol inválida
- codigo: asignacion_rol_invalida
- descripcion: la asignación de rol no resulta válida para el usuario o contexto informado.
- tipo: validacion
- aplica_a: usuario_rol, rol_administrativo, usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-020 — Conflicto de asignación de rol
- codigo: conflicto_asignacion_rol
- descripcion: existe una inconsistencia o superposición inválida en las asignaciones vigentes de rol.
- tipo: integridad
- aplica_a: usuario_rol
- origen: DER
- es_reintento_valido: no

### ERR-ADM-021 — Permiso no asignado
- codigo: permiso_no_asignado
- descripcion: el permiso requerido no se encuentra asignado al rol o usuario en el contexto consultado.
- tipo: funcional
- aplica_a: rol_permiso, usuario_rol, permiso
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-022 — Acceso denegado
- codigo: acceso_denegado
- descripcion: el acceso solicitado no está permitido para el contexto actual.
- tipo: funcional
- aplica_a: autorizacion, seguridad_administrativa
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-023 — Autorización insuficiente
- codigo: autorizacion_insuficiente
- descripcion: la autorización efectiva es insuficiente para ejecutar la operación.
- tipo: funcional
- aplica_a: autorizacion, usuario, rol_administrativo
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-024 — Conflicto de autorización
- codigo: conflicto_autorizacion
- descripcion: existen condiciones contradictorias en la resolución de la autorización contextual.
- tipo: integridad
- aplica_a: autorizacion, solicitud_autorizacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-025 — Denegación explícita
- codigo: denegacion_explicita
- descripcion: la operación se encuentra denegada explícitamente por política administrativa.
- tipo: funcional
- aplica_a: autorizacion, solicitud_autorizacion
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-026 — Inconsistencia de roles y permisos
- codigo: inconsistencia_roles_permisos
- descripcion: la relación entre roles, permisos y asignaciones presenta inconsistencia funcional o estructural.
- tipo: integridad
- aplica_a: rol_administrativo, permiso, rol_permiso, usuario_rol
- origen: DER
- es_reintento_valido: no

## C. Errores de auditoría administrativa

### ERR-ADM-027 — Evento de auditoría inválido
- codigo: evento_auditoria_invalido
- descripcion: el evento de auditoría no cumple con la información mínima requerida.
- tipo: validacion
- aplica_a: auditoria_evento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-028 — Objeto auditado inexistente
- codigo: objeto_auditado_inexistente
- descripcion: el objeto referenciado por la auditoría no existe o no puede vincularse.
- tipo: funcional
- aplica_a: auditoria_evento, entidad_auditada
- origen: DER
- es_reintento_valido: no

### ERR-ADM-029 — Inconsistencia de evento de auditoría
- codigo: inconsistencia_evento_auditoria
- descripcion: el contenido del evento auditado resulta inconsistente con su contexto o tipo.
- tipo: integridad
- aplica_a: auditoria_evento
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-030 — Inconsistencia de contexto de auditoría
- codigo: inconsistencia_contexto_auditoria
- descripcion: el contexto técnico o administrativo informado para la auditoría no es coherente.
- tipo: integridad
- aplica_a: auditoria_contexto
- origen: SYS-DER
- es_reintento_valido: no

### ERR-ADM-031 — Usuario de auditoría inválido
- codigo: usuario_auditoria_invalido
- descripcion: el usuario asociado al evento auditado no es válido para el contexto informado.
- tipo: validacion
- aplica_a: auditoria_evento, usuario
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-032 — Sucursal de auditoría inválida
- codigo: sucursal_auditoria_invalida
- descripcion: la sucursal indicada en el evento auditado no es válida o no es coherente con el contexto.
- tipo: validacion
- aplica_a: auditoria_contexto, sucursal
- origen: SYS-DER
- es_reintento_valido: no

### ERR-ADM-033 — Instalación de auditoría inválida
- codigo: instalacion_auditoria_invalida
- descripcion: la instalación indicada en el evento auditado no es válida o no es coherente con la sucursal/contexto.
- tipo: validacion
- aplica_a: auditoria_contexto, instalacion
- origen: SYS-DER
- es_reintento_valido: no

## D. Errores de configuración y parámetros

### ERR-ADM-034 — Configuración no encontrada
- codigo: configuracion_no_encontrada
- descripcion: no existe una configuración general para el criterio indicado.
- tipo: funcional
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-035 — Parámetro no encontrado
- codigo: parametro_no_encontrado
- descripcion: no existe un parámetro del sistema para el criterio indicado.
- tipo: funcional
- aplica_a: configuracion_parametro
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-036 — Valor de parámetro inválido
- codigo: valor_parametro_invalido
- descripcion: el valor informado no cumple con la política o tipo esperado del parámetro.
- tipo: validacion
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-037 — Conflicto de parámetro
- codigo: conflicto_parametro
- descripcion: existe conflicto entre valores, alcances o vigencias del parámetro.
- tipo: integridad
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-038 — Inconsistencia de parámetro
- codigo: inconsistencia_parametro
- descripcion: la definición o el contexto del parámetro resulta inconsistente.
- tipo: integridad
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DER
- es_reintento_valido: no

### ERR-ADM-039 — Vigencia de parámetro inválida
- codigo: vigencia_parametro_invalida
- descripcion: la vigencia informada para el parámetro es inválida o incompatible con valores existentes.
- tipo: validacion
- aplica_a: configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-040 — Duplicación de parámetro
- codigo: duplicacion_parametro
- descripcion: ya existe un parámetro o valor equivalente para el alcance informado.
- tipo: integridad
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-041 — Configuración inconsistente
- codigo: configuracion_inconsistente
- descripcion: la configuración resultante no es consistente con el contexto o con otras definiciones administrativas.
- tipo: integridad
- aplica_a: configuracion_parametro, configuracion_contexto
- origen: DEV-SRV
- es_reintento_valido: no

## E. Errores de catálogos maestros

### ERR-ADM-042 — Catálogo no encontrado
- codigo: catalogo_no_encontrado
- descripcion: no existe un catálogo maestro para el criterio indicado.
- tipo: funcional
- aplica_a: catalogo_maestro
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-043 — Ítem de catálogo no encontrado
- codigo: item_catalogo_no_encontrado
- descripcion: no existe un ítem de catálogo para el criterio indicado.
- tipo: funcional
- aplica_a: catalogo_item
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-044 — Duplicación de ítem de catálogo
- codigo: duplicacion_item_catalogo
- descripcion: ya existe un ítem equivalente dentro del catálogo informado.
- tipo: integridad
- aplica_a: catalogo_item, catalogo_maestro
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-045 — Inconsistencia de jerarquía de catálogo
- codigo: inconsistencia_jerarquia_catalogo
- descripcion: la jerarquía de catálogo informada es inconsistente o inválida.
- tipo: integridad
- aplica_a: catalogo_item, catalogo_maestro
- origen: DER
- es_reintento_valido: no

### ERR-ADM-046 — Referencia de catálogo inválida
- codigo: referencia_catalogo_invalida
- descripcion: la referencia entre catálogo, ítem o contexto asociado no es válida.
- tipo: validacion
- aplica_a: catalogo_maestro, catalogo_item
- origen: DER
- es_reintento_valido: no

### ERR-ADM-047 — Conflicto de catálogo
- codigo: conflicto_catalogo
- descripcion: existe conflicto entre definiciones, disponibilidad o relaciones del catálogo.
- tipo: integridad
- aplica_a: catalogo_maestro, catalogo_item
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ADM-048 — Ítem de catálogo inactivo
- codigo: item_catalogo_inactivo
- descripcion: el ítem de catálogo existe pero no se encuentra disponible o activo.
- tipo: funcional
- aplica_a: catalogo_item
- origen: DEV-SRV
- es_reintento_valido: no

## F. Errores transversales (concurrencia, idempotencia, versionado)

### ERR-ADM-049 — Versión esperada inválida
- codigo: version_esperada_invalida
- descripcion: la versión esperada no coincide con la versión vigente de la entidad.
- tipo: concurrencia
- aplica_a: entidades write sincronizables del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-ADM-050 — Lock lógico activo
- codigo: lock_logico_activo
- descripcion: existe un lock lógico vigente que impide la operación solicitada.
- tipo: concurrencia
- aplica_a: entidades write sensibles del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-ADM-051 — Recurso bloqueado
- codigo: recurso_bloqueado
- descripcion: el recurso solicitado se encuentra bloqueado para modificación concurrente.
- tipo: concurrencia
- aplica_a: entidades write del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-ADM-052 — Op_id duplicado
- codigo: op_id_duplicado
- descripcion: la operación ya fue registrada previamente con el mismo op_id.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-ADM-053 — Op_id duplicado con payload distinto
- codigo: op_id_duplicado_con_payload_distinto
- descripcion: el mismo op_id fue reutilizado con un contenido distinto y constituye conflicto.
- tipo: integridad
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-ADM-054 — Conflicto de concurrencia
- codigo: conflicto_concurrencia
- descripcion: la operación no puede completarse por conflicto concurrente sobre la misma entidad o contexto.
- tipo: concurrencia
- aplica_a: entidades write del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: sí

### ERR-ADM-055 — Entidad no encontrada
- codigo: entidad_no_encontrada
- descripcion: la entidad requerida no existe en el contexto administrativo consultado.
- tipo: funcional
- aplica_a: entidades administrativas sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-ADM-056 — Entidad inactiva
- codigo: entidad_inactiva
- descripcion: la entidad existe pero se encuentra inactiva para la operación solicitada.
- tipo: funcional
- aplica_a: entidades administrativas sincronizables
- origen: CORE-EF
- es_reintento_valido: no

### ERR-ADM-057 — Inconsistencia de contexto técnico
- codigo: inconsistencia_contexto_tecnico
- descripcion: el contexto técnico mínimo de la operación es insuficiente, inválido o incoherente.
- tipo: validacion
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: no

### ERR-ADM-058 — Error de idempotencia
- codigo: error_idempotencia
- descripcion: no puede garantizarse la idempotencia esperada de la operación administrativa.
- tipo: concurrencia
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen: CORE-EF
- es_reintento_valido: sí

---

## Notas
- Este catálogo deriva del DEV-SRV y CORE-EF.
- No reemplaza validaciones de servicios, sino que las estandariza.
- Debe mantenerse alineado con SRV-ADM y reglas RN-ADM.
- Es base para manejo consistente de errores en API.
