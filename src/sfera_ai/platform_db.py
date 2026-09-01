from collections.abc import Sequence

from sqlalchemy import Engine, MetaData
from sqlalchemy.ext.automap import AutomapBase, automap_base


def reflect_platform_tables(engine: Engine, *, tables: Sequence[str]) -> AutomapBase:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=tables)
    base = automap_base(metadata=metadata)
    base.prepare()
    base.engine = engine  # SQLAlchemy 2.0: MetaData больше не хранит bind
    return base


IDENTITY_RESOLVER_TABLES = ("courses_application", "headhunter_hhnegotiationrecord")
VIDEO_FACTS_TABLES = ("testchecks_transcriptionjob",)
CHANGE_DETECTION_TABLES = (
    "courses_application",
    "courses_progress",
    "testchecks_answer",
    "testchecks_testattempt",
    "headhunter_hhnegotiationrecord",
)
CANDIDATE_FACTS_TABLES = CHANGE_DETECTION_TABLES + ("testchecks_transcriptionjob",)
RESUME_DETECTION_TABLES = CANDIDATE_FACTS_TABLES + ("testchecks_question",)
MERGE_DETECTION_TABLES = ("courses_candidatemergelog",)
API_READ_TABLES = ("courses_course", "courses_application", "courses_progress")
