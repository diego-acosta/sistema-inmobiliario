import asyncio
from unittest.mock import patch

import pytest
from app.api.local_command_context import (
    LocalCommandHeaderError,
    _get_local_context_settings,
)
from app.application.common.local_command_context import (
    InstallationAssertionMismatch,
    LocalCommandContextTechnicalError,
    LocalInstallationUnavailable,
    OperationalBranchScopeDenied,
)
from app.application.common.local_installation import LocalInstallationNotConfigured
from app.main import (
    local_command_context_conflict_handler,
    local_command_context_technical_error_handler,
    local_command_header_error_handler,
    local_command_scope_denied_handler,
    local_installation_unavailable_handler,
)
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/test", "headers": []})


@pytest.mark.parametrize(
    ("handler", "error", "status", "code"),
    [
        (
            local_command_header_error_handler,
            LocalCommandHeaderError(header_name="X-Op-Id", reason="is required"),
            400,
            "LOCAL_COMMAND_HEADER_INVALID",
        ),
        (
            local_command_scope_denied_handler,
            OperationalBranchScopeDenied("dato interno"),
            403,
            "OPERATIONAL_BRANCH_SCOPE_DENIED",
        ),
        (
            local_command_context_conflict_handler,
            InstallationAssertionMismatch("ids internos"),
            409,
            "INSTALLATION_CONTEXT_MISMATCH",
        ),
        (
            local_installation_unavailable_handler,
            LocalInstallationUnavailable("configuración secreta"),
            503,
            "LOCAL_INSTALLATION_UNAVAILABLE",
        ),
        (
            local_command_context_technical_error_handler,
            LocalCommandContextTechnicalError("SQL secreto"),
            500,
            "LOCAL_COMMAND_CONTEXT_TECHNICAL_ERROR",
        ),
    ],
)
def test_mapeos_a0_b0_usan_error_response_sin_detail(
    handler, error, status, code
):
    response = asyncio.run(handler(_request(), error))
    body = response.body.decode()

    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    assert f'"error_code":"{code}"' in body
    assert '"error_message":' in body
    assert '"details":' in body
    assert '"detail":' not in body
    assert "secreto" not in body


def test_configuracion_local_invalida_se_convierte_en_error_sanitizado():
    with patch(
        "app.api.local_command_context.get_settings",
        side_effect=LocalInstallationNotConfigured("LOCAL_INSTALLATION_CODE=secreto"),
    ), pytest.raises(LocalInstallationUnavailable) as error:
        _get_local_context_settings()

    assert str(error.value) == "La instalación local no está disponible."
