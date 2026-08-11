import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

BACKEND = Path(__file__).resolve().parents[1]
PATCH_NAME = "patch_operacion_idempotente_20260810.sql"
PATCH = BACKEND / "database" / PATCH_NAME
EXPECTED_COLUMN_ORDER = (
    "id_operacion_idempotente", "op_id", "command_code", "target_type",
    "target_uid", "target_key", "payload_hash", "canonicalization_version",
    "result_code", "result_http_status", "result_target_uid", "result_version",
    "response_snapshot", "id_usuario", "id_sucursal", "id_instalacion", "created_at",
)
EXPECTED_COLUMNS = set(EXPECTED_COLUMN_ORDER)
PROHIBITED_COLUMNS = {
    "uid_global", "version_registro", "updated_at", "deleted_at", "op_id_alta",
    "op_id_ultima_modificacion", "id_instalacion_origen",
    "id_instalacion_ultima_modificacion", "status", "completed_at",
}
HISTORICAL_HELPER_SQL = """
CREATE OR REPLACE FUNCTION public.fn_assert_instalacion_pertenece_a_sucursal(
    p_id_instalacion bigint, p_id_sucursal bigint, p_contexto text
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    v_ok BOOLEAN;
BEGIN
    IF p_id_instalacion IS NULL OR p_id_sucursal IS NULL THEN
        RETURN;
    END IF;
    SELECT EXISTS (
        SELECT 1 FROM instalacion i
        WHERE i.id_instalacion = p_id_instalacion
          AND i.id_sucursal = p_id_sucursal
    ) INTO v_ok;
    IF NOT v_ok THEN
        RAISE EXCEPTION 'Inconsistencia sucursal/instalacion en %: instalacion % no pertenece a sucursal %',
            p_contexto, p_id_instalacion, p_id_sucursal;
    END IF;
END;
$$;
"""


def _patch_body() -> str:
    sql = PATCH.read_text(encoding="utf-8")
    return sql.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _installation(db) -> int:
    return db.execute(text("SELECT id_instalacion FROM instalacion ORDER BY id_instalacion LIMIT 1")).scalar_one()


def _installation_context(db) -> tuple[int, int]:
    row = db.execute(text("""
        SELECT id_instalacion, id_sucursal
          FROM instalacion
         ORDER BY id_instalacion
         LIMIT 1
    """)).one()
    return row.id_instalacion, row.id_sucursal


def _helper_body(db) -> str:
    return db.execute(text("""
        SELECT prosrc
          FROM pg_proc
         WHERE oid='public.fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)'::regprocedure
    """)).scalar_one()


