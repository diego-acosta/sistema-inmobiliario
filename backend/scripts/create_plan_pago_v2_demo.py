"""Create the DEV/test Plan Pago V2 indexed demo (#373)."""
from __future__ import annotations

import argparse
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import GeneratePlanPagoVentaV2PorBloquesCommand, PlanPagoVentaBloqueInput
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import GeneratePlanPagoVentaV2PorBloquesService
from app.application.common.commands import CommandContext
from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.aplicar_indexacion_cuotas_v2_service import AplicarIndexacionCuotasV2Command, AplicarIndexacionCuotasV2Service
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import PreviewIndexacionCuotasV2Command
from app.config.database import SessionLocal
from app.infrastructure.persistence.repositories.aplicar_indexacion_cuotas_v2_repository import AplicarIndexacionCuotasV2SqlAlchemyRepository
from app.infrastructure.persistence.repositories.plan_pago_venta_v2_repository import PlanPagoVentaV2Repository
from app.infrastructure.persistence.repositories.preview_indexacion_cuotas_v2_repository import PreviewIndexacionCuotasV2SqlAlchemyRepository
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import PreviewIndexacionCuotasV2Service

CODIGO_VENTA = "DEMO-VTA-CUOTAS-PPV2-INDEXADA"
CODIGO_BASE = "DEMO-VTA-CUOTAS"


def require_safe_environment() -> None:
    """Fail closed: demo data must never be applied to production."""
    env_raw = os.getenv("ENV")
    if env_raw is None or not env_raw.strip():
        raise RuntimeError("Debe definir explícitamente ENV=dev o ENV=test.")
    if env_raw.strip().lower() not in {"dev", "test"}:
        raise RuntimeError("Este script solo puede ejecutarse con ENV=dev o ENV=test.")


def _seed_ui(db) -> None:
    """Reuse the existing idempotent seed: it owns the valid sale and buyer."""
    sql = (Path(__file__).parents[1] / "database" / "seed_demo_ui.sql").read_text()
    db.connection().connection.driver_connection.cursor().execute(sql)


def _seed_indices_financieros_demo(db) -> None:
    """Load the existing idempotent DEV/test index fixture required by the plan."""
    sql = (
        Path(__file__).parents[1] / "database" / "seed_indices_financieros_demo.sql"
    ).read_text()
    db.connection().connection.driver_connection.cursor().execute(sql)


def _get_demo_sale(db, codigo_venta: str = CODIGO_VENTA) -> int | None:
    """Return the exclusive demo sale without changing it."""
    return db.execute(
        text("SELECT id_venta FROM venta WHERE codigo_venta=:code AND deleted_at IS NULL"),
        {"code": codigo_venta},
    ).scalar_one_or_none()


