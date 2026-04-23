# RN-ANA — Reglas del dominio Analítico

## Objetivo
Definir reglas de construcción, consistencia y explotación del dominio Analítico como apoyo a implementación backend.

## Alcance del dominio
Incluye consultas analíticas, consolidación de información, agregaciones, comparaciones temporales, cruces entre dominios e indicadores read-only.

---

## A. Reglas de naturaleza read-only

### RN-ANA-001 — Consulta sin persistencia
- descripcion: toda consulta analítica debe ejecutarse sin generar efectos persistentes ni registrar cambios de estado.
- aplica_a: dominio_analitico
- origen_principal: DEV-SRV
- observaciones: la ejecución de consultas, reportes o consolidaciones no debe producir escrituras ni efectos laterales sobre otros dominios.

### RN-ANA-002 — Prohibición de lógica write
- descripcion: el dominio analítico no debe ejecutar altas, modificaciones, bajas ni operaciones write sobre dominios funcionales.
- aplica_a: dominio_analitico
- origen_principal: DEV-SRV

### RN-ANA-003 — Analítico no como fuente primaria
- descripcion: una vista analítica no debe constituirse en fuente primaria de verdad del sistema.
- aplica_a: dominio_analitico
- origen_principal: DEV-SRV

## B. Reglas de dependencia funcional

### RN-ANA-004 — Respeto por dominio origen
- descripcion: la semántica del dato consumido debe venir definida por el dominio funcional propietario.
- aplica_a: consultas_analiticas
- origen_principal: DEV-SRV
- observaciones: la calidad, completitud y confiabilidad del resultado analítico dependen de la calidad de las fuentes consultadas.

### RN-ANA-005 — No redefinición del negocio
- descripcion: una consulta analítica no debe redefinir reglas de negocio ni reconstruir lógicas primarias de otros dominios.
- aplica_a: consultas_analiticas
- origen_principal: DEV-SRV

### RN-ANA-006 — Consistencia con SRV-FIN
- descripcion: las consultas analíticas financieras deben consumir resultados definidos por SRV-FIN o por read models derivados de éste.
- aplica_a: consultas_analiticas_financieras
- origen_principal: DEV-SRV
- observaciones: el dominio analítico no debe recalcular ni sustituir la verdad financiera primaria.

## C. Reglas de consolidación y agregación

### RN-ANA-007 — Agregación sobre datos existentes
- descripcion: las métricas e indicadores deben calcularse sobre datos ya disponibles en dominios funcionales, sin generar verdad paralela.
- aplica_a: metricas_analiticas, indicadores_analiticos
- origen_principal: DEV-SRV

### RN-ANA-008 — Coherencia de filtros
- descripcion: toda consulta analítica debe validar coherencia entre filtros, dimensiones y universo de análisis antes de consolidar resultados.
- aplica_a: consultas_analiticas
- origen_principal: DEV-SRV

### RN-ANA-009 — No doble conteo
- descripcion: los procesos de agregación deben evitar doble conteo de entidades, montos o resultados consolidados.
- aplica_a: agregaciones_analiticas
- origen_principal: DEV-SRV

### RN-ANA-010 — Corte temporal consistente
- descripcion: cuando exista fecha de corte o rango temporal, la consulta debe respetar consistencia temporal según la semántica del dominio origen.
- aplica_a: consultas_analiticas, historico_analitico
- origen_principal: DEV-SRV
- observaciones: la consulta puede combinar fuentes con distintos momentos de actualización y no garantiza consistencia transaccional global entre dominios.

## D. Reglas de cruces y proyecciones

### RN-ANA-011 — Cruce sin alterar ownership
- descripcion: el cruce entre dominios solo puede consolidar y proyectar información, sin alterar el ownership semántico de cada dato.
- aplica_a: consultas_transversales, cruces_interdominio
- origen_principal: DEV-SRV
- observaciones: los cruces interdominio no deben convertirse en un modelo paralelo que reinterprete reglas funcionales.

### RN-ANA-012 — Resultado apto para reporting
- descripcion: los resultados del dominio analítico deben construirse como vistas resumidas, comparables y aptas para consultas, dashboards o reportes.
- aplica_a: reportes_analiticos, vistas_analiticas
- origen_principal: DEV-SRV
- observaciones: la presentación analítica resume y proyecta datos existentes, pero no sustituye consultas operativas detalladas ni fuentes primarias de verdad.

## Notas
- Este catálogo deriva del DEV-SRV del dominio Analítico.
- No reemplaza al CAT-CU maestro.
- Las reglas aquí listadas se usan como apoyo a implementación y validación backend.
- Debe mantenerse alineado con `SRV-ANA`, `SYS-MAP-002` y la regla de dominio estrictamente read-only.