def _supports_conenforced(db) -> bool:
    return db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_attribute
            WHERE attrelid='pg_catalog.pg_constraint'::regclass
              AND attname='conenforced' AND NOT attisdropped
        )
    """)).scalar_one()


def _identity_sequence(db) -> str:
    return db.execute(text("""
        SELECT seq.oid::regclass::text FROM pg_class seq
        JOIN pg_depend d ON d.objid=seq.oid
        WHERE d.refobjid='public.operacion_idempotente'::regclass
          AND d.refobjsubid=1 AND d.deptype='i'
    """)).scalar_one()


def _sequence_state(db, sequence: str) -> tuple[int, bool]:
    row = db.execute(text(f"SELECT last_value,is_called FROM {sequence}")).one()
    return row.last_value, row.is_called


def _insert(db, **changes):
    values = {
        "op_id": uuid4(), "command_code": "TEST.COMMAND", "target_type": "TEST",
        "target_uid": None, "target_key": None, "payload_hash": "a" * 64,
        "canonicalization_version": 1, "result_code": "COMPLETED",
        "result_http_status": None, "result_target_uid": None, "result_version": None,
        "response_snapshot": json.dumps({"ok": True}), "id_usuario": None,
        "id_sucursal": None, "id_instalacion": _installation(db),
    }
    values.update(changes)
    columns = list(values)
    return db.execute(text(
        f"INSERT INTO operacion_idempotente ({','.join(columns)}) "
        f"VALUES ({','.join(':'+column for column in columns)}) RETURNING *"
    ), values).mappings().one()


def test_schema_fisico_exacto(db_session):
    relation = db_session.execute(text("""
        SELECT c.relkind,c.relpersistence
          FROM pg_class c
          JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='public' AND c.relname='operacion_idempotente'
    """)).one()
    assert (relation.relkind, relation.relpersistence) == ("r", "p")
    relation_flags = db_session.execute(text("""
        SELECT relispartition,relrowsecurity,relforcerowsecurity
        FROM pg_class WHERE oid='public.operacion_idempotente'::regclass
    """)).one()
    assert tuple(relation_flags) == (False, False, False)
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_inherits
        WHERE inhrelid='public.operacion_idempotente'::regclass
           OR inhparent='public.operacion_idempotente'::regclass
    """)).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM pg_rewrite WHERE ev_class='public.operacion_idempotente'::regclass")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM pg_policy WHERE polrelid='public.operacion_idempotente'::regclass")).scalar_one() == 0
    columns = db_session.execute(text("""
      SELECT column_name,data_type,character_maximum_length,is_nullable,column_default,
             identity_generation
        FROM information_schema.columns
       WHERE table_schema='public' AND table_name='operacion_idempotente'
    """)).mappings().all()
    by_name = {row["column_name"]: row for row in columns}
    assert set(by_name) == EXPECTED_COLUMNS
    assert not PROHIBITED_COLUMNS & set(by_name)
    expected_types = {
        "id_operacion_idempotente": ("bigint", None), "op_id": ("uuid", None),
        "command_code": ("character varying", 100), "target_type": ("character varying", 100),
        "target_uid": ("uuid", None), "target_key": ("character varying", 200),
        "payload_hash": ("character", 64), "canonicalization_version": ("integer", None),
        "result_code": ("character varying", 100), "result_http_status": ("integer", None),
        "result_target_uid": ("uuid", None), "result_version": ("integer", None),
        "response_snapshot": ("jsonb", None), "id_usuario": ("bigint", None),
        "id_sucursal": ("bigint", None), "id_instalacion": ("bigint", None),
        "created_at": ("timestamp without time zone", None),
    }
    for name, expected in expected_types.items():
        assert (by_name[name]["data_type"], by_name[name]["character_maximum_length"]) == expected
    nullable = {"target_uid", "target_key", "result_http_status", "result_target_uid", "result_version", "id_usuario", "id_sucursal"}
    assert {name for name, row in by_name.items() if row["is_nullable"] == "YES"} == nullable
    assert by_name["id_operacion_idempotente"]["identity_generation"] == "BY DEFAULT"
    assert by_name["created_at"]["column_default"] == "CURRENT_TIMESTAMP"
    assert all(row["column_default"] is None for name, row in by_name.items() if name not in {"created_at", "id_operacion_idempotente"})
    attributes = db_session.execute(text("""
        SELECT attnum,attname,atttypmod,attidentity,attgenerated,attisdropped
        FROM pg_attribute
        WHERE attrelid='public.operacion_idempotente'::regclass AND attnum>0
        ORDER BY attnum
    """)).all()
    assert [row.attname for row in attributes] == list(EXPECTED_COLUMN_ORDER)
    assert attributes[0].attidentity == "d"
    assert all(row.attidentity == "" for row in attributes[1:])
    assert all(row.attgenerated == "" and not row.attisdropped for row in attributes)
    assert attributes[-1].atttypmod == -1

    constraints = dict(db_session.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='operacion_idempotente'::regclass")).all())
    assert set(constraints) == {
        "operacion_idempotente_pkey", "uq_operacion_idempotente_op_id",
        "chk_operacion_idempotente_command_code", "chk_operacion_idempotente_target_type",
        "chk_operacion_idempotente_target_key", "chk_operacion_idempotente_payload_hash",
        "chk_operacion_idempotente_canonicalization_version", "chk_operacion_idempotente_result_code",
        "chk_operacion_idempotente_result_http_status", "chk_operacion_idempotente_result_version",
        "fk_operacion_idempotente_usuario", "fk_operacion_idempotente_sucursal",
        "fk_operacion_idempotente_instalacion",
    }
    assert all("ON DELETE RESTRICT" in constraints[name] for name in constraints if name.startswith("fk_"))
    check_validation = dict(db_session.execute(text("""
        SELECT conname,convalidated FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass AND contype='c'
    """)).all())
    assert len(check_validation) == 8
    assert all(check_validation.values())
    indexes = db_session.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='operacion_idempotente'")).scalars().all()
    assert set(indexes) == {"operacion_idempotente_pkey", "uq_operacion_idempotente_op_id"}
    index_contract = {
        row.conname: row
        for row in db_session.execute(text("""
            SELECT c.conname,c.condeferrable,c.condeferred,c.convalidated,c.conislocal,
                   c.coninhcount,i.indisprimary,i.indisunique,i.indimmediate,
                   i.indisvalid,i.indisready,i.indislive,i.indnkeyatts,i.indnatts,
                   i.indpred IS NULL pred_null,i.indexprs IS NULL expr_null
            FROM pg_constraint c JOIN pg_index i ON i.indexrelid=c.conindid
            WHERE c.conrelid='public.operacion_idempotente'::regclass AND c.contype IN ('p','u')
        """))
    }
    assert set(index_contract) == {"operacion_idempotente_pkey", "uq_operacion_idempotente_op_id"}
    for row in index_contract.values():
        assert not row.condeferrable and not row.condeferred and row.convalidated
        assert row.conislocal and row.coninhcount == 0
        assert row.indisunique and row.indimmediate and row.indisvalid and row.indisready and row.indislive
        assert row.indnkeyatts == row.indnatts == 1 and row.pred_null and row.expr_null
    assert index_contract["operacion_idempotente_pkey"].indisprimary
    assert not index_contract["uq_operacion_idempotente_op_id"].indisprimary
    fk_contract = db_session.execute(text("""
        SELECT conname,confupdtype,confdeltype,confmatchtype,condeferrable,
               condeferred,convalidated,conislocal,coninhcount
        FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass AND contype='f'
    """)).all()
    assert len(fk_contract) == 3
    assert all((r.confupdtype,r.confdeltype,r.confmatchtype) == ("a","r","s") for r in fk_contract)
    assert all(not r.condeferrable and not r.condeferred and r.convalidated and r.conislocal and r.coninhcount == 0 for r in fk_contract)
    ri_contract = db_session.execute(text("""
        SELECT c.conname,count(t.oid) trigger_count,
               count(t.oid) FILTER (WHERE t.tgisinternal AND t.tgenabled='O') enabled_internal_count,
               count(t.oid) FILTER (WHERE t.tgrelid=c.conrelid) local_count,
               count(t.oid) FILTER (WHERE t.tgrelid=c.confrelid) remote_count
        FROM pg_constraint c JOIN pg_trigger t ON t.tgconstraint=c.oid
        WHERE c.conrelid='public.operacion_idempotente'::regclass AND c.contype='f'
        GROUP BY c.oid,c.conname
    """)).all()
    assert len(ri_contract) == 3
    assert all(tuple(row)[1:] == (4, 4, 2, 2) for row in ri_contract)
    sequence_contract = db_session.execute(text("""
        SELECT count(*),min(s.seqincrement),min(s.seqstart),min(s.seqmin),
               min(s.seqmax),bool_and(NOT s.seqcycle)
        FROM pg_depend d
        JOIN pg_class seq ON seq.oid=d.objid
        JOIN pg_sequence s ON s.seqrelid=seq.oid
        WHERE d.refobjid='public.operacion_idempotente'::regclass
          AND d.refobjsubid=1 AND d.deptype='i'
          AND seq.relkind='S' AND seq.relpersistence='p' AND s.seqtypid='bigint'::regtype
    """)).one()
    assert tuple(sequence_contract) == (1, 1, 1, 1, 9223372036854775807, True)
    triggers = {
        row.tgname: (row.tgenabled, row.tgqual, row.attribute_count)
        for row in db_session.execute(text("""
            SELECT tgname,tgenabled,tgqual,cardinality(tgattr::smallint[]) attribute_count
            FROM pg_trigger
            WHERE tgrelid='public.operacion_idempotente'::regclass AND NOT tgisinternal
        """))
    }
    assert triggers == {
        "trg_bi_operacion_idempotente_instalacion_sucursal": ("A", None, 0),
        "trg_bt_operacion_idempotente_inmutable": ("A", None, 0),
        "trg_bud_operacion_idempotente_inmutable": ("A", None, 0),
    }
    functions = set(db_session.execute(text("""
        SELECT p.proname
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid=p.pronamespace
         WHERE n.nspname='public'
           AND p.proname IN (
             'fn_assert_instalacion_pertenece_a_sucursal',
             'trg_operacion_idempotente_instalacion_sucursal',
             'trg_operacion_idempotente_inmutable'
           )
    """)).scalars())
    assert functions == {
        "fn_assert_instalacion_pertenece_a_sucursal",
        "trg_operacion_idempotente_instalacion_sucursal",
        "trg_operacion_idempotente_inmutable",
    }


def test_unicidad_global_op_id_y_target_no_unico(db_session):
    op_id, target_uid = uuid4(), uuid4()
    _insert(db_session, op_id=op_id, target_uid=target_uid)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(db_session, op_id=op_id, command_code="OTHER")
    _insert(db_session, target_uid=target_uid)


@pytest.mark.parametrize(("changes", "valid"), [
    ({"command_code": " "}, False), ({"target_type": ""}, False), ({"target_key": "  "}, False),
    *[( {field: whitespace}, False) for field in ("command_code", "target_type", "target_key", "result_code") for whitespace in ("\t", "\n", "\r", "\f", "\x0b", " \t\r\n\f\x0b")],
    ({"target_uid": None, "target_key": None}, True), ({"payload_hash": "a" * 64}, True),
    ({"payload_hash": "a" * 63}, False), ({"payload_hash": "a" * 65}, False),
    ({"payload_hash": "A" * 64}, False), ({"payload_hash": "g" * 64}, False),
    ({"canonicalization_version": 0}, False), ({"canonicalization_version": -1}, False),
    ({"canonicalization_version": 2}, True), ({"result_code": " "}, False),
    ({"result_http_status": None}, True), ({"result_http_status": 100}, True),
    ({"result_http_status": 599}, True), ({"result_http_status": 99}, False),
    ({"result_http_status": 600}, False), ({"result_version": None}, True),
    ({"result_version": 1}, True), ({"result_version": 0}, False), ({"result_version": -1}, False),
    ({"id_usuario": None, "id_sucursal": None}, True), ({"id_instalacion": None}, False),
    ({"id_usuario": 999999999}, False), ({"id_sucursal": 999999999}, False),
    ({"id_instalacion": 999999999}, False),
])
def test_checks_contexto_y_fks(db_session, changes, valid):
    if valid:
        _insert(db_session, **changes)
    else:
        with pytest.raises(DBAPIError), db_session.begin_nested():
            _insert(db_session, **changes)


def test_canonicalization_version_sin_default(db_session):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO operacion_idempotente
            (op_id,command_code,target_type,payload_hash,result_code,response_snapshot,id_instalacion)
          VALUES (:op,'C','T',:hash,'OK','{}',:installation)
        """), {"op": uuid4(), "hash": "a" * 64, "installation": _installation(db_session)})


def test_contexto_sucursal_instalacion_consistente_y_sucursal_opcional(db_session):
    installation_id, branch_id = _installation_context(db_session)
    _insert(db_session, id_sucursal=branch_id, id_instalacion=installation_id)
    _insert(db_session, id_sucursal=None, id_instalacion=installation_id)


def test_contexto_sucursal_instalacion_inconsistente_es_rechazado(db_session):
    installation_id, branch_id = _installation_context(db_session)
    other_branch = db_session.execute(text("""
        INSERT INTO sucursal (
            codigo_sucursal, nombre_sucursal, estado_sucursal
        ) VALUES (
            :code, 'Sucursal ajena #469', 'ACTIVA'
        ) RETURNING id_sucursal
    """), {"code": f"SUC_469_{uuid4().hex[:12]}"}).scalar_one()
    assert other_branch != branch_id
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(
            db_session,
            id_sucursal=other_branch,
            id_instalacion=installation_id,
        )


def test_contexto_historico_inconsistente_falla_sin_reparacion(db_session):
    installation_id, branch_id = _installation_context(db_session)
    scenario = db_session.begin_nested()
    other_branch = db_session.execute(text("""
        INSERT INTO public.sucursal (
            codigo_sucursal, nombre_sucursal, estado_sucursal
        ) VALUES (
            :code, 'Sucursal histórica ajena #469', 'ACTIVA'
        ) RETURNING id_sucursal
    """), {"code": f"SUC_HIST_469_{uuid4().hex[:8]}"}).scalar_one()
    assert other_branch != branch_id

    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        DISABLE TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal
    """))
    receipt = _insert(
        db_session,
        id_sucursal=other_branch,
        id_instalacion=installation_id,
    )
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        ENABLE ALWAYS TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal
    """))

    trigger_contract = db_session.execute(text("""
        SELECT tgenabled,tgtype,tgqual,
               cardinality(tgattr::smallint[]) attribute_count,
               tgfoid='public.trg_operacion_idempotente_instalacion_sucursal()'::regprocedure function_matches
        FROM pg_trigger
        WHERE tgrelid='public.operacion_idempotente'::regclass
          AND tgname='trg_bi_operacion_idempotente_instalacion_sucursal'
          AND NOT tgisinternal
    """)).one()
    assert tuple(trigger_contract) == ("A", 7, None, 0, True)
    assert db_session.execute(text("""
        SELECT count(*)
        FROM public.operacion_idempotente oi
        JOIN public.instalacion i ON i.id_instalacion=oi.id_instalacion
        WHERE oi.id_operacion_idempotente=:id
          AND oi.id_sucursal IS DISTINCT FROM i.id_sucursal
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))

    persisted = db_session.execute(text("""
        SELECT id_sucursal,id_instalacion
        FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).one()
    assert tuple(persisted) == (other_branch, installation_id)
    assert db_session.execute(text("""
        SELECT tgenabled FROM pg_trigger
        WHERE tgrelid='public.operacion_idempotente'::regclass
          AND tgname='trg_bi_operacion_idempotente_instalacion_sucursal'
    """)).scalar_one() == "A"
    scenario.rollback()


def test_contexto_no_puede_ser_enganado_por_search_path(db_session):
    installation_id, branch_id = _installation_context(db_session)
    other_branch = db_session.execute(text("""
        INSERT INTO sucursal (codigo_sucursal, nombre_sucursal, estado_sucursal)
        VALUES (:code, 'Sucursal shadow #469', 'ACTIVA')
        RETURNING id_sucursal
    """), {"code": f"SUC_SHADOW_469_{uuid4().hex[:8]}"}).scalar_one()
    assert other_branch != branch_id
    db_session.execute(text("""
        CREATE TEMP TABLE instalacion (
            id_instalacion bigint PRIMARY KEY,
            id_sucursal bigint NOT NULL
        ) ON COMMIT DROP
    """))
    db_session.execute(
        text("INSERT INTO pg_temp.instalacion VALUES (:installation, :branch)"),
        {"installation": installation_id, "branch": other_branch},
    )
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(
            db_session,
            id_sucursal=other_branch,
            id_instalacion=installation_id,
        )


def test_upgrade_incremental_migra_helper_historico_y_crea_ledger_seguro(db_session):
    db_session.execute(text("DROP TABLE public.operacion_idempotente"))
    db_session.execute(text("DROP FUNCTION public.trg_operacion_idempotente_inmutable()"))
    db_session.execute(text("DROP FUNCTION public.trg_operacion_idempotente_instalacion_sucursal()"))
    db_session.execute(text(HISTORICAL_HELPER_SQL))
    assert "FROM instalacion i" in _helper_body(db_session)

    db_session.execute(text(_patch_body()))

    assert "FROM public.instalacion AS i" in _helper_body(db_session)
    assert db_session.execute(text("SELECT to_regclass('public.operacion_idempotente') IS NOT NULL")).scalar_one()
    installation_id, branch_id = _installation_context(db_session)
    other_branch = db_session.execute(text("""
        INSERT INTO sucursal (codigo_sucursal, nombre_sucursal, estado_sucursal)
        VALUES (:code, 'Sucursal upgrade #469', 'ACTIVA') RETURNING id_sucursal
    """), {"code": f"SUC_UPGRADE_469_{uuid4().hex[:8]}"}).scalar_one()
    assert other_branch != branch_id
    db_session.execute(text("CREATE TEMP TABLE instalacion (id_instalacion bigint, id_sucursal bigint) ON COMMIT DROP"))
    db_session.execute(text("INSERT INTO pg_temp.instalacion VALUES (:i,:s)"), {"i": installation_id, "s": other_branch})
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(db_session, id_sucursal=other_branch, id_instalacion=installation_id)


def test_helper_seguro_no_es_reemplazado_en_reejecucion(db_session):
    oid_before = db_session.execute(text("SELECT 'public.fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)'::regprocedure::oid")).scalar_one()
    body_before = _helper_body(db_session)
    db_session.execute(text(_patch_body()))
    assert db_session.execute(text("SELECT 'public.fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)'::regprocedure::oid")).scalar_one() == oid_before
    assert _helper_body(db_session) == body_before


def test_helper_desconocido_falla_sin_reemplazo(db_session):
    db_session.execute(text("""
        CREATE OR REPLACE FUNCTION public.fn_assert_instalacion_pertenece_a_sucursal(
            p_id_instalacion bigint, p_id_sucursal bigint, p_contexto text
        ) RETURNS void LANGUAGE plpgsql AS $$ BEGIN RETURN; END $$
    """))
    unknown_body = _helper_body(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert _helper_body(db_session) == unknown_body


def test_migracion_helper_y_ledger_son_atomicos(db_session):
    db_session.execute(text(HISTORICAL_HELPER_SQL))
    db_session.execute(text("ALTER TABLE operacion_idempotente ALTER COLUMN target_key TYPE text"))
    historical_body = _helper_body(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert _helper_body(db_session) == historical_body
    assert "FROM instalacion i" in historical_body


def test_jsonb_timestamp_e_inmutabilidad(db_session):
    snapshot = {"nested": {"array": [True, None, "áé漢字"]}}
    row = _insert(db_session, response_snapshot=json.dumps(snapshot, ensure_ascii=False))
    assert row["response_snapshot"] == snapshot
    assert row["created_at"] is not None
    for statement in (
        "UPDATE operacion_idempotente SET result_code='OTHER' WHERE id_operacion_idempotente=:id",
        "DELETE FROM operacion_idempotente WHERE id_operacion_idempotente=:id",
    ):
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(statement), {"id": row["id_operacion_idempotente"]})
    current = db_session.execute(text("SELECT result_code FROM operacion_idempotente WHERE id_operacion_idempotente=:id"), {"id": row["id_operacion_idempotente"]}).scalar_one()
    assert current == "COMPLETED"


def test_truncate_es_rechazado_y_conserva_receipts(db_session):
    row = _insert(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("TRUNCATE TABLE public.operacion_idempotente"))
    assert db_session.execute(text("""
        SELECT count(*) FROM operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]}).scalar_one() == 1


