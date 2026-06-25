# SRV-TEC-IMPORT-EXCEL-001 — Diseño previo del importador Excel reutilizable

## Estado del documento

- Issue asociado: #205.
- Tipo de entregable: auditoría técnica y diseño previo.
- Este documento no implementa endpoints, componentes Flet, dependencias ni SQL.
- No cierra #205; prepara la implementación posterior.

## 1. Objetivo

Crear una base reusable para importadores Excel del sistema, sin implementar todavía el importador completo. La base deberá permitir que luego existan importadores específicos de inmuebles/lotes, personas, ventas y pagos, manteniendo ownership de dominios y evitando duplicar lógica de negocio crítica en frontend.

Clasificación del concepto:

- **Soporte transversal técnico:** lectura de archivos Excel, normalización de encabezados, mapeo, preview, validación estructural por fila y reporte técnico.
- **Núcleo de dominio:** cada importador específico que cree/modifique entidades pertenece al dominio dueño de esas entidades; por ejemplo, inmuebles/lotes al Dominio Inmobiliario, personas al dominio personas, ventas al dominio comercial y pagos al dominio financiero. El contexto de ejecución puede incluir usuario autenticado, sucursal, instalación, headers CORE-EF, `op_id` y trazabilidad técnica, pero ese contexto no transfiere ownership al Dominio Operativo ni define ownership del activo inmobiliario o de sus writes principales.
- **Compatibilidad heredada:** no aplica como modelo principal para este diseño; cualquier compatibilidad con planillas existentes deberá declararse por importador específico.

## 2. Alcance

El importador reusable propuesto cubre:

- lectura de archivo `.xlsx`;
- detección de hojas y columnas;
- normalización de encabezados;
- mapeo de columnas Excel contra campos destino;
- preview previo a confirmación;
- validación por fila;
- confirmación posterior mediante endpoints/commands existentes o futuros del dominio dueño;
- reporte final con totales y errores por fila.

## 3. Fuera de alcance

Queda fuera de este PR documental y de la primera base reusable:

