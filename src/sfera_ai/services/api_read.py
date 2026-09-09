from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.services.candidate_facts import resume_status

SCREENING_FIT_SCORE_THRESHOLD = 60

QUEUED_STATUSES = ("PENDING", "PROCESSING")


def resolve_course_id(platform_base, course_uuid: str) -> int | None:
    """step-E8-02 — {course_uuid} из URL это Course.course_uuid платформы, а `course_id`
    в ai_* таблицах — Course.id (PK). Резолвится reflection'ом на каждый запрос."""
    Course = platform_base.classes.courses_course
    with PlatformSession(platform_base.engine) as platform_session:
        return platform_session.execute(
            select(Course.id).where(Course.course_uuid == course_uuid)
        ).scalar_one_or_none()


def resolve_company_slug_for_course(platform_base, course_id: int) -> str | None:
    """company_slug для `HHClient` — платформа мультитенантна (`Course.company_id` ->
    `Company.slug`), не единое значение из `.env` (найдено архитектурным ревью перед
    прод-деплоем E16 — единый `HH_BACKEND_COMPANY_SLUG` ломал бы все компании кроме
    захардкоженной)."""
    Course = platform_base.classes.courses_course
    Company = platform_base.classes.companies_company
    with PlatformSession(platform_base.engine) as platform_session:
        return platform_session.execute(
            select(Company.slug).join(Course, Course.company_id == Company.id).where(Course.id == course_id)
        ).scalar_one_or_none()


def resolve_company_slug_for_hh_negotiation(platform_base, hh_negotiation_id: int) -> str | None:
    """Для чистых HH-лидов (ещё не сконвертировавшихся в `Application`) компания
    резолвится через `HHNegotiationRecord.mapping` -> `VacancyCourseMapping.course` ->
    `Course.company`. `mapping` может быть `NULL` (лид ещё не привязан к вакансии/курсу)
    — тогда `None`, вызывающая сторона должна трактовать как resume недоступен."""
    Negotiation = platform_base.classes.headhunter_hhnegotiationrecord
    Mapping = platform_base.classes.headhunter_vacancycoursemapping
    Course = platform_base.classes.courses_course
    Company = platform_base.classes.companies_company
    with PlatformSession(platform_base.engine) as platform_session:
        return platform_session.execute(
            select(Company.slug)
            .select_from(Negotiation)
            .join(Mapping, Negotiation.mapping_id == Mapping.id)
            .join(Course, Mapping.course_id == Course.id)
            .join(Company, Course.company_id == Company.id)
            .where(Negotiation.id == hh_negotiation_id)
        ).scalar_one_or_none()


def get_summary(session: Session, course_id: int) -> dict[str, int]:
    """03_TDD.md, «3. API / контракты» — агрегат по AIProcessingJob.status +
    CandidateVacancyAnalysis наличие для course. total — кандидаты, хоть раз затронутые
    очередью или анализом для этого course (без похода в платформенные Application)."""
    touched_candidates = (
        select(AIProcessingJob.candidate_profile_id.label("candidate_profile_id"))
        .where(AIProcessingJob.course_id == course_id)
        .union(
            select(CandidateVacancyAnalysis.candidate_profile_id.label("candidate_profile_id")).where(
                CandidateVacancyAnalysis.course_id == course_id
            )
        )
        .subquery()
    )
    total = session.scalar(select(func.count()).select_from(touched_candidates)) or 0
    processed = (
        session.scalar(
            select(func.count(func.distinct(CandidateVacancyAnalysis.candidate_profile_id))).where(
                CandidateVacancyAnalysis.course_id == course_id,
                CandidateVacancyAnalysis.is_current.is_(True),
            )
        )
        or 0
    )
    queued = (
        session.scalar(
            select(func.count())
            .select_from(AIProcessingJob)
            .where(AIProcessingJob.course_id == course_id, AIProcessingJob.status.in_(QUEUED_STATUSES))
        )
        or 0
    )
    errors = (
        session.scalar(
            select(func.count())
            .select_from(AIProcessingJob)
            .where(AIProcessingJob.course_id == course_id, AIProcessingJob.status == "FAILED")
        )
        or 0
    )
    return {"total": total, "processed": processed, "queued": queued, "errors": errors}


