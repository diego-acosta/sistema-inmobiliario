from dataclasses import FrozenInstanceError, fields
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.common import local_installation as subject


class SessionSpy:
    commits = 0
    rollbacks = 0
    writes = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def row(**changes):
    return {
        "id_instalacion": 42,
        "uid_global": str(uuid4()),
        "codigo_instalacion": "Inst-Local-001",
        "nombre_instalacion": "Local controlado",
        "deleted_at": None,
        "estado_instalacion": "ACTIVA",
        "fecha_baja": None,
        "id_sucursal": 999,
        "es_principal": False,
        "permite_sincronizacion": False,
        **changes,
    }


def install_repo(monkeypatch, result=None, error=None):
    calls = []

    class FakeRepository:
        def __init__(self, session):
            calls.append(("init", session))

        def get_by_codigo_exact(self, code):
            calls.append(("get", code))
            if error:
                raise error
            return result

    monkeypatch.setattr(subject, "InstalacionRepository", FakeRepository)
    return calls


def resolve(monkeypatch, result):
    session = SessionSpy()
    calls = install_repo(monkeypatch, result)
    identity = subject.resolve_local_installation(
        session, SimpleNamespace(local_installation_code="Inst-Local-001")
    )
    return identity, session, calls


def test_resuelve_dto_minimo_inmutable_sin_efectos(monkeypatch):
    identity, session, calls = resolve(monkeypatch, row())
    assert identity.id_instalacion == 42
    assert identity.codigo_instalacion == "Inst-Local-001"
    assert {field.name for field in fields(identity)} == {
        "id_instalacion", "uid_global", "codigo_instalacion", "nombre_instalacion"
    }
    with pytest.raises((FrozenInstanceError, AttributeError)):
        identity.id_instalacion = 1
    assert calls == [("init", session), ("get", "Inst-Local-001")]
    assert (session.commits, session.rollbacks, session.writes) == (0, 0, 0)


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (None, subject.LocalInstallationNotFound),
        (row(deleted_at=datetime.now()), subject.LocalInstallationNotEligible),
        (row(estado_instalacion="INACTIVA"), subject.LocalInstallationNotEligible),
        (row(estado_instalacion="DADA_DE_BAJA"), subject.LocalInstallationNotEligible),
        (row(fecha_baja=datetime.now()), subject.LocalInstallationStateConflict),
        (row(estado_instalacion="NUEVA"), subject.LocalInstallationStateConflict),
    ],
)
def test_clasifica_inexistencia_y_estados(monkeypatch, result, error):
    install_repo(monkeypatch, result)
    with pytest.raises(error):
        subject.resolve_local_installation(
            SessionSpy(), SimpleNamespace(local_installation_code="Inst-Local-001")
        )


def test_es_principal_sucursal_y_sincronizacion_son_irrelevantes(monkeypatch):
    identity, _, _ = resolve(
        monkeypatch,
        row(id_sucursal=None, es_principal=False, permite_sincronizacion=False),
    )
    assert identity.id_instalacion == 42


def test_error_sql_es_sanitizado_y_conserva_causa(monkeypatch):
    cause = RuntimeError(
        "SELECT password FROM secret postgresql://user:password@db/name"
    )
    install_repo(monkeypatch, error=cause)
    with pytest.raises(subject.LocalInstallationTechnicalError) as exc_info:
        subject.resolve_local_installation(
            SessionSpy(), SimpleNamespace(local_installation_code="Inst-Local-001")
        )
    assert exc_info.value.__cause__ is cause
    assert "SELECT" not in str(exc_info.value)
    assert "password" not in str(exc_info.value)


def test_consumidor_controlado_reutiliza_id_sin_reconsultar(monkeypatch):
    identity, _, calls = resolve(monkeypatch, row())
    command = {
        "id_instalacion_origen": identity.id_instalacion,
        "id_instalacion_ultima_modificacion": identity.id_instalacion,
    }
    assert command == {
        "id_instalacion_origen": 42,
        "id_instalacion_ultima_modificacion": 42,
    }
    assert len([call for call in calls if call[0] == "get"]) == 1
