# SYS-MAP-002 — Mapa del sistema actualizado

## 1. Objetivo
Definir el mapa vigente de dominios del sistema con criterio orientado a implementación, tomando como base el `SYS-MAP-001` histórico y priorizando como fuente de verdad operativa la documentación actual de `backend/documentacion/DEV-SRV`.

## 2. Alcance
Este documento establece:
- los dominios actuales reconocidos por el sistema
- el alcance funcional esperado de cada dominio
- sus límites principales
- las relaciones de dependencia entre dominios
- las decisiones de nomenclatura que corrigen desalineaciones históricas

No reemplaza la documentación detallada por dominio ni el `SYS-MAP-001`, pero pasa a ser la referencia principal para naming y partición de dominios del sistema.

## 3. Principios de arquitectura
- El backend documentado en `DEV-SRV` prevalece como fuente de verdad para naming y alcance implementable.
- Los dominios deben separarse por responsabilidad principal y no por conveniencia documental histórica.
- Los dominios transversales no deben quedar absorbidos dentro de dominios funcionales específicos.
- Los límites entre dominios deben reducir duplicación semántica y evitar contaminación entre negocio, operación y técnica.
- Las consultas analíticas y los procesos técnicos no reemplazan la lógica primaria de los dominios funcionales.

## 4. Dominios del sistema

| Dominio | Nombre canónico | Alcance breve | Estado |
|---|---|---|---|
| PER | `personas` | sujeto base, identificación, domicilios, contactos, relaciones y representación | consolidado |
| INM | `inmobiliario` | desarrollos, inmuebles, unidades, atributos, disponibilidad, ocupación y estructura del activo | consolidado |
| COM | `comercial` | reservas de venta, ventas, condiciones comerciales, instrumentos de compraventa, cesiones y escrituración | consolidado |
| LOC | `locativo` | contratos de alquiler, condiciones locativas, garantías, renovaciones, rescisiones y ocupación locativa | consolidado |
| FIN | `financiero` | relaciones generadoras, obligaciones, pagos, imputación, mora, emisión y reportes financieros operativos | consolidado |
| DOC | `documental` | documentos lógicos, versionado, asociaciones documentales, plantillas, emisión y numeración | consolidado |
| ADM | `administrativo` | usuarios, roles, permisos, autorizaciones, auditoría, configuración y parametrización | consolidado |
| OPE | `operativo` | sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consulta operativa | consolidado |
| GOP | `gestion_operativa` | agenda, vencimientos, tareas, seguimiento, incidencias y observaciones internas | conceptual, no consolidado en backend |
| TEC | `tecnico` | sincronización, operaciones distribuidas, conflictos técnicos, import/export, respaldo e integridad técnica | consolidado |
| ANA | `analitico` | consultas analíticas, reportes consolidados, indicadores y vistas agregadas | consolidado |

## 5. Descripción breve de cada dominio

### 5.1 personas
Dominio transversal que define a la persona como sujeto base del sistema. No depende de comercial ni de locativo y no debe confundirse con usuarios administrativos.

### 5.2 inmobiliario
Dominio núcleo del activo inmobiliario. Administra desarrollos, inmuebles, unidades funcionales, atributos físicos, relaciones estructurales, disponibilidad y ocupación.

### 5.3 comercial
Dominio de compraventa. Administra reservas de venta, ventas, condiciones comerciales, instrumentos jurídicos de compraventa, cesiones y escrituración. No absorbe el dominio de personas.

### 5.4 locativo
Dominio contractual de alquileres. Administra contratos, condiciones locativas, garantías, renovaciones, rescisiones y ocupación asociada al circuito locativo.

### 5.5 financiero
Dominio del motor financiero unificado. Gestiona relaciones generadoras, obligaciones, pagos, imputaciones, mora, emisión, caja financiera y reportes financieros operativos.
El dominio financiero gestiona el estado lógico de obligaciones, pagos e imputaciones.
El dominio operativo gestiona la ejecución física de caja, incluyendo apertura, movimientos y cierre.
Ambos dominios no deben duplicar responsabilidades.

### 5.6 documental
Dominio transversal de documentos. Administra documento lógico, versionado, asociaciones documentales, plantillas, emisión y numeración sin reemplazar las entidades jurídicas principales de otros dominios.

### 5.7 administrativo
Dominio transversal de control institucional. Administra usuarios, roles, permisos, autorizaciones, auditoría y configuración global del sistema.

### 5.8 operativo
Dominio de operación real del sistema en backend. Administra sucursales, instalaciones, caja operativa, movimientos de caja, cierres y consultas operativas consolidadas.

### 5.9 gestion_operativa
Dominio conceptual heredado del `SYS-MAP-001` para agenda, tareas, seguimientos, vencimientos, incidencias y observaciones internas. Hoy no está consolidado como dominio real en `DEV-SRV`, pero se preserva como categoría arquitectónica para evitar colisión semántica con `operativo`.

### 5.10 tecnico
Dominio de infraestructura transversal. Baja a servicios concretos de backend la sincronización, operaciones distribuidas, conflictos, versionado, import/export, respaldo e integridad técnica.
El dominio técnico no contiene lógica de negocio.
Solo implementa mecanismos transversales como sincronización, idempotencia, versionado, locks e integridad técnica.

### 5.11 analitico
Dominio exclusivamente de lectura. Consolida información de los demás dominios para consultas analíticas, reportes y soporte a decisiones sin generar efectos persistentes.
El dominio analítico no debe ejecutar operaciones write.
No puede modificar estado de otros dominios.
Solo consume información para consultas y reportes.

## 6. Relaciones entre dominios

