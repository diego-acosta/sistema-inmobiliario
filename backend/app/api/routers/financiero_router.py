from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.financiero import (
    ConceptoFinancieroData,
    ConceptoFinancieroListData,
    ConceptoFinancieroListResponse,
    ErrorResponse,
    ObligacionFinancieraData,
    ObligacionFinancieraResponse,
    RelacionGeneradoraCreateRequest,
    RelacionGeneradoraData,
    RelacionGeneradoraListData,
    RelacionGeneradoraListResponse,
    RelacionGeneradoraResponse,
)
from app.application.common.commands import CommandContext
from app.application.financiero.commands.create_relacion_generadora import (
    CreateRelacionGeneradoraCommand,
)
from app.application.financiero.services.create_relacion_generadora_service import (
    CreateRelacionGeneradoraService,
)
from app.application.financiero.services.get_relacion_generadora_service import (
    GetRelacionGeneradoraService,
)
from app.application.financiero.services.get_obligacion_financiera_service import (
    GetObligacionFinancieraService,
)
from app.application.financiero.services.list_conceptos_financieros_service import (
    ListConceptosFinancierosService,
)
from app.application.financiero.services.list_relaciones_generadoras_service import (
    ListRelacionesGeneradorasService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)


router = APIRouter(tags=["Financiero"])


@dataclass(slots=True)
class FinancieroCommandContext(CommandContext):
    id_instalacion: int | None = None
    op_id: UUID | None = None


def _build_context(
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
) -> FinancieroCommandContext:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            pass
    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            pass

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

    return FinancieroCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )


@router.post(
    "/api/v1/financiero/relaciones-generadoras",
    status_code=201,
    response_model=RelacionGeneradoraResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_relacion_generadora(
    request: RelacionGeneradoraCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RelacionGeneradoraResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    command = CreateRelacionGeneradoraCommand(
        context=context,
        tipo_origen=request.tipo_origen,
        id_origen=request.id_origen,
        descripcion=request.descripcion,
    )

    repository = FinancieroRepository(db)
    service = CreateRelacionGeneradoraService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "TIPO_ORIGEN_INVALIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="APPLICATION_ERROR",
                    error_message="tipo_origen debe ser VENTA o CONTRATO_ALQUILER.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "NOT_FOUND_ORIGEN" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="El origen indicado no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo crear la relación generadora.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return RelacionGeneradoraResponse(data=RelacionGeneradoraData(**result.data))


@router.get(
    "/api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}",
    response_model=RelacionGeneradoraResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
def get_relacion_generadora(
    id_relacion_generadora: int,
    db: Session = Depends(get_db),
) -> RelacionGeneradoraResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetRelacionGeneradoraService(repository=repository)
    result = service.execute(id_relacion_generadora)

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La relación generadora indicada no existe.",
            ).model_dump(),
        )

    return RelacionGeneradoraResponse(data=RelacionGeneradoraData(**result.data))


@router.get(
    "/api/v1/financiero/relaciones-generadoras",
    response_model=RelacionGeneradoraListResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
def list_relaciones_generadoras(
    tipo_origen: str | None = Query(default=None),
    id_origen: int | None = Query(default=None),
    vigente: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RelacionGeneradoraListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListRelacionesGeneradorasService(repository=repository)

    try:
        result = service.execute(
            tipo_origen=tipo_origen,
            id_origen=id_origen,
            vigente=vigente,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    return RelacionGeneradoraListResponse(
        data=RelacionGeneradoraListData(
            items=[RelacionGeneradoraData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.get(
    "/api/v1/financiero/conceptos-financieros",
    response_model=ConceptoFinancieroListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_conceptos_financieros(
    estado: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConceptoFinancieroListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListConceptosFinancierosService(repository=repository)

    try:
        result = service.execute(estado=estado, limit=limit, offset=offset)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    return ConceptoFinancieroListResponse(
        data=ConceptoFinancieroListData(
            items=[ConceptoFinancieroData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.get(
    "/api/v1/financiero/obligaciones/{id_obligacion_financiera}",
    response_model=ObligacionFinancieraResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_obligacion_financiera(
    id_obligacion_financiera: int,
    db: Session = Depends(get_db),
) -> ObligacionFinancieraResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetObligacionFinancieraService(repository=repository)
    result = service.execute(id_obligacion_financiera)

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La obligación financiera indicada no existe.",
            ).model_dump(),
        )

    return ObligacionFinancieraResponse(
        data=ObligacionFinancieraData(**result.data)
    )
