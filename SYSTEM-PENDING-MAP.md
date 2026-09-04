# Sistema Inmobiliario — Mapa Maestro de Pendientes

Revisión documental: 2026-09-04
Base auditada: `main` en `744465e88c346fd0e10b02a6f5b39be3b524578b`

## 1. Propósito y criterio de lectura

Este documento responde qué falta para completar el Sistema Inmobiliario sin
confundir diseño, soporte físico y capacidad operativa. Fue reconciliado contra
`AGENTS.md`, `DEVELOPER-ONBOARDING.md`, DEV-ARCH, DER, SQL, runtime, tests e
issues vigentes, en ese orden. Los documentos históricos y los artefactos de
diseño se usan sólo cuando no contradicen el sistema real.

Cada capacidad se describe en dos dimensiones independientes:

- **Clasificación arquitectónica**: indica qué naturaleza tiene la capacidad.
  Usa exclusivamente `NUCLEO_DOMINIO`, `SOPORTE_TRANSVERSAL` o
  `COMPATIBILIDAD_HEREDADA`.
- **Estado de implementación**: indica cuánto está materializado hoy. Usa los
  estados enumerados a continuación.

`COMPATIBILIDAD_HEREDADA` no significa por sí sola que algo esté activo o
completo: es una naturaleza arquitectónica. `LEGACY_VIGENTE`, en cambio, es el
estado operativo de un mecanismo histórico que todavía sobrevive por
compatibilidad.

Estados de implementación utilizados:

- `IMPLEMENTADO`: existe un circuito verificable en runtime, persistencia y tests.
- `IMPLEMENTADO_PARCIALMENTE`: existe una parte útil, pero falta una dimensión material.
- `PENDIENTE`: no existe la capacidad necesaria o resta completarla.
- `LEGACY_VIGENTE`: sigue activo por compatibilidad, pero no es baseline para código nuevo.
- `POST_MVP`: expansión deliberadamente innecesaria para la primera operación controlada.
- `BLOQUEADO`: depende de una decisión o incremento previo identificable.
- `DOCUMENTADO_NO_IMPLEMENTADO`: contrato o diseño sin circuito runtime completo.
- `NO_APLICA`: la capacidad no corresponde al área evaluada.

`Owner issue` identifica coordinación, no prueba implementación. La columna
distingue `OWNER_VIGENTE`, `OWNER_HISTORICO_COMPLETADO`, `COORDINADOR`,
`RELACIONADO_NO_OWNER` y `OWNER_ISSUE = FALTA`. Esta última categoría
significa que no se encontró un issue focal vigente; no autoriza a crear uno
desde este mapa.

## 2. Resumen ejecutivo

El sistema posee un backend funcional amplio en Personas, Inmobiliario,
Comercial, Locativo y Financiero; infraestructura avanzada de autenticación,
idempotencia e inbox; y una UI Flet útil en los circuitos principales. Aún no es
un producto completo ni una instalación distribuida lista para producción.
Persisten cuatro brechas sistémicas:

1. identidad/contexto y autorización no adoptados uniformemente: #461 y #536;
2. Sync portable sólo completo para capacidades puntuales, no para el grafo de negocio;
3. operación productiva sin workers/scheduler, backup/restore, upgrade y pruebas multi-base integrales;
4. frontend desigual: cubre consultas y flujos comerciales relevantes, pero no toda la administración ni todos los actos de negocio.

| Área | Madurez global | Lectura ejecutiva |
| --- | --- | --- |
| Técnico / CORE-EF / Sync | AVANZADO | Ledger, outbox/inbox y retry existen; adopción, scheduler, seguridad técnica y portabilidad siguen parciales. |
| Administrativo | AVANZADO | Usuarios, Bearer, sesión, autorización base y calendario existen; roles/scope y migración global están incompletos. |
| Personas | INTERMEDIO | CRUD relacionado amplio; faltan lifecycle, deduplicación/merge, Sync portable y seguridad uniforme. |
| Inmobiliario | INTERMEDIO | Modelo y APIs centrales operativos; faltan lifecycle, seguridad y Sync portable integral. |
| Comercial | AVANZADO | Reservas, ventas y PPV2 actual funcionan; faltan portabilidad, base común definitiva y actos posteriores completos. |
| Locativo | INTERMEDIO | Solicitud, reserva, contrato, activación, finalización/cancelación y actos básicos existen; garantías, ajustes, rescisión contractual, renovación, vencimiento automatizado y Sync portable no tienen cierre runtime. |
| Financiero | AVANZADO | Obligaciones, pagos, imputaciones, mora e índices tienen runtime; faltan reversión avanzada, PPV2 definitivo, seguridad y Sync. |
| Operativo | INTERMEDIO | Sucursal, Instalación, configuración y caja base existen; jornada, arqueo, fecha operativa e integración real están incompletos. |
| Gestión Operativa (GOP) | DISEÑADO_NO_IMPLEMENTADO | DEV-ARCH y DER del MVP están cerrados; no existen DEV-SRV, API, SQL ni runtime GOP. |
| Documental | INICIAL | Hay modelo preparatorio disperso; no existe subsistema operativo de archivos. |
| Analítico | DISEÑADO_NO_IMPLEMENTADO | Hay arquitectura/servicios documentados; no existen marts, KPIs, router ni runtime analítico. |
| Frontend | INTERMEDIO | Flet cubre Partes, Inmuebles, Contratos, Ventas y parte de Finanzas; faltan identidad/contexto reales y cobertura transversal. |
| Operación / Deploy / Infraestructura | INICIAL | Hay scripts locales y configuración básica; no hay evidencia de operación productiva multi-base recuperable. |

