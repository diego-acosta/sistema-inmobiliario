from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.locativo import (
    ContratoAlquilerCreateData,
    ContratoAlquilerCreateRequest,
    ContratoAlquilerCreateResponse,
    ErrorResponse,
)
from app.application.common.commands import CommandContext
from app.application.locativo.commands.create_contrato_alquiler import (
    CreateContratoAlquilerCommand,
    CreateContratoAlquilerObjetoCommand,
    CreateContratoAlquilerParticipacionCommand,
)
from app.application.locativo.services.create_contrato_alquiler_service import (
    CreateContratoAlquilerService,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
)


router = APIRouter(tags=["Locativo"])


@dataclass(slots=True)
class LocativoCommandContext(CommandContext):
    id_instalacion: int | None = None
    op_id: UUID | None = None


@router.post(
    "/api/v1/contratos-alquiler",
    status_code=201,
    response_model=ContratoAlquilerCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_contrato_alquiler(
    request: ContratoAlquilerCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ContratoAlquilerCreateResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            id_instalacion = None

    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            op_id = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateContratoAlquilerCommand(
        context=context,
        codigo_contrato=request.codigo_contrato,
        fecha_contrato=request.fecha_contrato,
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin,
        canon_inicial=request.canon_inicial,
        moneda=request.moneda,
        observaciones=request.observaciones,
        objetos=[
            CreateContratoAlquilerObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
        participaciones=[
            CreateContratoAlquilerParticipacionCommand(
                id_persona=item.id_persona,
                id_rol_participacion=item.id_rol_participacion,
                fecha_desde=item.fecha_desde,
                fecha_hasta=item.fecha_hasta,
                observaciones=item.observaciones,
            )
            for item in request.participaciones
        ],
    )

    repository = LocativoRepository(db)
    service = CreateContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in (
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
                "NOT_FOUND_PERSONA",
                "NOT_FOUND_ROL_PARTICIPACION",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El objeto inmobiliario, la persona o el rol indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerCreateResponse(data=ContratoAlquilerCreateData(**result.data))
