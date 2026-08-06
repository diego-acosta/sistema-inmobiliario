from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.application.administrativo.commands.bootstrap_credential import (
    ActiveCredentialAlreadyExists,
    ActiveCredentialNotFound,
    BootstrapCredentialCommand,
    CredentialIdempotencyConflict,
    CredentialStateConflict,
    UserNotEligible,
    UserNotFound,
)
from app.application.common.security.password_hashing import (
    PASSWORD_HASH_ALGORITHM,
    hash_password,
    verify_password,
)
from app.config.database import engine
from app.infrastructure.persistence.repositories.credencial_usuario_repository import (
    CredencialUsuarioRepository,
)

PREFIX = "T454-"
Factory = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_rows():
    _clean()
    yield
    _clean()


def _clean():
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM credencial_usuario WHERE id_usuario IN (SELECT id_usuario FROM usuario WHERE codigo_usuario LIKE :prefix)"
            ),
            {"prefix": f"{PREFIX}%"},
        )
        connection.execute(
            text("DELETE FROM usuario WHERE codigo_usuario LIKE :prefix"),
            {"prefix": f"{PREFIX}%"},
        )


def _installation():
    with engine.connect() as connection:
        return dict(
            connection.execute(
                text(
                    "SELECT id_instalacion, codigo_instalacion FROM instalacion WHERE estado_instalacion='ACTIVA' AND deleted_at IS NULL ORDER BY id_instalacion LIMIT 1"
                )
            )
            .mappings()
            .one()
        )


def _user(suffix="USER", **changes):
    values = {
        "codigo": f"{PREFIX}{suffix}-{uuid4().hex[:8]}",
        "login": f"login-{uuid4().hex[:8]}",
        "estado": "ACTIVO",
        "fecha_baja": None,
        "deleted_at": None,
    } | changes
    with engine.begin() as connection:
        return dict(
            connection.execute(
                text("""
            INSERT INTO usuario(codigo_usuario,login,estado_usuario,fecha_baja,deleted_at)
            VALUES (:codigo,:login,:estado,:fecha_baja,:deleted_at)
            RETURNING id_usuario,codigo_usuario,login
        """),
                values,
            )
            .mappings()
            .one()
        )


def _command():
    return BootstrapCredentialCommand(
        Factory,
        SimpleNamespace(local_installation_code=_installation()["codigo_instalacion"]),
    )


def _run(operation, user, secret, op_id=None):
    command = _command()
    return command.execute(
        operation, command.preflight(user["codigo_usuario"]), secret, op_id or uuid4()
    )


def _credential(
    user, *, state="ACTIVA", principal=True, deleted_at=None, secret=None, op_id=None
):
    installation = _installation()
    secret = secret or f"Secret-{uuid4()}"
    op_id = op_id or uuid4()
    with engine.begin() as connection:
        row = connection.execute(
            text("""
          INSERT INTO credencial_usuario(id_usuario,tipo_credencial,hash_credencial,algoritmo_hash,
            estado_credencial,es_credencial_principal,fecha_activacion,fecha_revocacion,
            ultimo_cambio_credencial,id_instalacion_origen,id_instalacion_ultima_modificacion,
            op_id_alta,op_id_ultima_modificacion,deleted_at)
          VALUES (:user,'PASSWORD',:hash,:algorithm,CAST(:state AS varchar),:principal,CURRENT_TIMESTAMP,
            CASE WHEN CAST(:state AS varchar)='REVOCADA' THEN CURRENT_TIMESTAMP END,CURRENT_TIMESTAMP,:installation,
            :installation,:op,:op,:deleted_at) RETURNING id_credencial_usuario
        """),
            {
                "user": user["id_usuario"],
                "hash": hash_password(secret),
                "algorithm": PASSWORD_HASH_ALGORITHM,
                "state": state,
                "principal": principal,
                "installation": installation["id_instalacion"],
                "op": str(op_id),
                "deleted_at": deleted_at,
            },
        ).scalar_one()
    return row, secret, op_id


def _rows(user):
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT * FROM credencial_usuario WHERE id_usuario=:user ORDER BY id_credencial_usuario"
                ),
                {"user": user["id_usuario"]},
            ).mappings()
        ]


def _outbox_count():
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM outbox_event")
        ).scalar_one()


def test_repository_uses_postgresql_transaction_timestamp(db_session):
    repo = CredencialUsuarioRepository(db_session)
    assert repo.get_transaction_timestamp() == repo.get_transaction_timestamp()


