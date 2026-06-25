from __future__ import annotations

from app.api_client import ApiResult
from app.pages.inmuebles_page import InmuebleCreateForm


class FakeApi:
    def get_desarrollos(self):
        return ApiResult(True, data=[])


def test_clear_form_limpia_direccion_y_restaura_defaults() -> None:
    form = InmuebleCreateForm(FakeApi(), on_close=lambda: None, on_created=lambda: None)
    form.build()

    form.codigo_inmueble.value = "INM-1"
    form.nombre_inmueble.value = "Casa"
    form.calle.value = "San Martín"
    form.altura.value = "123 bis"
    form.superficie.value = "100"
    form.estado_administrativo.value = "INACTIVO"
    form.estado_juridico.value = "OBSERVADO"

    form._clear_form()

    assert form.codigo_inmueble.value == ""
    assert form.nombre_inmueble.value == ""
    assert form.calle.value == ""
    assert form.altura.value == ""
    assert form.superficie.value == ""
    assert form.estado_administrativo.value == "ACTIVO"
    assert form.estado_juridico.value == "REGULAR"
