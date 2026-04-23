# RN-ADM — Reglas del dominio Administrativo

## Objetivo
Definir las reglas canónicas del dominio administrativo como apoyo a implementación, validación funcional y revisión de consistencia del dominio.

## Alcance
Este catálogo cubre reglas sobre usuarios y acceso, seguridad y autorización, auditoría administrativa, configuración y parámetros, catálogos maestros y reglas transversales aplicadas al dominio, sin redefinir infraestructura transversal ni reglas de negocio de otros dominios.

## A. Usuarios y acceso

### RN-ADM-001 — Usuario y persona son conceptos distintos
- descripcion: la entidad usuario administrativo no reemplaza ni absorbe a la entidad persona; ambas deben mantenerse separadas conceptualmente.
- aplica_a: usuario, persona, vínculo usuario-persona
- origen_principal: ADM-DER
- observaciones: el dominio administrativo referencia a persona cuando corresponde, pero no redefine su semántica.

### RN-ADM-002 — Un usuario puede existir sin persona asociada
- descripcion: el alta y mantenimiento de usuario no exige necesariamente una persona asociada en todos los escenarios.
- aplica_a: usuario
- origen_principal: DEV-SRV

### RN-ADM-003 — Una persona puede existir sin usuario asociado
- descripcion: la existencia de una persona en el sistema no implica la existencia obligatoria de un usuario administrativo vinculado.
- aplica_a: persona, usuario
- origen_principal: ADM-DER

### RN-ADM-004 — El vínculo usuario-persona debe ser explícito y con vigencia
- descripcion: la relación entre usuario y persona debe resolverse mediante un vínculo identificable y temporalmente trazable cuando aplique.
- aplica_a: usuario, persona, vínculo usuario-persona
- origen_principal: ADM-DER

### RN-ADM-005 — No debe existir superposición inconsistente de vínculos principales vigentes
- descripcion: un usuario no debe quedar asociado en forma principal y simultánea a vínculos vigentes incompatibles según la política del dominio.
- aplica_a: usuario, vínculo usuario-persona
- origen_principal: ADM-DER

### RN-ADM-006 — El nombre de login debe ser único globalmente
- descripcion: la identidad de acceso utilizada para autenticación debe ser única en el universo del sistema.
- aplica_a: usuario, credencial_usuario
- origen_principal: DEV-SRV

### RN-ADM-007 — Un usuario dado de baja o bloqueado no autentica
- descripcion: un usuario inactivo, bloqueado o inválido no puede iniciar sesión ni generar autenticación efectiva.
- aplica_a: usuario, sesion_usuario, historial_acceso
- origen_principal: DEV-SRV

### RN-ADM-008 — Un usuario puede existir sin credencial activa temporalmente
- descripcion: la validez administrativa del usuario no depende de tener una credencial activa en todo momento.
- aplica_a: usuario, credencial_usuario
- origen_principal: DEV-SRV

### RN-ADM-009 — Una credencial revocada, vencida o bloqueada no autentica
- descripcion: la credencial debe estar vigente y habilitada para poder producir autenticación válida.
- aplica_a: credencial_usuario, sesion_usuario, historial_acceso
- origen_principal: DEV-SRV

### RN-ADM-010 — El historial de credenciales no se sobrescribe ni se borra
- descripcion: los cambios relevantes sobre credenciales deben preservar trazabilidad histórica y no destruir evidencia anterior.
- aplica_a: credencial_usuario, auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-011 — Toda sesión debe registrar usuario, sucursal operativa e instalación de origen
- descripcion: la sesión administrativa debe poder contextualizarse por usuario actor, sucursal operativa e instalación técnica.
- aplica_a: sesion_usuario
- origen_principal: DEV-SRV

### RN-ADM-012 — La instalación de la sesión debe ser coherente con la sucursal
- descripcion: cuando una sesión informa sucursal e instalación, ambas referencias deben ser compatibles entre sí.
- aplica_a: sesion_usuario, sucursal, instalacion
- origen_principal: SYS-DER