def _create_demo_sale(db, codigo_venta: str = CODIGO_VENTA) -> int:
    """Create the exclusive sale.  Call only after absence was established."""
    source = db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta=:code AND estado_venta='confirmada' AND deleted_at IS NULL"), {"code": CODIGO_BASE}).scalar_one()
    sale = db.execute(text("""
        INSERT INTO venta (id_instalacion_origen,id_instalacion_ultima_modificacion,op_id_alta,op_id_ultima_modificacion,codigo_venta,fecha_venta,estado_venta,monto_total,tipo_plan_financiero,moneda,observaciones)
        SELECT id_instalacion_origen,id_instalacion_ultima_modificacion,CAST(:op AS uuid),CAST(:op AS uuid),:code,fecha_venta,'confirmada',monto_total,tipo_plan_financiero,moneda,'Escenario demo aislado #373'
        FROM venta WHERE id_venta=:source RETURNING id_venta
    """), {"op": str(uuid4()), "code": codigo_venta, "source": source}).scalar_one()
    db.execute(text("""INSERT INTO venta_objeto_inmobiliario (id_instalacion_origen,id_instalacion_ultima_modificacion,op_id_alta,op_id_ultima_modificacion,id_venta,id_inmueble,id_unidad_funcional,precio_asignado,observaciones)
        SELECT id_instalacion_origen,id_instalacion_ultima_modificacion,CAST(:op AS uuid),CAST(:op AS uuid),:sale,id_inmueble,id_unidad_funcional,precio_asignado,'Objeto reutilizado solo para fixture #373' FROM venta_objeto_inmobiliario WHERE id_venta=:source"""), {"op": str(uuid4()), "sale": sale, "source": source})
    db.execute(text("""INSERT INTO relacion_persona_rol (id_instalacion_origen,id_instalacion_ultima_modificacion,op_id_alta,op_id_ultima_modificacion,id_persona,id_rol_participacion,tipo_relacion,id_relacion,fecha_desde,observaciones)
        SELECT id_instalacion_origen,id_instalacion_ultima_modificacion,CAST(:op AS uuid),CAST(:op AS uuid),id_persona,id_rol_participacion,'venta',:sale,fecha_desde,'Comprador demo #373' FROM relacion_persona_rol WHERE tipo_relacion='venta' AND id_relacion=:source AND deleted_at IS NULL"""), {"op": str(uuid4()), "sale": sale, "source": source})
    return sale


# Kept for the #373 isolation test helper; create() deliberately never uses it.
def _get_or_create_sale(db, codigo_venta: str = CODIGO_VENTA) -> int:
    return _get_demo_sale(db, codigo_venta) or _create_demo_sale(db, codigo_venta)


def _command(venta: int, indice: int) -> GeneratePlanPagoVentaV2PorBloquesCommand:
    common = dict(metodo_liquidacion="INDEXACION", id_indice_financiero=indice, fecha_base_indice=date(2026, 1, 1), valor_base_indice=Decimal("1000"), modo_indexacion="POR_COEFICIENTE", base_calculo_indexacion="CAPITAL_INICIAL_BLOQUE", tipo_generacion_indexada="DEFINITIVA", politica_valor_no_disponible="ERROR_SI_NO_EXISTE", conserva_capital_original=True, genera_ajuste_por_diferencia=True)
    block = lambda label, due: PlanPagoVentaBloqueInput(tipo_bloque="TRAMO_CUOTAS", etiqueta_bloque=label, cantidad_cuotas=1, importe_total_bloque=Decimal("40000000"), fecha_primer_vencimiento=due, periodicidad="MENSUAL", **common)
    return GeneratePlanPagoVentaV2PorBloquesCommand(context=CommandContext(actor_id="demo-ppv2", metadata={"op_id": str(uuid4())}), id_venta=venta, tipo_pago="FINANCIADO", monto_total_plan=Decimal("120000000"), moneda="ARS", bloques=[block("Demo: índice al nacimiento", date(2026, 3, 10)), block("Demo: proyectada sin índice", date(2027, 1, 10)), block("Demo: corrida posterior", date(2026, 2, 10))], observaciones="Fixture DEV/test #373; no usar como negocio productivo.")


