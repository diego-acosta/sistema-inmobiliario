from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


PATCH_NAME = "patch_calendario_comercial_482_20260814.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"

CODES = ("DIA_CIERRE_COMERCIAL", "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS")
EXPECTED = [
    (
        CODES[0],
        "Día de cierre comercial",
        "Día del mes, entre 1 y 31, utilizado para determinar el período base sugerido de una venta según su fecha de negocio.",
        "ENTERO", "GLOBAL", True, False, True,
    ),
    (
        CODES[1],
        "Día de vencimiento predeterminado de cuotas",
        "Día del mes, entre 1 y 31, utilizado para sugerir el vencimiento de las cuotas; la fecha sugerida puede ser modificada antes de confirmar la venta.",
        "ENTERO", "GLOBAL", True, False, True,
    ),
]


def _sql() -> str:
    content = PATCH.read_text(encoding="utf-8")
    return content.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _definitions(db):
    return db.execute(text("""
      SELECT p.codigo_parametro,p.nombre_parametro,p.descripcion,t.codigo_tipo_dato,
             a.codigo_alcance,p.exponible_api_administrativa,p.es_sensible,
             p.editable_administrativamente
        FROM parametro_sistema p JOIN tipo_dato_parametro t USING(id_tipo_dato_parametro)
        JOIN alcance_parametro a USING(id_alcance_parametro)
       WHERE p.codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
       ORDER BY p.codigo_parametro
    """)).all()


def _identity_sequence(db) -> str:
    return db.execute(text("""
      SELECT format('%I.%I',ns.nspname,seq.relname)
      FROM pg_depend d
      JOIN pg_class seq ON seq.oid=d.objid AND seq.relkind='S'
      JOIN pg_namespace ns ON ns.oid=seq.relnamespace
      JOIN pg_attribute a ON a.attrelid=d.refobjid AND a.attnum=d.refobjsubid
      WHERE d.classid='pg_class'::regclass AND d.refclassid='pg_class'::regclass
        AND d.refobjid='public.configuracion_calendario_comercial'::regclass
        AND a.attname='id_configuracion_calendario_comercial'
        AND d.deptype='i'
    """)).scalar_one()


def test_reset_deja_definiciones_sin_valores_ni_raiz(db_session):
    assert _definitions(db_session) == EXPECTED
    assert db_session.execute(text("""
      SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
       WHERE p.codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
    """)).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM configuracion_calendario_comercial")).scalar_one() == 0


