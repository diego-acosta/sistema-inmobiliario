# AUDITORIA-BACKEND-FIN - Backend Python vs schema financiero

Estado: AUDITORIA BACKEND / SIN CAMBIOS DE CODIGO

Fecha: 2026-04-29

## 1. Alcance

Se audito el backend Python y tests contra el schema financiero actualizado.

Alcance revisado:

- `backend/app`
- `backend/tests`
- `backend/scripts/reset_db.bat`
- `backend/database/schema_inmobiliaria_20260418.sql` solo como referencia

No se modifico codigo Python, tests, SQL ni documentacion existente.

## 2. Resumen ejecutivo

No se encontraron usos operativos en `backend/app` de los nombres fisicos viejos:

- `codigo_concepto`
- `codigo_obligacion`
- `importe_original`
- `tipo_obligacion`

Tampoco se encontro uso operativo de `tipo_obligacion` como eje central.

El backend financiero implementado actualmente es mucho mas chico que el schema/documentacion nuevos: solo cubre alta, lectura y listado de `relacion_generadora`. No hay implementacion Python vigente para:

- crear obligaciones financieras;
- consultar obligaciones;
- consultar composicion;
- consultar conceptos financieros;
- registrar pagos financieros;
- aplicar imputaciones;
- calcular saldos;
- generar cronogramas;
- materializar obligaciones desde planes.

La principal brecha no es una ruptura inmediata por columnas renombradas, sino ausencia de backend para el nuevo modelo fisico `relacion_generadora -> obligacion_financiera -> composicion_obligacion -> concepto_financiero`.

## 3. Hallazgos por severidad

### BLOQUEA IMPORTACION/ARRANQUE

No se detectaron referencias Python que bloqueen importacion por el cambio de schema financiero.

Archivos revisados relevantes:

- `backend/app/main.py`
- `backend/app/api/routers/financiero_router.py`
- `backend/app/api/schemas/financiero.py`
- `backend/app/application/financiero/**`
- `backend/app/infrastructure/persistence/repositories/financiero_repository.py`

Observacion: no se ejecuto refactor ni importacion forzada; la auditoria se baso en lectura y busqueda estatica.

### BLOQUEA TESTS

No se detectaron tests que usen columnas viejas de `concepto_financiero`, `obligacion_financiera` o `composicion_obligacion`.

Referencias encontradas a `obligacion_financiera`:

| Archivo | Linea | Uso | Impacto |
|---|---:|---|---|
| `backend/tests/test_reservas_venta_generate_venta.py` | 388 | `SELECT COUNT(*) FROM obligacion_financiera` | Compatible: solo cuenta filas. |
| `backend/tests/test_ventas_confirm.py` | 205 | `SELECT COUNT(*) FROM obligacion_financiera` | Compatible: solo cuenta filas. |
| `backend/tests/test_ventas_definir_condiciones_comerciales.py` | 310 | `SELECT COUNT(*) FROM obligacion_financiera` | Compatible: solo cuenta filas. |

Estos tests no bloquean por el rename de columnas porque no seleccionan campos.

Riesgo de test futuro: si se agregan tests de creacion de obligaciones con nombres viejos (`importe_original`, `codigo_obligacion`, `importe`) fallaran contra el schema nuevo.

### BLOQUEA ENDPOINT FINANCIERO

Hay una brecha funcional concreta en `SERVICIO_TRASLADADO`:

| Archivo | Linea | Hallazgo | Impacto |
|---|---:|---|---|
| `backend/app/application/financiero/services/create_relacion_generadora_service.py` | 14 | `TIPOS_ORIGEN_VALIDOS` incluye `SERVICIO_TRASLADADO`. | El servicio lo acepta conceptualmente. |
| `backend/app/application/financiero/services/create_relacion_generadora_service.py` | 62 | Valida `SERVICIO_TRASLADADO` contra `factura_servicio`. | El backend intenta soportarlo. |
| `backend/database/schema_inmobiliaria_20260418.sql` | 819 | Trigger `trg_relacion_generadora_polimorfica` solo permite `venta` y `contrato_alquiler`. | Crear relacion con `SERVICIO_TRASLADADO` fallara en SQL con error interno. |
| `backend/app/api/routers/financiero_router.py` | 128 | El mensaje de error declara `VENTA`, `CONTRATO_ALQUILER` o `SERVICIO_TRASLADADO`. | El contrato expuesto promete un origen que el SQL no permite. |