## 3. Técnico / CORE-EF / Sync

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Identidad humana | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Bearer, sesión revocable y `AuthenticatedPrincipal`. | Migrar todos los writes humanos y retirar `X-Usuario-Id`. | OWNER_VIGENTE: #461 | Coordinado con #536; adopción incremental por lotes | Sí, en los writes humanos afectados | CRÍTICA |
| Infraestructura de contexto local canónico | SOPORTE_TRANSVERSAL | IMPLEMENTADO | PR #537 integró `ResolvedLocalCommandContext`, resolución default-deny de Instalación local, `LOCAL_INSTALLATION_CODE` y corte temporal UTC del scope operativo. | Mantener el contrato reusable como baseline de los commands nuevos o migrados. | OWNER_VIGENTE: #536; RELACIONADO_NO_OWNER: #530 | Integrada en `main` por PR #537 | No por sí sola | ALTA |
| Adopción del contexto local por commands | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | La infraestructura común ya está integrada y disponible para adopción. | Migrar incrementalmente los commands afectados; `X-Instalacion-Id` queda sólo como aserción transicional y no como autoridad. | OWNER_VIGENTE: #536; coordinado con #461 | Por dominio/superficie | Sí, en migraciones afectadas | CRÍTICA |
| Sucursal/contexto | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Entidad, relaciones y alcance `usuario_sucursal`. | Resolver contexto canónico y scope por dominio sin confundirlo con Instalación. | OWNER_VIGENTE: #536; COORDINADOR Operativo: #248 | Coordinado con #461; adopción incremental | Sí, en los commands afectados | CRÍTICA |
| Contrato de headers CORE-EF vigente | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Helper común; `X-Op-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`, `If-Match-Version` cuando corresponde y `ErrorResponse` forman el baseline para código nuevo o migrado. `X-Instalacion-Id` es una aserción transicional, no la autoridad de identidad técnica. | Completar su adopción uniforme por lotes sin retirar los headers vigentes del contrato. | OWNER_VIGENTE: #461/#536; COORDINADOR histórico: #72 | Por dominio | Sí en endpoints aún no migrados | CRÍTICA |
| Compatibilidad legacy de headers | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Persisten `X-Usuario-Id` como identidad humana declarada, parseo manual, `X-Instalacion-Id` usado como autoridad y contratos históricos sin migrar. | Retirar esas interpretaciones heredadas al adoptar el helper y los principals canónicos. | OWNER_VIGENTE: #461/#536 | Contrato CORE-EF vigente | Sí en endpoints afectados | CRÍTICA |
| CAS/versionado | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | `version_registro`, `If-Match-Version` y CAS en flujos modernos. | Cobertura uniforme y evidencia endpoint→SQL→tests. | OWNER_VIGENTE: #107 | Migración por dominio | Sí, concurrencia | ALTA |
| Idempotencia | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Ledger #469/#470 y patrón claim/replay/conflict. | Adoptar en writes críticos restantes; no usar `op_id` embebido como sustituto. | OWNER_VIGENTE: #104 | Transaction ownership | Sí | ALTA |
| Transaction ownership | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Orquestadores modernos gobiernan commit/rollback; venta completa fue corregida. | Retirar commits internos de repositories/caminos legacy y auditar atomicidad por caso. | OWNER_VIGENTE de evidencia: #107; COORDINADOR legacy: #520; RELACIONADO_NO_OWNER: #63 | Por dominio | Sí | CRÍTICA |
| Outbox | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Tabla, publisher y emisión transaccional en circuitos modernos. | Cobertura transaccional por endpoint y reemplazo de eventos con payload incompleto o identidades locales. | OWNER_VIGENTE: #105; COORDINADOR legacy: #520 | Identidad portable | Sí para Sync | ALTA |
| Inbox / operation scope | SOPORTE_TRANSVERSAL | IMPLEMENTADO | Delivery, retained envelope, operation scope y deduplicación #511/#512. | Integrarlo a cada consumer nuevo; no existe scheduler productivo definitivo. | Owners de cada consumer | Worker productivo | Parcial | ALTA |
| Lease/fencing/takeover | SOPORTE_TRANSVERSAL | IMPLEMENTADO | Claim/reclaim, lease y fencing en baseline #512. | Ejecución productiva, métricas y runbooks. | OWNER_ISSUE = FALTA | Worker/observabilidad | Sí para operación distribuida | ALTA |
| Retry / `PENDING_DEPENDENCY` | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Lifecycle y entry point reusable. | Scheduler real e integración en consumers de negocio. | OWNER_HISTORICO_COMPLETADO: #511; OWNER_VIGENTE: cada consumer | Worker productivo | Sí para convergencia | ALTA |
| Portable identity/resolvers | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Usuario y calendario tienen circuito portable; varias entidades tienen `uid_global`. | `UNIQUE` físico y producer/consumer/resolver autoritativo para cada dependencia. | OWNERS_VIGENTES de fronteras: #534/#519; resto por dominio | Dominio dueño | Sí multi-base | CRÍTICA |
| Procedencia remota | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Metadata CORE-EF y contratos de recepción. | Evitar PK remota y client-controlled IDs en eventos/consumers legacy. | OWNERS_VIGENTES: #519/#534; COORDINADOR legacy: #520 | Identidad portable | Sí multi-base | CRÍTICA |
| Sucursal/Instalación portable | SOPORTE_TRANSVERSAL | DOCUMENTADO_NO_IMPLEMENTADO | Ambas poseen `uid_global`; identidad local resuelta. | Lifecycle/eventos autoritativos y resolución remota completa. | COORDINADOR: #248; #536 excluye expresamente lifecycle portable; OWNER_ISSUE = FALTA focal | Contrato local #536 + infraestructura Sync | Sí multi-base | ALTA |
| Worker/scheduler productivo | SOPORTE_TRANSVERSAL | PENDIENTE | Entry points invocables y lógica de retry. | Proceso supervisado, cadence, backoff, shutdown, health y recuperación. | OWNER_ISSUE = FALTA | Observabilidad/deploy | Sí multi-base | CRÍTICA |
| `origen=SISTEMA` | SOPORTE_TRANSVERSAL | BLOQUEADO | Contrato reconoce actor técnico. | Autenticación, autorización, principal técnico y auditoría sin falsificar Usuario humano. | OWNER_VIGENTE: #522 | Identidad técnica | Automatizaciones | ALTA |
| Autenticación técnica | SOPORTE_TRANSVERSAL | PENDIENTE | No hay modelo productivo cerrado. | Credencial/rotación/scope/revocación y vínculo con Instalación/proceso. | OWNER_VIGENTE: #522 | Secretos/deploy | Sí automatización y Sync online | ALTA |
| Temporalidad | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | UTC y temporalidad probada en capacidades modernas; PR #537 integró el corte UTC del scope operativo. | Política transversal; retirar `date.today()`/`datetime.now()` contractuales y deuda DTZ restante. | OWNER_VIGENTE: #365; RELACIONADO_NO_OWNER: #465 para deuda DTZ | DEPENDENCIA_IMPORTANTE para flujos de fecha contractual | Sólo en flujos concretos que exigen fecha reproducible | ALTA |
| Observabilidad técnica | SOPORTE_TRANSVERSAL | PENDIENTE | `worker_id`, estados y registros técnicos puntuales. | Métricas, correlación, alertas, dashboards y runbooks. | OWNER_ISSUE = FALTA | Workers/deploy | Sí operación productiva | ALTA |

## 4. Administrativo

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Usuario: alta/listado/detalle/baja lógica | NUCLEO_DOMINIO | IMPLEMENTADO | Alta, consultas, baja lógica, `uid_global`, versionado e idempotencia. | Completar adopción transversal y administración UI. | COORDINADOR: #249; owners históricos completados #259/#508 | #461 para adopción humana | Parcial | ALTA |
| Usuario: modificación/reactivación | NUCLEO_DOMINIO | PENDIENTE | No existe lifecycle runtime productivo completo para ambas operaciones. | Implementar modificación general, reactivación y sus invariantes. | COORDINADOR: #249; OWNER_ISSUE = FALTA focal | Seguridad y lifecycle portable | Sí para lifecycle completo | ALTA |
| Credenciales | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Hash, cambio de contraseña y credencial separada; no se sincroniza. | Políticas productivas de bootstrap, recuperación/rotación y secretos. | COORDINADOR: #249 | Deploy | Sí | ALTA |
| Sesiones/Bearer/principal | SOPORTE_TRANSVERSAL | IMPLEMENTADO | Login, sesión revocable, `/me`, dependency Bearer y principal canónico. | Migración de consumidores HTTP históricos. | OWNER_VIGENTE de migración: #461 | — | Sí | CRÍTICA |
| Roles/permisos | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | SQL, catálogos, relaciones y autorización GLOBAL reusable materializada por #443. | Administración completa, alcance efectivo y adopción fuera de Administrativo. | COORDINADOR: #249; OWNER_HISTORICO_COMPLETADO: #443; OWNER_VIGENTE de migración humana: #461 | Migración incremental #461 | Sí en endpoints afectados | CRÍTICA |
| `usuario_rol` / `usuario_sucursal` | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Relaciones, vigencia y helpers. | UI, lifecycle y enforcement uniforme por Sucursal. | COORDINADOR: #249; OWNER_ISSUE = FALTA focal | #536 | Sí | ALTA |
| Autorización global/por Sucursal | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Autorización GLOBAL reusable #443 y scope persistido. | Adopción transversal y autorización contextual uniforme por Sucursal/dominio. | OWNER_HISTORICO_COMPLETADO: #443; OWNER_VIGENTE de migración humana: #461; COORDINADOR: #249 | Contexto #536 en migraciones afectadas | Sí en endpoints afectados | CRÍTICA |
| Calendario comercial | NUCLEO_DOMINIO | IMPLEMENTADO | Singleton, programación, consulta y Sync portable. | Scheduler de activación productivo y observabilidad operacional. | OWNERS_HISTORICOS_COMPLETADOS: #425/#486; OWNER_ISSUE = FALTA para scheduler | Worker | Parcial | MEDIA |
| Parámetros | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | `parametro_sistema`/`valor_parametro` y endpoints relevantes. | Resolver NO CONFIRMADOS y retirar `configuracion_general` legacy. | OWNERS_VIGENTES: #435/#518 | Fecha/scope | Parcial | MEDIA |
| Sync Usuario: creación/desactivación | SOPORTE_TRANSVERSAL | IMPLEMENTADO | Producer/consumer portable de `usuario_creado` y `usuario_desactivado`, sin credenciales. | Mantener el contrato portable vigente. | OWNER_HISTORICO_COMPLETADO: #510 | Infraestructura inbox #512 | Parcial | MEDIA |
| Sync Usuario: modificación/reactivación | SOPORTE_TRANSVERSAL | PENDIENTE | No existe lifecycle portable productivo para estas operaciones. | Definir eventos, producer/consumer y convergencia si se incorporan. | COORDINADOR: #249; OWNER_ISSUE = FALTA focal | Modificación/reactivación local | Sí para lifecycle portable completo | MEDIA |
| Sync relaciones | SOPORTE_TRANSVERSAL | PENDIENTE | No hay circuito transversal completo de roles/permisos/scope. | Definir qué es portable, autoridad y resolución. | OWNER_ISSUE = FALTA | Sucursal portable | Sí multi-base | ALTA |
| Auditoría administrativa | NUCLEO_DOMINIO | PENDIENTE | Existen metadata CORE-EF e historiales técnicos puntuales. | Consulta administrativa especializada y legible. | OWNER_VIGENTE: #265; COORDINADOR: #249 | Fuentes administrativas estables | No para operación básica | MEDIA |
| Frontend administrativo | NUCLEO_DOMINIO | PENDIENTE | UI principal no ofrece gestión administrativa integral. | Usuarios, roles, permisos, sucursales, parámetros, calendario y auditoría. | COORDINADOR: #249; OWNER_ISSUE = FALTA focal | Seguridad/contexto | Sí operación delegada | ALTA |

