from sqlalchemy.orm import Session

from sfera_ai.integrations.hh_client import HHClient, HHClientError
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.services.api_read import resolve_company_slug_for_hh_negotiation

PLATFORM_ANSWER_TABLE = "testchecks_answer"


class ResumeFetchError(Exception):
    """Файл резюме не удалось получить (сеть, 404, отсутствующий Answer)."""


def _fetch_anketa_file(extract: ResumeExtract, *, platform_base, s3_client, s3_bucket: str) -> bytes:
    Answer = platform_base.classes.testchecks_answer
    with Session(platform_base.engine) as platform_session:
        answer = platform_session.get(Answer, extract.source_answer_id)
    if answer is None or not answer.file:
        raise ResumeFetchError(f"testchecks_answer.id={extract.source_answer_id} не найден или без файла")
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=answer.file)
        return response["Body"].read()
    except Exception as exc:
        raise ResumeFetchError(f"S3 get_object failed for key={answer.file}: {exc}") from exc


def _fetch_hh_resume(extract: ResumeExtract, *, session: Session, platform_base, hh_client: HHClient) -> bytes:
    profile = session.get(CandidateProfile, extract.candidate_profile_id)
    if profile is None or profile.hh_negotiation_id is None:
        raise ResumeFetchError(
            f"candidate_profile_id={extract.candidate_profile_id} без hh_negotiation_id"
        )
    company_slug = resolve_company_slug_for_hh_negotiation(platform_base, profile.hh_negotiation_id)
    if company_slug is None:
        raise ResumeFetchError(
            f"hh_negotiation_id={profile.hh_negotiation_id} без company (mapping не назначен)"
        )
    try:
        return hh_client.get_resume_pdf(profile.hh_negotiation_id, company_slug)
    except HHClientError as exc:
        raise ResumeFetchError(str(exc)) from exc


def _dispatch_fetch(
    extract: ResumeExtract, *, session: Session, platform_base, hh_client: HHClient, s3_client, s3_bucket: str
) -> bytes:
    if extract.source_type == "ANKETA_FILE":
        return _fetch_anketa_file(extract, platform_base=platform_base, s3_client=s3_client, s3_bucket=s3_bucket)
    if extract.source_type == "HH_RESUME":
        return _fetch_hh_resume(extract, session=session, platform_base=platform_base, hh_client=hh_client)
    raise ResumeFetchError(f"неизвестный source_type: {extract.source_type}")


def fetch_resume_bytes(
    extract: ResumeExtract,
    *,
    session: Session,
    platform_base,
    hh_client: HHClient,
    s3_client,
    s3_bucket: str,
) -> bytes | None:
    """Диспетчер по `source_type`. При ошибке переводит `extract` в `FAILED` с текстом
    ошибки и возвращает `None` — не бросает исключение наружу (03_TDD.md, «Failure
    Scenarios»: HH API недоступен / битый resume → FAILED, не блокирует остальной
    пайплайн). Использовать только для первичной экстракции (`resume_pipeline.py`) —
    `status` здесь отражает успех экстракции, мутировать его можно только там."""
    try:
        return _dispatch_fetch(
            extract, session=session, platform_base=platform_base, hh_client=hh_client,
            s3_client=s3_client, s3_bucket=s3_bucket,
        )
    except ResumeFetchError as exc:
        extract.status = "FAILED"
        extract.error = str(exc)
        session.commit()
        return None


def fetch_resume_bytes_readonly(
    extract: ResumeExtract,
    *,
    session: Session,
    platform_base,
    hh_client: HHClient,
    s3_client,
    s3_bucket: str,
) -> bytes | None:
    """Повторное скачивание уже готового (`status=DONE`) резюме — для вложения оригинала
    в export-архив. В отличие от `fetch_resume_bytes`, при ошибке НЕ мутирует
    `extract.status`: этот статус отражает успех экстракции текста, а не доступность
    файла прямо сейчас — временный сбой сети/HH при повторном скачивании не должен
    портить уже готовую экстракцию (баг кандидата 2398, `04_STATE.md` 2026-09-06/E17-02)."""
    try:
        return _dispatch_fetch(
            extract, session=session, platform_base=platform_base, hh_client=hh_client,
            s3_client=s3_client, s3_bucket=s3_bucket,
        )
    except ResumeFetchError:
        return None
