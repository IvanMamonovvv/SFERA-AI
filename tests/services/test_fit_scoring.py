import json

import pytest
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.providers import LLMProviderError, LLMResult
from sfera_ai.services.fit_scoring import InvalidFitScoringResponse, run_fit_scoring

_VALID_RESPONSE = {
    "fit_score": 78,
    "data_completeness": 60,
    "confidence": "MEDIUM",
    "recommendation": "POSSIBLE_MATCH",
    "summary": ["Подходит частично", "Опыт в Python подтверждён, опыт B2B не указан"],
    "strengths": ["Python 5 лет (резюме)"],
    "risks": ["нет опыта B2B"],
    "gaps": [],
    "missing_information": [],
    "criteria_scores": {"tech": 8.0},
    "evidence": [],
    "contradictions": [],
    "interview_questions": ["Расскажите про опыт продаж"],
}


def _llm_result(content: str) -> LLMResult:
    return LLMResult(
        content=content, provider="openrouter", model="test-model",
        tokens_input=100, tokens_output=50, latency_ms=300,
    )


def _make_profiles(session: Session) -> tuple[CandidateProfile, VacancyProfile]:
    profile = CandidateProfile(
        application_id=1,
        facts=[{"key": "experience_years", "value": "5"}],
        sources_snapshot={"max_answer_id": 10},
    )
    vacancy = VacancyProfile(
        course_id=1, version=1, is_current=True, requirements={"must_have": ["Python"]},
    )
    session.add_all([profile, vacancy])
    session.commit()
    return profile, vacancy


class _StubLLMClient:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def complete(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._result


def test_creates_first_version_as_current(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(_VALID_RESPONSE)))

        analysis = run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
        )

        assert analysis.version == 1
        assert analysis.is_current is True
        assert analysis.fit_score == 78
        assert analysis.candidate_profile_id == profile.id
        assert analysis.vacancy_profile_id == vacancy.id
        assert analysis.course_id == vacancy.course_id
        assert isinstance(analysis.summary, list)
        assert len(analysis.summary) == 2


def test_non_list_summary_raises_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        bad_response = {**_VALID_RESPONSE, "summary": "не список"}
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(bad_response)))

        with pytest.raises(InvalidFitScoringResponse):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0


def test_input_snapshot_has_all_three_components(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(_VALID_RESPONSE)))

        analysis = run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            memory_ids=[5, 6],
        )

        assert analysis.input_snapshot["max_answer_id"] == 10
        assert analysis.input_snapshot["vacancy_profile_id"] == vacancy.id
        assert analysis.input_snapshot["memory_ids"] == [5, 6]


def test_second_call_unsets_previous_current_in_one_transaction(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(_VALID_RESPONSE)))

        first = run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
        )
        second = run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
        )

        session.refresh(first)
        assert first.is_current is False
        assert second.version == 2
        assert second.is_current is True


def test_invalid_json_raises_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        llm_client = _StubLLMClient(result=_llm_result("это не json"))

        with pytest.raises(InvalidFitScoringResponse):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0


def test_invalid_enum_value_raises_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        bad_response = {**_VALID_RESPONSE, "confidence": "SUPER_HIGH"}
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(bad_response)))

        with pytest.raises(InvalidFitScoringResponse):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0


def test_criteria_scores_out_of_range_raises_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        bad_response = {**_VALID_RESPONSE, "criteria_scores": {"tech": 100}}
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(bad_response)))

        with pytest.raises(InvalidFitScoringResponse):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0


def test_criteria_scores_off_step_raises_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        bad_response = {**_VALID_RESPONSE, "criteria_scores": {"tech": 10.5}}
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(bad_response)))

        with pytest.raises(InvalidFitScoringResponse):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0


def test_criteria_scores_valid_half_step_or_none_accepted(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        good_response = {**_VALID_RESPONSE, "criteria_scores": {"tech": 8.5, "sales": None}}
        llm_client = _StubLLMClient(result=_llm_result(json.dumps(good_response)))

        analysis = run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
        )

        assert analysis.criteria_scores == {"tech": 8.5, "sales": None}


def test_provider_error_propagates_and_writes_nothing(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile, vacancy = _make_profiles(session)
        llm_client = _StubLLMClient(error=LLMProviderError("OpenRouter 500"))

        with pytest.raises(LLMProviderError):
            run_fit_scoring(
                session, candidate_profile=profile, vacancy_profile=vacancy, llm_client=llm_client,
            )

        assert session.query(CandidateVacancyAnalysis).count() == 0
