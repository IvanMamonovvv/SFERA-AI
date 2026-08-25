# Шаг E7-04 — триггер пересчёта затронутых анализов

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E7-03, E5-03 (постановка джоб)
**Перед началом:** прочитай `03_TDD.md» «Vacancy Profile + Vacancy Memory workflow»
п.5.

## Цель

Появление активной `VacancyMemory` или новой `is_current=True` версии `VacancyProfile`
ставит `AIProcessingJob(reason=VACANCY_PROFILE_CHANGED)` для всех `is_current`-анализов
этого `course` — только пересчёт Fit, без пересборки `CandidateProfile`.

## Что сделать

1. Хук после `approve_feedback` (E7-03) и после создания новой `is_current`
   `VacancyProfile` версии (E1) — вызов `enqueue_fit_recalc_for_course(course_id)`.
2. `enqueue_fit_recalc_for_course` — находит все `CandidateVacancyAnalysis.is_current`
   этого `course`, создаёт по джобе на каждый `candidate_profile` (переиспользует
   дедупликацию E5-03 — не дублировать уже стоящую `PENDING` джобу).

## Файлы

- `src/sfera_ai/services/job_detection.py` — расширение (или отдельный модуль,
  переиспользующий helper дедупликации из E5-03)
- `tests/services/test_recalc_trigger.py`

## Критерии готовности (DoD)

- [ ] Approve фидбека → джобы на все `is_current` анализы `course`, не на все
      `CandidateVacancyAnalysis` вообще
- [ ] Повторный триггер без новых изменений — не дублирует уже стоящие джобы

## Как проверить

```bash
uv run pytest tests/services/test_recalc_trigger.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E7
   → DONE).

## Журнал

- `YYYY-MM-DD` — <что сделано>.