- importador específico de inmuebles/lotes (#212), que pertenece al Dominio Inmobiliario;
- importación directa sin preview;
- cambios SQL;
- endpoints backend nuevos;
- sincronización offline;
- automatización externa;
- importación de ventas, pagos o personas en esta etapa;
- persistencia de archivo original o integración con documental real;
- definición de reglas de negocio propias de cada dominio.

## 4. Auditoría de documentación existente

### 4.1 Documentación técnica existente

- `backend/documentacion/DEV-SRV/dominios/tecnico/SRV-TEC-005-gestion-de-importacion-y-exportacion-tecnica.md` ya define un servicio técnico conceptual para importación/exportación de lotes, estados, procesamiento, idempotencia y trazabilidad. Ese documento está orientado a lotes técnicos persistidos y sincronización/procesamiento técnico, no a un wizard local de Excel con preview.
- `backend/documentacion/DEV-SRV/dominios/tecnico/00-INDICE-TECNICO.md` ya contiene un índice del dominio técnico con servicios CORE-EF, sincronización, conflictos, jobs, importación/exportación, respaldo y reportes.
- `backend/documentacion/CORE-EF/` y `backend/documentacion/DEV-SRV/dominios/tecnico/SRV-TEC-001-aplicacion-transversal-de-core-ef-en-commands.md` son referencia obligatoria para cualquier confirmación real que cree/modifique entidades sincronizables.
- `backend/documentacion/DEV-API/` documenta contratos por dominio; no se detectó un contrato específico de importación Excel reusable.
- `backend/documentacion/DECISIONES/` contiene decisiones por dominio e infraestructura; no existía una decisión específica para importador Excel reusable antes de este PR.
- `backend/documentacion/DER/` contiene referencias a importación/exportación técnica y archivos digitales en el modelo documental/sincronización; esas referencias no deben confundirse con el importador Excel local de planillas de carga.
- `frontend/flet_app/documentacion/UX-INMUEBLES.md` menciona explícitamente que la ficha de desarrollo/loteo prepara el camino para importación de inmuebles/lotes desde Excel, sin implementarla.
- `frontend/flet_app/documentacion/UX-PLAN-PAGO-V2-BLOQUES.md` y `frontend/flet_app/documentacion/UX-WIZARD-VENTA-COMPLETA-UNICO.md` consolidan patrones UX de preview antes de confirmación, bloqueo de confirmación con preview desactualizado y clasificación `PREVIEW_READLIKE`.

### 4.2 Documentación no encontrada o pendiente

No se encontró documentación específica vigente para:

- estructura reusable `ExcelColumn` / `ImportTargetField` / `ImportMapping`;
- componente Flet reusable de mapeo Excel;
- endpoint backend de preview/importación Excel;
- almacenamiento de archivos Excel importados;
- dependencia `openpyxl` instalada en backend o frontend;
- política cerrada de idempotencia para importaciones parciales por fila.

## 5. Auditoría de implementación existente

### 5.1 Frontend Flet reutilizable

Elementos reutilizables detectados:

- `frontend/flet_app/app/api_client.py`: cliente HTTP centralizado con patrón `ApiResult`, métodos por caso de uso y helper de headers CORE-EF para writes.
- `frontend/flet_app/app/components/loading_state.py` y `loading.py`: estados de carga reutilizables para lecturas o previews que demoren.
- `frontend/flet_app/app/components/error_state.py`: visualización reusable de errores sin exponer tracebacks.
- `frontend/flet_app/app/components/entity_table.py`: tabla simple reusable para listados y resultados tabulares.
- `frontend/flet_app/app/components/technical_output_panel.py`: panel técnico reusable para payloads/respuestas/debug controlado.
- `frontend/flet_app/app/router.py` y `shell.py`: patrón de navegación/rutas existentes.
- `frontend/flet_app/app/pages/plan_pago_v2_bloques.py`, `venta_create_wizard_page.py` y `venta_completa_wizard_v3_page.py`: patrones de wizard, preview, estados locales y bloqueo de confirmación.
- `frontend/flet_app/app/inmueble_alta_helpers.py` e `inmuebles_page.py`: helpers y formularios existentes para altas reales de inmuebles/desarrollos/unidades funcionales que pueden servir como destino de confirmación posterior.

No se detectó todavía:

- uso de `ft.FilePicker`;
- lectura local de archivos Excel;
- uso de `openpyxl`;
- uso de módulos Python `csv` para importación;
- parsing `.xlsx` reusable;
- componente específico para mapping de columnas;
- wizard reusable de importación de archivos.

### 5.2 Backend reutilizable

Elementos reutilizables detectados:

- routers existentes bajo `backend/app/api/routers/` para contratos HTTP por dominio;
- schemas bajo `backend/app/api/schemas/` para requests/responses tipadas;
- commands y services bajo `backend/app/application/**/commands` y `backend/app/application/**/services`;
- `backend/app/application/common/results.py` para patrón `AppResult`;
- `backend/app/application/common/commands.py` para `CommandContext`;
- helpers comunes CORE-EF en API para headers de writes sincronizables;
- outbox común en `backend/app/application/common/outbox.py` para comandos que emiten eventos;
- repositories bajo `backend/app/infrastructure/persistence/repositories/`.

No se detectó todavía:

- router técnico de importación Excel;
- service/command reusable de preview Excel;
- persistencia de lotes Excel;
- tablas SQL para importaciones Excel;
- tests backend específicos de importación Excel;
- dependencia `openpyxl` en `backend/requirements.txt`.

## 6. Decisión de arquitectura

Alternativas evaluadas:

### A) Frontend local con lectura Excel en Flet y confirmación vía endpoints existentes

Pros:

- menor superficie backend inicial;
- preview rápido sin persistir archivo ni crear contratos HTTP nuevos;
- permite reutilizar componentes Flet existentes de tabla, loading, error y panel técnico;
- facilita iterar con importadores específicos sin tocar SQL.

Contras:

- requiere incorporar lectura `.xlsx` en el entorno Flet en un PR posterior;
- riesgo de duplicar validaciones si se trasladan reglas de negocio al frontend;
- performance UI a controlar con archivos grandes;
- confirmación fila a fila debe cuidar idempotencia y errores parciales.

### B) Backend endpoint de preview/importación

Pros:

- centraliza parsing, validación y reglas cerca de services/repositorios;
- facilita tests de backend, trazabilidad y control de dependencias;
- mejor para archivos grandes o validaciones contra base.

Contras:

- exige diseñar contrato multipart/archivo y política de almacenamiento temporal;
- aumenta superficie CORE-EF si confirma entidades;
- podría adelantar infraestructura técnica que este PR no debe implementar;
- requiere definir lifecycle de archivo/lote antes de tener importador específico.

### C) Enfoque mixto

Pros:

- lectura/mapping/preview estructural inicial en frontend;
- validaciones contra backend mediante endpoints read-like o previews específicos cuando hagan falta;
- confirmación real por endpoints/commands del dominio dueño con CORE-EF;
- evita duplicar lógica crítica y mantiene la UI como orquestador.

Contras:

- requiere separar claramente validación estructural local vs validación de negocio backend;
- necesita contrato de errores por fila para no degradar UX;
- puede necesitar batching posterior para no saturar endpoints fila a fila.

### Decisión recomendada

Se recomienda el **enfoque mixto**:

1. Primera implementación: infraestructura reusable local en Flet para lectura, hojas, columnas, normalización, mapping y preview estructural.
2. Validaciones de negocio: mantenerlas en backend o consultarlas por endpoints read-like/previews específicos del dominio cuando correspondan.
3. Confirmación real: usar endpoints existentes o futuros commands backend del dominio dueño, con CORE-EF si crean/modifican entidades sincronizables.
4. No duplicar lógica de negocio crítica en frontend; el frontend solo normaliza, mapea y presenta errores estructurales o resultados devueltos por backend.

## 7. Modelo reusable propuesto

```python
ExcelColumn:
    index: int
    name: str
    normalized_name: str

ImportTargetField:
    key: str
    label: str
    required: bool
    aliases: list[str]
    validator: Callable | None
    normalizer: Callable | None

ImportMapping:
    target_field: str
    source_column: ExcelColumn | None

ImportRowPreview:
    row_number: int
    raw_values: dict[str, object]
    mapped_values: dict[str, object]
    errors: list[str]
    warnings: list[str]
    status: str  # VALID | INVALID | WARNING

ImportPreviewResult:
    columns: list[ExcelColumn]
    rows: list[ImportRowPreview]
    total_rows: int
    valid_rows: int
    invalid_rows: int

ImportConfirmResult:
    total: int
    created: int
    skipped: int
    failed: int
    errors_by_row: dict[int, list[str]]
```

Reglas del modelo:

- `ImportTargetField` no define semántica de dominio global; cada importador específico declara sus campos destino.
- `validator` local solo cubre estructura/formato básico; reglas de negocio definitivas pertenecen al dominio dueño.
- `ImportConfirmResult` debe soportar confirmaciones parciales sin ocultar filas fallidas.

## 8. Flujo funcional propuesto

1. Seleccionar archivo.
2. Leer hojas/columnas.
3. Elegir hoja.
4. Mapear columnas.
5. Generar preview.
6. Validar por fila.
7. Confirmar.
8. Mostrar reporte final.

## 9. Reglas UX

- Siempre debe existir preview antes de guardar.
- La confirmación debe bloquearse si el preview está ausente, inválido o desactualizado.
- Mostrar errores por fila y por campo cuando sea posible.
- No mostrar tracebacks al usuario final.
- Mostrar loading si la lectura, preview o validación tardan.
- Permitir cancelar antes de confirmar.
- Mostrar reporte final claro con totales, creados, omitidos, fallidos y detalle por fila.
- Mantener un panel técnico opcional para diagnóstico, sin reemplazar mensajes de usuario.

## 10. Reglas CORE-EF

- Lectura local de archivo: `QUERY_READLIKE`; CORE-EF **NO APLICA** porque no persiste ni modifica entidades.
- Preview local o backend sin persistencia: `PREVIEW_READLIKE`; CORE-EF **NO APLICA** porque no crea ni modifica entidades.
- Confirmación real que crea/modifica entidades sincronizables: `COMMAND_WRITE_NEGOCIO` o `COMMAND_WRITE_TECNICO` según caso; CORE-EF **APLICA**.
- Headers requeridos en confirmación real sincronizable: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; `If-Match-Version` si modifica entidad existente/versionada.
- Idempotencia: cada fila confirmada o lote confirmado deberá definir criterio explícito. Decisión pendiente por importador: `op_id` por lote con payload estable, `op_id` por fila, o combinación `id_importacion + row_number + payload_hash`.
- Outbox: aplica solo si el command del dominio dueño emite eventos; debe ocurrir en la misma transacción que el negocio.
- Lock lógico: aplica solo cuando el dominio dueño ya tenga entidad/operación incompatible a proteger.
- Versionado: aplica al modificar entidades versionadas; debe validar `version_registro` cuando corresponda.
- Rollback/transacción: si la confirmación es por lote, debe declarar si es all-or-nothing o parcial por fila; si es parcial, cada fila debe reportar estado final.
- Sincronización offline: **NO APLICA** en esta etapa; no se implementa.

## 11. Plan de implementación posterior

- **Etapa 1:** infraestructura reusable de lectura/mapeo/preview.
- **Etapa 2:** componente UI reusable de importación.
- **Etapa 3:** importador específico de inmuebles/lotes (#212), documentado e implementado como importador del Dominio Inmobiliario.
- **Etapa 4:** validaciones contra backend.
- **Etapa 5:** confirmación real y reporte final.
- **Etapa 6:** futuros importadores personas/ventas/pagos.

## 12. Riesgos detectados

- Archivos grandes que bloqueen la UI.
- Validaciones duplicadas frontend/backend.
- Idempotencia en importación parcial.
- Errores a mitad de importación.
- Duplicados dentro del archivo.
- Duplicados contra el sistema.
- Diferencia entre campos `nullable`, vacíos y omitidos.
- Performance de tablas Flet con muchas filas.
- Dependencias no instaladas (`openpyxl` no está en `backend/requirements.txt`).
- Trazabilidad insuficiente de importación si no se define lote/op_id.
- Mezcla accidental de dominios si un importador específico intenta crear entidades que no le pertenecen.

## 13. Criterios de aceptación para cerrar #205 en un PR posterior

Para cerrar la épica #205 deberá existir, como mínimo:

- base reusable de lectura/mapeo/preview;
- componente UI reusable;
- preview real antes de confirmación;
- validación por fila;
- confirmación reusable o simulada según etapa aprobada;
- reporte final;
- documentación de uso para importadores específicos;
- decisión CORE-EF verificable para cualquier confirmación write;
- pruebas acordes si se toca código, contratos HTTP, persistencia o flujos de dominio.

## 14. Validación contra arquitectura, implementación y tests

- Dominio correcto: el reusable queda clasificado como soporte transversal técnico; los writes pertenecen al dominio dueño de cada entidad. Para #212, desarrollos cuando correspondan, inmuebles —incluidos los identificados funcionalmente como lotes—, unidades funcionales si aplican, datos catastrales/registrales del inmueble y disponibilidad inmobiliaria inicial pertenecen al Dominio Inmobiliario. `lote` no queda documentado como entidad persistente separada.
- No invasión de dominios: este PR no mueve lógica ni crea endpoints; solo documenta diseño.
- Coherencia DEV-SRV: se alinea con `SRV-TEC-005` sin reemplazar la importación/exportación técnica de lotes persistidos.
- Coherencia DEV-API: no se declara contrato HTTP nuevo.
- Coherencia SQL: no se proponen tablas ni migraciones en este PR.
- Coherencia endpoints existentes: la confirmación posterior debe usar endpoints existentes o futuros debidamente documentados.
- Coherencia tests: al ser documentación/auditoría y no tocar código ejecutable, no se requieren tests unitarios nuevos.