def _fixture_corridas(db, venta: int, indice: int) -> None:
    """Persist presentation-only states unavailable through product commands.

    The applied and failed rows deliberately exercise read contracts.  They are
    fixtures, not a replacement for preparation/application services nor an
    outbox-producing business operation.
    """
    rows = db.execute(text("""
        SELECT p.id_plan_pago_venta, b.id_plan_pago_venta_bloque,
               b.etiqueta_bloque, i.id_plan_pago_venta_bloque_indexacion, o.id_obligacion_financiera,
               o.version_registro, o.importe_total, o.saldo_pendiente,
               oi.id_obligacion_financiera_indexacion
        FROM plan_pago_venta p JOIN plan_pago_venta_bloque b USING (id_plan_pago_venta)
        JOIN plan_pago_venta_bloque_indexacion i USING (id_plan_pago_venta_bloque)
        JOIN obligacion_financiera o USING (id_plan_pago_venta_bloque)
        LEFT JOIN obligacion_financiera_indexacion oi USING (id_obligacion_financiera)
        WHERE p.id_venta=:venta AND p.deleted_at IS NULL AND b.deleted_at IS NULL
        ORDER BY b.numero_bloque
    """), {"venta": venta}).mappings().all()
    if len(rows) < 3:
        raise RuntimeError("El plan demo no materializó las tres obligaciones esperadas.")
    valor = db.execute(text("SELECT id_indice_financiero_valor FROM indice_financiero_valor WHERE id_indice_financiero=:indice AND fecha_valor=DATE '2026-04-01' AND deleted_at IS NULL"), {"indice": indice}).scalar_one()
    by_label = {row["etiqueta_bloque"]: row for row in rows}
    # Keep the projected block free of materialized indexation.  The failed
    # fixture shares the later block with the real applied run so the integral
    # contract can expose both history and the applied value actually vigente.
    for item, state in ((by_label["Demo: proyectada sin índice"], "PENDIENTE_APLICACION"), (by_label["Demo: corrida posterior"], "FALLIDA")):
        exists = db.execute(text("SELECT 1 FROM corrida_indexacion_financiera WHERE id_plan_pago_venta_bloque=:block AND motivo=:motivo AND deleted_at IS NULL"), {"block": item["id_plan_pago_venta_bloque"], "motivo": f"DEMO-373-{state}"}).scalar()
        if exists:
            continue
        applied = False
        failed = state == "FALLIDA"
        corrida = db.execute(text("""
          INSERT INTO corrida_indexacion_financiera
          (id_plan_pago_venta,id_plan_pago_venta_bloque,id_plan_pago_venta_bloque_indexacion,id_indice_financiero,id_indice_financiero_valor_aplicado,periodo_base,periodo_aplicado,fecha_corte,fecha_calculo,fecha_publicacion_indice,fecha_aplicacion,origen_corrida,estado_corrida,op_id,hash_corrida,motivo,codigo_error,etapa_error,diagnostico_tecnico,cantidad_analizada,cantidad_elegible,cantidad_excluida,cantidad_aplicada,importe_total_anterior,importe_total_nuevo,saldo_anterior_total,saldo_nuevo_total)
          VALUES (:plan,:block,:config,:indice,:valor,DATE '2026-01-01',DATE '2026-04-01',DATE '2026-04-30',TIMESTAMP '2026-05-01',DATE '2026-04-10',:fecha,'REINDEXACION_MANUAL',:state,:op,:hash,:motivo,:error,:etapa,:diag,1,:eligible,:excluded,:applied,:amount,:amount,:saldo,:saldo)
          RETURNING id_corrida_indexacion_financiera
        """), {"plan": item["id_plan_pago_venta"], "block": item["id_plan_pago_venta_bloque"], "config": item["id_plan_pago_venta_bloque_indexacion"], "indice": indice, "valor": valor, "fecha": "2026-05-01 12:00:00" if applied else None, "state": state, "op": str(uuid4()), "hash": f"demo-373-{state}-{item['id_obligacion_financiera']}", "motivo": f"DEMO-373-{state}", "error": "DEMO_FALLO_CONTROLADO" if failed else None, "etapa": "APLICACION" if failed else None, "diag": "Fixture de error controlado #373" if failed else None, "eligible": 0 if failed else 1, "excluded": 1 if failed else 0, "applied": 1 if applied else 0, "amount": item["importe_total"], "saldo": item["saldo_pendiente"]}).scalar_one()
        db.execute(text("""
          INSERT INTO corrida_indexacion_financiera_detalle
          (id_corrida_indexacion_financiera,id_obligacion_financiera,id_obligacion_financiera_indexacion,version_esperada,version_resultante,capital_base,valor_indice_base,valor_indice_aplicado,coeficiente_indexacion,importe_anterior,importe_nuevo,saldo_anterior,saldo_nuevo,estado_elegibilidad,motivo_exclusion,codigo_error)
          VALUES (:corrida,:obligacion,:indexacion,:expected,:result,:capital,1000,1078.8,1.0788,:importe,:importe,:saldo,:saldo,:eligibility,:reason,:error)
        """), {"corrida": corrida, "obligacion": item["id_obligacion_financiera"], "indexacion": item["id_obligacion_financiera_indexacion"] if applied else None, "expected": item["version_registro"], "result": item["version_registro"] + 1 if applied else None, "capital": item["importe_total"], "importe": item["importe_total"], "saldo": item["saldo_pendiente"], "eligibility": "EXCLUIDA" if failed else "ELEGIBLE", "reason": "Exclusión demo controlada" if failed else None, "error": "DEMO_OBLIGACION_EXCLUIDA" if failed else None})


