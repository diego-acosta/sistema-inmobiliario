# EST-ANA — Estados del dominio Analítico

## Objetivo
Definir estados conceptuales de resultados, vistas y ejecuciones del dominio Analítico.

## Alcance del dominio
Incluye estados de disponibilidad y consistencia de resultados analíticos, sin incorporar workflow de negocio ni semántica write.

---

## A. Estados de resultado analítico

### EST-ANA-001 — Resultado disponible
- codigo: resultado_disponible
- tipo: operativo
- aplica_a: resultado_analitico
- descripcion: el resultado solicitado fue construido y se encuentra disponible para su consumo.
- estado_inicial: no
- estado_final: sí

### EST-ANA-002 — Resultado vacío
- codigo: resultado_vacio
- tipo: operativo
- aplica_a: resultado_analitico
- descripcion: la consulta se resolvió válidamente pero no produjo registros dentro de los criterios solicitados.
- estado_inicial: no
- estado_final: sí

### EST-ANA-003 — Datos incompletos
- codigo: datos_incompletos
- tipo: operativo
- aplica_a: resultado_analitico, vista_analitica
- descripcion: el resultado contiene información parcial o faltante respecto del universo esperado y afecta su calidad o confiabilidad analítica, sin implicar cambio de estado de negocio.
- estado_inicial: no
- estado_final: sí

### EST-ANA-004 — Inconsistente
- codigo: inconsistente
- tipo: operativo
- aplica_a: resultado_analitico, vista_analitica
- descripcion: el resultado no puede considerarse confiable por inconsistencias detectadas en consolidación o agregación, sin implicar cambio de estado de negocio.
- estado_inicial: no
- estado_final: sí

## B. Estados de ejecución analítica

### EST-ANA-005 — En proceso de generación
- codigo: en_proceso_de_generacion
- tipo: operativo
- aplica_a: consulta_analitica, reporte_analitico
- descripcion: la consulta o reporte se encuentra en construcción o consolidación de resultados como estado observable de ejecución, no persistente y no constitutivo de workflow del dominio.
- estado_inicial: sí
- estado_final: no
- observaciones: aplica solo cuando la ejecución sea observable como estado operativo y no debe persistirse como estado de entidad en el modelo de datos.

### EST-ANA-006 — Generación finalizada
- codigo: generacion_finalizada
- tipo: operativo
- aplica_a: consulta_analitica, reporte_analitico
- descripcion: la construcción del resultado analítico finalizó correctamente como estado observable de ejecución, no persistente y no constitutivo de workflow del dominio.
- estado_inicial: no
- estado_final: sí
- observaciones: no debe persistirse como estado de entidad en el modelo de datos.

## Notas
- Este catálogo deriva del DEV-SRV del dominio Analítico.
- No reemplaza al CAT-CU maestro.
- Los estados aquí listados se usan como apoyo a implementación, validación y consistencia del dominio backend.
- Debe mantenerse alineado con `SRV-ANA`, `SYS-MAP-002` y la regla de dominio estrictamente read-only.
