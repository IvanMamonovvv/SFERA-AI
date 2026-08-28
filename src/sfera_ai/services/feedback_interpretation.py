import logging

from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.providers import LLMProviderError, OpenRouterClient

logger = logging.getLogger(__name__)

PROMPT_VERSION = "feedback-interpretation-v1"
MODEL = "openai/gpt-4o-mini"

_SYSTEM_PROMPT = (
    "Ты помогаешь HR-менеджеру превратить фидбек по кандидату в короткое правило для "
    "будущего подбора по этой вакансии. По тексту фидбека и его тональности (POSITIVE/"
    "NEGATIVE/NEUTRAL) сформулируй одно короткое правило на русском языке (не более "
    "одного предложения). Верни ТОЛЬКО текст правила, без пояснений и кавычек."
)


def interpret_feedback(feedback: VacancyFeedback, *, llm_client: OpenRouterClient) -> str:
    """Дешёвый синхронный LLM-вызов: `text` + `sentiment` → короткое предлагаемое
    правило (`ai_suggested_rule`). Вызывается синхронно при создании `VacancyFeedback`
    (step-E7-02) — не через `AIProcessingJob`: вызов дешёвый, отдельная очередь не
    оправдана. Ошибка провайдера не пробрасывается — вызывающий код должен просто
    оставить `ai_suggested_rule` пустым, не роняя сохранение фидбека."""
    try:
        result = llm_client.complete(
            model=MODEL,
            prompt_version=PROMPT_VERSION,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Тональность: {feedback.sentiment}\nФидбек: {feedback.text}",
                },
            ],
        )
    except LLMProviderError:
        logger.exception("feedback_interpretation_failed feedback_id=%s", feedback.id)
        return ""

    return result.content.strip()
