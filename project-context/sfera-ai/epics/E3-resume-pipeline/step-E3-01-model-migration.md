# Шаг E3-01 — `ResumeExtract` модель + Alembic-ревизия

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E2 (модель `CandidateProfile` должна существовать — FK)
**Перед началом:** прочитай `03_TDD.md` раздел «2. Сущности / данные» → `ResumeExtract`,
раздел «Migration Plan».

## Цель

Есть таблица `ai_resume_extract` с полями и констрейнтами по TDD, миграция применяется
на dev-схему без ошибок.

## Что сделать

1. SQLAlchemy-модель `ResumeExtract` (`candidate_profile_id` FK CASCADE,
   `source_type` choices `ANKETA_FILE`/`HH_RESUME`, `source_answer_id` nullable,
   `hh_resume_id` nullable, `raw_text`, `structured_data` JSON, `status` choices
   `PENDING`/`DONE`/`FAILED`, `error`, `provider`/`model`/`prompt_version`,
   `processed_at` nullable).
2. `CheckConstraint`: ровно одно из `source_answer_id`/`hh_resume_id` заполнено.
3. `UniqueConstraint` partial: `(source_answer_id)` где не null; `(candidate_profile_id,
   hh_resume_id)` где `hh_resume_id` не null.
4. Alembic-ревизия (следующий номер после текущего head — см. номера ревизий E1/E2).

## Файлы

- `src/sfera_ai/models/resume_extract.py` — модель
- `migrations/versions/000X_ai_resume_extract.py` — ревизия
- `tests/models/test_resume_extract.py` — constraint-тесты (SQLite, partial unique —
  проверить, что реально работает как в Postgres, либо явно задокументировать разрыв,
  как в E1/E2)

## Критерии готовности (DoD)

- [x] Модель + тесты на констрейнты (ровно один источник; дубль по `source_answer_id`
      падает)
- [x] `uv run pytest` зелёный
- [x] Alembic upgrade без ошибок на staging (downgrade только на SQLite, staging — только upgrade head)

## Как проверить

```bash
uv run pytest tests/models/test_resume_extract.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — модель `ResumeExtract`, ревизия `0003_ai_resume_extract.py`, тесты
  (6 тестов на констрейнты) — уже были в рабочем дереве, проверены и доведены до DoD.
  `uv run pytest` — 26 passed (полный сьют, без регрессий). При `alembic upgrade head`
  на staging упал `InsufficientPrivilege` на FK к `testchecks_answer` — тот же паттерн,
  что раньше с `courses_course` (E1-09). С разрешения владельца выдан
  `GRANT REFERENCES ON testchecks_answer TO ai_owner;` на staging (роль `sfera_app`),
  повторный `alembic upgrade head` прошёл, таблица `ai_resume_extract` подтверждена
  `\d` — все констрейнты и FK на месте. Downgrade на staging не запускался (правило
  проекта — только SQLite). Туннель снесён после проверки.