## 5. Personas

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Humana/jurídica | NUCLEO_DOMINIO | IMPLEMENTADO | Modelo, CRUD y consultas. | Lifecycle backend y seguridad uniforme. | OWNER_VIGENTE de seguridad: #461; RELACIONADO_NO_OWNER frontend: #206; OWNER_ISSUE = FALTA para lifecycle backend | — | Parcial | ALTA |
| Documentos estructurados | NUCLEO_DOMINIO | IMPLEMENTADO | Tipos/números y gestión API. | No confundirlos con archivo digital; mejorar normalización y unicidad. | OWNER_VIGENTE frontend: #244; COORDINADOR frontend: #206; OWNER_ISSUE = FALTA backend focal | Documental para archivos | Parcial | ALTA |
| Domicilios/contactos | NUCLEO_DOMINIO | IMPLEMENTADO | CRUD backend y lectura UI. | Escritura UI completa y seguridad migrada. | OWNER_VIGENTE frontend: #244; OWNER_VIGENTE seguridad: #461 | #461 | No crítico | MEDIA |
| Relaciones/poderes | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Persona-relación y representación tienen SQL/API/tests. | Vigencia, autorización efectiva y uso homogéneo en actos comerciales/locativos. | RELACIONADO_NO_OWNER: #282 sólo para participantes locativos; OWNER_ISSUE = FALTA backend general | Seguridad | Sí en representación | ALTA |
| Roles de participación | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Catálogo y relaciones. | Retirar aliases write ambiguos `/roles-participacion`. | OWNER_VIGENTE: #517 | Clientes existentes | No | MEDIA |
| Deduplicación/normalización | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Resolver y señales `FUERTE/POSIBLE` en flujos puntuales. | Política canónica y cobertura de todos los canales de alta/importación. | OWNER_VIGENTE del importador: #330; COORDINADOR frontend: #206; OWNER_ISSUE = FALTA transversal | Importadores | Sí calidad de datos | ALTA |
| Merge de Personas | NUCLEO_DOMINIO | PENDIENTE | No existe un workflow seguro integral. | Diseño de reasignación, auditoría, conflicto y reversibilidad. | OWNER_ISSUE = FALTA | Deduplicación | No para MVP controlado | MEDIA |
| Lifecycle | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | `deleted_at`/metadata en estructuras. | Commands, invariantes, propagación y restauración si alguna vez se decide. | OWNER_ISSUE = FALTA | Sync | Sí para ciclo completo | ALTA |
| Auth/authz/idempotencia | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Helpers transversales disponibles; adopción desigual. | Migración completa de writes y scope. | OWNERS_VIGENTES: #461/#104 | #536 | Sí | CRÍTICA |
| Sync portable | SOPORTE_TRANSVERSAL | BLOQUEADO | `uid_global` parcial y payloads/eventos puntuales. | Lifecycle autoritativo de Persona/Documento, consumers y resolución remota. | OWNER_VIGENTE sólo para prerequisito PPV2: #534; OWNER_ISSUE = FALTA general | Unicidad física | Sí multi-base/ventas | CRÍTICA |
| Frontend | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Lista/ficha de Parte y datos relacionados. | Alta/edición completa, merge, poderes y acciones seguras. | OWNERS_VIGENTES frontend: #244/#319; COORDINADOR: #206 | Seguridad | Sí operación completa | ALTA |

## 6. Inmobiliario

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Inmueble/UF/desarrollos | NUCLEO_DOMINIO | IMPLEMENTADO | SQL, CRUD, consultas y UI relevante. | Lifecycle, autorización y portabilidad integral. | OWNER_VIGENTE de seguridad: #461; RELACIONADO_NO_OWNER frontend: #198; OWNER_ISSUE = FALTA para lifecycle/portabilidad backend | #536 en migraciones afectadas | Parcial | ALTA |
| Edificaciones/servicios | NUCLEO_DOMINIO | IMPLEMENTADO | APIs y persistencia, incluido XOR de owner. | Cobertura UI y Sync. | OWNER_ISSUE = FALTA | Inmueble portable | No crítico | MEDIA |
| Catastral/registral | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Datos estructurados y edición puntual. | Flujo completo, validación y documentación digital asociada. | OWNER_VIGENTE frontend: #198; OWNER_ISSUE = FALTA backend focal | Documental | Parcial | MEDIA |
| Disponibilidad/ocupación | NUCLEO_DOMINIO | IMPLEMENTADO | Modelo XOR y mutaciones integradas a venta/locativo. | Portabilidad y reconciliación interinstalación. | OWNERS_VIGENTES de fronteras: #519/#534; OWNER_ISSUE = FALTA general | Eventos dueños | Sí multi-base | CRÍTICA |
| Sucursal | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Asociación Inmueble–Sucursal. | Scope efectivo, lifecycle y resolución portable. | COORDINADOR: #248; OWNER_VIGENTE de contexto: #536 | Operativo | Sí | ALTA |
| Lifecycle/seguridad | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Metadata y guards no uniformes. | Commands canónicos, authz y CAS homogéneos. | OWNERS_VIGENTES de seguridad/evidencia: #461/#107; OWNER_ISSUE = FALTA lifecycle focal | #536 | Sí | ALTA |
| Sync portable | SOPORTE_TRANSVERSAL | PENDIENTE | `uid_global` no demuestra producer/consumer completo. | Eventos autoritativos de Inmueble/UF y dependencias resolubles. | OWNER_VIGENTE sólo para grafo PPV2: #534; OWNER_ISSUE = FALTA general | Sucursal/Instalación portable | Sí multi-base | CRÍTICA |
| Integración Comercial | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Reserva/venta afectan objetos y disponibilidad localmente. | Portabilidad y convergencia del grafo. | OWNER_VIGENTE de frontera PPV2: #534 | Personas portable | Sí multi-base | CRÍTICA |
| Integración Locativo | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Contrato, entrega/restitución y ocupación funcionan localmente. | Migrar la integración Sync cuyos payloads existentes contienen PK locales y carecen de identidades/resolvers portables suficientes. | OWNER_VIGENTE: #519 | Inmueble/UF portable | Sí multi-base | CRÍTICA |
| Frontend | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Listado, alta, ficha e importación Excel. | Toda acción relacionada, seguridad, lifecycle y estados consistentes. | OWNER_VIGENTE frontend: #198 | #461/#536 | Sí operación completa | ALTA |

