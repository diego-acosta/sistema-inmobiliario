from app.api_client import ApiResult
from app.pages.inmuebles_page import InmueblesListView


class FakeInmueblesApi:
    def __init__(self, *, total: int = 45) -> None:
        self.total = total
        self.calls: list[dict] = []

    def get_inmuebles(self, **kwargs):
        self.calls.append(kwargs)
        limit = kwargs["limit"]
        offset = kwargs["offset"]
        count = max(0, min(limit, self.total - offset))
        items = [
            {
                "id_inmueble": offset + index + 1,
                "codigo_inmueble": f"INM-{offset + index + 1:03d}",
                "nombre_inmueble": f"Inmueble {offset + index + 1}",
                "estado_administrativo": "ACTIVO",
                "estado_juridico": "REGULAR",
                "cantidad_unidades_funcionales": 0,
            }
            for index in range(count)
        ]
        return ApiResult(
            True,
            data={
                "data": items,
                "items": items,
                "total": self.total,
                "limit": limit,
                "offset": offset,
            },
        )


def _flatten(control):
    yield control
    for child in getattr(control, "controls", []) or []:
        yield from _flatten(child)
    content = getattr(control, "content", None)
    if content is not None:
        yield from _flatten(content)


def _button(view: InmueblesListView, text: str):
    for control in _flatten(view.results):
        if getattr(control, "text", None) == text and hasattr(control, "disabled"):
            return control
    raise AssertionError(f"No se encontro el boton {text!r}")


def _has_text(view: InmueblesListView, value: str) -> bool:
    return any(getattr(control, "value", None) == value for control in _flatten(view.results))


def test_inmuebles_paginacion_primera_pagina_total_mayor_al_limite() -> None:
    api = FakeInmueblesApi(total=45)
    view = InmueblesListView(api, lambda *args, **kwargs: None)

    view._load()

    assert api.calls[-1]["limit"] == 20
    assert api.calls[-1]["offset"] == 0
    assert _has_text(view, "1-20 de 45")
    assert _button(view, "Siguiente").disabled is False
    assert _button(view, "Anterior").disabled is True


def test_inmuebles_paginacion_siguiente_usa_offset_y_habilita_anterior() -> None:
    api = FakeInmueblesApi(total=45)
    view = InmueblesListView(api, lambda *args, **kwargs: None)
    view._load()

    view._next(None)

    assert api.calls[-1]["offset"] == 20
    assert _has_text(view, "21-40 de 45")
    assert _button(view, "Anterior").disabled is False
    assert _button(view, "Siguiente").disabled is False


def test_inmuebles_paginacion_ultima_pagina_deshabilita_siguiente() -> None:
    api = FakeInmueblesApi(total=45)
    view = InmueblesListView(api, lambda *args, **kwargs: None)
    view.offset = 40

    view._load()

    assert _has_text(view, "41-45 de 45")
    assert _button(view, "Anterior").disabled is False
    assert _button(view, "Siguiente").disabled is True


def test_inmuebles_paginacion_busqueda_conserva_q_y_total_filtrado() -> None:
    api = FakeInmueblesApi(total=33)
    view = InmueblesListView(api, lambda *args, **kwargs: None)
    view.q.value = "centro"
    view.offset = 20

    view._load()

    assert api.calls[-1]["q"] == "centro"
    assert api.calls[-1]["offset"] == 20
    assert _has_text(view, "21-33 de 33")
    assert _button(view, "Siguiente").disabled is True
