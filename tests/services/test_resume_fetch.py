from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.integrations.hh_client import HHClientError
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.resume_fetch import fetch_resume_bytes, fetch_resume_bytes_readonly


def _platform_base_with_answer(answer_id: int, file_key: str | None):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, file TEXT)")
        conn.exec_driver_sql(
            f"INSERT INTO testchecks_answer (id, file) VALUES ({answer_id}, "
            f"{'NULL' if file_key is None else repr(file_key)})"
        )
    return reflect_platform_tables(engine, tables=("testchecks_answer",))


def test_fetch_anketa_file_reads_from_s3(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_answer(1, "answer_file/resume.pdf")
    s3_client = MagicMock()
    s3_client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"%PDF-bytes"))}

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1,
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="test-bucket",
        )

        assert result == b"%PDF-bytes"
        s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="answer_file/resume.pdf")
        assert extract.status == "PENDING"


def test_fetch_anketa_file_missing_answer_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_answer(1, "answer_file/resume.pdf")

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=999,
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "FAILED"
        assert extract.error


def test_fetch_anketa_file_s3_error_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_answer(1, "answer_file/resume.pdf")
    s3_client = MagicMock()
    s3_client.get_object.side_effect = Exception("connection refused")

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1,
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "FAILED"
        assert "connection refused" in extract.error


def _platform_base_with_company(negotiation_id: int, *, mapping_id: int | None, company_slug: str = "acme"):
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
        conn.exec_driver_sql(f"INSERT INTO companies_company (id, slug) VALUES (1, {company_slug!r})")
        conn.exec_driver_sql("INSERT INTO courses_course (id, company_id) VALUES (1, 1)")
        conn.exec_driver_sql("INSERT INTO headhunter_vacancycoursemapping (id, course_id) VALUES (1, 1)")
        mapping_value = "NULL" if mapping_id is None else str(mapping_id)
        conn.exec_driver_sql(
            f"INSERT INTO headhunter_hhnegotiationrecord (id, mapping_id) VALUES ({negotiation_id}, {mapping_value})"
        )
    from sfera_ai.platform_db import HH_RESUME_COMPANY_TABLES
    return reflect_platform_tables(engine, tables=HH_RESUME_COMPANY_TABLES)


def test_fetch_hh_resume_calls_hh_client_with_negotiation_id(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    hh_client = MagicMock()
    hh_client.get_resume_pdf.return_value = b"%PDF-hh"
    platform_base = _platform_base_with_company(42, mapping_id=1)

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=hh_client, s3_client=MagicMock(), s3_bucket="test-bucket",
        )

        assert result == b"%PDF-hh"
        hh_client.get_resume_pdf.assert_called_once_with(42, "acme")
        assert extract.status == "PENDING"


def test_fetch_hh_resume_client_error_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    hh_client = MagicMock()
    hh_client.get_resume_pdf.side_effect = HHClientError("resume.pdf failed: 404 not found")
    platform_base = _platform_base_with_company(42, mapping_id=1)

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=hh_client, s3_client=MagicMock(), s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "FAILED"
        assert "404" in extract.error


def test_fetch_hh_resume_without_mapping_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_company(42, mapping_id=None)

    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "FAILED"
        assert "mapping" in extract.error


def test_fetch_resume_bytes_readonly_error_does_not_mutate_status(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_answer(1, "answer_file/resume.pdf")
    s3_client = MagicMock()
    s3_client.get_object.side_effect = Exception("connection refused")

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1, status="DONE",
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes_readonly(
            extract, session=session, platform_base=platform_base,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "DONE"
        assert extract.error == ""


def test_fetch_hh_resume_profile_without_negotiation_id_marks_failed(tmp_engine):
    Base.metadata.create_all(tmp_engine)

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        extract = ResumeExtract(
            candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1",
        )
        session.add(extract)
        session.commit()

        result = fetch_resume_bytes(
            extract, session=session, platform_base=MagicMock(),
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="test-bucket",
        )

        assert result is None
        assert extract.status == "FAILED"
