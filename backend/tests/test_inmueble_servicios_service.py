from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.application.common.commands import CommandContext
from app.application.inmuebles.commands.create_inmueble_servicio import (
    CreateInmuebleServicioCommand,
)
from app.application.inmuebles.services.create_inmueble_servicio_service import (
    CreateInmuebleServicioService,
)


class _Context(CommandContext):
    __slots__ = ("id_instalacion", "op_id")

    def __init__(self) -> None:
        super().__init__(actor_id="1")
        self.id_instalacion = 1
        self.op_id = None


class _FakeDiag:
    constraint_name = "ux_inmueble_servicio_activo"


class _FakeUniqueViolation(Exception):
    diag = _FakeDiag()


class _RepositoryWithUniqueViolation:
    def inmueble_exists(self, id_inmueble: int) -> bool:
        return True

    def servicio_exists(self, id_servicio: int) -> bool:
        return True

    def inmueble_servicio_exists(self, id_inmueble: int, id_servicio: int) -> bool:
        return False

    def create_inmueble_servicio(self, payload):
        raise IntegrityError("INSERT INTO inmueble_servicio", {}, _FakeUniqueViolation())


def test_create_inmueble_servicio_traduce_unique_violation_a_error_de_negocio() -> None:
    service = CreateInmuebleServicioService(
        repository=_RepositoryWithUniqueViolation(),
        uuid_generator=lambda: UUID("550e8400-e29b-41d4-a716-446655440000"),
    )

    command = CreateInmuebleServicioCommand(
        context=_Context(),
        id_inmueble=10,
        id_servicio=20,
        estado="ACTIVO",
    )

    result = service.execute(command)

    assert result.success is False
    assert result.data is None
    assert result.errors == ["DUPLICATE_INMUEBLE_SERVICIO"]
