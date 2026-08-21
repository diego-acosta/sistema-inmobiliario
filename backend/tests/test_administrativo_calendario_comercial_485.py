from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
import threading
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
)
from app.api.core_ef_headers import AuthenticatedCoreEFHeaders, TechnicalCoreEFHeaders
from app.application.administrativo.services.bootstrap_calendario_comercial_service import (
    BootstrapCalendarioComercialService,
)
from app.application.administrativo.services.programar_calendario_comercial_service import (
    ProgramarCalendarioComercialError,
    ProgramarCalendarioComercialService,
)
from app.config.database import engine

ENDPOINT = "/api/v1/administrativo/configuracion/calendario-comercial"
INITIAL = {
    "dia_cierre_comercial": 20,
    "dia_vencimiento_predeterminado_cuotas": 10,
    "vigente_desde": "2026-09-01",
}
PROGRAM = {**INITIAL, "vigente_desde": "2026-10-01"}


def _principal():
    return AuthenticatedPrincipal(
        id_usuario=1,
        codigo_usuario="ADMIN",
        login="admin",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1,
        id_sucursal_operativa=None,
    )


def _headers(op_id=None, version=None):
    result = {
        "X-Op-Id": str(op_id or uuid4()),
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "X-Usuario-Id": "ignorado",
    }
    if version is not None:
        result["If-Match-Version"] = str(version)
    return result


def _request(client, method, payload, headers):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    ):
        return client.request(method, ENDPOINT, json=payload, headers=headers)


def _bootstrap(client):
    response = _request(client, "POST", INITIAL, _headers())
    assert response.status_code == 201


def test_programacion_append_only_replay_outbox_y_version(client, db_session):
    _bootstrap(client)
    op_id = uuid4()
    first = _request(client, "PUT", PROGRAM, _headers(op_id, 1))
    assert first.status_code == 200
    assert first.json()["data"]["version_agregada"] == 2
    assert first.json()["data"]["fecha_desde"] == "2026-10-01T00:00:00"
    rows = db_session.execute(
        text("""
        SELECT v.fecha_desde,v.fecha_hasta,v.version_registro
          FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro IN
          ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
         ORDER BY v.fecha_desde,p.codigo_parametro
    """)
    ).all()
    assert len(rows) == 4
    assert all(row.fecha_hasta == datetime(2026, 10, 1) for row in rows[:2])
    assert all(row.fecha_hasta is None for row in rows[2:])
    assert (
        db_session.execute(
            text("SELECT version_registro FROM configuracion_calendario_comercial")
        ).scalar_one()
        == 2
    )
    assert (
        db_session.execute(
            text("""
        SELECT count(*) FROM outbox_event
         WHERE event_type='calendario_comercial_programado'
    """)
        ).scalar_one()
        == 1
    )
    replay = _request(
        client, "PUT", PROGRAM, {**_headers(op_id, 1), "X-Sucursal-Id": "999999"}
    )
    assert replay.status_code == 200 and replay.json() == first.json()


@pytest.mark.parametrize(
    "missing", ["X-Op-Id", "X-Sucursal-Id", "X-Instalacion-Id", "If-Match-Version"]
)
def test_headers_faltantes_pasan_por_parser_comun(client, missing):
    headers = _headers(version=1)
    headers.pop(missing)
    response = _request(client, "PUT", PROGRAM, headers)
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"] == {
        "header": missing,
        "reason": "requerido faltante",
    }


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("X-Op-Id", "x"),
        ("X-Sucursal-Id", "0"),
        ("X-Instalacion-Id", "x"),
        ("If-Match-Version", "0"),
    ],
)
def test_headers_invalidos(client, name, value):
    response = _request(client, "PUT", PROGRAM, {**_headers(version=1), name: value})
    assert response.status_code == 400
    assert response.json()["details"] == {"header": name, "reason": "inválido"}


def test_openapi_headers_unicos_y_sin_usuario(client):
    operation = client.get("/openapi.json").json()["paths"][ENDPOINT]["put"]
    pairs = [(item["name"], item["in"]) for item in operation["parameters"]]
    expected = {
        (name, "header")
        for name in ("X-Op-Id", "X-Sucursal-Id", "X-Instalacion-Id", "If-Match-Version")
    }
    assert set(pairs) == expected and len(pairs) == len(set(pairs))
    assert all(item["required"] for item in operation["parameters"])
    assert ("X-Usuario-Id", "header") not in pairs


def test_cas_y_temporalidad_rechazan_sin_efectos(client, db_session):
    _bootstrap(client)
    mismatch = _request(client, "PUT", PROGRAM, _headers(version=2))
    assert mismatch.status_code == 412
    assert mismatch.json()["error_code"] == "CONCURRENCY_ERROR"
    equal = _request(
        client, "PUT", {**PROGRAM, "vigente_desde": "2026-09-01"}, _headers(version=1)
    )
    assert equal.status_code == 409
    assert (
        db_session.execute(
            text("SELECT version_registro FROM configuracion_calendario_comercial")
        ).scalar_one()
        == 1
    )
    assert (
        db_session.execute(
            text("""
        SELECT count(*) FROM outbox_event
         WHERE event_type='calendario_comercial_programado'
    """)
        ).scalar_one()
        == 0
    )


