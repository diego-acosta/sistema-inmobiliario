# SRV-FIN-004 — Gestión de índices financieros

## Objetivo
Registrar y actualizar índices financieros utilizados por el dominio financiero para cálculo, ajuste, actualización o validación de obligaciones.

## Alcance
Este servicio cubre:
- alta de índice financiero
- modificación de índice financiero
- actualización de valor de índice
- mantenimiento de vigencia del índice cuando corresponda

No cubre:
- consulta histórica detallada
- generación de obligaciones
- recalculo masivo de deuda
- mora
- pagos
- emisión documental final

## Agregado principal
- indice_financiero

## Casos de uso cubiertos
- alta de índice
- modificación de índice
- actualización de valor de índice

## Reglas
- [[RN-FIN]]

## Entradas conceptuales
### Contexto técnico
- usuario_id
- sucursal_id
- instalacion_id
- op_id
- version_esperada cuando corresponda

### Datos de negocio
- identificador de índice cuando aplique
- tipo o nombre de índice
- período o fecha de vigencia
- valor del índice
- observación o motivo cuando corresponda

## Resultado esperado
- identificador del índice afectado
- versión resultante cuando corresponda
- op_id
- resumen de cambios realizados
- errores estructurados cuando corresponda

## Flujo de alto nivel
1. validar contexto técnico e idempotencia
2. validar existencia o unicidad del índice según operación
3. validar período, vigencia y valor informado
4. crear o actualizar índice financiero
5. persistir cambios
6. registrar outbox cuando corresponda
7. devolver resultado

## Validaciones clave
- identificación válida del índice
- no duplicidad indebida por tipo y período
- valor válido del índice
- coherencia de vigencia
- modificación sobre versión esperada correcta
- idempotencia en reintentos

## Efectos transaccionales
- alta o actualización de indice_financiero
- actualización de metadatos transversales
- registro de outbox en operaciones sincronizables

## Errores
- [[ERR-FIN]]

## Dependencias
### Hacia arriba
- configuración financiera compatible
- política de períodos y vigencias definida

### Hacia abajo
- generación de obligaciones
- ajustes de alquiler
- mora y rectificaciones por índice
- analítica financiera

## Transversales
- [[TRANSVERSALES]]
- [[CORE-EF-001-infraestructura-transversal]]

## Referencias
- [[00-INDICE-FINANCIERO]]
- [[RN-FIN]]
- [[ERR-FIN]]
- CAT-CU-001
- DEV-SRV-001 legado
- DER financiero

## Pendientes abiertos
- política exacta de unicidad por tipo de índice y período
- estrategia de corrección versus reemplazo de valores ya publicados
- efectos downstream automáticos ante actualización de índice
