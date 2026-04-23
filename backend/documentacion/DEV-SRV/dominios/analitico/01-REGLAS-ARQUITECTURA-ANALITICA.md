# Reglas de arquitectura analítica

## 1. Naturaleza del dominio
- El dominio analítico es exclusivamente de lectura.
- No genera efectos persistentes.
- No ejecuta lógica de negocio write.

## 2. Dependencia funcional
- Los servicios analíticos consumen información definida por los dominios funcionales.
- En la parte financiera, SRV-ANA consume resultados definidos por SRV-FIN o por read models derivados de éste.

## 3. Prohibiciones
Los servicios SRV-ANA no deben:
- recalcular intereses como lógica financiera primaria
- recalcular saldos como fuente primaria de verdad
- reconstruir obligaciones redefiniendo reglas del dominio financiero
- duplicar reglas de negocio de otros dominios

## 4. Responsabilidad
- Los dominios funcionales definen la semántica del dato.
- El dominio analítico agrega, filtra, compara, consolida y proyecta lecturas.

## 5. Corte temporal
- El dominio analítico puede consultar estado a fecha.
- La semántica del estado a fecha debe venir definida por el dominio funcional correspondiente.

## 6. Relación entre dominios
- SRV-FIN define verdad financiera funcional.
- SRV-ANA explota esa verdad para análisis, agregación y reportes.

## 7. Regla de consistencia
- Una consulta analítica no debe producir una verdad paralela del sistema.
- Debe leer, consolidar y proyectar sin redefinir el negocio.
