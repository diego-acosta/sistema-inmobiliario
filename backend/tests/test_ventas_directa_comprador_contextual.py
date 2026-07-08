from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from app.application.comercial.commands.confirm_venta_directa_completa import (
    ConfirmVentaDirectaCompletaCommand,
    ConfirmVentaDirectaCompletaCompradorInput,
    ConfirmVentaDirectaCompletaCondicionesComercialesInput,
    ConfirmVentaDirectaCompletaConfirmacionInput,
    ConfirmVentaDirectaCompletaDatosPersonaInput,
    ConfirmVentaDirectaCompletaDocumentoPersonaInput,
    ConfirmVentaDirectaCompletaGenerarVentaInput,
    ConfirmVentaDirectaCompletaObjetoInput,
    ConfirmVentaDirectaCompletaPlanPagoV2Input,
)
from app.application.comercial.services.confirm_venta_directa_completa_service import (
    ConfirmVentaDirectaCompletaService,
)


OP_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_OP_ID = UUID("22222222-2222-2222-2222-222222222222")
_DEFAULT_DOCUMENTO = object()


class FakeDb:
    def in_transaction(self) -> bool:
        return False


class FakeRepo:
    def __init__(self, duplicate: dict | None = None) -> None:
        self.db = FakeDb()
        self.duplicate = duplicate
        self.created_personas: list[dict] = []
        self.created_documentos: list[dict] = []

    def find_persona_duplicate_candidate(self, **_: object) -> dict | None:
        return self.duplicate

    def create_persona_contextual_tx(self, values: dict) -> dict:
        self.created_personas.append(values)
        return {"id_persona": 901, "uid_global": values["uid_global"], "version_registro": 1}

    def create_persona_documento_contextual_tx(self, values: dict) -> dict:
        self.created_documentos.append(values)
        return {"id_persona_documento": 902}


def _service(repo: FakeRepo) -> ConfirmVentaDirectaCompletaService:
    counter = {"value": 0}

    def uuid_generator() -> str:
        counter["value"] += 1
        return f"00000000-0000-0000-0000-{counter['value']:012d}"

    return ConfirmVentaDirectaCompletaService(
        comercial_repository=repo,
        plan_pago_v2_service=object(),
        uuid_generator=uuid_generator,
    )


def _datos_persona(
    *,
    tipo_persona: str = "FISICA",
    nombre: str | None = "Juan",
    apellido: str | None = "Pérez",
    razon_social: str | None = None,
    cuit_cuil: str | None = None,
    documento: (
        ConfirmVentaDirectaCompletaDocumentoPersonaInput | None | object
    ) = _DEFAULT_DOCUMENTO,
) -> ConfirmVentaDirectaCompletaDatosPersonaInput:
    if documento is _DEFAULT_DOCUMENTO:
        documento_principal = ConfirmVentaDirectaCompletaDocumentoPersonaInput(
            tipo_documento="DNI",
            numero_documento="12345678",
        )
    else:
        documento_principal = documento

    return ConfirmVentaDirectaCompletaDatosPersonaInput(
        tipo_persona=tipo_persona,
        nombre=nombre,
        apellido=apellido,
        razon_social=razon_social,
        cuit_cuil=cuit_cuil,
        documento_principal=documento_principal,
    )


def _comprador_contextual(
    datos: ConfirmVentaDirectaCompletaDatosPersonaInput | None = None,
) -> ConfirmVentaDirectaCompletaCompradorInput:
    return ConfirmVentaDirectaCompletaCompradorInput(
        id_persona=None,
        datos_persona=datos or _datos_persona(),
        id_rol_participacion=4,
        porcentaje_responsabilidad=Decimal("100.00"),
        fecha_desde=None,
        fecha_hasta=None,
        observaciones="Comprador contextual",
    )


