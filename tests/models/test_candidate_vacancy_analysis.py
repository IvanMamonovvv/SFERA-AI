from datetime import datetime, timezone

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_profile import VacancyProfile


def _enable_sqlite_fk(engine):
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))


def test_candidate_vacancy_analysis_has_expected_columns():
    columns = {c.name for c in CandidateVacancyAnalysis.__table__.columns}
    assert columns == {
        "id", "candidate_profile_id", "course_id", "vacancy_profile_id", "version",
        "is_current", "fit_score", "data_completeness", "confidence", "recommendation",
        "summary", "strengths", "risks", "gaps", "missing_information", "criteria_scores",
        "evidence", "contradictions", "interview_questions", "input_snapshot",
        "provider", "model", "prompt_version", "tokens_input", "tokens_output",
        "cost_estimate", "latency_ms", "analyzed_at", "created_at", "updated_at",
    }


def test_candidate_vacancy_analysis_unique_constraint_on_candidate_course_version():
    constraint_columns = {
        tuple(c.name for c in uc.columns)
        for uc in CandidateVacancyAnalysis.__table__.constraints
        if uc.__class__.__name__ == "UniqueConstraint"
    }
    assert ("candidate_profile_id", "course_id", "version") in constraint_columns


def test_candidate_vacancy_analysis_has_candidate_course_current_index():
    index_columns = {
        tuple(c.name for c in idx.columns)
        for idx in CandidateVacancyAnalysis.__table__.indexes
    }
    assert ("candidate_profile_id", "course_id", "is_current") in index_columns


def _make_analysis(session, candidate_profile_id, vacancy_profile_id, version=1):
    analysis = CandidateVacancyAnalysis(
        candidate_profile_id=candidate_profile_id,
        course_id=1,
        vacancy_profile_id=vacancy_profile_id,
        version=version,
        data_completeness=50,
        confidence="MEDIUM",
        recommendation="POSSIBLE_MATCH",
        analyzed_at=datetime.now(timezone.utc),
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def test_candidate_vacancy_analysis_defaults(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        vacancy = VacancyProfile(course_id=1, version=1, requirements={})
        session.add_all([profile, vacancy])
        session.commit()
        analysis = _make_analysis(session, profile.id, vacancy.id)
        assert analysis.is_current is True
        assert analysis.strengths == []
        assert analysis.criteria_scores == {}
        assert analysis.fit_score is None


def test_candidate_vacancy_analysis_vacancy_profile_fk_is_protect(tmp_engine):
    _enable_sqlite_fk(tmp_engine)
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.execute(text("PRAGMA foreign_keys=ON"))
        profile = CandidateProfile(application_id=1)
        vacancy = VacancyProfile(course_id=1, version=1, requirements={})
        session.add_all([profile, vacancy])
        session.commit()
        _make_analysis(session, profile.id, vacancy.id)

        session.delete(vacancy)
        with pytest.raises(IntegrityError):
            session.commit()


def test_candidate_vacancy_analysis_cascades_on_candidate_profile_delete(tmp_engine):
    _enable_sqlite_fk(tmp_engine)
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.execute(text("PRAGMA foreign_keys=ON"))
        profile = CandidateProfile(application_id=1)
        vacancy = VacancyProfile(course_id=1, version=1, requirements={})
        session.add_all([profile, vacancy])
        session.commit()
        analysis = _make_analysis(session, profile.id, vacancy.id)
        analysis_id = analysis.id

        session.delete(profile)
        session.commit()

        assert session.get(CandidateVacancyAnalysis, analysis_id) is None
