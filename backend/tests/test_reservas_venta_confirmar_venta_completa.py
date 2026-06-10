from datetime import date
from decimal import Decimal

from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)
from tests.test_reservas_venta_generate_venta import (
    _insertar_reserva_para_generar_venta,
)


def _crear_reserva_confirmada(client, db_session, *, codigo: str) -> dict[str, int]:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre=f"Comprador {codigo}", apellido="Test")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9600 + abs(hash(codigo)) % 300,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva=codigo,
        estado_reserva="confirmada",
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "observaciones": "Objeto reservado",
            }
        ],
        participaciones=[
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
                "observaciones": "Comprador",
            }
        ],
    )
    return {
        **reserva,
        "id_inmueble": id_inmueble,
    }


def _payload(
    *,
    codigo_venta: str,
    id_inmueble: int,
    confirmacion_observaciones: str = "Venta confirmada completa",
) -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": codigo_venta,
            "fecha_venta": "2026-04-22T11:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta completa desde reserva",
        },
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "ANTICIPO_Y_SALDO",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-04-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-05-30",
            "cuotas": [],
            "objetos": [
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": "150000.00",
                }
            ],
        },
        "plan_pago_v2": {
            "tipo_pago": "FINANCIADO",
            "monto_total_plan": "150000.00",
            "moneda": "ARS",
            "bloques": [
                {
                    "tipo_bloque": "ANTICIPO",
                    "etiqueta_bloque": "Anticipo",
                    "importe_total_bloque": "50000.00",
                    "fecha_vencimiento": "2026-04-30",
                },
                {
                    "tipo_bloque": "SALDO",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "fecha_vencimiento": "2026-05-30",
                },
            ],
            "observaciones": "Plan por bloques",
        },
        "confirmacion": {
            "observaciones": confirmacion_observaciones,
        },
    }


def _venta_by_codigo(db_session, codigo_venta: str):
    return (
        db_session.execute(
            text("""
            SELECT id_venta, estado_venta, version_registro, monto_total
            FROM venta
            WHERE codigo_venta = :codigo_venta
              AND deleted_at IS NULL
            """),
            {"codigo_venta": codigo_venta},
        )
        .mappings()
        .one_or_none()
    )


def _precios_objetos(db_session, id_venta: int) -> list[Decimal]:
    rows = (
        db_session.execute(
            text("""
            SELECT precio_asignado
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_venta_objeto
            """),
            {"id_venta": id_venta},
        )
        .mappings()
        .all()
    )
    return [row["precio_asignado"] for row in rows]


