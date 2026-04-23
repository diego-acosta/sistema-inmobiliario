# Lineamientos Transversales

## Objetivo
Reunir criterios comunes que aplican a multiples dominios y servicios.

## Temas base
- Validaciones compartidas.
- Auditoria y trazabilidad.
- Manejo de errores.
- Seguridad y permisos.

## Failpoints en tests transaccionales

Cuando un test necesita forzar una falla tecnica de SQL para validar rollback, outbox o consistencia transaccional, debe preferirse un failpoint local a la conexion de test antes que DDL sobre la base compartida.

### Regla

En tests que usan el fixture `db_session` transaccional de `backend/tests/conftest.py`, no debe usarse `CREATE TRIGGER`, `CREATE FUNCTION`, `DROP TRIGGER` ni otro DDL equivalente como mecanismo de failpoint.

En esos casos debe usarse `backend/tests/sql_failpoints.py`, que instala un listener SQLAlchemy sobre la conexion del propio test y fuerza la excepcion solo para el statement objetivo.

### Motivo

El fixture abre una transaccion externa real y luego trabaja con savepoints. En PostgreSQL, el DDL sobre tablas como `venta` o `escrituracion` toma locks de catalogo y de relacion que permanecen vivos hasta el cierre de esa transaccion externa, aunque el test haga `session.commit()` sobre el savepoint.

Eso puede bloquear o deadlockear otros tests paralelos que intenten ejecutar DML o mas DDL sobre las mismas tablas.

### Locks que se previenen

Al evitar DDL en failpoints transaccionales se evita retener, durante toda la vida del test, locks como:

1. `ShareRowExclusiveLock` sobre la tabla alcanzada por `CREATE TRIGGER`
2. locks de catalogo asociados a la creacion o borrado de triggers y funciones

Ese patron reduce el riesgo de cruces entre tests paralelos del flujo `comercial -> inmobiliario`, especialmente sobre `venta`, `escrituracion` y tablas tecnicas relacionadas con outbox.

### Cuando usar `sql_failpoints.py`

Usarlo cuando el objetivo del test sea:

1. forzar una excepcion durante `INSERT`, `UPDATE` o `DELETE`
2. verificar rollback completo de la operacion de negocio
3. verificar que no quede `outbox_event` persistido si falla la transaccion
4. reproducir fallas tecnicas locales sin introducir estado global en la base

No usarlo para modelar reglas de negocio permanentes ni para reemplazar constraints reales de SQL.

## Referencias
- [[CORE-EF-001-infraestructura-transversal]]
