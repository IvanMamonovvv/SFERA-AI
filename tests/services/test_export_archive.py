import zipfile
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.export.archive import build_candidates_export_archive

TABLES = (
    "courses_application", "testchecks_testattempt", "testchecks_answer", "testchecks_transcriptionjob",
    "courses_course", "companies_company",
)
COURSE_ID = 1


def _platform_base(*, video_answer=None, resume_answer=None, application_id=7, candidate_id=100):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER, file TEXT)")
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob (id INTEGER PRIMARY KEY, answer_id INTEGER, status TEXT)"
        )
        conn.exec_driver_sql("CREATE TABLE companies_company (id INTEGER PRIMARY KEY, name TEXT)")
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, company_id INTEGER)")
        conn.exec_driver_sql(
            f"INSERT INTO courses_application (id, candidate_id) VALUES ({application_id}, {candidate_id})"
        )
        conn.exec_driver_sql(f"INSERT INTO testchecks_testattempt (id, candidate_id) VALUES (1, {candidate_id})")
        if video_answer is not None:
            answer_id, file_key = video_answer
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_answer (id, attempt_id, file) VALUES ({answer_id}, 1, '{file_key}')"
            )
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_transcriptionjob (answer_id, status) VALUES ({answer_id}, 'DONE')"
            )
        if resume_answer is not None:
            answer_id, file_key = resume_answer
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_answer (id, attempt_id, file) VALUES ({answer_id}, 1, '{file_key}')"
            )
    return reflect_platform_tables(engine, tables=TABLES)


def _valid_pdf_bytes() -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 700, "resume page")
    c.showPage()
    c.save()
    return buffer.getvalue()


def _s3_client(files: dict[str, bytes]):
    s3_client = MagicMock()

    def get_object(Bucket, Key):
        if Key not in files:
            raise Exception(f"NoSuchKey: {Key}")
        return {"Body": MagicMock(read=MagicMock(return_value=files[Key]))}

    s3_client.get_object.side_effect = get_object
    return s3_client