def _resolve_demo_core_ef(db) -> CoreEFHeaders:
    row = db.execute(text("""SELECT u.id_usuario, s.id_sucursal, i.id_instalacion
        FROM usuario u CROSS JOIN sucursal s JOIN instalacion i ON i.id_sucursal=s.id_sucursal
        WHERE u.estado_usuario='ACTIVO' AND s.estado_sucursal='ACTIVA' AND i.estado_instalacion='ACTIVA'
        ORDER BY u.id_usuario,s.id_sucursal,i.id_instalacion LIMIT 1""")).mappings().one_or_none()
    if row is None:
        raise RuntimeError("No existe contexto CORE-EF activo para el demo.")
    return CoreEFHeaders(uuid4(), int(row["id_usuario"]), int(row["id_sucursal"]), int(row["id_instalacion"]))


def _reset_block_to_capital_state(db, venta: int, etiqueta_bloque: str) -> None:
    """Use the production preparation and application services for APPLIED."""
    # The generator materializes historical quotas at birth.  This fixture
    # restores only the third quota to its capital state so the real apply
    # service owns the subsequent adjustment and traceability.
    db.execute(text("""DELETE FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera IN
        (SELECT c.id_corrida_indexacion_financiera FROM corrida_indexacion_financiera c JOIN plan_pago_venta_bloque b ON b.id_plan_pago_venta_bloque=c.id_plan_pago_venta_bloque JOIN plan_pago_venta p ON p.id_plan_pago_venta=c.id_plan_pago_venta WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)"""), {"sale": venta, "label": etiqueta_bloque})
    db.execute(text("""DELETE FROM corrida_indexacion_financiera WHERE id_plan_pago_venta_bloque IN
        (SELECT b.id_plan_pago_venta_bloque FROM plan_pago_venta_bloque b JOIN plan_pago_venta p ON p.id_plan_pago_venta=b.id_plan_pago_venta WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)"""), {"sale": venta, "label": etiqueta_bloque})
    db.execute(text("""DELETE FROM obligacion_financiera_indexacion WHERE id_obligacion_financiera IN
        (SELECT o.id_obligacion_financiera FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING (id_plan_pago_venta_bloque)
         JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)"""), {"sale": venta, "label": etiqueta_bloque})
    db.execute(text("""DELETE FROM composicion_obligacion WHERE id_obligacion_financiera IN
        (SELECT o.id_obligacion_financiera FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING (id_plan_pago_venta_bloque)
        JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)
        AND id_concepto_financiero=(SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero='AJUSTE_INDEXACION' AND deleted_at IS NULL)"""), {"sale": venta, "label": etiqueta_bloque})
    db.execute(text("""UPDATE obligacion_financiera o SET importe_total=cap.importe_componente, saldo_pendiente=cap.saldo_componente
        FROM composicion_obligacion cap WHERE cap.id_obligacion_financiera=o.id_obligacion_financiera
        AND cap.id_concepto_financiero=(SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero='CAPITAL_VENTA' AND deleted_at IS NULL)
        AND o.id_obligacion_financiera IN (SELECT o2.id_obligacion_financiera FROM obligacion_financiera o2 JOIN plan_pago_venta_bloque b ON b.id_plan_pago_venta_bloque=o2.id_plan_pago_venta_bloque JOIN plan_pago_venta p ON p.id_plan_pago_venta=b.id_plan_pago_venta WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)"""), {"sale": venta, "label": etiqueta_bloque})