## 7. Comercial

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Reservas | NUCLEO_DOMINIO | IMPLEMENTADO | Reserva multiobjeto, participantes y generación de venta. | Lifecycle completo y Sync portable. | RELACIONADO_NO_OWNER: #59; OWNER_VIGENTE de portabilidad: #534; OWNER_ISSUE = FALTA para lifecycle general | Personas/Inmobiliario portable | Parcial | ALTA |
| Venta desde reserva/directa | NUCLEO_DOMINIO | IMPLEMENTADO | Orquestadores atómicos y venta completa directa/desde reserva. | Idempotencia portable multi-entidad y seguridad migrada. | OWNERS_VIGENTES por alcance: #534/#104/#461 | Grafo portable | Sí multi-base | CRÍTICA |
| Compradores/vendedores | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Participación y compradores inline/locales. | Asociación portable, orden causal y alta autoritativa remota. | OWNER_VIGENTE de portabilidad PPV2: #534 | Personas portable | Sí multi-base | CRÍTICA |
| `cliente_comprador` legacy | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Sigue materializado en SQL y seed bajo ownership de Comercial; no es el modelo comercial principal ni reemplaza participantes/compradores actuales. | No expandirlo y contemplarlo explícitamente al evolucionar o migrar compradores. | OWNER_ISSUE = FALTA focal; ownership funcional: Comercial | Modelo actual de participantes/compradores | No para flujos nuevos | MEDIA |
| Representación | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Estructura de poderes/partes disponible. | Enforcement uniforme en confirmación y actos posteriores. | OWNER_ISSUE = FALTA | Personas/authz | Sí riesgo legal | ALTA |
| PPV2/cuotas | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Plan por bloques, preview/generación, obligaciones e indexación actual. | Contrato de base común, período objetivo y selector exacto. | OWNERS_VIGENTES por incremento: #427/#428/#429/#423 | Secuencia indicada | Sí para indexación definitiva | CRÍTICA |
| Base común | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | `INT-FIN-005` y PR #533 definen contrato. | SQL/runtime; PR #533 no está en `main` auditado y #427 sigue abierto. | OWNER_VIGENTE: #427 | #534 | Sí PPV2 portable | CRÍTICA |
| Configuración pactada de indexación | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | PPV2 contempla bloques del plan y la configuración contractual de ajuste. | Cerrar período, base, selector y regla pactados; consumir catálogo, valores, corridas, cálculo y aplicación gobernados por Financiero sin duplicar ese ownership. | OWNERS_VIGENTES por alcance: #423/#349/#348/#374/#405 | #427–#429; capacidades de indexación de Financiero | Sí circuito avanzado | ALTA |
| Obligaciones | SOPORTE_TRANSVERSAL | IMPLEMENTADO | Confirmación materializa deuda financiera en flujos soportados. | Portabilidad y semántica definitiva de `fecha_emision`. | RELACIONADO_NO_OWNER: #4; OWNER_VIGENTE de portabilidad PPV2: #534 | Financiero portable | Parcial | MEDIA |
| Instrumentos/cesión/escritura | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Tablas, endpoints y flujos puntuales. | Ciclos completos, seguridad, documentos reales y Sync portable. | OWNER_ISSUE = FALTA | Documental/personas | Sí completitud legal | ALTA |
| Rescisión | NUCLEO_DOMINIO | PENDIENTE | Tabla mínima y guards parciales. | Workflow conservador y efectos financieros. | OWNER_VIGENTE: #6 | Reversión/pagos | No para venta inicial | MEDIA |
| Sync venta/reserva | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Eventos/outbox existentes con referencias locales o payload incompleto. | Evento autoritativo, dependencias portables y consumers convergentes. | OWNER_VIGENTE: #534 | Personas/Inmobiliario/Financiero portable | Sí multi-base | CRÍTICA |
| Idempotencia multi-entidad | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Transacción local atómica y ledger reusable. | Definir/implementar operación distribuida completa de confirmación. | OWNER_VIGENTE para PPV2 portable: #534 | Eventos granulares/orden causal | Sí multi-base | CRÍTICA |
| Frontend | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Wizard, ventas, fichas y PPV2/indexación parcial. | #430/#431, importación histórica completa y actos posteriores. | OWNERS_VIGENTES frontend/importación por alcance: #430/#431/#207/#330–#335 | Backend pendiente | Sí uso completo | ALTA |

Cadena contractual confirmada: `#534 → grafo PPV2 portable`; `#427 → #428/#429 → #423`;
`#430/#431` cierran UI e integración, no sustituyen los incrementos backend.

## 8. Locativo

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Solicitud/reserva/contrato/partes | NUCLEO_DOMINIO | IMPLEMENTADO | APIs y persistencia del flujo principal. | Lifecycle, authz uniforme y UI de todas las mutaciones. | OWNER_VIGENTE de seguridad: #461; RELACIONADO_NO_OWNER: #282 para patrón contextual de partes | #536 en migraciones afectadas | Parcial | ALTA |
| Condiciones/canon/activación | NUCLEO_DOMINIO | IMPLEMENTADO | Condición económica, contrato y cronograma financiero locativo. | Fecha operativa y escenarios avanzados. | DEPENDENCIA_IMPORTANTE: #365; OWNER_ISSUE = FALTA para escenarios funcionales avanzados | Calendario/Financiero | Sí | ALTA |
| Garantías | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | DEV-SRV contempla la capacidad; no existe SQL específico funcional ni circuito application/API/tests. | Diseñar soporte físico definitivo y workflow de constitución, devolución/ejecución y UI. | OWNER_ISSUE = FALTA | Financiero/Documental | Sí completitud contractual | ALTA |
| Ajustes/indexación | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Existe soporte físico `ajuste_alquiler`; no existe circuito application/API/tests. | Implementar caso de uso, lifecycle, integración financiera y UX. | OWNER_ISSUE = FALTA | Índices/fecha operativa | Parcial | ALTA |
| Entrega/restitución | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Registro de Entrega y Restitución, efectos locales e integración funcional local con ocupación e Inmueble/UF. | Completar portabilidad, identidades resolubles, convergencia multi-instalación y migración de la integración Sync heredada. | OWNER_VIGENTE: #519 | Inmueble/UF portable | Sí multi-base | CRÍTICA |
| Sync legacy de Entrega/Restitución | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Producers/consumers emiten y consumen payloads existentes que referencian PK locales. | Migrarlos bajo #519 a identidades portables y resolvers autoritativos suficientes, preservando el ownership funcional en Locativo. | OWNER_VIGENTE: #519 | Inmueble/UF portable | Sí multi-base | CRÍTICA |
| Finalización/cancelación | NUCLEO_DOMINIO | IMPLEMENTADO | Services y endpoints permiten finalizar o cancelar contratos según estados soportados. | Completar adopción de seguridad y efectos avanzados cuando correspondan. | OWNER_VIGENTE de seguridad: #461; OWNER_ISSUE = FALTA funcional focal | Contexto #536 en migraciones afectadas | Parcial | ALTA |
| Rescisión contractual | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Existe soporte físico `rescision_finalizacion_alquiler`; no hay workflow application/API/tests de rescisión. | Implementar causal, efectos financieros/documentales, trazabilidad y UI. | OWNER_ISSUE = FALTA | Pagos/garantías/documentos | Sí ciclo contractual completo | ALTA |
| Renovación | NUCLEO_DOMINIO | PENDIENTE | No existe workflow runtime de renovación. | Definir e implementar nuevo contrato, continuidad, partes, condiciones y efectos. | OWNER_ISSUE = FALTA | Lifecycle locativo | Sí ciclo contractual completo | ALTA |
| Vencimiento automatizado | NUCLEO_DOMINIO | PENDIENTE | No existe ejecución productiva automática. | Definir transición y ejecutarla mediante worker/scheduler cuando corresponda. | OWNER_ISSUE = FALTA | DEPENDENCIA_IMPORTANTE: #365; worker productivo | No para ejecución manual | MEDIA |
| Scheduler | SOPORTE_TRANSVERSAL | PENDIENTE | No hay ejecución productiva definitiva. | Vencimientos, mora y tareas controladas. | OWNER_ISSUE = FALTA | #365/#522 | Sí automatización | ALTA |
| Sync portable | SOPORTE_TRANSVERSAL | BLOQUEADO | Baseline técnico disponible; la integración heredada de Entrega/Restitución está identificada por separado. | Eventos completos de agregado, identidades portables, resolvers autoritativos y dependencias convergentes. | OWNER_VIGENTE para entrega/restitución: #519; OWNER_ISSUE = FALTA para el resto del agregado | Inmobiliario portable | Sí multi-base | CRÍTICA |
| Seguridad/frontend | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Router amplio y ficha/listado de contratos. | Bearer/scope uniforme y acciones de ciclo completas. | OWNER_VIGENTE de seguridad: #461; OWNER_ISSUE = FALTA UI | #536 | Sí | CRÍTICA |

