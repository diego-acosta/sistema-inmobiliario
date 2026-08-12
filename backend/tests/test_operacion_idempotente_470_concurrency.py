import threading
import time
from uuid import uuid4

from app.application.common.idempotency import (
    ClaimDecision,
    ConflictKind,
    OperationClaim,
    OperationCompletion,
    canonical_payload_hash,
    claim_operation,
    complete_operation,
)
from app.config.database import engine
from sqlalchemy import text
from sqlalchemy.orm import Session



def concurrent_case(change=None):
    op_id = uuid4()
    base = {
        "op_id": op_id,
        "command_code": "TEST.CONCURRENT",
        "target_type": "TEST",
        "target_uid": None,
        "target_key": "key",
        "payload_hash": canonical_payload_hash({"v": 1}),
        "canonicalization_version": 1,
    }
    second = {**base, **(change or {})}
    barrier = threading.Barrier(2)
    release = threading.Event()
    outcomes = []
    pids = []

    def first():
        with Session(engine) as session:
            pids.append(session.execute(text("SELECT pg_backend_pid() ")).scalar_one())
            outcomes.append(claim_operation(session, OperationClaim(**base)))
            barrier.wait()
            release.wait(5)
            complete_operation(session, OperationCompletion(
                **base, result_code="OK", result_http_status=200,
                result_target_uid=None, result_version=None,
                response_snapshot={"original": True}, id_usuario=None,
                id_sucursal=1, id_instalacion=1,
            ))
            session.commit()

    def contender():
        with Session(engine) as session:
            pids.append(session.execute(text("SELECT pg_backend_pid() ")).scalar_one())
            barrier.wait()
            outcomes.append(claim_operation(session, OperationClaim(**second)))
            session.rollback()

    t1 = threading.Thread(target=first)
    t2 = threading.Thread(target=contender)
    t1.start()
    t2.start()
    time.sleep(0.2)
    assert t2.is_alive(), "the contender must wait on the transaction advisory lock"
    release.set()
    t1.join(10)
    t2.join(10)
    assert not t1.is_alive() and not t2.is_alive()
    assert len(set(pids)) == 2
    with Session(engine) as session:
        assert session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"), {"op": op_id}).scalar_one() == 1
    return outcomes


def test_same_claim_executes_once_then_replays():
    assert sorted(result.decision for result in concurrent_case()) == [ClaimDecision.EXECUTE, ClaimDecision.REPLAY]


def test_concurrent_payload_conflict():
    results = concurrent_case({"payload_hash": "b" * 64})
    assert {result.decision for result in results} == {ClaimDecision.EXECUTE, ClaimDecision.CONFLICT}
    assert next(result for result in results if result.decision is ClaimDecision.CONFLICT).conflict is ConflictKind.PAYLOAD


def test_concurrent_target_conflict():
    results = concurrent_case({"target_key": "other"})
    assert next(result for result in results if result.decision is ClaimDecision.CONFLICT).conflict is ConflictKind.TARGET


def test_concurrent_command_conflict():
    results = concurrent_case({"command_code": "OTHER"})
    assert next(result for result in results if result.decision is ClaimDecision.CONFLICT).conflict is ConflictKind.COMMAND
