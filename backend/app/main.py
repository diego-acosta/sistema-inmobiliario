from app.api.local_command_context import LocalCommandHeaderError
from app.api.routers.administrativo_router import router as administrativo_router
from app.api.routers.comercial_router import router as comercial_router
from app.api.routers.desarrollos_router import router as desarrollos_router
from app.api.routers.edificaciones_router import router as edificaciones_router
from app.api.routers.financiero_router import router as financiero_router
from app.api.routers.health_router import router as health_router
from app.api.routers.inmuebles_router import router as inmuebles_router
from app.api.routers.locativo_router import router as locativo_router
from app.api.routers.operativo_router import router as operativo_router
from app.api.routers.personas_router import router as personas_router
from app.api.routers.servicios_router import router as servicios_router
from app.api.schemas.administrativo import ErrorResponse
from app.application.administrativo.authentication import (
    InvalidSession,
    SessionTechnicalError,
)
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationTechnicalError,
    InsufficientAdministrativeAuthorization,
)
from app.application.common.local_command_context import (
    HumanPrincipalRequired,
    InstallationAssertionMismatch,
    InstallationBranchMismatch,
    LocalCommandContextTechnicalError,
    LocalInstallationUnavailable,
    OperationalBranchNotEligible,
    OperationalBranchNotFound,
    OperationalBranchScopeDenied,
)
from app.config.settings import get_settings
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

settings = get_settings()

OPENAPI_TAGS = [
    {
        "name": "Personas",
        "description": "Dominio de personas: sujeto base, identificacion, domicilios, contactos, relaciones y representacion.",
    },
    {
        "name": "Inmobiliario",
        "description": "Dominio inmobiliario: desarrollos, inmuebles, unidades funcionales, edificaciones, servicios, disponibilidad y ocupacion.",
    },
    {
        "name": "Comercial",
        "description": "Dominio comercial: reservas de venta y operaciones del circuito de compraventa.",
    },
    {
        "name": "Locativo",
        "description": "Dominio locativo: contratos de alquiler, objetos locativos y participaciones.",
    },
    {
        "name": "Financiero",
        "description": "Dominio financiero: relaciones generadoras, obligaciones y movimientos.",
    },
    {
        "name": "Administrativo",
        "description": "Dominio administrativo: usuarios del sistema y soporte de administración.",
    },
    {
        "name": "Operativo",
        "description": "Dominio operativo: sucursales, instalaciones y operación física.",
    },
    {
        "name": "health",
        "description": "Endpoints tecnicos de salud del servicio.",
    },
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_tags=OPENAPI_TAGS,
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # #483 exige un query param requerido en OpenAPI sin exponer el `detail`
    # nativo. El resto de las rutas conserva el comportamiento vigente.
    calendario_path = "/api/v1/administrativo/configuracion/calendario-comercial"
    if request.method == "GET" and request.url.path == calendario_path:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message=(
                    "fecha_efectiva es obligatoria y debe usar el formato "
                    "YYYY-MM-DD."
                ),
                details={"field": "fecha_efectiva"},
            ).model_dump(),
            headers={"Cache-Control": "no-store"},
        )
    if request.method == "POST" and request.url.path == calendario_path:
        errors = exc.errors()
        fields = []
        for error in errors:
            location = error.get("loc", ())
            if len(location) >= 2 and location[0] in {"body", "header"}:
                field = str(location[-1])
                if field not in fields:
                    fields.append(field)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message="La solicitud de bootstrap contiene datos inválidos.",
                details={"fields": fields},
            ).model_dump(),
            headers={"Cache-Control": "no-store"},
        )
    if request.method == "PUT" and request.url.path == calendario_path:
        fields = []
        for error in exc.errors():
            location = error.get("loc", ())
            if len(location) >= 2 and location[0] in {"body", "header"}:
                field = str(location[-1])
                if field not in fields:
                    fields.append(field)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message=(
                    "La solicitud de programación contiene datos inválidos."
                ),
                details={"fields": fields},
            ).model_dump(),
            headers={"Cache-Control": "no-store"},
        )
    usuario_sucursal_path = request.url.path.strip("/").split("/")
    if (
        request.method == "POST"
        and len(usuario_sucursal_path) == 6
        and usuario_sucursal_path[:4]
        == ["api", "v1", "administrativo", "usuarios"]
        and usuario_sucursal_path[5] == "sucursales"
    ):
        fields = []
        for error in exc.errors():
            location = error.get("loc", ())
            if len(location) >= 2 and location[0] in {"body", "path"}:
                field = str(location[-1])
                if field not in fields:
                    fields.append(field)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message="La solicitud de asignación contiene datos inválidos.",
                details={"fields": fields},
            ).model_dump(),
            headers={"Cache-Control": "no-store"},
        )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(InvalidSession)
async def invalid_session_handler(_request: Request, _exc: InvalidSession) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=ErrorResponse(
            error_code="INVALID_SESSION",
            error_message="La sesión no es válida.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(SessionTechnicalError)
async def session_technical_error_handler(
    _request: Request, _exc: SessionTechnicalError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="SESSION_TECHNICAL_ERROR",
            error_message="No fue posible validar la sesión.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(InsufficientAdministrativeAuthorization)
async def insufficient_administrative_authorization_handler(
    _request: Request, _exc: InsufficientAdministrativeAuthorization
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            error_code="autorizacion_insuficiente",
            error_message=(
                "La autorización efectiva es insuficiente para ejecutar la operación."
            ),
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(AdministrativeAuthorizationTechnicalError)
async def administrative_authorization_technical_error_handler(
    _request: Request, _exc: AdministrativeAuthorizationTechnicalError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="inconsistencia_roles_permisos",
            error_message="No fue posible resolver la autorización administrativa.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(LocalCommandHeaderError)
async def local_command_header_error_handler(
    _request: Request, exc: LocalCommandHeaderError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code=exc.code,
            error_message="El contexto técnico contiene un header inválido.",
            details={"header": exc.header_name, "reason": exc.reason},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(OperationalBranchScopeDenied)
async def local_command_scope_denied_handler(
    _request: Request, exc: OperationalBranchScopeDenied
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            error_code=exc.code,
            error_message="El principal no posee alcance operativo suficiente.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(InstallationAssertionMismatch)
@app.exception_handler(InstallationBranchMismatch)
@app.exception_handler(OperationalBranchNotFound)
@app.exception_handler(OperationalBranchNotEligible)
async def local_command_context_conflict_handler(
    _request: Request, exc
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error_code=exc.code,
            error_message="El contexto operativo declarado es incompatible.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(LocalInstallationUnavailable)
async def local_installation_unavailable_handler(
    _request: Request, exc: LocalInstallationUnavailable
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error_code=exc.code,
            error_message="La instalación local no está disponible.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(LocalCommandContextTechnicalError)
@app.exception_handler(HumanPrincipalRequired)
async def local_command_context_technical_error_handler(
    _request: Request, exc: LocalCommandContextTechnicalError | HumanPrincipalRequired
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=exc.code,
            error_message="No fue posible validar el contexto local.",
            details={},
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )

app.include_router(health_router)
app.include_router(desarrollos_router)
app.include_router(edificaciones_router)
app.include_router(inmuebles_router)
app.include_router(personas_router)
app.include_router(servicios_router)
app.include_router(comercial_router)
app.include_router(locativo_router)
app.include_router(financiero_router)
app.include_router(administrativo_router)
app.include_router(operativo_router)
