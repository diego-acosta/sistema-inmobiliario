from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.api.authentication import get_authenticated_principal
from app.api.schemas.administrativo import UsuarioSucursalCreateRequest
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationService,
)
from app.application.common.idempotency import canonical_payload_hash
from app.infrastructure.persistence.repositories.technical_context_repository import (
    TechnicalContextRepository,
)
from sqlalchemy import text
from tests.test_administrativo_usuarios import (
    _central_headers,
    _central_request,
    _principal,
)

LEGACY_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def headers(op_id: str | None = None) -> dict[str, str]:
    return {"X-Op-Id": op_id or str(uuid4())}


def legacy_headers(op_id: str | None = None) -> dict[str, str]:
    return {**LEGACY_HEADERS, "X-Op-Id": op_id or str(uuid4())}


@pytest.fixture(autouse=True)
def usuario_sucursal_core_ef(db_session, client, monkeypatch):
    db_session.execute(text(open("backend/database/patch_usuario_sucursal_core_ef_20260702.sql").read()))
    db_session.commit()
    client.app.dependency_overrides[get_authenticated_principal] = lambda: _principal()
    monkeypatch.setattr(
        AdministrativeAuthorizationService,
        "authorize",
        lambda *args, **kwargs: AdministrativeAuthorizationDecision.GRANTED,
    )


def user_payload(suffix: str) -> dict:
    return {
        "codigo_usuario": f"USR-ALC-{suffix}",
        "login": f"usr.alc.{suffix}",
        "email": f"usr.alc.{suffix}@example.com",
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": "Usuario alcance operativo",
    }


def suc_payload(suffix: str) -> dict:
    return {
        "codigo_sucursal": f"SUC-ALC-{suffix}",
        "nombre_sucursal": f"Sucursal alcance {suffix}",
        "descripcion_sucursal": "Sucursal alcance operativo",
        "estado_sucursal": "ACTIVA",
        "es_casa_central": False,
        "permite_operacion": True,
        "observaciones": "Sucursal test #262",
    }


