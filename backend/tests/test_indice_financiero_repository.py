from datetime import date

from sqlalchemy import text

from app.infrastructure.persistence.repositories.indice_financiero_repository import (
    IndiceFinancieroRepository,
)


def _crear_indice(db_session, codigo: str, estado: str = "ACTIVO", deleted: bool = False) -> int:
    row = db_session.execute(
        text(
            """
            INSERT INTO indice_financiero (
                codigo_indice_financiero,
                nombre_indice_financiero,
                tipo_indice,
                unidad_medida,
                frecuencia_publicacion,
                estado_indice_financiero,
                deleted_at
            )
            VALUES (
                :codigo,
                :nombre,
                'IPC',
                'PUNTOS',
                'MENSUAL',
                :estado,
                :deleted_at
            )
            RETURNING id_indice_financiero
            """
        ),
        {
            "codigo": codigo,
            "nombre": f"Indice {codigo}",
            "estado": estado,
            "deleted_at": "2099-01-01 00:00:00" if deleted else None,
        },
    ).one()
    return row[0]


def _crear_valor(
    db_session,
    id_indice_financiero: int,
    fecha_valor: str,
    valor_indice: str,
    estado_valor_indice: str = "PUBLICADO",
    deleted: bool = False,
) -> int:
    row = db_session.execute(
        text(
            """
            INSERT INTO indice_financiero_valor (
                id_indice_financiero,
                fecha_valor,
                valor_indice,
                fecha_publicacion,
                fuente_valor,
                estado_valor_indice,
                deleted_at
            )
            VALUES (
                :id_indice_financiero,
                :fecha_valor,
                :valor_indice,
                :fecha_publicacion,
                'INDEC',
                :estado_valor_indice,
                :deleted_at
            )
            RETURNING id_indice_financiero_valor
            """
        ),
        {
            "id_indice_financiero": id_indice_financiero,
            "fecha_valor": fecha_valor,
            "valor_indice": valor_indice,
            "fecha_publicacion": fecha_valor,
            "estado_valor_indice": estado_valor_indice,
            "deleted_at": "2099-01-01 00:00:00" if deleted else None,
        },
    ).one()
    return row[0]


def test_indice_activo_valor_publicado_exacto_por_fecha(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "IPC_NAC")
    id_valor = _crear_valor(db_session, id_indice, "2026-01-15", "105.55000000")

    result = repo.get_valor_publicado_por_codigo_y_fecha("IPC_NAC", date(2026, 1, 15))

    assert result is not None
    assert result["id_indice_financiero"] == id_indice
    assert result["id_indice_financiero_valor"] == id_valor
    assert result["fecha_valor"] == date(2026, 1, 15)


def test_indice_activo_sin_fecha_exacta_devuelve_ultimo_anterior(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "UVA")
    _crear_valor(db_session, id_indice, "2026-02-10", "110.00000000")
    id_valor_esperado = _crear_valor(db_session, id_indice, "2026-03-10", "111.00000000")

    result = repo.get_valor_publicado_por_codigo_y_fecha("UVA", date(2026, 3, 20))

    assert result is not None
    assert result["id_indice_financiero_valor"] == id_valor_esperado
    assert result["fecha_valor"] == date(2026, 3, 10)


def test_indice_activo_con_valores_futuros_solo_devuelve_none(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "CER")
    _crear_valor(db_session, id_indice, "2026-06-01", "120.00000000")

    result = repo.get_valor_publicado_por_codigo_y_fecha("CER", date(2026, 5, 10))

    assert result is None


def test_indice_activo_ignora_borrador_y_anulado(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "ICC")
    _crear_valor(
        db_session,
        id_indice,
        "2026-04-10",
        "130.00000000",
        estado_valor_indice="BORRADOR",
    )
    _crear_valor(
        db_session,
        id_indice,
        "2026-04-09",
        "129.00000000",
        estado_valor_indice="ANULADO",
    )

    result = repo.get_valor_publicado_por_codigo_y_fecha("ICC", date(2026, 4, 10))

    assert result is None


def test_indice_no_activo_devuelve_none(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    for estado in ("INACTIVO", "ANULADO", "BORRADOR"):
        id_indice = _crear_indice(db_session, f"IDX_{estado}", estado=estado)
        _crear_valor(db_session, id_indice, "2026-01-10", "100.00000000")

        result = repo.get_valor_publicado_por_codigo_y_fecha(
            f"IDX_{estado}", date(2026, 1, 10)
        )

        assert result is None


def test_normaliza_codigo_con_espacios_y_minusculas(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "RIPTE")

    result_none = repo.get_valor_publicado_por_codigo_y_fecha("   ", date(2026, 1, 1))
    assert result_none is None

    _crear_valor(db_session, id_indice, "2026-01-01", "101.00000000")

    result = repo.get_valor_publicado_por_codigo_y_fecha("  ripte  ", date(2026, 1, 1))

    assert result is not None
    assert result["codigo_indice_financiero"] == "RIPTE"


def test_soft_delete_indice_y_valor_no_se_usan(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)

    id_indice_deleted = _crear_indice(db_session, "IND_DEL", deleted=True)
    _crear_valor(db_session, id_indice_deleted, "2026-01-05", "99.00000000")

    result_indice_deleted = repo.get_valor_publicado_por_codigo_y_fecha(
        "IND_DEL", date(2026, 1, 5)
    )
    assert result_indice_deleted is None

    id_indice = _crear_indice(db_session, "VAL_DEL")
    _crear_valor(db_session, id_indice, "2026-01-05", "98.00000000", deleted=True)

    result_valor_deleted = repo.get_valor_publicado_por_codigo_y_fecha(
        "VAL_DEL", date(2026, 1, 5)
    )
    assert result_valor_deleted is None


def test_indice_activo_valor_publicado_por_id_y_fecha(db_session) -> None:
    repo = IndiceFinancieroRepository(db_session)
    id_indice = _crear_indice(db_session, "IPC_ID")
    _crear_valor(db_session, id_indice, "2026-01-10", "100.00000000")
    id_valor_esperado = _crear_valor(
        db_session, id_indice, "2026-02-10", "105.00000000"
    )

    result = repo.get_valor_publicado_por_id_y_fecha(id_indice, date(2026, 2, 20))

    assert result is not None
    assert result["id_indice_financiero"] == id_indice
    assert result["id_indice_financiero_valor"] == id_valor_esperado
    assert result["fecha_valor"] == date(2026, 2, 10)
    assert repo.get_valor_publicado_por_id_y_fecha(0, date(2026, 2, 20)) is None
