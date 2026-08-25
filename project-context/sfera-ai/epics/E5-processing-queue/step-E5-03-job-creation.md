# Шаг E5-03 — детекция событий → постановка джоб

**Статус:** TODO
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

- [ ] Каждый `reason` покрыт минимум одним тестом
- [ ] Повторный тик без изменений источников — 0 новых джоб
- [ ] Detection не делает ни одного AI-вызова (переиспользует E5-02)

## Как проверить

```bash
uv run pytest tests/services/test_job_detection.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
