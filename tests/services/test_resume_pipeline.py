from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.providers import LLMResult
from sfera_ai.services.resume_pipeline import find_anketa_resume_answer_id, process_resume

_PDF_BYTES = b"%PDF-1.4 fake resume bytes"


def _hh_platform_base(negotiation_id: int = 42):
    from sqlalchemy import create_engine

    from sfera_ai.platform_db import HH_RESUME_COMPANY_TABLES, reflect_platform_tables

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE companies_company (id INTEGER PRIMARY KEY, slug TEXT)")
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, company_id INTEGER)")
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_vacancycoursemapping (id INTEGER PRIMARY KEY, course_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, mapping_id INTEGER)"
        )
        conn.exec_driver_sql("INSERT INTO companies_company (id, slug) VALUES (1, 'acme')")
        conn.exec_driver_sql("INSERT INTO courses_course (id, company_id) VALUES (1, 1)")
        conn.exec_driver_sql("INSERT INTO headhunter_vacancycoursemapping (id, course_id) VALUES (1, 1)")
        conn.exec_driver_sql(
            f"INSERT INTO headhunter_hhnegotiationrecord (id, mapping_id) VALUES ({negotiation_id}, 1)"
        )
    return reflect_platform_tables(engine, tables=HH_RESUME_COMPANY_TABLES)


def _llm_client():
    llm_client = MagicMock()
    llm_client.complete.return_value = LLMResult(
        content='{"experience_years": 5, "positions": ["Python-разработчик"]}',
        provider="openrouter",
        model="test-model",
        tokens_input=100,
        tokens_output=20,
        latency_ms=350,
    )
    return llm_client


def test_hh_resume_end_to_end_marks_done(tmp_engine, monkeypatch):
    Base.metadata.create_all(tmp_engine)
    monkeypatch.setattr(
        "sfera_ai.services.resume_pipeline.extract_text",
        lambda file_bytes, mime_type: "Иван Иванов, Python-разработчик, 5 лет опыта",
    )
    hh_client = MagicMock()
    hh_client.get_resume_pdf.return_value = _PDF_BYTES
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()

        extract = process_resume(
            session=session, platform_base=_hh_platform_base(), hh_client=hh_client,
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id="hh-1",
        )

        assert extract.status == "DONE"
        assert extract.structured_data == {"experience_years": 5, "positions": ["Python-разработчик"]}
        assert hh_client.get_resume_pdf.call_count == 1
        assert llm_client.complete.call_count == 1


def test_repeated_call_on_done_extract_makes_no_new_http_or_llm_calls(tmp_engine, monkeypatch):
    Base.metadata.create_all(tmp_engine)
    monkeypatch.setattr(
        "sfera_ai.services.resume_pipeline.extract_text",
        lambda file_bytes, mime_type: "Иван Иванов, Python-разработчик, 5 лет опыта",
    )
    hh_client = MagicMock()
    hh_client.get_resume_pdf.return_value = _PDF_BYTES
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()

        first = process_resume(
            session=session, platform_base=_hh_platform_base(), hh_client=hh_client,
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id="hh-1",
        )
        second = process_resume(
            session=session, platform_base=_hh_platform_base(), hh_client=hh_client,
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id="hh-1",
        )

        assert first.id == second.id
        assert second.status == "DONE"
        assert hh_client.get_resume_pdf.call_count == 1
        assert llm_client.complete.call_count == 1