def crear_usuario(client, suffix: str = "001") -> dict:
    r = _central_request(
        client,
        "POST",
        "/api/v1/administrativo/usuarios",
        json=user_payload(suffix),
        headers=_central_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


def crear_sucursal(client, suffix: str = "001") -> dict:
    r = client.post(
        "/api/v1/operativo/sucursales",
        json=suc_payload(suffix),
        headers=legacy_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


def alcance_payload(id_sucursal: int, **overrides) -> dict:
    data = {
        "id_sucursal": id_sucursal,
        "tipo_habilitacion_sucursal": "OPERATIVA_BASICA",
        "es_sucursal_predeterminada": False,
        "puede_operar": True,
        "puede_consultar": True,
        "puede_administrar": False,
        "fecha_desde": "2026-07-02T00:00:00+00:00",
        "fecha_hasta": None,
        "observaciones": "Alcance básico #262",
    }
    data.update(overrides)
    return data


def test_consultar_alcance_sin_sucursales_devuelve_lista_vacia(client):
    usuario = crear_usuario(client, "SIN-SUC")
    r = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/alcance-operativo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["sucursales_asignadas"] == []
    assert data["sucursal_predeterminada"] is None
    assert data["estado_vigencia"] == "SIN_ALCANCE"


def test_asignar_sucursal_central_incluye_ledger_y_provenance_null(client, db_session):
    usuario = crear_usuario(client, "OK")
    sucursal = crear_sucursal(client, "OK")
    op_id = str(uuid4())
    r = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(op_id),
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None
    assert data["id_instalacion_origen"] is None
    assert data["id_instalacion_ultima_modificacion"] is None
    assert data["op_id_alta"] == op_id
    assert data["op_id_ultima_modificacion"] == op_id
    row = db_session.execute(text("""
        SELECT uid_global, version_registro, created_at, updated_at, deleted_at,
               id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta::text AS op_id_alta, op_id_ultima_modificacion::text AS op_id_ultima_modificacion
        FROM usuario_sucursal WHERE id_usuario_sucursal = :id
    """), {"id": data["id_usuario_sucursal"]}).mappings().one()
    assert row["uid_global"] is not None
    assert row["version_registro"] == 1
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["deleted_at"] is None
    assert row["id_instalacion_origen"] is None
    assert row["id_instalacion_ultima_modificacion"] is None
    assert row["op_id_alta"] == op_id
    assert row["op_id_ultima_modificacion"] == op_id
    receipt = db_session.execute(
        text(
            """
            SELECT id_usuario, id_sucursal, id_instalacion, target_uid,
                   target_key, payload_hash
            FROM operacion_idempotente
            WHERE op_id = :op_id
            """
        ),
        {"op_id": op_id},
    ).one()
    expected_hash = canonical_payload_hash(
        {
            "actor": {"type": "HUMAN", "id_usuario": 1},
            "scope": {"mode": "GLOBAL", "id_sucursal": None},
            "payload": {
                "id_usuario": usuario["id_usuario"],
                "id_sucursal": sucursal["id_sucursal"],
                "tipo_habilitacion_sucursal": "OPERATIVA_BASICA",
                "es_sucursal_predeterminada": True,
                "puede_operar": True,
                "puede_consultar": True,
                "puede_administrar": False,
                "fecha_desde": "2026-07-02T00:00:00",
                "fecha_hasta": None,
                "observaciones": "Alcance básico #262",
            },
        }
    )
    assert receipt.id_usuario == 1
    assert receipt.id_sucursal is None
    assert receipt.id_instalacion is None
    assert receipt.target_uid is None
    assert receipt.target_key == (
        f"usuario:{usuario['id_usuario']}:sucursal:{sucursal['id_sucursal']}"
    )
    assert receipt.payload_hash == expected_hash


@pytest.mark.parametrize("field", ["fecha_desde", "fecha_hasta"])
def test_frontera_temporal_naive_devuelve_error_estandar(client, field):
    usuario = crear_usuario(client, f"NAIVE-{field}")
    sucursal = crear_sucursal(client, f"NAIVE-{field}")
    payload = alcance_payload(sucursal["id_sucursal"])
    payload[field] = "2026-09-04T18:00:00"

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": [field]},
    }
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    "raw_value",
    [
        1_788_549_600,
        1_788_549_600.5,
        "1788549600",
    ],
)
@pytest.mark.parametrize("field", ["fecha_desde", "fecha_hasta"])
def test_frontera_temporal_no_acepta_representaciones_epoch(
    client, raw_value, field
):
    payload = alcance_payload(1)
    payload[field] = raw_value

    response = client.post(
        "/api/v1/administrativo/usuarios/1/sucursales",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": [field]},
    }
    assert "detail" not in response.json()


def test_path_id_usuario_no_numerico_devuelve_error_estandar(client):
    response = client.post(
        "/api/v1/administrativo/usuarios/not-a-number/sucursales",
        json=alcance_payload(1),
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": ["id_usuario"]},
    }
    assert "detail" not in response.json()