def test_guard_delete_deshabilitado_expone_riesgo_y_patch_falla(db_session):
    row = _insert(db_session)
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        DISABLE TRIGGER trg_bud_operacion_idempotente_inmutable
    """))
    db_session.execute(text("""
        DELETE FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]})
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]}).scalar_one() == 0
    scenario.rollback()
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]}).scalar_one() == 1

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
            ALTER TABLE public.operacion_idempotente
            DISABLE TRIGGER trg_bud_operacion_idempotente_inmutable
        """))
        db_session.execute(text(_patch_body()))


def test_guard_delete_con_when_false_expone_riesgo_y_patch_falla(db_session):
    row = _insert(db_session)
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        DROP TRIGGER trg_bud_operacion_idempotente_inmutable
        ON public.operacion_idempotente;
        CREATE TRIGGER trg_bud_operacion_idempotente_inmutable
        BEFORE UPDATE OR DELETE ON public.operacion_idempotente
        FOR EACH ROW WHEN (false)
        EXECUTE FUNCTION public.trg_operacion_idempotente_inmutable();
        ALTER TABLE public.operacion_idempotente
        ENABLE ALWAYS TRIGGER trg_bud_operacion_idempotente_inmutable
    """))
    assert db_session.execute(text("""
        SELECT tgqual IS NOT NULL FROM pg_trigger
        WHERE tgrelid='public.operacion_idempotente'::regclass
          AND tgname='trg_bud_operacion_idempotente_inmutable'
    """)).scalar_one()
    db_session.execute(text("""
        DELETE FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]})
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": row["id_operacion_idempotente"]}).scalar_one() == 0
    scenario.rollback()

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
            DROP TRIGGER trg_bud_operacion_idempotente_inmutable
            ON public.operacion_idempotente;
            CREATE TRIGGER trg_bud_operacion_idempotente_inmutable
            BEFORE UPDATE OR DELETE ON public.operacion_idempotente
            FOR EACH ROW WHEN (false)
            EXECUTE FUNCTION public.trg_operacion_idempotente_inmutable();
            ALTER TABLE public.operacion_idempotente
            ENABLE ALWAYS TRIGGER trg_bud_operacion_idempotente_inmutable
        """))
        db_session.execute(text(_patch_body()))


