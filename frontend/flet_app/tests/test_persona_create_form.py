from __future__ import annotations

from app.api_client import ApiResult
from app.pages.partes_list_page import PersonaCreateForm
from app.persona_alta_helpers import build_persona_payload


class FakeApi:
    def __init__(self, result: ApiResult) -> None:
        self.result = result
        self.payloads: list[dict] = []

    def crear_persona(self, payload, op_id=None):
        self.payloads.append(payload)
        return self.result


def test_build_persona_payload_arma_alta_valida_persona_fisica() -> None:
    payload = build_persona_payload(
        {
            "tipo_persona": "FISICA",
            "nombre": " Ada ",
            "apellido": " Lovelace ",
            "razon_social": "No aplica",
            "fecha_nacimiento": "1815-12-10",
            "estado_persona": "ACTIVA",
            "observaciones": " alta ",
        }
    )

    assert payload == {
        "tipo_persona": "FISICA",
        "nombre": "Ada",
        "apellido": "Lovelace",
        "razon_social": None,
        "fecha_nacimiento": "1815-12-10",
        "estado_persona": "ACTIVA",
        "observaciones": "alta",
    }


def test_build_persona_payload_arma_alta_valida_persona_juridica() -> None:
    payload = build_persona_payload(
        {
            "tipo_persona": "JURIDICA",
            "nombre": "No aplica",
            "apellido": "No aplica",
            "razon_social": " Demo Propiedades SA ",
            "fecha_nacimiento": "",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        }
    )

    assert payload == {
        "tipo_persona": "JURIDICA",
        "nombre": "",
        "apellido": "",
        "razon_social": "Demo Propiedades SA",
        "fecha_nacimiento": None,
        "estado_persona": "ACTIVA",
        "observaciones": None,
    }


def test_alta_exitosa_muestra_mensaje_claro_e_id_creado() -> None:
    api = FakeApi(ApiResult(True, data={"id_persona": 42}))
    form = PersonaCreateForm(api, on_close=lambda: None, on_created=lambda _: None)
    form.build()
    form.nombre.value = "Ada"
    form.apellido.value = "Lovelace"

    form._submit(None)

    assert api.payloads[0]["nombre"] == "Ada"
    assert form.message.value == "Persona creada correctamente. ID: 42"
    assert "{" not in form.message.value
    assert form.clear_button.text == "Nueva alta"


def test_error_backend_se_muestra_claro_sin_dict_crudo() -> None:
    api = FakeApi(ApiResult(False, error_message="HTTP 400 | VALIDATION_ERROR | Header requerido faltante: X-Op-Id. | header=X-Op-Id"))
    form = PersonaCreateForm(api, on_close=lambda: None, on_created=lambda _: None)
    form.build()
    form.nombre.value = "Ada"
    form.apellido.value = "Lovelace"

    form._submit(None)

    assert "Header requerido faltante" in form.message.value
    assert "{" not in form.message.value
    assert "}" not in form.message.value


def test_limpiar_nueva_alta_resetea_formulario() -> None:
    form = PersonaCreateForm(FakeApi(ApiResult(True, data={"id_persona": 1})), on_close=lambda: None, on_created=lambda _: None)
    form.build()
    form.tipo_persona.value = "JURIDICA"
    form.nombre.value = "Ada"
    form.apellido.value = "Lovelace"
    form.razon_social.value = "Demo SA"
    form.fecha_nacimiento.value = "2020-01-01"
    form.estado_persona.value = "INACTIVA"
    form.observaciones.value = "Obs"
    form.message.value = "Persona creada correctamente. ID: 1"
    form.clear_button.text = "Nueva alta"

    form._clear_form()

    assert form.tipo_persona.value == "FISICA"
    assert form.nombre.value == ""
    assert form.apellido.value == ""
    assert form.razon_social.value == ""
    assert form.fecha_nacimiento.value == ""
    assert form.estado_persona.value == "ACTIVA"
    assert form.observaciones.value == ""
    assert form.message.value == ""
    assert form.clear_button.text == "Limpiar"


class DummyControl:
    def __init__(self, mounted: bool) -> None:
        self.page = object() if mounted else None
        self.updated = 0

    def update(self) -> None:
        self.updated += 1


def test_set_message_actualiza_estado_y_no_rompe_sin_montar() -> None:
    form = PersonaCreateForm(
        FakeApi(ApiResult(True)),
        on_close=lambda: None,
        on_created=lambda _: None,
    )
    form.build()

    form._set_message("Error claro", is_error=True)

    assert form.message.value == "Error claro"
    assert form.message.color is not None


def test_safe_update_intenta_refrescar_solo_controles_montados() -> None:
    form = PersonaCreateForm(
        FakeApi(ApiResult(True)),
        on_close=lambda: None,
        on_created=lambda _: None,
    )
    mounted = DummyControl(mounted=True)
    unmounted = DummyControl(mounted=False)

    form._safe_update(mounted, unmounted)

    assert mounted.updated == 1
    assert unmounted.updated == 0
