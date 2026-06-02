from datetime import date
from decimal import Decimal

from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _crear_unidad_funcional,
    _insertar_reserva_conflictiva,
    _insertar_venta_conflictiva,
)
from tests.test_reservas_venta_confirmar_venta_completa import (
    _composiciones_by_venta,
    _count_indexacion_config_by_venta,
    _count_obligacion_indexacion_by_venta,
    _insertar_indice_financiero_minimo,
    _insertar_indice_financiero_valor,
    _plan_bloques_by_venta,
    _usar_plan_indexado,
    _usar_plan_interes_directo,
)

ENDPOINT = "/api/v1/ventas/directa/confirmar-venta-completa"


def _crear_base_directa(client, db_session, *, codigo: str) -> dict[str, int]:
    id_persona = _crear_persona(
        client, nombre=f"Comprador {codigo}", apellido="Directo"
    )
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9900 + abs(hash(codigo)) % 200,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo=f"INM-VD-COMP-{codigo}")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    return {
        "id_inmueble": id_inmueble,
        "id_persona": id_persona,
        "id_rol": id_rol,
    }


def _payload(
    *,
    codigo_venta: str,
    id_inmueble: int,
    id_persona: int,
    id_rol: int,
    confirmacion_observaciones: str = "Venta directa confirmada",
) -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": codigo_venta,
            "fecha_venta": "2026-05-22T10:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta directa completa",
        },
        "objetos": [
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": "150000.00",
                "observaciones": "Objeto venta directa",
            }
        ],
        "compradores": [
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-05-22",
                "fecha_hasta": None,
                "observaciones": "Comprador principal",
            }
        ],
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "ANTICIPO_Y_SALDO",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-05-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-06-30",
            "cuotas": [],
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
                    "fecha_vencimiento": "2026-05-30",
                },
                {
                    "tipo_bloque": "SALDO",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "fecha_vencimiento": "2026-06-30",
                },
            ],
            "observaciones": "Plan venta directa",
        },
        "confirmacion": {
            "observaciones": confirmacion_observaciones,
        },
    }