Esto no deriva del rename de columnas, pero si bloquea un endpoint financiero documentado por el propio backend.

### DESALINEACION DOCUMENTAL/NAMING

No se encontraron usos de nombres viejos en backend operativo. La desalineacion actual es por ausencia de schemas/servicios/repositorios para entidades nuevas o ampliadas.

Faltan modelos/API internos para:

- `concepto_financiero.codigo_concepto_financiero`
- `concepto_financiero.nombre_concepto_financiero`
- `obligacion_financiera.codigo_obligacion_financiera`
- `obligacion_financiera.importe_total`
- `obligacion_financiera.moneda`
- `obligacion_financiera.estado_obligacion`
- `composicion_obligacion.importe_componente`
- `composicion_obligacion.saldo_componente`
- `composicion_obligacion.moneda_componente`
- `aplicacion_financiera.id_composicion_obligacion`

### RIESGO FUTURO

- El backend financiero actual no materializa obligaciones; cualquier endpoint nuevo debe usar los nombres fisicos nuevos desde el inicio.
- Los triggers de SQL recalculan saldos, pero no hay repositorio Python que los use ni contrato API que exponga el resultado.
- `aplicacion_financiera` existe y soporta `id_composicion_obligacion`, pero no hay servicio Python de imputacion por componente.
- `reset_db.bat` sigue apuntando al schema y seeds correctos; no requiere cambio por nombre de archivo.
- Los archivos `__pycache__` aparecen en el workspace, pero no fueron considerados fuente.

## 4. Archivos afectados

### Backend financiero actual

| Archivo | Estado frente al schema nuevo | Cambio minimo necesario |
|---|---|---|
| `backend/app/api/routers/financiero_router.py` | Compatible para `relacion_generadora`; promete `SERVICIO_TRASLADADO` aunque SQL lo bloquea. | Alinear origenes permitidos con SQL o ampliar SQL/backend de forma coherente. |
| `backend/app/api/schemas/financiero.py` | Solo modela `relacion_generadora`; no cubre obligaciones/composiciones/conceptos. | Agregar schemas nuevos cuando se implemente materializacion/consulta. |
| `backend/app/application/financiero/services/create_relacion_generadora_service.py` | Compatible para `VENTA` y `CONTRATO_ALQUILER`; desalineado para `SERVICIO_TRASLADADO`. | Remover temporalmente `SERVICIO_TRASLADADO` o ajustar SQL/origen completo. |
| `backend/app/application/financiero/services/get_relacion_generadora_service.py` | Compatible. | Sin cambio minimo por schema financiero nuevo. |
| `backend/app/application/financiero/services/list_relaciones_generadoras_service.py` | Compatible. | Sin cambio minimo por schema financiero nuevo. |
| `backend/app/infrastructure/persistence/repositories/financiero_repository.py` | Compatible para `relacion_generadora`; no implementa obligaciones/composiciones/conceptos. | Agregar metodos separados para conceptos, obligaciones, composiciones e imputaciones. |

### Tests

| Archivo | Estado frente al schema nuevo | Cambio minimo necesario |
|---|---|---|
| `backend/tests/test_fin_rel_gen_create.py` | Compatible para origenes vigentes; no cubre `SERVICIO_TRASLADADO`. | Agregar test o ajustar contrato cuando se cierre la brecha de origen. |
| `backend/tests/test_fin_rel_gen_get.py` | Compatible. | Sin cambio minimo. |
| `backend/tests/test_reservas_venta_generate_venta.py` | Compatible; solo cuenta obligaciones. | Sin cambio minimo por rename. |
| `backend/tests/test_ventas_confirm.py` | Compatible; solo cuenta obligaciones. | Sin cambio minimo por rename. |
| `backend/tests/test_ventas_definir_condiciones_comerciales.py` | Compatible; solo cuenta obligaciones. | Sin cambio minimo por rename. |

## 5. Referencias a nombres viejos

Resultado de busqueda en `backend/app`, `backend/tests` y `backend/scripts`:

- `codigo_concepto`: sin referencias.
- `codigo_obligacion`: sin referencias.
- `importe_original`: sin referencias.
- `tipo_obligacion`: sin referencias.
- `tipo obligacion` / `tipo obligación`: sin referencias.

Referencias vigentes a tablas financieras:

- `obligacion_financiera`: solo en tres tests que cuentan filas.
- `composicion_obligacion`: sin referencias en backend/tests.
- `concepto_financiero`: sin referencias en backend/tests.
- `aplicacion_financiera`: sin referencias en backend/tests.

