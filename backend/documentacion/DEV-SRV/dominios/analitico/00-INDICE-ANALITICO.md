# Dominio Analítico / Reportes

## Propósito
Definir la capa de consultas analíticas del sistema, permitiendo consolidar, agregar y analizar información proveniente de los distintos dominios funcionales, sin generar efectos persistentes.

## Naturaleza
- dominio exclusivamente de lectura
- sin efectos transaccionales
- no ejecuta lógica de negocio write
- consume información de dominios funcionales
- SRV-ANA utiliza resultados definidos por SRV-FIN en el dominio financiero

---

## Catálogos
- [[CU-ANA]]
- [[RN-ANA]]
- [[ERR-ANA]]
- [[EVT-ANA]]
- [[EST-ANA]]

---

## Organización del dominio
- [[01-ORGANIZACION-DEL-DOMINIO-ANALITICO]]
- [[01-REGLAS-ARQUITECTURA-ANALITICA]]

---

## Servicios analíticos

### Base transversal
- [[SRV-ANA-001-consulta-general-del-sistema]]
- [[SRV-ANA-002-consulta-analitica-inmobiliaria]]
- [[SRV-ANA-003-consulta-analitica-comercial]]
- [[SRV-ANA-004-consulta-analitica-locativa]]
- [[SRV-ANA-005-consulta-analitica-financiera]]
- [[SRV-ANA-006-consulta-analitica-documental]]
- [[SRV-ANA-007-consulta-analitica-operativa-y-administrativa]]

### Subdominio financiero especializado
- [[SRV-ANA-008-consulta-de-deuda]]
- [[SRV-ANA-009-consulta-de-flujo-financiero]]
- [[SRV-ANA-010-consulta-de-cobranzas]]
- [[SRV-ANA-011-consulta-de-mora]]
- [[SRV-ANA-012-consulta-de-refinanciaciones]]
- [[SRV-ANA-013-consulta-de-saldos-a-fecha]]
- [[SRV-ANA-014-consulta-de-cancelaciones-anticipadas]]

---

## Notas
- El dominio analítico no define lógica de negocio primaria.
- No recalcula estados financieros como fuente de verdad.
- Consume información de los dominios funcionales y la consolida.
- El subdominio financiero analítico no reemplaza al dominio financiero operativo.
- Dashboards, KPIs y reportes se construyen a partir de estos servicios.
- Este dominio puede evolucionar incorporando nuevas vistas analíticas según necesidades del negocio.