def _venta_by_codigo(db_session, codigo_venta: str):
    return (
        db_session.execute(
            text("""
            SELECT id_venta, id_reserva_venta, estado_venta, version_registro, monto_total
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


def _count_obligaciones(db_session) -> int:
    return db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()


def _count_venta_objetos(db_session, id_venta: int) -> int:
    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def _count_compradores(db_session, id_venta: int) -> int:
    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def _porcentajes_compradores(db_session, id_venta: int) -> list[Decimal]:
    rows = (
        db_session.execute(
            text("""
            SELECT porcentaje_responsabilidad
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_persona
            """),
            {"id_venta": id_venta},
        )
        .mappings()
        .all()
    )
    return [row["porcentaje_responsabilidad"] for row in rows]


def _obligados_porcentaje(db_session, id_venta: int) -> list[Decimal]:
    rows = (
        db_session.execute(
            text("""
            SELECT oo.porcentaje_responsabilidad
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
            ORDER BY o.numero_obligacion, oo.id_persona
            """),
            {"id_venta": id_venta},
        )
        .mappings()
        .all()
    )
    return [row["porcentaje_responsabilidad"] for row in rows]


def test_patch_porcentaje_responsabilidad_relacion_persona_rol_aplicado(
    db_session,
) -> None:
    column_exists = db_session.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'relacion_persona_rol'
                  AND column_name = 'porcentaje_responsabilidad'
            )
            """)).scalar_one()
    constraint_exists = db_session.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'public.relacion_persona_rol'::regclass
                  AND conname = 'chk_rpr_porcentaje_responsabilidad'
            )
            """)).scalar_one()

    assert column_exists is True
    assert constraint_exists is True


def test_confirmar_venta_directa_completa_exito(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="OK")

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-OK", **base),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["venta"]["estado_venta"] == "confirmada"
    assert body["data"]["obligaciones"]["cantidad"] == 2

    venta = _venta_by_codigo(db_session, "VD-COMP-OK")
    assert venta is not None
    assert venta["id_reserva_venta"] is None
    assert venta["estado_venta"] == "confirmada"
    assert _count_venta_objetos(db_session, venta["id_venta"]) == 1
    assert _count_compradores(db_session, venta["id_venta"]) == 1
    assert _porcentajes_compradores(db_session, venta["id_venta"]) == [
        Decimal("100.00")
    ]


def test_confirmar_venta_directa_un_objeto_sin_precio_defaulta_monto_total(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DEF-PRECIO")
    payload = _payload(codigo_venta="VD-COMP-DEF-PRECIO", **base)
    del payload["objetos"][0]["precio_asignado"]

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-DEF-PRECIO")
    assert venta is not None
    assert venta["monto_total"] == Decimal("150000.00")
    assert _precios_objetos(db_session, venta["id_venta"]) == [Decimal("150000.00")]


def test_confirmar_venta_directa_un_objeto_precio_distinto_de_monto_total_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="PRECIO-MISMATCH")
    payload = _payload(codigo_venta="VD-COMP-PRECIO-MISMATCH", **base)
    payload["objetos"][0]["precio_asignado"] = "140000.00"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA"
    ]
    assert _venta_by_codigo(db_session, "VD-COMP-PRECIO-MISMATCH") is None


def test_confirmar_venta_directa_dos_objetos_60_40_deriva_total_y_plan(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="OBJ-60-40-A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VD-COMP-OBJ-60-40-B")
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE"
    )
    payload = _payload(codigo_venta="VD-COMP-OBJ-60-40", **base)
    payload["generar_venta"]["monto_total"] = "100.00"
    payload["condiciones_comerciales"]["monto_total"] = "100.00"
    payload["condiciones_comerciales"]["importe_anticipo"] = "60.00"
    payload["condiciones_comerciales"]["importe_saldo"] = "40.00"
    payload["plan_pago_v2"]["monto_total_plan"] = "100.00"
    payload["plan_pago_v2"]["bloques"][0]["importe_total_bloque"] = "60.00"
    payload["plan_pago_v2"]["bloques"][1]["importe_total_bloque"] = "40.00"
    payload["objetos"][0]["precio_asignado"] = "60.00"
    payload["objetos"].append(
        {
            "id_inmueble": id_inmueble_2,
            "id_unidad_funcional": None,
            "precio_asignado": "40.00",
            "observaciones": "Objeto venta directa 2",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-OBJ-60-40")
    assert venta is not None
    assert venta["monto_total"] == Decimal("100.00")
    assert _precios_objetos(db_session, venta["id_venta"]) == [
        Decimal("60.00"),
        Decimal("40.00"),
    ]
    assert _monto_total_plan_by_venta(db_session, venta["id_venta"]) == Decimal(
        "100.00"
    )


def _ajustar_payload_multiobjeto_100(payload: dict[str, object]) -> None:
    payload["generar_venta"]["monto_total"] = "100.00"
    payload["condiciones_comerciales"]["monto_total"] = "100.00"
    payload["condiciones_comerciales"]["importe_anticipo"] = "60.00"
    payload["condiciones_comerciales"]["importe_saldo"] = "40.00"
    payload["plan_pago_v2"]["monto_total_plan"] = "100.00"
    payload["plan_pago_v2"]["bloques"][0]["importe_total_bloque"] = "60.00"
    payload["plan_pago_v2"]["bloques"][1]["importe_total_bloque"] = "40.00"
    payload["objetos"][0]["precio_asignado"] = "60.00"


def test_confirmar_venta_directa_inmueble_y_uf_hija_falla_por_jerarquia_solapada(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="JER-HIJA")
    id_unidad_funcional = _crear_unidad_funcional(
        client, id_inmueble=base["id_inmueble"], codigo="UF-VD-JER-HIJA"
    )
    payload = _payload(codigo_venta="VD-COMP-JER-HIJA", **base)
    _ajustar_payload_multiobjeto_100(payload)
    payload["objetos"].append(
        {
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "precio_asignado": "40.00",
            "observaciones": "UF hija del inmueble payload",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETO_VENTA_JERARQUIA_SOLAPADA"]
    assert _venta_by_codigo(db_session, "VD-COMP-JER-HIJA") is None


def test_confirmar_venta_directa_inmueble_y_uf_de_otro_inmueble_no_falla_por_jerarquia(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="JER-OTRO-A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VD-JER-OTRO-B")
    id_unidad_funcional = _crear_unidad_funcional(
        client, id_inmueble=id_inmueble_2, codigo="UF-VD-JER-OTRO"
    )
    _crear_disponibilidad(
        client,
        id_unidad_funcional=id_unidad_funcional,
        estado_disponibilidad="DISPONIBLE",
    )
    payload = _payload(codigo_venta="VD-COMP-JER-OTRO", **base)
    _ajustar_payload_multiobjeto_100(payload)
    payload["objetos"].append(
        {
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "precio_asignado": "40.00",
            "observaciones": "UF de otro inmueble",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-JER-OTRO")
    assert venta is not None
    assert venta["monto_total"] == Decimal("100.00")


def test_confirmar_venta_directa_dos_ufs_del_mismo_inmueble_siguen_permitidas(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="JER-UFS")
    id_inmueble = _crear_inmueble(client, codigo="INM-VD-JER-UFS")
    id_unidad_funcional_1 = _crear_unidad_funcional(
        client, id_inmueble=id_inmueble, codigo="UF-VD-JER-UFS-1"
    )
    id_unidad_funcional_2 = _crear_unidad_funcional(
        client, id_inmueble=id_inmueble, codigo="UF-VD-JER-UFS-2"
    )
    _crear_disponibilidad(
        client,
        id_unidad_funcional=id_unidad_funcional_1,
        estado_disponibilidad="DISPONIBLE",
    )
    _crear_disponibilidad(
        client,
        id_unidad_funcional=id_unidad_funcional_2,
        estado_disponibilidad="DISPONIBLE",
    )
    payload = _payload(codigo_venta="VD-COMP-JER-UFS", **base)
    _ajustar_payload_multiobjeto_100(payload)
    payload["objetos"] = [
        {
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional_1,
            "precio_asignado": "60.00",
            "observaciones": "UF 1",
        },
        {
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional_2,
            "precio_asignado": "40.00",
            "observaciones": "UF 2",
        },
    ]

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-JER-UFS")
    assert venta is not None
    assert _count_venta_objetos(db_session, venta["id_venta"]) == 2


def test_confirmar_venta_directa_objeto_duplicado_exactamente_sigue_fallando(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="OBJ-DUP")
    payload = _payload(codigo_venta="VD-COMP-OBJ-DUP", **base)
    _ajustar_payload_multiobjeto_100(payload)
    payload["objetos"].append(
        {
            "id_inmueble": base["id_inmueble"],
            "id_unidad_funcional": None,
            "precio_asignado": "40.00",
            "observaciones": "Duplicado exacto",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETO_VENTA_DUPLICADO"]
    assert _venta_by_codigo(db_session, "VD-COMP-OBJ-DUP") is None


def test_confirmar_venta_directa_dos_objetos_sin_precio_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="OBJ-SIN-PRECIO-A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VD-COMP-OBJ-SIN-PRECIO-B")
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE"
    )
    payload = _payload(codigo_venta="VD-COMP-OBJ-SIN-PRECIO", **base)
    payload["objetos"].append(
        {
            "id_inmueble": id_inmueble_2,
            "id_unidad_funcional": None,
            "observaciones": "Objeto venta directa sin precio",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["VALOR_ASIGNADO_OBJETO_REQUERIDO"]
    assert _venta_by_codigo(db_session, "VD-COMP-OBJ-SIN-PRECIO") is None


def test_confirmar_venta_directa_suma_objetos_distinta_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="SUMA-DISTINTA")
    payload = _payload(codigo_venta="VD-COMP-SUMA-DISTINTA", **base)
    payload["objetos"][0]["precio_asignado"] = "149999.99"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA"
    ]
    assert _venta_by_codigo(db_session, "VD-COMP-SUMA-DISTINTA") is None


def test_confirmar_venta_directa_precio_asignado_no_positivo_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="PRECIO-CERO")
    payload = _payload(codigo_venta="VD-COMP-PRECIO-CERO", **base)
    payload["objetos"][0]["precio_asignado"] = "0.00"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["VALOR_ASIGNADO_OBJETO_INVALIDO"]
    assert _venta_by_codigo(db_session, "VD-COMP-PRECIO-CERO") is None


def test_confirmar_venta_directa_completa_dos_compradores_50_50(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="MC-50")
    id_persona_2 = _crear_persona(client, nombre="Comprador 2", apellido="Directo")
    payload = _payload(codigo_venta="VD-COMP-MC-50", **base)
    payload["compradores"][0]["porcentaje_responsabilidad"] = "50.00"
    payload["compradores"].append(
        {
            "id_persona": id_persona_2,
            "id_rol_participacion": base["id_rol"],
            "porcentaje_responsabilidad": "50.00",
            "fecha_desde": "2026-05-22",
            "fecha_hasta": None,
            "observaciones": "Comprador secundario",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-MC-50")
    assert venta is not None
    assert _count_compradores(db_session, venta["id_venta"]) == 2
    assert _porcentajes_compradores(db_session, venta["id_venta"]) == [
        Decimal("50.00"),
        Decimal("50.00"),
    ]
    assert _obligados_porcentaje(db_session, venta["id_venta"]) == [
        Decimal("50.00"),
        Decimal("50.00"),
        Decimal("50.00"),
        Decimal("50.00"),
    ]


def test_confirmar_venta_directa_completa_dos_compradores_70_30(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="MC-70")
    id_persona_2 = _crear_persona(client, nombre="Comprador 2", apellido="Directo")
    payload = _payload(codigo_venta="VD-COMP-MC-70", **base)
    payload["compradores"][0]["porcentaje_responsabilidad"] = "70.00"
    payload["compradores"].append(
        {
            "id_persona": id_persona_2,
            "id_rol_participacion": base["id_rol"],
            "porcentaje_responsabilidad": "30.00",
            "fecha_desde": "2026-05-22",
            "fecha_hasta": None,
            "observaciones": "Comprador secundario",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-MC-70")
    assert venta is not None
    assert _porcentajes_compradores(db_session, venta["id_venta"]) == [
        Decimal("70.00"),
        Decimal("30.00"),
    ]


def test_confirmar_venta_directa_completa_comprador_duplicado_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DUP")
    payload = _payload(codigo_venta="VD-COMP-DUP", **base)
    payload["compradores"][0]["porcentaje_responsabilidad"] = "50.00"
    payload["compradores"].append({**payload["compradores"][0]})

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["COMPRADOR_DUPLICADO"]
    assert _venta_by_codigo(db_session, "VD-COMP-DUP") is None


def test_confirmar_venta_directa_completa_suma_90_falla(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="SUM90")
    id_persona_2 = _crear_persona(client, nombre="Comprador 2", apellido="Directo")
    payload = _payload(codigo_venta="VD-COMP-SUM90", **base)
    payload["compradores"][0]["porcentaje_responsabilidad"] = "60.00"
    payload["compradores"].append(
        {
            "id_persona": id_persona_2,
            "id_rol_participacion": base["id_rol"],
            "porcentaje_responsabilidad": "30.00",
            "fecha_desde": "2026-05-22",
            "fecha_hasta": None,
            "observaciones": "Comprador secundario",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "PORCENTAJE_COMPRADORES_NO_SUMA_100"
    ]
    assert _venta_by_codigo(db_session, "VD-COMP-SUM90") is None


def test_confirmar_venta_directa_completa_porcentaje_cero_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="PCT0")
    payload = _payload(codigo_venta="VD-COMP-PCT0", **base)
    payload["compradores"][0]["porcentaje_responsabilidad"] = "0.00"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["PORCENTAJE_COMPRADOR_INVALIDO"]
    assert _venta_by_codigo(db_session, "VD-COMP-PCT0") is None


def test_confirmar_venta_directa_completa_multiple_sin_porcentaje_falla(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="SIN-PCT")
    id_persona_2 = _crear_persona(client, nombre="Comprador 2", apellido="Directo")
    payload = _payload(codigo_venta="VD-COMP-SIN-PCT", **base)
    payload["compradores"].append(
        {
            "id_persona": id_persona_2,
            "id_rol_participacion": base["id_rol"],
            "fecha_desde": "2026-05-22",
            "fecha_hasta": None,
            "observaciones": "Comprador secundario",
        }
    )

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "PORCENTAJE_COMPRADORES_NO_DEFINIDO"
    ]
    assert _venta_by_codigo(db_session, "VD-COMP-SIN-PCT") is None


def test_confirmar_venta_directa_falla_condiciones_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="COND")
    payload = _payload(codigo_venta="VD-COMP-COND", **base)
    payload["condiciones_comerciales"]["monto_total"] = "140000.00"
    payload["plan_pago_v2"]["monto_total_plan"] = "140000.00"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == [
        "SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA"
    ]
    assert _venta_by_codigo(db_session, "VD-COMP-COND") is None


def test_confirmar_venta_directa_falla_plan_pago_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="PLAN")
    before_obligaciones = _count_obligaciones(db_session)
    payload = _payload(codigo_venta="VD-COMP-PLAN", **base)
    payload["plan_pago_v2"]["tipo_pago"] = "INVALIDO"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert _venta_by_codigo(db_session, "VD-COMP-PLAN") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_directa_falla_confirmacion_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="CONF")
    before_obligaciones = _count_obligaciones(db_session)
    install_statement_failpoint_once(
        db_session,
        statement_prefix="UPDATE venta",
        parameter_name="observaciones",
        parameter_value="FORCE_CONFIRM_FAIL",
        error_message="forced failure on direct complete confirm",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(
            codigo_venta="VD-COMP-CONF",
            confirmacion_observaciones="FORCE_CONFIRM_FAIL",
            **base,
        ),
    )

    assert response.status_code == 500
    assert _venta_by_codigo(db_session, "VD-COMP-CONF") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_directa_objeto_no_disponible(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="NO-DISP")
    db_session.execute(
        text("""
            UPDATE disponibilidad
            SET estado_disponibilidad = 'RESERVADA'
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """),
        {"id_inmueble": base["id_inmueble"]},
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-NO-DISP", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DISPONIBILIDAD_STATE"]
    assert _venta_by_codigo(db_session, "VD-COMP-NO-DISP") is None


def test_confirmar_venta_directa_objeto_con_reserva_vigente(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="RESERVA")
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=base["id_inmueble"],
        codigo_reserva="RV-VD-COMP-CONFLICTO",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-RESERVA", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONFLICTING_RESERVA"]
    assert _venta_by_codigo(db_session, "VD-COMP-RESERVA") is None


def test_confirmar_venta_directa_comprador_invalido(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="ROL")
    id_rol_no_comprador = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9950,
        codigo_rol="VENDEDOR-VD-COMP",
    )
    base["id_rol"] = id_rol_no_comprador

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-ROL", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_ROL_COMPRADOR"]
    assert _venta_by_codigo(db_session, "VD-COMP-ROL") is None


def test_confirmar_venta_directa_codigo_duplicado(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="DUP")
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=base["id_inmueble"],
        codigo_venta="VD-COMP-DUP",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-DUP", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["DUPLICATE_CODIGO_VENTA"]


def test_confirmar_venta_directa_completa_interes_directo_propaga_bloque(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="ID")
    payload = _payload(codigo_venta="VD-COMP-ID", **base)
    _usar_plan_interes_directo(payload)

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-ID")
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


def test_confirmar_venta_directa_completa_indexacion_propaga_bloque(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="IX")
    id_indice = _insertar_indice_financiero_minimo(
        db_session, codigo="RIPTE-COMP-VD-IX"
    )
    _insertar_indice_financiero_valor(
        db_session,
        id_indice_financiero=id_indice,
        fecha_valor=date(2026, 7, 10),
        valor_indice=Decimal("110.00000000"),
    )
    payload = _payload(codigo_venta="VD-COMP-IX", **base)
    _usar_plan_indexado(payload, id_indice)

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 200, response.text
    venta = _venta_by_codigo(db_session, "VD-COMP-IX")
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


def test_confirmar_venta_directa_completa_indexacion_invalida_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="IX-NEG")
    before_obligaciones = _count_obligaciones(db_session)
    id_indice = _insertar_indice_financiero_minimo(
        db_session, codigo="RIPTE-COMP-VD-NEG"
    )
    _insertar_indice_financiero_valor(
        db_session,
        id_indice_financiero=id_indice,
        fecha_valor=date(2026, 6, 1),
        valor_indice=Decimal("90.00000000"),
    )
    payload = _payload(codigo_venta="VD-COMP-IX-NEG", **base)
    _usar_plan_indexado(payload, id_indice)

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert (
        "INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO"
        in response.json()["details"]["errors"]
    )
    assert _venta_by_codigo(db_session, "VD-COMP-IX-NEG") is None
    assert _count_obligaciones(db_session) == before_obligaciones
