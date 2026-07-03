from uuid import uuid4

from sqlalchemy import text


BASE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _headers(if_match: int | None = 1) -> dict[str, str]:
    headers = {**BASE_HEADERS, "X-Op-Id": str(uuid4())}
    if if_match is not None:
        headers["If-Match-Version"] = str(if_match)
    return headers


def _numero() -> str:
    return str((uuid4().int % 90_000_000) + 10_000_000)


def _cuit() -> str:
    base = str((uuid4().int % 90_000_000) + 10_000_000)
    return f"20-{base}-9"


def _crear_persona(client, *, nombre: str = "Ada") -> int:
    response = client.post(
        "/api/v1/personas",
        headers=_headers(if_match=None),
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": "Lovelace",
            "razon_social": None,
            "fecha_nacimiento": "1815-12-10",
            "estado_persona": "ACTIVA",
            "observaciones": "alta inicial",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _crear_documento(client, id_persona: int, tipo: str, numero: str, *, principal: bool) -> dict:
    response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=_headers(if_match=None),
        json={
            "tipo_documento": tipo,
            "numero_documento": numero,
            "pais_emision": None,
            "es_principal": principal,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _payload_persona(version: int, *, nombre: str = "Ada", observaciones: str | None = "tx") -> dict:
    return {
        "tipo_persona": "FISICA",
        "nombre": nombre,
        "apellido": "Lovelace",
        "razon_social": None,
        "fecha_nacimiento": "1815-12-10",
        "estado_persona": "ACTIVA",
        "observaciones": observaciones,
        "version_registro": version,
    }


def _put_datos(client, id_persona: int, payload: dict, *, if_match: int | None = 1):
    return client.put(
        f"/api/v1/personas/{id_persona}/datos-principales",
        headers=_headers(if_match=if_match),
        json=payload,
    )


def _persona_row(db_session, id_persona: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id_persona, nombre, version_registro,
                   op_id_ultima_modificacion, id_instalacion_ultima_modificacion
            FROM persona WHERE id_persona = :id_persona
            """
        ),
        {"id_persona": id_persona},
    ).mappings().one()


def _doc_count(db_session, id_persona: int) -> int:
    return db_session.execute(
        text("SELECT COUNT(*) FROM persona_documento WHERE id_persona=:id_persona AND deleted_at IS NULL"),
        {"id_persona": id_persona},
    ).scalar_one()


def test_datos_principales_actualiza_solo_base_respuesta_completa_y_auditoria(client, db_session) -> None:
    id_persona = _crear_persona(client)

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1, nombre="Augusta Ada"),
            "documento_identidad": None,
            "identificacion_fiscal": None,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["nombre"] == "Augusta Ada"
    assert data["version_registro"] == 2
    assert data["documentos"] == []
    assert data["domicilios"] == []
    assert data["contactos"] == []
    assert data["relaciones"] == []
    assert data["representaciones_poder"] == []

    row = _persona_row(db_session, id_persona)
    assert row["version_registro"] == 2
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_ultima_modificacion"] is not None


def test_datos_principales_actualiza_persona_dni_y_cuit(client, db_session) -> None:
    id_persona = _crear_persona(client)
    dni = _crear_documento(client, id_persona, "DNI", _numero(), principal=True)
    cuit = _crear_documento(client, id_persona, "CUIT", _cuit(), principal=False)
    nuevo_dni = _numero()
    nuevo_cuit = _cuit()

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1, nombre="Ada Byron"),
            "documento_identidad": {
                "id_persona_documento": dni["id_persona_documento"],
                "tipo_documento": "DNI",
                "numero_documento": nuevo_dni,
                "pais_emision": None,
                "es_principal": True,
                "version_registro": 1,
            },
            "identificacion_fiscal": {
                "id_persona_documento": cuit["id_persona_documento"],
                "tipo_documento": "CUIT",
                "numero_documento": nuevo_cuit,
                "pais_emision": None,
                "es_principal": False,
                "version_registro": 1,
            },
        },
    )

    assert response.status_code == 200
    documentos = response.json()["data"]["documentos"]
    assert {doc["numero_documento"] for doc in documentos} >= {nuevo_dni, nuevo_cuit}
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada Byron"


def test_datos_principales_crea_dni_y_cuit_si_no_existen(client, db_session) -> None:
    id_persona = _crear_persona(client)
    dni = _numero()
    cuit = _cuit()

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1),
            "documento_identidad": {
                "tipo_documento": "DNI",
                "numero_documento": dni,
                "pais_emision": None,
                "es_principal": True,
            },
            "identificacion_fiscal": {
                "tipo_documento": "CUIT",
                "numero_documento": cuit,
                "pais_emision": None,
                "es_principal": False,
            },
        },
    )

    assert response.status_code == 200
    assert _doc_count(db_session, id_persona) == 2
    assert {doc["numero_documento"] for doc in response.json()["data"]["documentos"]} == {dni, cuit}



def test_datos_principales_crea_solo_dni_si_no_existe(client, db_session) -> None:
    id_persona = _crear_persona(client)
    dni = _numero()

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1),
            "documento_identidad": {
                "tipo_documento": "DNI",
                "numero_documento": dni,
                "pais_emision": None,
                "es_principal": True,
            },
            "identificacion_fiscal": None,
        },
    )

    assert response.status_code == 200
    assert _doc_count(db_session, id_persona) == 1
    assert response.json()["data"]["documentos"][0]["numero_documento"] == dni


def test_datos_principales_crea_solo_cuit_si_no_existe(client, db_session) -> None:
    id_persona = _crear_persona(client)
    cuit = _cuit()

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1),
            "documento_identidad": None,
            "identificacion_fiscal": {
                "tipo_documento": "CUIT",
                "numero_documento": cuit,
                "pais_emision": None,
                "es_principal": False,
            },
        },
    )

    assert response.status_code == 200
    assert _doc_count(db_session, id_persona) == 1
    assert response.json()["data"]["documentos"][0]["numero_documento"] == cuit

def test_datos_principales_requiere_if_match_version(client) -> None:
    id_persona = _crear_persona(client)

    response = _put_datos(
        client,
        id_persona,
        {"persona": _payload_persona(1), "documento_identidad": None, "identificacion_fiscal": None},
        if_match=None,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_datos_principales_rechaza_if_match_distinto_del_body_sin_escribir(client, db_session) -> None:
    id_persona = _crear_persona(client)

    response = _put_datos(
        client,
        id_persona,
        {"persona": _payload_persona(1, nombre="No Guardar"), "documento_identidad": None, "identificacion_fiscal": None},
        if_match=2,
    )

    assert response.status_code == 409
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada"


def test_datos_principales_version_persona_incorrecta_hace_rollback(client, db_session) -> None:
    id_persona = _crear_persona(client)
    db_session.execute(text("UPDATE persona SET version_registro=2 WHERE id_persona=:id"), {"id": id_persona})
    db_session.flush()

    response = _put_datos(
        client,
        id_persona,
        {"persona": _payload_persona(1, nombre="No Guardar"), "documento_identidad": None, "identificacion_fiscal": None},
        if_match=1,
    )

    assert response.status_code == 409
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada"


def test_datos_principales_version_documento_incorrecta_hace_rollback(client, db_session) -> None:
    id_persona = _crear_persona(client)
    dni = _crear_documento(client, id_persona, "DNI", _numero(), principal=True)

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1, nombre="No Guardar"),
            "documento_identidad": {
                "id_persona_documento": dni["id_persona_documento"],
                "tipo_documento": "DNI",
                "numero_documento": _numero(),
                "pais_emision": None,
                "es_principal": True,
                "version_registro": 99,
            },
            "identificacion_fiscal": None,
        },
    )

    assert response.status_code == 409
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada"


def test_datos_principales_documento_duplicado_activo_hace_rollback(client, db_session) -> None:
    id_persona = _crear_persona(client)
    _crear_documento(client, id_persona, "DNI", _numero(), principal=True)

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1, nombre="No Guardar"),
            "documento_identidad": {
                "tipo_documento": "DNI",
                "numero_documento": _numero(),
                "pais_emision": None,
                "es_principal": True,
            },
            "identificacion_fiscal": None,
        },
    )

    assert response.status_code == 400
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada"
    assert _doc_count(db_session, id_persona) == 1


def test_datos_principales_numero_vacio_en_documento_existente_hace_rollback(client, db_session) -> None:
    id_persona = _crear_persona(client)
    dni = _crear_documento(client, id_persona, "DNI", _numero(), principal=True)

    response = _put_datos(
        client,
        id_persona,
        {
            "persona": _payload_persona(1, nombre="No Guardar"),
            "documento_identidad": {
                "id_persona_documento": dni["id_persona_documento"],
                "tipo_documento": "DNI",
                "numero_documento": " ",
                "pais_emision": None,
                "es_principal": True,
                "version_registro": 1,
            },
            "identificacion_fiscal": None,
        },
    )

    assert response.status_code == 400
    assert _persona_row(db_session, id_persona)["nombre"] == "Ada"
