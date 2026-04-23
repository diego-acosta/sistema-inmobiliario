# SRV-ANA-005 — Consulta analítica financiera

## Objetivo
Proveer una vista analítica consolidada del dominio financiero, permitiendo consultar en forma resumida y agregada deuda, flujo, cobranzas, mora, refinanciaciones, saldos e indicadores financieros generales del sistema, sin generar efectos persistentes.

## Alcance
Incluye:
- consulta financiera consolidada de alto nivel
- métricas generales de deuda, saldo y cobranzas
- agregación por sucursal, relación, sujeto o dimensión financiera
- indicadores resumidos del estado financiero
- soporte base para paneles y reportes financieros

No incluye:
- registro de pagos
- imputación financiera write
- generación de obligaciones
- cálculo write de mora, intereses o refinanciaciones
- reconstrucción primaria de lógica financiera
- reemplazo de los servicios analíticos financieros especializados

## Naturaleza del servicio
- tipo: query
- alcance: analítica por dominio
- granularidad: agregada y resumida
- sin efectos transaccionales

## Entidades involucradas (referencial)
- relacion_generadora
- obligacion_financiera
- composicion_obligacion
- obligacion_obligado cuando corresponda
- movimiento_financiero
- aplicacion_financiera
- cuenta_financiera cuando corresponda
- movimiento_tesoreria / caja financiera cuando corresponda por lectura consolidada

## Entradas conceptuales
- fecha de corte (opcional)
- filtros por sucursal
- filtros por relación generadora
- filtros por persona, cliente o locatario
- filtros por estado financiero
- filtros por tipo de obligación o movimiento
- agrupación por dimensión financiera

## Resultado esperado
- deuda total resumida
- saldo financiero resumido
- cobranzas resumidas
- mora resumida
- refinanciaciones resumidas
- indicadores financieros consolidados
- distribución por dimensión financiera
- vistas consolidadas aptas para reporting financiero general

## Flujo de alto nivel
1. validar parámetros de consulta
2. determinar universo financiero a consultar
3. obtener información desde fuentes funcionales del dominio financiero
4. aplicar filtros y fecha de corte cuando corresponda
5. consolidar métricas e indicadores
6. construir vista agregada
7. devolver resultado

## Validaciones clave
- coherencia de filtros
- consistencia temporal cuando exista fecha de corte
- consistencia entre obligación, movimiento y aplicación en la proyección resumida
- no confusión entre estado actual y estado histórico
- no confusión entre vista general financiera y consultas analíticas especializadas

## Efectos transaccionales
- no aplica
- no genera cambios
- no registra operaciones
- no recalcula lógica financiera primaria como fuente de verdad

## Dependencias

### Hacia dominios funcionales
- SRV-FIN como fuente de verdad financiera funcional
- consultas y lecturas consolidadas del dominio financiero
- estados y saldos definidos por el dominio financiero

### Hacia infraestructura
- CORE-EF-001 para timestamps, corte temporal y trazabilidad de lectura cuando corresponda

## Reglas de arquitectura aplicadas
- no redefine la lógica del dominio financiero
- no recalcula intereses, saldos ni mora como lógica financiera primaria
- consume semántica financiera ya definida por SRV-FIN o por read models derivados de éste
- agrega, resume y consolida para fines analíticos
- no sustituye a los servicios financieros especializados del dominio analítico

## Relación con otros servicios analíticos
- complementa a SRV-ANA-001 como vista especializada por dominio
- sirve como puerta de entrada financiera analítica de alto nivel
- se articula con servicios especializados:
  - consulta de deuda
  - consulta de flujo financiero
  - consulta de cobranzas
  - consulta de mora
  - consulta de refinanciaciones
  - consulta de saldos a fecha
  - consulta de cancelaciones anticipadas
- no reemplaza esas consultas especializadas

## Pendientes abiertos
- definición exacta de KPIs financieros mínimos
- definición de métricas estándar de deuda, mora y cobranzas en la vista general
- política de corte temporal para indicadores financieros globales
- estrategia de vistas materializadas o cache analítico
