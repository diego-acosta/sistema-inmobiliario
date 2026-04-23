# SRV-FIN-001 — Gestión de relación generadora

## Objetivo
Administrar el ciclo de vida de la relación generadora como raíz formal del circuito financiero.

## Alcance
Este servicio cubre:
- alta de relación generadora
- edición en borrador
- activación
- cancelación
- finalización

No cubre directamente:
- parametrización financiera
- gestión de índices
- registro de pagos
- imputación de pagos
- mora
- caja operativa
- emisión documental final

## Agregado principal
- relacion_generadora

## Entidades relacionadas
- obligacion_financiera
- composicion_obligacion

## Casos de uso
- alta de relación generadora
- edición de relación generadora en borrador
- activación de relación generadora
- cancelación de relación generadora
- finalización de relación generadora

## Reglas
- [[RN-FIN]]

## Estados
- [[EST-FIN]]

## Entradas conceptuales
### Contexto técnico
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- tipo_origen
- id_origen
- descripcion
- identificador de relación generadora cuando aplique
- motivo u observación cuando aplique

## Resultado esperado
- id_relacion_generadora
- estado_resultante
- version_resultante
- op_id
- efectos generados
- errores estructurados cuando corresponda

## Flujo de alto nivel

### Alta
1. validar contexto técnico e idempotencia
2. validar origen y compatibilidad
3. crear relación en borrador
4. persistir
5. registrar outbox
6. devolver resultado

### Edición en borrador
1. cargar relación
2. validar existencia, lock y versión
3. validar estado borrador
4. aplicar cambios
5. persistir y registrar outbox

### Activación
1. cargar relación y validar contexto
2. validar estado y condiciones previas
3. activar relación
4. generar obligaciones iniciales y composiciones cuando corresponda
5. persistir de forma atómica
6. registrar outbox
7. devolver resultado

### Cancelación
1. cargar relación
2. validar lock, versión e idempotencia
3. validar cancelabilidad
4. cambiar estado
5. persistir y registrar outbox

### Finalización
1. cargar relación
2. validar lock, versión e idempotencia
3. validar saldo cero y ausencia de operaciones futuras
4. cambiar a estado finalizado
5. persistir y registrar outbox

## Validaciones clave
- origen existente
- origen compatible
- no duplicidad funcional por origen cuando corresponda
- edición estructural solo en borrador
- activación solo con condiciones mínimas completas
- finalización solo sin deuda ni operaciones futuras
- consistencia entre activación y generación inicial de obligaciones

## Efectos transaccionales
- alta o actualización de relacion_generadora
- alta de obligacion_financiera en activación cuando corresponda
- alta de composicion_obligacion en activación cuando corresponda
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias
### Hacia arriba
- origen comercial válido
- origen locativo válido
- otros orígenes financieros permitidos

### Hacia abajo
- generación de obligaciones
- cronograma y consulta de deuda
- pagos e imputación
- emisión financiera
- analítica financiera

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[RN-FIN]]
- [[ERR-FIN]]
- [[EST-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- política exacta para múltiples relaciones generadoras sobre un mismo origen
- normalización final del catálogo de estados funcionales
- definición final por método financiero de activación con generación inmediata versus habilitación previa
