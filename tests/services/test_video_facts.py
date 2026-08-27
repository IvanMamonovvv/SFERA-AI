from sqlalchemy import create_engine

from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.video_facts import get_transcript_for_answer, video_facts_from_transcript

TABLES = ("testchecks_transcriptionjob",)


def _make_platform_base():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob ("
            "id INTEGER PRIMARY KEY, answer_id INTEGER, status TEXT, "
            "transcript_text TEXT, summary_text TEXT)"
        )
    return reflect_platform_tables(engine, tables=TABLES)


def test_get_transcript_for_answer_returns_done_job():
    platform_base = _make_platform_base()
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    from sqlalchemy.orm import Session

    with Session(platform_base.engine) as session:
        session.add(TranscriptionJob(answer_id=1, status="DONE", transcript_text="привет"))
        session.commit()

    result = get_transcript_for_answer(platform_base, answer_id=1)

    assert result is not None
    assert result.transcript_text == "привет"


def test_get_transcript_for_answer_returns_none_when_not_done():
    platform_base = _make_platform_base()
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    from sqlalchemy.orm import Session

    with Session(platform_base.engine) as session:
        session.add(TranscriptionJob(answer_id=1, status="PENDING", transcript_text=""))
        session.commit()

    result = get_transcript_for_answer(platform_base, answer_id=1)

    assert result is None


def test_get_transcript_for_answer_returns_none_when_missing():
    platform_base = _make_platform_base()

    result = get_transcript_for_answer(platform_base, answer_id=999)

    assert result is None


def test_video_facts_from_transcript_builds_fact_with_evidence():
    platform_base = _make_platform_base()
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    from sqlalchemy.orm import Session

    with Session(platform_base.engine) as session:
        session.add(
            TranscriptionJob(
                answer_id=1,
                status="DONE",
                transcript_text="привет, меня зовут...",
                summary_text="Кандидат рассказал о мотивации.",
            )
        )
        session.commit()

    job = get_transcript_for_answer(platform_base, answer_id=1)
    facts = video_facts_from_transcript(job)

    assert facts == [
        {
            "key": "video_summary",
            "value": "Кандидат рассказал о мотивации.",
            "confidence": "MEDIUM",
            "evidence": [
                {
                    "source_type": "VIDEO",
                    "source_id": 1,
                    "excerpt": "Кандидат рассказал о мотивации.",
                }
            ],
        }
    ]


def test_video_facts_from_transcript_returns_empty_list_when_no_job():
    assert video_facts_from_transcript(None) == []


def test_video_facts_from_transcript_returns_empty_list_when_no_summary():
    platform_base = _make_platform_base()
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    from sqlalchemy.orm import Session

    with Session(platform_base.engine) as session:
        session.add(
            TranscriptionJob(answer_id=1, status="DONE", transcript_text="текст", summary_text="")
        )
        session.commit()

    job = get_transcript_for_answer(platform_base, answer_id=1)

    assert video_facts_from_transcript(job) == []
