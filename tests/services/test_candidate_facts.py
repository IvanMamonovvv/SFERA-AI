import json
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.platform_db import CANDIDATE_FACTS_TABLES, reflect_platform_tables
from sfera_ai.providers import LLMResult
from sfera_ai.services.candidate_facts import build_or_update_candidate_facts, resume_status


def _platform_base(*, application=(7, 100, 5, "2026-08-20T10:00:00"), answers=(), transcription_jobs=()):
    """application: (id, candidate_id, course_id, modified_at)
    answers: [(id, attempt_id, text)]  — text None для файловых/видео-ответов
    transcription_jobs: [(answer_id, status, summary_text)]"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER, "
            "course_id INTEGER, modified_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE courses_progress (id INTEGER PRIMARY KEY, candidate_id INTEGER, "
            "course_id INTEGER, modified_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER, text TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, "
            "modified_at DATETIME, hh_resume_id TEXT, application_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob (id INTEGER PRIMARY KEY, answer_id INTEGER, "
            "status TEXT, transcript_text TEXT, summary_text TEXT, finished_at DATETIME)"
        )
        if application is not None:
            app_id, candidate_id, course_id, modified_at = application
            conn.exec_driver_sql(
                f"INSERT INTO courses_application (id, candidate_id, course_id, modified_at) "
                f"VALUES ({app_id}, {candidate_id}, {course_id}, '{modified_at}')"
            )
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_testattempt (id, candidate_id) VALUES (1, {candidate_id})"
            )
            for answer_id, attempt_id, text in answers:
                text_sql = "NULL" if text is None else f"'{text}'"
                conn.exec_driver_sql(
                    f"INSERT INTO testchecks_answer (id, attempt_id, text) "
                    f"VALUES ({answer_id}, {attempt_id}, {text_sql})"
                )
        for answer_id, status, summary_text in transcription_jobs:
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_transcriptionjob (answer_id, status, transcript_text, summary_text) "
                f"VALUES ({answer_id}, '{status}', 'raw', '{summary_text}')"
            )
    return reflect_platform_tables(engine, tables=CANDIDATE_FACTS_TABLES)


def _llm_client(content='{"facts": []}'):
    llm_client = MagicMock()
    llm_client.complete.return_value = LLMResult(
        content=content, provider="openrouter", model="test-model",
        tokens_input=10, tokens_output=5, latency_ms=100,
    )
    return llm_client


def test_no_sources_stays_minimal_and_unbuilt(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(answers=())
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        result = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert result.version == 2  # sources_snapshot стартовый {} != текущему состоянию — одна пересборка
        assert result.facts == []
        assert result.data_completeness == "MINIMAL"


def test_repeated_call_without_new_sources_leaves_facts_and_version_unchanged(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(answers=[(1, 1, "мне интересна эта вакансия")])
    llm_client = _llm_client('{"facts": [{"key": "motivation", "value": "интерес к вакансии", "answer_id": 1}]}')

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        first = build_or_update_candidate_facts(session, platform_base, llm_client, profile)
        facts_after_first = first.facts
        version_after_first = first.version
        assert llm_client.complete.call_count == 1

        second = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert second.facts == facts_after_first
        assert second.version == version_after_first
        assert llm_client.complete.call_count == 1  # повторного LLM-вызова не было


def test_new_answer_only_adds_delta_keeps_old_facts(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(answers=[(1, 1, "первый ответ")])
    llm_client = _llm_client('{"facts": [{"key": "fact_a", "value": "A", "answer_id": 1}]}')

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        build_or_update_candidate_facts(session, platform_base, llm_client, profile)
        assert profile.facts == [
            {"key": "fact_a", "value": "A", "confidence": "MEDIUM", "evidence": [{"source_type": "ANSWER", "source_id": 1}]}
        ]

    platform_base_v2 = _platform_base(answers=[(1, 1, "первый ответ"), (2, 1, "второй ответ")])
    llm_client_v2 = _llm_client('{"facts": [{"key": "fact_b", "value": "B", "answer_id": 2}]}')

    with Session(tmp_engine) as session:
        profile = session.get(CandidateProfile, profile.id)
        build_or_update_candidate_facts(session, platform_base_v2, llm_client_v2, profile)

        assert profile.facts == [
            {"key": "fact_a", "value": "A", "confidence": "MEDIUM", "evidence": [{"source_type": "ANSWER", "source_id": 1}]},
            {"key": "fact_b", "value": "B", "confidence": "MEDIUM", "evidence": [{"source_type": "ANSWER", "source_id": 2}]},
        ]
        # только новый ответ ушёл в LLM-вызов, не оба
        sent_content = llm_client_v2.complete.call_args.kwargs["messages"][1]["content"]
        assert "answer_id=2" in sent_content
        assert "answer_id=1" not in sent_content


def test_resume_and_video_facts_mixed_in_without_llm_call_on_them(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(
        answers=[(9, 1, None)],
        transcription_jobs=[(9, "DONE", "Кандидат замотивирован.")],
    )
    llm_client = _llm_client('{"facts": []}')

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
            status="DONE", structured_data={"experience_years": 5},
        )
        session.add(extract)
        session.commit()

        result = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert {"key": "experience_years", "value": 5, "confidence": "MEDIUM",
                "evidence": [{"source_type": "HH_RESUME", "source_id": extract.id}]} in result.facts
        assert {"key": "video_summary", "value": "Кандидат замотивирован.", "confidence": "MEDIUM",
                "evidence": [{"source_type": "VIDEO", "source_id": 9, "excerpt": "Кандидат замотивирован."}]} in result.facts
        assert llm_client.complete.call_count == 0  # текстовых ответов не было — LLM не звали


def test_data_completeness_all_four_sources_present_is_full(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(
        answers=[(1, 1, "ответ кандидата"), (9, 1, None)],
        transcription_jobs=[(9, "DONE", "видео-саммари")],
    )
    llm_client = _llm_client('{"facts": [{"key": "fact_a", "value": "A", "answer_id": 1}]}')

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        for source_type, hh_resume_id, source_answer_id in [
            ("HH_RESUME", "hh-1", None),
            ("ANKETA_FILE", None, 42),
        ]:
            session.add(
                ResumeExtract(
                    candidate_profile_id=profile.id, source_type=source_type,
                    hh_resume_id=hh_resume_id, source_answer_id=source_answer_id,
                    status="DONE", structured_data={"experience_years": 3},
                )
            )
        session.commit()

        result = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert result.data_completeness == "FULL"


def test_llm_provider_error_leaves_answers_unadded(tmp_engine):
    from sfera_ai.providers import LLMProviderError

    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(answers=[(1, 1, "ответ")])
    llm_client = MagicMock()
    llm_client.complete.side_effect = LLMProviderError("недоступен")

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        result = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert result.facts == []
        assert result.data_completeness == "MINIMAL"


def test_resume_facts_picked_up_on_retry_even_when_platform_snapshot_unchanged(tmp_engine):
    """Регрессия: резюме упало (DNS/сетевой сбой), факты собраны без него, снапшот
    сохранён. Позже резюме успешно доретраено (ResumeExtract.status стал DONE), но
    платформенные данные (hh_resume_id и т.д.) не менялись — снапшот совпадает. Без
    фикса `build_or_update_candidate_facts` возвращал бы профиль без изменений
    навсегда, резюме реального кандидата так и не попадало бы в facts."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(answers=[(1, 1, "первый ответ")])
    llm_client = _llm_client('{"facts": [{"key": "fact_a", "value": "A", "answer_id": 1}]}')

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        first = build_or_update_candidate_facts(session, platform_base, llm_client, profile)
        assert not any(f["key"] == "experience_years" for f in first.facts)

        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
            status="DONE", structured_data={"experience_years": 13},
        )
        session.add(extract)
        session.commit()

        second = build_or_update_candidate_facts(session, platform_base, llm_client, profile)

        assert {"key": "experience_years", "value": 13, "confidence": "MEDIUM",
                "evidence": [{"source_type": "HH_RESUME", "source_id": extract.id}]} in second.facts
        assert llm_client.complete.call_count == 1  # LLM повторно не звали — новых ответов не было


def test_resume_status_missing_when_no_extracts():
    assert resume_status([]) == "MISSING"


def test_resume_status_ok_when_any_extract_done():
    extracts = [
        ResumeExtract(candidate_profile_id=1, source_type="ANKETA_FILE", source_answer_id=1, status="FAILED"),
        ResumeExtract(candidate_profile_id=1, source_type="HH_RESUME", hh_resume_id="r1", status="DONE"),
    ]
    assert resume_status(extracts) == "OK"


def test_resume_status_failed_when_no_extract_done():
    extracts = [
        ResumeExtract(candidate_profile_id=1, source_type="HH_RESUME", hh_resume_id="r1", status="FAILED"),
        ResumeExtract(candidate_profile_id=1, source_type="ANKETA_FILE", source_answer_id=1, status="PENDING"),
    ]
    assert resume_status(extracts) == "FAILED"
