# EVT-ANA — Eventos del dominio Analítico

## Objetivo
Definir eventos observables mínimos del dominio Analítico como apoyo a trazabilidad de consultas y reportes.

## Alcance del dominio
Incluye solo eventos observables de ejecución o generación de resultados analíticos. No replica eventos de negocio de otros dominios.

---

## A. Eventos de consultas analíticas

### EVT-ANA-001 — Consulta analítica ejecutada
- codigo: consulta_analitica_ejecutada
- descripcion: se ejecutó una consulta analítica sobre una vista o servicio del dominio.
- origen_principal: SRV-ANA-001
- entidad_principal: consulta_analitica
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí
- observaciones: aplica como evento técnico de trazabilidad de lectura cuando corresponda instrumentarlo.

## B. Eventos de reportes analíticos

### EVT-ANA-002 — Reporte analítico generado
- codigo: reporte_analitico_generado
- descripcion: se generó un reporte analítico a partir de una vista consolidada del dominio.
- origen_principal: SRV-ANA-001
- entidad_principal: reporte_analitico
- tipo_evento: auditoria
- sincronizable: no
- genera_trazabilidad: sí
- observaciones: aplica solo cuando la generación del reporte sea observable en la implementación.

## Notas
- Este catálogo deriva del DEV-SRV del dominio Analítico.
- No reemplaza al CAT-CU maestro.
- Los eventos aquí listados se usan como apoyo a auditoría, historización liviana y trazabilidad backend.
- Debe mantenerse alineado con `SRV-ANA`, `SYS-MAP-002` y la regla de dominio estrictamente read-only.
- Si una implementación concreta no instrumenta estos eventos, el catálogo debe interpretarse como mínimo y no expansivo.