def test_patch_transaccional_simetrico_idempotente_y_sin_duplicados(db_session):
    upper = PATCH.read_text(encoding="utf-8").upper()
    assert upper.count("BEGIN;") == upper.count("COMMIT;") == 1
    assert SH.read_text(encoding="utf-8").count(f'"{PATCH_NAME}"') == 2
    assert BAT.read_text(encoding="utf-8").count("PATCH_CALENDARIO_COMERCIAL_482_FILE") == 5
    before = db_session.execute(text("""
      SELECT (SELECT count(*) FROM parametro_sistema WHERE codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')),
             (SELECT count(*) FROM permiso WHERE codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR'),
             (SELECT count(*) FROM rol_seguridad_permiso rsp JOIN rol_seguridad r USING(id_rol_seguridad)
               JOIN permiso p USING(id_permiso) WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
               AND p.codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR')
    """)).one()
    db_session.execute(text(_sql()))
    assert before == (2, 1, 1)
    assert _definitions(db_session) == EXPECTED
    states = db_session.execute(text("""
      SELECT tgname,tgenabled FROM pg_trigger
       WHERE tgname IN (
         'trg_biu_configuracion_calendario_comercial_core_ef',
         'trg_biu_valor_parametro_calendario_comercial'
       ) ORDER BY tgname
    """)).all()
    assert states == [
        ("trg_biu_configuracion_calendario_comercial_core_ef", "O"),
        ("trg_biu_valor_parametro_calendario_comercial", "O"),
    ]
    nullable_defaults = db_session.execute(text("""
      SELECT a.attname,pg_get_expr(d.adbin,d.adrelid)
        FROM pg_attribute a LEFT JOIN pg_attrdef d
          ON d.adrelid=a.attrelid AND d.adnum=a.attnum
       WHERE a.attrelid='configuracion_calendario_comercial'::regclass
         AND a.attname IN (
           'deleted_at','id_instalacion_origen',
           'id_instalacion_ultima_modificacion','op_id_alta',
           'op_id_ultima_modificacion'
         ) ORDER BY a.attname
    """)).all()
    assert nullable_defaults == [
        ("deleted_at", None),
        ("id_instalacion_origen", None),
        ("id_instalacion_ultima_modificacion", None),
        ("op_id_alta", None),
        ("op_id_ultima_modificacion", None),
    ]
    constraints = db_session.execute(text("""
      SELECT contype,regexp_replace(
        replace(pg_get_constraintdef(oid),'public.',''),
        '[[:space:]()]|::[a-z ]+','','g'
      )
      FROM pg_constraint
      WHERE conrelid='configuracion_calendario_comercial'::regclass
        AND contype IN ('p','u','c','f')
      ORDER BY contype,2
    """)).all()
    assert constraints == sorted([
        ("p", "PRIMARYKEYid_configuracion_calendario_comercial"),
        ("u", "UNIQUEuid_global"),
        ("c", "CHECKdeleted_atISNULLORdeleted_at>=created_at"),
        ("c", "CHECKversion_registro>=1"),
        ("f", "FOREIGNKEYid_instalacion_origenREFERENCESinstalacionid_instalacionONDELETERESTRICT"),
        ("f", "FOREIGNKEYid_instalacion_ultima_modificacionREFERENCESinstalacionid_instalacionONDELETERESTRICT"),
    ])
    server_version, contractual_count, not_null_constraint_count = (
        db_session.execute(text("""
          SELECT current_setting('server_version_num')::integer,
                 count(*) FILTER (WHERE contype IN ('p','u','c','f')),
                 count(*) FILTER (WHERE contype='n')
          FROM pg_constraint
          WHERE conrelid='configuracion_calendario_comercial'::regclass
        """)).one()
    )
    assert contractual_count == 6
    if server_version >= 180000 and not_null_constraint_count:
        assert not_null_constraint_count == 5
    nullability = db_session.execute(text("""
      SELECT column_name,is_nullable
      FROM information_schema.columns
      WHERE table_schema='public'
        AND table_name='configuracion_calendario_comercial'
      ORDER BY ordinal_position
    """)).all()
    assert nullability == [
        ("id_configuracion_calendario_comercial", "NO"),
        ("uid_global", "NO"),
        ("version_registro", "NO"),
        ("created_at", "NO"),
        ("updated_at", "NO"),
        ("deleted_at", "YES"),
        ("id_instalacion_origen", "YES"),
        ("id_instalacion_ultima_modificacion", "YES"),
        ("op_id_alta", "YES"),
        ("op_id_ultima_modificacion", "YES"),
    ]
    indexes = db_session.execute(text("""
      SELECT pi.indexname,regexp_replace(pi.indexdef,'[[:space:]()]','','g'),
             i.indisvalid,i.indisready
      FROM pg_indexes pi JOIN pg_class ci ON ci.relname=pi.indexname
      JOIN pg_namespace n ON n.oid=ci.relnamespace AND n.nspname=pi.schemaname
      JOIN pg_index i ON i.indexrelid=ci.oid
      WHERE pi.schemaname='public'
        AND pi.tablename='configuracion_calendario_comercial'
      ORDER BY pi.indexname
    """)).all()
    assert indexes == [
        ("configuracion_calendario_comercial_pkey", "CREATEUNIQUEINDEXconfiguracion_calendario_comercial_pkeyONpublic.configuracion_calendario_comercialUSINGbtreeid_configuracion_calendario_comercial", True, True),
        ("uq_configuracion_calendario_comercial_uid", "CREATEUNIQUEINDEXuq_configuracion_calendario_comercial_uidONpublic.configuracion_calendario_comercialUSINGbtreeuid_global", True, True),
        ("ux_configuracion_calendario_comercial_activa", "CREATEUNIQUEINDEXux_configuracion_calendario_comercial_activaONpublic.configuracion_calendario_comercialUSINGbtreetrueWHEREdeleted_atISNULL", True, True),
        ("ux_configuracion_calendario_comercial_op_id_alta", "CREATEUNIQUEINDEXux_configuracion_calendario_comercial_op_id_altaONpublic.configuracion_calendario_comercialUSINGbtreeop_id_altaWHEREop_id_altaISNOTNULL", True, True),
    ]
    root_triggers = db_session.execute(text("""
      SELECT tgname,tgenabled FROM pg_trigger
      WHERE tgrelid='configuracion_calendario_comercial'::regclass
        AND NOT tgisinternal
    """)).all()
    assert root_triggers == [
        ("trg_biu_configuracion_calendario_comercial_core_ef", "O")
    ]
    assert db_session.execute(text("""
      SELECT count(*) FROM pg_rewrite
      WHERE ev_class='public.configuracion_calendario_comercial'::regclass
    """)).scalar_one() == 0
    assert db_session.execute(text("""
      SELECT relrowsecurity,relforcerowsecurity
      FROM pg_class
      WHERE oid='public.configuracion_calendario_comercial'::regclass
    """)).one() == (False, False)
    assert db_session.execute(text("""
      SELECT count(*) FROM pg_policy
      WHERE polrelid='public.configuracion_calendario_comercial'::regclass
    """)).scalar_one() == 0
    identity = db_session.execute(text("""
      SELECT a.attidentity,s.seqtypid::regtype::text,s.seqstart,s.seqincrement,
             s.seqmin,s.seqmax,s.seqcache,s.seqcycle,d.deptype
      FROM pg_attribute a
      JOIN pg_depend d ON d.refobjid=a.attrelid AND d.refobjsubid=a.attnum
        AND d.classid='pg_class'::regclass AND d.refclassid='pg_class'::regclass
      JOIN pg_class seq ON seq.oid=d.objid AND seq.relkind='S'
      JOIN pg_sequence s ON s.seqrelid=seq.oid
      WHERE a.attrelid='public.configuracion_calendario_comercial'::regclass
        AND a.attname='id_configuracion_calendario_comercial'
    """)).one()
    assert identity == (
        "d", "bigint", 1, 1, 1, 9223372036854775807, 1, False, "i"
    )
    sequence_name = _identity_sequence(db_session)
    last_value, is_called = db_session.execute(text(
        f"SELECT last_value,is_called FROM {sequence_name}"
    )).one()
    next_value = last_value + 1 if is_called else 1
    assert 1 <= next_value <= 9223372036854775807
    patch_source = PATCH.read_text(encoding="utf-8").lower()
    assert "nextval(" not in patch_source
    assert "setval(" not in patch_source