@pytest.mark.parametrize("id_usuario", ["not-a-number", "-1"])
def test_path_y_body_invalidos_devuelven_un_error_estandar(client, id_usuario):
    response = client.post(
        f"/api/v1/administrativo/usuarios/{id_usuario}/sucursales",
        json=alcance_payload(1, fecha_desde=1_788_549_600),
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {
            "fields": (
                ["id_usuario", "fecha_desde"]
                if id_usuario == "not-a-number"
                else ["fecha_desde"]
            )
        },
    }
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-04T21:00:00Z", "2026-09-04T21:00:00"),
        ("2026-09-04T21:00:00+00:00", "2026-09-04T21:00:00"),
        ("2026-09-04T21:00:00+0000", "2026-09-04T21:00:00"),
        ("2026-09-04T18:00:00-03:00", "2026-09-04T21:00:00"),
        ("2026-09-04T18:00:00-0300", "2026-09-04T21:00:00"),
        ("2026-09-04T18:00:00+03:00", "2026-09-04T15:00:00"),
        ("2026-09-04T18:00:00+0300", "2026-09-04T15:00:00"),
        ("2026-09-04T18:00:00+14:00", "2026-09-04T04:00:00"),
        ("2026-09-04T18:00:00+1400", "2026-09-04T04:00:00"),
        ("2026-09-04T18:00:00-14:00", "2026-09-05T08:00:00"),
        ("2026-09-04T18:00:00-1400", "2026-09-05T08:00:00"),
    ],
)
def test_frontera_temporal_aware_se_canoniza_antes_del_repository(value, expected):
    request = UsuarioSucursalCreateRequest(id_sucursal=1, fecha_desde=value)

    dumped = request.model_dump()

    assert dumped["fecha_desde"] == datetime.fromisoformat(expected)
    assert dumped["fecha_desde"].tzinfo is None


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-04T18:00:00-00:00",
        "2026-09-04T18:00:00-0000",
        "2026-09-04T18:00:00+24:00",
        "2026-09-04T18:00:00-24:00",
        "2026-09-04T18:00:00+14:60",
        "2026-09-04T18:00:00-03:99",
        "2026-09-04T18:00:00+000",
        "2026-09-04T18:00:00+00000",
        "2026-09-04T18:00:00+14:01",
        "2026-09-04T18:00:00+1401",
        "2026-09-04T18:00:00-14:01",
        "2026-09-04T18:00:00-1401",
        "2026-09-04T18:00:00+15:00",
        "2026-09-04T18:00:00+1500",
        "2026-09-04T18:00:00-15:00",
        "2026-09-04T18:00:00-1500",
        "2026-09-04T18:00:00+23:59",
        "2026-09-04T18:00:00+2359",
        "2026-09-04T18:00:00-23:59",
        "2026-09-04T18:00:00-2359",
    ],
)
def test_offset_desconocido_o_invalido_devuelve_error_estandar(client, value):
    response = client.post(
        "/api/v1/administrativo/usuarios/1/sucursales",
        json=alcance_payload(1, fecha_desde=value),
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": ["fecha_desde"]},
    }
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fecha_desde", "0001-01-01T00:00:00+14:00"),
        ("fecha_hasta", "9999-12-31T23:59:59-14:00"),
    ],
)
def test_frontera_fuera_del_rango_utc_devuelve_error_estandar(client, field, value):
    payload = alcance_payload(1)
    payload[field] = value

    response = client.post(
        "/api/v1/administrativo/usuarios/1/sucursales",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": [field]},
    }
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0001-01-01T14:00:00+14:00", "0001-01-01T00:00:00"),
        ("9999-12-31T09:59:59-14:00", "9999-12-31T23:59:59"),
    ],
)
def test_frontera_extrema_representable_se_canoniza(value, expected):
    request = UsuarioSucursalCreateRequest(id_sucursal=1, fecha_desde=value)

    assert request.fecha_desde == datetime.fromisoformat(expected)


def test_instantes_equivalentes_generan_el_mismo_payload_canonico():
    argentina = UsuarioSucursalCreateRequest(
        id_sucursal=1,
        fecha_desde="2026-09-04T18:00:00-03:00",
    )
    utc = UsuarioSucursalCreateRequest(
        id_sucursal=1,
        fecha_desde="2026-09-04T21:00:00+00:00",
    )

    assert argentina.model_dump()["fecha_desde"] == utc.model_dump()["fecha_desde"]


def test_rango_permite_extremos_iguales_despues_de_normalizar():
    request = UsuarioSucursalCreateRequest(
        id_sucursal=1,
        fecha_desde="2026-09-04T18:00:00-03:00",
        fecha_hasta="2026-09-04T21:00:00+00:00",
    )

    assert request.fecha_hasta == request.fecha_desde


@pytest.mark.parametrize(
    ("fecha_desde", "fecha_hasta", "valid"),
    [
        (
            "2026-09-04T18:00:00-03:00",
            "2026-09-04T22:00:00+00:00",
            True,
        ),
        (
            "2026-09-04T23:30:00+02:00",
            "2026-09-04T18:15:00-03:00",
            False,
        ),
        (
            "2026-09-04T18:00:00-03:00",
            "2026-09-04T21:00:00+00:00",
            True,
        ),
    ],
)
def test_rango_se_compara_despues_de_normalizar(
    fecha_desde, fecha_hasta, valid
):
    values = {
        "id_sucursal": 1,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }

    if valid:
        request = UsuarioSucursalCreateRequest(**values)
        assert request.fecha_hasta >= request.fecha_desde
    else:
        with pytest.raises(ValueError, match="fecha_hasta no puede ser menor"):
            UsuarioSucursalCreateRequest(**values)


