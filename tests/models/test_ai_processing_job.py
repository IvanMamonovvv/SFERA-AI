from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile


def test_ai_processing_job_has_expected_columns():
    columns = {c.name for c in AIProcessingJob.__table__.columns}
    assert columns == {
        "id", "candidate_profile_id", "course_id", "reason", "status", "attempts",
        "last_error", "priority", "started_at", "finished_at", "retry_after",
        "created_at", "updated_at",
    }


def test_ai_processing_job_has_status_retry_after_index():
    index_columns = {
        tuple(c.name for c in idx.columns)
        for idx in AIProcessingJob.__table__.indexes
    }
    assert ("status", "retry_after") in index_columns


def test_ai_processing_job_defaults(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        job = AIProcessingJob(candidate_profile_id=profile.id, reason="MANUAL")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.status == "PENDING"
        assert job.attempts == 0
        assert job.priority == 0
        assert job.last_error == ""
