from fastapi import FastAPI

from app.api.routers.comercial_router import router as comercial_router
from app.api.routers.edificaciones_router import router as edificaciones_router
from app.api.routers.inmuebles_router import router as inmuebles_router
from app.api.routers.desarrollos_router import router as desarrollos_router
from app.api.routers.health_router import router as health_router
from app.api.routers.personas_router import router as personas_router
from app.api.routers.servicios_router import router as servicios_router
from app.config.settings import get_settings


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
        "name": "health",
        "description": "Endpoints tecnicos de salud del servicio.",
    },
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_tags=OPENAPI_TAGS,
)

app.include_router(health_router)
app.include_router(desarrollos_router)
app.include_router(edificaciones_router)
app.include_router(inmuebles_router)
app.include_router(personas_router)
app.include_router(servicios_router)
app.include_router(comercial_router)