### RN-ADM-013 — Una sesión cerrada no reabre
- descripcion: una sesión finalizada no debe reactivarse; corresponde crear una nueva sesión.
- aplica_a: sesion_usuario
- origen_principal: DEV-SRV

### RN-ADM-014 — El historial de acceso registra eventos exitosos y fallidos
- descripcion: la trazabilidad de acceso debe contemplar intentos exitosos y fallidos para fines de control.
- aplica_a: historial_acceso
- origen_principal: DEV-SRV

### RN-ADM-015 — El historial de acceso no se modifica ni se reutiliza
- descripcion: cada evento de acceso debe preservarse como registro histórico inmutable y no reutilizable.
- aplica_a: historial_acceso
- origen_principal: DEV-SRV

### RN-ADM-016 — Un login exitoso puede enlazarse con sesión; un login fallido puede no tener sesión
- descripcion: la apertura de sesión deriva de autenticación válida, mientras que un intento fallido puede existir solo como evento de acceso.
- aplica_a: historial_acceso, sesion_usuario
- origen_principal: DEV-SRV

### RN-ADM-017 — La habilitación por sucursal no equivale a autorización por rol
- descripcion: la habilitación operativa del usuario en una sucursal y la autorización efectiva por seguridad deben resolverse como conceptos distintos.
- aplica_a: usuario_sucursal, usuario_rol, autorizacion
- origen_principal: DEV-SRV

## B. Seguridad, roles, permisos y autorización

### RN-ADM-018 — Los roles de seguridad no reemplazan roles de negocio
- descripcion: los roles administrativos de seguridad no deben confundirse ni fusionarse con roles funcionales de negocio definidos en otros dominios.
- aplica_a: rol_administrativo, permiso, usuario_rol
- origen_principal: DEV-SRV

### RN-ADM-019 — La autorización efectiva surge de roles, permisos, contexto y denegaciones explícitas
- descripcion: la autorización válida para operar debe resolverse a partir de la composición de asignaciones de seguridad, contexto y restricciones explícitas.
- aplica_a: autorizacion, solicitud_autorizacion, usuario_rol, rol_permiso
- origen_principal: DEV-SRV

### RN-ADM-020 — La denegación explícita tiene prioridad cuando la política así lo defina
- descripcion: cuando exista denegación explícita aplicable, su precedencia debe respetarse según la política del dominio.
- aplica_a: autorizacion, solicitud_autorizacion
- origen_principal: DEV-SRV

### RN-ADM-021 — La asignación de roles debe mantener trazabilidad y vigencia
- descripcion: toda asignación de rol a usuario debe ser trazable y, cuando corresponda, manejar vigencias.
- aplica_a: usuario_rol, rol_administrativo, usuario
- origen_principal: ADM-DER

### RN-ADM-022 — No debe existir duplicación inconsistente de asignaciones vigentes
- descripcion: no deben coexistir asignaciones vigentes redundantes o incompatibles para un mismo usuario, rol y contexto.
- aplica_a: usuario_rol, rol_permiso
- origen_principal: ADM-DER

### RN-ADM-023 — Permisos y roles de seguridad deben mantenerse separados de sucursal habilitada
- descripcion: la pertenencia o habilitación operativa por sucursal no constituye por sí misma una concesión de permisos de seguridad.
- aplica_a: usuario_sucursal, usuario_rol, rol_administrativo, permiso
- origen_principal: DEV-SRV

### RN-ADM-024 — La autorización contextual por sucursal no debe colapsarse con la habilitación operativa
- descripcion: el contexto de autorización por sucursal es una capa de control distinta de la mera habilitación del usuario en esa sucursal.
- aplica_a: autorizacion, usuario_sucursal, usuario_rol
- origen_principal: DEV-SRV