_ANALYSIS_FIELDS = ("fit_score", "confidence", "data_completeness", "recommendation")


def _snapshot_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """step-E8-03 — человекочитаемый diff `input_snapshot` между соседними версиями:
    только ключи, у которых значение реально поменялось, {key: {old, new}}."""
    keys = set(old) | set(new)
    return {key: {"old": old.get(key), "new": new.get(key)} for key in keys if old.get(key) != new.get(key)}


def _changed_fields(previous: CandidateVacancyAnalysis, current: CandidateVacancyAnalysis) -> list[str]:
    return [field for field in _ANALYSIS_FIELDS if getattr(previous, field) != getattr(current, field)]


def get_candidate_detail(session: Session, course_id: int, candidate_profile_id: int) -> dict[str, Any] | None:
    """03_TDD.md, «3. API / контракты» — полная карточка: текущий
    CandidateVacancyAnalysis + CandidateProfile.facts + evidence + сжатая история версий.
    None — нет ни одной версии анализа для этого candidate_profile_id+course_id (404 в роуте)."""
    versions = (
        session.execute(
            select(CandidateVacancyAnalysis)
            .where(
                CandidateVacancyAnalysis.candidate_profile_id == candidate_profile_id,
                CandidateVacancyAnalysis.course_id == course_id,
            )
            .order_by(CandidateVacancyAnalysis.version)
        )
        .scalars()
        .all()
    )
    if not versions:
        return None

    current = next((v for v in versions if v.is_current), versions[-1])
    profile = session.get(CandidateProfile, candidate_profile_id)
    facts = profile.facts if profile is not None else []

    resume_extracts = session.scalars(
        select(ResumeExtract).where(ResumeExtract.candidate_profile_id == candidate_profile_id)
    ).all()

    history = []
    previous: CandidateVacancyAnalysis | None = None
    for version in versions:
        history.append(
            {
                "id": version.id,
                "version": version.version,
                "fit_score": version.fit_score,
                "analyzed_at": version.analyzed_at,
                "changed": _changed_fields(previous, version) if previous is not None else [],
            }
        )
        previous = version

    return {
        "candidate_profile_id": candidate_profile_id,
        "resume_status": resume_status(resume_extracts),
        "current": {
            "id": current.id,
            "version": current.version,
            "fit_score": current.fit_score,
            "confidence": current.confidence,
            "data_completeness": current.data_completeness,
            "recommendation": current.recommendation,
            "summary": current.summary,
            "strengths": current.strengths,
            "risks": current.risks,
            "gaps": current.gaps,
            "missing_information": current.missing_information,
            "criteria_scores": current.criteria_scores,
            "evidence": current.evidence,
            "contradictions": current.contradictions,
            "interview_questions": current.interview_questions,
            "analyzed_at": current.analyzed_at,
        },
        "facts": facts,
        "history": history,
    }


def get_candidate_history(session: Session, course_id: int, candidate_profile_id: int) -> dict[str, Any] | None:
    """03_TDD.md — список версий CandidateVacancyAnalysis с human-readable diff
    `input_snapshot` между соседними версиями (объясняет «52→87»). None — нет версий (404)."""
    versions = (
        session.execute(
            select(CandidateVacancyAnalysis)
            .where(
                CandidateVacancyAnalysis.candidate_profile_id == candidate_profile_id,
                CandidateVacancyAnalysis.course_id == course_id,
            )
            .order_by(CandidateVacancyAnalysis.version)
        )
        .scalars()
        .all()
    )
    if not versions:
        return None

    items = []
    previous: CandidateVacancyAnalysis | None = None
    for version in versions:
        items.append(
            {
                "id": version.id,
                "version": version.version,
                "fit_score": version.fit_score,
                "confidence": version.confidence,
                "recommendation": version.recommendation,
                "analyzed_at": version.analyzed_at,
                "input_snapshot_diff": (
                    _snapshot_diff(previous.input_snapshot, version.input_snapshot) if previous is not None else {}
                ),
            }
        )
        previous = version

    return {"candidate_profile_id": candidate_profile_id, "items": items}


