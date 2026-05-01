# SRV-LOC-001 — Gestión de contratos de alquiler

## Objetivo
Gestionar contratos de alquiler como entidad raíz del dominio locativo, permitiendo su alta, modificación, activación, suspensión, finalización, baja lógica y consulta, preservando consistencia contractual y trazabilidad.

## Alcance
Este servicio cubre:
- alta de contrato de alquiler
- modificación de contrato
- activación de contrato
- suspensión o cambio de estado
- finalización de contrato
- baja lógica de contrato
- consulta de contratos
- vinculación de personas intervinientes y objetos locativos

No cubre:
- definición detallada de condiciones económicas
- gestión de garantías específicas
- generación de obligaciones financieras
- gestión documental locativa integral
- ocupación material del inmueble

## Entidades principales
- contrato_alquiler
- contrato_objeto_locativo
- persona
- inmueble
- unidad_funcional

## Modos del servicio

### Alta
Permite registrar un nuevo contrato de alquiler.

### Modificación
Permite actualizar datos contractuales permitidos.

### Activación
Permite pasar el contrato a estado vigente u operativo.

### Suspensión o cambio de estado
Permite registrar cambios de estado del contrato según reglas del proceso.

### Finalización
Permite cerrar el contrato por vencimiento, rescisión u otra causa válida.

### Baja lógica
Permite invalidar un contrato sin eliminarlo físicamente.

### Consulta
Permite visualizar contratos y su composición básica.

## Entradas conceptuales

### Contexto técnico (write)
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de contrato cuando corresponda
- personas intervinientes
- objetos inmobiliarios locados
- fecha de inicio
- fecha de fin prevista
- estado contractual
- destino locativo cuando corresponda
- observaciones contractuales

### Parámetros de consulta
- identificador de contrato
- persona interviniente
- objeto locativo
- estado contractual
- rango de fechas
- criterios básicos de búsqueda

## Resultado esperado

### Para operaciones write
- identificador de contrato
- estado resultante
- personas y objetos vinculados
- vigencia contractual
- versión resultante
- op_id
- errores estructurados cuando corresponda

### Para consulta
- datos del contrato
- estado contractual
- personas intervinientes
- objetos locativos
- vigencia

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. cargar personas y objetos locativos
3. validar elegibilidad contractual
4. registrar contrato
5. vincular objetos y personas
6. persistir con metadatos transversales
7. registrar outbox
8. devolver resultado

### Modificación
1. validar contexto técnico
2. cargar contrato existente
3. validar versión esperada
4. validar modificabilidad según estado
5. aplicar cambios
6. persistir actualización
7. registrar outbox
8. devolver resultado

### Activación
1. validar contexto técnico
2. cargar contrato
3. validar elegibilidad para activación
4. aplicar cambio de estado
5. persistir actualización
6. registrar outbox `contrato_alquiler_activado`
7. devolver resultado

### Finalización
1. validar contexto técnico
2. cargar contrato vigente
3. validar causal y condiciones de cierre
4. aplicar finalización
5. persistir cambios
6. registrar outbox
7. devolver resultado

### Consulta
1. validar parámetros
2. cargar contrato o conjunto de contratos
3. resolver personas y objetos asociados
4. devolver vista de lectura

## Validaciones clave
- personas intervinientes existentes
- objeto locativo existente y elegible
- consistencia de fechas contractuales
- coherencia de estados y transiciones
- no superposición indebida según política funcional
- control de versionado
- idempotencia en alta

## Efectos transaccionales
- alta o actualización de contrato_alquiler
- alta o actualización de contrato_objeto_locativo
- vinculación con personas intervinientes
- aplicación de borrado lógico cuando corresponda
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Integracion con financiero

Al activar `contrato_alquiler`, locativo emite `outbox_event` con:

- `event_type = contrato_alquiler_activado`
- `aggregate_type = contrato_alquiler`
- `payload = {"id_contrato_alquiler": int}`

El procesamiento financiero posterior se realiza por inbox financiero:

```text
contrato_alquiler_activado
-> POST /api/v1/financiero/inbox
-> relacion_generadora tipo_origen = contrato_alquiler
-> obligaciones_financieras mensuales CANON_LOCATIVO
```

Reglas implementadas:

- la activacion del contrato no se bloquea por ausencia de
  `condicion_economica_alquiler`
- locativo no genera obligaciones financieras directamente
- financiero materializa el cronograma mensual `CANON_LOCATIVO`
- financiero evalua la condicion economica vigente al inicio de cada periodo
  mensual
- financiero omite periodos sin condicion economica aplicable
- si no hay ningun periodo con condicion aplicable, financiero no crea
  `relacion_generadora`
- existe pipeline automatico interno `outbox_event -> inbox` mediante worker financiero

Limitaciones financieras vigentes:

- no hay prorrateo por cambios de condicion dentro del mes
- no se divide un periodo mensual cuando una condicion cambia a mitad de mes
- si dos condiciones aplican al mismo inicio de periodo, gana la de
  `fecha_desde` mas reciente
- la politica de moneda y la regla real de vencimiento permanecen pendientes
- no se generan expensas, servicios, impuestos ni punitorios
- no se resuelve obligado financiero o locatario

## Errores
- [[ERR-LOC]]

## Dependencias

### Hacia arriba
- personas existentes
- inmueble o unidad funcional existente
- contexto técnico válido
- permisos sobre gestión locativa

### Hacia abajo
- [[SRV-LOC-002-gestion-de-condiciones-locativas]]
- [[SRV-LOC-003-gestion-de-garantias]]
- [[SRV-LOC-004-gestion-de-renovaciones-y-rescisiones]]
- [[SRV-LOC-005-gestion-de-ocupacion-locativa]]
- dominio financiero

## Transversales
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-LOCATIVO]]
- [[CU-LOC]]
- [[RN-LOC]]
- [[ERR-LOC]]
- [[EVT-LOC]]
- [[EST-LOC]]
- [[SRV-PER-006-gestion-de-roles-de-participacion-y-clientes]]
- [[SRV-INM-007-gestion-de-estado-disponibilidad-y-ocupacion]]
- DER locativo

## Pendientes abiertos
- catálogo final de estados contractuales
- reglas de activación y suspensión
- política exacta de superposición contractual
- relación exacta entre contrato y objeto locativo
- prorrateo del cronograma financiero cuando cambien condiciones dentro del mes
- resolucion de obligado financiero o locatario
- definicion de ejecucion operativa del worker financiero