### RN-ADM-025 — Cambios relevantes de roles y permisos deben quedar auditados
- descripcion: toda alta, baja, modificación o asignación relevante sobre seguridad administrativa debe generar trazabilidad auditable.
- aplica_a: rol_administrativo, permiso, usuario_rol, rol_permiso, auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-026 — Toda operación write sobre seguridad sensible debe respetar control técnico transversal
- descripcion: las mutaciones sincronizables de roles, permisos y autorizaciones deben cumplir versión, op_id, outbox y demás controles aplicables.
- aplica_a: rol_administrativo, permiso, usuario_rol, rol_permiso, autorizacion
- origen_principal: CORE-EF
- observaciones: regla aplicada; no redefine CORE-EF.

## C. Auditoría administrativa

### RN-ADM-027 — Todo evento auditado relevante debe poder contextualizarse
- descripcion: un evento auditado relevante debe poder asociarse a usuario, sucursal, instalación y fecha/hora cuando el contexto exista.
- aplica_a: auditoria_evento, auditoria_contexto
- origen_principal: DEV-SRV

### RN-ADM-028 — Un evento auditado no debe borrarse
- descripcion: la auditoría administrativa debe preservar los eventos registrados y no eliminarlos por operaciones ordinarias.
- aplica_a: auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-029 — La auditoría debe registrar fecha y hora exactas
- descripcion: todo evento auditable debe incluir referencia temporal precisa suficiente para trazabilidad.
- aplica_a: auditoria_evento, auditoria_contexto
- origen_principal: SYS-DER

### RN-ADM-030 — Si existe sesión, el usuario del evento debe ser coherente con la sesión
- descripcion: cuando un evento administrativo se vincula a una sesión, el usuario actor debe ser consistente con dicha sesión.
- aplica_a: auditoria_evento, sesion_usuario, usuario
- origen_principal: ADM-DER

### RN-ADM-031 — Si se informa sucursal e instalación, ambas deben ser coherentes entre sí
- descripcion: el contexto técnico-administrativo del evento no debe contener referencias incompatibles entre sucursal e instalación.
- aplica_a: auditoria_contexto, sucursal, instalacion
- origen_principal: SYS-DER

### RN-ADM-032 — Un evento puede afectar múltiples objetos auditados
- descripcion: la auditoría administrativa debe permitir asociación conceptual con más de un objeto afectado cuando el caso lo requiera.
- aplica_a: auditoria_evento, entidad_auditada
- origen_principal: ADM-DER

### RN-ADM-033 — Los eventos que requieren objeto deben registrar al menos uno
- descripcion: cuando la naturaleza del evento exige objeto auditado, debe existir al menos una referencia de objeto asociada.
- aplica_a: auditoria_evento, entidad_auditada
- origen_principal: ADM-DER

### RN-ADM-034 — La auditoría administrativa debe poder enlazarse con op_id
- descripcion: las operaciones administrativas relevantes deben poder vincularse con su identidad técnica de operación cuando corresponda.
- aplica_a: auditoria_evento, auditoria_contexto
- origen_principal: CORE-EF
- observaciones: regla aplicada al dominio; la semántica de op_id proviene de CORE-EF.

### RN-ADM-035 — La auditoría debe poder referenciar objetos administrativos y transaccionales
- descripcion: la trazabilidad administrativa puede vincular tanto objetos propios del dominio como entidades de otros dominios afectadas por acciones administrativas.
- aplica_a: auditoria_evento, entidad_auditada
- origen_principal: ADM-DER

### RN-ADM-036 — Historial de acceso y auditoría administrativa no son equivalentes
- descripcion: los eventos de acceso no deben confundirse con auditoría administrativa, aunque puedan complementarse en trazabilidad.
- aplica_a: historial_acceso, auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-037 — La trazabilidad no debe perderse ante cambios sensibles
- descripcion: revocaciones, cambios de estado, modificaciones relevantes y denegaciones deben conservar rastro auditado suficiente.
- aplica_a: auditoria_evento, rol_administrativo, permiso, autorizacion, usuario, credencial_usuario, configuracion_parametro
- origen_principal: DEV-SRV