def test_reset_bat_verifica_cada_patch_antes_del_siguiente_psql():
    bat = BAT.read_text(encoding="utf-8")
    commands = [
        line.strip()
        for line in bat.splitlines()
        if line.strip().startswith("%PGBIN%\\psql")
    ]
    for database in ("%DEV_DB%", "%TEST_DB%"):
        sequence = [
            next(command for command in commands if database in command and name in command)
            for name in (
                "PATCH_ROL_ADMINISTRADOR_SISTEMA_FILE",
                "PATCH_ADMIN_VALOR_GLOBAL_412_FILE",
                "PATCH_CALENDARIO_COMERCIAL_482_FILE",
            )
        ]
        positions = [bat.index(command) for command in sequence]
        assert positions == sorted(positions)
        for index, position in enumerate(positions):
            boundary = positions[index + 1] if index + 1 < len(positions) else len(bat)
            block = bat[position:boundary].lower()
            assert "if errorlevel 1 (" in block
            assert block.index("if errorlevel 1 (") > block.index("psql")


def test_reejecucion_es_independiente_de_search_path_sin_public(db_session):
    with db_session.begin_nested():
        db_session.execute(text("SET LOCAL search_path TO pg_catalog"))
        db_session.execute(text(_sql()))
        triggers = db_session.execute(text("""
          SELECT tgname,tgenabled FROM pg_trigger
          WHERE tgname IN (
            'trg_biu_configuracion_calendario_comercial_core_ef',
            'trg_biu_valor_parametro_calendario_comercial'
          ) ORDER BY tgname
        """)).all()
        assert triggers == [
            ("trg_biu_configuracion_calendario_comercial_core_ef", "O"),
            ("trg_biu_valor_parametro_calendario_comercial", "O"),
        ]


