import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.providers import LLMProviderError, OpenRouterClient

PROMPT_VERSION = "resume-extract-v1"
MODEL = "openai/gpt-4o-mini"

_SYSTEM_PROMPT = (
    "Ты извлекаешь структурированные данные из текста резюме. Верни ТОЛЬКО валидный "
    "JSON-объект без пояснений и markdown-обёртки со следующими полями: "
    "full_name (строка, ФИО кандидата, или null если не найдено), "
    "experience_years (число, общий стаж в годах), positions (список должностей), "
    "companies (список компаний), salary_expectation (строка или null), "
    "phone_number (строка, телефон кандидата, или null если не найден), "
    "city (строка, город проживания кандидата, или null если не найден)."
)

_ERROR_TRUNCATE_LEN = 2000


def run_resume_extraction(extract: ResumeExtract, *, session: Session, llm_client: OpenRouterClient) -> ResumeExtract:
    """PENDING → вызов LLM → DONE + `structured_data`, или FAILED при недоступном
    провайдере или невалидном JSON-ответе (03_TDD.md, «Failure Scenarios» и шаг
    E3-04) — не пишет частичный результат, не роняет процесс."""
    try:
        result = llm_client.complete(
            model=MODEL,
            prompt_version=PROMPT_VERSION,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": extract.raw_text},
            ],
            response_format={"type": "json_object"},
        )
    except LLMProviderError as exc:
        extract.status = "FAILED"
        extract.error = str(exc)[:_ERROR_TRUNCATE_LEN]
        session.commit()
        return extract

    try:
        structured_data = json.loads(result.content)
    except json.JSONDecodeError:
        extract.status = "FAILED"
        extract.error = result.content[:_ERROR_TRUNCATE_LEN]
        extract.provider = result.provider
        extract.model = result.model
        extract.prompt_version = PROMPT_VERSION
        session.commit()
        return extract

    extract.structured_data = structured_data
    extract.provider = result.provider
    extract.model = result.model
    extract.prompt_version = PROMPT_VERSION
    extract.status = "DONE"
    extract.processed_at = datetime.now(timezone.utc)
    session.commit()
    return extract