## 9. Financiero

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Obligaciones/composición/obligados | NUCLEO_DOMINIO | IMPLEMENTADO | Modelo y servicios para ventas, locativo, recuperos e impuestos. | Portabilidad completa y lifecycle avanzado. | OWNER_VIGENTE sólo para PPV2 portable: #534; OWNER_ISSUE = FALTA general | Identidades dueñas | Parcial | ALTA |
| Pagos/imputaciones | NUCLEO_DOMINIO | IMPLEMENTADO | Simulación, registro scoped/global, aplicaciones y estado de cuenta. | UI de pago real completa, conciliación y casos avanzados. | COORDINADOR frontend: #208; OWNER_ISSUE = FALTA para conciliación backend | Seguridad/caja | Sí operación | CRÍTICA |
| Reversión | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Anulaciones puntuales; no hay reversión universal segura. | Reversión/reimputación, auditoría y efectos downstream. | OWNER_VIGENTE sólo para indexación: #349; OWNER_ISSUE = FALTA general | Caja/documentos | Sí corrección | ALTA |
| Estado de cuenta/deuda | NUCLEO_DOMINIO | IMPLEMENTADO | Queries por Persona y consolidado operativo. | Reportes formales y seguridad transversal. | COORDINADOR frontend: #208; OWNER_ISSUE = FALTA para reportes formales | #461 | Sí | ALTA |
| Mora/punitorios | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Parámetros y liquidación/cálculo en circuitos soportados. | Scheduler, fecha operativa y excepciones completas. | DEPENDENCIA_IMPORTANTE: #365; OWNER_ISSUE = FALTA para scheduler/excepciones | Worker | Sí cobranza | ALTA |
| Índices/valores | NUCLEO_DOMINIO | IMPLEMENTADO | Catálogo, publicación y consulta aplicable. | Lifecycle portable y materialización de base/objetivo exactos. | OWNERS_VIGENTES por incremento: #428/#423/#534 | #427/#429 | Sí PPV2 | CRÍTICA |
| PPV2 | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Cronograma, bloques, indexación y materialización actual. | Base común definitiva, período objetivo, selector exacto y Sync. | OWNERS_VIGENTES por incremento: #427–#429/#423/#534 | Comercial portable | Sí | CRÍTICA |
| Cancelación anticipada | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Reglas y servicios históricos de referencia. | Caso de uso completo, efectos y tests integrales. | OWNER_ISSUE = FALTA | Pagos/reversión | No MVP inicial | MEDIA |
| Refinanciación/reprogramación | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Modelo/arquitectura previstos. | Contrato, SQL/runtime, trazabilidad e integración. | OWNER_ISSUE = FALTA | Reversión/versionado | No MVP inicial | MEDIA |
| NC/ND | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Conceptos de crédito/débito previstos. | Emisión, aplicación, comprobante y auditoría. | OWNER_ISSUE = FALTA | Documental/caja | No MVP inicial | MEDIA |
| Emisión/comprobantes | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Numeración y entidades preparatorias; algunas emisiones internas. | Comprobante operativo/fiscal integral y archivos. | OWNER_ISSUE = FALTA | Documental | Sí formalización | ALTA |
| Tesorería/cuentas/garantías monetarias | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Financiero posee estructuras y servicios parciales para cuentas, movimientos de tesorería, conciliación financiera y garantías monetarias contempladas por SRV-FIN-011. | Completar el lifecycle financiero y la conciliación sin absorber Caja física ni garantías contractuales locativas. | COORDINADOR: #208; OWNER_ISSUE = FALTA focal | Integración Pago ↔ movimiento físico de Caja | Sí control financiero | CRÍTICA |
| Scheduler/Sync/seguridad | SOPORTE_TRANSVERSAL | PENDIENTE | Piezas técnicas reutilizables; adopción puntual. | Workers, eventos portables y Bearer/scope uniforme. | DEPENDENCIA_IMPORTANTE: #365; OWNERS_VIGENTES por alcance: #534/#461; OWNER_ISSUE = FALTA para worker | #536/#522 | Sí productivo | CRÍTICA |
| Frontend | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Estado de cuenta y simulación en Parte; vistas PPV2. | Registro/reversión de pagos, caja, conciliación, mora e índices operativos completos. | COORDINADOR: #208; OWNER_VIGENTE de indexación UI: #348; OWNER_ISSUE = FALTA para pagos/caja UI | Backend/seguridad | Sí | CRÍTICA |

## 10. Operativo

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sucursal/Instalación | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | SQL/API y resolver local; relación 1:N conceptual. | Contexto canónico en writes, lifecycle portable y administración UI. | OWNER_VIGENTE del contexto: #536; COORDINADOR: #248; OWNER_ISSUE = FALTA para lifecycle portable | Coordinado incrementalmente con #461 | Sí en migraciones afectadas | CRÍTICA |
| Configuración local | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | `configuracion_local` y `LOCAL_INSTALLATION_CODE`. | Bootstrap seguro y operación por deployment. | COORDINADOR: #248; OWNER_ISSUE = FALTA focal | Deploy | Sí | ALTA |
| Caja/apertura/cierre/movimientos | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Caja base y endpoints de apertura/cierre/movimiento. | Arqueo, diferencias, reglas de jornada e integración Financiero. | COORDINADOR: #248; OWNERS_VIGENTES focales: #256/#257/#258 | DEPENDENCIA_IMPORTANTE sólo según flujo: #365 | Sí | CRÍTICA |
| Arqueo/diferencias | NUCLEO_DOMINIO | PENDIENTE | No se confirma circuito completo. | Conteo, conciliación, aprobación y auditoría. | OWNER_VIGENTE: #256; COORDINADOR: #248 | Caja; jornada sólo si el contrato final la exige | Sí control | ALTA |
| Jornada operativa | NUCLEO_DOMINIO | PENDIENTE | No existe modelo SQL/application/API/tests runtime confirmado. | Implementar apertura, consulta y cierre de jornada. | OWNER_VIGENTE: #257; COORDINADOR: #248 | Contexto Sucursal/Instalación | Sí para jornada formal; no requiere worker para ejecución manual | CRÍTICA |
| Fecha operativa | SOPORTE_TRANSVERSAL | PENDIENTE | Los flujos conservan fechas explícitas o reloj local según el caso. | Definir y proveer fecha operativa transversal reproducible. | OWNER_VIGENTE: #365 | DEPENDENCIA_IMPORTANTE para flujos contractuales concretos | No es blocker transversal absoluto | ALTA |
| Lectura Financiero → Caja | SOPORTE_TRANSVERSAL | PENDIENTE | Ownership separado y datos financieros consultables. | Exponer lectura operativa sin absorber lógica Financiera. | OWNER_VIGENTE: #258; COORDINADOR: #248 | Caja e interfaces read-like de Financiero | No para caja manual básica | ALTA |
| Integración pago ↔ movimiento físico | SOPORTE_TRANSVERSAL | PENDIENTE | Caja Operativa y pagos Financieros existen separados. | Definir trazabilidad/integración sin fusionar ownership. | RELACIONADO_NO_OWNER: #258 sólo cubre lectura; OWNER_ISSUE = FALTA para integración write | Caja/identidad/transacción | Sí para control financiero-operativo integral | CRÍTICA |
| Lifecycle/Sync/multi-instalación | SOPORTE_TRANSVERSAL | PENDIENTE | `uid_global` y metadata no constituyen lifecycle portable. | Eventos, consumers y resolución autoritativa. | COORDINADOR: #248; #536 excluye lifecycle; OWNER_ISSUE = FALTA focal | Infra Sync | Sí multi-base | CRÍTICA |
| Contexto frontend/seguridad | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Headers/hardcodes históricos; la infraestructura canónica de PR #537 ya está integrada. | Adoptar sesión, Sucursal elegible e Instalación backend-authoritative mediante #536/#461. | OWNERS_VIGENTES por alcance: #461/#536 | Infraestructura #537 integrada; adopción incremental | Sí | CRÍTICA |

## 11. Gestión Operativa (GOP)

### MVP

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEV-ARCH/DER | NUCLEO_DOMINIO | IMPLEMENTADO | `DEV-ARCH-GOP-001` y DER de Tarea/Comentario/Historial. | Mantener alineación durante implementación. | OWNERS_HISTORICOS_COMPLETADOS: #523/#528 | — | No | — |
| DEV-SRV | NUCLEO_DOMINIO | PENDIENTE | Arquitectura define frontera e invariantes. | Diseñar casos de uso y transacciones. | Próximo incremento; OWNER_ISSUE = FALTA | DEV-ARCH/DER | Sí GOP | ALTA |
| DEV-API | NUCLEO_DOMINIO | BLOQUEADO | No existe contrato API GOP. | Definir luego de DEV-SRV. | OWNER_ISSUE = FALTA | DEV-SRV | Sí GOP | ALTA |
| SQL/runtime/tests/frontend GOP | NUCLEO_DOMINIO | BLOQUEADO | No existen tablas ni código GOP. | Implementar Tarea/Comentario/Historial, casos de uso, persistencia, tests funcionales y frontend humano. | OWNER_ISSUE = FALTA | DEV-SRV/API; #461/#536 | Sí GOP | ALTA |
| Integración Sync GOP | SOPORTE_TRANSVERSAL | BLOQUEADO | No existe integración portable GOP con la infraestructura Sync vigente. | Definir el payload funcional bajo semántica GOP e integrarlo con outbox/inbox, envelope, procedencia técnica, transporte, retry y resolución de dependencias. | OWNER_ISSUE = FALTA | DEV-SRV/API; #461/#536; infraestructura Sync vigente | Sí GOP portable | ALTA |

### Post-MVP