@pytest.mark.parametrize("health_column", ["indisvalid", "indisready"])
def test_indice_contractual_no_utilizable_aborta_sin_repararlo(
    db_session, health_column
):
    index_name = "ux_configuracion_calendario_comercial_op_id_alta"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          UPDATE pg_index SET {health_column}=false
          WHERE indexrelid=CAST(:index_name AS regclass)
        """), {"index_name": f"public.{index_name}"})
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(text(f"""
          SELECT NOT {health_column} FROM pg_index
          WHERE indexrelid=CAST(:index_name AS regclass)
        """), {"index_name": f"public.{index_name}"}).scalar_one() is True


@pytest.mark.parametrize("event", ["INSERT", "UPDATE"])
def test_rewrite_rule_extra_aborta_sin_eliminarla(db_session, event):
    rule_name = f"calendario_adversarial_{event.lower()}"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE RULE {rule_name} AS
          ON {event} TO public.configuracion_calendario_comercial
          DO INSTEAD NOTHING
        """))
        assert db_session.execute(text("""
          SELECT count(*) FROM pg_rewrite
          WHERE ev_class='public.configuracion_calendario_comercial'::regclass
            AND rulename=:rule_name
        """), {"rule_name": rule_name}).scalar_one() == 1
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(text("""
          SELECT count(*) FROM pg_rewrite
          WHERE ev_class='public.configuracion_calendario_comercial'::regclass
            AND rulename=:rule_name
        """), {"rule_name": rule_name}).scalar_one() == 1


@pytest.mark.parametrize(
    ("statements", "expected"),
    [
        (
            ["ALTER TABLE public.configuracion_calendario_comercial ENABLE ROW LEVEL SECURITY"],
            (True, False),
        ),
        (
            [
                "ALTER TABLE public.configuracion_calendario_comercial ENABLE ROW LEVEL SECURITY",
                "ALTER TABLE public.configuracion_calendario_comercial FORCE ROW LEVEL SECURITY",
            ],
            (True, True),
        ),
    ],
)
def test_rls_incompatible_aborta_sin_desactivarlo(db_session, statements, expected):
    with db_session.begin_nested():
        for statement in statements:
            db_session.execute(text(statement))
        state_query = text("""
          SELECT relrowsecurity,relforcerowsecurity FROM pg_class
          WHERE oid='public.configuracion_calendario_comercial'::regclass
        """)
        assert db_session.execute(state_query).one() == expected
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(state_query).one() == expected


