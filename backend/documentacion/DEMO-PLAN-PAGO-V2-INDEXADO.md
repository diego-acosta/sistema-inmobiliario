# Demo reproducible — Plan Pago V2 indexado

## Uso

El script `scripts/create_plan_pago_v2_demo.py` identifica la venta confirmada
del seed UI como `DEMO-VTA-CUOTAS-PPV2-INDEXADA` y materializa el plan por
bloques con el servicio real. Comercial conserva la venta; Financiero conserva
obligaciones e indexación. No crea endpoints ni toca Administrativo, #346,
#349, #365 o la UX de #374.

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
rechaza cualquier entorno que no sea `dev` o `test`.

## Decisión CORE-EF

Es una utilidad técnica local (`COMMAND_WRITE_TECNICO`), no una API. Reutiliza
el servicio real de generación y la transacción abarca seed, identificación y
generación; un error hace rollback. No aplican headers HTTP, If-Match, outbox o
lock de una API productiva.
