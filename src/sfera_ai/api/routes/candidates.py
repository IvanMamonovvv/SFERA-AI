from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from sfera_ai.api.deps import get_platform_engine, get_session, resolve_course_or_404
from sfera_ai.services.api_read import (
    get_candidate_detail,
    get_candidate_history,
    get_summary,
    is_screening_enabled_for_course,
    list_candidates,
    list_screening_candidates,
)
from sfera_ai.services.job_detection import ReanalyzeRateLimitedError, enqueue_manual_reanalyze

router = APIRouter()


@router.get("/summary/")
def get_course_summary(
    course_uuid: str,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    return get_summary(session, course_id)


@router.get("/candidates/")
def get_candidates(
    course_uuid: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, platform_base = resolve_course_or_404(platform_engine, course_uuid)
    return list_candidates(session, platform_base, course_id, limit=limit, offset=offset)


@router.get("/candidates/screening/")
def get_screening_candidates(
    course_uuid: str,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, platform_base = resolve_course_or_404(platform_engine, course_uuid)
    if not is_screening_enabled_for_course(platform_base, course_id):
        raise HTTPException(status_code=403, detail="candidate screening not enabled for this workspace")
    return list_screening_candidates(session, platform_base, course_id)


@router.get("/candidates/{candidate_profile_id}/")
def get_candidate(
    course_uuid: str,
    candidate_profile_id: int,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    detail = get_candidate_detail(session, course_id, candidate_profile_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return detail


@router.get("/candidates/{candidate_profile_id}/history/")
def get_candidate_history_route(
    course_uuid: str,
    candidate_profile_id: int,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    history = get_candidate_history(session, course_id, candidate_profile_id)
    if history is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return history


@router.post("/candidates/{candidate_profile_id}/reanalyze/", status_code=201)
def reanalyze_candidate(
    course_uuid: str,
    candidate_profile_id: int,
    session: Session = Depends(get_session),
    platform_engine: Engine = Depends(get_platform_engine),
) -> dict:
    course_id, _ = resolve_course_or_404(platform_engine, course_uuid)
    if get_candidate_detail(session, course_id, candidate_profile_id) is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    try:
        job = enqueue_manual_reanalyze(session, candidate_profile_id=candidate_profile_id, course_id=course_id)
    except ReanalyzeRateLimitedError as exc:
        raise HTTPException(status_code=429, detail="reanalyze rate limit: try again later") from exc
    return {"id": job.id, "status": job.status}