def test_init_persists_complete_contract_without_outbox():
    user, secret, op_id = _user(), f"Secret-{uuid4()}", uuid4()
    outbox = _outbox_count()
    result = _run("init", user, secret, op_id)
    row = _rows(user)[0]
    installation = _installation()
    assert result.result == "COMPLETADO" and verify_password(
        secret, row["hash_credencial"]
    )
    assert (
        row["tipo_credencial"],
        row["estado_credencial"],
        row["es_credencial_principal"],
    ) == ("PASSWORD", "ACTIVA", True)
    assert row["algoritmo_hash"] == PASSWORD_HASH_ALGORITHM
    assert (
        row["requiere_reset"] is False
        and row["obliga_rotacion"] is False
        and row["intentos_fallidos_acumulados"] == 0
    )
    assert (
        row["fecha_alta"] == row["fecha_activacion"] == row["ultimo_cambio_credencial"]
    )
    assert (
        row["id_instalacion_origen"]
        == row["id_instalacion_ultima_modificacion"]
        == installation["id_instalacion"]
    )
    assert row["op_id_alta"] == row["op_id_ultima_modificacion"] == op_id
    assert row["version_registro"] == 1 and row["deleted_at"] is None
    assert _outbox_count() == outbox


def test_init_again_with_new_op_does_not_modify_existing():
    user = _user()
    _run("init", user, f"Secret-{uuid4()}")
    before = _rows(user)
    with pytest.raises(ActiveCredentialAlreadyExists):
        _run("init", user, f"Other-{uuid4()}")
    assert _rows(user) == before


def test_reset_revokes_history_and_creates_one_active_atomically():
    user = _user()
    old_id, old_secret, old_op = _credential(user)
    before = _rows(user)[0]
    new_secret, new_op, outbox = f"New-{uuid4()}", uuid4(), _outbox_count()
    result = _run("reset", user, new_secret, new_op)
    old, new = _rows(user)
    assert result.result == "COMPLETADO" and old["id_credencial_usuario"] == old_id
    assert (
        old["estado_credencial"] == "REVOCADA"
        and old["es_credencial_principal"] is False
    )
    assert old["hash_credencial"] == before["hash_credencial"] and verify_password(
        old_secret, old["hash_credencial"]
    )
    assert (
        old["algoritmo_hash"] == before["algoritmo_hash"]
        and old["deleted_at"] == before["deleted_at"]
        and old["op_id_alta"] == old_op
    )
    assert (
        old["motivo_revocacion"] == "RESET_ADMINISTRATIVO_LOCAL"
        and old["op_id_ultima_modificacion"] == new_op
    )
    assert old["version_registro"] == before["version_registro"] + 1
    assert (
        new["estado_credencial"] == "ACTIVA"
        and new["es_credencial_principal"] is True
        and new["version_registro"] == 1
    )
    assert verify_password(new_secret, new["hash_credencial"])
    assert (
        old["fecha_revocacion"]
        == new["fecha_alta"]
        == new["fecha_activacion"]
        == new["ultimo_cambio_credencial"]
    )
    assert (
        sum(
            row["estado_credencial"] == "ACTIVA" and row["deleted_at"] is None
            for row in (old, new)
        )
        == 1
    )
    assert _outbox_count() == outbox


def test_reset_without_active_preserves_history():
    user = _user()
    _credential(user, state="REVOCADA", principal=False)
    before = _rows(user)
    with pytest.raises(ActiveCredentialNotFound):
        _run("reset", user, f"Secret-{uuid4()}")
    assert _rows(user) == before


@pytest.mark.parametrize(
    "state,deleted", [("ACTIVA", None), ("REVOCADA", None), ("ACTIVA", datetime.now() + timedelta(minutes=5))]
)
def test_replay_active_revoked_or_deleted_is_read_only(state, deleted):
    user, secret, op_id = _user(), f"Secret-{uuid4()}", uuid4()
    _credential(
        user,
        state=state,
        principal=state == "ACTIVA",
        deleted_at=deleted,
        secret=secret,
        op_id=op_id,
    )
    before = _rows(user)
    assert _run("init", user, secret, op_id).result == "REPLAY_IDEMPOTENTE"
    assert _rows(user) == before