def _monto_total_plan_by_venta(db_session, id_venta: int) -> Decimal:
    return db_session.execute(
        text("""
            SELECT monto_total_plan
            FROM plan_pago_venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def _estado_reserva(db_session, id_reserva_venta: int) -> str:
    return db_session.execute(
        text("""
            SELECT estado_reserva
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """),
        {"id_reserva_venta": id_reserva_venta},
    ).scalar_one()


def _count_obligaciones(db_session) -> int:
    return db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()


def _insertar_indice_financiero_minimo(db_session, *, codigo: str) -> int:
    return db_session.execute(
        text("""
            INSERT INTO indice_financiero (
                codigo_indice_financiero,
                nombre_indice_financiero,
                tipo_indice,
                unidad_medida,
                frecuencia_publicacion,
                fuente_indice,
                estado_indice_financiero
            )
            VALUES (:codigo, :codigo, 'INDICE', 'PUNTOS', 'MENSUAL', 'TEST', 'ACTIVO')
            RETURNING id_indice_financiero
            """),
        {"codigo": codigo},
    ).scalar_one()


def _insertar_indice_financiero_valor(
    db_session,
    *,
    id_indice_financiero: int,
    fecha_valor: date,
    valor_indice: Decimal,
) -> int:
    return db_session.execute(
        text("""
            INSERT INTO indice_financiero_valor (
                id_indice_financiero,
                fecha_valor,
                valor_indice,
                fecha_publicacion,
                fuente_valor,
                estado_valor_indice
            )
            VALUES (
                :id_indice_financiero,
                :fecha_valor,
                :valor_indice,
                :fecha_valor,
                'TEST',
                'PUBLICADO'
            )
            RETURNING id_indice_financiero_valor
            """),
        {
            "id_indice_financiero": id_indice_financiero,
            "fecha_valor": fecha_valor,
            "valor_indice": valor_indice,
        },
    ).scalar_one()


def _usar_plan_interes_directo(payload: dict[str, object]) -> None:
    payload["plan_pago_v2"]["bloques"] = [
        {
            "tipo_bloque": "TRAMO_CUOTAS",
            "etiqueta_bloque": "Tramo con interes directo",
            "importe_total_bloque": "150000.00",
            "cantidad_cuotas": 3,
            "fecha_primer_vencimiento": "2026-06-10",
            "periodicidad": "MENSUAL",
            "metodo_liquidacion": "INTERES_DIRECTO",
            "tasa_interes_directo_periodica": "0.02",
            "cantidad_periodos": 3,
            "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
        }
    ]


def _usar_plan_indexado(payload: dict[str, object], id_indice_financiero: int) -> None:
    payload["plan_pago_v2"]["bloques"] = [
        {
            "tipo_bloque": "TRAMO_CUOTAS",
            "etiqueta_bloque": "Tramo indexado",
            "importe_total_bloque": "150000.00",
            "cantidad_cuotas": 3,
            "fecha_primer_vencimiento": "2026-06-10",
            "periodicidad": "MENSUAL",
            "metodo_liquidacion": "INDEXACION",
            "id_indice_financiero": id_indice_financiero,
            "fecha_base_indice": "2026-05-01",
            "valor_base_indice": "100.12345678",
            "modo_indexacion": "POR_COEFICIENTE",
            "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
            "tipo_generacion_indexada": "DEFINITIVA",
            "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
            "conserva_capital_original": True,
            "genera_ajuste_por_diferencia": True,
        }
    ]


def _usar_plan_refuerzo_interno(payload: dict[str, object]) -> None:
    payload["plan_pago_v2"]["bloques"] = [
        {
            "tipo_bloque": "TRAMO_CUOTAS",
            "etiqueta_bloque": "Tramo con refuerzo interno",
            "importe_total_bloque": "150000.00",
            "cantidad_cuotas": 4,
            "fecha_primer_vencimiento": "2026-06-10",
            "periodicidad": "MENSUAL",
            "metodo_liquidacion": "SIN_INTERES",
            "cuotas_refuerzo": [
                {
                    "numero_cuota": 2,
                    "etiqueta": "Refuerzo interno cuota 2",
                    "unidades_refuerzo": "1.00",
                }
            ],
        }
    ]


def _obligaciones_items_by_venta(db_session, id_venta: int) -> list[dict]:
    return [
        dict(row)
        for row in db_session.execute(
            text("""
                SELECT o.numero_obligacion, o.tipo_item_cronograma, o.importe_total
                FROM obligacion_financiera o
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND o.deleted_at IS NULL
                ORDER BY o.numero_obligacion
                """),
            {"id_venta": id_venta},
        ).mappings()
    ]


def _plan_bloques_by_venta(db_session, id_venta: int) -> list[dict]:
    return [
        dict(row)
        for row in db_session.execute(
            text("""
                SELECT ppvb.*
                FROM plan_pago_venta_bloque ppvb
                JOIN plan_pago_venta ppv
                  ON ppv.id_plan_pago_venta = ppvb.id_plan_pago_venta
                WHERE ppv.id_venta = :id_venta
                  AND ppvb.deleted_at IS NULL
                ORDER BY ppvb.numero_bloque
                """),
            {"id_venta": id_venta},
        ).mappings()
    ]


def _composiciones_by_venta(db_session, id_venta: int) -> list[dict]:
    return [
        dict(row)
        for row in db_session.execute(
            text("""
                SELECT o.numero_obligacion, o.estado_obligacion, cf.codigo_concepto_financiero
                FROM composicion_obligacion co
                JOIN concepto_financiero cf
                  ON cf.id_concepto_financiero = co.id_concepto_financiero
                JOIN obligacion_financiera o
                  ON o.id_obligacion_financiera = co.id_obligacion_financiera
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND co.deleted_at IS NULL
                ORDER BY o.numero_obligacion, co.orden_composicion
                """),
            {"id_venta": id_venta},
        ).mappings()
    ]


def _count_indexacion_config_by_venta(db_session, id_venta: int) -> int:
    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM plan_pago_venta_bloque_indexacion ppvbi
            JOIN plan_pago_venta_bloque ppvb
              ON ppvb.id_plan_pago_venta_bloque = ppvbi.id_plan_pago_venta_bloque
            JOIN plan_pago_venta ppv
              ON ppv.id_plan_pago_venta = ppvb.id_plan_pago_venta
            WHERE ppv.id_venta = :id_venta
              AND ppvbi.deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def _count_obligacion_indexacion_by_venta(db_session, id_venta: int) -> int:
    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM obligacion_financiera_indexacion ofi
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = ofi.id_obligacion_financiera
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE rg.tipo_origen = 'venta'
              AND rg.id_origen = :id_venta
              AND ofi.deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def test_confirmar_venta_completa_desde_reserva_exito(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-OK")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-OK", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["reserva_venta"]["estado_reserva"] == "finalizada"
    assert body["data"]["venta"]["estado_venta"] == "confirmada"
    assert body["data"]["obligaciones"]["cantidad"] == 2

    venta = _venta_by_codigo(db_session, "V-COMP-OK")
    assert venta is not None
    assert venta["estado_venta"] == "confirmada"


def test_confirmar_venta_completa_desde_reserva_un_objeto_defaulta_monto_total(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-DEF-PRECIO")
    payload = _payload(
        codigo_venta="V-COMP-DEF-PRECIO", id_inmueble=reserva["id_inmueble"]
    )
    del payload["condiciones_comerciales"]["objetos"][0]["precio_asignado"]

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "V-COMP-DEF-PRECIO")
    assert venta is not None
    assert venta["monto_total"] == Decimal("150000.00")
    assert _precios_objetos(db_session, venta["id_venta"]) == [Decimal("150000.00")]


def test_confirmar_venta_completa_desde_reserva_multiobjeto_sin_asignacion_falla(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Comprador Multi", apellido="Reserva")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9821,
        codigo_rol="COMPRADOR",
    )
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RV-SIN-PRECIO-1")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RV-SIN-PRECIO-2")
    for id_inmueble in [id_inmueble_1, id_inmueble_2]:
        _crear_disponibilidad(
            client, id_inmueble=id_inmueble, estado_disponibilidad="RESERVADA"
        )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-COMP-SIN-PRECIO",
        estado_reserva="confirmada",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
        ],
        participaciones=[
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
            }
        ],
    )
    payload = _payload(codigo_venta="V-COMP-SIN-PRECIO", id_inmueble=id_inmueble_1)
    payload["condiciones_comerciales"]["objetos"] = [
        {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
        {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
    ]

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["VALOR_ASIGNADO_OBJETO_REQUERIDO"]
    assert _venta_by_codigo(db_session, "V-COMP-SIN-PRECIO") is None
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"


def test_confirmar_venta_completa_desde_reserva_plan_usa_total_derivado(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-PLAN-DER")
    payload = _payload(
        codigo_venta="V-COMP-PLAN-DER", id_inmueble=reserva["id_inmueble"]
    )
    payload["generar_venta"].pop("monto_total")
    payload["condiciones_comerciales"]["monto_total"] = "120000.00"
    payload["condiciones_comerciales"]["importe_anticipo"] = "20000.00"
    payload["condiciones_comerciales"]["importe_saldo"] = "100000.00"
    payload["condiciones_comerciales"]["objetos"][0]["precio_asignado"] = "120000.00"
    payload["plan_pago_v2"]["monto_total_plan"] = "120000.00"
    payload["plan_pago_v2"]["bloques"][0]["importe_total_bloque"] = "20000.00"
    payload["plan_pago_v2"]["bloques"][1]["importe_total_bloque"] = "100000.00"

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "V-COMP-PLAN-DER")
    assert venta is not None
    assert venta["monto_total"] == Decimal("120000.00")
    assert _precios_objetos(db_session, venta["id_venta"]) == [Decimal("120000.00")]
    assert _monto_total_plan_by_venta(db_session, venta["id_venta"]) == Decimal(
        "120000.00"
    )


def test_confirmar_venta_completa_desde_reserva_multiple_sin_porcentaje_falla(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona_1 = _crear_persona(client, nombre="Comprador A", apellido="Reserva")
    id_persona_2 = _crear_persona(client, nombre="Comprador B", apellido="Reserva")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9810,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-MC-SIN-PCT")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-COMP-MC-SIN-PCT",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
        participaciones=[
            {
                "id_persona": id_persona_1,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
            },
            {
                "id_persona": id_persona_2,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
            },
        ],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-MC-SIN-PCT", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "PORCENTAJE_COMPRADORES_NO_DEFINIDO"
    ]
    assert _venta_by_codigo(db_session, "V-COMP-MC-SIN-PCT") is None
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"


def test_confirmar_venta_completa_desde_reserva_copia_porcentajes_y_genera_obligados(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona_1 = _crear_persona(client, nombre="Comprador A", apellido="Reserva")
    id_persona_2 = _crear_persona(client, nombre="Comprador B", apellido="Reserva")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9811,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-MC-PCT")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-COMP-MC-PCT",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
        participaciones=[
            {
                "id_persona": id_persona_1,
                "id_rol_participacion": id_rol,
                "porcentaje_responsabilidad": Decimal("60.00"),
                "fecha_desde": "2026-04-21",
            },
            {
                "id_persona": id_persona_2,
                "id_rol_participacion": id_rol,
                "porcentaje_responsabilidad": Decimal("40.00"),
                "fecha_desde": "2026-04-21",
            },
        ],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-MC-PCT", id_inmueble=id_inmueble),
    )

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "V-COMP-MC-PCT")
    assert venta is not None
    porcentajes = (
        db_session.execute(
            text("""
            SELECT porcentaje_responsabilidad
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_persona
            """),
            {"id_venta": venta["id_venta"]},
        )
        .scalars()
        .all()
    )
    obligados = db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM relacion_generadora rg
            JOIN obligacion_financiera o
              ON o.id_relacion_generadora = rg.id_relacion_generadora
             AND o.deleted_at IS NULL
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            WHERE rg.tipo_origen = 'venta'
              AND rg.id_origen = :id_venta
              AND rg.deleted_at IS NULL
            """),
        {"id_venta": venta["id_venta"]},
    ).scalar_one()

    assert porcentajes == [Decimal("60.00"), Decimal("40.00")]
    assert obligados == 4


