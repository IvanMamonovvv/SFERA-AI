# Шаг E5-01 — `AIProcessingJob` модель + Alembic-ревизия

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E1, E2
**Перед началом:** прочитай `03_TDD.md` раздел «2. Сущности / данные» →
`AIProcessingJob`, раздел «6. Processing Queue».

## Цель

Таблица `ai_processing_job` создана по схеме TDD, миграция применяется чисто.

## Что сделать

1. Модель: `candidate_profile_id` FK CASCADE не-nullable, `course_id` FK CASCADE
   nullable, `reason` choices (10 значений из TDD), `status` choices
   `PENDING`/`PROCESSING`/`DONE`/`FAILED`, `attempts`, `last_error`, `priority`,
   `created_at`/`started_at`/`finished_at`/`retry_after`.
2. Индекс `(status, retry_after)`.
3. Alembic-ревизия.

## Файлы

- `src/sfera_ai/models/ai_processing_job.py`
- `migrations/versions/000X_ai_processing_job.py`
- `tests/models/test_ai_processing_job.py`

## Критерии готовности (DoD)

- [ ] Тесты на choices/индекс
- [ ] Alembic upgrade/downgrade чисто

## Как проверить

```bash
uv run pytest tests/models/test_ai_processing_job.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