@pytest.mark.parametrize("predicate", ["false", "true"])
def test_policy_incompatible_aborta_sin_eliminarla(db_session, predicate):
    policy_name = f"calendario_adversarial_{predicate}"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE POLICY {policy_name}
          ON public.configuracion_calendario_comercial
          FOR ALL USING ({predicate}) WITH CHECK ({predicate})
        """))
        policy_count = text("""
          SELECT count(*) FROM pg_policy
          WHERE polrelid='public.configuracion_calendario_comercial'::regclass
            AND polname=:policy_name
        """)
        assert db_session.execute(
            policy_count, {"policy_name": policy_name}
        ).scalar_one() == 1
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(
            policy_count, {"policy_name": policy_name}
        ).scalar_one() == 1


@pytest.mark.parametrize(
    ("alter_options", "evidence"),
    [
        (
            "MINVALUE 0 MAXVALUE 10",
            "SELECT seqmin=0 AND seqmax=10 FROM pg_sequence WHERE seqrelid=CAST(:sequence_name AS regclass)",
        ),
        (
            "INCREMENT BY 2",
            "SELECT seqincrement=2 FROM pg_sequence WHERE seqrelid=CAST(:sequence_name AS regclass)",
        ),
        (
            "CACHE 5",
            "SELECT seqcache=5 FROM pg_sequence WHERE seqrelid=CAST(:sequence_name AS regclass)",
        ),
        (
            "CYCLE",
            "SELECT seqcycle FROM pg_sequence WHERE seqrelid=CAST(:sequence_name AS regclass)",
        ),
    ],
)
def test_identity_sequence_incompatible_aborta_sin_repararla(
    db_session, alter_options, evidence
):
    sequence_name = _identity_sequence(db_session)
    with db_session.begin_nested():
        db_session.execute(text(
            f"ALTER SEQUENCE {sequence_name} {alter_options}"
        ))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(
            text(evidence), {"sequence_name": sequence_name}
        ).scalar_one() is True


def test_identity_sequence_agotada_aborta_sin_consumir_ni_reparar(db_session):
    sequence_name = _identity_sequence(db_session)
    original_last, original_called = db_session.execute(text(
        f"SELECT last_value,is_called FROM {sequence_name}"
    )).one()
    sequence_max = db_session.execute(text("""
      SELECT seqmax FROM pg_sequence
      WHERE seqrelid=CAST(:sequence_name AS regclass)
    """), {"sequence_name": sequence_name}).scalar_one()
    try:
        db_session.execute(text(
            "SELECT setval(CAST(:sequence_name AS regclass),:value,true)"
        ), {"sequence_name": sequence_name, "value": sequence_max})
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(text(
            f"SELECT last_value,is_called FROM {sequence_name}"
        )).one() == (sequence_max, True)
    finally:
        db_session.execute(text(
            "SELECT setval(CAST(:sequence_name AS regclass),:value,:is_called)"
        ), {
            "sequence_name": sequence_name,
            "value": original_last,
            "is_called": original_called,
        })


@pytest.mark.parametrize(
    ("mutation", "evidence"),
    [
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN version_registro SET DEFAULT 2",
            "SELECT column_default='2' FROM information_schema.columns WHERE table_schema='public' AND table_name='configuracion_calendario_comercial' AND column_name='version_registro'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT uq_configuracion_calendario_comercial_uid",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND contype='u')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT chk_configuracion_calendario_comercial_version",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='chk_configuracion_calendario_comercial_version')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT fk_configuracion_calendario_comercial_instalacion_origen",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='fk_configuracion_calendario_comercial_instalacion_origen')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN id_configuracion_calendario_comercial DROP IDENTITY",
            "SELECT attidentity='' FROM pg_attribute WHERE attrelid='configuracion_calendario_comercial'::regclass AND attname='id_configuracion_calendario_comercial'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN deleted_at SET DEFAULT CURRENT_TIMESTAMP",
            "SELECT pg_get_expr(d.adbin,d.adrelid) IS NOT NULL FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='configuracion_calendario_comercial'::regclass AND a.attname='deleted_at'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN id_instalacion_origen SET DEFAULT 1",
            "SELECT pg_get_expr(d.adbin,d.adrelid) IS NOT NULL FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='configuracion_calendario_comercial'::regclass AND a.attname='id_instalacion_origen'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN id_instalacion_ultima_modificacion SET DEFAULT 1",
            "SELECT pg_get_expr(d.adbin,d.adrelid) IS NOT NULL FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='configuracion_calendario_comercial'::regclass AND a.attname='id_instalacion_ultima_modificacion'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN op_id_alta SET DEFAULT gen_random_uuid()",
            "SELECT pg_get_expr(d.adbin,d.adrelid) IS NOT NULL FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='configuracion_calendario_comercial'::regclass AND a.attname='op_id_alta'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN op_id_ultima_modificacion SET DEFAULT gen_random_uuid()",
            "SELECT pg_get_expr(d.adbin,d.adrelid) IS NOT NULL FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='configuracion_calendario_comercial'::regclass AND a.attname='op_id_ultima_modificacion'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ADD CONSTRAINT chk_calendario_adversarial_false CHECK (false)",
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='chk_calendario_adversarial_false')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ADD CONSTRAINT chk_calendario_adversarial_inocua CHECK (version_registro >= 0)",
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='chk_calendario_adversarial_inocua')",
        ),
        (
            "CREATE INDEX idx_calendario_adversarial_expr ON configuracion_calendario_comercial (((1 / (version_registro - 1))))",
            "SELECT to_regclass('public.idx_calendario_adversarial_expr') IS NOT NULL",
        ),
        (
            "CREATE INDEX idx_calendario_adversarial_version ON configuracion_calendario_comercial(version_registro)",
            "SELECT to_regclass('public.idx_calendario_adversarial_version') IS NOT NULL",
        ),
    ],
)
def test_tabla_raiz_incompatible_falla_sin_sanear(db_session, mutation, evidence):
    with db_session.begin_nested():
        db_session.execute(text(mutation))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(text(evidence)).scalar_one() is True


@pytest.mark.parametrize(
    "function_name",
    [
        "trg_configuracion_calendario_comercial_core_ef",
        "trg_valor_parametro_calendario_comercial",
    ],
)
def test_funcion_homonima_incompatible_falla_sin_reemplazar(db_session, function_name):
    marker = "BODY_INCOMPATIBLE_482"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE OR REPLACE FUNCTION public.{function_name}() RETURNS trigger
          LANGUAGE plpgsql AS $function$
          BEGIN
            RAISE EXCEPTION '{marker}';
          END $function$
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        definition = db_session.execute(
            text("SELECT pg_get_functiondef(to_regprocedure(:signature))"),
            {"signature": f"public.{function_name}()"},
        ).scalar_one()
        assert marker in definition


@pytest.mark.parametrize(
    "body",
    [
        """
        BEGIN
          IF TG_OP='INSERT' THEN NEW.version_registro:=2;
          ELSE NEW.uid_global:=OLD.uid_global; NEW.version_registro:=OLD.version_registro+1; END IF;
          RETURN NEW; /* PARCIAL_VERSION_482 */
        END
        """,
        """
        BEGIN
          IF TG_OP='INSERT' THEN
            IF NEW.version_registro<>1 THEN RAISE EXCEPTION 'version'; END IF;
            NEW.op_id_ultima_modificacion:=COALESCE(NEW.op_id_ultima_modificacion,NEW.op_id_alta);
            NEW.id_instalacion_ultima_modificacion:=COALESCE(NEW.id_instalacion_ultima_modificacion,NEW.id_instalacion_origen);
          ELSE
            NEW.uid_global:=OLD.uid_global; NEW.id_instalacion_origen:=OLD.id_instalacion_origen;
            NEW.op_id_alta:=OLD.op_id_alta; NEW.updated_at:=CURRENT_TIMESTAMP;
            NEW.version_registro:=OLD.version_registro+1;
          END IF;
          RETURN NEW; /* PARCIAL_CREATED_AT_482 */
        END
        """,
        """
        BEGIN
          IF TG_OP='INSERT' THEN
            IF NEW.version_registro<>1 THEN RAISE EXCEPTION 'version'; END IF;
            NEW.op_id_ultima_modificacion:=COALESCE(NEW.op_id_ultima_modificacion,NEW.op_id_alta);
            NEW.id_instalacion_ultima_modificacion:=COALESCE(NEW.id_instalacion_ultima_modificacion,NEW.id_instalacion_origen);
          ELSE
            NEW.uid_global:=OLD.uid_global; NEW.created_at:=OLD.created_at;
            NEW.id_instalacion_origen:=OLD.id_instalacion_origen;
            NEW.updated_at:=CURRENT_TIMESTAMP; NEW.version_registro:=OLD.version_registro+1;
          END IF;
          RETURN NEW; /* PARCIAL_OP_ID_482 */
        END
        """,
    ],
)
def test_funcion_core_ef_parcialmente_compatible_aborta_sin_reemplazo(db_session, body):
    marker = body.split("PARCIAL_", 1)[1].split(" ", 1)[0]
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE OR REPLACE FUNCTION public.trg_configuracion_calendario_comercial_core_ef()
          RETURNS trigger LANGUAGE plpgsql AS $function${body}$function$
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        definition = db_session.execute(text("""
          SELECT pg_get_functiondef(
            'public.trg_configuracion_calendario_comercial_core_ef()'::regprocedure
          )
        """)).scalar_one()
        assert marker in definition


def test_funcion_rango_parcialmente_compatible_aborta_sin_reemplazo(db_session):
    marker = "PARCIAL_RANGO_482"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE OR REPLACE FUNCTION public.trg_valor_parametro_calendario_comercial()
          RETURNS trigger LANGUAGE plpgsql AS $function$
          BEGIN
            IF 'DIA_CIERRE_COMERCIAL' <> 'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS'
               AND NEW.valor_parametro::numeric BETWEEN 1 AND 31 THEN NULL; END IF;
            RETURN NEW; /* {marker} */
          END $function$
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        definition = db_session.execute(text("""
          SELECT pg_get_functiondef(
            'public.trg_valor_parametro_calendario_comercial()'::regprocedure
          )
        """)).scalar_one()
        assert marker in definition


@pytest.mark.parametrize(
    ("function_name", "contractual_literal", "adversarial_literal"),
    [
        (
            "trg_valor_parametro_calendario_comercial",
            "DIA_CIERRE_COMERCIAL",
            "DIA_CIERRE_ COMERCIAL",
        ),
        (
            "trg_valor_parametro_calendario_comercial",
            "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
            "DIA_VENCIMIENTO_PREDETERMINADO_ CUOTAS",
        ),
        (
            "trg_configuracion_calendario_comercial_core_ef",
            "calendario comercial debe iniciar en versión 1",
            "calendario  comercial debe iniciar en versión 1",
        ),
    ],
)
def test_whitespace_dentro_de_literal_hace_funcion_incompatible_sin_reemplazo(
    db_session, function_name, contractual_literal, adversarial_literal
):
    with db_session.begin_nested():
        original = db_session.execute(
            text("SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(:signature)"),
            {"signature": f"public.{function_name}()"},
        ).scalar_one()
        assert contractual_literal in original
        adversarial = original.replace(contractual_literal, adversarial_literal, 1)
        db_session.execute(text(f"""
          CREATE OR REPLACE FUNCTION public.{function_name}() RETURNS trigger
          LANGUAGE plpgsql AS $adversarial${adversarial}$adversarial$
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        installed = db_session.execute(
            text("SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(:signature)"),
            {"signature": f"public.{function_name}()"},
        ).scalar_one()
        assert adversarial_literal in installed
        assert contractual_literal not in installed


