"""
Tests de integracion para POST /api/v1/financiero/mora/generar.
Mora V1 simple: marca obligaciones vencidas y calcula mora dinamica en lectura.
"""
from datetime import date

from sqlalchemy import text

from app.domain.financiero.parametros_mora import TASA_DIARIA_MORA_DEFAULT
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import _crear_contrato, _crear_relacion_generadora


URL = "/api/v1/financiero/mora/generar"
URL_DEUDA = "/api/v1/financiero/deuda"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"
TASA_DIARIA_MORA = float(TASA_DIARIA_MORA_DEFAULT)


def _crear_rg(client, *, codigo: str) -> dict:
    contrato = _crear_contrato(client, codigo=codigo)
    return _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])


def _crear_obligacion(
    client,
    *,
    db_session,
    codigo: str,
    importe: float = 1000.00,
    fecha_vencimiento: str = "2026-04-01",
    estado: str = "EMITIDA",
    saldo_pendiente: float | None = None,
) -> dict:
    rg = _crear_rg(client, codigo=codigo)
    response = client.post(
        URL_OBLIGACIONES,
        headers=HEADERS,
        json={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_vencimiento": "2026-12-31",
            "composiciones": [
                {
                    "codigo_concepto_financiero": "CANON_LOCATIVO",
                    "importe_componente": importe,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    obligacion = response.json()["data"]
    saldo = importe if saldo_pendiente is None else saldo_pendiente

    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET fecha_emision = :fecha_vencimiento,
                fecha_vencimiento = :fecha_vencimiento,
                saldo_pendiente = :saldo_pendiente,
                estado_obligacion = :estado
            WHERE id_obligacion_financiera = :id
            """
        ),
        {
            "id": obligacion["id_obligacion_financiera"],
            "fecha_vencimiento": fecha_vencimiento,
            "saldo_pendiente": saldo,
            "estado": estado,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE composicion_obligacion
            SET saldo_componente = :saldo_pendiente
            WHERE id_obligacion_financiera = :id
            """
        ),
        {
            "id": obligacion["id_obligacion_financiera"],
            "saldo_pendiente": saldo,
        },
    )
    obligacion["id_relacion_generadora"] = rg["id_relacion_generadora"]
    return obligacion


def _generar_mora(client, *, fecha_proceso: str = "2026-05-01") -> dict:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"fecha_proceso": fecha_proceso},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _estado_obligacion(db_session, id_obligacion: int) -> str:
    return db_session.execute(
        text(
            """
            SELECT estado_obligacion
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        ),
        {"id": id_obligacion},
    ).scalar_one()


def _count_moras_persistidas(db_session) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE cf.codigo_concepto_financiero = 'INTERES_MORA'
              AND o.deleted_at IS NULL
              AND c.deleted_at IS NULL
            """
        )
    ).scalar_one()


def test_emitida_vencida_con_saldo_pasa_a_vencida(client, db_session) -> None:
    ob = _crear_obligacion(client, db_session=db_session, codigo="MORA-VENC-001")

    data = _generar_mora(client)

    assert data["procesadas"] == 1
    assert data["marcadas"] == 1
    assert data["generadas"] == 0
    assert data["tasa_diaria"] == str(TASA_DIARIA_MORA_DEFAULT)
    assert _estado_obligacion(db_session, ob["id_obligacion_financiera"]) == "VENCIDA"
    assert _count_moras_persistidas(db_session) == 0


def test_emitida_no_vencida_no_cambia(client, db_session) -> None:
    ob = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-NOVENC-001",
        fecha_vencimiento="2026-05-01",
    )

    data = _generar_mora(client, fecha_proceso="2026-05-01")

    assert data["procesadas"] == 0
    assert data["marcadas"] == 0
    assert _estado_obligacion(db_session, ob["id_obligacion_financiera"]) == "EMITIDA"


def test_estados_no_emitida_no_cambian(client, db_session) -> None:
    ids = []
    for estado in ("CANCELADA", "ANULADA", "REEMPLAZADA"):
        ob = _crear_obligacion(
            client,
            db_session=db_session,
            codigo=f"MORA-EST-{estado}",
            estado=estado,
        )
        ids.append((ob["id_obligacion_financiera"], estado))

    data = _generar_mora(client)

    assert data["procesadas"] == 0
    assert data["marcadas"] == 0
    for id_obligacion, estado in ids:
        assert _estado_obligacion(db_session, id_obligacion) == estado


def test_mora_calculada_en_deuda_consolidada(client, db_session) -> None:
    ob = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-CALC-001",
        importe=1000.00,
        fecha_vencimiento="2026-04-01",
    )

    _generar_mora(client, fecha_proceso="2026-05-01")
    response = client.get(
        URL_DEUDA,
        headers=HEADERS,
        params={"id_relacion_generadora": ob["id_relacion_generadora"]},
    )

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    dias_atraso = max((date.today() - date(2026, 4, 6)).days, 0)
    assert item["dias_atraso"] == dias_atraso
    assert item["mora_calculada"] == round(1000.00 * TASA_DIARIA_MORA * dias_atraso, 2)
    assert item["saldo_pendiente"] == 1000.00


def test_mora_es_idempotente_y_no_crea_obligacion_financiera(client, db_session) -> None:
    _crear_obligacion(client, db_session=db_session, codigo="MORA-IDEM-001")
    before = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()

    primera = _generar_mora(client)
    segunda = _generar_mora(client)
    after = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()

    assert primera["marcadas"] == 1
    assert segunda["procesadas"] == 0
    assert segunda["marcadas"] == 0
    assert after == before
    assert _count_moras_persistidas(db_session) == 0