def _create_and_apply_scoped_real_run(db, venta: int, indice: int, headers: CoreEFHeaders) -> None:
    value = db.execute(text("SELECT id_indice_financiero_valor FROM indice_financiero_valor WHERE id_indice_financiero=:indice AND fecha_valor=DATE '2026-04-01' AND deleted_at IS NULL"), {"indice": indice}).scalar_one()
    scope = db.execute(text("""SELECT p.id_plan_pago_venta,b.id_plan_pago_venta_bloque,i.id_plan_pago_venta_bloque_indexacion
        FROM plan_pago_venta p JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta) JOIN plan_pago_venta_bloque_indexacion i USING(id_plan_pago_venta_bloque)
        WHERE p.id_venta=:sale AND b.etiqueta_bloque='Demo: corrida posterior'"""), {"sale": venta}).mappings().one()
    preview = PreviewIndexacionCuotasV2Service(PreviewIndexacionCuotasV2SqlAlchemyRepository(db)).execute(
        PreviewIndexacionCuotasV2Command(**scope, id_indice_financiero=indice, id_indice_financiero_valor_aplicado=value, fecha_corte=date(2026, 4, 30), periodo_aplicado=date(2026, 4, 1), persistir=True, motivo="DEMO-373"), headers)
    if not preview.success:
        raise RuntimeError("No se pudo persistir preview demo: " + preview.errors[0])
    corrida = db.execute(text("SELECT id_corrida_indexacion_financiera,hash_corrida,version_registro FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id"), {"id": preview.data["id_corrida_indexacion_financiera"]}).mappings().one()
    applied = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db)).execute(
        AplicarIndexacionCuotasV2Command(corrida["id_corrida_indexacion_financiera"], corrida["hash_corrida"]),
        CoreEFHeaders(uuid4(), headers.x_usuario_id, headers.x_sucursal_id, headers.x_instalacion_id, int(corrida["version_registro"])),
    )
    if not applied.success:
        raise RuntimeError("No se pudo aplicar corrida demo: " + applied.errors[0])


def _get_demo_plan(db, venta: int) -> int | None:
    return db.execute(text("""SELECT id_plan_pago_venta FROM plan_pago_venta
        WHERE id_venta=:sale AND deleted_at IS NULL ORDER BY id_plan_pago_venta"""), {"sale": venta}).scalar_one_or_none()


