import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.providers import LLMProviderError, OpenRouterClient
from sfera_ai.services.change_detection import compute_current_sources_snapshot, get_candidate_id
from sfera_ai.services.video_facts import video_facts_from_transcript

PROMPT_VERSION = "candidate-answers-facts-v1"
MODEL = "openai/gpt-4o-mini"

_SYSTEM_PROMPT = (
    "Ты извлекаешь прямые факты о кандидате из его ответов на анкету. Верни ТОЛЬКО "
    "валидный JSON-объект без пояснений и markdown-обёртки вида "
    '{"facts": [{"key": ..., "value": ..., "answer_id": ...}]} — key - короткое имя '
    "факта, value - его значение строкой, answer_id - id ответа-источника."
)

_RESUME_FACT_KEYS = ("experience_years", "positions", "companies", "salary_expectation")


def _resume_facts(extract: ResumeExtract) -> list[dict[str, Any]]:
    facts = []
    for key in _RESUME_FACT_KEYS:
        value = extract.structured_data.get(key)
        if not value:
            continue
        facts.append(
            {
                "key": key,
                "value": value,
                "confidence": "MEDIUM",
                "evidence": [{"source_type": extract.source_type, "source_id": extract.id}],
            }
        )
    return facts


def _answers_facts(answers: list, *, llm_client: OpenRouterClient) -> list[dict[str, Any]]:
    """Батч новых текстовых `Answer` → один LLM-вызов (03_TDD.md, «Answers Pipeline»,
    не по одному — экономия токенов). Пустой ввод/ошибка провайдера/невалидный JSON —
    факты просто не добавляются в этот тик, следующий тик подхватит через change detection."""
    user_content = "\n".join(f"[answer_id={a.id}] {a.text}" for a in answers if a.text)
    if not user_content:
        return []

    try:
        result = llm_client.complete(
            model=MODEL,
            prompt_version=PROMPT_VERSION,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
    except LLMProviderError:
        return []

    try:
        parsed = json.loads(result.content)
    except json.JSONDecodeError:
        return []

    facts = []
    for item in parsed.get("facts", []) if isinstance(parsed, dict) else []:
        if not isinstance(item, dict) or "key" not in item or "value" not in item:
            continue
        facts.append(
            {
                "key": item["key"],
                "value": item["value"],
                "confidence": "MEDIUM",
                "evidence": [{"source_type": "ANSWER", "source_id": item.get("answer_id")}],
            }
        )
    return facts


def _video_facts(platform_base, *, candidate_answer_ids: list[int]) -> list[dict[str, Any]]:
    if not candidate_answer_ids:
        return []
    TranscriptionJob = platform_base.classes.testchecks_transcriptionjob
    with PlatformSession(platform_base.engine) as platform_session:
        jobs = platform_session.scalars(
            select(TranscriptionJob).where(
                TranscriptionJob.answer_id.in_(candidate_answer_ids),
                TranscriptionJob.status == "DONE",
            )
        ).all()
    facts = []
    for job in jobs:
        facts.extend(video_facts_from_transcript(job))
    return facts


def _completeness(*, has_hh_resume: bool, has_anketa_resume: bool, has_answers: bool, has_video: bool) -> str:
    """`data_completeness` — сколько из 4 источников (03_TDD.md, «Candidate Profile —
    как строится и обновляется») реально присутствует: 0 → MINIMAL, 1-2 → PARTIAL,
    3-4 → FULL."""
    present = sum([has_hh_resume, has_anketa_resume, has_answers, has_video])
    if present == 0:
        return "MINIMAL"
    if present <= 2:
        return "PARTIAL"
    return "FULL"


def resume_status(resume_extracts: list[ResumeExtract]) -> str:
    """Шаг E13-02 — видимый статус резюме кандидата: MISSING (нет ни одной записи),
    FAILED (есть записи, но ни одна не DONE), OK (хотя бы одна DONE). Не блокирует
    скоринг (E13-01) — только сигнализирует менеджеру причину низкого confidence."""
    if not resume_extracts:
        return "MISSING"
    if any(extract.status == "DONE" for extract in resume_extracts):
        return "OK"
    return "FAILED"


def _dedupe_key(fact: dict[str, Any]) -> tuple:
    evidence = fact.get("evidence") or [{}]
    return (fact.get("key"), evidence[0].get("source_type"), evidence[0].get("source_id"))


def build_or_update_candidate_facts(
    session: Session, platform_base, llm_client: OpenRouterClient, profile: CandidateProfile
) -> CandidateProfile:
    """Шаг E6-01, 03_TDD.md «Candidate Profile — как строится и обновляется» +
    «Answers Pipeline». Переиспользует E5-02 `compute_current_sources_snapshot` как
    триггер («нет новых источников — ничего не трогаем»); при рассинхроне —
    инкрементально дополняет `facts` дельтой из ответов/резюме/видео, не переписывая
    уже сохранённые факты, пересчитывает `data_completeness`, инкрементирует `version`."""
    current_snapshot = compute_current_sources_snapshot(platform_base, profile)

    existing_keys = {_dedupe_key(fact) for fact in profile.facts}

    resume_extracts = session.scalars(
        select(ResumeExtract).where(
            ResumeExtract.candidate_profile_id == profile.id,
            ResumeExtract.status == "DONE",
        )
    ).all()
    new_facts: list[dict[str, Any]] = []
    for extract in resume_extracts:
        for fact in _resume_facts(extract):
            if _dedupe_key(fact) not in existing_keys:
                new_facts.append(fact)
                existing_keys.add(_dedupe_key(fact))

    if current_snapshot == profile.sources_snapshot and not new_facts:
        # Снапшот считается по данным платформы (change_detection.py) — не знает про
        # состояние нашего ResumeExtract. Резюме может стать DONE позже отдельным
        # ретраем (после сетевого сбоя), не меняя платформенный снапшот — без этой
        # проверки такие факты никогда не попадут в profile.facts (баг нашёл владелец
        # на реальном кандидате: резюме DONE неделю, факты из него не подтягивались).
        return profile

    candidate_id = get_candidate_id(platform_base, profile)
    candidate_answer_ids: list[int] = []
    if candidate_id is not None:
        Answer = platform_base.classes.testchecks_answer
        TestAttempt = platform_base.classes.testchecks_testattempt
        old_max_answer_id = (profile.sources_snapshot or {}).get("max_answer_id") or 0
        with PlatformSession(platform_base.engine) as platform_session:
            candidate_answers = platform_session.scalars(
                select(Answer)
                .join(TestAttempt, Answer.attempt_id == TestAttempt.id)
                .where(TestAttempt.candidate_id == candidate_id)
            ).all()
            candidate_answer_ids = [a.id for a in candidate_answers]
            new_text_answers = [a for a in candidate_answers if a.id > old_max_answer_id and a.text]

        for fact in _answers_facts(new_text_answers, llm_client=llm_client):
            if _dedupe_key(fact) not in existing_keys:
                new_facts.append(fact)
                existing_keys.add(_dedupe_key(fact))

    for fact in _video_facts(platform_base, candidate_answer_ids=candidate_answer_ids):
        if _dedupe_key(fact) not in existing_keys:
            new_facts.append(fact)
            existing_keys.add(_dedupe_key(fact))

    profile.facts = [*profile.facts, *new_facts]
    profile.data_completeness = _completeness(
        has_hh_resume=any(e.source_type == "HH_RESUME" for e in resume_extracts),
        has_anketa_resume=any(e.source_type == "ANKETA_FILE" for e in resume_extracts),
        has_answers=any(f["evidence"][0]["source_type"] == "ANSWER" for f in profile.facts),
        has_video=any(f["evidence"][0]["source_type"] == "VIDEO" for f in profile.facts),
    )
    profile.sources_snapshot = current_snapshot
    profile.version += 1
    profile.built_at = datetime.now(UTC)
    session.commit()
    session.refresh(profile)
    return profile