def test_guards_always_operan_con_session_replication_role_replica(db_session):
    receipt = _insert(db_session)
    installation_id, branch_id = _installation_context(db_session)
    other_branch = db_session.execute(text("""
        INSERT INTO sucursal (codigo_sucursal,nombre_sucursal,estado_sucursal)
        VALUES (:code,'Sucursal replica #469','ACTIVA') RETURNING id_sucursal
    """), {"code": f"SUC_REPLICA_469_{uuid4().hex[:8]}"}).scalar_one()
    assert other_branch != branch_id

    operations = [
        ("DELETE FROM public.operacion_idempotente WHERE id_operacion_idempotente=:id", {"id": receipt["id_operacion_idempotente"]}),
        ("UPDATE public.operacion_idempotente SET result_code='ALTERED' WHERE id_operacion_idempotente=:id", {"id": receipt["id_operacion_idempotente"]}),
        ("TRUNCATE TABLE public.operacion_idempotente", {}),
    ]
    for statement, params in operations:
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text("SET LOCAL session_replication_role = replica"))
            db_session.execute(text(statement), params)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("SET LOCAL session_replication_role = replica"))
        _insert(db_session, id_sucursal=other_branch, id_instalacion=installation_id)
    assert db_session.execute(text("""
        SELECT result_code FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == "COMPLETED"


def test_check_contractual_not_valid_con_fila_invalida_falla_sin_reparar(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        DROP CONSTRAINT chk_operacion_idempotente_payload_hash
    """))
    invalid = _insert(db_session, payload_hash="INVALID")
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        ADD CONSTRAINT chk_operacion_idempotente_payload_hash
        CHECK (payload_hash ~ '^[0-9a-f]{64}$') NOT VALID
    """))
    assert not db_session.execute(text("""
        SELECT convalidated FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='chk_operacion_idempotente_payload_hash'
    """)).scalar_one()
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert not db_session.execute(text("""
        SELECT convalidated FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='chk_operacion_idempotente_payload_hash'
    """)).scalar_one()
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id AND payload_hash='INVALID'
    """), {"id": invalid["id_operacion_idempotente"]}).scalar_one() == 1
    scenario.rollback()


def test_tabla_unlogged_falla_sin_reparar_ni_modificar_receipt(db_session):
    receipt = _insert(db_session)
    scenario = db_session.begin_nested()
    db_session.execute(text("ALTER TABLE public.operacion_idempotente SET UNLOGGED"))
    assert db_session.execute(text("""
        SELECT relpersistence FROM pg_class
        WHERE oid='public.operacion_idempotente'::regclass
    """)).scalar_one() == "u"
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text("""
        SELECT relpersistence FROM pg_class
        WHERE oid='public.operacion_idempotente'::regclass
    """)).scalar_one() == "u"
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1
    scenario.rollback()