def _inspect_demo_scenario(db, venta: int) -> dict:
    """Read-only structural inspection used to choose create/reuse/fail.

    This intentionally validates the persisted financial contract before the
    no-op path.  It never repairs a partially created graph.
    """
    plan = _get_demo_plan(db, venta)
    if plan is None:
        return {"complete": False, "reason": "plan ausente"}
    blocks = db.execute(text("""SELECT b.etiqueta_bloque, b.id_plan_pago_venta_bloque,
        o.id_obligacion_financiera, o.importe_total, o.version_registro,
        oi.id_obligacion_financiera_indexacion
        FROM plan_pago_venta_bloque b
        LEFT JOIN obligacion_financiera o ON o.id_plan_pago_venta_bloque=b.id_plan_pago_venta_bloque
        LEFT JOIN obligacion_financiera_indexacion oi ON oi.id_obligacion_financiera=o.id_obligacion_financiera AND oi.deleted_at IS NULL
        WHERE b.id_plan_pago_venta=:plan AND b.deleted_at IS NULL ORDER BY b.numero_bloque"""), {"plan": plan}).mappings().all()
    expected = {"Demo: índice al nacimiento", "Demo: proyectada sin índice", "Demo: corrida posterior"}
    if len(blocks) != 3 or {row["etiqueta_bloque"] for row in blocks} != expected or any(row["id_obligacion_financiera"] is None for row in blocks):
        return {"complete": False, "reason": "bloques u obligaciones incompletos"}
    by_label = {row["etiqueta_bloque"]: row for row in blocks}
    if by_label["Demo: índice al nacimiento"]["id_obligacion_financiera_indexacion"] is None:
        return {"complete": False, "reason": "falta indexación al nacimiento"}
    if by_label["Demo: proyectada sin índice"]["id_obligacion_financiera_indexacion"] is not None:
        return {"complete": False, "reason": "bloque proyectado materializado"}
    runs = db.execute(text("""SELECT c.id_corrida_indexacion_financiera, c.estado_corrida,
        c.id_plan_pago_venta_bloque, c.hash_corrida, c.version_registro
        FROM corrida_indexacion_financiera c WHERE c.id_plan_pago_venta=:plan
        AND c.deleted_at IS NULL ORDER BY c.id_corrida_indexacion_financiera"""), {"plan": plan}).mappings().all()
    states = [row["estado_corrida"] for row in runs]
    if len(runs) != 3 or {state: states.count(state) for state in set(states)} != {"PENDIENTE_APLICACION": 1, "FALLIDA": 1, "APLICADA": 1}:
        return {"complete": False, "reason": "corridas incompletas o duplicadas"}
    detail_counts = db.execute(text("""SELECT id_corrida_indexacion_financiera, count(*) AS cantidad
        FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera IN
        (SELECT id_corrida_indexacion_financiera FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan)
        AND deleted_at IS NULL GROUP BY id_corrida_indexacion_financiera"""), {"plan": plan}).mappings().all()
    if {int(row["cantidad"]) for row in detail_counts} != {1} or len(detail_counts) != 3:
        return {"complete": False, "reason": "detalles de corrida incompletos"}
    runs_by_state = {row["estado_corrida"]: row for row in runs}
    expected_blocks_by_state = {
        "PENDIENTE_APLICACION": by_label["Demo: proyectada sin índice"]["id_plan_pago_venta_bloque"],
        # _fixture_corridas intentionally places the failed presentation run
        # on the same later block as the real applied run.
        "FALLIDA": by_label["Demo: corrida posterior"]["id_plan_pago_venta_bloque"],
        "APLICADA": by_label["Demo: corrida posterior"]["id_plan_pago_venta_bloque"],
    }
    for state, expected_block_id in expected_blocks_by_state.items():
        if runs_by_state[state]["id_plan_pago_venta_bloque"] != expected_block_id:
            return {
                "complete": False,
                "reason": f"corrida {state} asociada al bloque incorrecto",
            }
    applied = runs_by_state["APLICADA"]
    detail = db.execute(text("""SELECT d.version_resultante, d.id_obligacion_financiera_indexacion,
        d.id_obligacion_financiera, d.capital_base, d.importe_nuevo
        FROM corrida_indexacion_financiera_detalle d
        WHERE d.id_corrida_indexacion_financiera=:run AND d.deleted_at IS NULL"""), {"run": applied["id_corrida_indexacion_financiera"]}).mappings().all()
    if len(detail) != 1 or detail[0]["version_resultante"] != by_label["Demo: corrida posterior"]["version_registro"] or detail[0]["id_obligacion_financiera_indexacion"] is None:
        return {"complete": False, "reason": "detalle aplicado inconsistente"}
    amount = db.execute(text("""SELECT o.importe_total, co.importe_componente AS capital,
        aj.importe_componente AS ajuste FROM obligacion_financiera o
        JOIN composicion_obligacion co ON co.id_obligacion_financiera=o.id_obligacion_financiera
        JOIN concepto_financiero cc ON cc.id_concepto_financiero=co.id_concepto_financiero AND cc.codigo_concepto_financiero='CAPITAL_VENTA'
        JOIN composicion_obligacion aj ON aj.id_obligacion_financiera=o.id_obligacion_financiera AND aj.deleted_at IS NULL
        JOIN concepto_financiero ca ON ca.id_concepto_financiero=aj.id_concepto_financiero AND ca.codigo_concepto_financiero='AJUSTE_INDEXACION'
        WHERE o.id_obligacion_financiera=:obl AND co.deleted_at IS NULL"""), {"obl": detail[0]["id_obligacion_financiera"]}).mappings().one_or_none()
    if amount is None or amount["importe_total"] != amount["capital"] + amount["ajuste"]:
        return {"complete": False, "reason": "importe aplicado inconsistente"}
    outbox = db.execute(text("""SELECT count(*) FROM outbox_event
        WHERE aggregate_type='corrida_indexacion_financiera' AND aggregate_id=:run"""), {"run": applied["id_corrida_indexacion_financiera"]}).scalar_one()
    if outbox != 1:
        return {"complete": False, "reason": "outbox de aplicación inconsistente"}
    try:
        integral = PlanPagoVentaV2Repository(db).get_plan_pago_venta_v2_integral(venta)
    except Exception as exc:
        return {"complete": False, "reason": f"contrato integral no disponible: {exc}"}
    if integral is None or len(integral.get("bloques", [])) != 3 or len(integral.get("corridas_indexacion", [])) != 3:
        return {"complete": False, "reason": "contrato integral incompleto"}
    return {"complete": True, "venta": venta, "plan": plan, "obligaciones": 3, "corridas": 3}