Alertas, recordatorios, recurrencia, subtareas, dependencias, equipos, Kanban,
SLA, workflows, adjuntos, automatizaciones, mora e integraciones automáticas son
`POST_MVP` y están coordinados por #527. `origen=SISTEMA` depende además de #522.

## 12. Documental

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Documento lógico/versionado/asociación | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | Tablas preparatorias y DEV-SRV. | Servicios, invariantes, endpoints y tests. | OWNER_ISSUE = FALTA | Seguridad/ownership | Sí documentos reales | ALTA |
| Archivo físico/hash/integridad | NUCLEO_DOMINIO | PENDIENTE | `archivo_digital` en SQL no prueba storage operativo. | Backend de objetos, hash, malware policy, retención y verificación. | OWNER_ISSUE = FALTA | Infra/secretos | Sí | CRÍTICA |
| Upload/download/permisos | NUCLEO_DOMINIO | PENDIENTE | No existe subsistema integral. | Streaming, límites, autorización por entidad y auditoría. | OWNER_ISSUE = FALTA | #461/#536 | Sí | CRÍTICA |
| Numeración/emisión | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Estructuras de numeración/emisión. | Casos de uso transversales y documentos materializados. | OWNER_ISSUE = FALTA | Financiero/Comercial | Parcial | ALTA |
| Persona/Inmueble/contrato/escritura/comprobante | SOPORTE_TRANSVERSAL | DOCUMENTADO_NO_IMPLEMENTADO | Datos estructurados y asociaciones previstas. | Archivos, versiones, permisos y presentación UI. | OWNER_ISSUE = FALTA | Dominios dueños | Sí completitud formal | ALTA |
| Sync/offline | SOPORTE_TRANSVERSAL | POST_MVP | No hay transferencia binaria portable productiva. | Protocolo de blobs, deduplicación, integridad, cuotas y recuperación. | OWNER_ISSUE = FALTA | Sync productivo | No MVP controlado | MEDIA |
| Frontend | NUCLEO_DOMINIO | PENDIENTE | Secciones pueden mostrar datos, no gestión documental real. | Carga, descarga, versiones, permisos y asociación. | OWNER_ISSUE = FALTA | API documental | Sí | ALTA |

## 13. Analítico

Todo el dominio es read-only por arquitectura. No debe absorber reglas ni writes
de los dominios productores. Cualquier materialización, caché persistente o
precomputación queda fuera de su núcleo y bajo ownership Técnico/Infraestructura.

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arquitectura/servicios | NUCLEO_DOMINIO | DOCUMENTADO_NO_IMPLEMENTADO | DEV-ARCH y catálogo DEV-SRV. | Definir MVP y contratos de corte/scope. | OWNER_ISSUE = FALTA | Fuentes estables | No | MEDIA |
| KPIs/métricas/snapshots lógicos | NUCLEO_DOMINIO | PENDIENTE | Queries operativas aisladas. | Definiciones, lineage, cortes y tests; los snapshots de esta fila son read-like y no producen persistencia propia. | OWNER_ISSUE = FALTA | Fecha operativa | No MVP | MEDIA |
| Vistas/consultas/series analíticas | NUCLEO_DOMINIO | PENDIENTE | No hay capa SQL analítica propia. | Definir consultas, vistas ordinarias y series que consuman fuentes estables exclusivamente en lectura. | OWNER_ISSUE = FALTA | Fuentes estables | No MVP | MEDIA |
| Materializaciones/cachés persistentes | SOPORTE_TRANSVERSAL | PENDIENTE | No existe materialización ni caché persistente analítica implementada. | Si se adopta, definir precomputación, refresh y consistencia bajo ownership Técnico/Infraestructura; Analítico sólo consume el resultado en lectura. | OWNER_ISSUE = FALTA | Scheduler/infraestructura | No MVP | MEDIA |
| Ventas/cobranzas/mora/alquileres/disponibilidad/caja/sucursales | NUCLEO_DOMINIO | PENDIENTE | Datos fuente existen con madurez desigual. | Modelos de lectura sin duplicar ownership. | OWNER_ISSUE = FALTA | Dominios productores | No MVP | MEDIA |
| Dashboards/exportación | NUCLEO_DOMINIO | PENDIENTE | No existe frontend analítico. | API, exportación y UX. | OWNER_ISSUE = FALTA | KPIs | No MVP | BAJA |
| Consolidación multi-instalación | NUCLEO_DOMINIO | BLOQUEADO | Sync de fuentes no está completo. | Semántica de corte y consolidación convergente. | OWNER_ISSUE = FALTA | Sync productivo | No MVP local | MEDIA |

## 14. Frontend transversal

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Autenticación/sesión | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Backend listo; cliente conserva adopción desigual. | Login/sesión/logout y bearer uniforme sin persistencia insegura. | OWNER_VIGENTE de migración humana: #461 | Administrativo | Sí | CRÍTICA |
| Contexto canónico Sucursal/Instalación | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | PR #537 integró el contrato canónico y la resolución backend-authoritative de Instalación; `X-Instalacion-Id` permanece sólo como aserción transicional. | Completar el selector de Sucursal elegible/autorizada y su adopción con sesión y contexto operacional en el frontend mediante #536/#461. | OWNERS_VIGENTES por alcance: #536/#461 | Infraestructura integrada; migraciones incrementales | Sí | CRÍTICA |
| Compatibilidad legacy de frontend/contexto | COMPATIBILIDAD_HEREDADA | LEGACY_VIGENTE | Persisten shell/config y headers históricos, hardcodes, selección libre de Instalación y uso de `X-Instalacion-Id` como autoridad. | Migrar esas superficies al contexto canónico sin retirar el header vigente usado como aserción. | OWNERS_VIGENTES por alcance: #536/#461 | Contexto canónico Sucursal/Instalación | Sí | CRÍTICA |
| `op_id`/CAS | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | ApiClient y flujos modernos los generan/usan. | Política uniforme de retries, replay y refresh por conflicto. | OWNERS_VIGENTES por alcance: #104/#107 | Endpoints migrados | Sí confiabilidad | ALTA |
| Manejo de errores | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Componentes de estado/error y parseo puntual. | `ErrorResponse` uniforme, 401/403/409/422 y recuperación UX. | OWNER_ISSUE = FALTA | Backend uniforme | Sí | ALTA |
| Autorización/visibilidad | SOPORTE_TRANSVERSAL | PENDIENTE | Navegación no refleja permisos/scope integralmente; #443 ya materializó sólo infraestructura GLOBAL backend. | Ocultar/bloquear por permiso sin sustituir enforcement backend. | OWNER_VIGENTE de migración humana: #461; OWNER_HISTORICO_COMPLETADO: #443; COORDINADOR Administrativo: #249 | Roles/scope | Sí | CRÍTICA |
| Personas/Inmobiliario | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Listas, fichas y altas relevantes. | Lifecycle, relaciones, poderes y acciones completas. | OWNERS_VIGENTES frontend por alcance: #198/#206/#244 | Seguridad | Sí | ALTA |
| Comercial/Financiero | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Wizard, ventas, PPV2, estado de cuenta y simulación. | Roadmap #430/#431, pagos reales y actos posteriores. | OWNERS_VIGENTES/COORDINADORES frontend por alcance: #207/#208/#430/#431 | Backend pendiente | Sí | CRÍTICA |
| Locativo/Operativo/Administrativo | NUCLEO_DOMINIO | IMPLEMENTADO_PARCIALMENTE | Contratos visibles; cobertura operacional limitada. | Mutaciones completas y administración/caja/jornada. | COORDINADORES: #248/#249; OWNER_ISSUE = FALTA UI focal | Contexto/security | Sí | CRÍTICA |
| GOP/Documental/Analítico | NUCLEO_DOMINIO | PENDIENTE | No existen módulos funcionales. | Implementar después de sus contratos/backend. | COORDINADOR sólo post-MVP GOP: #527; OWNER_ISSUE = FALTA para MVP GOP/Documental/Analítico | Dominios respectivos | No MVP core salvo documental mínimo | MEDIA |

## 15. Operación, deploy e infraestructura productiva

