# DEV-ARCH-OPE-001 — Freeze arquitectónico del dominio Operativo

## 1. Objetivo
Congelar el criterio arquitectónico vigente del dominio `operativo` para asegurar alineación entre `SYS-MAP-002`, `DEV-SRV`, `CAT-CU` y los catálogos de implementación ya corregidos.

## 2. Alcance del dominio
El dominio `operativo` incluye:
- sucursales
- instalaciones
- caja operativa
- movimientos de caja
- cierre de caja
- consultas operativas

El dominio `operativo` no incluye:
- tareas
- agenda
- workflow interno
- incidencias
- seguimiento

## 3. Responsabilidad del dominio
El dominio `operativo` es responsable de modelar la operación física y organizativa del sistema en materia de sucursales, instalaciones y caja operativa.

Su responsabilidad incluye:
- definir y mantener sucursales e instalaciones
- gestionar la apertura y cambios de estado de caja operativa
- registrar y anular movimientos de caja
- ejecutar el cierre de caja como operación única del dominio
- proveer consultas y reportes operativos del propio dominio

No le corresponde:
- definir lógica financiera primaria
- gestionar usuarios, permisos o auditoría institucional
- resolver sincronización, locks o integridad técnica
- absorber semántica de gestión operativa interna

## 4. Límites del dominio

### con financiero
`operativo` gestiona la ejecución física de caja: apertura, movimientos y cierre.

`financiero` gestiona el estado lógico de obligaciones, pagos, imputaciones y resultados financieros.

La relación entre ambos dominios existe cuando un `movimiento_caja` debe vincularse con `movimiento_financiero`, pero esa vinculación no traslada lógica financiera al dominio `operativo`.

### con administrativo
`operativo` utiliza contexto administrativo usuario responsable y permisos de operación cuando corresponda.

No administra:
- usuarios
- roles
- permisos
- autorizaciones
- auditoría global

### con técnico
`operativo` consume mecanismos transversales de versionado, idempotencia, outbox y trazabilidad definidos por `CORE-EF` y por el dominio `tecnico`.

No define:
- sincronización
- conflictos técnicos
- locks
- integridad técnica

### con analítico
`operativo` provee información de lectura y trazabilidad para reportes operativos y para consumo por `analitico`.

`analitico` puede consolidar información operativa, pero no redefine su semántica ni reemplaza sus consultas operativas base.

## 5. Modelo conceptual

### entidades principales
- `sucursal`
- `instalacion`
- `caja_operativa`
- `movimiento_caja`
- `cierre_caja`

### naturaleza de caja operativa
`caja_operativa` representa una unidad de operación física vinculada a instalación, sucursal y usuario responsable.

Su función es habilitar:
- apertura
- cambio de estado
- registro de movimientos
- cierre

No debe confundirse con caja financiera ni con una cuenta financiera del dominio `financiero`.

### cierre de caja
`cierre_caja` representa el resultado persistente del proceso de cierre de una caja operativa.

El cierre de caja:
- es una sola operación del dominio
- consolida movimientos
- registra totales, diferencias y observaciones cuando corresponda
- actualiza el estado final de la caja

La validación de cierre forma parte interna de la ejecución del cierre y no constituye caso de uso independiente.

## 6. Reglas de modelado

### casos de uso
Los casos de uso del dominio deben representar operaciones reales respaldadas por `SRV-OPE`:
- alta, modificación, baja lógica y consulta de sucursal
- alta, modificación, baja lógica y consulta de instalación
- apertura, cambio de estado y consulta de caja operativa
- registro, anulación y consulta de movimientos de caja
- ejecución y consulta de cierre de caja
- consultas y reportes operativos

No deben modelarse como casos de uso:
- validaciones internas del flujo
- pasos intermedios no expuestos como operación
- semántica de tareas o workflow interno

### estados
Los estados del dominio deben representar estados persistentes de:
- `sucursal`
- `instalacion`
- `caja_operativa`
- `movimiento_caja`
- `cierre_caja`

No deben representar:
- resultados de ejecución
- estados técnicos
- workflow inventado
- estados transversales del dominio

### eventos
Los eventos del dominio deben derivar de operaciones write reales:
- creación, modificación y baja lógica de sucursal
- creación, modificación y baja lógica de instalación
- apertura de caja operativa
- cambio de estado de caja
- registro y anulación de movimiento de caja
- ejecución de cierre de caja

No deben modelarse como eventos autónomos:
- validaciones internas
- estados intermedios no persistentes
- eventos de workflow no respaldados por `SRV-OPE`

## 7. Decisiones congeladas
- `operativo` queda congelado como dominio de sucursales, instalaciones, caja operativa, movimientos, cierres y consultas operativas.
- `gestion_operativa` no forma parte de este dominio.
- `cierre de caja` es una sola operación.
- `validación de cierre` no es caso de uso independiente.
- los estados del dominio son persistentes y no técnicos.
- los eventos del dominio derivan solo de operaciones write reales.
- la vinculación con `financiero` no habilita a `operativo` a definir lógica financiera.

## 8. Criterio de evolución
Toda evolución futura del dominio debe:
- respetar el bounded context actual
- mantener separación explícita con `gestion_operativa`
- conservar la frontera con `financiero`, `administrativo`, `tecnico` y `analitico`
- evitar incorporar pasos internos como casos de uso, estados o eventos
- apoyarse en `SYS-MAP-002`, `DEV-SRV`, `CAT-CU` y catálogos corregidos antes de introducir cambios documentales

## 9. Notas
- Este documento congela el criterio arquitectónico vigente del dominio `operativo`.
- No reemplaza la documentación detallada de servicios ni catálogos, pero fija el límite semántico del dominio.
- Debe mantenerse alineado con `SYS-MAP-002`, `DEV-SRV`, `CAT-CU` y con los catálogos `CU-OPE`, `RN-OPE`, `ERR-OPE`, `EVT-OPE` y `EST-OPE`.
- Los reportes operativos del dominio no sustituyen reporting analitico agregado del dominio `analitico`