def _validate_complete_demo_scenario(db, venta: int) -> dict | None:
    inspected = _inspect_demo_scenario(db, venta)
    return inspected if inspected["complete"] else None


def _prepare_new_demo_scenario(db, venta: int, indice: int) -> None:
    repo = PlanPagoVentaV2Repository(db)
    result = GeneratePlanPagoVentaV2PorBloquesService(repo).execute_in_existing_transaction(_command(venta, indice))
    if not result.success:
        raise RuntimeError("No se pudo materializar el plan real: " + result.errors[0])
    _reset_block_to_capital_state(db, venta, "Demo: proyectada sin índice")
    _reset_block_to_capital_state(db, venta, "Demo: corrida posterior")


def _create_presentation_fixtures_before_apply(db, venta: int, indice: int) -> None:
    _fixture_corridas(db, venta, indice)


def _print_demo_summary(summary: dict, *, reused: bool) -> None:
    print(f"Escenario {'reutilizado' if reused else 'creado'}: venta id={summary['venta']}, código={CODIGO_VENTA}")
    print(f"Abrir: /ventas/{summary['venta']}")
    print(f"Obligaciones: {summary['obligaciones']}; corridas: {summary['corridas']}")


def create() -> None:
    require_safe_environment()
    with SessionLocal() as db:
        try:
            _seed_ui(db)
            _seed_indices_financieros_demo(db)
            venta = _get_demo_sale(db)
            if venta is not None:
                summary = _validate_complete_demo_scenario(db, venta)
                if summary is None:
                    raise RuntimeError("El escenario demo existe pero está incompleto o inconsistente. Ejecute --clean y vuelva a crear.")
                # The reuse path is strictly read-only after idempotent seeds.
                try:
                    _print_demo_summary(summary, reused=True)
                except Exception as exc:
                    print(f"ADVERTENCIA: escenario reutilizado, no se pudo imprimir el resumen: {exc}")
                return
            indice = db.execute(text("SELECT id_indice_financiero FROM indice_financiero WHERE codigo_indice_financiero='CAC_DEMO' AND deleted_at IS NULL")).scalar_one()
            venta = _create_demo_sale(db)
            _prepare_new_demo_scenario(db, venta, indice)
            _create_presentation_fixtures_before_apply(db, venta, indice)
            _create_and_apply_scoped_real_run(db, venta, indice, _resolve_demo_core_ef(db))
            # The service committed its own transaction.  No mutation, fixture,
            # reset or validation is allowed below this boundary.
            summary = {"venta": venta, "obligaciones": 3, "corridas": 3}
        except Exception:
            db.rollback()
            raise
    try:
        _print_demo_summary(summary, reused=False)
    except Exception as exc:
        # Presentation is deliberately non-fatal: the real apply service has
        # already committed and cannot be rolled back by this session.
        print(f"ADVERTENCIA: escenario creado, no se pudo imprimir el resumen: {exc}")


