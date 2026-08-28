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


def test_dry_run_flag_off_dispatches_profile_reason_to_candidate_facts(tmp_engine, monkeypatch):
    """step-E6-04, п.1: профильный reason (не VACANCY_REASONS) → E6-01
    build_or_update_candidate_facts, ровно один вызов."""
    import sfera_ai.services.job_processing as job_processing

    calls = []
    monkeypatch.setattr(
        job_processing,
        "build_or_update_candidate_facts",
        lambda session, platform_base, llm_client, profile: calls.append(profile.id) or profile,
    )

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        session.add(AIProcessingJob(candidate_profile_id=profile.id, reason="NEW_APPLICATION"))
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=False)

        assert processed[0].status == "DONE"
        assert calls == [profile.id]


def test_dry_run_flag_off_dispatches_vacancy_reason_to_fit_scoring(tmp_engine, monkeypatch):
    """step-E6-04, п.1: вакансийный reason (VACANCY_REASONS) → E6-03 run_fit_scoring."""
    import sfera_ai.services.job_processing as job_processing
    from sfera_ai.models.vacancy_profile import VacancyProfile

    calls = []
    monkeypatch.setattr(
        job_processing,
        "run_fit_scoring",
        lambda session, *, candidate_profile, vacancy_profile, llm_client: calls.append(
            (candidate_profile.id, vacancy_profile.id)
        ),
    )

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        vacancy = VacancyProfile(course_id=42, version=1, is_current=True, requirements={})
        session.add_all([profile, vacancy])
        session.commit()
        session.add(
            AIProcessingJob(
                candidate_profile_id=profile.id, course_id=42, reason="VACANCY_PROFILE_CHANGED"
            )
        )
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=False)

        assert processed[0].status == "DONE"
        assert calls == [(profile.id, vacancy.id)]


def test_no_longer_relevant_job_skips_ai_call(tmp_engine, monkeypatch):
    """DoD п.1: джоба с уже неактуальным условием (CANDIDATE_DATA_CHANGED, но
    needs_profile_rebuild уже False) — DONE без AI-вызова, счётчик вызовов == 0."""
    import sfera_ai.services.job_processing as job_processing

    calls = []
    monkeypatch.setattr(
        job_processing,
        "build_or_update_candidate_facts",
        lambda session, platform_base, llm_client, profile: calls.append(profile.id) or profile,
    )
    monkeypatch.setattr(job_processing, "needs_profile_rebuild", lambda platform_base, profile: False)

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        session.add(
            AIProcessingJob(candidate_profile_id=profile.id, reason="CANDIDATE_DATA_CHANGED")
        )
        session.commit()

        processed = process_batch(session, platform_base=None, limit=5, dry_run=False)

        assert processed[0].status == "DONE"
        assert calls == []


def test_pilot_course_id_skips_jobs_outside_pilot(tmp_engine, monkeypatch):
    """DoD п.2: pilot_course_id ограничивает реальные AI-вызовы одним course — джоба
    вне пилота остаётся PENDING, AI не вызывается."""
    import sfera_ai.services.job_processing as job_processing

    calls = []
    monkeypatch.setattr(
        job_processing,
        "build_or_update_candidate_facts",
        lambda session, platform_base, llm_client, profile: calls.append(profile.id) or profile,
    )
    monkeypatch.setattr(job_processing, "_job_course_id", lambda platform_base, job, profile: 7)

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1, sources_snapshot={})
        session.add(profile)
        session.commit()
        job = AIProcessingJob(candidate_profile_id=profile.id, reason="NEW_APPLICATION")
        session.add(job)
        session.commit()

        processed = process_batch(
            session, platform_base=None, limit=5, dry_run=False, pilot_course_id=42
        )

        assert calls == []
        assert processed[0].status == "PENDING"
        session.refresh(job)
        assert job.status == "PENDING"


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
