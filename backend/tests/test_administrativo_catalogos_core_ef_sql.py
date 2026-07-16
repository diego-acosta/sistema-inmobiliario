import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _catalogo(db_session, codigo: str, op_id: str | None = None) -> int:
    return db_session.execute(text("""
        INSERT INTO catalogo_maestro (
            codigo_catalogo_maestro, nombre_catalogo_maestro,
            id_instalacion_origen, op_id_alta
        ) VALUES (:codigo, :nombre, 1, CAST(:op_id AS uuid))
        RETURNING id_catalogo_maestro
    """), {"codigo": codigo, "nombre": codigo, "op_id": op_id}).scalar_one()


def _item(
    db_session, catalogo_id: int, codigo: str, op_id: str | None = None
) -> int:
    return db_session.execute(text("""
        INSERT INTO item_catalogo (
            id_catalogo_maestro, codigo_item_catalogo, nombre_item_catalogo,
            id_instalacion_origen, op_id_alta
        ) VALUES (:catalogo_id, :codigo, :nombre, 1, CAST(:op_id AS uuid))
        RETURNING id_item_catalogo
    """), {
        "catalogo_id": catalogo_id,
        "codigo": codigo,
        "nombre": codigo,
        "op_id": op_id,
    }).scalar_one()


def test_catalogos_core_ef_estructura_y_triggers(db_session):
    columns = db_session.execute(text("""
        SELECT table_name, column_name, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name IN ('catalogo_maestro', 'item_catalogo')
    """)).mappings().all()
    present = {(row["table_name"], row["column_name"]) for row in columns}
    core = {
        "uid_global", "version_registro", "created_at", "updated_at", "deleted_at",
        "id_instalacion_origen", "id_instalacion_ultima_modificacion",
        "op_id_alta", "op_id_ultima_modificacion",
    }
    assert {(table, column) for table in ("catalogo_maestro", "item_catalogo") for column in core} <= present
    assert {(row["table_name"], row["column_name"]): row["is_nullable"] for row in columns}[("catalogo_maestro", "uid_global")] == "NO"
    names = set(db_session.execute(text("""SELECT conname FROM pg_constraint WHERE conrelid IN ('catalogo_maestro'::regclass, 'item_catalogo'::regclass)""")).scalars())
    assert {"uq_catalogo_maestro_codigo", "uq_catalogo_maestro_uid_global", "uq_item_catalogo", "uq_item_catalogo_uid_global", "fk_item_catalogo_catalogo", "chk_catalogo_maestro_version_registro", "chk_item_catalogo_version_registro"} <= names
    triggers = set(db_session.execute(text("""SELECT tgname FROM pg_trigger WHERE tgrelid IN ('catalogo_maestro'::regclass, 'item_catalogo'::regclass) AND NOT tgisinternal""")).scalars())
    assert {"trg_bi_catalogo_maestro_core_ef", "trg_bu_catalogo_maestro_core_ef", "trg_bi_item_catalogo_core_ef", "trg_bu_item_catalogo_core_ef"} <= triggers


def test_catalogo_maestro_core_ef_defaults_unicidad_y_actualizacion(db_session):
    op_id = str(uuid.uuid4())
    catalogo_id = _catalogo(db_session, "ADM363_SQL_A", op_id)
    row = db_session.execute(text("SELECT uid_global, version_registro, created_at, updated_at, id_instalacion_origen, op_id_alta, op_id_ultima_modificacion FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": catalogo_id}).mappings().one()
    assert row["uid_global"] is not None and row["version_registro"] == 1 and row["created_at"] is not None and row["updated_at"] is not None and str(row["op_id_ultima_modificacion"]) == op_id and row["id_instalacion_origen"] == 1
    db_session.commit()
    with pytest.raises(IntegrityError):
        _catalogo(db_session, "ADM363_SQL_B", op_id)
    db_session.rollback()
    original_uid = row["uid_global"]
    db_session.execute(text("UPDATE catalogo_maestro SET uid_global = gen_random_uuid(), created_at = CURRENT_TIMESTAMP + INTERVAL '1 day', id_instalacion_origen = NULL, op_id_alta = gen_random_uuid(), nombre_catalogo_maestro = 'actualizado', deleted_at = CURRENT_TIMESTAMP WHERE id_catalogo_maestro = :id"), {"id": catalogo_id})
    updated = db_session.execute(text("SELECT uid_global, version_registro, created_at, updated_at, deleted_at, id_instalacion_origen, op_id_alta FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": catalogo_id}).mappings().one()
    assert updated["uid_global"] == original_uid and updated["created_at"] == row["created_at"] and updated["id_instalacion_origen"] == 1 and updated["op_id_alta"] == row["op_id_alta"] and updated["version_registro"] == 2 and updated["updated_at"] >= row["updated_at"] and updated["deleted_at"] is not None


def test_item_catalogo_core_ef_insert_defaults_and_idempotency_index(db_session):
    catalogo_id = _catalogo(db_session, "ADM363_ITEM_ALTA_CATALOGO")
    op_id = str(uuid.uuid4())
    item_id = _item(db_session, catalogo_id, "ADM363_ITEM_ALTA", op_id)
    row = db_session.execute(text("""
        SELECT uid_global, version_registro, created_at, updated_at,
               id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta, op_id_ultima_modificacion
        FROM item_catalogo WHERE id_item_catalogo = :id
    """), {"id": item_id}).mappings().one()
    assert row["uid_global"] is not None
    assert row["version_registro"] == 1
    assert row["created_at"] is not None and row["updated_at"] is not None
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == op_id
    assert str(row["op_id_ultima_modificacion"]) == op_id
    db_session.commit()

    other_catalogo_id = _catalogo(db_session, "ADM363_ITEM_ALTA_OTRO_CATALOGO")
    with pytest.raises(IntegrityError):
        _item(db_session, other_catalogo_id, "ADM363_ITEM_ALTA_OTRO", op_id)
    db_session.rollback()


