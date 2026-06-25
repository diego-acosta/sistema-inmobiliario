from __future__ import annotations

from app.api_client import ApiResult
from app.pages.inmuebles_page import InmuebleEditView


class FakeApi:
    def __init__(self, *, datos=None, fail_create: bool = False) -> None:
        self.datos = datos or []
        self.fail_create = fail_create
        self.updated = []
        self.created = []
        self.basic_updates = []

    def get_inmueble_detalle_integral(self, id_inmueble):
        return ApiResult(
            True,
            data={
                "id_inmueble": id_inmueble,
                "codigo_inmueble": "INM-1",
                "nombre_inmueble": "Casa",
                "estado_administrativo": "ACTIVO",
                "estado_juridico": "REGULAR",
                "version_registro": 7,
            },
        )

    def listar_datos_catastrales_registrales_inmueble(self, id_inmueble):
        return ApiResult(True, data=self.datos)

    def actualizar_inmueble(self, id_inmueble, payload, if_match_version, op_id=None):
        self.basic_updates.append((id_inmueble, payload, if_match_version, op_id))
        return ApiResult(True, data={})

    def actualizar_dato_catastral_registral_inmueble(
        self,
        id_inmueble,
        id_dato_catastral_registral,
        payload,
        if_match_version,
        op_id=None,
    ):
        self.updated.append(
            (id_inmueble, id_dato_catastral_registral, payload, if_match_version, op_id)
        )
        return ApiResult(True, data={})

    def crear_dato_catastral_registral_inmueble(self, id_inmueble, payload, op_id=None):
        self.created.append((id_inmueble, payload, op_id))
        if self.fail_create:
            return ApiResult(False, error_message="falló creación catastral")
        return ApiResult(True, data={"id_dato_catastral_registral": 99})


def _build_view(api: FakeApi) -> InmuebleEditView:
    view = InmuebleEditView(api, lambda *args, **kwargs: None, 1)
    view.build()
    return view


def test_edicion_con_dato_existente_actualiza_con_version() -> None:
    api = FakeApi(
        datos=[
            {
                "id_dato_catastral_registral": 10,
                "manzana": "M1",
                "lote": "L1",
                "partida_inmobiliaria": "P1",
                "estado_dato": "ACTIVO",
                "version_registro": 3,
            }
        ]
    )
    view = _build_view(api)

    assert view.catastral_fields["manzana"].value == "M1"
    view.catastral_fields["lote"].value = "L2"
    view._save(None)

    assert api.created == []
    assert len(api.updated) == 1
    _, id_dato, payload, if_match_version, op_id = api.updated[0]
    assert id_dato == 10
    assert payload == {"lote": "L2"}
    assert if_match_version == 3
    assert op_id


def test_edicion_sin_dato_crea_catastral_sin_version() -> None:
    api = FakeApi(datos=[])
    view = _build_view(api)

    assert view.dato is None
    assert view.catastral_fields["manzana"].disabled is False
    view.catastral_fields["manzana"].value = "M2"
    view.catastral_fields["lote"].value = "L3"
    view.catastral_fields["partida_inmobiliaria"].value = "P2"
    view._save(None)

    assert api.updated == []
    assert len(api.created) == 1
    _, payload, op_id = api.created[0]
    assert payload["manzana"] == "M2"
    assert payload["lote"] == "L3"
    assert payload["partida_inmobiliaria"] == "P2"
    assert payload["estado_dato"] == "ACTIVO"
    assert op_id


def test_edicion_sin_dato_y_catastral_vacio_no_crea_y_guarda_basicos() -> None:
    api = FakeApi(datos=[])
    view = _build_view(api)

    view.nombre_inmueble.value = "Casa actualizada"
    view._save(None)

    assert api.created == []
    assert api.updated == []
    assert len(api.basic_updates) == 1
    assert api.basic_updates[0][1]["nombre_inmueble"] == "Casa actualizada"


def test_error_al_crear_dato_catastral_muestra_mensaje_claro() -> None:
    api = FakeApi(datos=[], fail_create=True)
    view = _build_view(api)

    view.catastral_fields["manzana"].value = "M3"
    view._save(None)

    assert len(api.created) == 1
    assert view.message.visible is True
    assert "crear datos catastrales/registrales" in view.message.value
    assert "falló creación catastral" in view.message.value
