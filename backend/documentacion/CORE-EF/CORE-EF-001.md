# CORE-EF-001

## Estado
Este identificador remite al documento canonico:

- [[CORE-EF-001-infraestructura-transversal]]

## Nota
No mantener contenido normativo duplicado en este archivo.

## Identidad local para commands técnicos futuros (#456)

El resolver de `LOCAL_INSTALLATION_CODE` es soporte transversal read-only y default-deny. Endpoint, headers, `If-Match-Version`, idempotencia, outbox, locks y versionado: **NO APLICA**. Write: **NO**. Rollback: responsabilidad del futuro consumidor, que aportará su sesión/transacción; el resolver no hace commit ni rollback. Sincronización queda fuera de alcance. #456 no implementa #454 ni un command productivo.

## Bootstrap local de credenciales (#454)

`COMMAND_WRITE_TECNICO` por CLI, local y no sincronizable. No es endpoint: headers e `If-Match-Version` **NO APLICA**. Idempotencia local simplificada por `op_id_alta`; outbox y eventos **NO APLICA**. Usa locks transaccionales de usuario y credenciales, no lock lógico persistido. Los triggers mantienen `version_registro`. Revocación e inserción comparten transacción y rollback.
