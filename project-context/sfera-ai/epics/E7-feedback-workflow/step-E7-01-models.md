# Шаг E7-01 — `VacancyFeedback` + `VacancyMemory` модели + Alembic

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1
**Перед началом:** прочитай `03_TDD.md` «2. Сущности / данные» → `VacancyFeedback`,
`VacancyMemory`.

## Цель

Обе таблицы созданы по схеме TDD, миграция применяется чисто.

## Что сделать

1. `VacancyFeedback`: `course_id` CASCADE, `candidate_profile_id` CASCADE nullable,
   `analysis_id` SET_NULL nullable, `author_id` SET_NULL nullable, `text`, `sentiment`
   choices, `ai_suggested_rule`, `applied` default False.
2. `VacancyMemory`: `course_id` CASCADE, `rule_text`, `weight_hint` choices
   (`BOOST`/`PENALIZE`/`INFO_ONLY`), `source_feedback_id` SET_NULL nullable,
   `approved_by_id` SET_NULL nullable, `approved_at`, `is_active` default True.
3. Индексы: `VacancyFeedback(course, applied)`, `VacancyMemory(course, is_active)`.
4. Alembic-ревизия (одна на обе таблицы — по прецеденту TDD «Migration Plan» 0004).

## Файлы

- `src/sfera_ai/models/vacancy_feedback.py`
- `src/sfera_ai/models/vacancy_memory.py`
- `migrations/versions/000X_ai_vacancy_feedback_memory.py`
- `tests/models/test_vacancy_feedback.py`, `tests/models/test_vacancy_memory.py`

## Критерии готовности (DoD)

- [x] Обе модели покрыты тестами на constraints/индексы
- [x] Alembic upgrade/downgrade чисто (upgrade проверен на staging, downgrade — на SQLite tmp_engine)

## Как проверить

```bash
uv run pytest tests/models/test_vacancy_feedback.py tests/models/test_vacancy_memory.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-28` — `VacancyFeedback`/`VacancyMemory` модели + миграция 0007, тесты на
  constraints/индексы/FK-поведение (8 тестов). GRANT REFERENCES ON users_customuser TO
  ai_owner выдан на staging (первый раз для этой таблицы), upgrade head применён чисто.
