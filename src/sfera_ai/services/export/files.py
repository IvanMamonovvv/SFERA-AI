from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.services.change_detection import get_candidate_id
from sfera_ai.services.resume_fetch import fetch_resume_bytes_readonly


def _resume_file(session: Session, platform_base, profile: CandidateProfile, *, hh_client, s3_client, s3_bucket):
    # status="DONE" отражает успех ТЕКСТОВОЙ экстракции (LLM-парсинг), не наличие
    # самого файла — при FAILED на этапе парсинга файл резюме зачастую физически
    # скачан и валиден, поэтому фильтр по status тут не нужен: пробуем скачать файл
    # для любой записи, fetch_resume_bytes_readonly сам вернёт None при реальной
    # недоступности (баг карточки #2623, журнал step-E17-03).
    extract = session.scalar(
        select(ResumeExtract)
        .where(ResumeExtract.candidate_profile_id == profile.id)
        .order_by(ResumeExtract.id.desc())
    )
    if extract is None:
        return {"available": False, "bytes": None, "source_type": None}
    data = fetch_resume_bytes_readonly(
        extract, session=session, platform_base=platform_base,
        hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket,
    )
    if data is None:
        return {"available": False, "bytes": None, "source_type": extract.source_type}
    return {"available": True, "bytes": data, "source_type": extract.source_type}


def _video_file(session: Session, platform_base, profile: CandidateProfile, *, s3_client, s3_bucket):
    candidate_id = get_candidate_id(platform_base, profile)
    if candidate_id is None:
        return {"available": False, "bytes": None, "answer_id": None}

    Answer = platform_base.classes.testchecks_answer
    TestAttempt = platform_base.classes.testchecks_testattempt
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    with Session(platform_base.engine) as platform_session:
        answer = platform_session.scalar(
            select(Answer)
            .join(TestAttempt, Answer.attempt_id == TestAttempt.id)
            .join(TranscriptionJob, TranscriptionJob.answer_id == Answer.id)
            .where(TestAttempt.candidate_id == candidate_id, TranscriptionJob.status == "DONE")
        )
    if answer is None or not answer.file:
        return {"available": False, "bytes": None, "answer_id": None}

    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=answer.file)
        data = response["Body"].read()
    except Exception:
        # видео удаляется из S3 через 30 дней (03_TDD.md) — TranscriptionJob остаётся
        # DONE, но файла уже нет; export продолжается без него.
        return {"available": False, "bytes": None, "answer_id": answer.id}
    return {"available": True, "bytes": data, "answer_id": answer.id}


def collect_export_files(
    session: Session, platform_base, candidate_profile_id: int, *, hh_client, s3_client, s3_bucket: str
) -> dict:
    """Шаг E9-02, 03_TDD.md «Future Export» — оригинал резюме + видеовизитка тем же
    паттерном, что архивный сервис backend'а, собственной реализацией."""
    profile = session.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        return {
            "resume": {"available": False, "bytes": None, "source_type": None},
            "video": {"available": False, "bytes": None, "answer_id": None},
        }
    return {
        "resume": _resume_file(session, platform_base, profile, hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket),
        "video": _video_file(session, platform_base, profile, s3_client=s3_client, s3_bucket=s3_bucket),
    }
