from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.common.local_installation import (
    LocalInstallationNotEligible,
    LocalInstallationNotFound,
    LocalInstallationStateConflict,
    resolve_local_installation,
)


def create_installation(db_session, code: str, **changes) -> dict:
    values = {
        "uid_global": str(uuid4()),
        "id_sucursal": 1,
        "codigo": code,
        "nombre": f"Instalación {code}",
        "estado": "ACTIVA",
        "es_principal": False,
        "permite": False,
        "fecha_baja": None,
        "deleted_at": None,
    } | changes
    return dict(
        db_session.execute(
            text("""
                INSERT INTO instalacion (
                    uid_global, id_sucursal, codigo_instalacion, nombre_instalacion,
                    estado_instalacion, es_principal, permite_sincronizacion,
                    fecha_baja, deleted_at
                ) VALUES (
                    CAST(:uid_global AS uuid), :id_sucursal, :codigo, :nombre,
                    :estado, :es_principal, :permite, :fecha_baja, :deleted_at
                )
                RETURNING id_instalacion, uid_global, codigo_instalacion
            """),
            values,
        ).mappings().one()
    )


def settings(code):
    return SimpleNamespace(local_installation_code=code)


def test_resuelve_baseline_por_codigo_sin_asumir_id(db_session):
    expected = db_session.execute(
        text("SELECT id_instalacion FROM instalacion WHERE codigo_instalacion = :code"),
        {"code": "INST-TEST-001"},
    ).scalar_one()
    assert resolve_local_installation(
        db_session, settings("INST-TEST-001")
    ).id_instalacion == expected


def test_codigos_distintos_case_exacto_y_principal_irrelevante(db_session):
    first = create_installation(db_session, "Inst-Case-A", es_principal=False)
    second = create_installation(db_session, "Inst-Case-B", es_principal=True)
    assert resolve_local_installation(
        db_session, settings("Inst-Case-A")
    ).id_instalacion == first["id_instalacion"]
    assert resolve_local_installation(
        db_session, settings("Inst-Case-B")
    ).id_instalacion == second["id_instalacion"]
    with pytest.raises(LocalInstallationNotFound):
        resolve_local_installation(db_session, settings("inst-case-a"))


def test_resuelve_codigo_exclusivamente_numerico_sin_fallback(db_session):
    numeric = create_installation(db_session, "123")

    identity = resolve_local_installation(db_session, settings("123"))

    assert identity.id_instalacion == numeric["id_instalacion"]
    assert identity.codigo_instalacion == "123"


@pytest.mark.parametrize(
    ("suffix", "changes_factory", "error"),
    [
        ("INACTIVA", lambda: {"estado": "INACTIVA"}, LocalInstallationNotEligible),
        (
            "BAJA",
            lambda: {"estado": "DADA_DE_BAJA"},
            LocalInstallationNotEligible,
        ),
        (
            "FECHA",
            lambda: {"fecha_baja": datetime.now()},
            LocalInstallationStateConflict,
        ),
        (
            "DELETED",
            lambda: {"deleted_at": datetime.now() + timedelta(seconds=5)},
            LocalInstallationNotEligible,
        ),
        (
            "UNKNOWN",
            lambda: {"estado": "ESTADO_DESCONOCIDO"},
            LocalInstallationStateConflict,
        ),
    ],
)
def test_estados_no_elegibles_y_conflictos(
    db_session, suffix, changes_factory, error
):
    code = f"INST-LOCAL-{suffix}"
    changes = changes_factory()
    create_installation(db_session, code, **changes)
    with pytest.raises(error):
        resolve_local_installation(db_session, settings(code))


def test_lectura_no_produce_efectos_laterales(db_session):
    created = create_installation(db_session, "INST-LOCAL-NO-WRITE")
    before = dict(
        db_session.execute(
            text("""
                SELECT version_registro, updated_at, id_instalacion_origen,
                       id_instalacion_ultima_modificacion, op_id_alta,
                       op_id_ultima_modificacion
                FROM instalacion WHERE id_instalacion = :id
            """),
            {"id": created["id_instalacion"]},
        ).mappings().one()
    )
    outbox_before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar()

    resolve_local_installation(db_session, settings("INST-LOCAL-NO-WRITE"))

    after = dict(
        db_session.execute(
            text("""
                SELECT version_registro, updated_at, id_instalacion_origen,
                       id_instalacion_ultima_modificacion, op_id_alta,
                       op_id_ultima_modificacion
                FROM instalacion WHERE id_instalacion = :id
            """),
            {"id": created["id_instalacion"]},
        ).mappings().one()
    )
    assert after == before
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar() == outbox_before


def test_unicidad_estructural_del_codigo(db_session):
    constraints = db_session.execute(
        text("""
            SELECT count(*) FROM pg_constraint
            WHERE conrelid = 'public.instalacion'::regclass
              AND conname = 'uq_instalacion_codigo' AND contype = 'u'
        """)
    ).scalar_one()
    assert constraints == 1
