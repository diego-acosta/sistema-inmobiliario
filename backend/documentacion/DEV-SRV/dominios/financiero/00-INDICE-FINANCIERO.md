# Dominio financiero

## Propósito
Organizar los servicios y catálogos del dominio financiero en formato modular y referencial.

## Catálogos del dominio
- [[CU-FIN]]
- [[RN-FIN]]
- [[ERR-FIN]]
- [[EVT-FIN]]
- [[EST-FIN]]
- [[MODELO-FINANCIERO-FIN]]
  - Procesamiento de eventos (Inbox)
  - Procesamiento automatico de eventos (Outbox -> Inbox)
- [[CIERRE-MODULO-FINANCIERO-LOCATIVO]]
- [[CIERRE-EMPRESA-PAGA-Y-RECUPERA-V1]]
- [[../inmobiliario/CIERRE-SERVICIO-TRASLADADO-V1]]
- [[TIPO-OBLIGACION-FIN]]
- [[AUDITORIA-OBLIGACION-FINANCIERA-CRONOGRAMA-V2]]

## Servicios del dominio
- [[SRV-FIN-001-gestion-relacion-generadora]]
- [[SRV-FIN-002-consulta-relacion-generadora]]
- [[SRV-FIN-003-generacion-de-obligaciones]]
- [[SRV-FIN-004-gestion-de-indices-financieros]]
- [[SRV-FIN-005-consulta-de-indices]]
- [[SRV-FIN-006-cronograma-y-obligaciones]]
- [[SRV-FIN-007-simulacion-y-registro-de-pago]]
- [[SRV-FIN-008-gestion-de-imputacion-financiera]]
- [[SRV-FIN-009-gestion-de-mora-creditos-y-debitos]]
- [[SRV-FIN-010-emision-financiera]]
- [[SRV-FIN-011-gestion-de-caja-financiera-y-garantias-monetarias]]
- [[SRV-FIN-012-consulta-y-reporte-financiero-consolidado]]
- [[SRV-FIN-013-generacion-de-mora]]
- [[SRV-FIN-014-plan-financiero-venta]]
- [[SRV-FIN-015-plan-financiero-locativo]]
  - Cronograma mensual implementado para `CANON_LOCATIVO`
- [[SRV-FIN-020-recupero-servicios-comunes]]
  - V1 implementada/cerrada de `EMPRESA_PAGA_Y_RECUPERA`
  - Cierre V1 en [[CIERRE-EMPRESA-PAGA-Y-RECUPERA-V1]]
- [[SRV-FIN-021-impuestos-trasladados]]
  - V1 implementada/cerrada de `IMPUESTO_TRASLADADO`

## Notas
- Este dominio se está refactorizando desde el DEV-SRV-001 legado hacia una estructura modular.
- Los servicios deben mantenerse breves y referenciales.
- Reglas, errores y estados deben vivir en sus catálogos, no repetirse en cada servicio.
