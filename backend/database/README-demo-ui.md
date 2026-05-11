# Seed demo UI

`seed_demo_ui.sql` es un seed opcional para bases de desarrollo. No reemplaza `seed_minimo.sql`, no se usa en tests y no modifica estructura SQL.

Requiere una base ya inicializada con el baseline tecnico y `seed_minimo.sql`, incluyendo `sucursal=1`, `instalacion=1`, roles/conceptos base y constraints vigentes.

Aplicacion:

```bash
psql -d inmobiliaria_dev -f backend/database/seed_demo_ui.sql
```

Validacion sin persistir cambios en una base local:

```bash
psql -d inmobiliaria_dev -v ON_ERROR_STOP=1 -c "BEGIN" -f backend/database/seed_demo_ui.sql -c "ROLLBACK"
```

Datos incluidos:

- Partes demo con documentos, contactos y domicilios principales.
- Inmuebles y unidades funcionales para casos normal, sin vigente y ambiguo.
- Servicios demo y responsables asociados a inmuebles/unidades.
- Contrato de alquiler activo con roles locativos, objeto y condicion economica.
- Ventas demo `CONTADO`, `ANTICIPO_Y_SALDO` y `CUOTAS_FIJAS`.
- Relaciones generadoras, obligaciones, composiciones y obligados financieros.
- Pago scoped demo para la venta contado cancelada.

Consultas UI esperadas:

- `GET /api/v1/personas?q=DEMO`
- `GET /api/v1/inmuebles?q=DEMO`
- `GET /api/v1/ventas?q=DEMO`
- `GET /api/v1/contratos-alquiler?q=DEMO`