def test_unique_deferrable_falla_y_unique_final_conflicta_en_segundo_insert(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente DROP CONSTRAINT uq_operacion_idempotente_op_id;
        ALTER TABLE public.operacion_idempotente ADD CONSTRAINT uq_operacion_idempotente_op_id
        UNIQUE (op_id) DEFERRABLE INITIALLY DEFERRED
    """))
    drift = db_session.execute(text("""
        SELECT condeferrable,condeferred FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='uq_operacion_idempotente_op_id'
    """)).one()
    assert tuple(drift) == (True, True)
    duplicate = uuid4()
    _insert(db_session, op_id=duplicate)
    _insert(db_session, op_id=duplicate)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text("""
        SELECT condeferrable FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='uq_operacion_idempotente_op_id'
    """)).scalar_one()
    scenario.rollback()

    immediate = uuid4()
    _insert(db_session, op_id=immediate)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(db_session, op_id=immediate)


@pytest.mark.parametrize(("constraint_name", "definition", "drift_query", "drift_value"), [
    (
        "operacion_idempotente_pkey",
        "PRIMARY KEY (id_operacion_idempotente) DEFERRABLE INITIALLY DEFERRED",
        "SELECT condeferrable FROM pg_constraint WHERE conrelid='public.operacion_idempotente'::regclass AND conname='operacion_idempotente_pkey'",
        True,
    ),
    (
        "uq_operacion_idempotente_op_id",
        "UNIQUE (op_id) INCLUDE (command_code)",
        "SELECT indnatts FROM pg_index WHERE indexrelid=(SELECT conindid FROM pg_constraint WHERE conrelid='public.operacion_idempotente'::regclass AND conname='uq_operacion_idempotente_op_id')",
        2,
    ),
])
def test_pk_o_indice_unique_no_contractual_falla(db_session, constraint_name, definition, drift_query, drift_value):
    scenario = db_session.begin_nested()
    db_session.execute(text(f"ALTER TABLE public.operacion_idempotente DROP CONSTRAINT {constraint_name}"))
    db_session.execute(text(f"ALTER TABLE public.operacion_idempotente ADD CONSTRAINT {constraint_name} {definition}"))
    assert db_session.execute(text(drift_query)).scalar_one() == drift_value
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text(drift_query)).scalar_one() == drift_value
    scenario.rollback()


def test_identity_sequence_unlogged_falla_sin_reparacion(db_session):
    scenario = db_session.begin_nested()
    sequence = db_session.execute(text("""
        SELECT seq.oid::regclass::text FROM pg_class seq
        JOIN pg_depend d ON d.objid=seq.oid
        WHERE d.refobjid='public.operacion_idempotente'::regclass
          AND d.refobjsubid=1 AND d.deptype='i'
    """)).scalar_one()
    db_session.execute(text(f"ALTER SEQUENCE {sequence} SET UNLOGGED"))
    assert db_session.execute(text(f"SELECT relpersistence FROM pg_class WHERE oid='{sequence}'::regclass")).scalar_one() == "u"
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text(f"SELECT relpersistence FROM pg_class WHERE oid='{sequence}'::regclass")).scalar_one() == "u"
    scenario.rollback()


def test_identity_sequence_cycle_y_maxvalue_fallan_sin_reparacion(db_session):
    receipt = _insert(db_session)
    scenario = db_session.begin_nested()
    sequence = db_session.execute(text("""
        SELECT seq.oid::regclass::text FROM pg_class seq
        JOIN pg_depend d ON d.objid=seq.oid
        WHERE d.refobjid='public.operacion_idempotente'::regclass
          AND d.refobjsubid=1 AND d.deptype='i'
    """)).scalar_one()
    sequence_oid = db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one()
    db_session.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1 MAXVALUE 2 CYCLE"))
    drift = db_session.execute(text(f"""
        SELECT seqmax,seqcycle FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).one()
    assert tuple(drift) == (2, True)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one() == sequence_oid
    assert tuple(db_session.execute(text(f"""
        SELECT seqmax,seqcycle FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).one()) == (2, True)
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1
    scenario.rollback()


def test_identity_sequence_start_incompatible_falla_sin_reparacion(db_session):
    receipt = _insert(db_session)
    scenario = db_session.begin_nested()
    sequence = db_session.execute(text("""
        SELECT seq.oid::regclass::text FROM pg_class seq
        JOIN pg_depend d ON d.objid=seq.oid
        WHERE d.refobjid='public.operacion_idempotente'::regclass
          AND d.refobjsubid=1 AND d.deptype='i'
    """)).scalar_one()
    sequence_oid = db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one()
    db_session.execute(text(f"""
        ALTER SEQUENCE {sequence}
        START WITH 9223372036854775807 RESTART
    """))
    assert db_session.execute(text(f"""
        SELECT seqstart FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).scalar_one() == 9223372036854775807
    assert db_session.execute(text(f"SELECT nextval('{sequence}')")).scalar_one() == 9223372036854775807
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(f"SELECT nextval('{sequence}')"))

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one() == sequence_oid
    assert db_session.execute(text(f"""
        SELECT seqstart FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).scalar_one() == 9223372036854775807
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1
    scenario.rollback()


def test_identity_sequence_agotada_falla_sin_reparacion(db_session):
    receipt = _insert(db_session)
    sequence = _identity_sequence(db_session)
    sequence_oid = db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one()
    original_state = _sequence_state(db_session, sequence)
    configuration = db_session.execute(text(f"""
        SELECT seqtypid,seqincrement,seqstart,seqmin,seqmax,seqcycle
        FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).one()

    scenario = db_session.begin_nested()
    db_session.execute(text(
        f"SELECT setval('{sequence}', 9223372036854775807, true)"
    ))
    assert _sequence_state(db_session, sequence) == (9223372036854775807, True)
    assert tuple(db_session.execute(text(f"""
        SELECT seqtypid,seqincrement,seqstart,seqmin,seqmax,seqcycle
        FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).one()) == tuple(configuration)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(f"SELECT nextval('{sequence}')"))

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert _sequence_state(db_session, sequence) == (9223372036854775807, True)
    assert db_session.execute(text(f"SELECT '{sequence}'::regclass::oid")).scalar_one() == sequence_oid
    assert tuple(db_session.execute(text(f"""
        SELECT seqtypid,seqincrement,seqstart,seqmin,seqmax,seqcycle
        FROM pg_sequence WHERE seqrelid='{sequence}'::regclass
    """)).one()) == tuple(configuration)
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1
    db_session.execute(text(
        f"SELECT setval('{sequence}', :value, :called)"
    ), {"value": original_state[0], "called": original_state[1]})
    scenario.rollback()


@pytest.mark.parametrize("is_called", [True, False])
def test_identity_sequence_valor_avanzado_utilizable_es_aceptado(db_session, is_called):
    sequence = _identity_sequence(db_session)
    original_state = _sequence_state(db_session, sequence)
    scenario = db_session.begin_nested()
    db_session.execute(text(
        f"SELECT setval('{sequence}', 1500, :called)"
    ), {"called": is_called})
    assert _sequence_state(db_session, sequence) == (1500, is_called)
    db_session.execute(text(_patch_body()))
    assert _sequence_state(db_session, sequence) == (1500, is_called)
    db_session.execute(text(
        f"SELECT setval('{sequence}', :value, :called)"
    ), {"value": original_state[0], "called": original_state[1]})
    scenario.rollback()


def test_fk_ri_interno_disabled_falla_sin_reactivacion(db_session):
    scenario = db_session.begin_nested()
    fk_oid = db_session.execute(text("""
        SELECT oid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).scalar_one()
    triggers = db_session.execute(text("""
        SELECT t.oid,t.tgrelid::regclass::text relation_name,t.tgname
        FROM pg_trigger t WHERE t.tgconstraint=:fk_oid ORDER BY t.oid
    """), {"fk_oid": fk_oid}).all()
    assert len(triggers) == 4
    for trigger in triggers:
        db_session.execute(text(
            f'ALTER TABLE {trigger.relation_name} DISABLE TRIGGER "{trigger.tgname}"'
        ))
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_trigger
        WHERE tgconstraint=:fk_oid AND tgisinternal AND tgenabled='D'
    """), {"fk_oid": fk_oid}).scalar_one() == 4

    invalid_user = db_session.execute(text("SELECT coalesce(max(id_usuario),0)+1000000 FROM public.usuario")).scalar_one()
    invalid = _insert(db_session, id_usuario=invalid_user)
    assert invalid["id_usuario"] == invalid_user
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_trigger
        WHERE tgconstraint=:fk_oid AND tgenabled='D'
    """), {"fk_oid": fk_oid}).scalar_one() == 4
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id AND id_usuario=:user_id
    """), {"id": invalid["id_operacion_idempotente"], "user_id": invalid_user}).scalar_one() == 1
    scenario.rollback()


def test_fk_historica_huerfana_falla_con_ri_restaurada_sin_reparacion(db_session):
    scenario = db_session.begin_nested()
    fk_oid = db_session.execute(text("""
        SELECT oid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).scalar_one()
    triggers = db_session.execute(text("""
        SELECT t.tgrelid::regclass::text relation_name,t.tgname
        FROM pg_trigger t WHERE t.tgconstraint=:fk_oid ORDER BY t.oid
    """), {"fk_oid": fk_oid}).all()
    assert len(triggers) == 4
    for trigger in triggers:
        db_session.execute(text(
            f'ALTER TABLE {trigger.relation_name} DISABLE TRIGGER "{trigger.tgname}"'
        ))
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_trigger
        WHERE tgconstraint=:fk_oid AND tgisinternal AND tgenabled='D'
    """), {"fk_oid": fk_oid}).scalar_one() == 4

    invalid_user = db_session.execute(text(
        "SELECT coalesce(max(id_usuario),0)+1000000 FROM public.usuario"
    )).scalar_one()
    receipt = _insert(db_session, id_usuario=invalid_user)
    for trigger in triggers:
        db_session.execute(text(
            f'ALTER TABLE {trigger.relation_name} ENABLE TRIGGER "{trigger.tgname}"'
        ))

    fk_state = db_session.execute(text("""
        SELECT oid,convalidated FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).one()
    assert tuple(fk_state) == (fk_oid, True)
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_trigger
        WHERE tgconstraint=:fk_oid AND tgisinternal AND tgenabled='O'
    """), {"fk_oid": fk_oid}).scalar_one() == 4
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente oi
        LEFT JOIN public.usuario u ON u.id_usuario=oi.id_usuario
        WHERE oi.id_operacion_idempotente=:id
          AND oi.id_usuario=:user_id AND u.id_usuario IS NULL
    """), {"id": receipt["id_operacion_idempotente"], "user_id": invalid_user}).scalar_one() == 1

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))

    persisted = db_session.execute(text("""
        SELECT id_usuario FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one()
    assert persisted == invalid_user
    assert db_session.execute(text("""
        SELECT oid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).scalar_one() == fk_oid
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_trigger
        WHERE tgconstraint=:fk_oid AND tgenabled='O'
    """), {"fk_oid": fk_oid}).scalar_one() == 4
    scenario.rollback()


def test_pg18_check_not_enforced_falla_sin_reparar(db_session):
    if not _supports_conenforced(db_session):
        pytest.skip("pg_constraint.conenforced requiere PostgreSQL 18+")

    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        DROP CONSTRAINT chk_operacion_idempotente_payload_hash;
        ALTER TABLE public.operacion_idempotente
        ADD CONSTRAINT chk_operacion_idempotente_payload_hash
        CHECK (payload_hash ~ '^[0-9a-f]{64}$') NOT ENFORCED
    """))
    state = db_session.execute(text("""
        SELECT convalidated,conenforced FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='chk_operacion_idempotente_payload_hash'
    """)).one()
    assert tuple(state) == (True, False)
    invalid = _insert(db_session, payload_hash="INVALID")
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert tuple(db_session.execute(text("""
        SELECT convalidated,conenforced FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='chk_operacion_idempotente_payload_hash'
    """)).one()) == (True, False)
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id AND payload_hash='INVALID'
    """), {"id": invalid["id_operacion_idempotente"]}).scalar_one() == 1
    scenario.rollback()


def test_pg18_fk_not_enforced_falla_sin_reparar(db_session):
    if not _supports_conenforced(db_session):
        pytest.skip("pg_constraint.conenforced requiere PostgreSQL 18+")

    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        DROP CONSTRAINT fk_operacion_idempotente_usuario;
        ALTER TABLE public.operacion_idempotente
        ADD CONSTRAINT fk_operacion_idempotente_usuario
        FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario)
        ON DELETE RESTRICT NOT ENFORCED
    """))
    state = db_session.execute(text("""
        SELECT contype,convalidated,conenforced FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).one()
    assert tuple(state) == ("f", True, False)
    invalid_user = db_session.execute(text(
        "SELECT coalesce(max(id_usuario),0)+1000000 FROM public.usuario"
    )).scalar_one()
    invalid = _insert(db_session, id_usuario=invalid_user)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert tuple(db_session.execute(text("""
        SELECT contype,convalidated,conenforced FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).one()) == ("f", True, False)
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id AND id_usuario=:user_id
    """), {"id": invalid["id_operacion_idempotente"], "user_id": invalid_user}).scalar_one() == 1
    scenario.rollback()


def test_pg16_sin_conenforced_reejecuta_patch(db_session):
    if _supports_conenforced(db_session):
        pytest.skip("compatibilidad específica para catálogo anterior a PostgreSQL 18")
    db_session.execute(text(_patch_body()))


@pytest.mark.parametrize("definition", [
    "FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED",
    "FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT",
    "FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT NOT VALID",
])
def test_fk_usuario_con_semantica_no_contractual_falla_sin_reparar(db_session, definition):
    scenario = db_session.begin_nested()
    db_session.execute(text("ALTER TABLE public.operacion_idempotente DROP CONSTRAINT fk_operacion_idempotente_usuario"))
    db_session.execute(text(f"""
        ALTER TABLE public.operacion_idempotente
        ADD CONSTRAINT fk_operacion_idempotente_usuario {definition}
    """))
    drift = db_session.execute(text("""
        SELECT confupdtype,condeferrable,condeferred,convalidated
        FROM pg_constraint WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).one()
    assert tuple(drift) != ("a", False, False, True)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text("""
        SELECT confupdtype,condeferrable,condeferred,convalidated
        FROM pg_constraint WHERE conrelid='public.operacion_idempotente'::regclass
          AND conname='fk_operacion_idempotente_usuario'
    """)).one() == drift
    scenario.rollback()