def test_rollback_integral_y_retry(client, db_session):
    _bootstrap(client)
    op_id = uuid4()
    with patch(
        "app.application.administrativo.services.programar_calendario_comercial_service.complete_operation",
        side_effect=RuntimeError("fallo"),
    ):
        failed = _request(client, "PUT", PROGRAM, _headers(op_id, 1))
    assert failed.status_code == 500
    assert (
        db_session.execute(
            text("SELECT version_registro FROM configuracion_calendario_comercial")
        ).scalar_one()
        == 1
    )
    assert (
        db_session.execute(
            text("""
        SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
          USING(id_parametro_sistema) WHERE p.codigo_parametro IN
          ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
    """)
        ).scalar_one()
        == 2
    )
    assert _request(client, "PUT", PROGRAM, _headers(op_id, 1)).status_code == 200


def _calendar_effects(db_session, op_id):
    return db_session.execute(
        text("""
            SELECT
              (SELECT version_registro
                 FROM configuracion_calendario_comercial
                WHERE deleted_at IS NULL),
              (SELECT count(*) FROM valor_parametro v
                 JOIN parametro_sistema p USING(id_parametro_sistema)
                WHERE p.codigo_parametro IN
                  ('DIA_CIERRE_COMERCIAL',
                   'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')),
              (SELECT count(*) FROM outbox_event
                WHERE event_type='calendario_comercial_programado'),
              (SELECT count(*) FROM operacion_idempotente WHERE op_id=:op)
        """),
        {"op": op_id},
    ).one()


def _assert_structural_rejection_without_effects(
    client, db_session, *, version, payload, before
):
    op_id = uuid4()
    response = _request(client, "PUT", payload, _headers(op_id, version))
    assert response.status_code == 409
    assert (
        response.json()["error_code"]
        == "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
    )
    after = _calendar_effects(db_session, op_id)
    assert after[:3] == before[:3]
    assert after[3] == 0


@pytest.mark.parametrize(
    ("invalid_payload", "expected_field"),
    [
        (
            {key: value for key, value in PROGRAM.items() if key != "vigente_desde"},
            "vigente_desde",
        ),
        ({**PROGRAM, "dia_cierre_comercial": 32}, "dia_cierre_comercial"),
        ({**PROGRAM, "dia_cierre_comercial": "20"}, "dia_cierre_comercial"),
        ({**PROGRAM, "vigente_desde": 20261001}, "vigente_desde"),
        ({**PROGRAM, "vigente_desde": "2026-10-01T00:00:00"}, "vigente_desde"),
        ({**PROGRAM, "vigente_desde": "2026/10/01"}, "vigente_desde"),
        ({**PROGRAM, "campo_extra_privado": "NO_EXPONER_485"}, "campo_extra_privado"),
    ],
)
def test_body_invalido_put_usa_error_response_sanitizado_sin_efectos(
    client, db_session, invalid_payload, expected_field
):
    _bootstrap(client)
    op_id = uuid4()
    before = _calendar_effects(db_session, op_id)

    response = _request(client, "PUT", invalid_payload, _headers(op_id, 1))

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"ok", "error_code", "error_message", "details"}
    assert body["ok"] is False
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["error_message"] == (
        "La solicitud de programación contiene datos inválidos."
    )
    assert expected_field in body["details"]["fields"]
    serialized = str(body)
    assert "detail" not in body
    assert "input" not in serialized
    assert "fecha_efectiva" not in serialized
    assert "bootstrap" not in serialized.casefold()
    assert "NO_EXPONER_485" not in serialized
    after = _calendar_effects(db_session, op_id)
    assert after == before


def test_rechaza_ultima_pareja_abierta_marcada_no_vigente(client, db_session):
    _bootstrap(client)
    db_session.execute(
        text("""
            UPDATE valor_parametro v SET es_valor_vigente=false
              FROM parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL',
                  'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
               AND v.fecha_hasta IS NULL
        """)
    )
    db_session.commit()
    op_id = uuid4()
    before = _calendar_effects(db_session, op_id)
    _assert_structural_rejection_without_effects(
        client, db_session, version=1, payload=PROGRAM, before=before
    )


def test_rechaza_pareja_historica_cerrada_marcada_vigente(client, db_session):
    _bootstrap(client)
    assert _request(client, "PUT", PROGRAM, _headers(version=1)).status_code == 200
    db_session.execute(
        text("""
            UPDATE valor_parametro v SET es_valor_vigente=false
              FROM parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL',
                  'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
               AND v.fecha_hasta IS NULL
        """)
    )
    db_session.execute(
        text("""
            UPDATE valor_parametro v SET es_valor_vigente=true
              FROM parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL',
                  'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
               AND v.fecha_hasta IS NOT NULL
        """)
    )
    db_session.commit()
    op_id = uuid4()
    before = _calendar_effects(db_session, op_id)
    _assert_structural_rejection_without_effects(
        client,
        db_session,
        version=2,
        payload={**PROGRAM, "vigente_desde": "2026-11-01"},
        before=before,
    )


