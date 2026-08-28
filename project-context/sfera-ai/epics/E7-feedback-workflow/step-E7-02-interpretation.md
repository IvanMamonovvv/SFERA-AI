# Шаг E7-02 — интерпретация фидбека (LLM `ai_suggested_rule`)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E7-01
**Перед началом:** прочитай `03_TDD.md` «Vacancy Profile + Vacancy Memory workflow»
п.1–2, «AI Pipeline» → Feedback interpretation.

## Цель

При создании `VacancyFeedback` дешёвый LLM-вызов формирует `ai_suggested_rule` —
предлагаемый текст правила для будущего `VacancyMemory`.

## Что сделать

1. `interpret_feedback(feedback: VacancyFeedback) -> str` — промпт: `text` +
   `sentiment` → короткое правило.
2. Вызов через общий `providers.py`, логирование стоимости как везде.
3. Вызывается синхронно при создании (дешёвый вызов) — не через `AIProcessingJob`, если
   не требуется по нагрузке; либо `reason=FEEDBACK_APPLIED` — решить на этом шаге и
   зафиксировать выбор в журнале.

## Файлы

- `src/sfera_ai/services/feedback_interpretation.py`
- `tests/services/test_feedback_interpretation.py` — мок LLM

## Критерии готовности (DoD)

- [x] `ai_suggested_rule` заполняется на создании `VacancyFeedback`
- [x] Ошибка LLM не блокирует сохранение самого фидбека (`ai_suggested_rule` остаётся
      пустым, не роняет запрос)

## Как проверить

```bash
uv run pytest tests/services/test_feedback_interpretation.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-28 — `interpret_feedback(feedback, llm_client)` в `src/sfera_ai/services/feedback_interpretation.py`.
  Вызов синхронный (не через `AIProcessingJob`): вызов дешёвый (короткий промпт, `gpt-4o-mini`),
  задержка на создание фидбека приемлема, отдельная очередь не оправдана. `LLMProviderError`
  ловится внутри сервиса и не пробрасывается — `ai_suggested_rule` остаётся `""`, сохранение
  `VacancyFeedback` не блокируется (вызывающий код ещё не написан — эндпоинт создания фидбека вне
  этого шага, см. следующие шаги эпика E7). Тесты — `tests/services/test_feedback_interpretation.py`
  (мок `OpenRouterClient`). Логирование через `providers.py.complete()` — как везде в пайплайне.