## 6. Endpoints y servicios revisados

| Flujo | Existe en backend Python | Estado |
|---|---:|---|
| Crear `relacion_generadora` | SI | Implementado para `VENTA` y `CONTRATO_ALQUILER`; `SERVICIO_TRASLADADO` desalineado con SQL. |
| Consultar `relacion_generadora` | SI | Implementado. |
| Listar `relacion_generadora` | SI | Implementado. |
| Crear obligaciones | NO | Pendiente. |
| Consultar obligaciones | NO | Pendiente. |
| Consultar composicion | NO | Pendiente. |
| Consultar conceptos financieros | NO | Pendiente. |
| Registrar pagos | NO | Pendiente. |
| Aplicar imputaciones | NO | Pendiente. |
| Calcular saldos | NO | Pendiente en backend; SQL tiene triggers. |
| Generar cronogramas | NO | Pendiente. |
| Materializar obligaciones | NO | Pendiente. |

## 7. Cambios minimos necesarios

1. Alinear `SERVICIO_TRASLADADO`:
   - opcion conservadora: quitarlo temporalmente de `TIPOS_ORIGEN_VALIDOS` y del mensaje del router;
   - opcion funcional: ampliar `trg_relacion_generadora_polimorfica` y tests para aceptar `factura_servicio` o el origen definido.

2. Crear contratos Pydantic para:
   - `concepto_financiero`;
   - `obligacion_financiera`;
   - `composicion_obligacion`;
   - `aplicacion_financiera`.

3. Agregar metodos de repositorio con nombres fisicos nuevos:
   - `codigo_concepto_financiero`;
   - `codigo_obligacion_financiera`;
   - `importe_total`;
   - `importe_componente`;
   - `saldo_componente`.

4. Implementar primero lectura de catalogo y obligaciones antes de materializacion/escritura compleja.

5. Agregar tests de SQL/backend para:
   - seed de conceptos financieros;
   - alta de obligacion con composicion;
   - imputacion por componente;
   - recalc de `saldo_pendiente` y `saldo_componente`.

## 8. Orden recomendado de implementacion

1. Cerrar decision `SERVICIO_TRASLADADO` vs trigger SQL.
2. Agregar tests de repositorio financiero contra el schema nuevo.
3. Implementar lectura de `concepto_financiero`.
4. Implementar lectura de obligaciones y composiciones.
5. Implementar materializacion de obligaciones con composiciones.
6. Implementar registro/aplicacion de pagos por componente.
7. Recién despues exponer endpoints completos documentados en `DEV-API-FIN-001`.

## 9. Tests que probablemente fallen

Con el backend actual, no se identifican tests existentes que fallen solo por los renames financieros, porque no usan las columnas renombradas.

Tests nuevos o futuros fallaran si:

- crean `obligacion_financiera` con `codigo_obligacion` o `importe_original`;
- crean `composicion_obligacion` con `importe`;
- crean o consultan `concepto_financiero` con `codigo_concepto`;
- intentan crear `relacion_generadora` con `tipo_origen = SERVICIO_TRASLADADO` sin ajustar SQL;
- esperan endpoints de obligaciones, composiciones, pagos o imputaciones ya implementados.

## 10. Que NO tocar todavia

- No tocar dominios comercial, locativo o inmobiliario para generar deuda automaticamente.
- No agregar `tipo_obligacion`.
- No crear compatibilidad con nombres viejos en backend.
- No implementar pagos antes de definir distribucion por componente.
- No exponer endpoints completos de obligaciones sin repositorio y tests de saldos.
- No cambiar tests no financieros salvo que una implementacion futura los afecte directamente.

## 11. Prompt recomendado para el proximo paso

Trabaja dentro del workspace. Implementa el primer corte backend contra el nuevo schema financiero, sin tocar SQL ni documentacion. Primero alinea `SERVICIO_TRASLADADO` con la decision vigente: si no se amplia SQL, quitalo temporalmente del backend y ajusta tests. Luego agrega repositorio, schemas y tests para lectura de `concepto_financiero` y lectura de `obligacion_financiera` con `composicion_obligacion`, usando solo nombres fisicos nuevos (`codigo_concepto_financiero`, `codigo_obligacion_financiera`, `importe_total`, `importe_componente`, `saldo_componente`). No implementar pagos ni materializacion hasta que pasen esos tests.
