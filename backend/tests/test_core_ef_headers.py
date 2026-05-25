import pytest
from app.api.core_ef_headers import CoreEFHeaderValidationError, parse_core_ef_headers


def test_parse_core_ef_headers_validos() -> None:
    headers = parse_core_ef_headers(
        x_op_id="550e8400-e29b-41d4-a716-446655440000",
        x_usuario_id="10",
        x_sucursal_id="20",
        x_instalacion_id="30",
        if_match_version="7",
        require_if_match_version=True,
    )

    assert str(headers.x_op_id) == "550e8400-e29b-41d4-a716-446655440000"
    assert headers.x_usuario_id == 10
    assert headers.x_sucursal_id == 20
    assert headers.x_instalacion_id == 30
    assert headers.if_match_version == 7


def test_parse_core_ef_headers_x_op_id_invalido() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="invalido",
            x_usuario_id="10",
            x_sucursal_id="20",
            x_instalacion_id="30",
        )

    assert exc_info.value.header_name == "X-Op-Id"
    assert exc_info.value.message == "Header inválido: X-Op-Id."


def test_parse_core_ef_headers_x_usuario_id_faltante() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="550e8400-e29b-41d4-a716-446655440000",
            x_usuario_id=None,
            x_sucursal_id="20",
            x_instalacion_id="30",
        )

    assert exc_info.value.header_name == "X-Usuario-Id"
    assert exc_info.value.message == "Header requerido faltante: X-Usuario-Id."


def test_parse_core_ef_headers_x_sucursal_id_faltante() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="550e8400-e29b-41d4-a716-446655440000",
            x_usuario_id="10",
            x_sucursal_id=None,
            x_instalacion_id="30",
        )

    assert exc_info.value.header_name == "X-Sucursal-Id"
    assert exc_info.value.message == "Header requerido faltante: X-Sucursal-Id."


def test_parse_core_ef_headers_x_instalacion_id_faltante() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="550e8400-e29b-41d4-a716-446655440000",
            x_usuario_id="10",
            x_sucursal_id="20",
            x_instalacion_id=None,
        )

    assert exc_info.value.header_name == "X-Instalacion-Id"
    assert exc_info.value.message == "Header requerido faltante: X-Instalacion-Id."


def test_parse_core_ef_headers_if_match_faltante_cuando_requerido() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="550e8400-e29b-41d4-a716-446655440000",
            x_usuario_id="10",
            x_sucursal_id="20",
            x_instalacion_id="30",
            if_match_version=None,
            require_if_match_version=True,
        )

    assert exc_info.value.header_name == "If-Match-Version"
    assert exc_info.value.message == "Header requerido faltante: If-Match-Version."


def test_parse_core_ef_headers_if_match_ausente_cuando_opcional() -> None:
    headers = parse_core_ef_headers(
        x_op_id="550e8400-e29b-41d4-a716-446655440000",
        x_usuario_id="10",
        x_sucursal_id="20",
        x_instalacion_id="30",
        if_match_version=None,
        require_if_match_version=False,
    )

    assert headers.if_match_version is None


def test_parse_core_ef_headers_if_match_invalido() -> None:
    with pytest.raises(CoreEFHeaderValidationError) as exc_info:
        parse_core_ef_headers(
            x_op_id="550e8400-e29b-41d4-a716-446655440000",
            x_usuario_id="10",
            x_sucursal_id="20",
            x_instalacion_id="30",
            if_match_version="abc",
            require_if_match_version=True,
        )

    assert exc_info.value.header_name == "If-Match-Version"
    assert exc_info.value.message == "Header inválido: If-Match-Version."
