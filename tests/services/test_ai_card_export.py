from datetime import datetime, timezone

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.export.ai_card import candidate_display_name, render_ai_card_pdf


def _make_vacancy_profile(session: Session, course_id: int) -> VacancyProfile:
    vacancy_profile = VacancyProfile(course_id=course_id, version=1, is_current=True, requirements={})
    session.add(vacancy_profile)
    session.flush()
    return vacancy_profile


def test_renders_pdf_for_full_data_candidate(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy_profile = _make_vacancy_profile(session, course_id=1)
        profile = CandidateProfile(
            application_id=42,
            facts=[{"key": "experience", "value": "5 лет B2B продаж", "evidence": [{"source_type": "ANSWER", "source_id": 1}]}],
        )
        session.add(profile)
        session.flush()
        session.add(
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=1,
                vacancy_profile_id=vacancy_profile.id,
                version=1,
                is_current=True,
                fit_score=85,
                data_completeness=90,
                confidence="HIGH",
                recommendation="ADVANCE",
                summary="Сильный кандидат.",
                strengths=["Опыт B2B", "Хорошая коммуникация"],
                risks=["Нет опыта в EdTech"],
                gaps=["Не указан английский"],
                criteria_scores={"communication": 8, "sales_experience": 7},
                analyzed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        pdf = render_ai_card_pdf(session, profile.id, course_id=1)

    assert pdf is not None
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_renders_pdf_for_partial_data_candidate(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy_profile = _make_vacancy_profile(session, course_id=1)
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.flush()
        session.add(
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=1,
                vacancy_profile_id=vacancy_profile.id,
                version=1,
                is_current=True,
                fit_score=None,
                data_completeness=10,
                confidence="LOW",
                recommendation="UNCERTAIN",
                analyzed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        pdf = render_ai_card_pdf(session, profile.id, course_id=1)

    assert pdf is not None
    assert pdf.startswith(b"%PDF")


def test_candidate_display_name_fallback():
    assert candidate_display_name(42) == "Кандидат #42"


def test_candidate_display_name_uses_full_name():
    assert candidate_display_name(42, "Иванов Иван") == "Иванов Иван"


def test_candidate_display_name_fallback_on_empty_full_name():
    assert candidate_display_name(42, None) == "Кандидат #42"
    assert candidate_display_name(42, "") == "Кандидат #42"


def test_renders_pdf_with_full_name_from_resume_extract(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy_profile = _make_vacancy_profile(session, course_id=1)
        profile = CandidateProfile(application_id=42)
        session.add(profile)
        session.flush()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id,
                source_type="ANSWER",
                source_answer_id=1,
                raw_text="...",
                structured_data={"full_name": "Иванов Иван"},
                status="DONE",
            )
        )
        session.add(
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=1,
                vacancy_profile_id=vacancy_profile.id,
                version=1,
                is_current=True,
                fit_score=85,
                data_completeness=90,
                confidence="HIGH",
                recommendation="ADVANCE",
                analyzed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        pdf = render_ai_card_pdf(session, profile.id, course_id=1)

    assert pdf is not None
    assert pdf.startswith(b"%PDF")


def test_renders_pdf_falls_back_when_resume_extract_missing_full_name(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        vacancy_profile = _make_vacancy_profile(session, course_id=1)
        profile = CandidateProfile(application_id=42)
        session.add(profile)
        session.flush()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id,
                source_type="ANSWER",
                source_answer_id=1,
                raw_text="...",
                structured_data={"experience_years": 5},
                status="DONE",
            )
        )
        session.add(
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=1,
                vacancy_profile_id=vacancy_profile.id,
                version=1,
                is_current=True,
                fit_score=None,
                data_completeness=10,
                confidence="LOW",
                recommendation="UNCERTAIN",
                analyzed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        pdf = render_ai_card_pdf(session, profile.id, course_id=1)

    assert pdf is not None
    assert pdf.startswith(b"%PDF")


def test_returns_none_when_no_current_analysis(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=99)
        session.add(profile)
        session.commit()

        pdf = render_ai_card_pdf(session, profile.id, course_id=1)

    assert pdf is None
