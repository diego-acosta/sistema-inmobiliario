# Demo reproducible — Plan Pago V2 indexado

## Uso

El script crea una venta exclusiva `DEMO-VTA-CUOTAS-PPV2-INDEXADA`; nunca
renombra ni elimina `DEMO-VTA-CUOTAS`. Reutiliza comprador, objeto e índices
del seed UI, mientras que plan y obligaciones se materializan con el servicio
real. La corrida aplicada se prepara y aplica mediante los servicios reales;
pendiente/fallida son fixtures DEV/test de presentación.

1. Con PostgreSQL activo, ejecutar el reset oficial:
   `cd backend && scripts/reset_db.sh`.
2. Ejecutar: `PYTHONPATH=. ENV=dev python scripts/create_plan_pago_v2_demo.py`.
3. Iniciar backend/frontend, localizar el código en **Ventas** y abrir
   `/ventas/{id}` (el ID se imprime). El seed `CAC_DEMO` tiene valores
   explícitos y ficticios; nunca usar en producción.

La segunda ejecución inspecciona y valida el escenario completo antes de
reutilizarlo; no resetea bloques, no crea fixtures, no persiste preview ni
vuelve a aplicar la corrida. Para eliminar solamente el
escenario identificado por su código estable:
`PYTHONPATH=. ENV=dev python scripts/create_plan_pago_v2_demo.py --clean`.
La limpieza elimina en orden las relaciones financieras, plan, bloques,
indexaciones, corridas y venta de ese escenario; no usa IDs fijos. El script
requiere `ENV` explícito y rechaza cualquier entorno que no sea `dev` o `test`.

## Contrato y garantías verificadas (#373)

El fixture conserva los tres bloques y tres obligaciones del Plan Pago V2:
**índice al nacimiento**, **proyectada sin índice** y **corrida posterior**.
La segunda no materializa indexación ni corrida aplicada vigente; la primera
expone capital, ajuste, importe vigente, fecha/valor base, fecha/valor aplicado
y coeficiente. La tercera se prepara solamente para su bloque y se aplica con
`AplicarIndexacionCuotasV2Service`; su corrida `APLICADA`, detalle `ELEGIBLE`,
indexación y composición `AJUSTE_INDEXACION` son datos reales.

El fix #376 está incorporado: la aplicación relee la versión bloqueada final y
la igualdad es estricta entre
`corrida_indexacion_financiera_detalle.version_resultante` y
`obligacion_financiera.version_registro`; no se infiere con `version_esperada +
1`. Las únicas corridas de presentación son una `PENDIENTE_APLICACION` y una
`FALLIDA` DEV/test: la pendiente no se presenta como aplicada y la fallida
incluye código, etapa y diagnóstico visibles en el contrato integral.

La prueba de aislamiento crea un segundo plan válido y alcanzable por abril de
2026 con `CAC_DEMO`, captura sus bloques, obligaciones, versiones, importes,
saldos, composiciones, indexaciones y corridas, y verifica que `create()` no
modifica ninguno. La corrida real queda limitada a `Demo: corrida posterior`.

`create()` es un no-op observable en su segunda ejecución: conserva IDs,
versiones, timestamps, op IDs, trazabilidad, corridas, detalles, composiciones,
indexaciones y outbox. Si la venta exclusiva existe pero no pasa la inspección
completa, el script falla con una indicación de ejecutar `--clean`; nunca intenta
repararla mediante resets parciales.

## Límite transaccional real (#380)

Seeds, venta, plan, reseteos iniciales, fixtures de presentación y el preview
persistido se preparan antes de la aplicación real. Mientras esa aplicación no
se invocó, un error del script hace rollback del grafo exclusivo creado en la
sesión.

`AplicarIndexacionCuotasV2Service` confirma mediante un `commit` interno de su
repository. Ese commit es el límite transaccional real: después no hay rollback
externo que pueda revertir venta, plan, corrida aplicada, ajuste, trazabilidad o
outbox ya confirmados. Por eso no se ejecutan fixtures, resets, inserciones,
deletes ni validaciones funcionales después de llamar al servicio. El resumen
se construye con los IDs y cantidades ya conocidas; si imprimirlo falla, se
informa una advertencia y no se presenta como rollback de una creación exitosa.

La primera creación deja exactamente una corrida pendiente, fallida y aplicada,
y una sola composición/indexación activa por obligación aplicable. `clean()` borra sólo el código exclusivo y puede
ejecutarse dos veces; preserva venta base, comprador/personas/roles, inmueble y
unidad, `CAC_DEMO` y sus valores, conceptos financieros, sucursal e instalación.

La ruta frontend continúa siendo `/ventas/{id_venta}`. Los datos compartidos
son seeds reutilizados y nunca se eliminan desde esta utilidad.

## Decisión CORE-EF

Es una utilidad técnica local (`COMMAND_WRITE_TECNICO`), no una API. Reutiliza
el servicio real de generación y la transacción abarca seed, identificación y
generación; un error hace rollback. No aplican headers HTTP, If-Match, outbox o
lock de una API productiva.

Para la aplicación real, el contexto CORE-EF se resuelve desde PostgreSQL y se
envía al servicio junto con `If-Match-Version` de la corrida. La idempotencia
del fixture se define por el código exclusivo de venta y los motivos/bloques de
corrida; no publica outbox ni toma lock lógico porque no expone un endpoint
sincronizable. El versionado de obligaciones sí aplica y queda cubierto por la
igualdad estricta anterior.
