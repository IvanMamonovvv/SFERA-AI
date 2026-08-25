# Шаг E8-02 — `summary` и `candidates` (список)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E8-01, E1, E2, E6

## Цель

`GET .../ai-analysis/summary/` и `GET .../ai-analysis/candidates/` отдают данные по
контракту TDD.

## Что сделать

1. `summary/` — агрегат: всего/обработано/в очереди/ошибки (по `AIProcessingJob.status`
   + `CandidateVacancyAnalysis` наличие для `course`).
2. `candidates/` — список: `candidate_profile_id`, `fit_score`, `confidence`,
   `data_completeness`, `recommendation`, `fit_delta` (текущий vs предыдущий
   `is_current`), `demo_progress` (источник — reflection на `Progress`, если нужно).
3. Пагинация — решить схему (offset/cursor), зафиксировать в журнале.

## Файлы

- `src/sfera_ai/api/routes/candidates.py`
- `src/sfera_ai/services/api_read.py` — сервисный слой чтения (не размазывать SQL по
  роутам)
- `tests/api/test_candidates_list.py`

## Критерии готовности (DoD)

- [ ] Оба эндпоинта покрыты тестами (пустой course, course с данными)
- [ ] `fit_delta` считается корректно (сравнение двух последних версий)

## Как проверить

```bash
uv run pytest tests/api/test_candidates_list.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, схема пагинации>.
