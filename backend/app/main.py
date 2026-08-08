from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers.administrativo_router import router as administrativo_router
from app.api.routers.comercial_router import router as comercial_router
from app.api.routers.edificaciones_router import router as edificaciones_router
from app.api.routers.inmuebles_router import router as inmuebles_router
from app.api.routers.desarrollos_router import router as desarrollos_router
from app.api.routers.health_router import router as health_router
from app.api.routers.personas_router import router as personas_router
from app.api.routers.servicios_router import router as servicios_router
from app.api.routers.locativo_router import router as locativo_router
from app.api.routers.operativo_router import router as operativo_router
from app.api.routers.financiero_router import router as financiero_router
from app.config.settings import get_settings
from app.application.administrativo.authentication import InvalidSession, SessionTechnicalError
from app.api.schemas.administrativo import ErrorResponse


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