def test_fetch_failure_returns_failed_extract_without_calling_llm(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    from sfera_ai.integrations.hh_client import HHClientError

    hh_client = MagicMock()
    hh_client.get_resume_pdf.side_effect = HHClientError("resume.pdf failed: 404 not found")
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()

        extract = process_resume(
            session=session, platform_base=_hh_platform_base(), hh_client=hh_client,
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id="hh-1",
        )

        assert extract.status == "FAILED"
        assert "404" in extract.error
        assert llm_client.complete.call_count == 0


def test_unrecognized_file_bytes_marks_failed_without_calling_llm(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    hh_client = MagicMock()
    hh_client.get_resume_pdf.return_value = b"not a real resume file"
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()

        extract = process_resume(
            session=session, platform_base=_hh_platform_base(), hh_client=hh_client,
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id="hh-1",
        )

        assert extract.status == "FAILED"
        assert extract.error
        assert llm_client.complete.call_count == 0


def test_requires_exactly_one_source():
    import pytest

    with pytest.raises(ValueError):
        process_resume(
            session=MagicMock(), platform_base=MagicMock(), hh_client=MagicMock(),
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=MagicMock(),
            candidate_profile_id=1,
        )

    with pytest.raises(ValueError):
        process_resume(
            session=MagicMock(), platform_base=MagicMock(), hh_client=MagicMock(),
            s3_client=MagicMock(), s3_bucket="test-bucket", llm_client=MagicMock(),
            candidate_profile_id=1, source_answer_id=1, hh_resume_id="hh-1",
        )


def test_anketa_file_end_to_end_marks_done(tmp_engine, monkeypatch):
    Base.metadata.create_all(tmp_engine)
    monkeypatch.setattr(
        "sfera_ai.services.resume_pipeline.extract_text",
        lambda file_bytes, mime_type: "Иван Иванов, Python-разработчик, 5 лет опыта",
    )
    from sqlalchemy import create_engine

    from sfera_ai.platform_db import reflect_platform_tables

    platform_engine = create_engine("sqlite:///:memory:")
    with platform_engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, file TEXT)")
        conn.exec_driver_sql("INSERT INTO testchecks_answer (id, file) VALUES (1, 'answer_file/resume.pdf')")
    platform_base = reflect_platform_tables(platform_engine, tables=("testchecks_answer",))

    s3_client = MagicMock()
    s3_client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=_PDF_BYTES))}
    llm_client = _llm_client()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()

        extract = process_resume(
            session=session, platform_base=platform_base, hh_client=MagicMock(),
            s3_client=s3_client, s3_bucket="test-bucket", llm_client=llm_client,
            candidate_profile_id=profile.id, source_answer_id=1,
        )

        assert extract.status == "DONE"
        assert s3_client.get_object.call_count == 1
        assert llm_client.complete.call_count == 1


def _build_answers_platform(rows: list[tuple[int, int, int, str, str]]):
    """rows: (answer_id, question_id, attempt_id, question_text, answered_at)."""
    from sqlalchemy import create_engine

    from sfera_ai.platform_db import reflect_platform_tables

    platform_engine = create_engine("sqlite:///:memory:")
    with platform_engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE testchecks_question (id INTEGER PRIMARY KEY, question_text TEXT)")
        conn.exec_driver_sql("CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, question_id INTEGER, "
            "attempt_id INTEGER, answered_at TEXT)"
        )
        for answer_id, question_id, attempt_id, question_text, answered_at in rows:
            conn.exec_driver_sql(
                f"INSERT OR IGNORE INTO testchecks_question (id, question_text) "
                f"VALUES ({question_id}, '{question_text}')"
            )
            conn.exec_driver_sql(
                f"INSERT OR IGNORE INTO testchecks_testattempt (id, candidate_id) "
                f"VALUES ({attempt_id}, {attempt_id})"
            )
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_answer (id, question_id, attempt_id, answered_at) "
                f"VALUES ({answer_id}, {question_id}, {attempt_id}, '{answered_at}')"
            )
    return reflect_platform_tables(
        platform_engine, tables=("testchecks_question", "testchecks_testattempt", "testchecks_answer")
    )


def test_find_anketa_resume_answer_id_returns_latest_matching_answer():
    platform_base = _build_answers_platform([
        (1, 10, 100, "ANKETA_RESUME", "2026-01-01T00:00:00"),
        (2, 10, 100, "ANKETA_RESUME", "2026-02-01T00:00:00"),
        (3, 20, 100, "OTHER_QUESTION", "2026-03-01T00:00:00"),
    ])

    result = find_anketa_resume_answer_id(platform_base, candidate_id=100)

    assert result == 2


def test_find_anketa_resume_answer_id_returns_none_when_no_file():
    platform_base = _build_answers_platform([
        (1, 20, 100, "OTHER_QUESTION", "2026-01-01T00:00:00"),
    ])

    result = find_anketa_resume_answer_id(platform_base, candidate_id=100)

    assert result is None
