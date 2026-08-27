from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.services.job_processing import backoff, process_batch, requeue_stuck_jobs


def test_empty_queue_no_ai_calls(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        processed = process_batch(session, platform_base=None, limit=5, dry_run=True)
        assert processed == []


def test_dry_run_marks_jobs_done_without_ai_call(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        session.add(AIProcessingJob(candidate_profile_id=profile.id, reason="NEW_APPLICATION"))
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=True)

        assert len(processed) == 1
        assert processed[0].status == "DONE"
        assert processed[0].finished_at is not None


def test_dry_run_flag_off_fails_instead_of_calling_real_ai(tmp_engine):
    """DoD: "dry-run флаг подтверждён" — с флагом выключенным джоба падает на
    NotImplementedError (реальный AI-клиент ещё не подключён, E6/E7), а не тихо проходит
    как DONE — подтверждает, что без явного dry_run=True реального вызова не происходит."""
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        session.add(AIProcessingJob(candidate_profile_id=profile.id, reason="NEW_APPLICATION"))
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=False)

        assert processed[0].status == "FAILED"
        assert "NotImplementedError" not in processed[0].last_error  # str(exc) без имени класса
        assert "не реализован" in processed[0].last_error


def test_one_failing_job_does_not_block_others(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()

        broken = AIProcessingJob(candidate_profile_id=999, reason="NEW_APPLICATION")  # профиля нет
        ok = AIProcessingJob(candidate_profile_id=profile.id, reason="NEW_APPLICATION")
        session.add_all([broken, ok])
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=True)

        by_id = {job.id: job for job in processed}
        assert by_id[broken.id].status == "FAILED"
        assert by_id[broken.id].attempts == 1
        assert by_id[broken.id].retry_after is not None
        assert by_id[ok.id].status == "DONE"


def test_backoff_grows_exponentially():
    assert backoff(1).total_seconds() == 5 * 60
    assert backoff(2).total_seconds() == 10 * 60
    assert backoff(3).total_seconds() == 20 * 60


def test_stuck_processing_job_requeued_to_pending(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        job = AIProcessingJob(
            candidate_profile_id=profile.id,
            reason="NEW_APPLICATION",
            status="PROCESSING",
            started_at=datetime.now(UTC) - timedelta(hours=3),
            attempts=1,
        )
        session.add(job)
        session.commit()

        requeued = requeue_stuck_jobs(session, threshold_hours=2)

        assert [j.id for j in requeued] == [job.id]
        session.refresh(job)
        assert job.status == "PENDING"
        assert job.attempts == 2
        assert job.started_at is None


def test_fresh_processing_job_not_touched(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        job = AIProcessingJob(
            candidate_profile_id=profile.id,
            reason="NEW_APPLICATION",
            status="PROCESSING",
            started_at=datetime.now(UTC) - timedelta(minutes=10),
        )
        session.add(job)
        session.commit()

        requeued = requeue_stuck_jobs(session, threshold_hours=2)

        assert requeued == []
        session.refresh(job)
        assert job.status == "PROCESSING"
        assert job.attempts == 0
