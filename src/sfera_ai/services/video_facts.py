from sqlalchemy import select
from sqlalchemy.orm import Session


def video_facts_from_transcript(job) -> list[dict]:
    """Готовый TranscriptionJob.summary_text → факт-объект (без LLM-вызова).
    Полагается только на текстовые поля — не на видеофайл (удаляется через 30 дней)."""
    if job is None or not job.summary_text:
        return []
    return [
        {
            "key": "video_summary",
            "value": job.summary_text,
            "confidence": "MEDIUM",
            "evidence": [
                {
                    "source_type": "VIDEO",
                    "source_id": job.answer_id,
                    "excerpt": job.summary_text,
                }
            ],
        }
    ]


def get_transcript_for_answer(platform_base, *, answer_id: int):
    """Читает TranscriptionJob для answer_id через reflection. Только DONE — частичный
    результат (PENDING/PROCESSING/FAILED) не отдаётся."""
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    with Session(platform_base.engine) as session:
        return session.scalar(
            select(TranscriptionJob).where(
                TranscriptionJob.answer_id == answer_id,
                TranscriptionJob.status == "DONE",
            )
        )
