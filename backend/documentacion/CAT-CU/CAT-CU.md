# CAT-CU — Catálogo global de casos de uso

## Objetivo
Consolidar los casos de uso del sistema organizados por dominio.

## Alcance
Incluye todos los dominios funcionales, técnicos y analíticos del sistema.

---

## Estructura por dominio

### Administrativo (CU-ADM)

Dominio transversal responsable de usuarios, roles, permisos, configuración y trazabilidad administrativa del sistema.

- CU-ADM-001 — Alta de usuario
- CU-ADM-002 — Modificación de usuario
- CU-ADM-003 — Baja lógica de usuario
- CU-ADM-004 — Activación de usuario
- CU-ADM-005 — Desactivación de usuario
- CU-ADM-006 — Consulta de usuario
- CU-ADM-021 — Consulta de usuarios
- CU-ADM-007 — Alta de rol
- CU-ADM-008 — Modificación de rol
- CU-ADM-009 — Baja de rol
- CU-ADM-010 — Asignación de rol a usuario
- CU-ADM-011 — Remoción de rol
- CU-ADM-012 — Consulta de roles
- CU-ADM-013 — Consulta de permisos
- CU-ADM-022 — Gestión de permisos
- CU-ADM-014 — Modificación de parámetros del sistema
- CU-ADM-015 — Consulta de configuración
- CU-ADM-016 — Activación o desactivación de funcionalidades
- CU-ADM-017 — Consulta de auditoría de operaciones
- CU-ADM-018 — Consulta de historial de cambios
- CU-ADM-019 — Consulta por op_id
- CU-ADM-020 — Consulta de eventos administrativos

### Personas (CU-PER)

Dominio base de sujetos de negocio del sistema, incluyendo identificación, domicilios, contactos, relaciones y representación.

- CU-PER-001 — Alta de persona
- CU-PER-002 — Modificación de persona
- CU-PER-003 — Baja lógica de persona
- CU-PER-004 — Reactivación de persona
- CU-PER-005 — Alta de documento identificatorio
- CU-PER-006 — Modificación de documento identificatorio
- CU-PER-007 — Baja lógica de documento identificatorio
- CU-PER-008 — Cambio de documento principal
- CU-PER-009 — Alta de domicilio
- CU-PER-010 — Modificación de domicilio
- CU-PER-011 — Baja lógica de domicilio
- CU-PER-012 — Cambio de domicilio principal
- CU-PER-013 — Alta de contacto
- CU-PER-014 — Modificación de contacto
- CU-PER-015 — Baja lógica de contacto
- CU-PER-016 — Cambio de contacto principal
- CU-PER-017 — Alta de relación entre personas
- CU-PER-018 — Modificación de relación entre personas
- CU-PER-019 — Baja lógica de relación entre personas
- CU-PER-020 — Alta de representación o poder
- CU-PER-021 — Modificación de representación o poder
- CU-PER-022 — Baja lógica de representación o poder
- CU-PER-023 — Consulta de representación vigente
- CU-PER-024 — Asignación de rol de participación a persona en una relación del sistema
- CU-PER-025 — Modificación de rol de participación
- CU-PER-026 — Baja lógica de rol de participación
- CU-PER-027 — Consulta de persona
- CU-PER-028 — Consulta de personas
- CU-PER-029 — Consulta de ficha integral de persona
- CU-PER-030 — Consulta por documento
- CU-PER-031 — Consulta por CUIT o CUIL
- CU-PER-032 — Consulta por nombre o razón social
- CU-PER-033 — Consulta de histórico vinculado a persona

### Inmobiliario (CU-INM)

Dominio responsable del activo inmobiliario base, sus unidades funcionales, atributos, relaciones, estado y disponibilidad.