## D. Configuración y parámetros

### RN-ADM-038 — La configuración general no debe redefinir reglas estructurales del negocio
- descripcion: los parámetros administrativos pueden modular comportamiento, pero no alterar la semántica estructural de dominios funcionales.
- aplica_a: configuracion_parametro, configuracion_contexto
- origen_principal: DEV-SRV

### RN-ADM-039 — Los parámetros administrativos no deben duplicar catálogos o reglas congeladas de negocio
- descripcion: no deben trasladarse al dominio administrativo definiciones maestras que ya pertenecen de forma canónica a otros dominios.
- aplica_a: configuracion_parametro, catalogo_maestro
- origen_principal: DEV-SRV

### RN-ADM-040 — Los valores de parámetro deben manejar vigencia e historial cuando aplique
- descripcion: cuando la política del parámetro lo requiera, sus valores deben resolverse con trazabilidad temporal.
- aplica_a: configuracion_parametro, configuracion_contexto
- origen_principal: DEV-SRV

### RN-ADM-041 — No debe sobrescribirse destructivamente un valor histórico si la política es por vigencia
- descripcion: la modificación de valores parametrizados no debe destruir el historial cuando la gestión sea temporal.
- aplica_a: configuracion_parametro, configuracion_contexto
- origen_principal: DEV-SRV

### RN-ADM-042 — Debe poder resolverse el valor efectivo por contexto
- descripcion: el dominio debe permitir resolución consistente de valores efectivos según alcance global, sucursal o instalación.
- aplica_a: configuracion_parametro, configuracion_contexto, sucursal, instalacion
- origen_principal: DEV-SRV

### RN-ADM-043 — Sucursal e instalación informadas deben ser coherentes entre sí
- descripcion: cuando un valor parametrizado use simultáneamente sucursal e instalación, ambas referencias deben ser compatibles.
- aplica_a: configuracion_contexto, sucursal, instalacion
- origen_principal: SYS-DER

### RN-ADM-044 — Los cambios relevantes de configuración y parámetros deben quedar auditados
- descripcion: altas, bajas, cambios de vigencia y modificaciones relevantes deben preservar trazabilidad administrativa.
- aplica_a: configuracion_parametro, configuracion_contexto, auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-045 — Toda operación write sincronizable sobre parámetros debe respetar control técnico transversal
- descripcion: las mutaciones sincronizables de configuración deben respetar versión, op_id, outbox y demás requisitos transversales.
- aplica_a: configuracion_parametro, configuracion_contexto
- origen_principal: CORE-EF
- observaciones: regla aplicada; la infraestructura técnica se referencia, no se redefine.

## E. Catálogos maestros

### RN-ADM-046 — Los catálogos administrativos no deben duplicar catálogos de negocio ya congelados
- descripcion: el dominio administrativo solo debe alojar catálogos maestros bajo su responsabilidad y no replicar catálogos canónicos de otros dominios.
- aplica_a: catalogo_maestro, catalogo_item
- origen_principal: DEV-SRV

### RN-ADM-047 — Los ítems de catálogo deben mantener integridad jerárquica cuando aplique
- descripcion: la relación jerárquica entre ítems debe conservar consistencia estructural según el modelo del catálogo.
- aplica_a: catalogo_item, catalogo_maestro
- origen_principal: ADM-DER

### RN-ADM-048 — No debe haber autorreferencia inválida en jerarquías
- descripcion: un ítem no debe referenciarse a sí mismo ni generar jerarquías inválidas según la política de catálogo.
- aplica_a: catalogo_item
- origen_principal: ADM-DER

### RN-ADM-049 — Debe existir política consistente de disponibilidad, activación o default cuando corresponda
- descripcion: la activación y disponibilidad de catálogos e ítems debe resolverse con criterio uniforme según el modelo.
- aplica_a: catalogo_maestro, catalogo_item
- origen_principal: DEV-SRV

