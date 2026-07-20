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

La segunda ejecución reutiliza el plan V2 existente. Para eliminar solamente el
escenario identificado por su código estable:
`PYTHONPATH=. ENV=dev python scripts/create_plan_pago_v2_demo.py --clean`.
La limpieza elimina en orden las relaciones financieras, plan, bloques,
indexaciones, corridas y venta de ese escenario; no usa IDs fijos. El script
requiere `ENV` explícito y rechaza cualquier entorno que no sea `dev` o `test`.

## Decisión CORE-EF

Es una utilidad técnica local (`COMMAND_WRITE_TECNICO`), no una API. Reutiliza
el servicio real de generación y la transacción abarca seed, identificación y
generación; un error hace rollback. No aplican headers HTTP, If-Match, outbox o
lock de una API productiva.
