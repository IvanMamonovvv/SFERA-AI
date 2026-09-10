# Шаг E24-01 — BACKFILL реально считает fit_score

**Статус:** DONE
**Слой:** Backend (SFERA-AI, свой репозиторий, без ограничений) · **Зависит от:** —
**Перед началом:** прочитай `src/sfera_ai/services/job_processing.py` (`_run_real_ai_call`,
`VACANCY_REASONS`, `process_batch`), `src/sfera_ai/services/job_detection.py`
(`enqueue_full_screening_for_course`, `enqueue_fit_recalc_for_course`), `04_STATE.md`
(запись 2026-09-10 про находку архитектурного ревью на E25).

## Цель

Кандидат, обработанный джобой `reason='BACKFILL'` (первый отклик, ни разу не
анализировался), после `status=DONE` имеет реально посчитанный `fit_score`
(`CandidateVacancyAnalysis.is_current=True`), а не только пересобранные факты.

## Контекст находки

`_run_real_ai_call` (`job_processing.py:62-86`) вызывает `run_fit_scoring` только если
`job.reason in VACANCY_REASONS`, а `VACANCY_REASONS = ("VACANCY_PROFILE_CHANGED",
"FEEDBACK_APPLIED")` (`job_processing.py:21`) — `BACKFILL` туда не входит. Для BACKFILL
джоба закрывается `DONE` после `build_or_update_candidate_facts`, `run_fit_scoring` не
вызывается вовсе. Кандидат никогда не попадёт в список подходящих
(`GET .../candidates/screening/`, `fit_score>=60`) — не потому что не подошёл, а потому
что его не считали. Найдено архитектурным ревью 2026-09-10 при разборе плана E25
(счётчик прогресса) — без этого фикса счётчик «осталось 0» будет врать.

Уже проанализированные кандидаты (есть `CandidateVacancyAnalysis.is_current=True`) этим
багом не затронуты — их пересчитывает отдельная синхронная джоба `VACANCY_PROFILE_CHANGED`,
которую ставит `create_vacancy_profile_version` (`services/vacancy_profile.py:44` →
`enqueue_fit_recalc_for_course`) при каждом сохранении портрета.

## Что сделать

1. Добавить `"BACKFILL"` в `VACANCY_REASONS` (`job_processing.py:21`) — `job.course_id`
   для BACKFILL-джоб всегда явный (`job_detection.py:104-127`, `_create_job_if_absent(...,
   course_id=course_id)`), обходной путь через `application_id` (`_job_course_id`) не
   нужен для этой ветки.
2. Проверить `_run_real_ai_call`: для `reason in VACANCY_REASONS` уже вызывается
   `build_or_update_candidate_facts` ДО `run_fit_scoring` (`job_processing.py:81-84`) —
   удостовериться, что порядок не ломается при добавлении BACKFILL (сборка фактов
   первой запускается всегда, `ensure_resume_processed` — до ветвления).
3. Отдельно решить (владелец подтвердил на этапе реализации, не додумывать самому):
   что делать с `FAILED`-джобами (любой reason), исчерпавшими `ai_processing_job_max_attempts`
   — сейчас они остаются `FAILED` навсегда без сигнала HR. Не обязательно чинить в этом
   шаге, но зафиксировать решение (чинить сейчас / отдельным шагом / не трогать) —
   влияет на дизайн E25 (что считать «незавершённым»).
4. Проверить регрессии: `_still_relevant` (`job_processing.py:29-34`) не завязан на
   `reason`, кроме `CANDIDATE_DATA_CHANGED` — BACKFILL не задет.

## Файлы

- `src/sfera_ai/services/job_processing.py` — `VACANCY_REASONS`, `_run_real_ai_call`.

## Критерии готовности (DoD)

- [ ] Новая джоба `reason='BACKFILL'`, доведённая до `DONE` через `process_batch`
  (`dry_run=False`), создаёт/обновляет `CandidateVacancyAnalysis.is_current=True` с
  посчитанным `fit_score`.
- [ ] Существующее поведение `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` не изменилось.
- [ ] `dry_run=True` для BACKFILL по-прежнему не делает реального AI-вызова (только
  идемпотентная проверка).
- [ ] Новые/обновлённые тесты в `tests/services/test_job_processing.py` — явно
  покрывают "BACKFILL создаёт CandidateVacancyAnalysis" (пробел, который нашло
  архитектурное ревью: раньше это не тестировалось вообще).
- [ ] Полный `uv run pytest` — без регрессий.

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v
uv run pytest
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг — E25-01, но E25 требует отдельного «начинай»).

## Журнал

- `2026-09-10` — `"BACKFILL"` добавлен в `VACANCY_REASONS` (`job_processing.py:21`) —
  теперь BACKFILL-джоба реально вызывает `run_fit_scoring` после
  `build_or_update_candidate_facts`, как и `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED`.
  Порядок вызовов (`ensure_resume_processed` → facts → fit_scoring) не менялся, только
  условие ветвления. `_still_relevant` не затронут (не завязан на reason кроме
  `CANDIDATE_DATA_CHANGED`). Тест `test_dry_run_flag_off_dispatches_backfill_reason_to_fit_scoring`
  (`tests/services/test_job_processing.py`) — зеркало существующего теста для
  `VACANCY_PROFILE_CHANGED`, проверяет dispatch в `run_fit_scoring` с моками.
  П.3 (FAILED-джобы, исчерпавшие `max_attempts`, без сигнала HR) — владелец подтвердил
  «чинить сейчас»: `get_summary` (`api_read.py`) получил параметр `max_attempts` и новое
  поле `permanently_failed` (подмножество `errors` с `attempts>=max_attempts`) — отдельно
  от «ещё ретраящихся» FAILED. Роут `GET .../summary/` (`api/routes/candidates.py`)
  передаёт `Settings().ai_processing_job_max_attempts`. Тест
  `test_summary_distinguishes_permanently_failed_from_retryable_errors`
  (`tests/api/test_candidates_list.py`) + обновлены существующие summary-тесты под новое
  поле в ответе. Влияет на дизайн E25: счётчик прогресса может явно показать HR
  «N кандидатов не поддаются автоматической обработке» вместо тихого зависания в errors.
  Полный `uv run pytest` — 265 passed, регрессий нет.
