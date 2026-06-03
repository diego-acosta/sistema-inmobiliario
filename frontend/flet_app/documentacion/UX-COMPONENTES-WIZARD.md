# UX-COMPONENTES-WIZARD — Buscadores reutilizables para wizards Flet

## Propósito

El buscador reutilizable demo define una experiencia visual común para buscar y seleccionar registros antes de rehacer los wizards Flet pantalla por pantalla.

Su objetivo es reemplazar campos manuales crudos como `id_persona`, `id_inmueble`, `id_unidad_funcional` o `id_reserva_venta` por una selección humana, verificable y reutilizable.

## Alcance actual

- Es un prototipo UI/demo aislado.
- Usa datos demo en memoria.
- No consume endpoints reales.
- No modifica backend, SQL, persistencia ni contratos de API.
- No implementa todavía el wizard completo de venta completa.

## Usos previstos

El componente queda preparado como base UX para futuros pasos del wizard de venta completa, especialmente para:

1. seleccionar una reserva vigente;
2. seleccionar un inmueble o unidad funcional;
3. seleccionar una persona/comprador.

Cada fila muestra primero información humana y deja los IDs técnicos como texto secundario. Por ejemplo:

- reserva: `RV-000123 — Juan Pérez — Lote 12`;
- objeto inmobiliario: `Lote 12 — Manzana B — Disponible`;
- persona/comprador: `Juan Pérez — DNI 12.345.678`.

## Contrato de selección demo

Por ahora el componente devuelve payloads simples para que el prototipo pueda mostrar qué seleccionaría el wizard futuro:

- reserva: `id_reserva_venta`, `version_registro` y texto visual;
- objeto inmobiliario: `tipo_objeto` e ID correspondiente (`id_inmueble` o `id_unidad_funcional`);
- persona/comprador: `id_persona` y texto visual.

## Evolución futura

En una fase posterior se conectará a endpoints reales de consulta. Esa integración deberá respetar los dominios fuente:

- `personas` para identidad base de personas;
- `comercial` para reserva de venta y rol comprador en contexto comercial;
- el dominio correspondiente de inmuebles/unidades para objetos inmobiliarios, sin redefinir su semántica desde el wizard.

Mientras siga siendo demo, cualquier dato visible debe tratarse como no confirmado y no persistente.