- `personas` alimenta a `comercial`, `locativo`, `financiero`, `documental` y `administrativo`.
- `inmobiliario` es base para `comercial`, `locativo`, `documental`, `analitico` y parte de `operativo`.
- `comercial` genera relaciones que pueden derivar en obligaciones de `financiero`.
- `locativo` genera relaciones contractuales que alimentan a `financiero`.
- `inmobiliario` puede originar obligaciones en `financiero` por registro de `factura_servicio` cuando exista contrato implementado; el sistema no emite esa factura.
- `financiero` consume origen comercial, locativo u otro origen compatible documentado, pero mantiene motor único de deuda y cobro.
- `documental` se asocia transversalmente a entidades de `inmobiliario`, `comercial`, `locativo`, `financiero`, `personas` y `administrativo`.
- `administrativo` controla acceso, parametrización y auditoría global sobre todos los dominios.
- `operativo` interactúa con `administrativo` por sucursal y usuario, y con `financiero` por movimientos y caja operativa.
- `operativo` genera información que puede impactar en `analitico` y en procesos de conciliación dentro de `financiero`.
- `gestion_operativa`, cuando se implemente como dominio real, deberá consumir estados y eventos de otros dominios sin reemplazar su semántica.
- `tecnico` soporta sincronización, integridad e idempotencia para dominios write sincronizables.
- `analitico` consume información de todos los dominios funcionales y transversales, sin convertirse en fuente primaria de verdad.

### 6.1 Flujo conceptual pendiente: factura_servicio

Estado: `SQL IMPLEMENTADO` / `API-BACKEND-EVENTO-CONSUMER NO IMPLEMENTADOS`

```text
INMOBILIARIO
  registra factura_servicio
        |
        v
EVENTO conceptual pendiente
  factura_servicio_registrada
        |
        v
FINANCIERO
  crea relacion_generadora
  crea obligacion_financiera
```

El dominio inmobiliario no crea obligaciones financieras. `factura_servicio` existe como tabla SQL estructural para registrar el origen, pero no existe API/backend para operarla y no publica eventos reales. El dominio financiero conserva ownership exclusivo sobre `relacion_generadora`, `obligacion_financiera` y calculo de deuda.

El evento conceptual pendiente `factura_servicio_registrada` debe ser idempotente. La clave conceptual recomendada es `id_factura_servicio`; el consumidor financiero no debe crear obligaciones duplicadas ante reintentos. Este evento queda `NO IMPLEMENTADO`, no existe consumer financiero y no se genera `relacion_generadora` ni `obligacion_financiera` desde `factura_servicio`.

## 7. Decisiones de nomenclatura

### 7.1 Operativo vs Gestión Operativa
Se congela la siguiente corrección conceptual:

- `operativo` = dominio real de backend para:
  - sucursales
  - instalaciones
  - caja operativa
  - movimientos de caja
  - cierre de caja
  - consulta y reporte operativo

- `gestion_operativa` = nombre reservado para el dominio conceptual del `SYS-MAP-001` que cubre:
  - agenda
  - vencimientos
  - tareas
  - seguimiento interno
  - observaciones
  - incidencias

Esta separación evita la colisión de significado detectada entre el mapa histórico y la implementación backend actual.

### 7.2 Personas como dominio autónomo
`personas` se reconoce como dominio transversal independiente. No debe quedar embebido dentro de `comercial` ni de `locativo`.

### 7.3 Nombres canónicos vigentes
Los nombres canónicos de dominios a usar en documentación actualizada son:
- `personas`
- `inmobiliario`
- `comercial`
- `locativo`
- `financiero`
- `documental`
- `administrativo`
- `operativo`
- `gestion_operativa`
- `tecnico`
- `analitico`

## 8. Estado de implementación por dominio

| Dominio | Situación actual en backend | Comentario |
|---|---|---|
| `personas` | consolidado | catálogos y servicios consistentes |
| `inmobiliario` | consolidado | fuerte alineación con alcance núcleo del activo |
| `comercial` | consolidado | alineado con compraventa |
| `locativo` | consolidado | alineado con contratos y ciclo locativo |
| `financiero` | consolidado | motor financiero unificado documentado |
| `documental` | consolidado | transversal y consistente |
| `administrativo` | consolidado | transversal y consistente |
| `operativo` | consolidado | ya alineado a sucursales, instalaciones y caja |
| `gestion_operativa` | pendiente (no implementado en DEV-SRV) | reconocido conceptualmente, sin dominio DEV-SRV consolidado |
| `tecnico` | consolidado | alineado con CORE-EF y sincronización |
| `analitico` | consolidado | dominio read-only bien delimitado |

## 9. Compatibilidad con SYS-MAP-001

- `SYS-MAP-001` se conserva como documento histórico y conceptual.
- `SYS-MAP-002` no replica su estructura por capas y módulos extensos.
- El contenido histórico sigue siendo útil para entender alcance amplio del sistema, pero no debe usarse como naming operativo directo cuando contradice al backend.
- La principal rectificación respecto del mapa histórico es la separación entre:
  - `operativo` en backend
  - `gestion_operativa` como nombre actualizado del viejo operativo funcional interno
- También se consolida `personas` como dominio transversal explícito, corrigiendo su dispersión histórica dentro de módulos comerciales y contractuales.

## Notas
- Este documento pasa a ser la fuente de verdad vigente para naming de dominios del sistema.
- La fuente histórica se preserva en `SYS-MAP-001.md`.
- La fuente de implementación prevalente sigue siendo `backend/documentacion/DEV-SRV`.
- Todo ajuste futuro de dominios debe contrastarse contra `DEV-SRV`, `CAT-CU` y este documento antes de propagarse al resto de la documentación.
