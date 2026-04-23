# DEV-ARCH-ANA-001 — Freeze arquitectónico del dominio Analítico

## 1. Objetivo
Congelar el criterio arquitectónico vigente del dominio `analitico` para asegurar alineación entre `SYS-MAP-002`, `DEV-SRV`, los catálogos `CU/RN/ERR/EVT/EST` ya generados y los freezes existentes de `personas`, `comercial` y `operativo`.

## 2. Alcance del dominio
El dominio `analitico` es estrictamente read-only.

Su alcance incluye:
- consultas analíticas
- consolidación de información
- agregación de datos
- proyección de vistas
- reportes analíticos
- métricas e indicadores derivados de dominios origen

Las métricas e indicadores son derivados de datos fuente y no constituyen verdad funcional autónoma ni reemplazan la semántica de los dominios origen.

No incluye:
- operaciones write
- modificación de estado
- definición de entidades de negocio propias
- redefinición de semántica funcional
- sustitución de dominios funcionales como fuente primaria de verdad

## 3. Responsabilidad del dominio
El dominio `analitico` es responsable de consultar, consolidar, agregar y proyectar información proveniente de dominios funcionales y transversales del sistema.

Su responsabilidad incluye:
- construir vistas analíticas
- ejecutar consultas analíticas
- generar reportes analíticos
- consolidar información interdominio
- exponer métricas e indicadores derivados

No le corresponde:
- crear, modificar o eliminar información
- definir reglas de negocio
- definir estados persistentes
- definir eventos de negocio
- recalcular lógica funcional primaria

## 4. Límites del dominio

### con personas
`analitico` consume identidad, relaciones y datos de consulta del dominio `personas`.

No redefine:
- persona base
- clasificación funcional
- roles contextuales
- ownership semántico de sujeto

### con comercial
`analitico` consume reservas, ventas, condiciones comerciales, instrumentos, cesiones y escrituración como fuentes de lectura.

No define:
- cliente
- comprador
- vendedor
- semántica comercial de la operación

### con locativo
`analitico` consume contratos, reservas locativas, condiciones y relaciones del circuito locativo.

No define:
- semántica locativa
- roles locativos
- reglas contractuales

### con financiero
`analitico` consume deuda, pagos, saldos, cobranzas, mora, refinanciaciones y demás resultados definidos por `financiero`.

No recalcula:
- intereses
- saldos primarios
- mora como lógica fuente
- obligaciones ni imputaciones

No sustituye a `financiero` como fuente de verdad.

### con operativo
`analitico` consume sucursales, instalaciones, cajas operativas, movimientos y cierres como fuentes de lectura.

No ejecuta:
- apertura de caja
- movimientos
- cierre
- operaciones físicas del dominio `operativo`

### con técnico
`analitico` puede consumir soporte técnico transversal para lectura o trazabilidad, sin asumir ownership de infraestructura ni de mecanismos técnicos.

No define:
- infraestructura
- sincronización
- idempotencia
- versionado
- locks

## 5. Modelo conceptual

### vistas analíticas
Las vistas analíticas son proyecciones consolidadas construidas a partir de datos existentes en dominios origen.

No constituyen entidades de negocio propias ni fuente primaria de verdad.

### consultas analíticas
Las consultas analíticas son operaciones read-only que:
- filtran
- comparan
- agregan
- consolidan
- proyectan

Su semántica depende de los dominios origen y no del dominio `analitico` como dueño funcional del dato.

### reportes analíticos
Los reportes analíticos son salidas derivadas de vistas o consultas consolidadas del dominio.

No implican persistencia obligatoria, no crean estados nuevos del sistema y no reemplazan reportes operativos o funcionales de los dominios origen.

## 6. Reglas de modelado

### naturaleza read-only
- `analitico` solo consulta, consolida, agrega y proyecta
- `analitico` nunca crea, modifica ni elimina
- toda ejecución del dominio debe ser sin efectos persistentes
- el dominio no debe generar verdad paralela del sistema

### dependencia de dominios origen
- toda semántica proviene de los dominios origen
- `analitico` no redefine reglas, estados ni condiciones funcionales
- la calidad del resultado depende de la calidad y disponibilidad lógica de las fuentes
- `analitico` no sustituye ownership semántico de ningún dominio funcional

### agregación y consolidación
- la agregación debe hacerse sobre datos ya definidos por dominios origen
- la consolidación no debe recalcular lógica funcional primaria
- las comparaciones temporales deben respetar la semántica temporal definida por cada dominio origen
- la proyección analítica no debe convertirse en modelo de negocio autónomo

## 7. Decisiones congeladas
- `analitico` es un dominio estrictamente de lectura.
- `analitico` no ejecuta operaciones write.
- `analitico` no es fuente primaria de verdad.
- `analitico` no define entidades de negocio propias.
- `analitico` no redefine reglas de negocio, estados ni condiciones funcionales.
- `analitico` consume semántica de `personas`, `comercial`, `locativo`, `financiero`, `operativo` y otros dominios, sin absorber su ownership.
- `analitico` no sustituye a ningún dominio funcional.

## 8. Criterio de evolución
Toda evolución futura del dominio debe:
- mantener su naturaleza estrictamente read-only
- evitar incorporar writes, estados persistentes o eventos de negocio
- preservar la dependencia semántica de dominios origen
- evitar recalcular lógica funcional primaria
- respetar los límites ya fijados con `personas`, `comercial`, `locativo`, `financiero`, `operativo` y `tecnico`
- apoyarse en `SYS-MAP-002`, `DEV-SRV`, catálogos analíticos y freezes arquitectónicos existentes antes de introducir cambios

## 9. Notas
- Este documento congela el criterio arquitectónico vigente del dominio `analitico`.
- No reemplaza la documentación detallada de servicios ni catálogos, pero fija el límite semántico del dominio.
- Debe mantenerse alineado con `SYS-MAP-002`, `DEV-SRV`, `CU-ANA`, `RN-ANA`, `ERR-ANA`, `EVT-ANA`, `EST-ANA` y con los freezes existentes de `personas`, `comercial` y `operativo`.
