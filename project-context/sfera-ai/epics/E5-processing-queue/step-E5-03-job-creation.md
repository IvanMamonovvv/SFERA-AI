# Шаг E5-03 — детекция событий → постановка джоб

**Статус:** PARTIAL — реализованы `NEW_HH_LEAD`/`NEW_APPLICATION`/`CANDIDATE_DATA_CHANGED`
(см. журнал), `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` отложены
**Слой:** Backend · **Зависит от:** E5-02, E2 (переход HH Lead), E4 (NEW_VIDEO источник)

## Цель

Тик детекции проходит по кандидатам/вакансиям и создаёт `AIProcessingJob` со всеми 10
`reason` из TDD, идемпотентно (повторный тик без изменений не плодит дубли `PENDING`).

## Что сделать

1. Функция `detect_and_enqueue()` — обходит источники событий:
   - `NEW_HH_LEAD`/`NEW_APPLICATION` — новый `CandidateProfile` без ни одной джобы
   - `NEW_ANSWER`/`NEW_RESUME`/`NEW_VIDEO` — через `needs_profile_rebuild`
   - `CANDIDATE_DATA_CHANGED` — synonim `needs_profile_rebuild=True` для существующего
     профиля
   - `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` — через `needs_fit_recalc`, джоба на
     каждый `is_current`-анализ этого `course`
   - `MANUAL`/`BACKFILL` — явный вызов извне (E8/CLI), не детекция
2. Перед созданием джобы — проверка «уже есть `PENDING`/`PROCESSING` джоба с тем же
   `candidate_profile`+`reason`?» — не дублировать.
3. Интеграция перехода HH Lead → Application (E2 `promote_hh_lead_to_application`) в
   этот же тик.

## Файлы

- `src/sfera_ai/services/job_detection.py`
- `tests/services/test_job_detection.py`

## Критерии готовности (DoD)

- [x] Каждый реализованный `reason` покрыт минимум одним тестом (`VACANCY_PROFILE_CHANGED`/
      `FEEDBACK_APPLIED` отложены — см. журнал)
- [x] Повторный тик без изменений источников — 0 новых джоб
- [x] Detection не делает ни одного AI-вызова (переиспользует E5-02)

## Как проверить

```bash
uv run pytest tests/services/test_job_detection.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — `detect_and_enqueue(session, platform_base)` реализован в
  `src/sfera_ai/services/job_detection.py`. Решения владельца (согласовано в чате):
  - **`NEW_ANSWER`/`NEW_RESUME`/`NEW_VIDEO` объединены в один `CANDIDATE_DATA_CHANGED`** —
    на уровне детекции доступен только общий флаг `needs_profile_rebuild` (bool), без
    разбора, какой конкретно источник изменился; разбор реального источника отложен на
    момент обработки джобы, не постановки.
  - **`VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` отложены** — тот же гэп, что в
    `step-E5-02-change-detection.md` (зависят от `CandidateVacancyAnalysis`/`VacancyMemory`,
    ещё не созданных).
  - **`MANUAL`/`BACKFILL`** — вне scope детекции, явный вызов извне (не реализовано здесь).

  Реализованный поток: (1) новые `headhunter_hhnegotiationrecord` без профиля →
  `resolve_or_create_candidate_profile` + `NEW_HH_LEAD`; (2) записи с заполненным
  `application_id` → `promote_hh_lead_to_application` (конверсия лида, без отдельной
  джобы на сам факт перехода); (3) новые `courses_application` без профиля и без связанного
  HH-лида → `NEW_APPLICATION`; (4) для всех существующих профилей без уже активной джобы
  (любой reason) — `needs_profile_rebuild` → `CANDIDATE_DATA_CHANGED`.

  **Найденный и исправленный баг в первой версии:** если у профиля уже есть активная
  джоба (например только что поставленная `NEW_HH_LEAD`), а `sources_snapshot` ещё не
  обновлён (профиль ещё не пересобран) — следующий тик снова видел «устарело» и плодил
  вторую джобу `CANDIDATE_DATA_CHANGED` поверх первой (избыточно: первая джоба и так
  пересоберёт профиль). Исправлено — детекция `CANDIDATE_DATA_CHANGED` пропускает
  профили с любой активной джобой (`PENDING`/`PROCESSING`), не только с той же `reason`.
  Тест `test_no_new_jobs_on_repeat_tick_without_changes` поймал это до коммита.

  Тесты `tests/services/test_job_detection.py` — 6 (все 3 реализованных reason, конверсия
  лида без лишней джобы, идемпотентность повторного тика, dedup при уже существующей
  активной джобе). Полный сьют `uv run pytest` — 72 passed, регрессий нет.