- CU-INM-001 — Alta de inmueble
- CU-INM-002 — Modificación de inmueble
- CU-INM-003 — Baja lógica de inmueble
- CU-INM-004 — Reactivación de inmueble
- CU-INM-005 — Alta de unidad funcional
- CU-INM-006 — Modificación de unidad funcional
- CU-INM-007 — Baja lógica de unidad funcional
- CU-INM-008 — Reactivación de unidad funcional
- CU-INM-009 — Alta de atributo inmobiliario
- CU-INM-010 — Modificación de atributo inmobiliario
- CU-INM-011 — Baja lógica de atributo inmobiliario
- CU-INM-012 — Consulta de atributos inmobiliarios
- CU-INM-013 — Alta de relación inmobiliaria
- CU-INM-014 — Modificación de relación inmobiliaria
- CU-INM-015 — Baja lógica de relación inmobiliaria
- CU-INM-016 — Consulta de relación inmobiliaria vigente
- CU-INM-017 — Cambio de estado inmobiliario
- CU-INM-018 — Cambio de disponibilidad inmobiliaria
- CU-INM-019 — Bloqueo de disponibilidad inmobiliaria
- CU-INM-020 — Liberación de disponibilidad inmobiliaria
- CU-INM-021 — Consulta de inmueble
- CU-INM-022 — Consulta de inmuebles
- CU-INM-023 — Consulta de unidad funcional
- CU-INM-024 — Consulta de unidades funcionales
- CU-INM-025 — Consulta de ficha integral de inmueble
- CU-INM-026 — Consulta de disponibilidad inmobiliaria
- CU-INM-027 — Consulta de histórico inmobiliario

### Comercial (CU-COM)

Dominio comercial orientado a clientes, operaciones, reservas e interacciones del flujo previo a contratación.

- CU-COM-001 — Alta de cliente
- CU-COM-002 — Modificación de cliente
- CU-COM-003 — Baja lógica de cliente
- CU-COM-004 — Consulta de cliente
- CU-COM-005 — Consulta de clientes
- CU-COM-006 — Alta de operación comercial
- CU-COM-007 — Modificación de operación
- CU-COM-008 — Cambio de estado de operación comercial
- CU-COM-009 — Cierre de operación comercial
- CU-COM-010 — Cancelación de operación
- CU-COM-011 — Consulta de operación
- CU-COM-012 — Consulta de operaciones
- CU-COM-013 — Generación de reserva
- CU-COM-014 — Confirmación de reserva
- CU-COM-015 — Cancelación de reserva
- CU-COM-016 — Consulta de reservas
- CU-COM-017 — Registro de interacción con cliente
- CU-COM-018 — Consulta de historial comercial
- CU-COM-019 — Consulta de pipeline comercial

### Locativo (CU-LOC)

Dominio responsable del ciclo de vida contractual locativo, sus condiciones, vigencia, renovaciones, rescisiones y consultas.

- CU-LOC-001 — Alta de contrato locativo
- CU-LOC-002 — Modificación de contrato locativo
- CU-LOC-003 — Cancelación de contrato locativo
- CU-LOC-004 — Definición de condiciones locativas
- CU-LOC-005 — Modificación de condiciones locativas
- CU-LOC-006 — Consulta de condiciones locativas
- CU-LOC-007 — Activación de contrato locativo
- CU-LOC-008 — Suspensión de contrato locativo
- CU-LOC-009 — Finalización de contrato locativo
- CU-LOC-010 — Generación de renovación
- CU-LOC-011 — Confirmación de renovación
- CU-LOC-012 — Solicitud de rescisión
- CU-LOC-013 — Aprobación de rescisión
- CU-LOC-014 — Ejecución de rescisión
- CU-LOC-015 — Consulta de contrato locativo
- CU-LOC-016 — Consulta de contratos locativos
- CU-LOC-017 — Consulta de estado contractual
- CU-LOC-018 — Consulta de historial contractual

### Financiero (CU-FIN)

Dominio encargado de relaciones generadoras, obligaciones, imputaciones, ajustes, cancelaciones y consultas del estado financiero.

- CU-FIN-001 — Alta de relación generadora
- CU-FIN-002 — Modificación de relación generadora
- CU-FIN-003 — Activación de relación generadora
- CU-FIN-004 — Cancelación de relación generadora
- CU-FIN-005 — Finalización de relación generadora
- CU-FIN-006 — Generación de obligación
- CU-FIN-007 — Generación masiva de obligaciones
- CU-FIN-008 — Reversión de generación de obligación
- CU-FIN-009 — Registro de débito financiero
- CU-FIN-010 — Registro de crédito financiero
- CU-FIN-011 — Imputación de pago
- CU-FIN-012 — Reversión de imputación
- CU-FIN-013 — Registro de ajuste positivo
- CU-FIN-014 — Registro de ajuste negativo
- CU-FIN-015 — Cancelación de obligación
- CU-FIN-016 — Regularización de deuda
- CU-FIN-017 — Consulta de obligación
- CU-FIN-018 — Consulta de obligaciones
- CU-FIN-019 — Consulta de estado de deuda
- CU-FIN-020 — Consulta de movimientos financieros
- CU-FIN-021 — Consulta de historial financiero

### Documental (CU-DOC)

Dominio transversal de plantillas, generación, emisión, asociación, control y consulta documental del sistema.

- CU-DOC-001 — Alta de plantilla documental
- CU-DOC-002 — Modificación de plantilla documental
- CU-DOC-003 — Baja de plantilla documental
- CU-DOC-004 — Consulta de plantillas
- CU-DOC-005 — Generación de documento
- CU-DOC-006 — Regeneración de documento
- CU-DOC-007 — Anulación de documento generado
- CU-DOC-008 — Emisión de documento
- CU-DOC-009 — Reemisión de documento
- CU-DOC-010 — Cambio de estado documental
- CU-DOC-011 — Versionado de documento
- CU-DOC-015 — Asociación de documento a entidad
- CU-DOC-016 — Reasociación de documento
- CU-DOC-017 — Consulta de asociaciones documentales
- CU-DOC-018 — Consulta de documento
- CU-DOC-019 — Consulta de documentos
- CU-DOC-020 — Consulta de historial documental

### Operativo (CU-OPER)

Dominio orientado a coordinación de trabajo, pendientes, asignaciones, seguimiento de ejecución y consultas operativas consolidadas.

- CU-OPER-001 — Alta de tarea operativa
- CU-OPER-002 — Modificación de tarea operativa
- CU-OPER-003 — Cancelación de tarea operativa
- CU-OPER-004 — Cierre de tarea operativa
- CU-OPER-005 — Registro de pendiente operativo
- CU-OPER-006 — Modificación de pendiente operativo
- CU-OPER-007 — Resolución de pendiente operativo
- CU-OPER-008 — Reapertura de pendiente operativo
- CU-OPER-009 — Asignación de tarea operativa
- CU-OPER-010 — Reasignación de tarea operativa
- CU-OPER-011 — Desasignación de tarea operativa
- CU-OPER-012 — Cambio de estado operativo
- CU-OPER-013 — Registro de avance operativo
- CU-OPER-014 — Registro de incidencia operativa
- CU-OPER-015 — Inicio de proceso operativo
- CU-OPER-016 — Pausa de proceso operativo
- CU-OPER-017 — Reanudación de proceso operativo
- CU-OPER-018 — Finalización de proceso operativo
- CU-OPER-019 — Cancelación de proceso operativo
- CU-OPER-020 — Consulta de tarea operativa
- CU-OPER-021 — Consulta de tareas operativas
- CU-OPER-022 — Consulta de pendientes operativos
- CU-OPER-023 — Consulta de bandeja operativa
- CU-OPER-024 — Consulta de estado operativo
- CU-OPER-025 — Consulta de histórico operativo

### Técnico (CU-TEC)

Dominio técnico de soporte distribuido para sincronización, inbox/outbox, idempotencia, locks, conflictos y trazabilidad técnica.

- CU-TEC-001 — Registro de operación distribuida
- CU-TEC-002 — Validación de operación distribuida
- CU-TEC-003 — Rechazo de operación distribuida inválida
- CU-TEC-004 — Cierre técnico de operación distribuida
- CU-TEC-005 — Inicio de sincronización
- CU-TEC-006 — Recepción de cambio remoto
- CU-TEC-007 — Aplicación de cambio remoto
- CU-TEC-008 — Confirmación de sincronización
- CU-TEC-009 — Reintento de sincronización fallida
- CU-TEC-010 — Registro en outbox
- CU-TEC-011 — Emisión desde outbox
- CU-TEC-012 — Registro en inbox
- CU-TEC-013 — Procesamiento de inbox
- CU-TEC-014 — Confirmación de procesamiento técnico
- CU-TEC-015 — Validación de op_id
- CU-TEC-016 — Detección de operación duplicada
- CU-TEC-017 — Reintento técnico controlado
- CU-TEC-018 — Rechazo por conflicto de op_id
- CU-TEC-019 — Toma de lock lógico
- CU-TEC-020 — Liberación de lock lógico
- CU-TEC-021 — Rechazo por lock activo
- CU-TEC-022 — Validación de versión esperada
- CU-TEC-023 — Detección de conflicto técnico
- CU-TEC-024 — Registro de conflicto de sincronización
- CU-TEC-025 — Resolución técnica de conflicto
- CU-TEC-026 — Escalamiento de conflicto no resoluble automáticamente
- CU-TEC-027 — Consulta de operación distribuida
- CU-TEC-028 — Consulta de outbox
- CU-TEC-029 — Consulta de inbox
- CU-TEC-030 — Consulta de locks lógicos
- CU-TEC-031 — Consulta de conflictos técnicos
- CU-TEC-032 — Consulta de trazabilidad técnica
- CU-TEC-033 — Consulta de histórico técnico

### Analítico (CU-ANA)

Dominio de consumo analítico orientado a reportes, indicadores, análisis histórico y vistas agregadas del sistema.

- CU-ANA-001 — Generación de reporte operativo
- CU-ANA-002 — Consulta de estado operativo consolidado
- CU-ANA-003 — Consulta de carga de trabajo
- CU-ANA-004 — Generación de reporte de deuda
- CU-ANA-005 — Generación de reporte de cobranzas
- CU-ANA-006 — Consulta de estado financiero consolidado
- CU-ANA-007 — Generación de reporte comercial
- CU-ANA-008 — Consulta de pipeline comercial
- CU-ANA-009 — Consulta de conversiones comerciales
- CU-ANA-010 — Consulta de indicadores operativos
- CU-ANA-011 — Consulta de indicadores financieros
- CU-ANA-012 — Consulta de indicadores comerciales
- CU-ANA-013 — Consulta de métricas del sistema
- CU-ANA-014 — Consulta de evolución histórica financiera
- CU-ANA-015 — Consulta de evolución histórica comercial
- CU-ANA-016 — Consulta de evolución histórica operativa
- CU-ANA-017 — Consulta de evolución de activos inmobiliarios
- CU-ANA-018 — Consulta analítica consolidada
- CU-ANA-019 — Consulta de vistas agregadas del sistema
- CU-ANA-020 — Consulta de información cruzada entre dominios
- CU-ANA-021 — Consulta de tendencias

---

## Reglas

1. Este documento no reemplaza los CU por dominio.
2. No define lógica de negocio.
3. No define implementación.
4. No redefine entidades.
5. Funciona como índice estructural del sistema.

---

## Notas

- Este documento permite navegar el sistema completo a nivel de casos de uso.
- Cada dominio mantiene su definición detallada en su archivo correspondiente.
- Este catálogo sirve como base para el diseño de API (DEV-API) y servicios (DEV-SRV).
