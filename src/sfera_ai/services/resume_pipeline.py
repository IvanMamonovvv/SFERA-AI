from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.integrations.hh_client import HHClient
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.change_detection import get_candidate_id
from sfera_ai.services.resume_extraction import PROMPT_VERSION, run_resume_extraction
from sfera_ai.services.resume_fetch import fetch_resume_bytes
from sfera_ai.services.resume_text_extraction import TextExtractionError, extract_text

_PDF_MAGIC = b"%PDF"
_DOCX_MAGIC = b"PK\x03\x04"
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _sniff_mime_type(file_bytes: bytes) -> str:
    """extract_text не знает про source_type/answer.file — mime_type определяем по
    magic bytes самого файла, не по расширению (03_TDD.md, «Resume Pipeline»)."""
    if file_bytes.startswith(_PDF_MAGIC):
        return _PDF_MIME
    if file_bytes.startswith(_DOCX_MAGIC):
        return _DOCX_MIME
    raise TextExtractionError(f"не удалось определить mime_type файла (magic bytes: {file_bytes[:8]!r})")


def find_anketa_resume_answer_id(platform_base, candidate_id: int) -> int | None:
    """Анкетное резюме — `Answer` с `question.question_text == "ANKETA_RESUME"`
    (03_TDD.md, «Resume Pipeline» — гэп из E3/E5, закрыт в step-E10-01). Берёт
    последний по `answered_at`, `None` — если файл не загружен."""
    Answer = platform_base.classes.testchecks_answer
    Question = platform_base.classes.testchecks_question
    TestAttempt = platform_base.classes.testchecks_testattempt
    with PlatformSession(platform_base.engine) as platform_session:
        return platform_session.scalar(
            select(Answer.id)
            .join(Question, Answer.question_id == Question.id)
            .join(TestAttempt, Answer.attempt_id == TestAttempt.id)
            .where(Question.question_text == "ANKETA_RESUME", TestAttempt.candidate_id == candidate_id)
            .order_by(Answer.answered_at.desc())
            .limit(1)
        )


def process_resume(
    *,
    session: Session,
    platform_base,
    hh_client: HHClient,
    s3_client,
    s3_bucket: str,
    llm_client: OpenRouterClient,
    candidate_profile_id: int,
    source_answer_id: int | None = None,
    hh_resume_id: str | None = None,
) -> ResumeExtract:
    """Оркестрация fetch → extract text → LLM → сохранить (03_TDD.md, «Resume
    Pipeline»). Идемпотентна по `source_answer_id`/`(candidate_profile_id,
    hh_resume_id)` — DONE-запись переиспользуется без повторных HTTP/LLM вызовов
    («7. Риски», Cost Protection п.2); проверка на уровне сервиса, до БД-constraint,
    чтобы не тратить AI-бюджет впустую."""
    if (source_answer_id is None) == (hh_resume_id is None):
        raise ValueError("ровно один из source_answer_id/hh_resume_id обязателен")

    if source_answer_id is not None:
        lookup = select(ResumeExtract).where(ResumeExtract.source_answer_id == source_answer_id)
    else:
        lookup = select(ResumeExtract).where(
            ResumeExtract.candidate_profile_id == candidate_profile_id,
            ResumeExtract.hh_resume_id == hh_resume_id,
        )
    extract = session.scalar(lookup)

    if extract is not None and extract.status == "DONE":
        return extract

    if extract is None:
        extract = ResumeExtract(
            candidate_profile_id=candidate_profile_id,
            source_type="ANKETA_FILE" if source_answer_id is not None else "HH_RESUME",
            source_answer_id=source_answer_id,
            hh_resume_id=hh_resume_id,
        )
        session.add(extract)
        session.commit()

    if not extract.raw_text:
        file_bytes = fetch_resume_bytes(
            extract, session=session, platform_base=platform_base,
            hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket,
        )
        if file_bytes is None:
            return extract  # fetch_resume_bytes уже перевёл в FAILED

        try:
            extract.raw_text = extract_text(file_bytes, _sniff_mime_type(file_bytes))
        except TextExtractionError as exc:
            extract.status = "FAILED"
            extract.error = str(exc)
            session.commit()
            return extract
        session.commit()

    return run_resume_extraction(extract, session=session, llm_client=llm_client)