def _command(
    comprador: ConfirmVentaDirectaCompletaCompradorInput,
) -> ConfirmVentaDirectaCompletaCommand:
    return ConfirmVentaDirectaCompletaCommand(
        context=SimpleNamespace(op_id=OP_ID, id_instalacion=1),
        generar_venta=ConfirmVentaDirectaCompletaGenerarVentaInput(
            codigo_venta="VD-CTX",
            fecha_venta=datetime(2026, 5, 22, 10, 0, 0),
            monto_total=Decimal("1000.00"),
            observaciones=None,
        ),
        objetos=[
            ConfirmVentaDirectaCompletaObjetoInput(
                id_inmueble=10,
                id_unidad_funcional=None,
                precio_asignado=Decimal("1000.00"),
                observaciones=None,
            )
        ],
        compradores=[comprador],
        condiciones_comerciales=ConfirmVentaDirectaCompletaCondicionesComercialesInput(
            monto_total=Decimal("1000.00"),
            tipo_plan_financiero="CONTADO",
            moneda="USD",
            importe_anticipo=None,
            fecha_vencimiento_anticipo=None,
            importe_saldo=None,
            fecha_vencimiento_saldo=None,
            cuotas=[],
        ),
        plan_pago_v2=ConfirmVentaDirectaCompletaPlanPagoV2Input(
            tipo_pago="CONTADO",
            monto_total_plan=Decimal("1000.00"),
            moneda="USD",
            bloques=[],
            observaciones=None,
        ),
        confirmacion=ConfirmVentaDirectaCompletaConfirmacionInput(observaciones=None),
    )


def test_resolucion_contextual_rechaza_duplicado_externo() -> None:
    repo = FakeRepo(
        duplicate={
            "id_persona": 800,
            "criterio": "documento_principal",
            "tipo_duplicado": "FUERTE",
            "op_id_alta": OTHER_OP_ID,
        }
    )
    comprador = _comprador_contextual()

    error = _service(repo)._resolve_compradores_contextuales(
        _command(comprador),
        id_instalacion=1,
    )

    assert error == "PERSONA_DUPLICADA_REUTILIZAR_EXISTENTE"
    assert comprador.id_persona is None
    assert repo.created_personas == []


def test_resolucion_contextual_reutiliza_duplicado_del_mismo_op_id() -> None:
    repo = FakeRepo(
        duplicate={
            "id_persona": 800,
            "criterio": "documento_principal",
            "tipo_duplicado": "FUERTE",
            "op_id_alta": OP_ID,
        }
    )
    comprador = _comprador_contextual()

    error = _service(repo)._resolve_compradores_contextuales(
        _command(comprador),
        id_instalacion=1,
    )

    assert error is None
    assert comprador.id_persona == 800
    assert repo.created_personas == []
    assert repo.created_documentos == []


def test_resolucion_contextual_no_bloquea_posible_duplicado_sin_warning_contract() -> None:
    repo = FakeRepo(
        duplicate={
            "id_persona": 800,
            "criterio": "nombre_apellido",
            "tipo_duplicado": "POSIBLE",
            "op_id_alta": OTHER_OP_ID,
        }
    )
    comprador = _comprador_contextual()

    error = _service(repo)._resolve_compradores_contextuales(
        _command(comprador),
        id_instalacion=1,
    )

    assert error is None
    assert comprador.id_persona == 901
    assert repo.created_personas != []


def test_resolucion_contextual_crea_persona_y_documento_si_no_hay_duplicado() -> None:
    repo = FakeRepo()
    comprador = _comprador_contextual()

    error = _service(repo)._resolve_compradores_contextuales(
        _command(comprador),
        id_instalacion=1,
    )

    assert error is None
    assert comprador.id_persona == 901
    assert repo.created_personas[0]["op_id_alta"] == OP_ID
    assert repo.created_documentos[0]["id_persona"] == 901


def test_validaciones_contextuales_minimas() -> None:
    service = _service(FakeRepo())

    assert (
        service._validate_compradores(_command(_comprador_contextual(_datos_persona(nombre=None))))
        == "PERSONA_FISICA_NOMBRE_APELLIDO_REQUERIDOS"
    )
    assert (
        service._validate_compradores(
            _command(
                _comprador_contextual(
                    _datos_persona(
                        tipo_persona="JURIDICA",
                        nombre=None,
                        apellido=None,
                        razon_social=None,
                        cuit_cuil="30-12345678-9",
                        documento=None,
                    )
                )
            )
        )
        == "PERSONA_JURIDICA_RAZON_SOCIAL_REQUERIDA"
    )
    assert (
        service._validate_compradores(
            _command(_comprador_contextual(_datos_persona(cuit_cuil=None, documento=None)))
        )
        == "IDENTIFICACION_PERSONA_REQUERIDA"
    )