def test_inheritance_como_padre_permitiria_op_id_duplicado_y_patch_falla(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        CREATE TABLE public.operacion_idempotente_hija
        (LIKE public.operacion_idempotente INCLUDING ALL);
        ALTER TABLE public.operacion_idempotente_hija
        INHERIT public.operacion_idempotente
    """))
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_inherits
        WHERE inhparent='public.operacion_idempotente'::regclass
    """)).scalar_one() == 1
    op_id = uuid4()
    _insert(db_session, op_id=op_id)
    installation = _installation(db_session)
    db_session.execute(text("""
        INSERT INTO public.operacion_idempotente_hija
          (op_id,command_code,target_type,payload_hash,canonicalization_version,
           result_code,response_snapshot,id_instalacion)
        VALUES (:op,'C','T',:hash,1,'OK','{}',:installation)
    """), {"op": op_id, "hash": "a" * 64, "installation": installation})
    assert db_session.execute(text("SELECT count(*) FROM public.operacion_idempotente WHERE op_id=:op"), {"op": op_id}).scalar_one() == 2
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    scenario.rollback()


def test_inheritance_como_hija_falla_sin_reparar(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("CREATE TABLE public.operacion_idempotente_padre (LIKE public.operacion_idempotente INCLUDING ALL)"))
    db_session.execute(text("ALTER TABLE public.operacion_idempotente INHERIT public.operacion_idempotente_padre"))
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_inherits
        WHERE inhrelid='public.operacion_idempotente'::regclass
    """)).scalar_one() == 1
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    scenario.rollback()


def test_rule_insert_do_instead_falla_y_sin_guard_suprime_receipt(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        CREATE RULE operacion_idempotente_suprime_insert AS
        ON INSERT TO public.operacion_idempotente DO INSTEAD NOTHING
    """))
    assert db_session.execute(text("SELECT count(*) FROM pg_rewrite WHERE ev_class='public.operacion_idempotente'::regclass")).scalar_one() == 1
    before = db_session.execute(text("SELECT count(*) FROM public.operacion_idempotente")).scalar_one()
    db_session.execute(text("""
        INSERT INTO public.operacion_idempotente
          (op_id,command_code,target_type,payload_hash,canonicalization_version,
           result_code,response_snapshot,id_instalacion)
        VALUES (:op,'C','T',:hash,1,'OK','{}',:installation)
    """), {"op": uuid4(), "hash": "a" * 64, "installation": _installation(db_session)})
    assert db_session.execute(text("SELECT count(*) FROM public.operacion_idempotente")).scalar_one() == before
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    scenario.rollback()