def ensure_resume_processed(profile, *, platform_base, hh_client, s3_client, s3_bucket, llm_client, session) -> None:
    """HH-лид → резюме по hh_negotiation_id; иначе — анкетное резюме по
    ANKETA_RESUME-ответу; кандидат без резюме ни там ни там — no-op
    (перенесено из cli/run_full_course_screening.py, step-E18-01a)."""
    if profile.hh_negotiation_id is not None:
        process_resume(
            session=session, platform_base=platform_base, hh_client=hh_client,
            s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client,
            candidate_profile_id=profile.id, hh_resume_id=str(profile.hh_negotiation_id),
        )
        return

    candidate_id = get_candidate_id(platform_base, profile)
    if candidate_id is None:
        return
    answer_id = find_anketa_resume_answer_id(platform_base, candidate_id)
    if answer_id is None:
        return
    process_resume(
        session=session, platform_base=platform_base, hh_client=hh_client,
        s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client,
        candidate_profile_id=profile.id, source_answer_id=answer_id,
    )


def requeue_failed_resumes(
    session: Session,
    platform_base,
    *,
    hh_client: HHClient,
    s3_client,
    s3_bucket: str,
    llm_client: OpenRouterClient,
    max_attempts: int,
) -> list[ResumeExtract]:
    """Отдельный периодический ретрай `ResumeExtract.status=FAILED` — без участия
    `AIProcessingJob`/детекции (step-E18-03). Строки с `attempts >= max_attempts`
    в выборку не попадают вообще — остаются `FAILED` навсегда."""
    from sfera_ai.services.job_processing import backoff  # локальный импорт — циклическая зависимость

    now = datetime.now(UTC)
    rows = session.scalars(
        select(ResumeExtract).where(
            ResumeExtract.status == "FAILED",
            ResumeExtract.attempts < max_attempts,
            or_(ResumeExtract.retry_after.is_(None), ResumeExtract.retry_after <= now),
        )
    ).all()

    for extract in rows:
        process_resume(
            session=session, platform_base=platform_base, hh_client=hh_client,
            s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client,
            candidate_profile_id=extract.candidate_profile_id,
            source_answer_id=extract.source_answer_id,
            hh_resume_id=extract.hh_resume_id,
        )
        if extract.status == "DONE":
            extract.retry_after = None
        else:
            extract.attempts += 1
            extract.retry_after = now + backoff(extract.attempts)
        session.commit()

    return rows


def reprocess_stale_resume_extracts(
    session: Session, *, llm_client: OpenRouterClient, candidate_profile_ids: list[int] | None = None,
) -> list[ResumeExtract]:
    """`ResumeExtract.status=DONE`, но `prompt_version` старее текущего
    `resume_extraction.PROMPT_VERSION` — уже сохранённый `structured_data` посчитан
    промптом, который мог не запрашивать поле (пример: `age` появился только в
    `resume-extract-v2`), и никогда не переизвлекается заново сам по себе (E19-E22,
    «баги после ре-обсчёта» — владелец нашёл пустые город/возраст в PDF-карточке
    у кандидата, обработанного до деплоя фикса). Переиспользует уже закэшированный
    `extract.raw_text` — HH/S3 не трогает, только повторный LLM-вызов."""
    query = select(ResumeExtract).where(
        ResumeExtract.status == "DONE", ResumeExtract.prompt_version != PROMPT_VERSION
    )
    if candidate_profile_ids is not None:
        query = query.where(ResumeExtract.candidate_profile_id.in_(candidate_profile_ids))
    rows = session.scalars(query).all()

    for extract in rows:
        run_resume_extraction(extract, session=session, llm_client=llm_client)

    return rows