@pytest.mark.parametrize(
    ("table_name", "trigger_name", "mode", "expected_state"),
    [
        (
            "configuracion_calendario_comercial",
            "trg_biu_configuracion_calendario_comercial_core_ef",
            "DISABLE",
            "D",
        ),
        (
            "valor_parametro",
            "trg_biu_valor_parametro_calendario_comercial",
            "DISABLE",
            "D",
        ),
        (
            "valor_parametro",
            "trg_biu_valor_parametro_calendario_comercial",
            "ENABLE REPLICA",
            "R",
        ),
        (
            "configuracion_calendario_comercial",
            "trg_biu_configuracion_calendario_comercial_core_ef",
            "ENABLE ALWAYS",
            "A",
        ),
    ],
)
def test_trigger_contractual_no_normal_aborta_sin_reactivarlo(
    db_session, table_name, trigger_name, mode, expected_state
):
    with db_session.begin_nested():
        db_session.execute(text(
            f"ALTER TABLE {table_name} {mode} TRIGGER {trigger_name}"
        ))
        state = db_session.execute(
            text("SELECT tgenabled FROM pg_trigger WHERE tgname=:name"),
            {"name": trigger_name},
        ).scalar_one()
        assert state == expected_state
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(
            text("SELECT tgenabled FROM pg_trigger WHERE tgname=:name"),
            {"name": trigger_name},
        ).scalar_one() == expected_state