def _demo_progress_by_candidate_profile(
    session: Session, platform_base, course_id: int, candidate_profile_ids: list[int]
) -> dict[int, int | None]:
    """Процент прохождения демо-курса — та же формула, что уже задублирована дважды в
    sfera_backend (`CourseCandidatesBaseSerializer.get_progress`,
    `candidates_archive_service.py`), см. PLATFORM_AUDIT_REFERENCE.md раздел 12.
    Третья копия здесь осознанна — AI-сервис читает платформенную БД только read-only
    reflection'ом, общий Python-helper с Django-кодом платформы недоступен."""
    if not candidate_profile_ids:
        return {}
    profile_rows = session.execute(
        select(CandidateProfile.id, CandidateProfile.application_id).where(
            CandidateProfile.id.in_(candidate_profile_ids)
        )
    ).all()
    application_id_by_profile = {row.id: row.application_id for row in profile_rows if row.application_id is not None}
    result: dict[int, int | None] = dict.fromkeys(candidate_profile_ids)
    if not application_id_by_profile:
        return result

    Application = platform_base.classes.courses_application
    Progress = platform_base.classes.courses_progress
    with PlatformSession(platform_base.engine) as platform_session:
        application_rows = platform_session.execute(
            select(Application.id, Application.candidate_id).where(
                Application.id.in_(application_id_by_profile.values())
            )
        ).all()
        candidate_id_by_application = {row.id: row.candidate_id for row in application_rows}
        progress_rows = platform_session.execute(
            select(Progress.candidate_id, Progress.completed_lessons, Progress.total_lessons).where(
                Progress.course_id == course_id,
                Progress.candidate_id.in_(candidate_id_by_application.values()),
            )
        ).all()
        progress_by_candidate = {
            row.candidate_id: (round(row.completed_lessons / row.total_lessons * 100) if row.total_lessons else 0)
            for row in progress_rows
        }

    for profile_id, application_id in application_id_by_profile.items():
        candidate_id = candidate_id_by_application.get(application_id)
        if candidate_id is None:
            continue
        result[profile_id] = progress_by_candidate.get(candidate_id, 0)
    return result


def _application_id_by_candidate_profile(session: Session, candidate_profile_ids: list[int]) -> dict[int, int | None]:
    """`CandidateProfile.application_id` (платформенный `Application.id`) по профилю —
    ключ, по которому фронтенд SPHERA сопоставляет строку скрининга с уже загруженной
    карточкой кандидата (имя/email), т.к. `candidate_profile_id` — внутренний
    идентификатор SFERA-AI, платформе неизвестный (step-E15-08). `None` — кандидат
    привязан только по `hh_negotiation_id`, без `Application` (см. constraint
    `CandidateProfile`), фронтенд в этом случае карточку не находит."""
    if not candidate_profile_ids:
        return {}
    rows = session.execute(
        select(CandidateProfile.id, CandidateProfile.application_id).where(
            CandidateProfile.id.in_(candidate_profile_ids)
        )
    ).all()
    return {row.id: row.application_id for row in rows}


def _resume_status_by_candidate_profile(session: Session, candidate_profile_ids: list[int]) -> dict[int, str]:
    """Батч-загрузка `ResumeExtract` по всем кандидатам страницы одним запросом
    (E13-02) — без N+1 на кандидата, аналогично `_demo_progress_by_candidate_profile`."""
    if not candidate_profile_ids:
        return {}
    extracts = session.scalars(
        select(ResumeExtract).where(ResumeExtract.candidate_profile_id.in_(candidate_profile_ids))
    ).all()
    extracts_by_profile: dict[int, list[ResumeExtract]] = {profile_id: [] for profile_id in candidate_profile_ids}
    for extract in extracts:
        extracts_by_profile[extract.candidate_profile_id].append(extract)
    return {profile_id: resume_status(profile_extracts) for profile_id, profile_extracts in extracts_by_profile.items()}