| Capacidad | Clasificación | Estado | Qué existe hoy | Qué falta | Owner issue | Dependencias | Bloquea uso real | Prioridad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Configuración/bootstrap/base inicial | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | `.env.example`, settings y scripts de reset DEV/TEST. | Provisionamiento idempotente por instalación y usuario inicial seguro. | OWNER_ISSUE = FALTA | #536/secretos | Sí | CRÍTICA |
| Workers/scheduler | SOPORTE_TRANSVERSAL | PENDIENTE | Entry points y lógica invocable. | Servicio supervisado para inbox, retry, calendario, mora y vencimientos. | OWNER_ISSUE = FALTA | #522/#365 | Sí | CRÍTICA |
| Sync real entre bases | SOPORTE_TRANSVERSAL | BLOQUEADO | Protocolo y consumers puntuales. | Transporte, coordinación, pruebas E2E multi-base y resolución de dependencias de negocio. | OWNERS_VIGENTES sólo de fronteras: #519/#534; OWNER_ISSUE = FALTA para transporte/operación transversal | Portable graph | Sí multi-instalación | CRÍTICA |
| Backup/restore | SOPORTE_TRANSVERSAL | DOCUMENTADO_NO_IMPLEMENTADO | DEV-SRV técnico menciona recuperación. | Scripts, cifrado, retención, restore probado y runbook. | OWNER_ISSUE = FALTA | Storage/secretos | Sí producción | CRÍTICA |
| Upgrade/migrations | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | SQL base y patches/reset ordenados. | Mecanismo productivo versionado, rollback/forward fix y compatibilidad. | OWNER_ISSUE = FALTA | Packaging | Sí producción | CRÍTICA |
| Logging/observabilidad | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Logs y tablas técnicas puntuales. | Correlación, métricas, alertas, privacidad y health de workers. | OWNER_ISSUE = FALTA | Deploy | Sí soporte | ALTA |
| Recuperación de fallos | SOPORTE_TRANSVERSAL | IMPLEMENTADO_PARCIALMENTE | Idempotencia, retry y fencing reducen riesgo local. | Runbooks de caída, disco, corrupción, cola atascada y desastre. | OWNER_ISSUE = FALTA | Backup/observabilidad | Sí | CRÍTICA |
| Packaging/deployment/desktop update | SOPORTE_TRANSVERSAL | PENDIENTE | Arranque local documentado. | Artefactos firmados, instalación, servicio backend, actualización y rollback. | OWNER_ISSUE = FALTA | Upgrade/secretos | Sí | CRÍTICA |
| Pruebas multi-base | SOPORTE_TRANSVERSAL | PENDIENTE | Tests PostgreSQL y Sync focales. | Matriz real con dos o más bases, pérdida/reorden/replay/takeover y recuperación. | OWNER_ISSUE = FALTA | Transporte/workers | Sí multi-base | CRÍTICA |
| Seguridad de secretos | SOPORTE_TRANSVERSAL | PENDIENTE | Settings y hashes de credenciales. | Vault/almacén OS, rotación, mínimos privilegios y exclusión de logs/backups. | OWNER_ISSUE = FALTA | Deployment | Sí producción | CRÍTICA |

## 16. Horizontes de entrega

