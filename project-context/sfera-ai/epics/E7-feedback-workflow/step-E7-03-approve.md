# Шаг E7-03 — approve workflow (Feedback → Memory)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E7-02
**Перед началом:** прочитай `03_TDD.md` «Vacancy Profile + Vacancy Memory workflow»
п.3, «Positive feedback».

## Цель

`approve_feedback(feedback_id, approved_by)` создаёт `VacancyMemory` из
`VacancyFeedback`, помечает `feedback.applied=True`, работает одинаково для
негативного и позитивного сентимента (`weight_hint` зависит от `sentiment`).

## Что сделать

1. `approve_feedback(feedback, approved_by) -> VacancyMemory` — маппинг `sentiment` →
   `weight_hint` (`NEGATIVE`→`PENALIZE`, `POSITIVE`→`BOOST`, `NEUTRAL`→`INFO_ONLY`, если
   явно не переопределено вызывающим).
2. Транзакция: создать `VacancyMemory(is_active=True)` + `feedback.applied=True` — одна
   транзакция.
3. Повторный approve уже применённого фидбека — явная ошибка/no-op (зафиксировать
   поведение в тесте).

## Файлы

- `src/sfera_ai/services/vacancy_memory.py`
- `tests/services/test_vacancy_memory_approve.py`

## Критерии готовности (DoD)

- [x] Оба сентимента (negative/positive) создают корректный `weight_hint`
- [x] Повторный approve не создаёт вторую `VacancyMemory` от того же `feedback`

## Как проверить

```bash
uv run pytest tests/services/test_vacancy_memory_approve.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-28 — `approve_feedback(session, feedback, approved_by, weight_hint=None)` в
  `src/sfera_ai/services/vacancy_memory.py`. Маппинг сентимента на `weight_hint`
  (`NEGATIVE`→`PENALIZE`, `POSITIVE`→`BOOST`, `NEUTRAL`→`INFO_ONLY`), явный параметр
  `weight_hint` перекрывает маппинг. `rule_text` берётся из `feedback.ai_suggested_rule`
  (E7-02). Одна транзакция: `VacancyMemory(is_active=True)` + `feedback.applied=True`,
  один `commit()`. Повторный approve уже применённого фидбека — `FeedbackAlreadyAppliedError`
  ДО создания записи (явная ошибка, не no-op — решение зафиксировано тестом). Тесты —
  `tests/services/test_vacancy_memory_approve.py` (5: три сентимента параметризованы,
  явный override, повторный approve). Полный сьют `uv run pytest` — 125 passed,
  регрессий нет.
