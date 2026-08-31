import zipfile
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.export.archive import build_candidates_export_archive

TABLES = ("courses_application", "testchecks_testattempt", "testchecks_answer", "testchecks_transcriptionjob")
COURSE_ID = 1


def _platform_base(*, video_answer=None, application_id=7, candidate_id=100):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER, file TEXT)")
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob (id INTEGER PRIMARY KEY, answer_id INTEGER, status TEXT)"
        )
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
    return reflect_platform_tables(engine, tables=TABLES)


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