def test_rechaza_flags_divergentes_dentro_de_pareja(client, db_session):
    _bootstrap(client)
    db_session.execute(
        text("""
            UPDATE valor_parametro v SET es_valor_vigente=false
              FROM parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro='DIA_CIERRE_COMERCIAL'
               AND v.fecha_hasta IS NULL
        """)
    )
    db_session.commit()
    op_id = uuid4()
    before = _calendar_effects(db_session, op_id)
    _assert_structural_rejection_without_effects(
        client, db_session, version=1, payload=PROGRAM, before=before
    )


def test_rechaza_dos_filas_abiertas_si_alguna_no_esta_vigente(client, db_session):
    _bootstrap(client)
    db_session.execute(
        text("""
            UPDATE valor_parametro v SET es_valor_vigente=false
              FROM parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro=
                   'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS'
               AND v.fecha_hasta IS NULL
        """)
    )
    db_session.commit()
    op_id = uuid4()
    before = _calendar_effects(db_session, op_id)
    _assert_structural_rejection_without_effects(
        client, db_session, version=1, payload=PROGRAM, before=before
    )


def _concurrent_program(*, same_op: bool):
    bootstrap_op = uuid4()
    op_ids = [uuid4(), uuid4()]
    if same_op:
        op_ids[1] = op_ids[0]
    with Session(engine) as session:
        BootstrapCalendarioComercialService(session).execute(
            dia_cierre_comercial=20,
            dia_vencimiento_predeterminado_cuotas=10,
            vigente_desde=date(2026, 9, 1),
            headers=TechnicalCoreEFHeaders(bootstrap_op, 1, 1),
            id_usuario=1,
        )
        session.commit()
    barrier = threading.Barrier(2)
    outcomes = []

    def run(index):
        with Session(engine) as session:
            barrier.wait()
            try:
                result = ProgramarCalendarioComercialService(session).execute(
                    dia_cierre_comercial=21,
                    dia_vencimiento_predeterminado_cuotas=11,
                    vigente_desde=date(2026, 10, 1),
                    headers=AuthenticatedCoreEFHeaders(op_ids[index], 1, 1, 1),
                    id_usuario=1,
                )
                session.commit()
                outcomes.append(("OK", result))
            except ProgramarCalendarioComercialError as exc:
                session.rollback()
                outcomes.append((exc.code, None))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, index) for index in range(2)]
            for future in futures:
                future.result(10)
        with Session(engine) as session:
            state = session.execute(
                text("""
                SELECT (SELECT version_registro FROM configuracion_calendario_comercial),
                       (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
                         USING(id_parametro_sistema) WHERE p.codigo_parametro IN
                         ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')),
                       (SELECT count(*) FROM operacion_idempotente WHERE op_id=ANY(:ops)),
                       (SELECT count(*) FROM outbox_event
                         WHERE event_type='calendario_comercial_programado')
            """),
                {"ops": list(set(op_ids))},
            ).one()
        return outcomes, state
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM outbox_event WHERE aggregate_type='calendario_comercial'"
                )
            )
            connection.execute(
                text("""
                DELETE FROM valor_parametro v USING parametro_sistema p
                 WHERE v.id_parametro_sistema=p.id_parametro_sistema
                   AND p.codigo_parametro IN
                   ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
            """)
            )
            connection.execute(text("DELETE FROM configuracion_calendario_comercial"))
            for trigger in (
                "trg_bud_operacion_idempotente_inmutable",
                "trg_bt_operacion_idempotente_inmutable",
            ):
                connection.execute(
                    text(f"ALTER TABLE operacion_idempotente DISABLE TRIGGER {trigger}")
                )
            try:
                connection.execute(
                    text("DELETE FROM operacion_idempotente WHERE op_id=ANY(:ops)"),
                    {"ops": [bootstrap_op, *set(op_ids)]},
                )
            finally:
                for trigger in (
                    "trg_bud_operacion_idempotente_inmutable",
                    "trg_bt_operacion_idempotente_inmutable",
                ):
                    connection.execute(
                        text(
                            f"ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER {trigger}"
                        )
                    )


def test_concurrencia_postgresql_cas_serializa_sin_deadlock():
    outcomes, state = _concurrent_program(same_op=False)
    assert sorted(item[0] for item in outcomes) == ["CONCURRENCY_ERROR", "OK"]
    assert state == (2, 4, 1, 1)


def test_concurrencia_postgresql_mismo_op_replay_durable():
    outcomes, state = _concurrent_program(same_op=True)
    assert [item[0] for item in outcomes] == ["OK", "OK"]
    assert outcomes[0][1] == outcomes[1][1]
    assert state == (2, 4, 1, 1)