| Horizonte | Capacidades mínimas |
| --- | --- |
| Necesario para sistema utilizable | Login/sesión frontend; identidad humana no spoofeable en writes usados; contexto Sucursal/Instalación confiable; autorización mínima; flujos UI de Personas/Inmueble/Venta/Contrato/Pago; errores recuperables. |
| Necesario para MVP operativo | Lo anterior; caja/apertura/cierre controlados; fecha operativa donde el contrato la requiera; garantías locativas todavía no implementadas y demás actos indispensables; pagos/imputaciones; backup/restore y deploy actualizable para operación real; auditoría básica. GOP humano puede avanzar en paralelo una vez cerrados sus contratos y contexto humano/local, sin esperar multi-instalación completa. |
| Necesario para multi-instalación productiva | Identidades portables únicas; lifecycle autoritativo de dependencias; #519/#534; workers y transporte; pruebas multi-base; observabilidad, retry y recuperación. |
| Necesario para sistema funcionalmente completo | Ciclos legales Comercial/Locativo; reversión, refinanciación, NC/ND y emisión; Documental real; administración integral; frontend de todos los actos. |
| POST-MVP | GOP avanzado, Analítico avanzado, automatizaciones `SISTEMA`, Documental offline completo, workflows, SLA, Kanban, reporting sofisticado y expensas formales (#3). |

## 17. Bloqueadores y dependencias transversales

| Pendiente | Clasificación | Dominios afectados | Owner | Qué habilita / límite |
| --- | --- | --- | --- | --- |
| Identidad humana legacy | BLOQUEADOR_REAL | Writes humanos afectados y frontend | OWNER_VIGENTE: #461 | Usuario efectivo confiable y retiro de `X-Usuario-Id`; la migración es incremental, no un gate único para todo avance. |
| Adopción del contexto local canónico | BLOQUEADOR_REAL | Commands incluidos en cada migración | OWNER_VIGENTE: #536; infraestructura aportada por PR #537 ya integrada | Procedencia y contexto canónicos en los lotes afectados; no exige cerrar toda #461 antes de avanzar. |
| Entrega/Restitución portable | BLOQUEADOR_REAL | Locativo e Inmobiliario en esa frontera Sync | OWNER_VIGENTE: #519 | Convergencia de esos actos sin PK remota. |
| Grafo PPV2 portable | BLOQUEADOR_REAL | Comercial, Personas, Inmobiliario y Financiero involucrados | OWNER_VIGENTE: #534 | Habilita PPV2 portable y el escenario distribuido de #427. |
| Fecha operativa | DEPENDENCIA_IMPORTANTE | Comercial, Locativo, Financiero y Operativo según caso | OWNER_VIGENTE: #365 | Fechas contractuales reproducibles; sólo bloquea flujos concretos cuyo contrato la requiera. |
| Transaction ownership legacy | DEUDA_NO_BLOQUEANTE | Caminos históricos de varios dominios | OWNER_VIGENTE de evidencia: #107; COORDINADOR legacy: #520; owners focales | Requiere auditoría/corrección por caso; los orquestadores modernos validados pueden avanzar. |
| Frontend real seguro | BLOQUEADOR_REAL | Uso humano integral | OWNERS_VIGENTES por alcance: #461/#536; epics de frontend | Uso diario sin autoridad declarada por headers; puede migrarse por superficies. |
| Workers/scheduler | BLOQUEADOR_REAL | Automatización productiva de Sync, mora y vencimientos | OWNER_ISSUE = FALTA | No bloquea ejecución manual ni jornada manual; sí automatización supervisada. |
| Operación multi-base recuperable | BLOQUEADOR_REAL | Multi-instalación productiva | OWNER_ISSUE = FALTA | Deployment, backup/restore, pruebas multi-base y recuperación. |

## 18. Mapa textual de dependencias

```text
#461 ↔ #536 (infraestructura común de PR #537 ya integrada)
→ tracks coordinados de identidad humana y contexto técnico/operativo
→ adopción incremental por dominio/superficie
→ cada lote puede avanzar con el contrato que necesita, sin esperar el cierre
  total de ambos coordinadores

#534
→ Persona/Documento + Reserva/Venta + Inmueble/UF + Índice/Valor portables
→ grafo PPV2 resoluble y físicamente único
→ #427 / #428 / #429 / #423 en escenario multi-instalación

#427
→ base común de la venta
→ #428 materializa valor base pendiente
→ #429 persiste período objetivo
→ #423 selecciona exactamente el valor contractual
→ #430 / #431 completan UI e integración

#519
→ Entrega/Restitución con identidades portables, sin PK local como identidad distribuida
→ Locativo ↔ Inmobiliario portable

#257
→ jornada operativa manual

#365
→ proveedor/definición de fecha operativa
→ dependencia importante de los flujos contractuales que la requieran

worker/scheduler productivo
→ automatización supervisada de vencimientos, mora, retry y otros jobs
→ no es prerequisito de una jornada ejecutada manualmente

DEV-SRV GOP
→ DEV-API GOP
→ SQL/runtime/Sync/tests
→ frontend MVP humano

#522
→ actor técnico autenticado/autorizado
→ origen SISTEMA y automatizaciones (no bloquea GOP humano)
```

## 19. Capacidades relevantes sin owner focal

| Pendiente | Dominio | Importancia | Issue owner | Crear issue recomendado |
| --- | --- | --- | --- | --- |
| Worker/scheduler productivo transversal | Técnico/Infra | CRÍTICA | FALTA | Sí, antes de automatizar consumers y vencimientos. |
| Bootstrap y deployment por instalación | Infra/Operativo | CRÍTICA | FALTA | Sí. |
| Backup/restore probado y runbook | Infra | CRÍTICA | FALTA | Sí. |
| Migrations/upgrades productivos y rollback | Infra | CRÍTICA | FALTA | Sí. |
| Observabilidad y recuperación multi-base | Técnico/Infra | CRÍTICA | FALTA | Sí. |
| Lifecycle portable Sucursal/Instalación | Operativo/Sync | ALTA | COORDINADOR #248; FALTA owner focal | Sí, separado de #536. |
| Sync portable general de Personas | Personas/Sync | CRÍTICA | FALTA | Sí; #534 sólo cubre prerequisitos PPV2. |
| Merge seguro de Personas | Personas | MEDIA | FALTA | Sí, después de deduplicación canónica. |
| Garantías locativas end-to-end | Locativo/Financiero | ALTA | FALTA | Sí. |
| Cierre de renovación/rescisión/vencimiento locativo | Locativo | ALTA | FALTA | Sí, posiblemente dividido. |
| Lectura Financiero → Caja | Operativo/Financiero | ALTA | #258 | No; usar el owner existente. |
| Integración write pago ↔ movimiento físico | Operativo/Financiero | CRÍTICA | RELACIONADO_NO_OWNER #258; FALTA owner focal | Sí sólo para el alcance write no cubierto por #258, preservando ownership separado. |
| DEV-SRV/API e implementación GOP MVP | GOP | ALTA | FALTA | Sí, uno por incremento. |
| Subsistema Documental mínimo | Documental | CRÍTICA | FALTA | Sí, primero contrato/storage/seguridad. |
| MVP Analítico | Analítico | MEDIA | FALTA | Sí, después de estabilizar fuentes. |
| Frontend Administrativo/Operativo integral | Frontend | ALTA | FALTA focal | Sí, coordinado con #248/#249. |

## 20. Deuda legacy vigente

No es funcionalidad faltante: es comportamiento existente que debe retirarse o
aislarse sin romper consumidores actuales.

| Deuda | Riesgo | Owner |
| --- | --- | --- |
| `X-Usuario-Id` como identidad declarada por cliente | Spoofing y auditoría no confiable | #461 |
| `X-Instalacion-Id` client-controlled como procedencia | Nodo falso y corrupción de metadata | #536 |
| PK locales en eventos y contratos de payload incompletos | Imposibilidad de resolver/aplicar correctamente en otra base | #519/#534/#520 |
| Commits/rollbacks en repositories | Respuestas exitosas no durables o atomicidad rota | #107/#520 y owners focales |
| Producers/consumers/outbox legacy | Dedupe débil y dependencias invisibles | #520 |
| `configuracion_general` | Dos fuentes aparentes de configuración | #518 |
| Aliases write `/roles-participacion` | Ambigüedad entre catálogo y relación | #517 |
| Hardcodes/contexto manual frontend | Operación dependiente de IDs técnicos | #461/#536 |
| `date.today()`/`datetime.now()` contractuales | Resultados no reproducibles por fecha operativa/zona | #365/#465 |
| Deuda Ruff estructural | Dificulta señal de calidad; no debe mezclarse con features | #463–#467 |

## 21. Qué no hace falta para el MVP

- GOP post-MVP de #527: recurrencia, Kanban, SLA, workflows, equipos y subtareas.
- Automatizaciones `origen=SISTEMA`; primero alcanza GOP humano y #522 puede seguir separado.
- Analítico avanzado, dashboards multi-dimensionales y reporting sofisticado.
- Documental offline completo o replicación binaria multi-base; sí hace falta un
  manejo documental mínimo cuando la operación legal lo requiera.
- Refinanciación/reprogramación universal, NC/ND avanzada y cancelación anticipada completa.
- Expensas formales (#3) y otros circuitos especializados.
- SSO/OAuth, refresh tokens o una plataforma IAM compleja, salvo nueva decisión.
- Merge automático de Personas; para MVP puede utilizarse deduplicación y resolución manual controlada.

Excluir estas capacidades no permite omitir autenticación humana, autorización
mínima, fecha operativa, pagos, caja controlada, backup/restore ni errores seguros.

## 22. Vista ejecutiva final

| Área | Estado | Pendiente crítico | Pendiente importante | Post-MVP |
| --- | --- | --- | --- | --- |
| Técnico/Sync | AVANZADO | #461/#536, workers, portabilidad | observabilidad/temporalidad | automatización avanzada |
| Administrativo | AVANZADO | authz/scope transversal | UI y Sync de relaciones | IAM avanzado |
| Personas | INTERMEDIO | seguridad y portabilidad | lifecycle/deduplicación | merge sofisticado |
| Inmobiliario | INTERMEDIO | portabilidad disponibilidad/ocupación | lifecycle/UI completa | analítica espacial |
| Comercial | AVANZADO | #534 y cierre #427–#423 | actos legales/importación | liquidaciones avanzadas |
| Locativo | INTERMEDIO | #519, garantías y seguridad | ciclo de renovación/rescisión | automatizaciones |
| Financiero | AVANZADO | pagos/caja segura y PPV2 definitivo | reversión/emisión | refinanciación avanzada |
| Operativo | INTERMEDIO | contexto, jornada, caja/fecha | arqueo/multi-instalación | optimización operacional |
| GOP | DISEÑADO_NO_IMPLEMENTADO | DEV-SRV/API/runtime MVP | UI/Sync humano | backlog #527 |
| Documental | INICIAL | storage/upload/permisos | versionado/asociaciones | offline completo |
| Analítico | DISEÑADO_NO_IMPLEMENTADO | ninguno para MVP core | definir MVP | analítica avanzada |
| Frontend | INTERMEDIO | sesión/contexto/authz y operaciones core | cobertura restante | dashboards/workflows |
| Infra productiva | INICIAL | deploy, backup, upgrades, worker | observabilidad/runbooks | alta disponibilidad avanzada |

## 23. Roadmap orientativo por fases

1. **FASE 1 — Estabilización transversal.** Incorporar el contrato reusable de
   #536 cuando quede verificado y avanzar incrementalmente #461; delimitar #365,
   transaction ownership, seguridad de errores y owner para worker/infra. El
   cierre total de #461 y #536 no es gate absoluto para todo trabajo posterior.
2. **FASE 2 — Cierre de dominios core y GOP humano en paralelo.** Caja/pagos,
   garantías y ciclo Locativo; #427–#429/#423; lifecycle y deduplicación
   indispensables. DEV-SRV, DEV-API e implementación del MVP humano GOP pueden
   avanzar con identidad humana/local suficiente y sus contratos propios.
3. **FASE 3 — Frontend y operación real.** Sesión/contexto, autorización visible,
   administración, operaciones Comerciales/Locativas/Financieras y Documental mínimo.
4. **FASE 4 — Multi-instalación productiva.** #519/#534, transporte, workers,
   pruebas multi-base, observabilidad, backup/restore, upgrades y recuperación.
5. **FASE 5 — Dominio Documental completo.** Completar el subsistema Documental
   más allá del mínimo requerido para la operación real.
6. **FASE 6 — Analítica y automatización.** MVP Analítico, #522, GOP post-MVP y
   reporting/automatizaciones avanzadas.

Las fases expresan precedencia, no fechas. Puede haber trabajo paralelo sólo
cuando no dependa de contratos aún abiertos.

## 24. Regla de mantenimiento

- Este mapa **no es source of truth de implementación**: orienta y enlaza.
- Debe reconciliarse contra runtime, SQL, tests e issues antes de cada decisión.
- Cada PR relevante debe evaluar si cambia estado, dependencia u owner del mapa.
- Cuando avance `main` o se integre un prerequisito material, el corte y las
  capacidades afectadas deben reconciliarse antes de usar el mapa para planificar.
- No debe duplicar el detalle normativo de DEV-ARCH, DER, DEV-SRV o DEV-API.
- Un issue abierto no demuestra que todo su body siga vigente; un PR histórico
  mergeado no debe mostrarse como pendiente.
- Una tabla SQL, `uid_global`, outbox o diseño no bastan para marcar una capacidad
  `IMPLEMENTADO`.

## 25. Corte GitHub verificado

- `main`: `744465e88c346fd0e10b02a6f5b39be3b524578b`.
- PR #535: `MERGED` el 2026-09-04 e incluido en la historia del corte auditado.
- PR #537: `MERGED`; merge commit
  `744465e88c346fd0e10b02a6f5b39be3b524578b`. Su infraestructura común se
  contabiliza como integrada; la adopción incremental continúa bajo #536/#461.
- #461: `OPEN`.
- #536: `OPEN`.
- Owners abiertos centrales reconciliados: #248, #249, #365, #423,
  #427–#431, #461, #463–#467, #517–#520, #522, #527 y #534.
