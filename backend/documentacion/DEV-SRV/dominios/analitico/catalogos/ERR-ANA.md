# ERR-ANA — Errores del dominio Analítico

## Objetivo
Definir errores funcionales y de validación asociados a consultas del dominio Analítico.

## Alcance del dominio
Incluye errores de criterios de consulta, corte temporal, disponibilidad de datos, consolidación, agregación y consistencia analítica.

---

## A. Errores de criterios y filtros

### ERR-ANA-001 — criterio_consulta_analitica_invalido
- codigo: criterio_consulta_analitica_invalido
- descripcion: los criterios de consulta informados no son válidos para la vista analítica solicitada.
- tipo: validacion
- aplica_a: consultas_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-002 — filtro_analitico_inconsistente
- codigo: filtro_analitico_inconsistente
- descripcion: los filtros informados no son consistentes entre sí o con el universo de análisis.
- tipo: validacion
- aplica_a: consultas_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-003 — agrupacion_analitica_invalida
- codigo: agrupacion_analitica_invalida
- descripcion: la agrupación solicitada no es válida para los datos o dimensiones de la consulta.
- tipo: validacion
- aplica_a: consultas_analiticas, agregaciones_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

## B. Errores temporales y de disponibilidad

### ERR-ANA-004 — rango_temporal_invalido
- codigo: rango_temporal_invalido
- descripcion: el rango temporal o la fecha de corte informados no cumplen las condiciones requeridas por la consulta.
- tipo: validacion
- aplica_a: historico_analitico, consultas_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-005 — datos_analiticos_no_disponibles
- codigo: datos_analiticos_no_disponibles
- descripcion: no se encuentran disponibles los datos necesarios para construir la vista analítica solicitada.
- tipo: funcional
- aplica_a: consultas_analiticas
- origen: DEV-SRV
- es_reintento_valido: sí
- observaciones: refiere a ausencia lógica de datos en las fuentes, no a indisponibilidad técnica de las mismas.

## C. Errores de consistencia y agregación

### ERR-ANA-007 — inconsistencia_analitica
- codigo: inconsistencia_analitica
- descripcion: la información consolidada presenta inconsistencias incompatibles con la vista analítica solicitada.
- tipo: integridad
- aplica_a: vistas_analiticas, reportes_analiticos
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-008 — error_de_agregacion
- codigo: error_de_agregacion
- descripcion: no fue posible consolidar correctamente los datos por una inconsistencia en la agregación analítica.
- tipo: integridad
- aplica_a: agregaciones_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-009 — doble_conteo_detectado
- codigo: doble_conteo_detectado
- descripcion: se detectó una superposición de datos que compromete la validez del resultado analítico.
- tipo: integridad
- aplica_a: agregaciones_analiticas, metricas_analiticas
- origen: DEV-SRV
- es_reintento_valido: no

### ERR-ANA-010 — proyeccion_analitica_invalida
- codigo: proyeccion_analitica_invalida
- descripcion: la proyección solicitada no respeta la semántica disponible en los dominios origen.
- tipo: validacion
- aplica_a: proyecciones_analiticas, cruces_interdominio
- origen: DEV-SRV
- es_reintento_valido: no

## D. Errores de resultado

### ERR-ANA-011 — resultado_analitico_incompleto
- codigo: resultado_analitico_incompleto
- descripcion: la consulta produjo un resultado parcial, existente pero incompleto, por limitación de datos disponibles o de las fuentes consultadas.
- tipo: funcional
- aplica_a: vistas_analiticas, reportes_analiticos
- origen: DEV-SRV
- es_reintento_valido: sí

### ERR-ANA-012 — historico_analitico_inconsistente
- codigo: historico_analitico_inconsistente
- descripcion: el histórico analítico no puede reconstruirse de forma consistente con las fuentes funcionales disponibles.
- tipo: integridad
- aplica_a: historico_analitico
- origen: DEV-SRV
- es_reintento_valido: no

## Notas
- Este catálogo deriva del DEV-SRV del dominio Analítico.
- No reemplaza al CAT-CU maestro.
- Los errores aquí listados se usan como apoyo a implementación, validación y manejo consistente de respuestas backend.
- Debe mantenerse alineado con `SRV-ANA`, `SYS-MAP-002` y la regla de dominio estrictamente read-only.
