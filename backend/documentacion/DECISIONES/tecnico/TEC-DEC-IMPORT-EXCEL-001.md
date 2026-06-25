# TEC-DEC-IMPORT-EXCEL-001 — Decisión de arquitectura para importador Excel reutilizable

## Estado

Aceptada como diseño previo para #205.

## Contexto

Se necesita preparar un importador Excel reutilizable sin implementar todavía el importador completo. La solución debe alinearse con la documentación existente, respetar ownership de dominios y evitar que el frontend duplique reglas críticas de negocio.

Ya existe documentación técnica conceptual sobre importación/exportación de lotes técnicos en `DEV-SRV/dominios/tecnico/SRV-TEC-005-gestion-de-importacion-y-exportacion-tecnica.md`, pero no existe un diseño específico para una experiencia Flet de lectura de Excel, mapping, preview, validación por fila, confirmación y reporte.

## Decisión

Adoptar un **enfoque mixto** para el importador Excel reusable:

1. La primera implementación deberá resolver lectura local, selección de hoja, normalización de encabezados, mapeo y preview estructural en frontend Flet.
2. Las validaciones de negocio definitivas deberán quedar en backend o consultarse mediante endpoints read-like/previews específicos del dominio dueño.
3. La confirmación real deberá usar endpoints existentes o futuros commands del dominio dueño, no un servicio transversal que invada semántica de personas, comercial, inmobiliario, operativo o financiero. Para inmuebles/lotes, el dominio dueño es inmobiliario; el contexto de usuario/autorización, auditoría, headers CORE-EF, `op_id` y trazabilidad técnica no transfiere ownership al Dominio Operativo.
4. Cualquier endpoint write que cree/modifique entidades sincronizables deberá aplicar CORE-EF desde su primer PR de implementación.
5. La épica #205 no queda cerrada con esta decisión; esta decisión prepara el PR de implementación posterior.

## Alternativas consideradas

### Frontend local únicamente

Rechazada como estrategia completa porque podría duplicar reglas de negocio críticas y dificultar validaciones contra base, aunque sí se acepta para lectura/mapping/preview estructural inicial.

### Backend endpoint único de importación Excel

Rechazada para la primera etapa porque adelanta contratos, dependencias, almacenamiento temporal y posible persistencia de lotes antes de definir el primer importador específico. Puede incorporarse después si archivos grandes, validaciones contra base o auditoría de importación lo justifican.

### Enfoque mixto

Aceptado porque separa responsabilidades: frontend para interacción y estructura del archivo; backend para reglas de negocio, persistencia, idempotencia, outbox y versionado cuando corresponda.

## Decisión CORE-EF

- Lectura local de archivo: `QUERY_READLIKE`; CORE-EF **NO APLICA**.
- Preview local o backend sin persistencia: `PREVIEW_READLIKE`; CORE-EF **NO APLICA**.
- Confirmación real sincronizable: `COMMAND_WRITE_NEGOCIO` o `COMMAND_WRITE_TECNICO`; CORE-EF **APLICA**.
- Headers para confirmación real: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; `If-Match-Version` si modifica entidad existente/versionada.
- Idempotencia: pendiente de cerrar por importador específico; no se permite implementar confirmación real sin definir criterio explícito por lote/fila/payload.
- Outbox: aplica solo si el command del dominio dueño emite eventos; debe compartir transacción con el cambio de negocio.
- Lock lógico: aplica según entidad y operaciones incompatibles del dominio dueño.
- Versionado: aplica si modifica entidades versionadas.
- Tests: no aplican en este PR documental; serán obligatorios para PRs que creen/modifiquen endpoints write.

## Consecuencias

- La base reusable no define campos de negocio globales; cada importador específico declarará sus `ImportTargetField`.
- El importador de inmuebles/lotes (#212) deberá documentar su mapping y validaciones como importador específico del Dominio Inmobiliario, sin delegar los writes principales al Dominio Operativo ni invadir otros dominios.
- Si se agrega `openpyxl`, se hará en un PR de implementación con justificación y pruebas.
- Si se crea backend de preview/importación, deberá tener contrato DEV-API y tests propios.
- No se modifica SQL ni se crea persistencia de importaciones en esta decisión.

## Referencias

- `backend/documentacion/DEV-SRV/dominios/tecnico/SRV-TEC-IMPORT-EXCEL-001.md`
- `backend/documentacion/DECISIONES/inmobiliario/INM-DEC-IMPORT-EXCEL-001.md`
- `backend/documentacion/DEV-SRV/dominios/tecnico/SRV-TEC-005-gestion-de-importacion-y-exportacion-tecnica.md`
- `backend/documentacion/CORE-EF/`
- `frontend/flet_app/documentacion/UX-INMUEBLES.md`
- `frontend/flet_app/documentacion/UX-PLAN-PAGO-V2-BLOQUES.md`
- `frontend/flet_app/documentacion/UX-WIZARD-VENTA-COMPLETA-UNICO.md`
