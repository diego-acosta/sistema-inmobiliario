"""
Tests de integración para POST /api/v1/financiero/mora/generar.
"""
from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import _crear_contrato, _crear_relacion_generadora


URL = "/api/v1/financiero/mora/generar"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"


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
    estado: str = "PROYECTADA",
    saldo_pendiente: float | None = None,
) -> dict:
    rg = _crear_rg(client, codigo=codigo)
    response = client.post(
        URL_OBLIGACIONES,
        headers=HEADERS,
        json={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_vencimiento": "2026-05-01",
            "composiciones": [
                {
                    "codigo_concepto_financiero": "CANON_LOCATIVO",
                    "importe_componente": importe,
                }
            ],
        },
    )
    assert response.status_code == 201
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
    return obligacion


def _generar_mora(client, *, fecha_proceso: str = "2026-05-01") -> dict:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"fecha_proceso": fecha_proceso},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _moras_de_base(db_session, id_obligacion_base: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.importe_total,
                o.saldo_pendiente,
                o.fecha_vencimiento,
                cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
                ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
                ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.observaciones LIKE :marker
              AND o.deleted_at IS NULL
              AND c.deleted_at IS NULL
            ORDER BY o.id_obligacion_financiera
            """
        ),
        {"marker": f"MORA_AUTO id_obligacion_base={id_obligacion_base} %"},
    ).mappings().all()
    return [dict(row) for row in rows]


def test_generar_mora_para_obligacion_vencida_con_saldo(client, db_session) -> None:
    ob = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-OK-001",
        importe=1000.00,
    )

    data = _generar_mora(client)

    assert data == {
        "fecha_proceso": "2026-05-01",
        "procesadas": 1,
        "generadas": 1,
    }
    moras = _moras_de_base(db_session, ob["id_obligacion_financiera"])
    assert len(moras) == 1
    assert float(moras[0]["importe_total"]) == 1.00
    assert float(moras[0]["saldo_pendiente"]) == 1.00
    assert moras[0]["codigo_concepto_financiero"] == "INTERES_MORA"


def test_no_genera_mora_si_saldo_es_cero(client, db_session) -> None:
    _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-SALDO-000",
        saldo_pendiente=0.00,
    )

    data = _generar_mora(client)

    assert data["procesadas"] == 0
    assert data["generadas"] == 0


def test_no_genera_mora_si_no_esta_vencida(client, db_session) -> None:
    _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-NOVENC-001",
        fecha_vencimiento="2026-05-01",
    )

    data = _generar_mora(client, fecha_proceso="2026-05-01")

    assert data["procesadas"] == 0
    assert data["generadas"] == 0


def test_no_genera_mora_para_estados_excluidos(client, db_session) -> None:
    for estado in ("CANCELADA", "ANULADA", "REEMPLAZADA"):
        _crear_obligacion(
            client,
            db_session=db_session,
            codigo=f"MORA-EST-{estado}",
            estado=estado,
        )

    data = _generar_mora(client)

    assert data["procesadas"] == 0
    assert data["generadas"] == 0


def test_no_duplica_mora_para_misma_obligacion_y_fecha(client, db_session) -> None:
    ob = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-DUP-001",
        importe=2000.00,
    )

    primera = _generar_mora(client)
    segunda = _generar_mora(client)

    assert primera["generadas"] == 1
    assert segunda["procesadas"] == 1
    assert segunda["generadas"] == 0
    assert len(_moras_de_base(db_session, ob["id_obligacion_financiera"])) == 1


def test_genera_multiples_moras_en_lote(client, db_session) -> None:
    ob1 = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-LOTE-001",
        importe=1000.00,
    )
    ob2 = _crear_obligacion(
        client,
        db_session=db_session,
        codigo="MORA-LOTE-002",
        importe=2500.00,
    )

    data = _generar_mora(client)

    assert data["procesadas"] == 2
    assert data["generadas"] == 2
    assert len(_moras_de_base(db_session, ob1["id_obligacion_financiera"])) == 1
    assert len(_moras_de_base(db_session, ob2["id_obligacion_financiera"])) == 1