@pytest.mark.parametrize(
    ("timing", "events"),
    [("BEFORE", "INSERT"), ("AFTER", "UPDATE")],
)
def test_trigger_extra_en_raiz_aborta_sin_eliminarlo(db_session, timing, events):
    trigger_name = f"trg_calendario_adversarial_{timing.lower()}"
    with db_session.begin_nested():
        db_session.execute(text("""
          CREATE FUNCTION public.trg_calendario_adversarial_fn() RETURNS trigger
          LANGUAGE plpgsql AS $function$ BEGIN RETURN NEW; END $function$
        """))
        db_session.execute(text(f"""
          CREATE TRIGGER {trigger_name} {timing} {events}
          ON configuracion_calendario_comercial FOR EACH ROW
          EXECUTE FUNCTION public.trg_calendario_adversarial_fn()
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        names = db_session.execute(text("""
          SELECT tgname FROM pg_trigger
          WHERE tgrelid='configuracion_calendario_comercial'::regclass
            AND NOT tgisinternal ORDER BY tgname
        """)).scalars().all()
        assert names == sorted([
            "trg_biu_configuracion_calendario_comercial_core_ef",
            trigger_name,
        ])


@pytest.mark.parametrize("column,value", [
    ("id_tipo_dato_parametro", 999999), ("id_alcance_parametro", 999999),
    ("exponible_api_administrativa", False), ("es_sensible", True),
    ("editable_administrativamente", False), ("nombre_parametro", "incompatible"),
])
def test_definicion_incompatible_falla_sin_sanear(db_session, column, value):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(f"UPDATE parametro_sistema SET {column}=:value WHERE codigo_parametro=:code"),
                           {"value": value, "code": CODES[0]})
        db_session.execute(text(_sql()))
    assert _definitions(db_session) == EXPECTED


def test_permiso_y_receptor_canonico_sin_roles_ni_asignaciones_nuevas(db_session):
    assert db_session.execute(text("""
      SELECT p.nombre_permiso,p.descripcion,p.estado_permiso,r.codigo_rol
        FROM permiso p JOIN rol_seguridad_permiso rsp USING(id_permiso)
        JOIN rol_seguridad r USING(id_rol_seguridad)
       WHERE p.codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR'
    """)).one() == (
        "Administrar calendario comercial",
        "Permite crear y programar configuraciones del calendario comercial global, incluyendo día de cierre comercial y día de vencimiento predeterminado de cuotas.",
        "ACTIVO", "ADMINISTRADOR_SISTEMA",
    )
    assert db_session.execute(text("SELECT count(*) FROM rol_seguridad WHERE codigo_rol='ADMIN'")).scalar_one() == 0
    assert db_session.execute(text("""
      SELECT count(*) FROM usuario_rol_seguridad ur JOIN rol_seguridad r USING(id_rol_seguridad)
       WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
    """)).scalar_one() == 0


def test_raiz_core_ef_permite_cero_o_una_activa_y_versiona(db_session):
    columns = db_session.execute(text("""
      SELECT column_name FROM information_schema.columns
       WHERE table_schema='public' AND table_name='configuracion_calendario_comercial'
       ORDER BY ordinal_position
    """)).scalars().all()
    assert columns == ["id_configuracion_calendario_comercial", "uid_global", "version_registro",
                       "created_at", "updated_at", "deleted_at", "id_instalacion_origen",
                       "id_instalacion_ultima_modificacion", "op_id_alta", "op_id_ultima_modificacion"]
    assert db_session.execute(text("SELECT count(*) FROM configuracion_calendario_comercial")).scalar_one() == 0
    with db_session.begin_nested():
        root_id = db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES RETURNING id_configuracion_calendario_comercial")).scalar_one()
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES"))
        before = db_session.execute(text("SELECT uid_global,created_at,version_registro FROM configuracion_calendario_comercial WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id}).one()
        db_session.execute(text("UPDATE configuracion_calendario_comercial SET uid_global=gen_random_uuid() WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id})
        after = db_session.execute(text("SELECT uid_global,created_at,version_registro FROM configuracion_calendario_comercial WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id}).one()
        assert after[:2] == before[:2]
        assert after.version_registro == 2


@pytest.mark.parametrize(
    "raw",
    ["0", "32", "texto"],
)
def test_patch_rechaza_valor_preexistente_incompatible_sin_sanear(db_session, raw):
    with db_session.begin_nested():
        db_session.execute(text(
            "ALTER TABLE valor_parametro DISABLE TRIGGER "
            "trg_biu_valor_parametro_calendario_comercial"
        ))
        value_id = db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,:raw,false FROM parametro_sistema
           WHERE codigo_parametro=:code RETURNING id_valor_parametro
        """), {"raw": raw, "code": CODES[0]}).scalar_one()
        db_session.execute(text(
            "ALTER TABLE valor_parametro ENABLE TRIGGER "
            "trg_biu_valor_parametro_calendario_comercial"
        ))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(
            text("SELECT valor_parametro FROM valor_parametro WHERE id_valor_parametro=:id"),
            {"id": value_id},
        ).scalar_one() == raw


