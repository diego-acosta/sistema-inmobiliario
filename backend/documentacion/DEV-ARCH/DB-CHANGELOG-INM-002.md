# DB-CHANGELOG-INM-002 — Corrección de FK contrato_alquiler y limpieza de escenario locativo de prueba

## Objetivo

Documentar la eliminación de un escenario de prueba descartable en `inmobiliaria_test` y la posterior corrección de la FK `fk_ca_cartera` para alinear `contrato_alquiler` con `cartera_locativa`.

## Contexto

- `contrato_alquiler` pertenece al dominio locativo.
- En la base real, su FK `fk_ca_cartera` apuntaba a `cartera_locativa_legacy`.
- Existe tabla actual `cartera_locativa` como reemplazo estructural.
- En `inmobiliaria_dev` ya se había alineado la FK.
- En `inmobiliaria_test` existían datos que impedían aplicar el mismo cambio.

## Problema detectado

- La FK `fk_ca_cartera` apuntaba a `cartera_locativa_legacy`.
- Existía un escenario precargado de prueba que mantenía activa esa dependencia.
- Esto generaba desalineación entre entornos `dev` y `test`.
- El sistema quedaba en estado híbrido innecesario.

## Análisis previo

Se auditó el escenario en `inmobiliaria_test`:

- `contrato_alquiler(1)`
- `reserva_locativa(1)`
- `cartera_locativa(1)`
- `cartera_locativa_legacy(1)`
- dependencias:
  - `ajuste_alquiler`
  - `condicion_economica_alquiler`
  - `contrato_objeto_locativo_legacy`

Conclusiones:

- Los datos eran de prueba (`*_TEST_001`).
- No estaban referenciados por tests versionados.
- Existía duplicación entre modelo actual y legacy.
- La base estaba en estado híbrido por ese escenario.

Clasificación:

- datos descartables

## Cambio realizado

1. Eliminación controlada del escenario de prueba:
   - `ajuste_alquiler`
   - `condicion_economica_alquiler`
   - `contrato_objeto_locativo_legacy`
   - `contrato_alquiler`
   - `reserva_locativa`
   - `cartera_locativa`
   - `cartera_locativa_legacy`
2. Verificación de tablas sin filas bloqueantes.
3. Eliminación de la FK:
   - `fk_ca_cartera`
4. Recreación de la FK:
   - `contrato_alquiler.id_cartera_locativa`
   - `cartera_locativa(id_cartera_locativa)`

## Validación

- FK verificada en catálogo PostgreSQL:
  - apunta a `cartera_locativa`
- Integridad referencial: OK.
- Backend: sin cambios.
- Tests ejecutados:
  - suite completa
- Resultado:
  - `271/271 passed`

## Impacto

- Se elimina dependencia estructural directa con `cartera_locativa_legacy`.
- Se alinea el dominio locativo con el modelo actual.
- Se elimina estado híbrido innecesario en entorno de test.
- No se modifica:
  - backend
  - contratos API
  - arquitectura funcional

## Alcance

- Aplicado en:
  - `inmobiliaria_test`
  - `inmobiliaria_dev`
- No implica que otros entornos estén alineados.
- No se modificaron otras FKs `_legacy`.

## Notas

- Los datos eliminados eran exclusivamente de prueba.
- No existía dependencia funcional real de esos registros.
- Este cambio consolida el modelo actual como fuente de verdad.
- La eliminación de otras estructuras `_legacy` queda fuera de este alcance.
- Este documento deja trazabilidad de una corrección estructural del dominio locativo.
