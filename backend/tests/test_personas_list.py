from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(
    client,
    *,
    nombre: str,
    apellido: str,
    razon_social: str | None = None,
    tipo_persona: str = "FISICA",
    estado_persona: str = "ACTIVA",
) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": tipo_persona,
            "nombre": nombre,
            "apellido": apellido,
            "razon_social": razon_social,
            "fecha_nacimiento": "1990-01-01",
            "estado_persona": estado_persona,
            "observaciones": "persona para listado UI",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _set_cuit(db_session, id_persona: int, cuit_cuil: str) -> None:
    db_session.execute(
        text(
            """
            UPDATE persona
            SET cuit_cuil = :cuit_cuil
            WHERE id_persona = :id_persona
            """
        ),
        {"id_persona": id_persona, "cuit_cuil": cuit_cuil},
    )


def test_list_personas_lista_activas_y_excluye_deleted_at(client, db_session) -> None:
    activo = _crear_persona(client, nombre="UiListaActivo", apellido="MarkerDeleted")
    eliminado = _crear_persona(client, nombre="UiListaEliminado", apellido="MarkerDeleted")
    db_session.execute(
        text("UPDATE persona SET deleted_at = created_at WHERE id_persona = :id"),
        {"id": eliminado},
    )

    response = client.get("/api/v1/personas", params={"q": "MarkerDeleted"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["id_persona"] for item in data["items"]] == [activo]


def test_list_personas_busca_por_nombre(client) -> None:
    id_persona = _crear_persona(client, nombre="NombreUnicoUi", apellido="Perez")

    response = client.get("/api/v1/personas", params={"q": "NombreUnicoUi"})

    assert response.status_code == 200
    assert {item["id_persona"] for item in response.json()["data"]["items"]} == {
        id_persona
    }


def test_list_personas_busca_por_apellido(client) -> None:
    id_persona = _crear_persona(client, nombre="Ana", apellido="ApellidoUnicoUi")

    response = client.get("/api/v1/personas", params={"q": "ApellidoUnicoUi"})

    assert response.status_code == 200
    assert {item["id_persona"] for item in response.json()["data"]["items"]} == {
        id_persona
    }


def test_list_personas_busca_por_razon_social(client) -> None:
    id_persona = _crear_persona(
        client,
        nombre="",
        apellido="",
        razon_social="Razon Social UI Busqueda SA",
        tipo_persona="JURIDICA",
    )

    response = client.get("/api/v1/personas", params={"q": "Busqueda SA"})

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["id_persona"] == id_persona
    assert item["display_name"] == "Razon Social UI Busqueda SA"


def test_list_personas_busca_por_cuit_cuil(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="CuitUi", apellido="Persona")
    _set_cuit(db_session, id_persona, "20-99999999-1")

    response = client.get("/api/v1/personas", params={"q": "99999999"})

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["id_persona"] == id_persona
    assert item["cuit_cuil"] == "20-99999999-1"


def test_list_personas_busca_por_numero_documento(client) -> None:
    id_persona = _crear_persona(client, nombre="DocumentoUi", apellido="Persona")
    doc_response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": "44556677",
            "pais_emision": "AR",
            "es_principal": False,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    assert doc_response.status_code == 201

    response = client.get("/api/v1/personas", params={"numero_documento": "44556677"})

    assert response.status_code == 200
    assert [item["id_persona"] for item in response.json()["data"]["items"]] == [
        id_persona
    ]


def test_list_personas_incluye_documento_principal_si_existe(client) -> None:
    id_persona = _crear_persona(client, nombre="DocPrincipalUi", apellido="Persona")
    doc_response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": "11223344",
            "pais_emision": "AR",
            "es_principal": True,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    assert doc_response.status_code == 201
    id_documento = doc_response.json()["data"]["id_persona_documento"]

    response = client.get("/api/v1/personas", params={"q": "DocPrincipalUi"})

    documento = response.json()["data"]["items"][0]["documento_principal"]
    assert documento == {
        "id_persona_documento": id_documento,
        "tipo_documento_persona": "DNI",
        "numero_documento": "11223344",
        "pais_emision": "AR",
    }


def test_list_personas_incluye_contacto_principal_si_existe(client) -> None:
    id_persona = _crear_persona(client, nombre="ContactoPrincipalUi", apellido="Persona")
    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "principal-ui@example.com",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    assert contacto_response.status_code == 201
    id_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    response = client.get("/api/v1/personas", params={"q": "principal-ui@example.com"})

    contacto = response.json()["data"]["items"][0]["contacto_principal"]
    assert contacto == {
        "id_persona_contacto": id_contacto,
        "tipo_contacto": "EMAIL",
        "valor_contacto": "principal-ui@example.com",
    }


def test_list_personas_paginacion_limit_offset(client) -> None:
    ids = [
        _crear_persona(client, nombre="PaginacionUi", apellido="A"),
        _crear_persona(client, nombre="PaginacionUi", apellido="B"),
        _crear_persona(client, nombre="PaginacionUi", apellido="C"),
    ]

    response = client.get(
        "/api/v1/personas",
        params={"q": "PaginacionUi", "limit": 1, "offset": 1},
    )

    data = response.json()["data"]
    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert [item["id_persona"] for item in data["items"]] == [ids[1]]


def test_list_personas_filtra_tipo_persona(client) -> None:
    juridica = _crear_persona(
        client,
        nombre="",
        apellido="",
        razon_social="Filtro Tipo Persona UI SRL",
        tipo_persona="JURIDICA",
    )
    _crear_persona(client, nombre="Filtro Tipo Persona UI", apellido="Fisica")

    response = client.get(
        "/api/v1/personas",
        params={"q": "Filtro Tipo Persona UI", "tipo_persona": "JURIDICA"},
    )

    assert [item["id_persona"] for item in response.json()["data"]["items"]] == [
        juridica
    ]


def test_list_personas_filtra_estado_persona(client) -> None:
    inactiva = _crear_persona(
        client,
        nombre="FiltroEstadoUi",
        apellido="Inactiva",
        estado_persona="INACTIVA",
    )
    _crear_persona(client, nombre="FiltroEstadoUi", apellido="Activa")

    response = client.get(
        "/api/v1/personas",
        params={"q": "FiltroEstadoUi", "estado_persona": "INACTIVA"},
    )

    assert [item["id_persona"] for item in response.json()["data"]["items"]] == [
        inactiva
    ]


def test_list_personas_sin_resultados_devuelve_lista_vacia(client) -> None:
    response = client.get("/api/v1/personas", params={"q": "NoExistePersonaUi999"})

    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }


def test_list_personas_no_crea_ni_modifica_entidades(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="ReadOnlyUi", apellido="Persona")
    client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": "99887766",
            "pais_emision": "AR",
            "es_principal": True,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "readonly-ui@example.com",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle ReadOnly 123",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    counts_before = _counts(db_session)

    response = client.get("/api/v1/personas", params={"q": "ReadOnlyUi"})

    assert response.status_code == 200
    assert _counts(db_session) == counts_before


def _counts(db_session) -> dict[str, int]:
    tables = [
        "persona",
        "persona_documento",
        "persona_contacto",
        "persona_domicilio",
        "relacion_persona_rol",
    ]
    return {
        table: db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in tables
    }