### RN-ADM-050 — Los cambios relevantes de catálogo deben mantener historial y trazabilidad
- descripcion: la evolución de catálogos maestros e ítems debe poder auditarse y reconstruirse conceptualmente.
- aplica_a: catalogo_maestro, catalogo_item, auditoria_evento
- origen_principal: DEV-SRV

### RN-ADM-051 — La asignación contextual por sucursal o instalación debe respetar coherencia entre ambos ejes
- descripcion: cuando la disponibilidad de catálogo se contextualiza por sucursal o instalación, ambas referencias deben ser consistentes entre sí.
- aplica_a: catalogo_maestro, catalogo_item, sucursal, instalacion
- origen_principal: SYS-DER

## F. Reglas transversales aplicadas al dominio administrativo

### RN-ADM-052 — Toda entidad sincronizable administrativa debe tener identidad global y versión cuando corresponda
- descripcion: las entidades administrativas sincronizables deben respetar identidad global y versionado según la infraestructura transversal.
- aplica_a: usuario, rol_administrativo, permiso, configuracion_parametro, catalogo_maestro, catalogo_item
- origen_principal: CORE-EF
- observaciones: regla aplicada al dominio administrativo.

### RN-ADM-053 — Toda operación write sincronizable debe usar op_id
- descripcion: las operaciones administrativas sincronizables deben ejecutarse con identidad técnica de operación.
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen_principal: CORE-EF

### RN-ADM-054 — Toda operación write sincronizable debe generar outbox en la misma transacción
- descripcion: cuando una mutación administrativa es sincronizable, el outbox debe quedar persistido coordinadamente con la mutación.
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen_principal: CORE-EF

### RN-ADM-055 — Debe existir control de lock lógico cuando aplique
- descripcion: las operaciones administrativas que lo requieran deben validar y respetar lock lógico según política transversal.
- aplica_a: operaciones write sensibles del dominio administrativo
- origen_principal: CORE-EF

### RN-ADM-056 — Mismo op_id con payload distinto constituye conflicto
- descripcion: la reutilización inconsistente de una identidad de operación debe tratarse como conflicto técnico.
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen_principal: CORE-EF

### RN-ADM-057 — No debe haber write sincronizable sin contexto técnico mínimo
- descripcion: toda mutación sincronizable debe disponer del contexto técnico requerido por la infraestructura transversal.
- aplica_a: operaciones write sincronizables del dominio administrativo
- origen_principal: CORE-EF

### RN-ADM-058 — Sucursal e instalación son conceptos distintos y no deben fusionarse
- descripcion: la dimensión organizativa de sucursal y la dimensión técnica de instalación deben mantenerse separadas.
- aplica_a: sucursal, instalacion, sesion_usuario, auditoria_contexto, configuracion_contexto
- origen_principal: SYS-DER

### RN-ADM-059 — Usuario y persona son conceptos distintos y no deben fusionarse
- descripcion: la identidad administrativa del usuario y la identidad civil o funcional de persona no deben colapsarse en una única entidad conceptual.
- aplica_a: usuario, persona
- origen_principal: ADM-DER

### RN-ADM-060 — El dominio administrativo se monta sobre el transaccional por referencia, contexto y trazabilidad
- descripcion: el dominio administrativo controla, referencia y audita entidades y operaciones, pero no redefine las entidades de negocio de otros dominios.
- aplica_a: dominio administrativo en relación con dominios funcionales
- origen_principal: DEV-SRV

## Notas
- Este catálogo deriva del DEV-SRV del dominio administrativo y del DER administrativo.
- No reemplaza a CORE-EF ni al DER global.
- Debe mantenerse alineado con SRV-ADM-001 a SRV-ADM-006.
- Las reglas aquí listadas son canónicas para implementación, validación y revisión del dominio administrativo.
