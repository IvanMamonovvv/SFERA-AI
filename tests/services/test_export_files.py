from unittest.mock import MagicMock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.export.files import collect_export_files

TABLES = ("courses_application", "testchecks_testattempt", "testchecks_answer", "testchecks_transcriptionjob")


def _platform_base(*, resume_answer=None, video_answer=None, application_id=7, candidate_id=100):
    """resume_answer/video_answer: (answer_id, file_key) или None."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER, file TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob (id INTEGER PRIMARY KEY, answer_id INTEGER, status TEXT)"
        )
        conn.exec_driver_sql(
            f"INSERT INTO courses_application (id, candidate_id) VALUES ({application_id}, {candidate_id})"
        )
        conn.exec_driver_sql(f"INSERT INTO testchecks_testattempt (id, candidate_id) VALUES (1, {candidate_id})")
        if resume_answer is not None:
            answer_id, file_key = resume_answer
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_answer (id, attempt_id, file) VALUES ({answer_id}, 1, '{file_key}')"
            )
        if video_answer is not None:
            answer_id, file_key = video_answer
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_answer (id, attempt_id, file) VALUES ({answer_id}, 1, '{file_key}')"
            )
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_transcriptionjob (answer_id, status) VALUES ({answer_id}, 'DONE')"
            )
    return reflect_platform_tables(engine, tables=TABLES)


def _s3_client(files: dict[str, bytes]):
    s3_client = MagicMock()

    def get_object(Bucket, Key):
        if Key not in files:
            raise Exception(f"NoSuchKey: {Key}")
        return {"Body": MagicMock(read=MagicMock(return_value=files[Key]))}

    s3_client.get_object.side_effect = get_object
    return s3_client


def test_collects_resume_and_video_when_both_available(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(resume_answer=(1, "resume.pdf"), video_answer=(2, "video.mp4"))
    s3_client = _s3_client({"resume.pdf": b"%PDF-resume", "video.mp4": b"video-bytes"})

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        result = collect_export_files(
            session, platform_base, profile.id, hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

        assert result["resume"] == {"available": True, "bytes": b"%PDF-resume", "source_type": "ANKETA_FILE"}
        assert result["video"] == {"available": True, "bytes": b"video-bytes", "answer_id": 2}


def test_video_unavailable_when_file_expired_export_continues(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(resume_answer=(1, "resume.pdf"), video_answer=(2, "video.mp4"))
    s3_client = _s3_client({"resume.pdf": b"%PDF-resume"})  # video.mp4 отсутствует — истёк срок

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        result = collect_export_files(
            session, platform_base, profile.id, hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

        assert result["resume"]["available"] is True
        assert result["video"] == {"available": False, "bytes": None, "answer_id": 2}


def test_no_resume_extract_marks_resume_unavailable(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base()

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        result = collect_export_files(
            session, platform_base, profile.id, hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

        assert result["resume"] == {"available": False, "bytes": None, "source_type": None}
        assert result["video"] == {"available": False, "bytes": None, "answer_id": None}


def test_resume_refetch_failure_at_export_does_not_corrupt_done_status(tmp_engine):
    """Регрессия E17-02 (кандидат 2398, `04_STATE.md` 2026-09-06/2026-09-09): экспорт
    перескачивает файл уже готового (`status=DONE`) резюме для вложения в zip —
    временный сбой S3/HH при этом не должен переводить extract в `FAILED` (это поле
    отражает успех экстракции текста, используется в скоринге/фактах, а не доступность
    файла прямо сейчас)."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(resume_answer=(1, "resume.pdf"))
    s3_client = _s3_client({})  # resume.pdf отсутствует в S3 при повторном скачивании

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        result = collect_export_files(
            session, platform_base, profile.id, hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

        assert result["resume"] == {"available": False, "bytes": None, "source_type": "ANKETA_FILE"}
        extract = session.scalar(select(ResumeExtract).where(ResumeExtract.candidate_profile_id == profile.id))
        assert extract.status == "DONE"
        assert extract.error == ""


def test_resume_available_when_status_failed_but_file_downloadable(tmp_engine):
    """Регрессия карточки #2623: `status=FAILED` означает провал текстовой экстракции
    (LLM/JSON-парсинг, см. `resume_extraction.py`), не отсутствие самого файла — если
    файл реально скачивается, его нужно приложить к card.pdf даже при FAILED."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(resume_answer=(1, "resume.pdf"))
    s3_client = _s3_client({"resume.pdf": b"%PDF-resume"})

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1,
                status="FAILED", error="LLM вернул невалидный JSON",
            )
        )
        session.commit()

        result = collect_export_files(
            session, platform_base, profile.id, hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

        assert result["resume"] == {"available": True, "bytes": b"%PDF-resume", "source_type": "ANKETA_FILE"}


def test_unknown_candidate_profile_id_returns_unavailable(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base()

    with Session(tmp_engine) as session:
        result = collect_export_files(
            session, platform_base, 9999, hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

        assert result["resume"]["available"] is False
        assert result["video"]["available"] is False
