# Auditoría #374 — Tramos indexados en Venta completa V3

> **Vigencia contractual:** esta auditoría conserva evidencia del selector y del
> frontend existentes. Desde `#424`, `INT-FIN-005` fija para la deuda PPV2 futura
> un período objetivo mensual persistido y resolución exacta. El fallback al último
> valor anterior no puede materializar deuda; solo puede presentarse como
> estimación explícita. La implementación definitiva corresponde a `#423/#429`.

**Estado:** BLOQUEADO POR BRECHA CONTRACTUAL CONFIRMADA

## Alcance auditado

Este documento registra la auditoría previa obligatoria de #374. No se modifica
la lógica financiera, SQL, contratos ni reservas. El flujo actual está en
`prototypes/venta_completa_wizard_v3_prototype.py`, integrado por la página
`app/pages/venta_completa_wizard_v3_page.py`.

El concepto `TRAMO_CUOTAS` forma parte de la coordinación comercial del wizard.
El catálogo de índices, los valores publicados, la aplicabilidad por fecha y la
materialización siguen siendo semántica exclusiva de Financiero. El frontend no
puede consultar SQL ni calcular, interpolar o proyectar valores.

## Matriz de la pantalla actual

| Campo actual | Fuente | Editable | Técnico | Problema | Decisión |
| --- | --- | --- | --- | --- | --- |
| Capital, cuotas y primer vencimiento | draft local | Sí | No | Son datos del tramo y se validan antes de agregarlo. | Conservar. |
| Periodicidad `MENSUAL` | default local | No | No | Se muestra como dato fijo; no es una configuración indexada. | Conservar. |
| Método de liquidación | selector local | Sí | No | Permite `INDEXACION`, pero no guía la configuración posterior. | Conservar y complementar cuando exista catálogo. |
| `id_indice_financiero` | texto manual | Sí | **Sí** | Expone un identificador backend y obliga a conocerlo. | Reemplazar solamente cuando exista query HTTP de catálogo. |
| Código visual | texto libre | Sí | Sí | No se vincula a un catálogo; puede no corresponder al ID. | Eliminar al integrar catálogo real. |
| Fecha base | texto/calendario | Sí | No | La UI sólo valida formato, no puede informar qué valor publicado aplica. | Conservar como fecha solicitada; resolver sólo con query backend. |
| Valor base | texto manual | Sí | **Sí** | El usuario debe conocer/copiar un valor financiero. | Autocompletar sólo desde valor publicado consultado. |
| Modo/base/generación/política/frecuencia | texto de defaults | No | **Sí** | La pantalla muestra enums/defaults internos sin contrato de lectura. | Mostrar etiquetas sólo si un contrato Financiero las entrega; no inventar valores. |

Actualmente “Agregar tramo” valida capital, cuotas, fecha, ID, fecha base y
valor base; si todo es válido, guarda un `TramoCuotasWizardDraft` local.
El botón global “Siguiente” depende además de que todos los tramos estén
agregados y de las reglas comerciales/preview existentes. Al volver desde los
pasos posteriores, los drafts se conservan en `WizardVentaCompletaV3State`; al
cancelar un formulario, el draft del formulario se limpia. Los tramos guardados
se pueden quitar, pero no existe edición de un tramo ya agregado.

## Contratos backend realmente disponibles

Se inspeccionaron routers, schemas, repositorios y tests. No existe un endpoint
HTTP que liste `indice_financiero`, ni un endpoint HTTP que liste/consulte
`indice_financiero_valor` por índice y fecha. `ApiClient` tampoco tiene métodos
para ellos.

La capacidad de resolución ya existe **dentro de la infraestructura backend** en
`IndiceFinancieroRepository`, y está cubierta por tests de repositorio. Hay dos
resolvers, ninguno de los cuales constituye un contrato HTTP ni puede ser
invocado directamente por Flet:

- `get_valor_publicado_por_id_y_fecha(id_indice_financiero, fecha_objetivo)`
  recibe un ID positivo y la fecha objetivo;
