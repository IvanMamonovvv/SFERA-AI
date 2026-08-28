# Шаг E7-04 — триггер пересчёта затронутых анализов

**Статус:** DONE
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

- [x] Approve фидбека → джобы на все `is_current` анализы `course`, не на все
      `CandidateVacancyAnalysis` вообще
- [x] Повторный триггер без новых изменений — не дублирует уже стоящие джобы

## Как проверить

```bash
uv run pytest tests/services/test_recalc_trigger.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E7
   → DONE).

## Журнал

- 2026-08-28 — `enqueue_fit_recalc_for_course(session, course_id)` в
  `src/sfera_ai/services/job_detection.py` — берёт `CandidateVacancyAnalysis.is_current`
  этого `course`, ставит по джобе `reason=VACANCY_PROFILE_CHANGED` на каждый
  `candidate_profile`, переиспользуя `_create_job_if_absent` (E5-03). `_create_job_if_absent`
  расширен параметром `course_id` (раньше не участвовал ни в дедуп-запросе, ни в
  создании джобы — для вакансийных джоб это обязательное поле, «Вакансийные джобы
  несут `course_id` явно», `job_processing.py`). Хуки подключены в двух местах: конец
  `approve_feedback` (`vacancy_memory.py`, после commit) и конец
  `create_vacancy_profile_version` (`vacancy_profile.py`, после commit) — оба вызывают
  `enqueue_fit_recalc_for_course` напрямую (не через отдельный event/сигнал — прямой
  вызов проще и достаточен, других подписчиков не предвидится). Тесты —
  `tests/services/test_recalc_trigger.py` (3: только `is_current` анализы того же
  `course` получают джобу, повторный вызов не дублирует `PENDING`, `approve_feedback`
  триггерит recalc сквозным тестом). Полный сьют `uv run pytest` — 128 passed,
  регрессий нет. **Эпик E7 завершён.**
