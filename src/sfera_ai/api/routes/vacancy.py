import threading
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sfera_ai.api.deps import get_llm_client, get_platform_engine, get_session, resolve_course_or_404
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_memory import VacancyMemory
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import IDENTITY_RESOLVER_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.feedback_interpretation import interpret_feedback
from sfera_ai.services.job_detection import enqueue_full_screening_for_course
from sfera_ai.services.vacancy_memory import FeedbackAlreadyAppliedError, approve_feedback
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version

router = APIRouter()


class VacancyProfileCreate(BaseModel):
    requirements: dict[str, Any]
    notes: str = ""
    created_by_id: int | None = None


class VacancyFeedbackCreate(BaseModel):
    candidate_profile_id: int | None = None
    analysis_id: int | None = None
    author_id: int | None = None
    text: str
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


class FeedbackApproveRequest(BaseModel):
    approved_by: int
    weight_hint: Literal["BOOST", "PENALIZE", "INFO_ONLY"] | None = None


def _serialize_vacancy_profile(profile: VacancyProfile) -> dict:
    return {
        "id": profile.id,
        "course_id": profile.course_id,
        "version": profile.version,
        "is_current": profile.is_current,
        "requirements": profile.requirements,
        "notes": profile.notes,
        "created_by_id": profile.created_by_id,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def _serialize_feedback(feedback: VacancyFeedback) -> dict:
    return {
        "id": feedback.id,
        "course_id": feedback.course_id,
        "candidate_profile_id": feedback.candidate_profile_id,
        "analysis_id": feedback.analysis_id,
        "author_id": feedback.author_id,
        "text": feedback.text,
        "sentiment": feedback.sentiment,
        "ai_suggested_rule": feedback.ai_suggested_rule,
        "applied": feedback.applied,
        "created_at": feedback.created_at,
    }


def _serialize_memory(memory: VacancyMemory) -> dict:
    return {
        "id": memory.id,
        "course_id": memory.course_id,
        "rule_text": memory.rule_text,
        "weight_hint": memory.weight_hint,
        "source_feedback_id": memory.source_feedback_id,
        "approved_by_id": memory.approved_by_id,
        "approved_at": memory.approved_at,
        "is_active": memory.is_active,
    }


@router.get("/vacancy-profile/")
def get_vacancy_profile(
    course_uuid: str,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    profile = session.scalar(
        select(VacancyProfile).where(VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True))
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="vacancy profile not found")
    return _serialize_vacancy_profile(profile)


def _run_full_screening_background(engine: Engine, platform_engine: Engine, course_id: int) -> None:
    """step-E15-04 — постановка `AIProcessingJob` по всем кандидатам курса не должна
    блокировать ответ `POST vacancy-profile/`: на курсах до ~500 кандидатов (демо-масштаб,
    архитектурное ревью 2026-09-08) цикл по заявкам в `enqueue_full_screening_for_course`
    занимает заметное время. Отдельный поток (не FastAPI `BackgroundTasks` — те выполняются
    до отправки ответа тестовому/ASGI-клиенту, что фактически блокирует его так же, как
    прямой вызов в теле запроса) — самый дешёвый вариант поверх текущего стека без отдельной
    очереди задач; своя сессия и свой `platform_base`, т.к. request-scoped session закрывается
    сразу после ответа."""
    factory = sessionmaker(bind=engine)
    platform_base = reflect_platform_tables(platform_engine, tables=IDENTITY_RESOLVER_TABLES)
    with factory() as session:
        enqueue_full_screening_for_course(session, platform_base, course_id)


@router.post("/vacancy-profile/", status_code=201)
def create_vacancy_profile(
    course_uuid: str,
    body: VacancyProfileCreate,
    request: Request,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    profile = create_vacancy_profile_version(
        session,
        course_id=course_id,
        requirements=body.requirements,
        notes=body.notes,
        created_by_id=body.created_by_id,
    )
    threading.Thread(
        target=_run_full_screening_background,
        args=(request.app.state.engine, platform_engine, course_id),
        daemon=True,
    ).start()
    return _serialize_vacancy_profile(profile)


@router.get("/feedback/")
def list_feedback(
    course_uuid: str,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    items = (
        session.execute(select(VacancyFeedback).where(VacancyFeedback.course_id == course_id).order_by(VacancyFeedback.id))
        .scalars()
        .all()
    )
    return {"items": [_serialize_feedback(item) for item in items]}


@router.post("/feedback/", status_code=201)
def create_feedback(
    course_uuid: str,
    body: VacancyFeedbackCreate,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
    llm_client: OpenRouterClient = Depends(get_llm_client),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    feedback = VacancyFeedback(
        course_id=course_id,
        candidate_profile_id=body.candidate_profile_id,
        analysis_id=body.analysis_id,
        author_id=body.author_id,
        text=body.text,
        sentiment=body.sentiment,
    )
    session.add(feedback)
    session.flush()
    feedback.ai_suggested_rule = interpret_feedback(feedback, llm_client=llm_client)
    session.commit()
    session.refresh(feedback)
    return _serialize_feedback(feedback)


@router.post("/feedback/{feedback_id}/approve/")
def approve_feedback_route(
    course_uuid: str,
    feedback_id: int,
    body: FeedbackApproveRequest,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    feedback = session.get(VacancyFeedback, feedback_id)
    if feedback is None or feedback.course_id != course_id:
        raise HTTPException(status_code=404, detail="feedback not found")
    try:
        memory = approve_feedback(session, feedback, approved_by=body.approved_by, weight_hint=body.weight_hint)
    except FeedbackAlreadyAppliedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_memory(memory)
