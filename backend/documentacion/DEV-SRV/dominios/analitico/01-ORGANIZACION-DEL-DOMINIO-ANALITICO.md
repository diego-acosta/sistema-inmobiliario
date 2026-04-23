# Organización del dominio analítico

## Objetivo
Definir la estructura interna del dominio Analítico / Reportes como capa de lectura transversal del sistema.

## Naturaleza del dominio
El dominio analítico es exclusivamente de lectura.
No genera efectos persistentes.
No reemplaza la lógica funcional de los dominios operativos.

## Estructura del dominio

### 1. Base transversal
Incluye servicios de lectura analítica general y por grandes dominios del sistema:
- consulta general del sistema
- consulta analítica inmobiliaria
- consulta analítica comercial
- consulta analítica locativa
- consulta analítica financiera
- consulta analítica documental
- consulta analítica operativa y administrativa

### 2. Subdominio financiero especializado
Incluye servicios analíticos financieros de mayor profundidad:
- deuda
- flujo financiero
- cobranzas
- mora
- refinanciaciones
- saldos a fecha
- cancelaciones anticipadas

## Regla de organización
Los servicios de la base transversal proveen visión general, resumida o consolidada.
Los servicios del subdominio financiero especializado profundizan fenómenos financieros concretos.

## Dashboards, KPIs y reportes
Dashboards, indicadores y reportes ejecutivos se apoyan en los servicios SRV-ANA,
pero no se modelan en esta etapa base como servicios independientes.

## Nota
Este dominio puede consumir información de todos los dominios del sistema,
pero la parte más profunda hoy queda concentrada en el área financiera.
