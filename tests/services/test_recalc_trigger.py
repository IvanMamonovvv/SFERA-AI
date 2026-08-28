from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.job_detection import enqueue_fit_recalc_for_course
from sfera_ai.services.vacancy_memory import approve_feedback


def _make_profile(session: Session, *, application_id: int) -> CandidateProfile:
    profile = CandidateProfile(application_id=application_id)
    session.add(profile)
    session.commit()
    return profile


def _make_current_analysis(
    session: Session, *, candidate_profile_id: int, course_id: int, vacancy_profile_id: int, is_current: bool = True,
) -> CandidateVacancyAnalysis:
    analysis = CandidateVacancyAnalysis(
        candidate_profile_id=candidate_profile_id, course_id=course_id, vacancy_profile_id=vacancy_profile_id,
        version=1, is_current=is_current, data_completeness=50, confidence="MEDIUM", recommendation="POSSIBLE_MATCH",
        analyzed_at=datetime.now(UTC),
    )
    session.add(analysis)
    session.commit()
    return analysis


def test_enqueue_fit_recalc_creates_job_only_for_current_analyses(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy = VacancyProfile(course_id=1, version=1, is_current=True, requirements={})
        session.add(vacancy)
        session.commit()

        current_profile = _make_profile(session, application_id=1)
        stale_profile = _make_profile(session, application_id=2)
        other_course_profile = _make_profile(session, application_id=3)

        _make_current_analysis(
            session, candidate_profile_id=current_profile.id, course_id=1, vacancy_profile_id=vacancy.id,
        )
        _make_current_analysis(
            session, candidate_profile_id=stale_profile.id, course_id=1, vacancy_profile_id=vacancy.id,
            is_current=False,
        )
        _make_current_analysis(
            session, candidate_profile_id=other_course_profile.id, course_id=2, vacancy_profile_id=vacancy.id,
        )

        created = enqueue_fit_recalc_for_course(session, 1)

        assert len(created) == 1
        assert created[0].candidate_profile_id == current_profile.id
        assert created[0].course_id == 1
        assert created[0].reason == "VACANCY_PROFILE_CHANGED"


def test_enqueue_fit_recalc_does_not_duplicate_pending_job(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy = VacancyProfile(course_id=1, version=1, is_current=True, requirements={})
        session.add(vacancy)
        session.commit()
        profile = _make_profile(session, application_id=1)
        _make_current_analysis(session, candidate_profile_id=profile.id, course_id=1, vacancy_profile_id=vacancy.id)

        first = enqueue_fit_recalc_for_course(session, 1)
        second = enqueue_fit_recalc_for_course(session, 1)

        assert len(first) == 1
        assert len(second) == 0
        assert session.query(AIProcessingJob).count() == 1


def test_approve_feedback_enqueues_recalc_for_current_analyses(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy = VacancyProfile(course_id=1, version=1, is_current=True, requirements={})
        session.add(vacancy)
        session.commit()
        profile = _make_profile(session, application_id=1)
        _make_current_analysis(session, candidate_profile_id=profile.id, course_id=1, vacancy_profile_id=vacancy.id)

        feedback = VacancyFeedback(course_id=1, text="фидбек", sentiment="POSITIVE", ai_suggested_rule="правило")
        session.add(feedback)
        session.commit()

        approve_feedback(session, feedback, approved_by=1)

        jobs = session.query(AIProcessingJob).filter_by(reason="VACANCY_PROFILE_CHANGED").all()
        assert len(jobs) == 1
        assert jobs[0].candidate_profile_id == profile.id
        assert jobs[0].course_id == 1