@pytest.mark.parametrize("raw", ["1", "015", "31"])
def test_patch_acepta_valor_preexistente_compatible_sin_mutarlo(db_session, raw):
    with db_session.begin_nested():
        value_id = db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,:raw,false FROM parametro_sistema
           WHERE codigo_parametro=:code RETURNING id_valor_parametro
        """), {"raw": raw, "code": CODES[0]}).scalar_one()
        db_session.execute(text(_sql()))
        assert db_session.execute(
            text("SELECT valor_parametro FROM valor_parametro WHERE id_valor_parametro=:id"),
            {"id": value_id},
        ).scalar_one() == raw


@pytest.mark.parametrize(
    ("raw", "accepted"),
    [
        ("1", True), ("015", True), ("31", True),
        ("0", False), ("000", False), ("-0", False), ("32", False),
        ("abc", False), ("+1", False), ("1.0", False), (" 1", False),
    ],
)
def test_rango_exclusivo_calendario(db_session, raw, accepted):
    statement = text("""
      INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
      SELECT id_parametro_sistema,:raw,false FROM parametro_sistema WHERE codigo_parametro=:code
    """)
    if accepted:
        with db_session.begin_nested():
            db_session.execute(statement, {"raw": raw, "code": CODES[0]})
    else:
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(statement, {"raw": raw, "code": CODES[0]})


def test_otro_entero_no_queda_limitado_y_global_rechaza_contexto(db_session):
    with db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,'999',false FROM parametro_sistema
           WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'
        """))
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,id_instalacion,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,1,'15',false FROM parametro_sistema WHERE codigo_parametro=:code
        """), {"code": CODES[0]})
