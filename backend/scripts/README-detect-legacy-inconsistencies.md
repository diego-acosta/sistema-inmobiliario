# Detect Legacy Inconsistencies

## Objetivo

`detect_legacy_inconsistencies.py` inspecciona la base PostgreSQL configurada para el backend y reporta dependencias hacia tablas `_legacy` sin modificar datos ni estructura.

## Qué detecta

- Foreign keys que apuntan a tablas `_legacy`
- Tablas actuales que dependen de tablas `_legacy`
- Tablas `_legacy` que siguen recibiendo referencias
- Pares de naming por sufijo `_legacy`, por ejemplo `unidad_funcional` y `unidad_funcional_legacy`
- Alertas por severidad:
  - `CRITICO`: tabla actual depende de `_legacy`
  - `MEDIO`: tabla `_legacy` todavía recibe referencias
  - `BAJO`: tabla `_legacy` existe sin referencias activas

## Cómo ejecutarlo

Desde `backend/`:

```powershell
python scripts/detect_legacy_inconsistencies.py
```

Usando el entorno de tests:

```powershell
$env:ENV='test'
python scripts/detect_legacy_inconsistencies.py
```

Indicando un archivo `.env` explícito:

```powershell
python scripts/detect_legacy_inconsistencies.py --env-file .env.test
```

Indicando una URL de conexión explícita:

```powershell
python scripts/detect_legacy_inconsistencies.py --db-url "postgresql+psycopg://usuario:clave@localhost:5432/base"
```

Exportando reporte:

```powershell
python scripts/detect_legacy_inconsistencies.py --json-out reports/legacy-report.json --md-out reports/legacy-report.md
```

## Notas

- El script es de solo lectura.
- No ejecuta `ALTER TABLE`, `DELETE`, `UPDATE` ni `INSERT`.
- Si la conexión falla, informa el error y termina con código distinto de cero.