def test_replay_wrong_secret_and_other_user_are_conflicts(monkeypatch):
    owner, other, secret, op_id = (
        _user("OWNER"),
        _user("OTHER"),
        f"Secret-{uuid4()}",
        uuid4(),
    )
    _credential(owner, secret=secret, op_id=op_id)
    before = _rows(owner)
    with pytest.raises(CredentialIdempotencyConflict):
        _run("init", owner, f"Wrong-{uuid4()}", op_id)
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.verify_password",
        lambda *_: pytest.fail("foreign hash verified"),
    )
    with pytest.raises(CredentialIdempotencyConflict):
        _run("init", other, f"Other-{uuid4()}", op_id)
    assert _rows(owner) == before and _rows(other) == []


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"estado": "INACTIVO"}, UserNotEligible),
        ({"deleted_at": datetime.now()}, UserNotEligible),
        ({"fecha_baja": datetime.now()}, UserNotEligible),
    ],
)
def test_ineligible_users_do_not_write(changes, error):
    user = _user(**changes)
    with pytest.raises(error):
        _command().preflight(user["codigo_usuario"])
    assert _rows(user) == []


def test_missing_user_does_not_write():
    with pytest.raises(UserNotFound):
        _command().preflight(f"{PREFIX}MISSING")


def test_active_nonprincipal_is_state_conflict():
    user = _user()
    _credential(user, principal=False)
    before = _rows(user)
    with pytest.raises(CredentialStateConflict):
        _run("reset", user, f"Secret-{uuid4()}")
    assert _rows(user) == before


def test_reset_rolls_back_real_transaction_when_insert_fails(monkeypatch):
    user = _user()
    _credential(user)
    before = _rows(user)
    monkeypatch.setattr(
        CredencialUsuarioRepository,
        "insert_active_password",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("controlled")),
    )
    with pytest.raises(RuntimeError, match="controlled"):
        _run("reset", user, f"Secret-{uuid4()}")
    assert _rows(user) == before


def _parallel(calls):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(call) for call in calls]
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=15))
            except Exception as exc:
                results.append(exc)
        return results


def test_concurrent_init_init_serializes_to_one_active():
    user, barrier = _user(), __import__("threading").Barrier(2)

    def call():
        command, preview = _command(), None
        preview = command.preflight(user["codigo_usuario"])
        barrier.wait(timeout=5)
        return command.execute("init", preview, f"Secret-{uuid4()}", uuid4())

    results = _parallel([call, call])
    assert sum(not isinstance(x, Exception) for x in results) == 1
    assert any(isinstance(x, ActiveCredentialAlreadyExists) for x in results)
    assert len([r for r in _rows(user) if r["estado_credencial"] == "ACTIVA"]) == 1


def test_concurrent_replay_same_op_converges():
    user, secret, op_id, barrier = (
        _user(),
        f"Secret-{uuid4()}",
        uuid4(),
        __import__("threading").Barrier(2),
    )

    def call():
        command = _command()
        preview = command.preflight(user["codigo_usuario"])
        barrier.wait(timeout=5)
        return command.execute("init", preview, secret, op_id)

    results = _parallel([call, call])
    assert all(not isinstance(x, Exception) for x in results)
    assert {x.result for x in results} == {"COMPLETADO", "REPLAY_IDEMPOTENTE"}
    assert len(_rows(user)) == 1


def test_concurrent_same_op_between_users_maps_idempotency():
    users, op_id, barrier = (
        [_user("A"), _user("B")],
        uuid4(),
        __import__("threading").Barrier(2),
    )

    def call(user):
        command = _command()
        preview = command.preflight(user["codigo_usuario"])
        barrier.wait(timeout=5)
        return command.execute("init", preview, f"Secret-{uuid4()}", op_id)

    results = _parallel([lambda: call(users[0]), lambda: call(users[1])])
    assert sum(not isinstance(x, Exception) for x in results) == 1
    assert any(isinstance(x, CredentialIdempotencyConflict) for x in results)


def test_concurrent_reset_reset_are_legitimate_serial_rotations():
    user, barrier = _user(), __import__("threading").Barrier(2)
    _credential(user)

    def call():
        command = _command()
        preview = command.preflight(user["codigo_usuario"])
        barrier.wait(timeout=5)
        return command.execute("reset", preview, f"Secret-{uuid4()}", uuid4())

    results = _parallel([call, call])
    assert all(not isinstance(x, Exception) for x in results)
    rows = _rows(user)
    assert len(rows) == 3 and sum(r["estado_credencial"] == "ACTIVA" for r in rows) == 1
