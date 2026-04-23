# CU-ANA — Casos de uso del dominio Analítico

## Objetivo
Definir los casos de uso del dominio Analítico.

## Alcance
Incluye reportes, indicadores, consultas consolidadas y análisis histórico del sistema.

---

## A. Reportes operativos

### CU-ANA-001 — Generación de reporte operativo
- tipo: read
- objetivo: Generar un reporte operativo consolidado a partir de información disponible en los dominios de ejecución del sistema.
- entidades: reporte_operativo, vista_analitica
- criticidad: media

### CU-ANA-002 — Consulta de estado operativo consolidado
- tipo: read
- objetivo: Consultar el estado operativo consolidado del sistema sobre información agregada.
- entidades: estado_operativo_consolidado, vista_analitica
- criticidad: media

### CU-ANA-003 — Consulta de carga de trabajo
- tipo: read
- objetivo: Consultar la carga de trabajo consolidada para análisis de distribución y seguimiento.
- entidades: carga_trabajo, vista_analitica
- criticidad: media

## B. Reportes financieros

### CU-ANA-004 — Generación de reporte de deuda
- tipo: read
- objetivo: Generar un reporte analítico de deuda sobre información consolidada del dominio financiero.
- entidades: reporte_financiero, vista_analitica
- criticidad: alta

### CU-ANA-005 — Generación de reporte de cobranzas
- tipo: read
- objetivo: Generar un reporte analítico de cobranzas sobre información consolidada del dominio financiero.
- entidades: reporte_financiero, vista_analitica
- criticidad: alta

### CU-ANA-006 — Consulta de estado financiero consolidado
- tipo: read
- objetivo: Consultar el estado financiero consolidado del sistema sin alterar la lógica del dominio origen.
- entidades: estado_financiero_consolidado, vista_analitica
- criticidad: alta

## C. Reportes comerciales

### CU-ANA-007 — Generación de reporte comercial
- tipo: read
- objetivo: Generar un reporte comercial consolidado sobre operaciones, reservas y seguimiento comercial.
- entidades: reporte_comercial, vista_analitica
- criticidad: media

### CU-ANA-008 — Consulta de pipeline comercial
- tipo: read
- objetivo: Consultar el pipeline comercial consolidado a partir de estados e interacciones del flujo comercial.
- entidades: pipeline_comercial, vista_analitica
- criticidad: media

### CU-ANA-009 — Consulta de conversiones comerciales
- tipo: read
- objetivo: Consultar conversiones comerciales sobre información histórica y agregada del dominio origen.
- entidades: conversion_comercial, vista_analitica
- criticidad: media

## D. Indicadores y métricas

### CU-ANA-010 — Consulta de indicadores operativos
- tipo: read
- objetivo: Consultar indicadores operativos calculados sobre información consolidada del sistema.
- entidades: indicador, vista_analitica
- criticidad: media

### CU-ANA-011 — Consulta de indicadores financieros
- tipo: read
- objetivo: Consultar indicadores financieros derivados de datos consolidados del dominio financiero.
- entidades: indicador, vista_analitica
- criticidad: alta

### CU-ANA-012 — Consulta de indicadores comerciales
- tipo: read
- objetivo: Consultar indicadores comerciales construidos sobre información agregada del dominio comercial.
- entidades: indicador, vista_analitica
- criticidad: media

### CU-ANA-013 — Consulta de métricas del sistema
- tipo: read
- objetivo: Consultar métricas generales del sistema para análisis y seguimiento transversal.
- entidades: metrica, vista_analitica
- criticidad: media

## E. Análisis histórico

### CU-ANA-014 — Consulta de evolución histórica financiera
- tipo: read
- objetivo: Consultar la evolución histórica financiera del sistema respetando la lógica del dominio origen.
- entidades: historico_financiero, vista_analitica
- criticidad: alta

### CU-ANA-015 — Consulta de evolución histórica comercial
- tipo: read
- objetivo: Consultar la evolución histórica comercial sobre datos consolidados del sistema.
- entidades: historico_comercial, vista_analitica
- criticidad: media

### CU-ANA-016 — Consulta de evolución histórica operativa
- tipo: read
- objetivo: Consultar la evolución histórica operativa a partir de información agregada de ejecución.
- entidades: historico_operativo, vista_analitica
- criticidad: media

### CU-ANA-017 — Consulta de evolución de activos inmobiliarios
- tipo: read
- objetivo: Consultar la evolución histórica de activos inmobiliarios sobre información consolidada del dominio origen.
- entidades: historico_inmobiliario, vista_analitica
- criticidad: media

## F. Consultas analíticas

### CU-ANA-018 — Consulta analítica consolidada
- tipo: read
- objetivo: Consultar una vista analítica consolidada a partir de múltiples dominios del sistema.
- entidades: vista_analitica
- criticidad: alta

### CU-ANA-019 — Consulta de vistas agregadas del sistema
- tipo: read
- objetivo: Consultar vistas agregadas del sistema para análisis transversal y soporte a decisiones.
- entidades: vista_analitica
- criticidad: media

### CU-ANA-020 — Consulta de información cruzada entre dominios
- tipo: read
- objetivo: Consultar información cruzada entre dominios preservando la semántica de cada dominio origen.
- entidades: vista_analitica, cruce_analitico
- criticidad: alta

### CU-ANA-021 — Consulta de tendencias
- tipo: read
- objetivo: Consultar tendencias del sistema sobre series históricas y datos agregados.
- entidades: tendencia, vista_analitica
- criticidad: media

---

## Reglas

1. Todas las operaciones son read-only.
2. No generar efectos persistentes.
3. No duplicar lógica de negocio.
4. No redefinir estados funcionales.
5. Los cálculos deben apoyarse en reglas del dominio origen.
6. No utilizar lógica analítica para alterar comportamiento del sistema.

---

## Notas

- El dominio Analítico consume información de todos los dominios.
- No modifica datos ni estados.
- Su objetivo es proveer visibilidad y soporte a la toma de decisiones.
- Los reportes deben respetar la lógica del dominio origen (financiero, locativo, comercial, etc.).
- Este dominio no reemplaza lógica funcional ni técnica.
- Puede evolucionar hacia modelos de reporting o BI sin afectar el núcleo del sistema.
- Las entidades analíticas mencionadas en este documento (reporte, indicador, métrica, vista analítica, histórico, tendencia, cruce analítico, etc.) representan capacidades funcionales del dominio Analítico.
- La implementación física concreta de estas estructuras puede variar y debe alinearse con el modelo real de reporting, read models o BI del sistema.
- Este documento no define por sí mismo tablas analíticas persistentes ni reemplaza la semántica de los dominios origen.