def test_rango_invalido_reporta_fecha_hasta(client):
    response = client.post(
        "/api/v1/administrativo/usuarios/1/sucursales",
        json=alcance_payload(
            1,
            fecha_desde="2026-09-04T22:00:00+00:00",
            fecha_hasta="2026-09-04T18:00:00+00:00",
        ),
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de asignación contiene datos inválidos.",
        "details": {"fields": ["fecha_hasta"]},
    }
    assert "detail" not in response.json()


def test_postgres_persiste_utc_naive_con_sesion_no_utc(client, db_session):
    usuario = crear_usuario(client, "TZ-PG")
    sucursal = crear_sucursal(client, "TZ-PG")
    db_session.execute(
        text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'")
    )

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(
            sucursal["id_sucursal"],
            fecha_desde="2026-09-04T18:00:00-03:00",
            fecha_hasta="2026-09-04T22:00:00+00:00",
        ),
        headers=headers(),
    )

    assert response.status_code == 201, response.text
    stored = db_session.execute(
        text(
            """
            SELECT fecha_desde, fecha_hasta
              FROM usuario_sucursal
             WHERE id_usuario_sucursal = :id
            """
        ),
        {"id": response.json()["data"]["id_usuario_sucursal"]},
    ).mappings().one()
    assert stored["fecha_desde"] == datetime.fromisoformat("2026-09-04T21:00:00")
    assert stored["fecha_hasta"] == datetime.fromisoformat("2026-09-04T22:00:00")
    assert stored["fecha_desde"].tzinfo is None
    assert stored["fecha_hasta"].tzinfo is None


def test_write_canonico_es_elegible_por_reader_utc_537(client, db_session):
    usuario = crear_usuario(client, "READER-537")
    now_utc = datetime.now(UTC)
    argentina = timezone(-timedelta(hours=3))
    db_session.execute(
        text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'")
    )

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(
            1,
            fecha_desde=(now_utc - timedelta(hours=1))
            .astimezone(argentina)
            .isoformat(),
            fecha_hasta=(now_utc + timedelta(hours=1)).isoformat(),
        ),
        headers=headers(),
    )

    assert response.status_code == 201, response.text
    projection = TechnicalContextRepository(db_session).resolve_operational_context(
        id_sucursal=1,
        id_instalacion=1,
        id_usuario=usuario["id_usuario"],
    )
    assert projection.principal_has_operational_scope is True


def test_replay_equivalente_por_offset_reutiliza_vinculo(client, db_session):
    usuario = crear_usuario(client, "IDEMP-TZ")
    sucursal = crear_sucursal(client, "IDEMP-TZ")
    op_id = str(uuid4())
    argentina = alcance_payload(
        sucursal["id_sucursal"],
        fecha_desde="2026-09-04T18:00:00-03:00",
    )
    utc = alcance_payload(
        sucursal["id_sucursal"],
        fecha_desde="2026-09-04T21:00:00+00:00",
    )

    first = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=argentina,
        headers=headers(op_id),
    )
    second = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=utc,
        headers=headers(op_id),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["id_usuario_sucursal"] == first.json()["data"][
        "id_usuario_sucursal"
    ]
    assert db_session.execute(
        text("SELECT COUNT(*) FROM usuario_sucursal WHERE op_id_alta = :op"),
        {"op": op_id},
    ).scalar_one() == 1


def test_replay_idempotente_compatible_no_duplica_vinculo_ni_outbox(client, db_session):
    usuario = crear_usuario(client, "IDEMP")
    sucursal = crear_sucursal(client, "IDEMP")
    op_id = str(uuid4())
    payload = alcance_payload(sucursal["id_sucursal"])
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=payload, headers=headers(op_id))
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=payload, headers=headers(op_id))
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["id_usuario_sucursal"] == first.json()["data"]["id_usuario_sucursal"]
    assert db_session.execute(text("SELECT COUNT(*) FROM usuario_sucursal WHERE op_id_alta = :op"), {"op": op_id}).scalar() == 1
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type = 'usuario_asociado_a_sucursal' AND aggregate_id = :id"), {"id": first.json()["data"]["id_usuario_sucursal"]}).scalar() == 0


def test_replay_idempotente_incompatible_devuelve_409(client):
    usuario = crear_usuario(client, "IDEMP-DIFF")
    sucursal = crear_sucursal(client, "IDEMP-DIFF")
    op_id = str(uuid4())
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers(op_id))
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"], puede_administrar=True), headers=headers(op_id))
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_duplicado_activo_distinto_op_id_devuelve_409(client):
    usuario = crear_usuario(client, "DUP")
    sucursal = crear_sucursal(client, "DUP")
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers())
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers())
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "DUPLICATE_ACTIVE_SCOPE"


