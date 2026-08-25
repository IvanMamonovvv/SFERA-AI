# Шаг E6-02 — `CandidateVacancyAnalysis` модель + Alembic

**Статус:** TODO
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

- [ ] PROTECT на `vacancy_profile` подтверждён тестом (удаление профиля с зависимым
      анализом падает)
- [ ] Alembic upgrade/downgrade чисто

## Как проверить

```bash
uv run pytest tests/models/test_candidate_vacancy_analysis.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
