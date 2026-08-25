# Шаг E7-02 — интерпретация фидбека (LLM `ai_suggested_rule`)

**Статус:** TODO
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

- [ ] `ai_suggested_rule` заполняется на создании `VacancyFeedback`
- [ ] Ошибка LLM не блокирует сохранение самого фидбека (`ai_suggested_rule` остаётся
      пустым, не роняет запрос)

## Как проверить

```bash
uv run pytest tests/services/test_feedback_interpretation.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, синхронно или через очередь — и почему>.