def test_usuario_o_sucursal_inexistente_y_sucursal_baja(client, db_session):
    sucursal = crear_sucursal(client, "404")
    assert client.post("/api/v1/administrativo/usuarios/999999/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers()).status_code == 404
    usuario = crear_usuario(client, "404")
    assert client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(999999), headers=headers()).status_code == 404
    db_session.execute(text("UPDATE sucursal SET deleted_at = CURRENT_TIMESTAMP, fecha_baja = CURRENT_TIMESTAMP WHERE id_sucursal = :id"), {"id": sucursal["id_sucursal"]})
    db_session.commit()
    assert client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers()).status_code == 409


def test_falta_x_op_id_en_post_central_devuelve_400(client):
    usuario = crear_usuario(client, "HEAD")
    sucursal = crear_sucursal(client, "HEAD")
    r = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]))
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_get_lista_y_alcance_consolidado_incluyen_sucursales_y_flags(client):
    usuario = crear_usuario(client, "GET")
    sucursal = crear_sucursal(client, "GET")
    r = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"], puede_administrar=True), headers=headers())
    assert r.status_code == 201
    lista = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales")
    alcance = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/alcance-operativo")
    assert lista.status_code == 200
    assert len(lista.json()["data"]) == 1
    assert alcance.status_code == 200
    data = alcance.json()["data"]
    assert len(data["sucursales_asignadas"]) == 1
    assert data["puede_operar"] is True
    assert data["puede_consultar"] is True
    assert data["puede_administrar"] is True


def test_post_sin_fecha_desde_devuelve_422(client):
    usuario = crear_usuario(client, "SIN-FECHA")
    sucursal = crear_sucursal(client, "SIN-FECHA")
    payload = alcance_payload(sucursal["id_sucursal"])
    payload.pop("fecha_desde")

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert "detail" not in response.json()


