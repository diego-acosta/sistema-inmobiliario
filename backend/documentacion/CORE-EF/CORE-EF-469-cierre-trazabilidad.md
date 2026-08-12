# Cierre documental y trazabilidad — #469

**Fecha de corte:** 2026-08-12
**Clasificación:** soporte transversal CORE-EF
**Estado:** IMPLEMENTADO / VALIDADO

## Texto de cierre para #469

#469 cumple su criterio de cierre técnico mediante una implementación distribuida
entre el PR #471 (merge commit
`ba0b13f1443ec119f527eeb69cd559971148800d`) y el PR #472 (merge commit
`731db8c562168dca925d76b90d0ebb278b715ed8`). Ambos PR están mergeados en
`main`.

La persistencia resultante incorpora `public.operacion_idempotente` como ledger
durable, local, inmutable y no sincronizable de receipts completados. Su contrato
físico comprende 17 columnas, unicidad global inmediata de `op_id`, guards
propios `ENABLE ALWAYS`, protección frente a `UPDATE`, `DELETE` y `TRUNCATE`,
relación coherente entre sucursal e instalación y preflight adversarial de los
invariantes contractuales.

La validación registrada comprende:

- PostgreSQL 16.14: reset DEV/TEST exitoso, suite focal y regresión relacionada
  verdes. El PR #472 reportó `120 passed, 3 skipped, 1 warning`.
- PostgreSQL 18 real: `122 passed, 1 skipped, 0 failed`. El único skip fue
  `test_pg16_sin_conenforced_reejecuta_patch`, específico de catálogos anteriores
  a PostgreSQL 18. La inspección física confirmó 8 CHECK, 10 NOT NULL, 1 PRIMARY
  KEY y 1 UNIQUE; el conteo contractual limitado a `c`, `f`, `p` y `u` fue 13.
  La regresión relacionada reportó `102 passed`.
- La auditoría adversarial final posterior al merge de #472 no confirmó blockers,
  findings materiales adicionales ni false negatives materiales del preflight
  dentro del threat model.

Por lo tanto, #469 queda **IMPLEMENTADO / VALIDADO** y cumple su criterio de
cierre. El siguiente incremento técnico es #470. El issue coordinador #402 debe
continuar abierto.

Este documento prepara la trazabilidad de cierre, pero no cierra #469 ni modifica
issues automáticamente.

## Actualización de trazabilidad para #402

Actualizar exclusivamente el checklist/estado coordinador de #402 para marcar
#469 como completado, sin modificar su contrato funcional ni cerrar #402. El
orden debe permanecer:

```text
#469 ✅
→ #470
→ #412 piloto
```

Estado coordinado resultante:

- #469: completado.
- #470: pendiente y próximo incremento.
- #412: piloto posterior; continúa bloqueado por #470 y por sus restantes
  contratos propios.
- #402: abierto y coordinador.

## Alcance de este cierre

Este cierre es exclusivamente documental y de trazabilidad. No modifica SQL,
runtime, sincronización, resets ni tests, y no implementa #470 ni #412.