def test_confirmar_venta_completa_falla_condiciones_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-COND")
    payload = _payload(codigo_venta="V-COMP-COND", id_inmueble=reserva["id_inmueble"])
    payload["condiciones_comerciales"]["objetos"] = []

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-COND") is None


def test_confirmar_venta_completa_falla_plan_pago_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-PLAN")
    before_obligaciones = _count_obligaciones(db_session)
    payload = _payload(codigo_venta="V-COMP-PLAN", id_inmueble=reserva["id_inmueble"])
    payload["plan_pago_v2"]["tipo_pago"] = "INVALIDO"

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-PLAN") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_completa_falla_confirmacion_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-CONF")
    before_obligaciones = _count_obligaciones(db_session)
    install_statement_failpoint_once(
        db_session,
        statement_prefix="UPDATE venta",
        parameter_name="observaciones",
        parameter_value="FORCE_CONFIRM_FAIL",
        error_message="forced failure on complete confirm",
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(
            codigo_venta="V-COMP-CONF",
            id_inmueble=reserva["id_inmueble"],
            confirmacion_observaciones="FORCE_CONFIRM_FAIL",
        ),
    )

    assert response.status_code == 500
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-CONF") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_completa_reserva_inexistente(client) -> None:
    response = client.post(
        "/api/v1/reservas-venta/999999/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload(codigo_venta="V-COMP-NF", id_inmueble=1),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND_RESERVA_VENTA"


def test_confirmar_venta_completa_reserva_estado_invalido(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-STATE")
    db_session.execute(
        text("""
            UPDATE reserva_venta
            SET estado_reserva = 'borrador'
            WHERE id_reserva_venta = :id_reserva_venta
            """),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-STATE", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_RESERVA_STATE"]


def test_confirmar_venta_completa_if_match_invalido(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFMATCH")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload(
            codigo_venta="V-COMP-IFMATCH", id_inmueble=reserva["id_inmueble"]
        ),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_confirmar_venta_completa_x_op_id_faltante_devuelve_400(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-HDR-MISS")

    headers = {**HEADERS, "If-Match-Version": str(reserva["version_registro"])}
    headers.pop("X-Op-Id", None)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers=headers,
        json=_payload(
            codigo_venta="V-COMP-HDR-MISS", id_inmueble=reserva["id_inmueble"]
        ),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "X-Op-Id"}


def test_confirmar_venta_completa_if_match_faltante_devuelve_400(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFMISS")

    headers = dict(HEADERS)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers=headers,
        json=_payload(codigo_venta="V-COMP-IFMISS", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "If-Match-Version"}


def test_confirmar_venta_completa_if_match_invalido_formato_devuelve_400(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFBAD")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json=_payload(codigo_venta="V-COMP-IFBAD", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "If-Match-Version"}


def test_confirmar_venta_completa_desde_reserva_interes_directo_propaga_bloque(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-ID")
    payload = _payload(codigo_venta="V-COMP-ID", id_inmueble=reserva["id_inmueble"])
    _usar_plan_interes_directo(payload)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "V-COMP-ID")
    assert venta is not None
    bloques = _plan_bloques_by_venta(db_session, venta["id_venta"])
    assert bloques[0]["metodo_liquidacion"] == "INTERES_DIRECTO"
    assert Decimal(str(bloques[0]["tasa_interes_directo_periodica"])) == Decimal(
        "0.02000000"
    )
    assert bloques[0]["cantidad_periodos"] == 3
    assert bloques[0]["base_calculo_interes"] == "CAPITAL_INICIAL_BLOQUE"
    conceptos = {
        row["codigo_concepto_financiero"]
        for row in _composiciones_by_venta(db_session, venta["id_venta"])
    }
    assert {"CAPITAL_VENTA", "INTERES_FINANCIERO"}.issubset(conceptos)


def test_confirmar_venta_completa_desde_reserva_indexacion_propaga_bloque(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IX")
    id_indice = _insertar_indice_financiero_minimo(
        db_session, codigo="RIPTE-COMP-RV-IX"
    )
    _insertar_indice_financiero_valor(
        db_session,
        id_indice_financiero=id_indice,
        fecha_valor=date(2026, 7, 10),
        valor_indice=Decimal("110.00000000"),
    )
    payload = _payload(codigo_venta="V-COMP-IX", id_inmueble=reserva["id_inmueble"])
    _usar_plan_indexado(payload, id_indice)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "V-COMP-IX")
    assert venta is not None
    bloques = _plan_bloques_by_venta(db_session, venta["id_venta"])
    assert bloques[0]["metodo_liquidacion"] == "INDEXACION"
    assert _count_indexacion_config_by_venta(db_session, venta["id_venta"]) == 1
    assert _count_obligacion_indexacion_by_venta(db_session, venta["id_venta"]) == 2
    composiciones = _composiciones_by_venta(db_session, venta["id_venta"])
    assert "AJUSTE_INDEXACION" in {
        row["codigo_concepto_financiero"] for row in composiciones
    }
    assert [row for row in composiciones if row["numero_obligacion"] == 1] == [
        {
            "numero_obligacion": 1,
            "estado_obligacion": "PROYECTADA",
            "codigo_concepto_financiero": "CAPITAL_VENTA",
        }
    ]


def test_confirmar_venta_completa_desde_reserva_indexacion_invalida_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IX-NEG")
    before_obligaciones = _count_obligaciones(db_session)
    id_indice = _insertar_indice_financiero_minimo(
        db_session, codigo="RIPTE-COMP-RV-NEG"
    )
    _insertar_indice_financiero_valor(
        db_session,
        id_indice_financiero=id_indice,
        fecha_valor=date(2026, 6, 1),
        valor_indice=Decimal("90.00000000"),
    )
    payload = _payload(codigo_venta="V-COMP-IX-NEG", id_inmueble=reserva["id_inmueble"])
    _usar_plan_indexado(payload, id_indice)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert (
        "INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO"
        in response.json()["details"]["errors"]
    )
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-IX-NEG") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_completa_desde_reserva_propaga_refuerzo_interno(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-REF")
    payload = _payload(codigo_venta="V-COMP-REF", id_inmueble=reserva["id_inmueble"])
    _usar_plan_refuerzo_interno(payload)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["obligaciones"]["cantidad"] == 3
    venta = _venta_by_codigo(db_session, "V-COMP-REF")
    assert venta is not None
    obligaciones = _obligaciones_items_by_venta(db_session, venta["id_venta"])
    assert len(obligaciones) == 3
    assert all(ob["tipo_item_cronograma"] == "CUOTA" for ob in obligaciones)
    assert obligaciones[1]["importe_total"] == Decimal("75000.00")
    assert sum(
        (ob["importe_total"] for ob in obligaciones), Decimal("0.00")
    ) == Decimal("150000.00")


def test_confirmar_venta_completa_desde_reserva_refuerzo_duplicado_error_controlado(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-REF-DUP")
    payload = _payload(
        codigo_venta="V-COMP-REF-DUP", id_inmueble=reserva["id_inmueble"]
    )
    _usar_plan_refuerzo_interno(payload)
    payload["plan_pago_v2"]["bloques"][0]["cuotas_refuerzo"].append({"numero_cuota": 2})

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400, response.text
    assert "CUOTA_REFUERZO_DUPLICADA" in response.json()["details"]["errors"]
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-REF-DUP") is None
