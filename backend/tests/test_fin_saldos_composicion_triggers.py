from pathlib import Path

import pytest
from sqlalchemy import text

from tests.test_fin_imputaciones_create import _crear_obligacion, _crear_rg, _imputar


PATCH_SQL = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "patch_composicion_refresca_saldo_obligacion_20260504.sql"
)


def _install_patch(db_session) -> None:
    db_session.connection().exec_driver_sql(PATCH_SQL.read_text(encoding="utf-8"))


def _concepto_id(db_session, codigo: str) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = :codigo
              AND deleted_at IS NULL
            """
        ),
        {"codigo": codigo},
    ).scalar_one()


def _saldos_obligacion(db_session, id_obligacion_financiera: int) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT importe_total, saldo_pendiente, importe_cancelado_acumulado
                FROM obligacion_financiera
                WHERE id_obligacion_financiera = :id
                """
            ),
            {"id": id_obligacion_financiera},
        )
        .mappings()
        .one()
    )


def _insertar_composicion(
    db_session,
    *,
    id_obligacion_financiera: int,
    codigo_concepto: str,
    importe: float,
    orden: int = 2,
) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO composicion_obligacion (
                id_obligacion_financiera, id_concepto_financiero,
                orden_composicion, importe_componente, saldo_componente
            )
            VALUES (
                :id_obligacion_financiera, :id_concepto_financiero,
                :orden_composicion, :importe_componente, :importe_componente
            )
            RETURNING id_composicion_obligacion
            """
        ),
        {
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_concepto_financiero": _concepto_id(db_session, codigo_concepto),
            "orden_composicion": orden,
            "importe_componente": importe,
        },
    ).scalar_one()


def _crear_obligacion_base(client, db_session, *, codigo: str = "SAL-COMP-001") -> dict:
    rg = _crear_rg(client, codigo=codigo)
    return _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[
            {
                "codigo_concepto_financiero": "CANON_LOCATIVO",
                "importe_componente": 1000.00,
            }
        ],
    )


def _insertar_aplicacion_directa(
    db_session,
    *,
    id_obligacion_financiera: int,
    id_composicion_obligacion: int,
    importe: float,
) -> None:
    id_movimiento = db_session.execute(
        text(
            """
            INSERT INTO movimiento_financiero (
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento
            )
            VALUES (CURRENT_TIMESTAMP, 'PAGO', :importe, 'CREDITO', 'APLICADO')
            RETURNING id_movimiento_financiero
            """
        ),
        {"importe": importe},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO aplicacion_financiera (
                id_movimiento_financiero, id_obligacion_financiera,
                id_composicion_obligacion, fecha_aplicacion,
                tipo_aplicacion, orden_aplicacion, importe_aplicado,
                origen_automatico_o_manual
            )
            VALUES (
                :id_movimiento_financiero, :id_obligacion_financiera,
                :id_composicion_obligacion, CURRENT_DATE,
                'PAGO', 1, :importe, 'MANUAL'
            )
            """
        ),
        {
            "id_movimiento_financiero": id_movimiento,
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_composicion_obligacion": id_composicion_obligacion,
            "importe": importe,
        },
    )


def test_insertar_composicion_aumenta_importe_total_y_saldo_pendiente(
    client, db_session
) -> None:
    _install_patch(db_session)
    ob = _crear_obligacion_base(client, db_session)

    _insertar_composicion(
        db_session,
        id_obligacion_financiera=ob["id_obligacion_financiera"],
        codigo_concepto="EXPENSA_TRASLADADA",
        importe=250.00,
    )

    saldos = _saldos_obligacion(db_session, ob["id_obligacion_financiera"])
    assert float(saldos["importe_total"]) == pytest.approx(1250.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(1250.00)


def test_actualizar_importe_componente_actualiza_obligacion(client, db_session) -> None:
    _install_patch(db_session)
    ob = _crear_obligacion_base(client, db_session, codigo="SAL-COMP-UPD-001")
    id_comp = ob["composiciones"][0]["id_composicion_obligacion"]

    db_session.execute(
        text(
            """
            UPDATE composicion_obligacion
            SET importe_componente = 800.00
            WHERE id_composicion_obligacion = :id
            """
        ),
        {"id": id_comp},
    )

    saldos = _saldos_obligacion(db_session, ob["id_obligacion_financiera"])
    assert float(saldos["importe_total"]) == pytest.approx(800.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(800.00)


def test_soft_delete_y_anulacion_de_composicion_reducen_obligacion(
    client, db_session
) -> None:
    _install_patch(db_session)
    ob = _crear_obligacion_base(client, db_session, codigo="SAL-COMP-DEL-001")
    id_ob = ob["id_obligacion_financiera"]
    id_expensa = _insertar_composicion(
        db_session,
        id_obligacion_financiera=id_ob,
        codigo_concepto="EXPENSA_TRASLADADA",
        importe=250.00,
    )
    id_admin = _insertar_composicion(
        db_session,
        id_obligacion_financiera=id_ob,
        codigo_concepto="CARGO_ADMINISTRATIVO",
        importe=150.00,
        orden=3,
    )

    db_session.execute(
        text(
            """
            UPDATE composicion_obligacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_composicion_obligacion = :id
            """
        ),
        {"id": id_expensa},
    )
    saldos = _saldos_obligacion(db_session, id_ob)
    assert float(saldos["importe_total"]) == pytest.approx(1150.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(1150.00)

    db_session.execute(
        text(
            """
            UPDATE composicion_obligacion
            SET estado_composicion_obligacion = 'ANULADA'
            WHERE id_composicion_obligacion = :id
            """
        ),
        {"id": id_admin},
    )
    saldos = _saldos_obligacion(db_session, id_ob)
    assert float(saldos["importe_total"]) == pytest.approx(1000.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(1000.00)


def test_aplicacion_contra_composicion_recalcula_saldo_correctamente(
    client, db_session
) -> None:
    _install_patch(db_session)
    ob = _crear_obligacion_base(client, db_session, codigo="SAL-COMP-APL-001")
    id_ob = ob["id_obligacion_financiera"]
    id_expensa = _insertar_composicion(
        db_session,
        id_obligacion_financiera=id_ob,
        codigo_concepto="EXPENSA_TRASLADADA",
        importe=500.00,
    )

    _insertar_aplicacion_directa(
        db_session,
        id_obligacion_financiera=id_ob,
        id_composicion_obligacion=id_expensa,
        importe=300.00,
    )

    saldos = _saldos_obligacion(db_session, id_ob)
    saldo_comp = db_session.execute(
        text(
            """
            SELECT saldo_componente
            FROM composicion_obligacion
            WHERE id_composicion_obligacion = :id
            """
        ),
        {"id": id_expensa},
    ).scalar_one()
    assert float(saldos["importe_total"]) == pytest.approx(1500.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(1200.00)
    assert float(saldos["importe_cancelado_acumulado"]) == pytest.approx(300.00)
    assert float(saldo_comp) == pytest.approx(200.00)


def test_imputacion_existente_sigue_reduciendo_saldos(client, db_session) -> None:
    _install_patch(db_session)
    ob = _crear_obligacion_base(client, db_session, codigo="SAL-COMP-IMP-001")

    _imputar(client, id_obligacion_financiera=ob["id_obligacion_financiera"], monto=400.00)

    saldos = _saldos_obligacion(db_session, ob["id_obligacion_financiera"])
    assert float(saldos["importe_total"]) == pytest.approx(1000.00)
    assert float(saldos["saldo_pendiente"]) == pytest.approx(600.00)
