# CORE-EF-001

## Estado
Este identificador remite al documento canonico:

- [[CORE-EF-001-infraestructura-transversal]]

## Nota
No mantener contenido normativo duplicado en este archivo.

## Identidad local para commands técnicos futuros (#456)

El resolver de `LOCAL_INSTALLATION_CODE` es soporte transversal read-only y default-deny. Endpoint, headers, `If-Match-Version`, idempotencia, outbox, locks y versionado: **NO APLICA**. Write: **NO**. Rollback: responsabilidad del futuro consumidor, que aportará su sesión/transacción; el resolver no hace commit ni rollback. Sincronización queda fuera de alcance. #456 no implementa #454 ni un command productivo.