def list_candidates(session: Session, platform_base, course_id: int, *, limit: int, offset: int) -> dict[str, Any]:
    """03_TDD.md, «3. API / контракты» — список кандидатов курса по текущей версии
    CandidateVacancyAnalysis, с fit_delta (текущий vs предыдущая версия) и demo_progress."""
    total = (
        session.scalar(
            select(func.count())
            .select_from(CandidateVacancyAnalysis)
            .where(CandidateVacancyAnalysis.course_id == course_id, CandidateVacancyAnalysis.is_current.is_(True))
        )
        or 0
    )
    rows = (
        session.execute(
            select(CandidateVacancyAnalysis)
            .where(CandidateVacancyAnalysis.course_id == course_id, CandidateVacancyAnalysis.is_current.is_(True))
            .order_by(CandidateVacancyAnalysis.candidate_profile_id)
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    candidate_profile_ids = [row.candidate_profile_id for row in rows]
    demo_progress_map = _demo_progress_by_candidate_profile(session, platform_base, course_id, candidate_profile_ids)
    resume_status_map = _resume_status_by_candidate_profile(session, candidate_profile_ids)

    items = []
    for analysis in rows:
        previous_fit_score = session.scalar(
            select(CandidateVacancyAnalysis.fit_score).where(
                CandidateVacancyAnalysis.candidate_profile_id == analysis.candidate_profile_id,
                CandidateVacancyAnalysis.course_id == course_id,
                CandidateVacancyAnalysis.version == analysis.version - 1,
            )
        )
        fit_delta = (
            analysis.fit_score - previous_fit_score
            if analysis.fit_score is not None and previous_fit_score is not None
            else None
        )
        items.append(
            {
                "candidate_profile_id": analysis.candidate_profile_id,
                "fit_score": analysis.fit_score,
                "confidence": analysis.confidence,
                "data_completeness": analysis.data_completeness,
                "recommendation": analysis.recommendation,
                "fit_delta": fit_delta,
                "demo_progress": demo_progress_map.get(analysis.candidate_profile_id),
                "resume_status": resume_status_map.get(analysis.candidate_profile_id, "MISSING"),
            }
        )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def list_screening_candidates(session: Session, platform_base, course_id: int) -> dict[str, Any]:
    """step-E15-03 — кандидаты курса с `fit_score >= 60` для модалки скрининга,
    отсортированные по убыванию `fit_score`, поля как в `list_candidates` +
    `transferred` (E15-01, `CandidateVacancyTransfer`)."""
    rows = (
        session.execute(
            select(CandidateVacancyAnalysis)
            .where(
                CandidateVacancyAnalysis.course_id == course_id,
                CandidateVacancyAnalysis.is_current.is_(True),
                CandidateVacancyAnalysis.fit_score >= SCREENING_FIT_SCORE_THRESHOLD,
            )
            .order_by(CandidateVacancyAnalysis.fit_score.desc())
        )
        .scalars()
        .all()
    )

    candidate_profile_ids = [row.candidate_profile_id for row in rows]
    demo_progress_map = _demo_progress_by_candidate_profile(session, platform_base, course_id, candidate_profile_ids)
    resume_status_map = _resume_status_by_candidate_profile(session, candidate_profile_ids)
    application_id_map = _application_id_by_candidate_profile(session, candidate_profile_ids)
    transferred_ids = set(
        session.scalars(
            select(CandidateVacancyTransfer.candidate_profile_id).where(
                CandidateVacancyTransfer.course_id == course_id,
                CandidateVacancyTransfer.candidate_profile_id.in_(candidate_profile_ids),
            )
        ).all()
    )

    items = []
    for analysis in rows:
        previous_fit_score = session.scalar(
            select(CandidateVacancyAnalysis.fit_score).where(
                CandidateVacancyAnalysis.candidate_profile_id == analysis.candidate_profile_id,
                CandidateVacancyAnalysis.course_id == course_id,
                CandidateVacancyAnalysis.version == analysis.version - 1,
            )
        )
        fit_delta = (
            analysis.fit_score - previous_fit_score
            if analysis.fit_score is not None and previous_fit_score is not None
            else None
        )
        items.append(
            {
                "candidate_profile_id": analysis.candidate_profile_id,
                "application_id": application_id_map.get(analysis.candidate_profile_id),
                "fit_score": analysis.fit_score,
                "confidence": analysis.confidence,
                "data_completeness": analysis.data_completeness,
                "recommendation": analysis.recommendation,
                "fit_delta": fit_delta,
                "demo_progress": demo_progress_map.get(analysis.candidate_profile_id),
                "resume_status": resume_status_map.get(analysis.candidate_profile_id, "MISSING"),
                "transferred": analysis.candidate_profile_id in transferred_ids,
            }
        )
    return {"items": items}