def test_rls_y_policy_fallan_sin_reparacion(db_session):
    scenario = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.operacion_idempotente FORCE ROW LEVEL SECURITY;
        CREATE POLICY operacion_idempotente_deny_all ON public.operacion_idempotente
        USING (false) WITH CHECK (false)
    """))
    flags = db_session.execute(text("""
        SELECT relrowsecurity,relforcerowsecurity FROM pg_class
        WHERE oid='public.operacion_idempotente'::regclass
    """)).one()
    assert tuple(flags) == (True, True)
    assert db_session.execute(text("SELECT count(*) FROM pg_policy WHERE polrelid='public.operacion_idempotente'::regclass")).scalar_one() == 1
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    assert db_session.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid='public.operacion_idempotente'::regclass")).scalar_one()
    scenario.rollback()


def test_columna_generated_y_timestamp_con_precision_fallan(db_session):
    generated = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente DROP COLUMN result_target_uid;
        ALTER TABLE public.operacion_idempotente ADD COLUMN result_target_uid uuid
        GENERATED ALWAYS AS (target_uid) STORED
    """))
    assert db_session.execute(text("""
        SELECT attgenerated FROM pg_attribute
        WHERE attrelid='public.operacion_idempotente'::regclass AND attname='result_target_uid'
    """)).scalar_one() == "s"
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    generated.rollback()

    precision = db_session.begin_nested()
    db_session.execute(text("""
        ALTER TABLE public.operacion_idempotente
        ALTER COLUMN created_at TYPE timestamp(0) without time zone
    """))
    assert db_session.execute(text("""
        SELECT atttypmod FROM pg_attribute
        WHERE attrelid='public.operacion_idempotente'::regclass AND attname='created_at'
    """)).scalar_one() == 0
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    precision.rollback()


@pytest.mark.parametrize(("function_name", "alteration", "column", "expected"), [
    ("fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)", "IMMUTABLE", "provolatile", "i"),
    ("trg_operacion_idempotente_inmutable()", "SECURITY DEFINER", "prosecdef", True),
    ("trg_operacion_idempotente_instalacion_sucursal()", "STRICT", "proisstrict", True),
])
def test_atributos_materiales_de_funcion_incompatibles_fallan(db_session, function_name, alteration, column, expected):
    scenario = db_session.begin_nested()
    db_session.execute(text(f"ALTER FUNCTION public.{function_name} {alteration}"))
    assert db_session.execute(text(f"SELECT {column} FROM pg_proc WHERE oid='public.{function_name}'::regprocedure")).scalar_one() == expected
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_body()))
    scenario.rollback()


def test_reejecucion_compatible_no_reemplaza_objetos_ni_filas(db_session):
    row = _insert(db_session)
    function_oid = db_session.execute(text("SELECT 'trg_operacion_idempotente_inmutable()'::regprocedure::oid")).scalar_one()
    context_function_oid = db_session.execute(text("SELECT 'trg_operacion_idempotente_instalacion_sucursal()'::regprocedure::oid")).scalar_one()
    triggers_before = {
        row.tgname: (row.oid, row.tgenabled, row.tgqual, row.attribute_count)
        for row in db_session.execute(text("SELECT tgname,oid,tgenabled,tgqual,cardinality(tgattr::smallint[]) attribute_count FROM pg_trigger WHERE tgrelid='operacion_idempotente'::regclass AND NOT tgisinternal"))
    }
    db_session.execute(text(_patch_body()))
    assert db_session.execute(text("SELECT 'trg_operacion_idempotente_inmutable()'::regprocedure::oid")).scalar_one() == function_oid
    assert db_session.execute(text("SELECT 'trg_operacion_idempotente_instalacion_sucursal()'::regprocedure::oid")).scalar_one() == context_function_oid
    assert {
        row.tgname: (row.oid, row.tgenabled, row.tgqual, row.attribute_count)
        for row in db_session.execute(text("SELECT tgname,oid,tgenabled,tgqual,cardinality(tgattr::smallint[]) attribute_count FROM pg_trigger WHERE tgrelid='operacion_idempotente'::regclass AND NOT tgisinternal"))
    } == triggers_before
    assert db_session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE id_operacion_idempotente=:id"), {"id": row["id_operacion_idempotente"]}).scalar_one() == 1


