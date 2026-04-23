# DB-CHANGELOG-INM-001 — Corrección de FK en unidad_funcional_servicio

## Objetivo

Documentar una corrección aplicada sobre la base real usada por tests para alinear una FK heredada con el modelo actual del dominio inmobiliario.

## Contexto

- El backend actual usa `unidad_funcional`.
- La tabla `unidad_funcional_servicio` referenciaba `unidad_funcional_legacy`.
- Eso generaba `ForeignKeyViolation` en tests e implementación.

## Problema detectado

La FK `fk_ufs_unidad` apuntaba a `unidad_funcional_legacy(id_unidad_funcional)` cuando el modelo actual y el backend trabajan con `unidad_funcional(id_unidad_funcional)`.

## Cambio realizado

1. Se verificó la FK existente.
2. Se confirmó que `unidad_funcional_servicio` estaba vacía.
3. Se eliminó `fk_ufs_unidad`.
4. Se recreó `fk_ufs_unidad` apuntando a `unidad_funcional(id_unidad_funcional)`.

## Validación

- Tests validados:
  - `tests/test_unidad_funcional_servicios_create.py`
  - `tests/test_unidad_funcional_servicios_get.py`
  - `tests/test_servicio_unidades_funcionales_get.py`
- Total validado: `10 passed`.
- Suite completa backend: `271/271 passed`.

## Impacto

- No hubo cambios en backend.
- No hubo cambios en contratos API.
- La corrección alinea base real con modelo actual.
- Evita expandir legacy como modelo principal.

## Alcance

- El cambio se aplicó sobre la base real usada por el entorno de tests.
- No implica que otros entornos ya estén corregidos.
- Otras FKs `_legacy` fueron detectadas pero no modificadas.

## Notas

- Los datos existentes eran de prueba y descartables.
- Este documento no redefine arquitectura.
- Deja trazabilidad de una corrección física puntual.
