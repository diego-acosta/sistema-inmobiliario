# Dominio locativo

## Propósito
Organizar los servicios y catálogos del dominio locativo en formato modular y referencial.

## Catálogos del dominio
- [[CU-LOC]]
- [[RN-LOC]]
- [[ERR-LOC]]
- [[EVT-LOC]]
- [[EST-LOC]]

## Servicios del dominio
- [[SRV-LOC-001-gestion-de-contratos-de-alquiler]]
- [[SRV-LOC-002-gestion-de-condiciones-locativas]]
- [[SRV-LOC-003-gestion-de-garantias]]
- [[SRV-LOC-004-gestion-de-renovaciones-y-rescisiones]]
- [[SRV-LOC-005-gestion-de-ocupacion-locativa]]
- [[SRV-LOC-006-gestion-de-documentacion-locativa]]
- [[SRV-LOC-007-consulta-y-reporte-locativo]]

## Notas
- La consulta integral read-only de contrato de alquiler vive en [[SRV-LOC-001-gestion-de-contratos-de-alquiler]] y funciona como base de lectura para bloques locativos y comerciales posteriores sin ejecutar logica financiera ni modificar datos.
- Este dominio se incorporará progresivamente a la estructura modular de DEV-SRV.
- Los servicios deben mantenerse breves y referenciales.
- Reglas, errores y estados deben vivir en sus catálogos, no repetirse en cada servicio.
- Existe integración fuerte con el dominio financiero.