def test_segunda_sucursal_predeterminada_devuelve_409_y_preserva_primera(client, db_session):
    usuario = crear_usuario(client, "PRED")
    suc1 = crear_sucursal(client, "PRED1")
    suc2 = crear_sucursal(client, "PRED2")
    first = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(suc1["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(),
    )
    second = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(suc2["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "DUPLICATE_ACTIVE_SCOPE"
    row = db_session.execute(text("""
        SELECT es_sucursal_predeterminada, version_registro
        FROM usuario_sucursal
        WHERE id_usuario_sucursal = :id
    """), {"id": first.json()["data"]["id_usuario_sucursal"]}).mappings().one()
    assert row["es_sucursal_predeterminada"] is True
    assert row["version_registro"] == 1


def test_contrato_central_headers_legacy_ignorados_y_openapi(client, db_session):
    usuario = crear_usuario(client, "HEAD-CENTRAL")
    sucursal = crear_sucursal(client, "HEAD-CENTRAL")
    op_id = str(uuid4())
    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"]),
        headers={
            "X-Op-Id": op_id,
            "X-Usuario-Id": "999",
            "X-Sucursal-Id": "999",
            "X-Instalacion-Id": "999",
        },
    )
    assert response.status_code == 201
    assert db_session.execute(
        text(
            """
            SELECT id_sucursal, id_instalacion
            FROM operacion_idempotente WHERE op_id=:op_id
            """
        ),
        {"op_id": op_id},
    ).one() == (None, None)

    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/administrativo/usuarios/{id_usuario}/sucursales"
    ]["post"]
    parameters = operation["parameters"]
    assert {p["name"] for p in parameters if p.get("required")} >= {"X-Op-Id"}
    assert not {
        "X-Usuario-Id",
        "X-Sucursal-Id",
        "X-Instalacion-Id",
        "If-Match-Version",
    } & {p["name"] for p in parameters}


def test_d1_denegado_bloquea_command(client):
    usuario = crear_usuario(client, "D1-DENY")
    sucursal = crear_sucursal(client, "D1-DENY")
    response = _central_request(
        client,
        "POST",
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"]),
        headers=headers(),
        granted=False,
    )
    assert response.status_code == 403


def test_sin_bearer_devuelve_401(client):
    client.app.dependency_overrides.pop(get_authenticated_principal, None)
    response = client.post(
        "/api/v1/administrativo/usuarios/1/sucursales",
        json=alcance_payload(1),
        headers=headers(),
    )
    assert response.status_code == 401


def test_actor_distinto_conflict_y_autoasignacion_permitida(client):
    target = crear_usuario(client, "ACTOR-TARGET")
    sucursal = crear_sucursal(client, "ACTOR-TARGET")
    op_id = uuid4()
    url = f"/api/v1/administrativo/usuarios/{target['id_usuario']}/sucursales"
    payload = alcance_payload(sucursal["id_sucursal"])
    first = _central_request(
        client,
        "POST",
        url,
        json=payload,
        headers=_central_headers(op_id),
        user=1,
    )
    cross_actor = _central_request(
        client,
        "POST",
        url,
        json=payload,
        headers=_central_headers(op_id),
        user=target["id_usuario"],
    )
    assert first.status_code == 201
    assert cross_actor.status_code == 409
    assert cross_actor.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"

    self_target = crear_usuario(client, "SELF")
    self_branch = crear_sucursal(client, "SELF")
    self_response = _central_request(
        client,
        "POST",
        f"/api/v1/administrativo/usuarios/{self_target['id_usuario']}/sucursales",
        json=alcance_payload(self_branch["id_sucursal"]),
        headers=_central_headers(),
        user=self_target["id_usuario"],
    )
    assert self_response.status_code == 201


@pytest.mark.parametrize(
    ("entity", "state", "expected_status"),
    [
        ("usuario", "INACTIVO", 409),
        ("usuario", "DESCONOCIDO", 500),
        ("sucursal", "INACTIVA", 409),
        ("sucursal", "DADA_DE_BAJA", 409),
        ("sucursal", "DESCONOCIDO", 500),
    ],
)
def test_estados_target_conocidos_y_desconocidos(
    client, db_session, entity, state, expected_status
):
    usuario = crear_usuario(client, f"STATE-U-{entity}-{state}")
    sucursal = crear_sucursal(client, f"STATE-S-{entity}-{state}")
    if entity == "usuario":
        db_session.execute(
            text("UPDATE usuario SET estado_usuario=:state WHERE id_usuario=:id"),
            {"state": state, "id": usuario["id_usuario"]},
        )
    else:
        db_session.execute(
            text("UPDATE sucursal SET estado_sucursal=:state WHERE id_sucursal=:id"),
            {"state": state, "id": sucursal["id_sucursal"]},
        )
    db_session.commit()
    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"]),
        headers=headers(),
    )
    assert response.status_code == expected_status