def test_reejecucion_independiente_de_search_path_y_homonimos(db_session):
    receipt = _insert(db_session)
    db_session.execute(text("CREATE SCHEMA otro_schema"))
    for table in ("usuario", "sucursal", "instalacion"):
        db_session.execute(text(f"CREATE TABLE otro_schema.{table} (id_{table} bigint PRIMARY KEY)"))
    function_oids = dict(db_session.execute(text("""
        SELECT proname,oid FROM pg_proc
        WHERE oid IN (
          'public.fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)'::regprocedure,
          'public.trg_operacion_idempotente_instalacion_sucursal()'::regprocedure,
          'public.trg_operacion_idempotente_inmutable()'::regprocedure
        )
    """)).all())
    trigger_oids = dict(db_session.execute(text("""
        SELECT tgname,oid FROM pg_trigger
        WHERE tgrelid='public.operacion_idempotente'::regclass AND NOT tgisinternal
    """)).all())
    constraint_oids = dict(db_session.execute(text("""
        SELECT conname,oid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
    """)).all())

    db_session.execute(text("SET LOCAL search_path = pg_catalog"))
    db_session.execute(text(_patch_body()))
    db_session.execute(text("SET LOCAL search_path = otro_schema, public, pg_catalog"))
    db_session.execute(text(_patch_body()))

    assert dict(db_session.execute(text("""
        SELECT proname,oid FROM pg_proc
        WHERE oid IN (
          'public.fn_assert_instalacion_pertenece_a_sucursal(bigint,bigint,text)'::regprocedure,
          'public.trg_operacion_idempotente_instalacion_sucursal()'::regprocedure,
          'public.trg_operacion_idempotente_inmutable()'::regprocedure
        )
    """)).all()) == function_oids
    assert dict(db_session.execute(text("""
        SELECT tgname,oid FROM pg_trigger
        WHERE tgrelid='public.operacion_idempotente'::regclass AND NOT tgisinternal
    """)).all()) == trigger_oids
    assert dict(db_session.execute(text("""
        SELECT conname,oid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass
    """)).all()) == constraint_oids
    assert db_session.execute(text("""
        SELECT count(*) FROM public.operacion_idempotente
        WHERE id_operacion_idempotente=:id
    """), {"id": receipt["id_operacion_idempotente"]}).scalar_one() == 1
    referenced = set(db_session.execute(text("""
        SELECT confrelid FROM pg_constraint
        WHERE conrelid='public.operacion_idempotente'::regclass AND contype='f'
    """)).scalars())
    assert referenced == {
        db_session.execute(text("SELECT 'public.usuario'::regclass::oid")).scalar_one(),
        db_session.execute(text("SELECT 'public.sucursal'::regclass::oid")).scalar_one(),
        db_session.execute(text("SELECT 'public.instalacion'::regclass::oid")).scalar_one(),
    }
    db_session.execute(text("SET LOCAL search_path = public, pg_catalog"))


@pytest.mark.parametrize("mutation", [
    "ALTER TABLE operacion_idempotente DROP COLUMN target_key",
    "ALTER TABLE operacion_idempotente ALTER COLUMN target_key TYPE text",
    "ALTER TABLE operacion_idempotente ALTER COLUMN target_uid SET NOT NULL",
    "ALTER TABLE operacion_idempotente ALTER COLUMN canonicalization_version SET DEFAULT 1",
    "ALTER TABLE operacion_idempotente DROP CONSTRAINT uq_operacion_idempotente_op_id; ALTER TABLE operacion_idempotente ADD UNIQUE(op_id,command_code)",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_inmutable()",
    "DROP TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal ON operacion_idempotente; CREATE TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal BEFORE UPDATE ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_instalacion_sucursal()",
    "DROP TRIGGER trg_bt_operacion_idempotente_inmutable ON operacion_idempotente",
    "DROP TRIGGER trg_bt_operacion_idempotente_inmutable ON operacion_idempotente; CREATE TRIGGER trg_bt_operacion_idempotente_inmutable BEFORE INSERT ON operacion_idempotente FOR EACH STATEMENT EXECUTE FUNCTION trg_operacion_idempotente_inmutable()",
    "ALTER TABLE operacion_idempotente DISABLE TRIGGER trg_bud_operacion_idempotente_inmutable",
    "ALTER TABLE operacion_idempotente ENABLE REPLICA TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal",
    "ALTER TABLE operacion_idempotente ENABLE TRIGGER trg_bt_operacion_idempotente_inmutable",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE OR DELETE ON operacion_idempotente FOR EACH ROW WHEN (false) EXECUTE FUNCTION trg_operacion_idempotente_inmutable(); ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER trg_bud_operacion_idempotente_inmutable",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE OF result_code ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_inmutable(); ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER trg_bud_operacion_idempotente_inmutable",
    "DROP TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal ON operacion_idempotente; CREATE TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal BEFORE INSERT ON operacion_idempotente FOR EACH ROW WHEN (false) EXECUTE FUNCTION trg_operacion_idempotente_instalacion_sucursal(); ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal",
    "DROP TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal ON operacion_idempotente; DROP FUNCTION trg_operacion_idempotente_instalacion_sucursal(); CREATE FUNCTION trg_operacion_idempotente_instalacion_sucursal() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$; CREATE TRIGGER trg_bi_operacion_idempotente_instalacion_sucursal BEFORE INSERT ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_instalacion_sucursal()",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; DROP TRIGGER trg_bt_operacion_idempotente_inmutable ON operacion_idempotente; DROP FUNCTION trg_operacion_idempotente_inmutable(); CREATE FUNCTION trg_operacion_idempotente_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END $$; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE OR DELETE ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_inmutable(); CREATE TRIGGER trg_bt_operacion_idempotente_inmutable BEFORE TRUNCATE ON operacion_idempotente FOR EACH STATEMENT EXECUTE FUNCTION trg_operacion_idempotente_inmutable()",
])
def test_fail_fast_estructura_incompatible_y_rollback(db_session, mutation):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(mutation))
        db_session.execute(text(_patch_body()))
    assert set(db_session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='operacion_idempotente'")).scalars()) == EXPECTED_COLUMNS


def test_reset_simetrico_ordenado_y_no_sync():
    sh = (BACKEND / "scripts/reset_db.sh").read_text(encoding="utf-8")
    bat = (BACKEND / "scripts/reset_db.bat").read_text(encoding="utf-8")
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count('-f "%PATCH_OPERACION_IDEMPOTENTE_FILE%"') == 2
    assert sh.index("patch_sesion_usuario_runtime_20260807.sql") < sh.index(PATCH_NAME) < sh.index("seed_minimo.sql")
    assert bat.index("PATCH_SESION_USUARIO_RUNTIME_FILE") < bat.index("PATCH_OPERACION_IDEMPOTENTE_FILE") < bat.index("%SEED_FILE%")
    assert all("ON_ERROR_STOP=1" in line for line in bat.splitlines() if '-f "%PATCH_OPERACION_IDEMPOTENTE_FILE%"' in line)
    policy_files = list((BACKEND / "app").rglob("*.py"))
    assert not any("operacion_idempotente" in path.read_text(encoding="utf-8") for path in policy_files)


def test_insert_no_modifica_outbox_inbox(db_session):
    before = tuple(db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in ("outbox_event", "inbox_event"))
    _insert(db_session)
    after = tuple(db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in ("outbox_event", "inbox_event"))
    assert after == before
