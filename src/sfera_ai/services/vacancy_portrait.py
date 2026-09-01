import json
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from sfera_ai.providers import OpenRouterClient

logger = logging.getLogger(__name__)

PROMPT_VERSION = "vacancy-portrait-v1"
MODEL = "openai/gpt-4o-mini"

_MAX_VACANCY_TEXT_LEN = 8000

_SYSTEM_PROMPT = (
    "Ты помогаешь HR-менеджеру превратить текстовый портрет идеального кандидата (и, "
    "опционально, текст описания вакансии с внешнего сайта) в структурированные "
    "требования к кандидату. Верни ТОЛЬКО валидный JSON-объект без пояснений и "
    "markdown-обёртки, описывающий требования к кандидату (навыки, опыт, качества и "
    "прочее по смыслу портрета/описания вакансии)."
)


class InvalidVacancyRequirementsResponse(Exception):
    """LLM вернул невалидный JSON — `VacancyProfile` не создаётся, ошибка пробрасывается
    наверх (по паттерну `InvalidFitScoringResponse`/`run_resume_extraction`)."""


def _fetch_vacancy_text(source_url: str) -> str | None:
    try:
        response = httpx.get(source_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("vacancy_portrait_source_url_fetch_failed url=%s error=%s", source_url, exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:_MAX_VACANCY_TEXT_LEN]


def build_vacancy_requirements(
    portrait_text: str, source_url: str | None, *, llm_client: OpenRouterClient
) -> dict[str, Any]:
    """Портрет кандидата (+ опционально текст вакансии по `source_url`) → один LLM-вызов
    → структурированный `VacancyProfile.requirements` (03_TDD.md, step-E10-02). Ошибка
    скачивания `source_url` не блокирует сборку — продолжает только по портрету."""
    user_content = f"Портрет идеального кандидата:\n{portrait_text}"

    vacancy_text = _fetch_vacancy_text(source_url) if source_url else None
    if vacancy_text:
        user_content += f"\n\nОписание вакансии (с сайта):\n{vacancy_text}"

    result = llm_client.complete(
        model=MODEL,
        prompt_version=PROMPT_VERSION,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    try:
        requirements = json.loads(result.content)
    except json.JSONDecodeError as exc:
        raise InvalidVacancyRequirementsResponse(f"invalid JSON: {exc}") from exc

    if not isinstance(requirements, dict):
        raise InvalidVacancyRequirementsResponse("response is not a JSON object")

    if source_url:
        requirements["source_url"] = source_url

    return requirements