def test_sucursal_distinta_con_mismo_op_es_target_conflict(client):
    usuario = crear_usuario(client, "TARGET-CONFLICT")
    first_branch = crear_sucursal(client, "TARGET-CONFLICT-1")
    second_branch = crear_sucursal(client, "TARGET-CONFLICT-2")
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales"
    assert client.post(
        url,
        json=alcance_payload(first_branch["id_sucursal"]),
        headers=headers(op_id),
    ).status_code == 201
    conflict = client.post(
        url,
        json=alcance_payload(second_branch["id_sucursal"]),
        headers=headers(op_id),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENCY_TARGET_CONFLICT"


def test_autorizacion_revocada_bloquea_replay(client):
    usuario = crear_usuario(client, "REVOKED-REPLAY")
    sucursal = crear_sucursal(client, "REVOKED-REPLAY")
    op_id = uuid4()
    url = f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales"
    payload = alcance_payload(sucursal["id_sucursal"])
    assert _central_request(
        client,
        "POST",
        url,
        json=payload,
        headers=_central_headers(op_id),
    ).status_code == 201
    denied = _central_request(
        client,
        "POST",
        url,
        json=payload,
        headers=_central_headers(op_id),
        granted=False,
    )
    assert denied.status_code == 403


def test_fallo_completion_revierte_vinculo_y_permite_retry(client, db_session):
    usuario = crear_usuario(client, "ROLLBACK")
    sucursal = crear_sucursal(client, "ROLLBACK")
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales"
    payload = alcance_payload(sucursal["id_sucursal"])
    with patch(
        "app.application.administrativo.services."
        "usuario_sucursal_central_command_service.complete_operation",
        side_effect=RuntimeError("forced completion failure"),
    ):
        failed = client.post(url, json=payload, headers=headers(op_id))
    assert failed.status_code == 500
    assert db_session.execute(
        text(
            "SELECT count(*) FROM usuario_sucursal "
            "WHERE id_usuario=:usuario AND id_sucursal=:sucursal"
        ),
        {"usuario": usuario["id_usuario"], "sucursal": sucursal["id_sucursal"]},
    ).scalar_one() == 0
    assert db_session.execute(
        text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op_id"),
        {"op_id": op_id},
    ).scalar_one() == 0
    retry = client.post(url, json=payload, headers=headers(op_id))
    assert retry.status_code == 201


def test_vinculo_acotado_vigente_no_admite_segundo_alcance_d1(client):
    usuario = crear_usuario(client, "BOUNDED-CURRENT")
    sucursal = crear_sucursal(client, "BOUNDED-CURRENT")
    now = datetime.now(UTC)
    payload = alcance_payload(
        sucursal["id_sucursal"],
        fecha_desde=(now - timedelta(hours=1)).isoformat(),
        fecha_hasta=(now + timedelta(hours=1)).isoformat(),
    )
    url = f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales"
    assert client.post(url, json=payload, headers=headers()).status_code == 201
    duplicate = client.post(url, json=payload, headers=headers())
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "DUPLICATE_ACTIVE_SCOPE"


def _insert_bounded_link(
    db_session,
    *,
    id_usuario: int,
    id_sucursal: int,
    predeterminada: bool,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.execute(
        text(
            """
            INSERT INTO usuario_sucursal (
                id_usuario, id_sucursal, tipo_habilitacion_sucursal,
                es_sucursal_predeterminada, puede_operar, puede_consultar,
                puede_administrar, fecha_desde, fecha_hasta, estado_vinculo,
                observaciones, version_registro, id_instalacion_origen,
                id_instalacion_ultima_modificacion, op_id_alta,
                op_id_ultima_modificacion
            ) VALUES (
                :id_usuario, :id_sucursal, 'OPERATIVA_BASICA',
                :predeterminada, true, true, false,
                :fecha_desde, :fecha_hasta, 'ACTIVO', NULL, 1,
                NULL, NULL, :op_id, :op_id
            )
            """
        ),
        {
            "id_usuario": id_usuario,
            "id_sucursal": id_sucursal,
            "predeterminada": predeterminada,
            "fecha_desde": now - timedelta(hours=1),
            "fecha_hasta": now + timedelta(hours=1),
            "op_id": uuid4(),
        },
    )


def test_multiples_vinculos_bounded_efectivos_devuelven_409(client, db_session):
    usuario = crear_usuario(client, "MULTI-BOUNDED")
    sucursal = crear_sucursal(client, "MULTI-BOUNDED")
    for _ in range(2):
        _insert_bounded_link(
            db_session,
            id_usuario=usuario["id_usuario"],
            id_sucursal=sucursal["id_sucursal"],
            predeterminada=False,
        )
    db_session.commit()

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"]),
        headers=headers(),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "DUPLICATE_ACTIVE_SCOPE"


def test_multiples_predeterminadas_bounded_efectivas_devuelven_409(
    client,
    db_session,
):
    usuario = crear_usuario(client, "MULTI-DEFAULT")
    existing = [
        crear_sucursal(client, f"MULTI-DEFAULT-{index}") for index in range(3)
    ]
    for sucursal in existing[:2]:
        _insert_bounded_link(
            db_session,
            id_usuario=usuario["id_usuario"],
            id_sucursal=sucursal["id_sucursal"],
            predeterminada=True,
        )
    db_session.commit()

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(
            existing[2]["id_sucursal"],
            es_sucursal_predeterminada=True,
        ),
        headers=headers(),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "DUPLICATE_ACTIVE_SCOPE"


def test_existen_indices_unicos_usuario_sucursal_core_ef(db_session):
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_op_id_alta')")).scalar() == "ux_usuario_sucursal_op_id_alta"
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_uid_global')")).scalar() == "ux_usuario_sucursal_uid_global"
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_predeterminada_activa')")).scalar() == "ux_usuario_sucursal_predeterminada_activa"