def test_item_catalogo_core_ef_update_preserves_original_metadata(db_session):
    catalogo_id = _catalogo(db_session, "ADM363_ITEM_UPDATE_CATALOGO")
    op_id_alta = str(uuid.uuid4())
    item_id = _item(db_session, catalogo_id, "ADM363_ITEM_UPDATE", op_id_alta)
    original = db_session.execute(text("""
        SELECT uid_global, version_registro, created_at, updated_at,
               id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta, op_id_ultima_modificacion
        FROM item_catalogo WHERE id_item_catalogo = :id
    """), {"id": item_id}).mappings().one()
    db_session.commit()

    op_id_modificacion = str(uuid.uuid4())
    db_session.execute(text("""
        UPDATE item_catalogo
        SET uid_global = gen_random_uuid(),
            created_at = CURRENT_TIMESTAMP + INTERVAL '1 day',
            id_instalacion_origen = NULL,
            op_id_alta = gen_random_uuid(),
            nombre_item_catalogo = 'Nombre actualizado',
            id_instalacion_ultima_modificacion = 1,
            op_id_ultima_modificacion = CAST(:op_id_modificacion AS uuid)
        WHERE id_item_catalogo = :id
    """), {"id": item_id, "op_id_modificacion": op_id_modificacion})
    updated = db_session.execute(text("""
        SELECT uid_global, version_registro, created_at, updated_at,
               id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta, op_id_ultima_modificacion, nombre_item_catalogo
        FROM item_catalogo WHERE id_item_catalogo = :id
    """), {"id": item_id}).mappings().one()
    assert updated["uid_global"] == original["uid_global"]
    assert updated["created_at"] == original["created_at"]
    assert updated["id_instalacion_origen"] == original["id_instalacion_origen"]
    assert updated["op_id_alta"] == original["op_id_alta"]
    assert updated["nombre_item_catalogo"] == "Nombre actualizado"
    assert updated["version_registro"] == original["version_registro"] + 1
    assert updated["updated_at"] >= original["updated_at"]
    assert updated["id_instalacion_ultima_modificacion"] == 1
    assert str(updated["op_id_ultima_modificacion"]) == op_id_modificacion


def test_item_catalogo_soft_delete_is_versioned_and_hidden_from_readonly(client, db_session):
    catalogo_id = _catalogo(db_session, "ADM363_ITEM_BAJA_CATALOGO")
    item_id = _item(db_session, catalogo_id, "ADM363_ITEM_BAJA")
    original = db_session.execute(text("SELECT version_registro, updated_at FROM item_catalogo WHERE id_item_catalogo = :id"), {"id": item_id}).mappings().one()
    db_session.execute(text("UPDATE item_catalogo SET deleted_at = CURRENT_TIMESTAMP WHERE id_item_catalogo = :id"), {"id": item_id})
    db_session.commit()
    deleted = db_session.execute(text("SELECT deleted_at, version_registro, updated_at FROM item_catalogo WHERE id_item_catalogo = :id"), {"id": item_id}).mappings().one()
    assert deleted["deleted_at"] is not None
    assert deleted["version_registro"] == original["version_registro"] + 1
    assert deleted["updated_at"] >= original["updated_at"]
    assert db_session.execute(text("SELECT COUNT(*) FROM item_catalogo WHERE id_item_catalogo = :id"), {"id": item_id}).scalar_one() == 1

    response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items")
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_item_catalogo_rejects_deleted_at_before_created_at(db_session):
    catalogo_id = _catalogo(db_session, "ADM363_ITEM_FECHA_CATALOGO")
    item_id = _item(db_session, catalogo_id, "ADM363_ITEM_FECHA")
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(text("""
            UPDATE item_catalogo
            SET deleted_at = created_at - INTERVAL '1 second'
            WHERE id_item_catalogo = :id
        """), {"id": item_id})
    db_session.rollback()


def test_item_catalogo_version_constraint_rejects_invalid_value_when_trigger_is_disabled(db_session):
    catalogo_id = _catalogo(db_session, "ADM363_ITEM_VERSION_CATALOGO")
    item_id = _item(db_session, catalogo_id, "ADM363_ITEM_VERSION")
    db_session.commit()
    try:
        db_session.execute(text("ALTER TABLE item_catalogo DISABLE TRIGGER trg_bu_item_catalogo_core_ef"))
        with pytest.raises(IntegrityError):
            db_session.execute(text("UPDATE item_catalogo SET version_registro = 0 WHERE id_item_catalogo = :id"), {"id": item_id})
        db_session.rollback()
    finally:
        db_session.execute(text("ALTER TABLE item_catalogo ENABLE TRIGGER trg_bu_item_catalogo_core_ef"))
        db_session.commit()


def test_items_permiten_codigo_entre_catalogos_no_dentro_del_mismo(db_session):
    first = _catalogo(db_session, "ADM363_ITEMS_A")
    second = _catalogo(db_session, "ADM363_ITEMS_B")
    for catalogo_id in (first, second):
        _item(db_session, catalogo_id, "REPETIDO")
    with pytest.raises(IntegrityError):
        _item(db_session, first, "REPETIDO")
    db_session.rollback()
