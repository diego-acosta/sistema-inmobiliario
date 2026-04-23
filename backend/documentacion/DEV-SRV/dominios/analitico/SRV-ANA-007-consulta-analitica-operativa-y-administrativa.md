# SRV-ANA-007 — Consulta analítica operativa y administrativa

## Objetivo
Proveer una vista analítica consolidada de la actividad operativa y administrativa del sistema, permitiendo consultar en forma resumida y agregada uso del sistema, usuarios, sesiones, accesos, auditoría y actividad operativa, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta consolidada de actividad del sistema
- métricas de uso por usuario y sucursal
- métricas de sesiones y accesos
- trazabilidad operativa agregada
- indicadores de actividad administrativa
- soporte para paneles y reportes operativos

No incluye:
- gestión de usuarios
- control de acceso write
- modificación de credenciales
- ejecución de lógica administrativa
- modificación de auditoría o trazas

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- usuario
- usuario_sucursal
- credencial_usuario
- sesion_usuario
- historial_acceso
- registro_auditoria
- operaciones del sistema (op_id, trazabilidad)

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por usuario
- filtros por sucursal
- filtros por tipo de operación
- filtros por estado de sesión
- agrupación por dimensión operativa

## Resultado esperado
- cantidad de usuarios activos
- cantidad de sesiones
- distribución de accesos por sucursal
- actividad por usuario
- indicadores de uso del sistema
- trazabilidad operativa resumida
- vistas consolidadas aptas para reporting operativo

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo operativo a consultar
3. obtener información desde fuentes administrativas y técnicas
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre sesión, usuario y acceso
- no confusión entre actividad actual e histórica

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no modifica auditoría ni trazabilidad

## Dependencias

### Hacia dominios funcionales
- servicios del dominio administrativo
- servicios de autenticación y gestión de usuarios
- registros de auditoría y trazabilidad del sistema

### Hacia infraestructura
- CORE-EF-001 para timestamps, op_id, versionado y trazabilidad
- mecanismos de logging y auditoría

## Reglas de arquitectura aplicadas
- no redefine la lógica administrativa ni de seguridad
- no reemplaza la consulta operativa de usuarios o auditoría
- consume información estructural ya definida por dominios administrativos y técnicos
- agrega, resume y consolida para fines analíticos

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- se articula con todos los dominios como capa transversal de uso del sistema
- puede alimentar dashboards operativos y administrativos
- no reemplaza consultas analíticas financieras, comerciales, locativas o documentales

## Pendientes abiertos
- definición exacta de KPIs operativos mínimos
- definición de métricas estándar de uso del sistema
- política de retención de datos históricos de auditoría
- estrategia de vistas materializadas o cache analítico