def _seed_candidate_with_analysis(session, *, application_id: int) -> int:
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    profile = CandidateProfile(application_id=application_id, facts=[])
    session.add(profile)
    session.flush()
    session.add(
        CandidateVacancyAnalysis(
            candidate_profile_id=profile.id,
            course_id=COURSE_ID,
            vacancy_profile_id=vacancy.id,
            version=1,
            is_current=True,
            fit_score=70,
            data_completeness=50,
            confidence="MEDIUM",
            recommendation="POSSIBLE_MATCH",
            criteria_scores={"communication": 8},
            analyzed_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    return profile.id


def test_archive_contains_subfolder_per_candidate_with_available_files(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(video_answer=(2, "video.mp4"), application_id=7, candidate_id=100)
    s3_client = _s3_client({"video.mp4": b"video-bytes"})

    with Session(tmp_engine) as session:
        candidate_profile_id = _seed_candidate_with_analysis(session, application_id=7)

        archive_bytes = build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        names = set(archive.namelist())
        folder = f"candidate_{candidate_profile_id}"
        assert f"{folder}/card.pdf" in names
        assert f"{folder}/video.mp4" in names
        assert archive.read(f"{folder}/video.mp4") == b"video-bytes"
        assert f"{folder}/manifest.txt" in names
        manifest = archive.read(f"{folder}/manifest.txt").decode()
        assert "resume: недоступно" in manifest


def test_pdf_resume_merges_into_card_pdf_not_separate_file(tmp_engine):
    """step-E17-03 — резюме PDF мерджится страницами в card.pdf, не отдельный resume.pdf."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100, resume_answer=(1, "resume.pdf"))
    s3_client = _s3_client({"resume.pdf": _valid_pdf_bytes()})

    with Session(tmp_engine) as session:
        candidate_profile_id = _seed_candidate_with_analysis(session, application_id=7)
        session.add(
            ResumeExtract(
                candidate_profile_id=candidate_profile_id, source_type="ANKETA_FILE",
                source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        archive_bytes = build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        folder = f"candidate_{candidate_profile_id}"
        names = set(archive.namelist())
        assert f"{folder}/card.pdf" in names
        assert f"{folder}/resume.pdf" not in names
        card_pages = len(PdfReader(BytesIO(archive.read(f"{folder}/card.pdf"))).pages)
        assert card_pages == 2  # 1 карточка + 1 резюме


def test_non_pdf_resume_gets_stub_page_and_stays_as_separate_file(tmp_engine):
    """step-E17-03 п.1 — резюме не PDF: страница-заглушка в card.pdf + сам файл всё равно в ZIP."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100, resume_answer=(1, "resume.docx"))
    s3_client = _s3_client({"resume.docx": b"PK\x03\x04docx-not-a-real-docx"})

    with Session(tmp_engine) as session:
        candidate_profile_id = _seed_candidate_with_analysis(session, application_id=7)
        session.add(
            ResumeExtract(
                candidate_profile_id=candidate_profile_id, source_type="ANKETA_FILE",
                source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        archive_bytes = build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        folder = f"candidate_{candidate_profile_id}"
        names = set(archive.namelist())
        assert f"{folder}/card.pdf" in names
        assert f"{folder}/resume.docx" in names
        assert archive.read(f"{folder}/resume.docx") == b"PK\x03\x04docx-not-a-real-docx"
        card_pages = len(PdfReader(BytesIO(archive.read(f"{folder}/card.pdf"))).pages)
        assert card_pages == 2  # 1 карточка + 1 заглушка


def test_resume_written_separately_when_card_pdf_unavailable(tmp_engine):
    """Резюме доступно, но card.pdf нет (нет анализа) — merge не применим, резюме кладём как раньше."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100, resume_answer=(1, "resume.pdf"))
    s3_client = _s3_client({"resume.pdf": b"%PDF-1.4\nresume-bytes"})

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7, facts=[])
        session.add(profile)
        session.commit()
        candidate_profile_id = profile.id
        session.add(
            ResumeExtract(
                candidate_profile_id=candidate_profile_id, source_type="ANKETA_FILE",
                source_answer_id=1, status="DONE",
            )
        )
        session.commit()

        archive_bytes = build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        folder = f"candidate_{candidate_profile_id}"
        names = set(archive.namelist())
        assert f"{folder}/card.pdf" not in names
        assert f"{folder}/resume.pdf" in names
        assert archive.read(f"{folder}/resume.pdf") == b"%PDF-1.4\nresume-bytes"


def test_archive_manifest_notes_expired_video_and_missing_analysis(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(video_answer=(2, "video.mp4"), application_id=7, candidate_id=100)
    s3_client = _s3_client({})  # video удалено, истёк срок хранения

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7, facts=[])
        session.add(profile)
        session.commit()
        candidate_profile_id = profile.id

        archive_bytes = build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=s3_client, s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        folder = f"candidate_{candidate_profile_id}"
        assert f"{folder}/card.pdf" not in archive.namelist()
        assert f"{folder}/video.mp4" not in archive.namelist()
        manifest = archive.read(f"{folder}/manifest.txt").decode()
        assert "card.pdf: недоступно" in manifest
        assert "video.mp4: недоступно (истёк срок хранения)" in manifest


def test_archive_multiple_candidates_get_separate_folders(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base_a = _platform_base(application_id=7, candidate_id=100)

    with Session(tmp_engine) as session:
        first_id = _seed_candidate_with_analysis(session, application_id=7)
        second = CandidateProfile(application_id=8, facts=[])
        session.add(second)
        session.commit()
        second_id = second.id

        archive_bytes = build_candidates_export_archive(
            session, platform_base_a, [first_id, second_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        assert any(name.startswith(f"candidate_{first_id}/") for name in names)
        assert any(name.startswith(f"candidate_{second_id}/") for name in names)


def _transferred_ids(session: Session, course_id: int) -> set[int]:
    return set(
        session.scalars(
            select(CandidateVacancyTransfer.candidate_profile_id).where(
                CandidateVacancyTransfer.course_id == course_id
            )
        ).all()
    )


def test_export_marks_transfer_only_for_candidate_with_card(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100)

    with Session(tmp_engine) as session:
        candidate_profile_id = _seed_candidate_with_analysis(session, application_id=7)

        build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

        assert _transferred_ids(session, COURSE_ID) == {candidate_profile_id}


def test_export_does_not_mark_transfer_for_candidate_without_card(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100)

    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7, facts=[])
        session.add(profile)
        session.commit()
        candidate_profile_id = profile.id

        build_candidates_export_archive(
            session, platform_base, [candidate_profile_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

        assert _transferred_ids(session, COURSE_ID) == set()


def test_export_mixed_request_marks_only_candidate_with_card(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(application_id=7, candidate_id=100)

    with Session(tmp_engine) as session:
        with_card_id = _seed_candidate_with_analysis(session, application_id=7)
        without_card = CandidateProfile(application_id=8, facts=[])
        session.add(without_card)
        session.commit()
        without_card_id = without_card.id

        build_candidates_export_archive(
            session, platform_base, [with_card_id, without_card_id], COURSE_ID,
            hh_client=MagicMock(), s3_client=MagicMock(), s3_bucket="bucket",
        )

        assert _transferred_ids(session, COURSE_ID) == {with_card_id}
