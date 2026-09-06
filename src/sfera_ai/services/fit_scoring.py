import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.providers import OpenRouterClient

PROMPT_VERSION = "fit-scoring-v2"
MODEL = "openai/gpt-4o-mini"

_CONFIDENCE_CHOICES = {"LOW", "MEDIUM", "HIGH"}
_RECOMMENDATION_CHOICES = {
    "STRONG_MATCH", "POSSIBLE_MATCH", "WEAK_MATCH", "NOT_ENOUGH_DATA", "NOT_A_MATCH",
}
_LIST_FIELDS = (
    "strengths", "risks", "gaps", "missing_information", "evidence",
    "contradictions", "interview_questions",
)

_SYSTEM_PROMPT = (
    "Ты оцениваешь соответствие кандидата вакансии по фактам о кандидате и требованиям "
    "вакансии. Каждый факт помечен evidence[0].source_type: HH_RESUME или ANKETA_FILE "
    "(резюме), ANSWER (ответ на анкету), VIDEO (видеовизитка). Приоритет источников при "
    "противоречии по одному и тому же параметру: резюме (HH_RESUME/ANKETA_FILE) важнее "
    "ответов (ANSWER), ответы важнее видео (VIDEO) — при конфликте верь более "
    "приоритетному источнику. Если в приоритетном источнике значения параметра нет, "
    "бери его из следующего по приоритету источника без штрафа за это — отсутствие "
    "значения в резюме не повод занижать оценку, если ответ или видео его подтверждают. "
    "Менее приоритетные источники не отбрасывай — используй как дополнение там, где "
    "в резюме этого параметра нет. Нехватка данных сама по себе не повод занижать оценку "
    "искусственно ниже того, что подтверждают присутствующие факты, и не блокирует "
    "кандидата — отражай в оценке реальный объём и качество доступных фактов через "
    "data_completeness и confidence, а не через искусственный потолок fit_score. "
    "Верни ТОЛЬКО валидный JSON-объект без пояснений и markdown-обёртки со "
    "следующими полями: fit_score (число 0-100 или null), data_completeness (число "
    "0-100), confidence (одно из LOW/MEDIUM/HIGH), recommendation (одно из "
    "STRONG_MATCH/POSSIBLE_MATCH/WEAK_MATCH/NOT_ENOUGH_DATA/NOT_A_MATCH), "
    "summary (строка), strengths (список строк), risks (список строк), gaps (список "
    "строк), missing_information (список строк), criteria_scores (объект строка->число), "
    "evidence (список), contradictions (список), interview_questions (список строк)."
)


class InvalidFitScoringResponse(Exception):
    """LLM вернул невалидный JSON или JSON с недопустимыми значениями полей —
    не пишет частичную версию (step-E6-03, DoD п.3), ошибка пробрасывается наверх
    для обработки на уровне очереди (E5, `AIProcessingJob.FAILED`)."""


def _build_messages(
    *, facts: list[Any], requirements: dict[str, Any], memory_rule_texts: list[str],
) -> list[dict]:
    user_content = json.dumps(
        {"facts": facts, "requirements": requirements, "vacancy_memory_rules": memory_rule_texts},
        ensure_ascii=False,
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _parse_and_validate(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InvalidFitScoringResponse(f"invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise InvalidFitScoringResponse("response is not a JSON object")

    confidence = parsed.get("confidence")
    if confidence not in _CONFIDENCE_CHOICES:
        raise InvalidFitScoringResponse(f"invalid confidence: {confidence!r}")

    recommendation = parsed.get("recommendation")
    if recommendation not in _RECOMMENDATION_CHOICES:
        raise InvalidFitScoringResponse(f"invalid recommendation: {recommendation!r}")

    data_completeness = parsed.get("data_completeness")
    if not isinstance(data_completeness, int) or not (0 <= data_completeness <= 100):
        raise InvalidFitScoringResponse(f"invalid data_completeness: {data_completeness!r}")

    fit_score = parsed.get("fit_score")
    if fit_score is not None and (not isinstance(fit_score, int) or not (0 <= fit_score <= 100)):
        raise InvalidFitScoringResponse(f"invalid fit_score: {fit_score!r}")

    for field in _LIST_FIELDS:
        if not isinstance(parsed.get(field, []), list):
            raise InvalidFitScoringResponse(f"invalid {field}: expected list")

    if not isinstance(parsed.get("criteria_scores", {}), dict):
        raise InvalidFitScoringResponse("invalid criteria_scores: expected object")

    return parsed


def run_fit_scoring(
    session: Session,
    *,
    candidate_profile: CandidateProfile,
    vacancy_profile: VacancyProfile,
    llm_client: OpenRouterClient,
    memory_ids: list[int] | None = None,
    memory_rule_texts: list[str] | None = None,
) -> CandidateVacancyAnalysis:
    """`facts + requirements + активные VacancyMemory → fit_score + evidence +
    recommendation` (step-E6-03). `VacancyMemory` (E7) ещё не реализована — вызывающий
    код передаёт пустые списки до готовности E7."""
    memory_ids = memory_ids or []
    memory_rule_texts = memory_rule_texts or []

    result = llm_client.complete(
        model=MODEL,
        prompt_version=PROMPT_VERSION,
        messages=_build_messages(
            facts=candidate_profile.facts,
            requirements=vacancy_profile.requirements,
            memory_rule_texts=memory_rule_texts,
        ),
        response_format={"type": "json_object"},
    )
    parsed = _parse_and_validate(result.content)

    course_id = vacancy_profile.course_id
    previous_current = session.scalar(
        select(CandidateVacancyAnalysis).where(
            CandidateVacancyAnalysis.candidate_profile_id == candidate_profile.id,
            CandidateVacancyAnalysis.course_id == course_id,
            CandidateVacancyAnalysis.is_current.is_(True),
        )
    )
    next_version = (previous_current.version + 1) if previous_current else 1

    if previous_current is not None:
        previous_current.is_current = False
        session.flush()  # UPDATE до INSERT — иначе partial index на miг увидит две is_current=True

    input_snapshot = {
        **candidate_profile.sources_snapshot,
        "vacancy_profile_id": vacancy_profile.id,
        "memory_ids": memory_ids,
    }

    analysis = CandidateVacancyAnalysis(
        candidate_profile_id=candidate_profile.id,
        course_id=course_id,
        vacancy_profile_id=vacancy_profile.id,
        version=next_version,
        is_current=True,
        fit_score=parsed.get("fit_score"),
        data_completeness=parsed["data_completeness"],
        confidence=parsed["confidence"],
        recommendation=parsed["recommendation"],
        summary=parsed.get("summary", ""),
        strengths=parsed.get("strengths", []),
        risks=parsed.get("risks", []),
        gaps=parsed.get("gaps", []),
        missing_information=parsed.get("missing_information", []),
        criteria_scores=parsed.get("criteria_scores", {}),
        evidence=parsed.get("evidence", []),
        contradictions=parsed.get("contradictions", []),
        interview_questions=parsed.get("interview_questions", []),
        input_snapshot=input_snapshot,
        provider=result.provider,
        model=result.model,
        prompt_version=PROMPT_VERSION,
        tokens_input=result.tokens_input,
        tokens_output=result.tokens_output,
        cost_estimate=None,  # нет согласованной формулы стоимости на модель — TODO при появлении тарифов
        latency_ms=result.latency_ms,
        analyzed_at=datetime.now(UTC),
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis
