from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.providers import LLMProviderError, LLMResult
from sfera_ai.services.resume_extraction import run_resume_extraction


def _make_extract(session: Session) -> ResumeExtract:
    profile = CandidateProfile(application_id=1)
    session.add(profile)
    session.commit()
    extract = ResumeExtract(
        candidate_profile_id=profile.id,
        source_type="ANKETA_FILE",
        source_answer_id=1,
        raw_text="Иван Иванов, Python-разработчик, 5 лет опыта",
    )
    session.add(extract)
    session.commit()
    return extract


def test_valid_llm_response_marks_done(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    llm_client = MagicMock()
    llm_client.complete.return_value = LLMResult(
        content='{"experience_years": 5, "positions": ["Python-разработчик"]}',
        provider="openrouter",
        model="test-model",
        tokens_input=100,
        tokens_output=20,
        latency_ms=350,
    )

    with Session(tmp_engine) as session:
        extract = _make_extract(session)

        result = run_resume_extraction(extract, session=session, llm_client=llm_client)

        assert result.status == "DONE"
        assert result.structured_data == {"experience_years": 5, "positions": ["Python-разработчик"]}
        assert result.provider == "openrouter"
        assert result.model == "test-model"
        assert result.prompt_version
        assert result.processed_at is not None


def test_invalid_json_marks_failed_with_truncated_raw_response(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    llm_client = MagicMock()
    llm_client.complete.return_value = LLMResult(
        content="это не json, а обычный текст ответа модели",
        provider="openrouter",
        model="test-model",
        tokens_input=100,
        tokens_output=20,
        latency_ms=350,
    )

    with Session(tmp_engine) as session:
        extract = _make_extract(session)

        result = run_resume_extraction(extract, session=session, llm_client=llm_client)

        assert result.status == "FAILED"
        assert "не json" in result.error
        assert result.structured_data == {}


def test_provider_error_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    llm_client = MagicMock()
    llm_client.complete.side_effect = LLMProviderError("OpenRouter 500: internal error")

    with Session(tmp_engine) as session:
        extract = _make_extract(session)

        result = run_resume_extraction(extract, session=session, llm_client=llm_client)

        assert result.status == "FAILED"
        assert "500" in result.error