def clean() -> None:
    require_safe_environment()
    with SessionLocal() as db, db.begin():
        venta = db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta=:code AND deleted_at IS NULL"), {"code": CODIGO_VENTA}).scalar_one_or_none()
        if venta is None:
            print("No existe escenario demo para limpiar.")
            return
        # Delete only rows reached from the stable demo code, children first.
        db.execute(text("DELETE FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera IN (SELECT c.id_corrida_indexacion_financiera FROM corrida_indexacion_financiera c JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM corrida_indexacion_financiera WHERE id_plan_pago_venta IN (SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM obligacion_financiera_indexacion WHERE id_obligacion_financiera IN (SELECT o.id_obligacion_financiera FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING (id_plan_pago_venta_bloque) JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM composicion_obligacion WHERE id_obligacion_financiera IN (SELECT o.id_obligacion_financiera FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING (id_plan_pago_venta_bloque) JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM obligacion_obligado WHERE id_obligacion_financiera IN (SELECT id_obligacion_financiera FROM obligacion_financiera WHERE id_relacion_generadora IN (SELECT id_relacion_generadora FROM relacion_generadora WHERE tipo_origen='venta' AND id_origen=:id))"), {"id": venta})
        db.execute(text("DELETE FROM composicion_obligacion WHERE id_obligacion_financiera IN (SELECT id_obligacion_financiera FROM obligacion_financiera WHERE id_relacion_generadora IN (SELECT id_relacion_generadora FROM relacion_generadora WHERE tipo_origen='venta' AND id_origen=:id))"), {"id": venta})
        db.execute(text("DELETE FROM obligacion_financiera WHERE id_plan_pago_venta_bloque IN (SELECT b.id_plan_pago_venta_bloque FROM plan_pago_venta_bloque b JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM generacion_cronograma_financiero WHERE id_plan_pago_venta IN (SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM plan_pago_venta_bloque_indexacion WHERE id_plan_pago_venta_bloque IN (SELECT b.id_plan_pago_venta_bloque FROM plan_pago_venta_bloque b JOIN plan_pago_venta p USING (id_plan_pago_venta) WHERE p.id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM plan_pago_venta_bloque WHERE id_plan_pago_venta IN (SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:id)"), {"id": venta})
        db.execute(text("DELETE FROM plan_pago_venta WHERE id_venta=:id"), {"id": venta})
        db.execute(text("DELETE FROM obligacion_financiera WHERE id_relacion_generadora IN (SELECT id_relacion_generadora FROM relacion_generadora WHERE tipo_origen='venta' AND id_origen=:id)"), {"id": venta})
        db.execute(text("DELETE FROM relacion_generadora WHERE tipo_origen='venta' AND id_origen=:id"), {"id": venta})
        db.execute(text("DELETE FROM relacion_persona_rol WHERE tipo_relacion='venta' AND id_relacion=:id"), {"id": venta})
        db.execute(text("DELETE FROM venta_objeto_inmobiliario WHERE id_venta=:id"), {"id": venta})
        db.execute(text("DELETE FROM venta_plan_cuota WHERE id_venta=:id"), {"id": venta})
        db.execute(text("DELETE FROM venta WHERE id_venta=:id"), {"id": venta})
    print("Escenario demo eliminado; no se modificaron ventas ajenas.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    print("ADVERTENCIA: fixture exclusivo para desarrollo/test.")
    (clean if args.clean else create)()


if __name__ == "__main__":
    main()