- `get_valor_publicado_por_codigo_y_fecha(codigo_indice_financiero,
  fecha_objetivo)` normaliza el código con `strip().upper()` y no consulta si el
  resultado queda vacío.

Ambos consultan un índice activo no eliminado y valores no eliminados con estado
`PUBLICADO`, `fecha_publicacion` informada y `fecha_valor <= fecha_objetivo`;
ordenan por `fecha_valor` descendente y seleccionan el último aplicable. El
repositorio convierte la fila seleccionada mediante el mismo mapper interno;
no se afirma identidad de implementación fuera de lo verificado. Los tests
cubren la búsqueda por código exacta, el fallback al último anterior, futuros,
estados no publicables, inactividad, normalización y soft-delete; y también la
búsqueda por ID con su validación de ID no positivo.

Los endpoints de venta existentes aceptan el comando ya resuelto:

- `POST /api/v1/ventas/plan-pago-v2/preview`;
- `POST /api/v1/ventas/directa/confirmar-venta-completa`;
- `POST /api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa`.

El bloque comercial admite `id_indice_financiero`, `fecha_base_indice` y
`valor_base_indice`. El preview/generación puede resolver materialización como
parte de la lógica Financiera, pero no es catálogo ni una consulta de valor base
para un draft: requiere que el frontend ya posea el ID y el valor base. Tampoco
es correcto llamarlo para inferir catálogo/valores o decidir estados.

## Brecha que bloquea la implementación UX

#374 exige seleccionar por catálogo real y autocompletar el valor aplicable sin
exponer IDs. La brecha no es ausencia de capacidad de resolución en backend:
esta ya existe en los dos resolvers internos anteriores. La brecha es que esa
capacidad no está expuesta mediante queries HTTP read-only consumibles por
frontend.

El incremento previo de Financiero debe definir y documentar, como mínimo:

1. **Query 1 — Catálogo de índices.** Una query HTTP read-only para listar
   índices activos con los campos reales disponibles y documentados (ID técnico,
   código, nombre, unidad, periodicidad/frecuencia y estado, además de su orden
   y paginación contractual).
2. **Query 2 — Valor aplicable.** Una query HTTP read-only que reciba una fecha
   objetivo y resuelva el valor publicado aplicable por ID, por código o por una
   única interfaz contractual que acepte exactamente uno de ambos
   identificadores. Debe reutilizar
   `get_valor_publicado_por_id_y_fecha` y
   `get_valor_publicado_por_codigo_y_fecha` según corresponda, sin reimplementar
   en service/router la regla SQL de aplicabilidad ni trasladarla a Flet.
3. Schemas de respuesta y errores contractuales para el caso sin valor aplicable,
   incluida la fecha efectiva y fuente cuando exista resultado.

No se propone ni se implementa aquí un endpoint, SQL ni un cálculo alternativo:
ello invadiría el ownership Financiero y contradice las restricciones del issue.
Hasta que exista ese contrato, tampoco es válido reemplazar los campos actuales
por CAC/IPC/ICL fijos, mocks, texto libre “amigable” o valores inferidos.

## Resultado y próximo incremento permitido

El incremento frontend solicitado queda **NO IMPLEMENTABLE** con los endpoints
reales auditados. La corrección necesaria es una issue/PR previa y acotada de
Financiero para las queries read-only anteriores, con DEV-API, router, schemas,
repository y tests contractuales. Recién entonces #374 puede implementar:
selector, estados de carga/error, autocompletado, mensajes por campo,
resumen de pendientes, edición de tramo y pruebas de navegación, sin cálculo
financiero local.

Mientras tanto, la lógica exclusivamente backend comprende la selección del
valor aplicable, la política ante ausencia, el coeficiente, importes, generación
y los estados `PROYECTADA`/`EMITIDA`. El frontend sólo podrá presentar la
respuesta y construir el comando válido una vez que el contrato exista.
