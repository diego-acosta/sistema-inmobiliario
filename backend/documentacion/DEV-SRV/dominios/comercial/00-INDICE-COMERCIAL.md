# Dominio comercial / compraventa

## Proposito
Organizar los servicios y catalogos del dominio comercial en formato modular y referencial.

## Estado actual del dominio

El dominio `comercial` debe considerarse cerrado como bloque operativo `v1` para el alcance hoy materializado en backend y congelado en `DEV-API-COMERCIAL.md`.

Alcance implementado real del `v1`:

- `reserva_venta`
  - alta
  - actualizacion escalar
  - baja logica
  - detalle
  - listado
  - activar
  - cancelar
  - vencer
  - confirmar
  - generar `venta`
- `venta`
  - detalle enriquecido
  - detalle integral read-only con partes y estado financiero asociado
  - definir condiciones comerciales
  - generar planes de pago V2 iniciales `CUOTAS_IGUALES_SIMPLE` y `ANTICIPO_MAS_CUOTAS_IGUALES`
  - confirmar
- recursos hijos de `venta`
  - alta y listado de `instrumento_compraventa`
  - alta y listado de `cesion`
  - alta y listado de `escrituracion`
- integracion `comercial -> inmobiliario`
  - emision de `venta_confirmada`
  - emision de `escrituracion_registrada`
  - lectura de estado de integracion por venta
- integracion `comercial -> financiero`
  - lectura read-only de `relacion_generadora` y obligaciones asociadas a una venta
  - generacion inicial de cronogramas V2 desde `plan_pago_venta`
  - sin recalculo de deuda, sin mora y sin generacion de obligaciones desde la consulta

Backlog fuera de `v1`:

- `rescision_venta`
- venta directa fuera de reserva
- cancelacion propia de `venta`
- mutaciones y bajas de instrumentos, cesiones y escrituraciones
- detalle individual de recursos hijos
- reportes amplios o analiticos
- documental comercial propia
- plan financiero avanzado de venta fuera de los metodos V2 iniciales
- rescision financiera/comercial de venta
- cesion real con cambio de comprador y ajuste de obligados

## Catalogos del dominio

- [[CU-COM]]
- [[RN-COM]]
- [[ERR-COM]]
- [[EVT-COM]]
- [[EST-COM]]

## Servicios del dominio

- [[MODELO-PLANES-PAGO-VENTA]]
- [[MODELO-PLANES-PAGO-VENTA-BLOQUES]]
- [[DISEÑO-ENDPOINT-PLAN-PAGO-V2-GENERAR]]
- [[SRV-COM-001-gestion-de-reserva-de-venta]]
- [[SRV-COM-002-gestion-de-venta]]
- [[SRV-COM-003-gestion-de-condiciones-comerciales-de-venta]]
- [[SRV-COM-004-gestion-de-instrumentos-de-compraventa]]
- [[SRV-COM-005-gestion-de-cesiones]]
- [[SRV-COM-006-gestion-de-escrituracion]]
- [[SRV-COM-007-gestion-documental-comercial]]
- [[SRV-COM-008-consulta-y-reporte-comercial]]

## Notas

- `DEV-API-COMERCIAL.md` es la fuente publica de verdad del surface HTTP vigente.
- `SRV-COM-007` y los reportes amplios de `SRV-COM-008` quedan fuera del `v1` operativo actual.
- Todo pedido nuevo sobre `comercial` debe clasificarse primero como correccion de drift del `v1` o como backlog post-`v1`.
