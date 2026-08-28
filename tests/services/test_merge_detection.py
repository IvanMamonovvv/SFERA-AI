from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_service_state import AiServiceState
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.platform_db import MERGE_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.services.merge_detection import MERGE_LOG_CURSOR_KEY, detect_and_process_merges


def _platform_base(*, merges=()):
    """merges: [(id, canonical_application_id, duplicate_application_id)]"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE courses_candidatemergelog (id INTEGER PRIMARY KEY, "
            "canonical_application_id INTEGER, duplicate_application_id INTEGER)"
        )
        for log_id, canonical_id, duplicate_id in merges:
            conn.exec_driver_sql(
                f"INSERT INTO courses_candidatemergelog "
                f"(id, canonical_application_id, duplicate_application_id) "
                f"VALUES ({log_id}, {canonical_id}, {duplicate_id})"
            )
    return reflect_platform_tables(engine, tables=MERGE_DETECTION_TABLES)


def test_merge_transfers_fk_when_target_has_no_profile(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(merges=[(1, 100, 200)])
    with Session(tmp_engine) as session:
        source = CandidateProfile(application_id=200)
        session.add(source)
        session.commit()

        detect_and_process_merges(session, platform_base)

        session.refresh(source)
        assert source.application_id == 100
        assert source.is_superseded is False


def test_merge_marks_superseded_when_target_already_has_profile(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(merges=[(1, 100, 200)])
    with Session(tmp_engine) as session:
        source = CandidateProfile(application_id=200)
        target = CandidateProfile(application_id=100)
        session.add_all([source, target])
        session.commit()

        detect_and_process_merges(session, platform_base)

        session.refresh(source)
        assert source.application_id == 200  # FK не тронут
        assert source.is_superseded is True
        assert source.superseded_by_id == target.id


def test_merge_cursor_advances_even_without_matching_source_profile(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(merges=[(1, 100, 200)])
    with Session(tmp_engine) as session:
        detect_and_process_merges(session, platform_base)

        state = session.get(AiServiceState, MERGE_LOG_CURSOR_KEY)
        assert state.value == "1"


def test_repeat_tick_without_new_merges_does_not_reprocess(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(merges=[(1, 100, 200)])
    with Session(tmp_engine) as session:
        source = CandidateProfile(application_id=200)
        target = CandidateProfile(application_id=100)
        session.add_all([source, target])
        session.commit()

        detect_and_process_merges(session, platform_base)
        session.refresh(source)
        assert source.is_superseded is True

        # ручной откат, чтобы доказать: повторный тик без новых логов ничего не трогает
        source.is_superseded = False
        session.commit()

        detect_and_process_merges(session, platform_base)
        session.refresh(source)
        assert source.is_superseded is False


def test_already_superseded_source_profile_is_skipped(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(merges=[(1, 100, 200)])
    with Session(tmp_engine) as session:
        source = CandidateProfile(application_id=200, is_superseded=True)
        session.add(source)
        session.commit()

        detect_and_process_merges(session, platform_base)

        session.refresh(source)
        assert source.application_id == 200

        state = session.get(AiServiceState, MERGE_LOG_CURSOR_KEY)
        assert state.value == "1"
