from pathlib import Path
from sqlalchemy import text

PATCH = (
    Path(__file__).parents[1] / "database" / "patch_admin_valor_global_412_20260813.sql"
)


def test_patch_seed_contractual_y_reejecutable(db_session):
    sql = PATCH.read_text()
    assert "ADMINISTRADOR_SISTEMA" in sql
    assert "ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR" in sql
    assert "PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO" in sql
    assert sql.startswith("-- #412")
    assert "BEGIN;" in sql and sql.rstrip().endswith("COMMIT;")
    assert "WHERE NOT EXISTS" in sql
    counts = db_session.execute(
        text("""
      SELECT
       (SELECT count(*) FROM permiso WHERE codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'),
       (SELECT count(*) FROM parametro_sistema WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'),
       (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO' AND v.es_valor_vigente AND v.deleted_at IS NULL)
    """)
    ).one()
    assert counts == (1, 1, 1)
