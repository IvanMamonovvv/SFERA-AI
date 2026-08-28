# Шаг E6-02 — `CandidateVacancyAnalysis` модель + Alembic

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1, E2
**Перед началом:** прочитай `03_TDD.md` «2. Сущности / данные» →
`CandidateVacancyAnalysis`.

## Цель

Таблица `ai_candidate_vacancy_analysis` создана по схеме TDD, append-only versioning
готов (по паре `candidate_profile, course`).

## Что сделать

1. Модель: все поля из TDD (`fit_score`, `data_completeness`, `confidence`,
   `recommendation`, `summary`, JSON-поля `strengths`/`risks`/`gaps`/
   `missing_information`/`criteria_scores`/`evidence`/`contradictions`/
   `interview_questions`, `input_snapshot`, `provider`/`model`/`prompt_version`,
   `tokens_input`/`tokens_output`/`cost_estimate`/`latency_ms`, `analyzed_at`).
2. `UniqueConstraint (candidate_profile, course, version)`, индекс `(candidate_profile,
   course, is_current)`.
3. `vacancy_profile` FK **PROTECT** (не CASCADE — отличие от остальных FK, явно
   отметить в тесте).
4. Alembic-ревизия.

## Файлы

- `src/sfera_ai/models/candidate_vacancy_analysis.py`
- `migrations/versions/000X_ai_candidate_vacancy_analysis.py`
- `tests/models/test_candidate_vacancy_analysis.py`

## Критерии готовности (DoD)

- [x] PROTECT на `vacancy_profile` подтверждён тестом (удаление профиля с зависимым
      анализом падает)
- [x] Alembic upgrade/downgrade чисто

## Как проверить

```bash
uv run pytest tests/models/test_candidate_vacancy_analysis.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — модель `CandidateVacancyAnalysis` (`src/sfera_ai/models/candidate_vacancy_analysis.py`),
  ревизия `0005` (`migrations/versions/0005_ai_candidate_vacancy_analysis.py`), тесты
  `tests/models/test_candidate_vacancy_analysis.py` (6 тестов). `course_id` без
  SQLAlchemy `ForeignKey` в модели (как `AIProcessingJob.course_id`) — платформенная
  таблица `courses_course` не в `Base.metadata`, FK на неё только в raw-миграции.
  `vacancy_profile_id` — `ForeignKey(..., ondelete="RESTRICT")` (PROTECT), подтверждено
  тестом с `PRAGMA foreign_keys=ON` на SQLite: удаление `VacancyProfile` с зависимым
  анализом падает `IntegrityError`. Upgrade head применён на staging через туннель
  (GRANT REFERENCES на `courses_course` уже был выдан в E1-09, новых grant'ов не
  потребовалось); upgrade+downgrade полного цикла проверен на отдельной SQLite-БД
  (staging не даунгрейдился). Полный тест-сьют — 94 passed.
